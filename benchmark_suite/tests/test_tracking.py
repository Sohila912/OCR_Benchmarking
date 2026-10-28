"""Recovery and policy tests; no models, services or downloaded data needed."""

from copy import deepcopy
from pathlib import Path
import subprocess
import sys

import pytest

from benchmark_suite import tracking


@pytest.fixture
def initial():
    """Independent pre-TASK-002 checkpoint; never depend on live progress."""
    return {
        "schema_version": 1, "updated_date": "2026-10-28", "timezone": "Africa/Cairo",
        "branch": "feature/ocr-comprehensive-benchmark", "audited_base_commit": "a" * 40,
        "current_task": "TASK-002",
        "tasks": {t: "COMPLETED" if t == "TASK-001" else "PENDING" for t in tracking.TASK_IDS},
        "models": {m: "PENDING" for m in tracking.MODEL_IDS}, "model_block_reasons": {},
        "last_completed_checkpoint": "TASK-001", "checkpoint_git_commit_subject": "initial checkpoint",
        "approval_required_before": "TASK-002", "approved_tasks": ["TASK-001"],
        "next_action": "Wait for approval", "verification": {"status": "COMPLETED"},
    }


def start(status):
    updated = deepcopy(status)
    updated["approved_tasks"].append("TASK-002")
    updated["approval_required_before"] = None
    updated["tasks"]["TASK-002"] = "IN_PROGRESS"
    updated["next_action"] = "Create architecture; Arabic label: \u0627\u062e\u062a\u0628\u0627\u0631"
    return updated


def test_roundtrip_and_terminal_checkpoint(tmp_path, initial):
    path = tmp_path / "status.json"
    tracking.save_status(path, initial)
    running = start(initial)
    tracking.save_status(path, running)
    assert tracking.load_status(path) == running
    assert "\u0627\u062e\u062a\u0628\u0627\u0631" in path.read_text(encoding="utf-8")
    completed = deepcopy(running)
    completed["tasks"]["TASK-002"] = "COMPLETED"
    completed["last_completed_checkpoint"] = "TASK-002"
    completed["current_task"] = "TASK-003"
    tracking.save_status(path, completed)
    before = path.read_bytes()
    regression = deepcopy(completed)
    regression["tasks"]["TASK-002"] = "PENDING"
    regression["last_completed_checkpoint"] = "TASK-001"
    with pytest.raises(tracking.StatusError, match="Forbidden"):
        tracking.save_status(path, regression)
    assert path.read_bytes() == before
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize("field,value", [
    ("schema_version", True), ("schema_version", 2), ("updated_date", "2026-02-30"),
    ("timezone", "Unknown/Nowhere"), ("branch", ""), ("audited_base_commit", "short"),
    ("current_task", "TASK-099"), ("approval_required_before", []),
    ("approved_tasks", ["TASK-001", "TASK-001"]), ("approved_tasks", []),
    ("last_completed_checkpoint", None), ("verification", {"status": "PASSED"}),
    ("verification", {"status": "COMPLETED", "value": float("nan")}),
    ("next_action", ""), ("model_block_reasons", {"surya": "BLOCKED_BY_HARDWARE"}),
])
def test_reject_invalid_schema_before_touching_file(tmp_path, initial, field, value):
    path = tmp_path / "status.json"
    tracking.save_status(path, initial)
    before = path.read_bytes()
    updated = deepcopy(initial)
    updated[field] = value
    with pytest.raises(tracking.StatusError):
        tracking.save_status(path, updated)
    assert path.read_bytes() == before
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize("mutation", ["unknown_field", "missing_task", "unknown_model", "bad_state"])
def test_schema_keys_and_states(initial, mutation):
    if mutation == "unknown_field":
        initial["current_taks"] = "TASK-002"
    elif mutation == "missing_task":
        del initial["tasks"]["TASK-021"]
    elif mutation == "unknown_model":
        initial["models"]["qwen"] = "PENDING"
    else:
        initial["models"]["surya"] = "BLOCKED_BY_HARDWARE"
    with pytest.raises(tracking.StatusError):
        tracking.validate_status(initial)


