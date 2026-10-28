"""Hardware collector tests: fail closed, avoid model imports and preserve evidence."""

import json
from pathlib import Path
import subprocess
import sys

import pytest

from benchmark_suite.scripts import check_hardware as hw


@pytest.mark.parametrize("value,expected", [
    (None, "UNKNOWN"), (0, "BLOCKED_BY_HARDWARE"),
    (int(0.6 * hw.GIB), "BLOCKED_BY_HARDWARE"),
    (2 * hw.GIB, "REQUIRES_MODEL_PREFLIGHT"), (32 * hw.GIB, "REQUIRES_MODEL_PREFLIGHT"),
])
def test_memory_gate_never_certifies_model_compatibility(value, expected):
    assert hw.conservative_loading_gate(value)["status"] == expected


@pytest.mark.parametrize("encoding", ["utf-8", "utf-16-le", "utf-16"])
def test_wsl_redirect_encoding(encoding):
    text = "Ubuntu    Stopped    2\r\n"
    assert hw.decode_output(text.encode(encoding)) == text.strip()


def test_nvidia_dedicated_vram_is_not_wmi_or_driver_cuda():
    parsed = hw.parse_nvidia_csv("NVIDIA GeForce MX350, 2048, 1965, 582.67, 6.1\n")
    assert parsed == [{"name": "NVIDIA GeForce MX350", "vram_total_mib": 2048.0,
                       "vram_free_mib": 1965.0, "driver_version": "582.67", "compute_capability": "6.1"}]
    with pytest.raises(ValueError):
        hw.parse_nvidia_csv("GPU, N/A, 2048, driver, 6.1")
    with pytest.raises(ValueError):
        hw.parse_nvidia_csv("unexpected output")


@pytest.mark.parametrize("error,status", [
    (FileNotFoundError(), "NOT_FOUND"),
    (subprocess.TimeoutExpired("probe", 15), "TIMEOUT"), (PermissionError(), "ERROR"),
])
def test_native_probe_failure_is_explicit(monkeypatch, error, status):
    def fail(*args, **kwargs):
        raise error
    monkeypatch.setattr(hw.subprocess, "run", fail)
    assert hw.run_probe(["missing"])["status"] == status


def test_collection_uses_metadata_and_status_only(monkeypatch):
    commands = []
    monkeypatch.setattr(hw.platform, "system", lambda: "Windows")
    monkeypatch.setattr(hw.shutil, "which", lambda command: None)
    monkeypatch.setattr(hw.shutil, "disk_usage", lambda drive: type("Disk", (), {"total": 100*hw.GIB, "free": 25*hw.GIB})())
    def probe(command, timeout=15):
        commands.append(command)
        if command[0] == "powershell.exe":
            return {"status": "OK", "stdout": json.dumps({"cpu": [], "gpus": [], "memory": {
                "total_bytes": 8*hw.GIB, "available_bytes": int(.5*hw.GIB)}})}
        if "-c" in command:
            assert command[-1] == hw.PACKAGE_PROBE
            return {"status": "OK", "stdout": '{"torch":{"version":"test+cpu","cuda":null}}'}
        return {"status": "ERROR", "stdout": "", "stderr": "unavailable"}
    monkeypatch.setattr(hw, "run_probe", probe)
    profile = hw.collect_hardware("python-test", "tesseract-test")
    assert not profile["frameworks_imported"]
    assert profile["loading_gate"]["status"] == "BLOCKED_BY_HARDWARE"
    assert profile["packages"]["torch"]["cuda"] is None
    assert all(command[:2] != ["wsl", "--exec"] for command in commands)
    assert "| RAM total / available | 8.00 GiB / 0.50 GiB |" in hw.render_profile(profile)


def test_failed_inventory_remains_unknown(monkeypatch):
    monkeypatch.setattr(hw.platform, "system", lambda: "Windows")
    monkeypatch.setattr(hw.shutil, "which", lambda command: None)
    monkeypatch.setattr(hw, "run_probe", lambda *args, **kwargs: {"status": "ERROR", "stdout": "", "stderr": "failed"})
    profile = hw.collect_hardware(tesseract="fake")
    assert profile["loading_gate"]["status"] == "UNKNOWN"
    assert profile["nvidia_devices"] == []
    assert "UNKNOWN / UNKNOWN" in hw.render_profile(profile)


def test_exclusive_report_output(tmp_path, monkeypatch):
    sentinel = tmp_path / "HARDWARE_PROFILE.json"
    sentinel.write_bytes(b"existing evidence")
    monkeypatch.setattr(sys, "argv", ["check_hardware", "--output", str(tmp_path)])
    monkeypatch.setattr(hw, "collect_hardware", lambda *args: pytest.fail("Must refuse before probing"))
    with pytest.raises(SystemExit) as error:
        hw.main()
    assert error.value.code == 2
    assert sentinel.read_bytes() == b"existing evidence"


def test_package_probe_never_imports_frameworks():
    script = hw.PACKAGE_PROBE + "\nimport sys; assert not any(n in sys.modules for n in ['torch','paddle','docling','surya','marker'])"
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    assert isinstance(json.loads(result.stdout), dict)


def test_registry_covers_all_candidates_and_evidence():
    path = Path(__file__).resolve().parents[1] / "MODEL_REGISTRY.yaml"
    registry = json.loads(path.read_text(encoding="utf-8"))  # JSON is a strict YAML subset.
    from benchmark_suite.tracking import MODEL_IDS
    assert set(registry["models"]) == set(MODEL_IDS)
    for model in registry["models"].values():
        assert model["hardware_compatibility"] in {"COMPATIBLE", "LIMITED", "INCOMPATIBLE", "UNKNOWN"}
        assert model["execution_authorized"] is False
        assert model["sources"] and all(url.startswith("https://") for url in model["sources"])
        assert model["memory_basis"] == "ESTIMATE_NOT_MEASURED"
        assert set(model["capabilities"]) == {"english", "arabic", "layout", "reading_order", "tables", "chart_data", "structured_output"}
