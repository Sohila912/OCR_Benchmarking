"""Provider selection, serialized local inference, and safe PDF ingestion."""

import hashlib
import logging
import tempfile
from pathlib import Path, PurePosixPath, PureWindowsPath
from threading import RLock
from uuid import uuid4

from OCR.config import Settings
from OCR.errors import OCRError, ExtractionError, InvalidDocumentError, UnsupportedProviderError, UploadTooLargeError
from OCR.providers.base import OCRDocument, OCRProvider
from OCR.providers.docling import DoclingProvider
from OCR.providers.paddle_vl import PaddleVLProvider
from OCR.providers.tesseract import TesseractProvider
from OCR.schemas import OCRResult

PROVIDER_TYPES = {"paddle_vl": PaddleVLProvider, "docling": DoclingProvider, "tesseract": TesseractProvider}
logger = logging.getLogger(__name__)


def validate_upload_name(filename: str | None) -> str:
    if (not filename or filename != filename.strip() or "\x00" in filename
            or any(ord(c) < 32 for c in filename) or ":" in filename
            or PureWindowsPath(filename).name != filename or PurePosixPath(filename).name != filename
            or Path(filename).suffix.lower() != ".pdf"):
        raise InvalidDocumentError("Upload a PDF with a plain filename, without directory components.")
    return filename


def ingest_pdf(stream, filename: str | None, settings: Settings) -> OCRDocument:
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
        storage_name = uuid4().hex + ".pdf"
        path = settings.upload_dir / storage_name
        staging.seek(0)
        with path.open("xb") as target:
            while chunk := staging.read(1024 * 1024):
                target.write(chunk)
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

    def select(self, provider: str | None = None) -> OCRProvider:
        name = provider if provider is not None else self.settings.provider
        if name not in self.providers:
            raise UnsupportedProviderError(f"Unsupported provider: {name}")
        return self.providers[name]

    def health(self) -> list:
        return [provider.health() for provider in self.providers.values()]

    def extract(self, document: OCRDocument, provider: str | None = None) -> OCRResult:
        selected = self.select(provider)
        with self._lock:
            try:
                selected.initialize()
                result = selected.extract(document)
            except OCRError:
                raise
            except Exception as exc:
                logger.exception("Unexpected provider failure")
                raise ExtractionError("Provider execution failed.", provider=selected.health().provider) from exc
            if (result.document_id != document.document_id or result.filename != document.filename
                    or result.source != document.source or result.source_metadata != document.source_metadata
                    or result.provider != selected.health().provider):
                raise ExtractionError("Provider returned inconsistent document provenance.")
            try:
                result = OCRResult.model_validate(result.model_dump())
            except ValueError as exc:
                raise ExtractionError("Provider returned invalid normalized provenance.") from exc
            # Filenames never incorporate caller-controlled identities or provider output.
            try:
                self.settings.output_dir.mkdir(parents=True, exist_ok=True)
                destination = self.settings.output_dir / f"{uuid4().hex}.json"
                with destination.open("x", encoding="utf-8") as output:
                    output.write(result.model_dump_json(indent=2))
            except OSError as exc:
                raise ExtractionError("Could not persist the normalized OCR result.") from exc
            return result
