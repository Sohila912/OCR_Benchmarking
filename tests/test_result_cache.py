"""Persistent cache integration with fake OCR, real SQLite and cross-process locks."""
import hashlib
import io
import multiprocessing
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from conftest import FakeProvider
from OCR.app import create_app
from OCR.errors import ExtractionError, ProviderNotReadyError
from OCR.providers.base import OCRDocument
from OCR.result_cache import ResultCache, digest_json, fingerprint
from OCR.schemas import OCRIssue, OCRResult
from OCR.service import OCRService, ingest_pdf


class CountingProvider(FakeProvider):
    model_name = "fixture"
    model_version = "v1"

    def __init__(self, name="tesseract", marker=None):
        super().__init__(name)
        self.calls = 0
        self.marker = marker
        self.prompt = "transcribe"

    def cache_identity(self):
        return {"prompt": self.prompt}

    def extract(self, document):
        self.calls += 1
        if self.marker:
            with open(self.marker, "ab") as stream:
                stream.write(b"inference\n")
            time.sleep(0.3)
        result = super().extract(document)
        result.model_name, result.model_version = self.model_name, self.model_version
        result.markdown = "# Hello مرحبا"
        return result


def uploaded(settings, filename="sample.pdf", payload=b"%PDF-1.4 same document"):
    return ingest_pdf(io.BytesIO(payload), filename, settings)


def status(result):
    return result.provider_metadata["cache"]["status"]


def job(cache, key):
    with cache.connect() as db:
        return dict(db.execute("SELECT * FROM ocr_jobs WHERE cache_key=?", (key,)).fetchone())


def test_identical_bytes_renamed_and_service_restart_reuse(settings):
    provider = CountingProvider()
    one, two = uploaded(settings), uploaded(settings, "renamed.pdf")
    assert one.document_id == two.document_id == hashlib.sha256(one.path.read_bytes()).hexdigest()
    first = OCRService(settings, {"tesseract": provider}).extract(one)
    other = CountingProvider()
    second = OCRService(settings, {"tesseract": other}).extract(two)
    assert status(first) == "miss" and status(second) == "hit"
    assert provider.calls == 1 and other.calls == other.initializations == 0
    assert first.text == second.text and first.markdown == second.markdown
    assert second.filename == "renamed.pdf" and second.source == two.source
    assert second.source_metadata == two.source_metadata
    assert first.provider_metadata["duration_seconds"] == second.provider_metadata["duration_seconds"]
    assert len(list((settings.output_dir / "cache").glob("*.json"))) == 1
    # The returned value cannot mutate saved content.
    second.pages[0].text = "mutated"
    assert OCRService(settings, {"tesseract": other}).extract(one).pages[0].text != "mutated"


@pytest.mark.parametrize("change", ["bytes", "provider", "model_name", "model_version", "config", "prompt", "pipeline"])
def test_output_identity_changes_invalidate(settings, change):
    provider = CountingProvider()
    document = uploaded(settings)
    OCRService(settings, {"tesseract": provider}).extract(document)
    name = "tesseract"
    if change == "bytes":
        document = uploaded(settings, payload=b"%PDF-1.4 different")
    elif change == "provider":
        name = provider.name = "other_engine"
    elif change in ("model_name", "model_version"):
        setattr(provider, change, "changed")
    elif change == "config":
        settings = settings.model_copy(update={"pdf_dpi": 150})
    elif change == "prompt":
        provider.prompt = "new prompt"
    else:
        settings = settings.model_copy(update={"cache_pipeline_revision": "2"})
    assert status(OCRService(settings, {name: provider}).extract(document, name)) == "miss"
    assert provider.calls == 2


def test_fingerprint_excludes_storage_and_benchmark_settings(settings):
    provider = CountingProvider()
    identity = fingerprint(settings, provider)
    changed = settings.model_copy(update={"benchmark_retention_days": 1, "benchmark_db": Path("elsewhere"),
                                          "api_url": "http://other", "retain_uploads": False,
                                          "output_dir": settings.temp_dir})
    assert fingerprint(changed, provider) == identity


