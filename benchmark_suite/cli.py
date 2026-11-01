"""Windows menu and single-model CLI. No implicit installation or model imports."""

from __future__ import annotations

import argparse
from contextlib import redirect_stdout
from datetime import datetime, timezone
import importlib
import importlib.metadata
from io import StringIO
import json
from pathlib import Path
import re
import sys
from uuid import uuid4

from benchmark_suite.tracking import MODEL_IDS, load_status

ROOT = Path(__file__).resolve().parent
MENU = (
    "Check environment", "Show available models", "Show benchmark progress",
    "Setup selected model", "Validate datasets", "Run quick smoke test",
    "Run selected model benchmark", "Resume interrupted benchmark",
    "Evaluate stored predictions", "Generate model report", "Compare completed models",
    "Generate final comparison report", "Exit",
)


class CLIError(RuntimeError):
    def __init__(self, message, code=1, status="ERROR"):
        super().__init__(message)
        self.code, self.status = code, status


class SingleModel(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if getattr(namespace, self.dest, None) is not None:
            parser.error("Select exactly one model; repeated --model is not supported")
        setattr(namespace, self.dest, values)


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="command")
    for command, help_text in (
        ("menu", "Open the 13-option interactive menu (default)"),
        ("models", "List candidates, implementation and checkpoint blockers"),
        ("progress", "Show validated saved progress; never change approval"),
        ("check-environment", "Inspect Python, shared dependencies and live hardware"),
        ("setup", "Check the selected approved model's existing isolated setup; never install"),
        ("validate-datasets", "Rehash frozen local sources/references; no download"),
        ("smoke", "Run one approved model on the frozen development split"),
        ("run", "Run exactly one approved model, quick or full"),
        ("resume", "Resume one unfinished run with its original configuration"),
        ("evaluate", "Evaluate saved predictions without inference"),
        ("report", "Regenerate metrics/report from saved predictions, no inference"),
        ("compare", "Pending TASK-018; no inference or fabricated scores"),
        ("final-report", "Pending TASK-019; no inference or fabricated report"),
    ):
        sub = commands.add_parser(command, help=help_text)
        sub.add_argument("--json", action="store_true", help="One machine-readable JSON response")
        if command in {"check-environment", "setup", "smoke", "run", "resume", "evaluate", "report"}:
            sub.add_argument("--model", choices=MODEL_IDS, action=SingleModel,
                             required=command != "check-environment", help="One candidate; no all-model option")
        if command in {"smoke", "run"}:
            sub.add_argument("--language", choices=("en", "ar", "both"), default="both")
        if command == "run":
            sub.add_argument("--mode", choices=("quick", "full"), default="quick")
        if command in {"resume", "evaluate", "report"}:
            sub.add_argument("--run-dir", type=Path, required=True, help="Explicit saved run directory; never select latest silently")
    return result


def _json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _inside(root, value):
    path = Path(value)
    if not path.is_absolute():
        path = Path(root)/path
    path = path.resolve()
    if not path.is_relative_to(Path(root).resolve()):
        raise CLIError("Configured/artifact path leaves the suite directory")
    return path


def catalog(root):
    data = _json(root/"configs/models.json")
    if data.get("schema_version") != 1 or set(data.get("models", {})) != set(MODEL_IDS):
        raise CLIError("Model catalog must contain exactly the nine requested candidates")
    for i, model in enumerate(MODEL_IDS, 9):
        entry = data["models"][model]
        if set(entry) != {"name", "task", "spec", "config", "factory", "python", "requirements"} or entry["task"] != f"TASK-{i:03}":
            raise CLIError("Invalid model catalog entry")
        for field in ("spec", "config", "python", "requirements"):
            if entry[field] is not None:
                _inside(root, entry[field])
        if entry["factory"] is not None and not re.fullmatch(r"benchmark_suite\.adapters\.[a-z][a-z0-9_]*:[a-z][a-z0-9_]*", entry["factory"]):
            raise CLIError("Only reviewed benchmark-suite adapter factories are supported")
    return data["models"]


def model_rows(root):
    state = load_status(root/"BENCHMARK_STATUS.json")
    return [{"model": model, "name": entry["name"], "task": entry["task"],
             "state": state["models"][model], "implementation": "REGISTERED" if entry["factory"] else "PENDING",
             "reason": state["model_block_reasons"].get(model),
             "approved": entry["task"] in state["approved_tasks"]}
            for model, entry in catalog(root).items()]


