"""Provider selection, serialized local inference, and safe PDF ingestion."""

import hashlib
import logging
import re
import sqlite3
import tempfile
import time
from pathlib import Path, PurePosixPath, PureWindowsPath
from threading import RLock
from uuid import uuid4

from OCR.config import Settings
from OCR.logging_utils import log_event
from OCR.errors import OCRError, ExtractionError, InvalidDocumentError, UnsupportedProviderError, UploadTooLargeError
from OCR.providers.base import OCRDocument, OCRProvider
from OCR.providers.docling import DoclingProvider
from OCR.providers.paddle_vl import PaddleVLProvider
from OCR.providers.qwen_ollama import QwenOllamaProvider
from OCR.providers.tesseract import TesseractProvider
from OCR.schemas import OCRResult
from OCR.result_cache import ResultCache, fingerprint, digest_json, file_digest

PROVIDER_TYPES = {"paddle_vl": PaddleVLProvider, "docling": DoclingProvider, "tesseract": TesseractProvider,
                  "qwen_ollama": QwenOllamaProvider}
logger = logging.getLogger(__name__)


def validate_upload_name(filename: str | None) -> str:
    if (not filename or filename != filename.strip() or "\x00" in filename
            or any(ord(c) < 32 for c in filename) or ":" in filename
            or PureWindowsPath(filename).name != filename or PurePosixPath(filename).name != filename
            or Path(filename).suffix.lower() != ".pdf"):
        raise InvalidDocumentError("Upload a PDF with a plain filename, without directory components.")
    return filename


def ingest_pdf(stream, filename: str | None, settings: Settings, benchmark: bool = False) -> OCRDocument:
    """Bounded streaming copy; uploaded names never form filesystem paths."""
    filename = validate_upload_name(filename)
    settings.temp_dir.mkdir(parents=True, exist_ok=True)
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    size, header = 0, b""
    # NamedTemporaryFile's own context manager owns cleanup, including validation failures.
    with tempfile.TemporaryFile(dir=settings.temp_dir) as staging:
        while chunk := stream.read(1024 * 1024):
            size += len(chunk)
            if size > settings.max_upload_bytes:
                raise UploadTooLargeError("Upload exceeds OCR_MAX_UPLOAD_BYTES.")
            header = (header + chunk)[:1024]
            digest.update(chunk)
            staging.write(chunk)
        if not size or not header.startswith(b"%PDF-"):
            raise InvalidDocumentError("Upload does not have a PDF header.")
        storage_name = ("benchmark-" if benchmark else "") + uuid4().hex + ".pdf"
        path = settings.upload_dir / storage_name
        staging.seek(0)
        created = False
        try:
            with path.open("xb") as target:
                created = True
                while chunk := staging.read(1024 * 1024):
                    target.write(chunk)
        except OSError:
            if created:
                path.unlink(missing_ok=True)
            raise
    return OCRDocument(document_id=digest.hexdigest(), filename=filename, path=path,
                        source="upload:" + storage_name,
                        source_metadata={"sha256": digest.hexdigest(), "size_bytes": size,
                                         "media_type": "application/pdf", "original_filename": filename,
                                         "storage_name": storage_name})