def test_requires_approval_and_hardware_assessment(initial):
    initial["tasks"]["TASK-002"] = "IN_PROGRESS"
    with pytest.raises(tracking.StatusError, match="approval"):
        tracking.validate_status(initial)
    running = start({**initial, "tasks": {**initial["tasks"], "TASK-002": "PENDING"}})
    running["models"]["surya"] = "IN_PROGRESS"
    with pytest.raises(tracking.StatusError, match="hardware"):
        tracking.validate_status(running)


def test_model_requires_approved_evaluation_task(initial):
    ready = deepcopy(initial)
    for task in ("TASK-002", "TASK-003"):
        ready["tasks"][task] = "COMPLETED"
        ready["approved_tasks"].append(task)
    ready["last_completed_checkpoint"] = "TASK-003"
    ready["approval_required_before"] = None
    ready["current_task"] = "TASK-009"
    ready["models"]["surya"] = "IN_PROGRESS"
    with pytest.raises(tracking.StatusError, match="evaluation task"):
        tracking.validate_status(ready)
    ready["tasks"]["TASK-009"] = "IN_PROGRESS"
    ready["approved_tasks"].append("TASK-009")
    tracking.validate_status(ready)


def test_blocked_model_reason_and_retry(initial):
    blocked = deepcopy(initial)
    blocked["models"]["surya"] = "BLOCKED"
    with pytest.raises(tracking.StatusError, match="reason"):
        tracking.validate_status(blocked)
    blocked["model_block_reasons"]["surya"] = "BLOCKED_BY_HARDWARE"
    tracking.validate_transition(initial, blocked)
    blocked["models"]["surya"] = "FAILED"
    blocked["model_block_reasons"] = {}
    with pytest.raises(tracking.StatusError, match="Forbidden"):
        tracking.validate_transition(initial, blocked)


@pytest.mark.parametrize("state", ["BLOCKED", "FAILED"])
def test_task_retry_requires_in_progress(initial, state):
    running = start(initial)
    stopped = deepcopy(running)
    stopped["tasks"]["TASK-002"] = state
    tracking.validate_transition(running, stopped)
    tracking.validate_transition(stopped, running)
    completed = deepcopy(stopped)
    completed["tasks"]["TASK-002"] = "COMPLETED"
    completed["last_completed_checkpoint"] = "TASK-002"
    with pytest.raises(tracking.StatusError, match="Forbidden"):
        tracking.validate_transition(stopped, completed)


def test_cannot_skip_execution_phase_or_erase_identity(initial):
    completed = start(initial)
    completed["tasks"]["TASK-002"] = "COMPLETED"
    completed["last_completed_checkpoint"] = "TASK-002"
    with pytest.raises(tracking.StatusError, match="Forbidden"):
        tracking.validate_transition(initial, completed)
    renamed = deepcopy(initial)
    renamed["branch"] = "other"
    with pytest.raises(tracking.StatusError, match="identity"):
        tracking.validate_transition(initial, renamed)
    running = start(initial)
    removed = deepcopy(running)
    removed["tasks"]["TASK-002"] = "BLOCKED"
    removed["approved_tasks"].remove("TASK-002")
    with pytest.raises(tracking.StatusError, match="erase"):
        tracking.validate_transition(running, removed)


@pytest.mark.parametrize("failure_point", ["fsync", "replace"])
def test_interrupted_write_preserves_old_checkpoint(tmp_path, initial, monkeypatch, failure_point):
    path = tmp_path / "status.json"
    tracking.save_status(path, initial)
    before = path.read_bytes()

    def fail(*args):
        if failure_point == "replace":
            source, destination = map(Path, args)
            assert source.parent == destination.parent == tmp_path
            assert tracking.load_status(source) == start(initial)
            assert path.read_bytes() == before
        raise OSError("simulated interrupted I/O")

    monkeypatch.setattr(tracking.os, failure_point, fail)
    with pytest.raises(OSError, match="interrupted"):
        tracking.save_status(path, start(initial))
    assert path.read_bytes() == before
    assert tracking.load_status(path) == initial
    assert list(tmp_path.iterdir()) == [path]


