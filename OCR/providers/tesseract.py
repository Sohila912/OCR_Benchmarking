"""Tesseract 5 CLI adapter; TSV words retain their source hierarchy and scores."""

import csv
import io
import logging
import re
import subprocess
import tempfile
from pathlib import Path

from OCR.errors import ExtractionError, InvalidDocumentError, ProviderInitializationError
from OCR.pdf import get_pdf_page_count, render_pdf_page, require_pdf_renderer
from OCR.providers.base import OCRDocument
from OCR.providers.common import LocalProvider
from OCR.schemas import BoundingBox, OCRBlock, OCRIssue, OCRPage, OCRResult


def probe_tesseract(command: str, languages: str, timeout: int) -> str:
    version = subprocess.run([command, "--version"], capture_output=True, text=True,
                             encoding="utf-8", errors="replace", check=True, timeout=timeout)
    identity = (version.stdout or version.stderr).splitlines()[0]
    if not re.search(r"tesseract\s+v?5\.", identity, re.IGNORECASE):
        raise RuntimeError("The selected adapter requires Tesseract 5.")
    result = subprocess.run([command, "--list-langs"], capture_output=True, text=True,
                            encoding="utf-8", errors="replace", check=True, timeout=timeout)
    available = set((result.stdout + "\n" + result.stderr).splitlines())
    missing = set(languages.split("+")) - available
    if missing:
        raise RuntimeError("Missing Tesseract language packs: " + ", ".join(sorted(missing)))
    return identity


def page_from_tsv(tsv: str, number: int, width: int, height: int) -> OCRPage:
    reader = csv.DictReader(io.StringIO(tsv), delimiter="\t", quoting=csv.QUOTE_NONE)
    required = {"level", "text", "conf", "left", "top", "width", "height", "block_num", "par_num", "line_num", "word_num"}
    if not required.issubset(reader.fieldnames or []):
        raise ValueError("Tesseract returned an invalid TSV header.")
    blocks, lines = [], {}
    for row_index, row in enumerate(reader):
        if row["level"] != "5" or not row["text"].strip():
            continue
        left, top, w, h = (int(row[k]) for k in ("left", "top", "width", "height"))
        raw_score = float(row["conf"])
        hierarchy = {k: int(row[k]) for k in ("block_num", "par_num", "line_num", "word_num")}
        key = tuple(hierarchy[k] for k in ("block_num", "par_num", "line_num"))
        lines.setdefault(key, []).append(row["text"])
        blocks.append(OCRBlock(
            block_id=f"p{number}-word{row_index}", block_type="word", text=row["text"],
            confidence=raw_score / 100 if 0 <= raw_score <= 100 else None,
            bounding_box=BoundingBox(x_min=left, y_min=top, x_max=left+w, y_max=top+h,
                                    units="pixels", origin="top_left"),
            provider_metadata={"tsv_row": row_index, **hierarchy, "confidence_raw": raw_score,
                               "confidence_scale": "0..100; -1 means unavailable"},
        ))
    return OCRPage(page_number=number, text="\n".join(" ".join(words) for words in lines.values()),
                   width=width, height=height, dimension_units="pixels", blocks=blocks)


class TesseractProvider(LocalProvider):
    provider_id = "tesseract"

    def initialize(self) -> None:
        if self.health().status == "ready":
            return
        try:
            require_pdf_renderer(self.settings.poppler_path)
            self._version = probe_tesseract(self.settings.tesseract_cmd, self.settings.tesseract_lang,
                                            self.settings.operation_timeout)
        except Exception as exc:
            self._state("unavailable", "Initialization failed; check server logs and configured dependencies.")
            raise ProviderInitializationError(str(exc), provider=self.provider_id) from exc
        self._state("ready")

    def extract(self, document: OCRDocument) -> OCRResult:
        self._require_ready(document)
        settings = self.settings
        count = get_pdf_page_count(document.path, poppler_path=settings.poppler_path,
                                   timeout=settings.operation_timeout)
        if count > settings.max_pages:
            raise InvalidDocumentError("PDF exceeds the configured page limit.", provider=self.provider_id)
        settings.temp_dir.mkdir(parents=True, exist_ok=True)
        pages = []
        for number in range(1, count + 1):
            image = None
            try:
                image = render_pdf_page(document.path, number, dpi=settings.pdf_dpi,
                                        poppler_path=settings.poppler_path, timeout=settings.operation_timeout)
                with tempfile.TemporaryDirectory(dir=settings.temp_dir, prefix="tesseract-") as directory:
                    image_path = Path(directory) / "page.png"
                    image.save(image_path, "PNG")
                    output = subprocess.run(
                        [settings.tesseract_cmd, str(image_path), "stdout", "-l", settings.tesseract_lang, "tsv"],
                        capture_output=True, text=True, encoding="utf-8", errors="replace", check=True,
                        timeout=settings.operation_timeout,
                    )
                pages.append(page_from_tsv(output.stdout, number, image.width, image.height))
            except Exception as exc:
                logging.getLogger(__name__).warning("Tesseract page %s failed", number, exc_info=True)
                pages.append(OCRPage(page_number=number, errors=[OCRIssue(
                    code="page_extraction_failed", message=f"Page extraction failed ({type(exc).__name__}).",
                    page_number=number)]))
            finally:
                if image is not None:
                    image.close()
        if all(p.errors for p in pages):
            raise ExtractionError("Tesseract failed on every page.", provider=self.provider_id)
        return self._result(document, pages, model_name="Tesseract", model_version=self._version,
                            provider_metadata={"recognition_languages": settings.tesseract_lang.split("+"),
                                               "render_dpi": settings.pdf_dpi, "text_assembly": "TSV words grouped by line"})