class OCRService:
    def __init__(self, settings: Settings, providers: dict[str, OCRProvider] | None = None):
        self.settings = settings
        self.providers = providers if providers is not None else {name: cls(settings) for name, cls in PROVIDER_TYPES.items()}
        # One process, one inference at a time: model memory and CLI settings stay predictable.
        self._lock = RLock()
        self.inference_checks = {}
        self._loaded_cache_identity = {}

    def select(self, provider: str | None = None) -> OCRProvider:
        name = provider if provider is not None else self.settings.provider
        if name not in self.providers:
            raise UnsupportedProviderError(f"Unsupported provider: {name}")
        return self.providers[name]

    def health(self) -> list:
        return [provider.health() for provider in self.providers.values()]

    def extract(self, document: OCRDocument, provider: str | None = None, persist_result: bool = True,
                force_reprocess: bool = False) -> OCRResult:
        """Share successful OCR across processing and scoring; references never enter the key.

        Content-addressed PDFs are verified against their original bytes. Synthetic
        provider-test inputs without a SHA-256 identity use the uncached lifecycle path.
        persist_result controls legacy exports; cache_enabled controls the shared cache.
        """
        selected = self.select(provider)
        if not self.settings.cache_enabled or not re.fullmatch(r"[0-9a-f]{64}", document.document_id):
            result = self._extract(document, provider, persist_result)
            result.provider_metadata["cache"] = {"status": "disabled", "state": "completed"}
            return result
        started = time.monotonic()
        requested_at = time.time()
        try:
            if file_digest(document.path) != document.document_id:
                raise InvalidDocumentError("Document bytes changed after upload; upload the document again.")
            identity = fingerprint(self.settings, selected)
            cache = ResultCache(self.settings.output_dir, self.settings.cache_wait_seconds)

            def compute():
                with self._lock:
                    # Settings/assets can change while this request waits behind another job.
                    if fingerprint(self.settings, selected) != identity:
                        raise ExtractionError("Model/configuration changed while queued; retry the request.")
                    token = digest_json(identity)
                    from OCR.providers.common import LocalProvider
                    if isinstance(selected, LocalProvider) and self._loaded_cache_identity.get(identity["provider"]) != token:
                        selected.unload()
                        selected._state("uninitialized")
                    result = self._extract(document, provider, persist_result=False)
                    self._loaded_cache_identity[identity["provider"]] = token
                    if fingerprint(self.settings, selected) != identity:
                        raise ExtractionError("Model/configuration changed during OCR; retry the request.")
                    return result

            result = cache.run(document, identity, compute, force=force_reprocess, requested_at=requested_at)
            result.provider_metadata["cache"]["request_seconds"] = time.monotonic() - started
            log_event(logger, "ocr_cache", provider=identity["provider"],
                      status=result.provider_metadata["cache"]["status"], document_id=document.document_id)
            return result
        except (OSError, sqlite3.Error) as exc:
            raise ExtractionError("OCR cache storage is unavailable.",
                                  public_message="OCR cache storage is unavailable. Check output directory permissions and free disk space, then retry.") from exc

    def _extract(self, document: OCRDocument, provider: str | None = None, persist_result: bool = True) -> OCRResult:
        selected = self.select(provider)
        with self._lock:
            started = time.monotonic()
            provider_name = selected.health().provider
            self.inference_checks[provider_name] = {'state': 'Not tested', 'detail': 'Inference in progress; no completed smoke-test evidence for this request.'}
            log_event(logger, 'extraction_started', provider=provider_name)
            # Keep only the selected heavy pipeline resident on small-memory PCs.
            for other in self.providers.values():
                if other is not selected:
                    try:
                        other.unload()
                    except Exception as exc:
                        log_event(logger, "provider_unload_failed", level=logging.ERROR,
                                  provider=other.health().provider, error_type=type(exc).__name__)
                        raise ExtractionError("Could not release previous model resources.", provider=provider_name) from exc
            phase = 'initialization'
            try:
                log_event(logger, 'provider_initializing', provider=provider_name)
                selected.initialize()
                initialized = time.monotonic()
                phase = "inference"
                log_event(logger, 'provider_ready', provider=provider_name)
                result = selected.extract(document)
                finished = time.monotonic()
                result.provider_metadata.update(initialization_seconds=initialized-started, inference_seconds=finished-initialized, duration_seconds=finished-started)
            except OCRError as exc:
                self.inference_checks[provider_name] = {'state': 'Initialization failed' if phase == 'initialization' else 'Inference failed', 'detail': phase.capitalize() + ' failed; verify runtime and local model assets.'}
                log_event(logger, 'extraction_failed', level=logging.WARNING, provider=provider_name, code=exc.code)
                raise
            except Exception as exc:
                self.inference_checks[provider_name] = {'state': 'Initialization failed' if phase == 'initialization' else 'Inference failed', 'detail': phase.capitalize() + ' failed; verify runtime compatibility.'}
                log_event(logger, 'extraction_failed', level=logging.ERROR, provider=provider_name, error_type=type(exc).__name__)
                raise ExtractionError("Provider execution failed.", provider=provider_name) from exc
            self.inference_checks[provider_name] = {"state": "Inference failed", "detail": "Provider output validation has not completed."}
            if (result.document_id != document.document_id or result.filename != document.filename
                    or result.source != document.source or result.source_metadata != document.source_metadata
                    or result.provider != selected.health().provider):
                raise ExtractionError("Provider returned inconsistent document provenance.")
            try:
                result = OCRResult.model_validate(result.model_dump())
            except ValueError as exc:
                raise ExtractionError("Provider returned invalid normalized provenance.") from exc
            complete = not result.errors and not any(p.errors for p in result.pages or [])
            self.inference_checks[provider_name] = {"state": "Ready" if complete else "Inference failed", "detail": "Actual extraction succeeded in this process." if complete else "Inference returned partial errors."}
            # Filenames never incorporate caller-controlled identities or provider output.
            try:
                if not persist_result:
                    return result
                self.settings.output_dir.mkdir(parents=True, exist_ok=True)
                destination = self.settings.output_dir / f"{uuid4().hex}.json"
                with destination.open("x", encoding="utf-8") as output:
                    output.write(result.model_dump_json(indent=2))
            except OSError as exc:
                raise ExtractionError("Could not persist the normalized OCR result.") from exc
            log_event(logger, 'extraction_completed', provider=provider_name, duration_seconds=round(time.monotonic() - started, 3))
            return result