def test_process_kill_before_replace_keeps_old_checkpoint(tmp_path, initial):
    path = tmp_path / "status.json"
    tracking.save_status(path, initial)
    script = """
import os, sys
from benchmark_suite import tracking
path = sys.argv[1]
status = tracking.load_status(path)
status['next_action'] = 'interrupted update'
tracking.os.replace = lambda *args: os._exit(73)
tracking.save_status(path, status)
"""
    result = subprocess.run([sys.executable, "-c", script, str(path)], check=False)
    assert result.returncode == 73
    assert tracking.load_status(path) == initial
    leftovers = list(tmp_path.glob(".status.json.*.tmp"))
    assert len(leftovers) == 1
    assert tracking.load_status(leftovers[0])["next_action"] == "interrupted update"
    # An orphan belongs to the dead writer; later saves must not consume/delete it.
    tracking.save_status(path, start(initial))
    assert leftovers[0].exists()


@pytest.mark.parametrize("content", [b'{"tasks":', b'\xff', b'{"schema_version":1,"schema_version":2}'])
def test_corrupt_status_is_not_overwritten(tmp_path, initial, content):
    path = tmp_path / "status.json"
    path.write_bytes(content)
    with pytest.raises(tracking.StatusError):
        tracking.save_status(path, initial)
    assert path.read_bytes() == content


def test_load_missing_and_missing_parent_do_not_create_files(tmp_path, initial):
    path = tmp_path / "absent" / "status.json"
    with pytest.raises(FileNotFoundError):
        tracking.load_status(path)
    with pytest.raises(FileNotFoundError):
        tracking.save_status(path, initial)
    assert not path.parent.exists()


def test_validate_returns_detached_copy(initial):
    validated = tracking.validate_status(initial)
    validated["models"]["surya"] = "SKIPPED"
    assert initial["models"]["surya"] == "PENDING"


def test_multiple_active_tasks_are_rejected(initial):
    running = start(initial)
    running["tasks"]["TASK-003"] = "IN_PROGRESS"
    running["approved_tasks"].append("TASK-003")
    with pytest.raises(tracking.StatusError, match="Only one task"):
        tracking.validate_status(running)


def test_date_regression_is_rejected(initial):
    older = deepcopy(initial)
    older["updated_date"] = "2026-10-27"
    with pytest.raises(tracking.StatusError, match="backwards"):
        tracking.validate_transition(initial, older)


def test_validator_cli_is_read_only(tmp_path, initial):
    path = tmp_path / "status.json"
    tracking.save_status(path, initial)
    before = path.read_bytes()
    result = subprocess.run([sys.executable, "-m", "benchmark_suite.tracking", "--status", str(path)],
                            capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    assert "TASK-001" in result.stdout
    assert path.read_bytes() == before
    path.write_text("{}", encoding="utf-8")
    result = subprocess.run([sys.executable, "-m", "benchmark_suite.tracking", "--status", str(path)],
                            capture_output=True, text=True, check=False)
    assert result.returncode == 1
    assert "validation failed" in result.stderr


def test_tracker_import_does_not_load_ocr():
    result = subprocess.run([
        sys.executable, "-c",
        "import sys; import benchmark_suite.tracking; "
        "assert not any(n == 'OCR' or n.startswith(('OCR.', 'torch', 'paddle', 'docling', 'surya')) "
        "for n in sys.modules)",
    ], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("path,ignored", [
    ("benchmark_suite/datasets/english/example.pdf", True),
    ("benchmark_suite/datasets/arabic/reference.txt", True),
    ("benchmark_suite/downloads/dataset.zip", True),
    ("benchmark_suite/results/surya/run/predictions.jsonl", True),
    ("benchmark_suite/models/model.bin", True),
    ("benchmark_suite/weights/model.safetensors", True),
    ("benchmark_suite/environments/ocr/python.exe", True),
    ("benchmark_suite/.venv-surya/pyvenv.cfg", True),
    ("benchmark_suite/.env.private", True),
    ("benchmark_suite/configs/credentials.json", True),
    ("benchmark_suite/.BENCHMARK_STATUS.json.random.tmp", True),
    ("benchmark_suite/datasets/manifest/evaluation.jsonl", False),
    ("benchmark_suite/datasets/DATASET_SELECTION.md", False),
    ("benchmark_suite/configs/surya.json", False),
    ("benchmark_suite/configs/.env.example", False),
    ("benchmark_suite/reports/HARDWARE_PROFILE.md", False),
])
def test_git_artifact_policy(path, ignored):
    result = subprocess.run(["git", "check-ignore", "--no-index", "--quiet", path], check=False)
    assert result.returncode in {0, 1}
    assert (result.returncode == 0) == ignored
