"""Explicit OCR failures, separate from extracted document content."""

from __future__ import annotations


class OCRError(Exception):
    """Base application error with a stable code and optional provider name."""

    code = "ocr_error"

    def __init__(self, message: str, *, provider: str | None = None, public_message: str | None = None) -> None:
        super().__init__(message)
        self.provider = provider
        self.public_message = public_message


class ProviderInitializationError(OCRError):
    """A dependency, executable, model asset, or initialization step failed."""

    code = "provider_initialization_failed"


class ProviderNotReadyError(OCRError):
    """Extraction was requested before successful provider initialization."""

    code = "provider_not_ready"


class InvalidDocumentError(OCRError):
    """The input is missing, unreadable, or unsupported."""

    code = "invalid_document"


class ExtractionError(OCRError):
    """A fatal failure prevented extraction from the document."""

    code = "extraction_failed"


class UnsupportedProviderError(OCRError):
    code = "unsupported_provider"


class UploadTooLargeError(InvalidDocumentError):
    code = "upload_too_large"


class ProviderResourceError(ProviderInitializationError):
    """Known hardware capacity cannot safely initialize this provider."""

    code = "provider_resources_unavailable"


def public_error_message(exc: OCRError) -> str:
    """Expose only explicitly safe diagnostics, never raw runtime exceptions."""
    if exc.public_message:
        return exc.public_message
    if isinstance(exc, (InvalidDocumentError, UnsupportedProviderError)):
        return str(exc)
    name = {"paddle_vl": "PaddleOCR-VL", "docling": "Docling", "tesseract": "Tesseract",
            "qwen_ollama": "Qwen/Ollama"}.get(exc.provider, "OCR provider")
    phase = "initialization" if isinstance(exc, (ProviderInitializationError, ProviderNotReadyError)) else "extraction"
    return f"{name} {phase} failed. Open Settings / Provider Status for runtime and model diagnostics."
