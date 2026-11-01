"""Fail-closed authorization/resources, using metadata rather than model imports."""

from datetime import datetime, timezone
import importlib.metadata
from pathlib import Path
import platform
import shutil
import sys

import psutil

from benchmark_suite.dataset_io import digest
from benchmark_suite.scripts.check_hardware import PACKAGE_PROBE, parse_nvidia_csv, run_probe
from benchmark_suite.tracking import MODEL_IDS, load_status

GIB = 1024**3


class PreflightBlocked(RuntimeError):
    def __init__(self, reasons):
        self.reasons = reasons
        super().__init__("; ".join(reasons))


def authorize(spec, config, status_path):
    if config.purpose == "fixture":
        if spec.model_id != "fixture":
            raise PreflightBlocked(["Fixture mode is restricted to the synthetic fixture adapter"])
        return
    if spec.model_id not in MODEL_IDS:
        raise PreflightBlocked(["Unregistered model; no execution approval"])
    status = load_status(status_path)
    task = f"TASK-{MODEL_IDS.index(spec.model_id)+9:03}"
    if any(status["tasks"][f"TASK-{i:03}"] != "COMPLETED" for i in (3, 5, 6, 7, 8)):
        raise PreflightBlocked(["Shared prerequisites TASK-003/005/006/007/008 are incomplete"])
    if task not in status["approved_tasks"] or status["tasks"][task] != "IN_PROGRESS" or status["current_task"] != task:
        raise PreflightBlocked([f"Explicit approval and active checkpoint required for {task} / {spec.model_id}"])
    if status["models"][spec.model_id] != "IN_PROGRESS":
        raise PreflightBlocked([status["model_block_reasons"].get(spec.model_id, "Model is not authorized for execution")])


def snapshot(root):
    memory = psutil.virtual_memory()
    gpu = run_probe(["nvidia-smi", "--query-gpu=name,memory.total,memory.free,driver_version,compute_cap", "--format=csv,noheader,nounits"], timeout=5)
    try:
        devices = parse_nvidia_csv(gpu["stdout"]) if gpu["status"] == "OK" else []
    except (ValueError, KeyError):
        devices = []
    package_probe = run_probe([sys.executable, "-c", PACKAGE_PROBE], timeout=10)
    import json
    try:
        builds = json.loads(package_probe["stdout"]) if package_probe["status"] == "OK" else {}
    except (ValueError, KeyError):
        builds = {}
    return {"captured_at": datetime.now(timezone.utc).isoformat(), "ram_available_bytes": memory.available,
            "ram_total_bytes": memory.total, "disk_free_bytes": shutil.disk_usage(root).free,
            "gpus": devices, "os": platform.platform(), "cpu": platform.processor(),
            "logical_cpus": psutil.cpu_count(), "physical_cpus": psutil.cpu_count(logical=False),
            "python": platform.python_version(), "frameworks_imported": False, "framework_builds": builds}


def environment():
    return {"python": platform.python_version(), "os": platform.platform(),
            "packages": dict(sorted((d.metadata["Name"], d.version) for d in importlib.metadata.distributions() if d.metadata.get("Name")))}


def check(spec, config, observed, assets_root):
    req, reasons = spec.requirements, []
    if req.compatibility not in {"COMPATIBLE", "LIMITED"}:
        reasons.append("BLOCKED_BY_HARDWARE: compatibility is incompatible or unknown")
    ram_floor = 0 if config.purpose == "fixture" else 2*GIB
    if config.purpose != "fixture" and req.ram_bytes <= 0:
        reasons.append("Missing model-specific RAM estimate")
    if observed.get("ram_available_bytes", -1) < max(req.ram_bytes, ram_floor):
        reasons.append("BLOCKED_BY_HARDWARE: insufficient available RAM")
    reserve = 0 if config.purpose == "fixture" else 6*GIB
    if observed.get("disk_free_bytes", -1) < req.disk_bytes + reserve:
        reasons.append("BLOCKED_BY_HARDWARE: insufficient free disk plus reserve")
    if config.device.startswith("cuda:"):
        index = int(config.device.split(":")[1])
        devices = observed.get("gpus", [])
        if index >= len(devices) or req.vram_bytes <= 0:
            reasons.append("BLOCKED_BY_HARDWARE: GPU/VRAM estimate unavailable")
        else:
            gpu = devices[index]
            if gpu["vram_free_mib"]*1024**2 < req.vram_bytes or float(gpu["compute_capability"]) < req.min_compute_capability:
                reasons.append("BLOCKED_BY_HARDWARE: insufficient free VRAM or compute capability")
        builds = observed.get("framework_builds", {})
        if spec.gpu_backend == "none":
            reasons.append("GPU backend was not verified")
        elif spec.gpu_backend == "torch" and not (builds.get("torch") or {}).get("cuda"):
            reasons.append("BLOCKED_BY_HARDWARE: PyTorch CUDA build is unavailable")
        elif spec.gpu_backend == "paddle" and not builds.get("paddlepaddle-gpu"):
            reasons.append("BLOCKED_BY_HARDWARE: GPU Paddle distribution is unavailable")
    for name, expected in spec.packages.items():
        try:
            actual = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            actual = None
        if actual != expected:
            reasons.append(f"Dependency version mismatch: {name}")
    for relative, expected in [*spec.assets.items(), *spec.source_files.items()]:
        path = Path(assets_root) / relative
        if not path.is_file() or digest(path) != expected:
            reasons.append(f"Asset/source checksum mismatch: {relative}")
    if config.purpose != "fixture" and not spec.source_files:
        reasons.append("Adapter implementation source hashes are required")
    if reasons:
        raise PreflightBlocked(reasons)