def test_real_adapter_assets_prompt_and_remote_digest_invalidate(settings, tmp_path, monkeypatch):
    from OCR.providers.paddle_vl import PaddleVLProvider
    from OCR.providers.qwen_ollama import QwenOllamaProvider
    import OCR.providers.qwen_ollama as qwen
    assets = tmp_path / "models"
    assets.mkdir()
    weights = assets / "weights.bin"
    weights.write_bytes(b"first")
    current = settings.model_copy(update={"paddle_vl_model_dir": assets})
    provider = PaddleVLProvider(current)
    first = fingerprint(current, provider)
    weights.write_bytes(b"second")
    assert first != fingerprint(current, provider)
    digest = ["sha256:first"]
    monkeypatch.setattr("requests.get", lambda *a, **kw: Mock(raise_for_status=lambda: None,
                        json=lambda: {"models": [{"name": settings.ollama_ocr_model, "digest": digest[0]}]}))
    provider = QwenOllamaProvider(settings)
    original = fingerprint(settings, provider)
    digest[0] = "sha256:second"
    assert original != fingerprint(settings, provider)
    original = fingerprint(settings, provider)
    monkeypatch.setattr(qwen, "OCR_PROMPT", "changed prompt")
    assert original != fingerprint(settings, provider)
    assert provider.health().status == "uninitialized"


def test_failures_and_partial_results_are_retried(settings):
    provider = CountingProvider()
    provider.failure = ExtractionError("secret detail")
    service = OCRService(settings, {"tesseract": provider})
    document = uploaded(settings)
    with pytest.raises(ExtractionError):
        service.extract(document)
    cache = ResultCache(settings.output_dir)
    with cache.connect() as db:
        row = dict(db.execute("SELECT * FROM ocr_jobs").fetchone())
    assert row["state"] == "failed" and "secret" not in row["error"]
    provider.failure = None
    result = service.extract(document)
    assert status(result) == "miss" and provider.calls == 2
    assert job(cache, result.provider_metadata["cache"]["key"])["attempts"] == 2

    class Partial(CountingProvider):
        def extract(self, document):
            result = super().extract(document)
            result.pages[0].errors.append(OCRIssue(code="page_failed", message="Failed page"))
            return result
    partial = Partial()
    service = OCRService(settings, {"tesseract": partial})
    assert status(service.extract(document)) == "not_cached"
    assert status(service.extract(document)) == "not_cached"
    assert partial.calls == 2


@pytest.mark.parametrize("damage", ["missing", "truncated", "schema", "wrong_document"])
def test_corrupt_files_recover(settings, damage):
    provider = CountingProvider()
    service = OCRService(settings, {"tesseract": provider})
    document = uploaded(settings)
    original = service.extract(document)
    key = original.provider_metadata["cache"]["key"]
    cache = ResultCache(settings.output_dir)
    path = cache.directory / job(cache, key)["result_file"]
    if damage == "missing":
        path.unlink()
    else:
        payload = b"{" if damage == "truncated" else b'{"invalid": true}'
        if damage == "wrong_document":
            payload = original.model_copy(update={"document_id": "other"}).model_dump_json().encode()
        path.write_bytes(payload)
        if damage != "truncated":
            # Even matching checksums must not bypass schema/identity validation.
            with cache.connect() as db:
                db.execute("UPDATE ocr_jobs SET result_sha256=? WHERE cache_key=?", (hashlib.sha256(payload).hexdigest(), key))
    orphan = cache.directory / (key + "-abandoned.tmp")
    orphan.write_bytes(b"incomplete")
    assert status(service.extract(document)) == "miss" and provider.calls == 2
    assert job(cache, key)["state"] == "completed" and not orphan.exists()
    assert len(list(cache.directory.glob(key + "-*.json"))) == 1