def dependency_pins(path, seen=None):
    """Direct exact pins only. Inspect, never execute pip/requirements options."""
    path, seen = Path(path).resolve(), set() if seen is None else seen
    if path in seen:
        raise CLIError("Cyclic requirements include")
    seen.add(path)
    result = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith("-r "):
            included = dependency_pins(_inside(path.parent, line[3:].strip()), seen)
            for name, version in included.items():
                if name in result and result[name] != version:
                    raise CLIError("Conflicting direct dependency pins")
                result[name] = version
        elif re.fullmatch(r"[A-Za-z0-9_.-]+==[A-Za-z0-9_.+!-]+", line):
            name, version = line.split("==")
            name = re.sub(r"[-_.]+", "-", name).lower()
            if name in result and result[name] != version:
                raise CLIError("Conflicting direct dependency pins")
            result[name] = version
        else:
            raise CLIError("Requirements must contain reviewed exact pins and local -r includes")
    seen.remove(path)
    return result


def dependencies(root):
    rows = []
    for name, expected in dependency_pins(root/"requirements-runner.txt").items():
        try:
            actual = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            actual = None
        rows.append({"package": name, "expected": expected, "installed": actual, "ready": actual == expected})
    return rows


def _require_dependencies(root):
    missing = [r for r in dependencies(root) if not r["ready"]]
    if missing:
        raise CLIError(f"Shared dependencies differ from tested pins: {', '.join(r['package'] for r in missing)}. "
                       "Use an existing compatible interpreter or the reviewed requirements-runner.txt in an isolated environment. Nothing was installed.")


def _environment_reasons(root, model, entry):
    reasons = []
    if entry["python"] is None or entry["requirements"] is None:
        return ["Isolated pinned model environment is not registered"]
    target = _inside(root, entry["python"])
    env_root = (root/"environments"/model).resolve()
    if not target.is_relative_to(env_root) or not target.is_file():
        reasons.append("Registered model interpreter is missing or outside its isolated model environment")
    if Path(sys.prefix).resolve() != env_root:
        reasons.append(f"Use the explicitly registered isolated interpreter: {target}; the CLI will not switch environments automatically")
    pins = dependency_pins(_inside(root, entry["requirements"]))
    if not pins:
        reasons.append("Model requirements must include reviewed exact pins")
    for name, expected in pins.items():
        try:
            actual = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            actual = None
        if actual != expected:
            reasons.append(f"Model dependency mismatch: {name}")
    return reasons


def _ready(root, model):
    """Metadata only: never import a factory to determine readiness."""
    from benchmark_suite.runners.preflight import PreflightBlocked, authorize_model
    entry = catalog(root)[model]
    state = load_status(root/"BENCHMARK_STATUS.json")
    reasons = []
    try:
        authorize_model(model, root/"BENCHMARK_STATUS.json")
    except PreflightBlocked as exc:
        reasons.extend(exc.reasons)
    if state["models"][model] == "BLOCKED":
        reasons.append(state["model_block_reasons"][model])
    if not all(entry[k] for k in ("factory", "spec", "config")):
        reasons.append(f"Adapter/setup is PENDING {entry['task']}; separate model-specific approval required")
    reasons.extend(_environment_reasons(root, model, entry))
    return entry, list(dict.fromkeys(reasons))


def _definition(root, model):
    entry, reasons = _ready(root, model)
    if reasons:
        raise CLIError(f"{model}: " + "; ".join(reasons), 3, "BLOCKED")
    from benchmark_suite.runners.schemas import AdapterSpec, RunConfig
    selected = AdapterSpec.model_validate(_json(_inside(root, entry["spec"])))
    settings = RunConfig.model_validate(_json(_inside(root, entry["config"])))
    if selected.model_id != model or settings.purpose != "benchmark":
        raise CLIError("Registry/spec/config model identity is inconsistent; fixture mode is not exposed by CLI")
    return entry, selected, settings


def _factory(entry, selected):
    # Resolve only when the runner calls this closure after its live preflight.
    def construct():
        module, name = entry["factory"].split(":")
        return getattr(importlib.import_module(module), name)(selected)
    return construct


def _saved_run(root, model, value):
    # Command-line artifact paths follow the caller's working directory;
    # configured catalog paths remain suite-relative.
    path = Path(value)
    directory = _inside(root, path if path.is_absolute() else Path.cwd()/path)
    if directory.parent != (root/"results"/model).resolve():
        raise CLIError("Select a run directly inside results/<selected-model>/")
    descriptor = _json(directory/"run_manifest.json")
    if descriptor["identity"]["spec"]["model_id"] != model or descriptor["identity"]["config"]["purpose"] != "benchmark":
        raise CLIError("Stored run does not belong to the selected benchmark model")
    return directory, descriptor


