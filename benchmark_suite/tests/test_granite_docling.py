import hashlib
import json
from types import SimpleNamespace

import pytest

from OCR.providers.base import OCRDocument
from benchmark_suite.adapters.granite_docling import GraniteDoclingAdapter


def setup_adapter(tmp_path):
    path = tmp_path / "page.png"
    path.write_bytes(b"frozen input")
    doc = OCRDocument(document_id="test", filename="page.png", path=path,
        source_metadata={"source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "language": "ar"})
    adapter = GraniteDoclingAdapter(None)
    adapter.config = SimpleNamespace(adapter_options={"asset_root": str(tmp_path / "assets"),
        "worker_python": "unused", "maximum_job_memory_bytes": 4 * 1024**3})
    return adapter, doc


def test_corrupt_frozen_source_is_rejected_before_spawning(tmp_path):
    adapter, doc = setup_adapter(tmp_path)
    doc.path.write_bytes(b"changed input")
    with pytest.raises(ValueError, match="Frozen source checksum mismatch"):
        adapter.predict(doc)
    assert adapter.process is None


def test_truncated_generation_cannot_become_successful_prediction(tmp_path, monkeypatch):
    adapter, doc = setup_adapter(tmp_path)
    module = "benchmark_suite.adapters.granite_docling"
    monkeypatch.setattr(module + ".psutil.virtual_memory", lambda: SimpleNamespace(available=5 * 1024**3))

    def spawn(command, **kwargs):
        output = command[command.index("--output") + 1]
        from pathlib import Path
        (Path(output) / "result.json").write_text(json.dumps({"status": "INCOMPLETE",
            "error_type": "GenerationLimitReached", "error": "Output truncated"}))
        return SimpleNamespace(poll=lambda: 1, returncode=1, wait=lambda **kw: 1)

    monkeypatch.setattr(module + ".subprocess.Popen", spawn)
    with pytest.raises(RuntimeError, match="GenerationLimitReached: Output truncated"):
        adapter.predict(doc)
    assert adapter.process is None
