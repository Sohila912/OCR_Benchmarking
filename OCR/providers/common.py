"""Small lifecycle and result helpers shared by the local adapters."""

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from OCR.config import Settings
from OCR.errors import InvalidDocumentError, ProviderNotReadyError
from OCR.providers.base import OCRDocument, OCRProvider, ProviderHealth
from OCR.schemas import OCRPage, OCRResult, attach_text_provenance


def package_version(name: str) -> str | None:
    try:
        return version(name)
    except PackageNotFoundError:
        return None


def require_assets(path: Path | None, setting: str) -> Path:
    if path is None or not path.is_dir() or not any(path.iterdir()):
        raise FileNotFoundError(f"Set {setting} to an existing, populated local model directory.")
    return path


class LocalProvider(OCRProvider):
    provider_id: str

    def __init__(self, settings: Settings):
        self.settings = settings
        self._health = ProviderHealth(provider=self.provider_id, status="uninitialized")

    def health(self) -> ProviderHealth:
        return self._health

    def _state(self, status: str, detail: str | None = None) -> None:
        self._health = ProviderHealth(provider=self.provider_id, status=status, detail=detail)

    def _require_ready(self, document: OCRDocument) -> None:
        if self._health.status != "ready":
            raise ProviderNotReadyError("Initialize the provider before extraction.", provider=self.provider_id)
        try:
            if document.path.suffix.lower() != ".pdf" or not document.path.is_file():
                raise InvalidDocumentError("Input must be an existing PDF.", provider=self.provider_id)
            if document.path.stat().st_size > self.settings.max_upload_bytes:
                raise InvalidDocumentError("PDF exceeds the configured size limit.", provider=self.provider_id)
        except OSError as exc:
            raise InvalidDocumentError("Cannot access the PDF.", provider=self.provider_id) from exc

    def _result(self, document: OCRDocument, pages: list[OCRPage], **metadata) -> OCRResult:
        return attach_text_provenance(OCRResult(
            document_id=document.document_id, filename=document.filename, source=document.source,
            source_metadata=document.source_metadata,
            provider=self.provider_id, pages=pages,
            text="\n\n".join(p.text for p in pages if p.text is not None),
            markdown=("\n\n".join(p.markdown for p in pages if p.markdown is not None)
                      if any(p.markdown is not None for p in pages) else None),
            warnings=[issue for p in pages for issue in p.warnings],
            errors=[issue for p in pages for issue in p.errors], **metadata,
        ))