def test_force_reprocess_and_cache_disabled(settings):
    provider = CountingProvider()
    service = OCRService(settings, {"tesseract": provider})
    document = uploaded(settings)
    first = service.extract(document)
    forced = service.extract(document, force_reprocess=True)
    assert status(forced) == "reprocessed" and provider.calls == 2
    assert status(service.extract(document)) == "hit" and provider.calls == 2
    assert first.provider_metadata["cache"]["key"] == forced.provider_metadata["cache"]["key"]
    disabled = settings.model_copy(update={"cache_enabled": False})
    service = OCRService(disabled, {"tesseract": provider})
    assert status(service.extract(document, persist_result=False)) == "disabled"
    assert status(service.extract(document, persist_result=False)) == "disabled"
    assert provider.calls == 4


def test_pending_timeout_does_not_steal_live_lock(settings):
    cache = ResultCache(settings.output_dir, wait_seconds=0.1)
    document = uploaded(settings)
    identity = fingerprint(settings, CountingProvider())
    key = digest_json({"document_id": document.document_id, **identity})
    with cache.locked(key):
        with ThreadPoolExecutor() as executor:
            future = executor.submit(cache.run, document, identity, lambda: pytest.fail("Must not infer"))
            with pytest.raises(ProviderNotReadyError, match="still processing"):
                future.result(timeout=5)
        assert job(cache, key)["state"] == "pending"
    result = cache.run(document, identity, lambda: OCRResult(document_id=document.document_id,
                        filename=document.filename, provider="tesseract", text="recovered"))
    assert status(result) == "miss" and job(cache, key)["state"] == "completed"


def test_concurrent_threads_and_force_requests_share_inference(settings):
    cache = ResultCache(settings.output_dir)
    document = uploaded(settings)
    identity = fingerprint(settings, CountingProvider())
    entered, release = Event(), Event()
    calls = []
    def compute():
        calls.append(1)
        entered.set()
        assert release.wait(10)
        return OCRResult(document_id=document.document_id, filename=document.filename,
                         provider="tesseract", text="once")
    requested = time.time()
    with ThreadPoolExecutor(max_workers=4) as executor:
        first = executor.submit(cache.run, document, identity, compute)
        assert entered.wait(10)
        key = digest_json({"document_id": document.document_id, **identity})
        assert job(cache, key)["state"] == "processing"
        others = [executor.submit(cache.run, document, identity, compute, force=True, requested_at=requested) for _ in range(3)]
        release.set()
        results = [first.result(timeout=10), *[f.result(timeout=10) for f in others]]
    assert len(calls) == 1
    assert [status(r) for r in results] == ["miss", "hit", "hit", "hit"]


def _service_worker(settings_data, document_data, marker, start, queue):
    from OCR.config import Settings
    settings = Settings.model_validate(settings_data)
    document = OCRDocument.model_validate(document_data)
    provider = CountingProvider(marker=marker)
    try:
        if not start.wait(15):
            raise RuntimeError("Start signal timed out")
        result = OCRService(settings, {"tesseract": provider}).extract(document)
        queue.put((status(result), None))
    except Exception as exc:
        queue.put((None, repr(exc) + "; cause=" + repr(exc.__cause__)))


def _crashing_worker(output_dir, document_data, identity, entered):
    document = OCRDocument.model_validate(document_data)
    def compute():
        entered.set()
        time.sleep(120)
    ResultCache(output_dir).run(document, identity, compute)


def test_concurrent_processes_run_only_once(settings, tmp_path):
    document = uploaded(settings)
    context = multiprocessing.get_context("spawn")
    start, queue = context.Event(), context.Queue()
    marker = str(tmp_path / "calls.txt")
    processes = [context.Process(target=_service_worker, args=(settings.model_dump(mode="json"),
                 document.model_dump(mode="json"), marker, start, queue)) for _ in range(2)]
    try:
        for process in processes:
            process.start()
        start.set()
        results = [queue.get(timeout=30) for _ in processes]
        for process in processes:
            process.join(10)
            assert process.exitcode == 0
        assert sorted(r[0] for r in results if r[0]) == ["hit", "miss"], results
        assert Path(marker).read_text().splitlines() == ["inference"]
    finally:
        for process in processes:
            if process.is_alive():
                process.terminate()
                process.join(5)
        queue.close()


