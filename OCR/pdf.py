"""On-demand PDF inspection and single-page rendering for OCR adapters."""

from __future__ import annotations

from pathlib import Path
import shutil
from types import ModuleType
from typing import TYPE_CHECKING

from OCR.errors import (
    ExtractionError,
    InvalidDocumentError,
    ProviderInitializationError,
)

if TYPE_CHECKING:
    from PIL.Image import Image


def _validate_pdf_path(path: Path) -> Path:
    path = Path(path)
    try:
        if not path.is_file():
            raise InvalidDocumentError(f"PDF file does not exist: {path}")
    except OSError as exc:
        raise InvalidDocumentError(f"Cannot access PDF file: {path}") from exc
    if path.suffix.lower() != ".pdf":
        raise InvalidDocumentError(f"Expected a PDF file: {path}")
    return path


def _load_backend() -> tuple[ModuleType, ModuleType]:
    try:
        import pdf2image
        from pdf2image import exceptions
    except (ImportError, OSError) as exc:
        raise ProviderInitializationError(
            "PDF rendering requires an available pdf2image installation and Pillow."
        ) from exc
    return pdf2image, exceptions


def _require_positive_integer(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer.")


def require_pdf_renderer(poppler_path: Path | None = None) -> None:
    """Check optional imports and executable discovery without opening a PDF."""
    _load_backend()
    for executable in ("pdfinfo", "pdftoppm"):
        if shutil.which(executable, path=str(poppler_path) if poppler_path is not None else None) is None:
            raise ProviderInitializationError(f"Poppler {executable} is unavailable; configure PATH or OCR_POPPLER_PATH.")


def get_pdf_page_count(
    path: Path,
    *,
    poppler_path: Path | None = None,
    timeout: int = 60,
) -> int:
    """Inspect a PDF using pdfinfo; timeout is in seconds.

    No dependency import or subprocess occurs until this function is called.
    Without a Poppler directory, pdf2image uses executable discovery on PATH.
    """
    _require_positive_integer("timeout", timeout)
    path = _validate_pdf_path(path)
    backend, errors = _load_backend()
    try:
        info = backend.pdfinfo_from_path(
            str(path),
            poppler_path=str(poppler_path) if poppler_path is not None else None,
            timeout=timeout,
        )
    except (errors.PDFInfoNotInstalledError, errors.PopplerNotInstalledError, FileNotFoundError) as exc:
        raise ProviderInitializationError(
            "Poppler pdfinfo is unavailable; check PATH or OCR_POPPLER_PATH."
        ) from exc
    except (errors.PDFPageCountError, errors.PDFSyntaxError) as exc:
        raise InvalidDocumentError(
            f"Cannot inspect PDF; it may be unreadable, invalid, or password-protected: {path}"
        ) from exc
    except errors.PDFPopplerTimeoutError as exc:
        raise ExtractionError(f"PDF inspection timed out after {timeout} seconds.") from exc
    except Exception as exc:
        raise ExtractionError(f"PDF inspection failed: {exc}") from exc

    count = info.get("Pages")
    if isinstance(count, bool) or not isinstance(count, int) or count <= 0:
        raise InvalidDocumentError(f"PDF did not report a positive page count: {path}")
    return count


def render_pdf_page(
    path: Path,
    page_number: int,
    *,
    dpi: int = 300,
    poppler_path: Path | None = None,
    timeout: int = 60,
) -> Image:
    """Render one one-based page in color, without resizing or OCR.

    The caller owns the returned Pillow image and must close it after use.
    Timeout is in seconds per backend operation. No output directory or
    temporary image file is requested; the rendered image is held in memory.
    """
    _require_positive_integer("page_number", page_number)
    _require_positive_integer("dpi", dpi)
    _require_positive_integer("timeout", timeout)
    path = _validate_pdf_path(path)
    backend, errors = _load_backend()
    try:
        pages = backend.convert_from_path(
            str(path),
            first_page=page_number,
            last_page=page_number,
            dpi=dpi,
            poppler_path=str(poppler_path) if poppler_path is not None else None,
            timeout=timeout,
            grayscale=False,
            thread_count=1,
        )
    except (errors.PDFInfoNotInstalledError, errors.PopplerNotInstalledError, FileNotFoundError) as exc:
        raise ProviderInitializationError(
            "Poppler rendering tools are unavailable; check PATH or OCR_POPPLER_PATH."
        ) from exc
    except (errors.PDFPageCountError, errors.PDFSyntaxError) as exc:
        raise InvalidDocumentError(
            f"Cannot render PDF; it may be unreadable, invalid, or password-protected: {path}"
        ) from exc
    except errors.PDFPopplerTimeoutError as exc:
        raise ExtractionError(
            f"Rendering page {page_number} timed out after {timeout} seconds."
        ) from exc
    except Exception as exc:
        raise ExtractionError(f"Rendering page {page_number} failed: {exc}") from exc

    if len(pages) != 1:
        for image in pages:
            image.close()
        raise ExtractionError(
            f"Expected one rendered image for page {page_number}, received {len(pages)}."
        )
    return pages[0]