def dispatch(args, root):
    command = args.command
    if command == "models":
        return {"status": "OK", "models": model_rows(root), "message": "Each candidate needs its own approval; PENDING is not a zero score."}
    if command == "progress":
        state = load_status(root/"BENCHMARK_STATUS.json")
        return {"status": "OK", "checkpoint": state, "message": f"Last completed: {state['last_completed_checkpoint']}; current: {state['current_task']}"}
    if command in {"compare", "final-report"}:
        task = "TASK-018" if command == "compare" else "TASK-019"
        raise CLIError(f"PENDING {task}: saved-result comparison/reporting is not implemented yet. No inference was run.", 4, "PENDING")
    if command == "check-environment":
        found = dependencies(root)
        if not all(row["ready"] for row in found):
            return {"status": "ERROR", "exit_code": 1, "python": sys.executable, "dependencies": found,
                    "message": "Shared dependencies are missing/different. Use a compatible existing interpreter or reviewed isolated requirements. Nothing was installed."}
        from benchmark_suite.runners.preflight import snapshot, check, PreflightBlocked
        result = {"status": "OK", "python": sys.executable, "dependencies": dependencies(root), "hardware": snapshot(root),
                  "message": "Metadata/native checks only; passing shared checks does not approve or certify a model."}
        from benchmark_suite.scripts.check_hardware import conservative_loading_gate
        result["model_loading_gate"] = conservative_loading_gate(result["hardware"].get("ram_available_bytes"))
        if args.model:
            entry, reasons = _ready(root, args.model)
            if not reasons:
                _, selected, settings = _definition(root, args.model)
                try:
                    check(selected, settings, result["hardware"], root.parent)
                except PreflightBlocked as exc:
                    reasons.extend(exc.reasons)
            result["model"] = {"id": args.model, "ready": not reasons, "reasons": reasons}
            if reasons:
                result["status"] = "BLOCKED"
                result["exit_code"] = 3
        return result
    _require_dependencies(root)
    if command == "validate-datasets":
        from benchmark_suite.dataset_preparation import validate
        capture = StringIO()
        with redirect_stdout(capture):
            provenance = validate(root)
        return {"status": "OK", "message": capture.getvalue().strip(), "records": provenance["records"], "network": False}
    if command in {"evaluate", "report"}:
        directory, _ = _saved_run(root, args.model, args.run_dir)
        from benchmark_suite.runners.report import evaluate_run
        output = evaluate_run(root, directory)
        return {"status": "OK", "evaluation_directory": str(output), "report": str(output/"MODEL_REPORT.md"),
                "message": "Saved predictions evaluated; new metrics/report generated without model initialization or inference."}
    entry, selected, settings = _definition(root, args.model)
    if command == "setup":
        from benchmark_suite.runners.preflight import snapshot, check
        check(selected, settings, snapshot(root), root.parent)
        return {"status": "OK", "model": args.model, "message": "Existing isolated pinned setup passed preflight. No installation, download or model initialization performed."}
    resume = None
    if command == "resume":
        resume, descriptor = _saved_run(root, args.model, args.run_dir)
        if (resume/"completion.json").exists():
            raise CLIError("Run is completed and immutable; use evaluate/report or start a new run")
        from benchmark_suite.runners.schemas import RunConfig
        settings = RunConfig.model_validate(descriptor["identity"]["config"])
        splits = descriptor["dataset"]["splits"]
        if splits not in (["development"], ["evaluation"]):
            raise CLIError("Stored run has an invalid frozen split")
        split = splits[0]
    else:
        settings.language = args.language
        mode = "quick" if command == "smoke" else args.mode
        split = "development" if mode == "quick" else "evaluation"
    from benchmark_suite.runners.run import run
    directory = run(root, root/f"datasets/manifest/{split}.jsonl", selected, settings, _factory(entry, selected), resume=resume)
    # Running succeeds before evaluation. If evaluation fails, raw/normalized run
    # bundles remain completed; evaluate/report can be retried without inference.
    from benchmark_suite.runners.report import evaluate_run
    try:
        output = evaluate_run(root, directory)
    except Exception as exc:
        raise CLIError(f"Run saved at {directory}; evaluation stopped: {exc}. Retry evaluate/report on this run without inference.") from exc
    completion = _json(directory/"completion.json")
    failed = completion["failed"]
    return {"status": "COMPLETED_WITH_FAILURES" if failed else "OK", "exit_code": 1 if failed else 0,
            "failed_documents": failed, "model": args.model, "run_directory": str(directory), "evaluation_directory": str(output),
            "message": f"Selected model invocation finished ({failed} failed documents). Stop for review; no subsequent model was selected or approved."}