def test_crashed_worker_stale_claim_is_recovered(settings):
    context = multiprocessing.get_context("spawn")
    document = uploaded(settings)
    identity = fingerprint(settings, CountingProvider())
    entered = context.Event()
    process = context.Process(target=_crashing_worker, args=(settings.output_dir,
                              document.model_dump(mode="json"), identity, entered))
    try:
        process.start()
        assert entered.wait(20)
        process.terminate()
        process.join(10)
        cache = ResultCache(settings.output_dir)
        key = digest_json({"document_id": document.document_id, **identity})
        assert job(cache, key)["state"] == "processing"
        result = cache.run(document, identity, lambda: OCRResult(document_id=document.document_id,
                          filename=document.filename, provider="tesseract", text="recovered"))
        assert status(result) == "miss" and job(cache, key)["attempts"] == 2
    finally:
        if process.is_alive():
            process.terminate()
            process.join(5)


def test_processing_and_benchmarks_share_ocr_but_rescore_references(settings):
    provider = CountingProvider()
    service = OCRService(settings, {"tesseract": provider})
    with TestClient(create_app(settings, service)) as client:
        def extract(force=False):
            return client.post("/extract", files={"file": ("first.pdf", b"%PDF-1.4 same")},
                               data={"force_reprocess": str(force).lower()})
        def benchmark(reference, force=False):
            response = client.post("/benchmarks/run", files={"file": ("renamed.pdf", b"%PDF-1.4 same"),
                "reference": ("truth.md", reference)}, data={"providers": '["tesseract"]', "paired": "true",
                "force_reprocess": str(force).lower()})
            assert response.status_code == 200
            return response.json()["results"][0]
        assert extract().status_code == 200
        first = benchmark("Hello مرحبا")
        second = benchmark("different reference")
        assert first["cache_status"] == second["cache_status"] == "hit"
        assert provider.calls == 1
        assert first["metrics"]["cer"] == 0 and second["metrics"]["cer"] > 0
        assert first["reference_hash"] != second["reference_hash"] and first["id"] != second["id"]
        assert first["ocr_result"]["filename"] == "renamed.pdf"
        assert benchmark("Hello مرحبا", force=True)["cache_status"] == "reprocessed"
        assert provider.calls == 2
        assert extract(force=True).json()["provider_metadata"]["cache"]["status"] == "reprocessed"
        assert provider.calls == 3
        history = client.get("/benchmarks/history").json()
        assert len(history) == 3 and all("output" not in row and "ocr_result" not in row for row in history)
    contents = "\n".join(path.read_text(encoding="utf-8") for path in (settings.output_dir / "cache").glob("*.json"))
    assert "different reference" not in contents


def test_cache_write_failure_marks_failed_and_retries(settings, monkeypatch):
    import OCR.result_cache as module
    provider = CountingProvider()
    service = OCRService(settings, {"tesseract": provider})
    document = uploaded(settings)
    original_replace = module.os.replace
    monkeypatch.setattr(module.os, "replace", Mock(side_effect=OSError("disk failure")))
    with pytest.raises(ExtractionError, match="storage is unavailable"):
        service.extract(document)
    cache = ResultCache(settings.output_dir)
    with cache.connect() as db:
        assert db.execute("SELECT state FROM ocr_jobs").fetchone()[0] == "failed"
    assert not list(cache.directory.glob("*.tmp"))
    monkeypatch.setattr(module.os, "replace", original_replace)
    assert status(service.extract(document)) == "miss" and provider.calls == 2


def test_changed_upload_bytes_cannot_poison_cache(settings):
    provider = CountingProvider()
    service = OCRService(settings, {"tesseract": provider})
    document = uploaded(settings)
    document.path.write_bytes(b"%PDF-1.4 changed after ingest")
    from OCR.errors import InvalidDocumentError
    with pytest.raises(InvalidDocumentError, match="changed after upload"):
        service.extract(document)
    assert provider.calls == 0
