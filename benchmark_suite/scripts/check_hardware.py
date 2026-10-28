"""Read-only Windows inventory; never import model frameworks or provision assets.

Only the requested report files are written, exclusively (no overwrites).
Invoke from the repository root, or provide any output directory explicitly.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
from typing import Any
from zoneinfo import ZoneInfo

GIB = 1024 ** 3
POWERSHELL_INVENTORY = r"""
$ErrorActionPreference='Stop'
$os=Get-CimInstance Win32_OperatingSystem
$cs=Get-CimInstance Win32_ComputerSystem
@{
 cpu=@(Get-CimInstance Win32_Processor | Select-Object Name,NumberOfCores,NumberOfLogicalProcessors)
 memory=@{total_bytes=[long]$cs.TotalPhysicalMemory; available_bytes=[long]$os.FreePhysicalMemory*1024}
 windows=@{caption=$os.Caption; version=$os.Version; build=$os.BuildNumber}
 gpus=@(Get-CimInstance Win32_VideoController | Select-Object Name,AdapterRAM,DriverVersion)
} | ConvertTo-Json -Depth 5
"""

# Query distribution metadata / read version.py as text. Never execute its code.
PACKAGE_PROBE = r"""
import ast, importlib.metadata as metadata, json
names = ['torch','torchvision','paddlepaddle','paddlepaddle-gpu','paddleocr',
         'docling','easyocr','transformers','surya-ocr','marker-pdf']
result = {}
for name in names:
    try:
        dist = metadata.distribution(name)
        item = {'version': dist.version, 'requires_python': dist.metadata.get('Requires-Python')}
        if name == 'torch':
            source = dist.locate_file('torch/version.py')
            if source.is_file():
                for node in ast.parse(source.read_text(encoding='utf-8')).body:
                    target = node.target if isinstance(node, ast.AnnAssign) else (
                        node.targets[0] if isinstance(node, ast.Assign) else None)
                    if isinstance(target, ast.Name) and target.id in {'__version__','cuda','hip'}:
                        try: item[target.id] = ast.literal_eval(node.value)
                        except (ValueError, TypeError): pass
        result[name] = item
    except metadata.PackageNotFoundError:
        result[name] = None
