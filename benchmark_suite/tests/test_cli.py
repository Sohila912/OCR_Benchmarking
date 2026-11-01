"""CLI/menu tests use fakes or blocked candidates, never real model execution."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from benchmark_suite import cli
from benchmark_suite.runners import preflight
from benchmark_suite.runners import run as runner
from benchmark_suite.runners import report as reporter
from benchmark_suite.runners.schemas import AdapterSpec, Capabilities, Requirements, RunConfig
from benchmark_suite.tracking import MODEL_IDS

SUITE = Path(__file__).resolve().parents[1]


@pytest.fixture
def root(tmp_path):
    value = tmp_path/"suite"
    (value/"configs").mkdir(parents=True)
    for name in ("BENCHMARK_STATUS.json", "requirements-runner.txt", "requirements-metrics.txt"):
        shutil.copyfile(SUITE/name, value/name)
    # A fixed pre-model checkpoint keeps approval tests independent of future
    # real user approvals. This edits only the temporary fixture, never the suite.
    status_path = value/"BENCHMARK_STATUS.json"
    state = json.loads(status_path.read_bytes())
    state["tasks"] = {task: "COMPLETED" if int(task[5:]) <= 8 else "PENDING" for task in state["tasks"]}
    state["approved_tasks"] = list(state["tasks"])[:8]
    state.update(current_task="TASK-009", last_completed_checkpoint="TASK-008", approval_required_before="TASK-009")
    state["models"] = {model: "BLOCKED" for model in MODEL_IDS}
    state["model_block_reasons"] = {model: "FIXTURE_REQUIRES_MODEL_APPROVAL" for model in MODEL_IDS}
    status_path.write_text(json.dumps(state), encoding="utf-8")
    shutil.copyfile(SUITE/"configs/models.json", value/"configs/models.json")
    return value


def response(capsys):
    return json.loads(capsys.readouterr().out)


def test_help_works_without_site_packages_or_model_imports():
    reply = subprocess.run([sys.executable, "-S", "-m", "benchmark_suite.cli", "--help"], capture_output=True, text=True, check=False)
    assert reply.returncode == 0
    assert "single-model" in reply.stdout
    assert "ModuleNotFound" not in reply.stderr


def test_model_listing_preserves_status_and_exposes_all_pending(root, capsys):
    before = (root/"BENCHMARK_STATUS.json").read_bytes()
    assert cli.main(["models", "--json"], root=root) == 0
    result = response(capsys)
    assert {row["model"] for row in result["models"]} == set(MODEL_IDS)
    assert all(row["implementation"] == "PENDING" and not row["approved"] for row in result["models"])
    assert (root/"BENCHMARK_STATUS.json").read_bytes() == before
    assert Path(result["log_file"]).is_file()


def test_progress_is_read_only(root, capsys):
    before = (root/"BENCHMARK_STATUS.json").read_bytes()
    assert cli.main(["progress", "--json"], root=root) == 0
    assert "checkpoint" in response(capsys)
    assert (root/"BENCHMARK_STATUS.json").read_bytes() == before


@pytest.mark.parametrize("model", MODEL_IDS)
def test_no_candidate_can_run_or_install_without_its_own_task(root, capsys, monkeypatch, model):
    monkeypatch.setattr(runner, "run", lambda *a, **k: pytest.fail("Runner must not be called"))
    monkeypatch.setattr(cli.importlib, "import_module", lambda *a: pytest.fail("No factory may be imported"))
    before = (root/"BENCHMARK_STATUS.json").read_bytes()
    for command in ("setup", "smoke", "run"):
        assert cli.main([command, "--model", model, "--json"], root=root) == 3
        result = response(capsys)
        assert result["status"] == "BLOCKED"
        assert "PENDING" in result["message"] and "approval" in result["message"]
    assert (root/"BENCHMARK_STATUS.json").read_bytes() == before


@pytest.mark.parametrize("argv", [
    ["run", "--model", "all"], ["run", "--model", "surya", "marker"],
    ["run", "--model", "surya", "--model", "marker"], ["setup"],
    ["run", "--model", "surya", "--language", "mixed"],
    ["resume", "--model", "surya", "--run-dir", "x", "--language", "ar"],
    ["run", "--model", "surya", "--fixture"], ["run", "--model", "surya", "--yes"],
])
def test_ambiguous_or_unsupported_invocations_are_rejected(root, argv):
    with pytest.raises(SystemExit) as failure:
        cli.main(argv, root=root)
    assert failure.value.code == 2
    assert not (root/"logs").exists()


@pytest.mark.parametrize("command,task", [("compare", "TASK-018"), ("final-report", "TASK-019")])
def test_comparison_commands_are_explicit_pending(root, capsys, command, task):
    assert cli.main([command, "--json"], root=root) == 4
    result = response(capsys)
    assert result["status"] == "PENDING" and task in result["message"]
    assert not (root/"results").exists()


def test_missing_dependencies_produce_readable_error_without_heavy_import(root, capsys, monkeypatch):
    missing = [{"package": "psutil", "expected": "7.2.2", "installed": None, "ready": False}]
    monkeypatch.setattr(cli, "dependencies", lambda root: missing)
    monkeypatch.setattr(preflight, "snapshot", lambda *a: pytest.fail("No live probe with missing dependencies"))
    assert cli.main(["check-environment", "--json"], root=root) == 1
    assert response(capsys)["dependencies"] == missing
    assert cli.main(["run", "--model", "surya", "--json"], root=root) == 1
    assert "Nothing was installed" in response(capsys)["message"]


def test_environment_check_is_metadata_only(root, capsys, monkeypatch):
    monkeypatch.setattr(preflight, "snapshot", lambda root: {"frameworks_imported": False, "ram_available_bytes": 100})
    assert cli.main(["check-environment", "--json"], root=root) == 0
    assert response(capsys)["hardware"]["frameworks_imported"] is False
    assert cli.main(["check-environment", "--model", "surya", "--json"], root=root) == 3
    result = response(capsys)
    assert result["model"]["ready"] is False
    assert result["model"]["reasons"]


def ready_definition(root):
    """Simulated future registration; the factory/runner boundary stays fake."""
    catalog = json.loads((root/"configs/models.json").read_bytes())
    entry = catalog["models"]["surya"]
    entry.update(spec="configs/test-spec.json", config="configs/test-run.json", factory="benchmark_suite.adapters.unit_fake:create_adapter")
    (root/"configs/models.json").write_text(json.dumps(catalog))
    spec = AdapterSpec(model_id="surya", model_revision="synthetic-test", adapter_revision="synthetic-test",
                       raw_level="synthetic-test", capabilities=Capabilities(text=True),
                       requirements=Requirements(compatibility="COMPATIBLE", evidence="Unit test", ram_bytes=1, disk_bytes=0))
    settings = RunConfig(device="cpu", precision="unit-test", preprocessing={"resize": "none"})
    (root/entry["spec"]).write_text(spec.model_dump_json())
    (root/entry["config"]).write_text(settings.model_dump_json())
    return entry, spec, settings


def simulate_authorized(monkeypatch):
    observed = []
    monkeypatch.setattr(preflight, "authorize_model", lambda model, path: observed.append(model))
    monkeypatch.setattr(cli, "_environment_reasons", lambda *args: [])
    original = cli.load_status
    def state(path):
        data = original(path)
        data["models"]["surya"] = "IN_PROGRESS"
        return data
    monkeypatch.setattr(cli, "load_status", state)
    return observed


@pytest.mark.parametrize("command,language,mode,split", [
    ("smoke", "en", None, "development"), ("run", "ar", "quick", "development"),
    ("run", "both", "full", "evaluation"),
])
def test_run_routes_one_model_and_frozen_split_through_shared_runner(root, capsys, monkeypatch, command, language, mode, split):
    ready_definition(root)
    approvals = simulate_authorized(monkeypatch)
    seen = []
    def fake_run(suite, manifest, selected, settings, factory, **kwargs):
        assert selected.model_id == "surya" and settings.language == language
        assert manifest.name == split+".jsonl"
        assert kwargs["resume"] is None
        # Dynamic import is deferred to the shared runner after its preflight.
        seen.append(factory)
        directory = root/"results/surya/unit-fake"
        directory.mkdir(parents=True)
        (directory/"completion.json").write_text('{"failed": 0}')
        return directory
    monkeypatch.setattr(runner, "run", fake_run)
    monkeypatch.setattr(reporter, "evaluate_run", lambda suite, directory: root/"results/surya/evaluations/unit-fake")
    monkeypatch.setattr(cli.importlib, "import_module", lambda *args: pytest.fail("CLI must not import factory before shared preflight"))
    argv = [command, "--model", "surya", "--language", language, "--json"]
    if mode: argv += ["--mode", mode]
    assert cli.main(argv, root=root) == 0
    assert response(capsys)["model"] == "surya"
    assert approvals == ["surya"] and len(seen) == 1


def stored_run(root, *, complete=False):
    _, selected, settings = ready_definition(root)
    settings.language = "ar"
    settings.dpi = 321
    directory = root/"results/surya/unit-fake"
    directory.mkdir(parents=True)
    descriptor = {"identity": {"spec": selected.model_dump(), "config": settings.model_dump()}, "dataset": {"splits": ["development"]}}
    (directory/"run_manifest.json").write_text(json.dumps(descriptor))
    if complete: (directory/"completion.json").write_text('{}')
    return directory, settings


def test_resume_uses_original_language_precision_and_split(root, capsys, monkeypatch):
    directory, original = stored_run(root)
    simulate_authorized(monkeypatch)
    def fake_run(suite, manifest, selected, settings, factory, **kwargs):
        assert settings == original
        assert manifest.name == "development.jsonl" and kwargs["resume"] == directory
        (directory/"completion.json").write_text('{"failed": 0}')
        return directory
    monkeypatch.setattr(runner, "run", fake_run)
    monkeypatch.setattr(reporter, "evaluate_run", lambda *args: directory/"evaluation-fake")
    assert cli.main(["resume", "--model", "surya", "--run-dir", str(directory), "--json"], root=root) == 0
    assert "finished" in response(capsys)["message"]


def test_completed_run_cannot_resume(root, capsys, monkeypatch):
    directory, _ = stored_run(root, complete=True)
    simulate_authorized(monkeypatch)
    monkeypatch.setattr(runner, "run", lambda *a, **k: pytest.fail("Completed runs are immutable"))
    assert cli.main(["resume", "--model", "surya", "--run-dir", str(directory), "--json"], root=root) == 1
    assert "immutable" in response(capsys)["message"]


@pytest.mark.parametrize("command", ["evaluate", "report"])
def test_offline_commands_do_not_require_active_model_or_factory(root, capsys, monkeypatch, command):
    directory, _ = stored_run(root, complete=True)
    monkeypatch.setattr(cli, "_definition", lambda *a: pytest.fail("Offline work must not resolve model setup"))
    monkeypatch.setattr(runner, "run", lambda *a, **k: pytest.fail("No inference"))
    monkeypatch.setattr(reporter, "evaluate_run", lambda *a: root/"results/surya/evaluations/unit-fake")
    assert cli.main([command, "--model", "surya", "--run-dir", str(directory), "--json"], root=root) == 0
    assert "without model initialization" in response(capsys)["message"]


def test_wrong_model_and_external_paths_are_rejected(root, capsys, monkeypatch):
    directory, _ = stored_run(root, complete=True)
    monkeypatch.setattr(reporter, "evaluate_run", lambda *a: pytest.fail("Invalid path must not be evaluated"))
    for model, path in (("marker", directory), ("surya", root.parent/"other-run")):
        assert cli.main(["evaluate", "--model", model, "--run-dir", str(path), "--json"], root=root) == 1
        response(capsys)


def test_relative_run_paths_follow_working_directory(root, monkeypatch):
    directory, _ = stored_run(root, complete=True)
    monkeypatch.chdir(root.parent)
    found, _ = cli._saved_run(root, "surya", directory.relative_to(root.parent))
    assert found == directory


def test_setup_only_checks_existing_environment_and_preflight(root, capsys, monkeypatch):
    ready_definition(root); simulate_authorized(monkeypatch)
    monkeypatch.setattr(preflight, "snapshot", lambda *a: {})
    checked = []
    monkeypatch.setattr(preflight, "check", lambda *a: checked.append(a))
    monkeypatch.setattr(cli.importlib, "import_module", lambda *a: pytest.fail("Setup must not initialize"))
    assert cli.main(["setup", "--model", "surya", "--json"], root=root) == 0
    assert len(checked) == 1
    assert "No installation" in response(capsys)["message"]


def test_failed_documents_return_nonzero_and_evaluation_errors_name_saved_run(root, capsys, monkeypatch):
    directory, _ = stored_run(root, complete=True)
    (directory/"completion.json").write_text('{"failed": 1}')
    simulate_authorized(monkeypatch)
    monkeypatch.setattr(runner, "run", lambda *a, **k: directory)
    monkeypatch.setattr(reporter, "evaluate_run", lambda *a: root/"results/surya/evaluations/unit-fake")
    argv = ["run", "--model", "surya", "--json"]
    assert cli.main(argv, root=root) == 1
    assert response(capsys)["status"] == "COMPLETED_WITH_FAILURES"
    def broken(*args): raise ValueError("fixture evaluation error")
    monkeypatch.setattr(reporter, "evaluate_run", broken)
    assert cli.main(argv, root=root) == 1
    result = response(capsys)
    assert str(directory) in result["message"]
    assert "without inference" in result["message"]


def test_model_environment_must_be_isolated_and_explicitly_selected(root):
    entry = cli.catalog(root)["surya"]
    assert "not registered" in cli._environment_reasons(root, "surya", entry)[0]
    (root/"model-pins.txt").write_text("psutil==7.2.2\n")
    entry.update(python="missing/python.exe", requirements="model-pins.txt")
    reasons = cli._environment_reasons(root, "surya", entry)
    assert any("isolated" in r for r in reasons)
    assert any("will not switch" in r for r in reasons)


def test_requirements_reject_options_cycles_and_conflicts(tmp_path):
    one, two = tmp_path/"one.txt", tmp_path/"two.txt"
    one.write_text("--extra-index-url https://example.com\n")
    with pytest.raises(cli.CLIError): cli.dependency_pins(one)
    one.write_text("-r two.txt\n"); two.write_text("-r one.txt\n")
    with pytest.raises(cli.CLIError, match="Cyclic"): cli.dependency_pins(one)
    one.write_text("psutil==1\n-r two.txt\n"); two.write_text("psutil==2\n")
    with pytest.raises(cli.CLIError, match="Conflicting"): cli.dependency_pins(one)


def test_dataset_validation_uses_offline_validator_and_json_is_clean(root, capsys, monkeypatch):
    from benchmark_suite import dataset_preparation
    def validate(suite):
        assert suite == root
        print("Validated fixture metadata only")
        return {"records": 2}
    monkeypatch.setattr(dataset_preparation, "validate", validate)
    assert cli.main(["validate-datasets", "--json"], root=root) == 0
    result = response(capsys)
    assert result["network"] is False and result["records"] == 2


def test_menu_has_exact_options_and_calls_same_cli(root, monkeypatch, capsys):
    inputs = iter(["invalid", "2", "13"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    assert cli.menu(root) == 0
    output = capsys.readouterr().out
    for index, label in enumerate(cli.MENU, 1):
        assert f"{index}. {label}" in output
    assert "surya: BLOCKED" in output


def test_menu_selected_model_and_language_then_returns_to_menu(root, monkeypatch):
    inputs = iter(["7", "2", "ar", "quick", "13"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    seen = []
    monkeypatch.setattr(cli, "main", lambda argv, **kw: seen.append(argv) or 3)
    assert cli.menu(root) == 0
    assert seen == [["run", "--model", "paddle_vl", "--language", "ar", "--mode", "quick"]]


def test_menu_cancel_and_eof_never_start_model(root, monkeypatch):
    values = iter(["6", "0"])
    def read(prompt):
        try: return next(values)
        except StopIteration: raise EOFError
    monkeypatch.setattr("builtins.input", read)
    monkeypatch.setattr(cli, "main", lambda *a, **k: pytest.fail("Cancel must not execute"))
    assert cli.menu(root) == 0


@pytest.mark.skipif(os.name != "nt", reason="Real cmd.exe launcher test is Windows-only")
@pytest.mark.parametrize("exit_code", [0, 7])
def test_batch_launcher_from_spaces_and_ampersand_paths(tmp_path, exit_code):
    repo = tmp_path/"Folder With Spaces & Ampersand"
    script = repo/"benchmark_suite/scripts/run_benchmark.bat"
    script.parent.mkdir(parents=True)
    shutil.copyfile(SUITE/"scripts/run_benchmark.bat", script)
    (script.parent.parent/"__init__.py").write_text("")
    (script.parent.parent/"cli.py").write_text("import json,os,sys\nprint(json.dumps({'cwd':os.getcwd(),'argv':sys.argv[1:]}))\nsys.exit(int(os.environ['FIXTURE_EXIT']))\n")
    env = dict(os.environ, OCR_BENCHMARK_PYTHON=sys.executable, FIXTURE_EXIT=str(exit_code))
    reply = subprocess.run(f'cmd.exe /d /s /c ""{script}" progress --json"', cwd=tmp_path, env=env,
                           capture_output=True, text=True, check=False, timeout=15)
    assert reply.returncode == exit_code, reply.stdout+reply.stderr
    output = json.loads(reply.stdout)
    assert Path(output["cwd"]) == repo
    assert output["argv"] == ["progress", "--json"]