def _emit(result, machine):
    if machine:
        print(json.dumps(result, ensure_ascii=True, allow_nan=False))
    else:
        print(result.get("message", result["status"]))
        if "models" in result:
            for row in result["models"]:
                print(f"{row['model']}: {row['state']}; implementation {row['implementation']}; {row['task']}; {row['reason'] or 'no recorded blocker'}")
        if "checkpoint" in result:
            saved = result["checkpoint"]
            print(f"Approval required before: {saved['approval_required_before']}")
            print(saved["next_action"])
            for task, status in saved["tasks"].items():
                print(f"{task}: {status}")
        for key, value in result.items():
            if key not in {"message", "status", "command", "exit_code", "models", "checkpoint"}:
                print(f"{key}: {json.dumps(value, ensure_ascii=True, allow_nan=False, indent=2) if isinstance(value, (dict, list)) else value}")


def _log(root, result):
    directory = root/"logs/cli"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory/(datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")+"-"+uuid4().hex[:8]+".json")
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump({"time": datetime.now(timezone.utc).isoformat(), **result}, stream, ensure_ascii=True, allow_nan=False, indent=2)
        stream.write("\n")
    return path


def main(argv=None, *, root=None):
    args = parser().parse_args(argv)
    root = ROOT if root is None else Path(root).resolve()
    if args.command in {None, "menu"}:
        if getattr(args, "json", False):
            print("The interactive menu does not support --json", file=sys.stderr)
            return 2
        return menu(root)
    try:
        if sys.version_info < (3, 10):
            raise CLIError("Python 3.10 or newer is required")
        result = dict(dispatch(args, root), command=args.command)
        code = result.get("exit_code", 0)
    except KeyboardInterrupt:
        result = {"command": args.command, "status": "INTERRUPTED", "message": "Interrupted. Persisted run bundles remain resumable; no next model started."}
        code = 130
    except Exception as exc:
        blocked = isinstance(exc, getattr(sys.modules.get("benchmark_suite.runners.preflight"), "PreflightBlocked", ()))
        code = exc.code if isinstance(exc, CLIError) else 3 if blocked else 1
        result = {"command": args.command, "status": exc.status if isinstance(exc, CLIError) else "BLOCKED" if blocked else "ERROR",
                  "message": str(exc), "error_type": type(exc).__name__}
    try:
        result["log_file"] = str(_log(root, dict(result, exit_code=code)))
    except OSError as exc:
        result["log_error"] = type(exc).__name__
        if code == 0:
            code = 1
    _emit(result, args.json)
    return code


def _choose_model():
    for index, model in enumerate(MODEL_IDS, 1):
        print(f"{index}. {model}")
    value = input("Select one model (1-9, 0 cancels): ").strip()
    if value == "0":
        return None
    if value not in {str(i) for i in range(1, 10)}:
        raise ValueError("Select one number from 1 to 9")
    return MODEL_IDS[int(value)-1]


def menu(root):
    while True:
        print("\n========================================\n       OCR BENCHMARKING SUITE\n========================================")
        for number, label in enumerate(MENU, 1):
            print(f"{number}. {label}")
        print("========================================")
        try:
            choice = input("Select option (1-13): ").strip()
            if choice == "13":
                return 0
            commands = {"1": "check-environment", "2": "models", "3": "progress", "4": "setup", "5": "validate-datasets",
                        "6": "smoke", "7": "run", "8": "resume", "9": "evaluate", "10": "report", "11": "compare", "12": "final-report"}
            if choice not in commands:
                print("Select one number from 1 to 13.")
                continue
            command = commands[choice]
            argv = [command]
            if choice in {"4", "6", "7", "8", "9", "10"}:
                model = _choose_model()
                if model is None:
                    continue
                argv += ["--model", model]
            if choice in {"6", "7"}:
                language = input("Language (en/ar/both) [both]: ").strip() or "both"
                if language not in {"en", "ar", "both"}:
                    raise ValueError("Language must be en, ar or both")
                argv += ["--language", language]
            if choice == "7":
                mode = input("Mode (quick/full) [quick]: ").strip() or "quick"
                if mode not in {"quick", "full"}:
                    raise ValueError("Mode must be quick or full")
                argv += ["--mode", mode]
            if choice in {"8", "9", "10"}:
                path = input("Existing run directory (blank cancels): ").strip()
                if not path:
                    continue
                argv += ["--run-dir", path]
            main(argv, root=root)
        except ValueError as exc:
            print(str(exc))
        except (EOFError, KeyboardInterrupt):
            print("\nMenu closed. No additional model was started.")
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
