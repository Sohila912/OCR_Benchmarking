"""Linux/container memory-capacity checks; no model imports or downloads."""
from pathlib import Path

def memory_capacity_bytes():
    limits = []
    for filename in ("/sys/fs/cgroup/memory.max", "/sys/fs/cgroup/memory/memory.limit_in_bytes"):
        try:
            value = int(Path(filename).read_text().strip())
            if 0 < value < 2**60:
                limits.append(value)
        except (OSError, ValueError):
            pass
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemTotal:"):
                limits.append(int(line.split()[1]) * 1024)
                break
    except (OSError, ValueError, IndexError):
        pass
    return min(limits) if limits else None

def paddle_memory_issue(settings):
    capacity = memory_capacity_bytes()
    minimum = settings.paddle_min_memory_gib
    if settings.paddle_device.lower().startswith("cpu") and capacity and capacity < minimum * 1024**3:
        return (f"PaddleOCR-VL CPU loading is blocked: memory capacity {capacity / 1024**3:.1f} GiB is below the configured {minimum:g} GiB safety floor. "
                "Use a higher-memory host/container while leaving RAM for the host OS, then retry. "
                "The floor is an OOM guard, not a guarantee of sufficient memory; OCR_PADDLE_MIN_MEMORY_GIB controls it.")
    return None
