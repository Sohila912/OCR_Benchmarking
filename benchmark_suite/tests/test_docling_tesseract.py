import hashlib
import io
from types import SimpleNamespace

import pytest

from OCR.providers.base import OCRDocument
from benchmark_suite.adapters.docling_tesseract import DoclingTesseractAdapter


def test_prepare_switches_language_and_copies_identical_input_to_assets(tmp_path):
    source = tmp_path / "original.png"
    source.write_bytes(b"frozen-image-bytes")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    document = OCRDocument(document_id="test", filename="original.png", path=source,
                           source_metadata={"language": "en", "source_sha256": digest})
    adapter = DoclingTesseractAdapter(None)
    adapter.config = SimpleNamespace(adapter_options={"asset_root": str(tmp_path / "assets")})
    adapter.process = SimpleNamespace(poll=lambda: None)
    adapter.current_language = "ar"
    switches = []

    def start(language):
        switches.append(language)
        adapter.current_language = language

    adapter._start = start
    prepared, _ = adapter.prepare(document)
    assert switches == ["en"]
    assert prepared.document_id == document.document_id
    assert prepared.path.parent == tmp_path / "assets/inputs"
    assert hashlib.sha256(prepared.path.read_bytes()).hexdigest() == digest
    adapter.prepare(document)
    assert switches == ["en"]


def test_failed_worker_reply_cleans_up_and_never_returns_a_prediction():
    adapter = DoclingTesseractAdapter(SimpleNamespace(model_revision="test"))
    adapter.process = SimpleNamespace(stdin=io.StringIO())
    adapter._receive = lambda _: {"ok": False, "error_type": "MemoryError", "error": "bounded worker"}
    cleaned = []
    adapter.cleanup = lambda: cleaned.append(True)
    document = OCRDocument(document_id="test", filename="test.png", path="test.png")
    with pytest.raises(RuntimeError, match="MemoryError: bounded worker"):
        adapter.predict((document, 0))
    assert cleaned == [True]
