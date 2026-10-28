"""Validated, atomic checkpoint files for a single benchmark coordinator.

No OCR or third-party dependencies are imported. Updates must be serialized by
the caller. Atomic replacement protects readers from partial JSON; it is not a
multi-writer transaction or a claim of power-loss durability on every filesystem.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import date
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

TASK_IDS = tuple(f"TASK-{number:03}" for number in range(1, 22))
MODEL_IDS = (
    "surya", "paddle_vl", "marker", "paddle", "tesseract",
    "docling_easyocr", "docling_tesseract", "granite_docling", "baidu",
)
STATES = frozenset({"PENDING", "IN_PROGRESS", "BLOCKED", "COMPLETED", "FAILED", "SKIPPED"})
TRANSITIONS = {
    "PENDING": {"IN_PROGRESS", "BLOCKED", "SKIPPED"},
    "IN_PROGRESS": {"COMPLETED", "BLOCKED", "FAILED"},
    "BLOCKED": {"IN_PROGRESS", "SKIPPED"},
    "FAILED": {"IN_PROGRESS", "SKIPPED"},
    "COMPLETED": set(),
    "SKIPPED": set(),
}
REQUIRED_FIELDS = frozenset({
    "schema_version", "updated_date", "timezone", "branch", "audited_base_commit",
    "current_task", "tasks", "models", "model_block_reasons",
    "last_completed_checkpoint", "checkpoint_git_commit_subject",
    "approval_required_before", "approved_tasks", "next_action", "verification",
})


class StatusError(ValueError):
    """A malformed checkpoint or forbidden transition; never silently reset it."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise StatusError(message)


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_status(status: Any) -> dict[str, Any]:
    """Validate schema v1, returning a detached JSON-compatible checkpoint.

    Unknown fields are rejected to expose typos. The verification object is
    extensible, but must carry a status from the normal task-state vocabulary.
    """
    _require(isinstance(status, dict), "Status must be an object.")
    _require(set(status) == REQUIRED_FIELDS, "Missing or unknown status fields.")
    _require(type(status["schema_version"]) is int and status["schema_version"] == 1,
             "Unsupported schema_version; expected integer 1.")
    _require(isinstance(status["updated_date"], str), "updated_date must be an ISO date.")
    try:
        parsed = date.fromisoformat(status["updated_date"])
        _require(parsed.isoformat() == status["updated_date"], "Use YYYY-MM-DD dates.")
    except ValueError as exc:
        raise StatusError("updated_date must be a valid YYYY-MM-DD date.") from exc
    _require(_text(status["timezone"]), "timezone must be a nonempty IANA name.")
    try:
        ZoneInfo(status["timezone"])
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise StatusError("Unknown IANA timezone; Windows may need the tzdata package.") from exc
    for field in ("branch", "checkpoint_git_commit_subject", "next_action"):
        _require(_text(status[field]), f"{field} must be nonempty text.")
    _require(isinstance(status["audited_base_commit"], str) and
             bool(re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", status["audited_base_commit"])),
             "audited_base_commit must be a full Git commit hash.")
    for field, keys in (("tasks", TASK_IDS), ("models", MODEL_IDS)):
        values = status[field]
        _require(isinstance(values, dict) and set(values) == set(keys),
                 f"{field} must contain exactly the expected IDs.")
        _require(all(isinstance(v, str) and v in STATES for v in values.values()),
                 f"Invalid state in {field}.")
    _require(isinstance(status["current_task"], str) and status["current_task"] in TASK_IDS,
             "current_task must identify a known task.")
    approval = status["approval_required_before"]
    _require(approval is None or (isinstance(approval, str) and approval in TASK_IDS),
             "approval_required_before must be a task ID or null.")
    approved = status["approved_tasks"]
    _require(isinstance(approved, list) and all(isinstance(t, str) and t in TASK_IDS for t in approved),
             "approved_tasks must list known task IDs.")
    _require(len(approved) == len(set(approved)), "approved_tasks contains duplicates.")
    for task, state in status["tasks"].items():
        if state in {"IN_PROGRESS", "COMPLETED"}:
            _require(task in approved, f"{task} requires recorded user approval.")
    if approval is not None:
        _require(approval not in approved, "Approval gate contradicts recorded approval.")
    active = [t for t, v in status["tasks"].items() if v == "IN_PROGRESS"]
    _require(len(active) <= 1, "Only one task may be IN_PROGRESS.")
    _require(not active or active[0] == status["current_task"], "Active task must match current_task.")
    completed = [t for t in TASK_IDS if status["tasks"][t] == "COMPLETED"]
    _require(status["last_completed_checkpoint"] == (completed[-1] if completed else None),
             "last_completed_checkpoint must match the latest completed task ID.")
    reasons = status["model_block_reasons"]
    _require(isinstance(reasons, dict) and set(reasons) <= set(MODEL_IDS),
             "model_block_reasons must use known model IDs.")
    _require(all(_text(reason) and status["models"][model] == "BLOCKED"
                 for model, reason in reasons.items()), "Reasons must describe BLOCKED models.")
    _require(all(model in reasons for model, state in status["models"].items() if state == "BLOCKED"),
             "Every BLOCKED model needs a reason (e.g. BLOCKED_BY_HARDWARE).")
    active_models = [m for m, state in status["models"].items() if state == "IN_PROGRESS"]
    _require(len(active_models) <= 1, "Only one model may be IN_PROGRESS.")
    if any(state in {"IN_PROGRESS", "COMPLETED"} for state in status["models"].values()):
        _require(status["tasks"]["TASK-003"] == "COMPLETED",
                 "Model execution requires a completed hardware assessment task.")
    for number, model in enumerate(MODEL_IDS, start=9):
        state = status["models"][model]
        if state in {"IN_PROGRESS", "COMPLETED"}:
            _require(status["tasks"][f"TASK-{number:03}"] == state,
                     f"{model} must match its approved evaluation task state.")
    verification = status["verification"]
    _require(isinstance(verification, dict) and isinstance(verification.get("status"), str)
             and verification["status"] in STATES, "verification.status must use a task state.")
    try:
        # Ensure extensible verification metadata is finite JSON, not Python objects.
        json.dumps(status, ensure_ascii=False, allow_nan=False)
    except (ValueError, TypeError) as exc:
        raise StatusError("Checkpoint must contain finite JSON values.") from exc
    return deepcopy(status)


def validate_transition(previous: dict[str, Any], updated: dict[str, Any]) -> None:
    """Reject state regression and changes to completed checkpoint identity."""
    old, new = validate_status(previous), validate_status(updated)
    for field in ("schema_version", "branch", "audited_base_commit"):
        _require(old[field] == new[field], f"Cannot change checkpoint identity: {field}.")
    _require(set(old["approved_tasks"]) <= set(new["approved_tasks"]),
             "Cannot erase recorded approvals.")
    _require(new["updated_date"] >= old["updated_date"], "updated_date cannot move backwards.")
    for field in ("tasks", "models"):
        for key, state in old[field].items():
            target = new[field][key]
            _require(target == state or target in TRANSITIONS[state],
                     f"Forbidden {key} transition: {state} -> {target}.")


def load_status(path: str | Path) -> dict[str, Any]:
    """Read UTF-8 explicitly; corrupt or missing files are never reinitialized."""
    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            _require(key not in result, f"Duplicate JSON key: {key}.")
            result[key] = value
        return result

    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=unique_object)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise StatusError("Checkpoint is not valid UTF-8 JSON; preserve it for diagnosis.") from exc
    return validate_status(data)


def save_status(path: str | Path, status: dict[str, Any]) -> None:
    """Validate before writing, then flush/fsync and atomically replace.

    Destination parent must already exist. For an existing file, transitions
    are checked against its validated contents before creating a temporary file.
    Catchable failures remove this writer's temp file and preserve the old JSON.
    A process kill may leave an orphan .tmp, which readers ignore. After a replace
    succeeds the complete new checkpoint is authoritative.
    """
    destination = Path(path)
    updated = validate_status(status)
    if destination.exists():
        validate_transition(load_status(destination), updated)
    payload = json.dumps(updated, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="\n", dir=destination.parent,
            prefix=f".{destination.name}.", suffix=".tmp", delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main() -> int:
    """Read-only checkpoint validation from the repository root."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--status", type=Path,
                        default=Path(__file__).with_name("BENCHMARK_STATUS.json"))
    args = parser.parse_args()
    try:
        status = load_status(args.status)
    except (StatusError, OSError) as exc:
        parser.exit(1, f"Checkpoint validation failed: {exc}\n")
    print(f"Valid checkpoint: {status['last_completed_checkpoint']}; "
          f"current task: {status['current_task']}; next: {status['next_action']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
