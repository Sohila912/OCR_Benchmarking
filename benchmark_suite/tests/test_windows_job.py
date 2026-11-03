"""Exercise the actual OS memory guard in disposable child processes."""

import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.skipif(os.name != "nt", reason="Windows job API")
def test_windows_job_rejects_oversized_allocation():
    scripts = Path(__file__).resolve().parents[1] / "scripts"
    code = f"""
import sys
sys.path.insert(0, {str(scripts)!r})
from windows_job import limit_current_process
limit_current_process(96 * 1024**2)
try:
    bytearray(128 * 1024**2)
except MemoryError:
    print('guarded')
else:
    raise RuntimeError('Windows did not enforce the cap')
"""
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "guarded"