print(json.dumps(result))
"""


def decode_output(data: bytes) -> str:
    """wsl.exe can emit UTF-16LE even when stdout is redirected."""
    encoding = "utf-16" if data.startswith((b"\xff\xfe", b"\xfe\xff")) else (
        "utf-16-le" if data.count(b"\x00") > len(data) // 5 else "utf-8-sig")
    return data.decode(encoding, errors="replace").strip()


def run_probe(command: list[str], timeout: int = 15) -> dict[str, Any]:
    """Bound native probes and preserve missing/error/timeout as distinct evidence."""
    try:
        result = subprocess.run(command, capture_output=True, timeout=timeout, check=False)
    except FileNotFoundError:
        return {"status": "NOT_FOUND"}
    except subprocess.TimeoutExpired:
        return {"status": "TIMEOUT"}
    except OSError as exc:
        return {"status": "ERROR", "detail": type(exc).__name__}
    return {"status": "OK" if result.returncode == 0 else "ERROR",
            "returncode": result.returncode, "stdout": decode_output(result.stdout),
            "stderr": decode_output(result.stderr)}


def parse_nvidia_csv(text: str) -> list[dict[str, Any]]:
    devices = []
    for row in csv.reader(text.splitlines()):
        if not row:
            continue
        if len(row) != 5:
            raise ValueError("Unexpected nvidia-smi GPU column count.")
        name, total, free, driver, capability = (v.strip() for v in row)
        devices.append({"name": name, "vram_total_mib": float(total),
                        "vram_free_mib": float(free), "driver_version": driver,
                        "compute_capability": capability})
    return devices


def conservative_loading_gate(available_bytes: int | None) -> dict[str, Any]:
    """A research safety stop, not a universal model minimum or a runner preflight."""
    if available_bytes is None:
        return {"status": "UNKNOWN", "reason": "Available RAM was not measured; no loading authorized."}
    if available_bytes < 2 * GIB:
        return {"status": "BLOCKED_BY_HARDWARE",
                "reason": "Less than 2 GiB free RAM; block model loading until rechecked.",
                "floor_basis": "Conservative suite policy; not a vendor minimum."}
    return {"status": "REQUIRES_MODEL_PREFLIGHT",
            "reason": "A generic floor does not establish any model's compatibility."}


def collect_hardware(python: str = sys.executable, tesseract: str | None = None) -> dict[str, Any]:
    profile: dict[str, Any] = {
        "schema_version": 1,
        "captured_at": datetime.now(ZoneInfo("Africa/Cairo")).isoformat(timespec="seconds"),
        "timezone": "Africa/Cairo", "collector_python": platform.python_version(),
        "architecture": platform.machine(), "frameworks_imported": False,
        "model_inference_executed": False,
    }
    if platform.system() != "Windows":
        raise RuntimeError("This collector targets Windows; refusing to fabricate CIM results.")
    cim = run_probe(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", POWERSHELL_INVENTORY])
    profile["inventory_probe_status"] = cim["status"]
    if cim["status"] == "OK":
        try:
            profile.update(json.loads(cim["stdout"]))
        except json.JSONDecodeError:
            profile["inventory_probe_status"] = "INVALID_JSON"
    disk = shutil.disk_usage(Path.cwd().anchor)
    profile["workspace_disk"] = {"total_bytes": disk.total, "free_bytes": disk.free}
    gpu = run_probe(["nvidia-smi", "--query-gpu=name,memory.total,memory.free,driver_version,compute_cap",
                     "--format=csv,noheader,nounits"])
    profile["nvidia_probe_status"] = gpu["status"]
    profile["nvidia_devices"] = []
    if gpu["status"] == "OK":
        try:
            profile["nvidia_devices"] = parse_nvidia_csv(gpu["stdout"])
        except ValueError:
            profile["nvidia_probe_status"] = "INVALID_OUTPUT"
    # The full native output includes process names; persist only the CUDA header.
    header = run_probe(["nvidia-smi"])
    match = re.search(r"CUDA Version:\s*([\d.]+)", header.get("stdout", ""))
    profile["driver_cuda_max_version"] = match.group(1) if match else None
    profile["cuda_toolkit"] = run_probe(["nvcc", "--version"])
    profile["wsl_status"] = run_probe(["wsl", "--status"])
    profile["wsl_distributions"] = run_probe(["wsl", "--list", "--verbose"])
    packages = run_probe([python, "-c", PACKAGE_PROBE])
    profile["package_probe_status"] = packages["status"]
    profile["packages"] = {}
    if packages["status"] == "OK":
        try:
            profile["packages"] = json.loads(packages["stdout"])
        except json.JSONDecodeError:
            profile["package_probe_status"] = "INVALID_JSON"
    profile["target_python"] = run_probe([python, "--version"])
    native = tesseract or shutil.which("tesseract")
    if native is None:
        # Standard Windows installation; no registry scan or environment secrets.
        program_files = os.environ.get("ProgramFiles")
        candidate = Path(program_files) / "Tesseract-OCR/tesseract.exe" if program_files else None
        native = str(candidate) if candidate is not None and candidate.is_file() else None
    profile["tesseract_version"] = run_probe([native, "--version"]) if native else {"status": "NOT_FOUND"}
    languages = run_probe([native, "--list-langs"]) if native else {"status": "NOT_FOUND"}
    # The first line can expose local paths; keep only validated language IDs.
    profile["tesseract_languages"] = {
        "status": languages["status"],
        "languages": [s for s in languages.get("stdout", "").splitlines()
                      if re.fullmatch(r"[a-zA-Z_]+(?:/[a-zA-Z_]+)?", s.strip())],
    }
    profile["poppler_version"] = run_probe(["pdftoppm", "-v"])
    profile["loading_gate"] = conservative_loading_gate(profile.get("memory", {}).get("available_bytes"))
    return profile


def render_profile(profile: dict[str, Any]) -> str:
    memory = profile.get("memory", {})
    def gib(value: int | None) -> str:
        return "UNKNOWN" if value is None else f"{value / GIB:.2f} GiB"
    lines = ["# Hardware profile", "", f"Captured: {profile['captured_at']} (Africa/Cairo).",
             "Read-only native/metadata probes; no model or framework imports, installations or inference.", "",
             "| Field | Observation |", "|---|---|"]
    def row(key: str, value: Any) -> None:
        clean = str(value).replace('|', '/').replace('\r', '').replace('\n', '; ')
        lines.append(f"| {key} | {clean} |")
    for cpu in profile.get("cpu", []):
        row("CPU", f"{cpu['Name']}; {cpu['NumberOfCores']} cores / {cpu['NumberOfLogicalProcessors']} threads")
    row("RAM total / available", f"{gib(memory.get('total_bytes'))} / {gib(memory.get('available_bytes'))}")
    row("Windows", profile.get("windows", "UNKNOWN"))
    row("Collector / target Python", f"{profile['collector_python']} / {profile['target_python'].get('stdout', 'UNKNOWN')}")
    row("Architecture", profile["architecture"])
    for gpu in profile.get("gpus", []):
        row("Display adapter", f"{gpu['Name']}; WMI driver {gpu['DriverVersion']}; AdapterRAM is not reliable dedicated VRAM")
    for gpu in profile["nvidia_devices"]:
        row("NVIDIA GPU", f"{gpu['name']}; {gpu['vram_total_mib']:g} MiB dedicated VRAM; {gpu['vram_free_mib']:g} MiB free; CC {gpu['compute_capability']}; driver {gpu['driver_version']}")
    row("Driver CUDA ceiling", profile["driver_cuda_max_version"])
    row("CUDA toolkit (nvcc)", profile["cuda_toolkit"]["status"])
    row("Disk free / total", f"{gib(profile['workspace_disk']['free_bytes'])} / {gib(profile['workspace_disk']['total_bytes'])}")
    row("WSL status", profile["wsl_status"].get("stdout", profile["wsl_status"]["status"]).replace("\n", "; "))
    row("WSL distributions", profile["wsl_distributions"].get("stdout", profile["wsl_distributions"]["status"]).replace("\n", "; "))
    native_version = profile["tesseract_version"]
    row("Tesseract version", (native_version.get("stdout") or native_version.get("stderr")
                              or native_version["status"]).splitlines()[0])
    row("Tesseract language assets", ", ".join(profile["tesseract_languages"]["languages"]) or "UNKNOWN")
    row("Poppler", (profile["poppler_version"].get("stderr") or profile["poppler_version"]["status"]).splitlines()[0])
    row("Model loading gate", profile["loading_gate"])
    lines += ["", "## Installed package evidence", "", "| Distribution | Version / evidence |", "|---|---|"]
    for name, package in profile["packages"].items():
        row(name, "NOT_INSTALLED" if package is None else json.dumps(package, ensure_ascii=False))
    lines += ["", "## Interpretation and limits", "",
              "- RAM/free VRAM/disk are a point-in-time snapshot. Recheck immediately before each model; availability can fall.",
              "- NVIDIA-SMI's CUDA number is driver capability, not an installed toolkit or usable framework CUDA build. nvcc NOT_FOUND means not on PATH, not proof no toolkit exists anywhere.",
              "- A torch version.py cuda=null / +cpu build is CPU-only. paddlepaddle installed without paddlepaddle-gpu provides no evidence of a GPU-enabled Paddle runtime. Framework runtime calls were intentionally skipped to avoid memory pressure; no torch/paddle imports occurred.",
              "- Integrated Intel AdapterRAM is a WMI display value, not a separate dedicated VRAM bank; never add it to NVIDIA VRAM.",
              "- WSL inventory does not start a distribution or certify CUDA passthrough. WSL2 presence cannot fix insufficient physical RAM/VRAM or GPU architecture.",
              "- The 2 GiB available-RAM gate is a conservative suite safety floor, not a documented minimum for any model. Passing it still requires model-specific preflight in TASK-007.",
              "- Exact native probe statuses and sanitized evidence are in HARDWARE_PROFILE.json. No machine hostname, serials, environment secrets or running-process inventory is stored.", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True,
                        help="New or existing report directory; existing profile files are never overwritten")
    parser.add_argument("--python", default=sys.executable, help="Interpreter whose package metadata to inspect")
    parser.add_argument("--tesseract", help="Optional native executable path; never used for OCR")
    args = parser.parse_args()
    targets = [args.output / "HARDWARE_PROFILE.json", args.output / "HARDWARE_PROFILE.md"]
    if any(p.exists() for p in targets):
        parser.error("Profile already exists. Choose a new --output directory to preserve prior observations.")
    try:
        profile = collect_hardware(args.python, args.tesseract)
        rendered = render_profile(profile)
        args.output.mkdir(parents=True, exist_ok=True)
        for path, content in zip(targets, [json.dumps(profile, indent=2, ensure_ascii=False) + "\n", rendered]):
            with path.open("x", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
    except (OSError, RuntimeError, ValueError) as exc:
        parser.exit(1, f"Hardware inventory failed: {exc}\n")
    print(f"Saved hardware profile. Model loading: {profile['loading_gate']['status']}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
