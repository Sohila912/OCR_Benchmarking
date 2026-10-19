"""Local PaddleOCR-VL-1.6 adapter, distinct from the conventional legacy runner."""

import json
import logging
import os

from OCR.errors import ExtractionError, InvalidDocumentError, ProviderInitializationError, ProviderResourceError
from OCR.resources import paddle_memory_issue
from OCR.pdf import get_pdf_page_count, render_pdf_page, require_pdf_renderer
from OCR.providers.base import OCRDocument
from OCR.providers.common import LocalProvider, package_version, require_assets
from OCR.schemas import BoundingBox, OCRBlock, OCRIssue, OCRPage, OCRResult
from OCR.logging_utils import log_event


def page_from_paddle(result, number: int) -> OCRPage:
    payload = result.json
    if isinstance(payload, str):
        payload = json.loads(payload)
    data = payload.get("res", payload)
    raw_blocks = data.get("parsing_res_list")
    blocks = None if raw_blocks is None else []
    for index, raw in enumerate(raw_blocks or []):
        coords = raw.get("block_bbox")
        box = None if coords is None else BoundingBox(
            x_min=coords[0], y_min=coords[1], x_max=coords[2], y_max=coords[3], units="pixels", origin="top_left")
        order = raw.get("block_order")
        blocks.append(OCRBlock(
            block_id=f"p{number}-block{index}", block_type=raw.get("block_label"), text=raw.get("block_content"),
            reading_order=order - 1 if order is not None else None, bounding_box=box,
            provider_metadata={"source_index": index, **raw},
        ))
    markdown = result.markdown.get("markdown_texts")
    page = OCRPage(page_number=number,
                   text="\n\n".join(b.text for b in blocks if b.text is not None) if blocks is not None else None,
                   markdown=markdown, width=data.get("width"), height=data.get("height"),
                   dimension_units="pixels" if data.get("width") or data.get("height") else None, blocks=blocks)
    if blocks is None:
        page.warnings.append(OCRIssue(code="blocks_unavailable", message="Provider supplied no parsing blocks.", page_number=number))
    return page


class PaddleVLProvider(LocalProvider):
    provider_id = "paddle_vl"

    def initialize(self) -> None:
        if self.health().status == "ready":
            return
        issue = paddle_memory_issue(self.settings)
        if issue:
            self._state("unavailable", issue)
            raise ProviderResourceError(issue, provider=self.provider_id, public_message=issue)
        try:
            vl = require_assets(self.settings.paddle_vl_model_dir, "OCR_PADDLE_VL_MODEL_DIR")
            layout = require_assets(self.settings.paddle_layout_model_dir, "OCR_PADDLE_LAYOUT_MODEL_DIR")
            require_pdf_renderer(self.settings.poppler_path)
            # All enabled models use explicit local directories. Extra preprocessing models are disabled.
            os.environ["HF_HUB_OFFLINE"] = "1"
            os.environ["TRANSFORMERS_OFFLINE"] = "1"
            os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
            from paddleocr import PaddleOCRVL

            if self.settings.paddle_device.lower().startswith("gpu"):
                import paddle
                if not paddle.is_compiled_with_cuda():
                    message = "PaddleOCR-VL is configured for GPU, but this image contains the CPU Paddle runtime. Select OCR_PADDLE_DEVICE=cpu or install a compatible GPU runtime on a GPU-enabled host."
                    raise ProviderResourceError(message, provider=self.provider_id, public_message=message)
            self._pipeline = PaddleOCRVL(
                pipeline_version="v1.6", vl_rec_backend="native",
                vl_rec_model_name="PaddleOCR-VL-1.6-0.9B", vl_rec_model_dir=str(vl),
                layout_detection_model_name="PP-DocLayoutV3", layout_detection_model_dir=str(layout),
                device=self.settings.paddle_device, use_doc_orientation_classify=False, use_doc_unwarping=False,
                use_layout_detection=True, use_chart_recognition=False, use_seal_recognition=False,
                use_ocr_for_image_block=False, use_queues=False, format_block_content=False,
            )
        except ProviderResourceError:
            self._state("unavailable", "Configured GPU runtime is unavailable.")
            raise
        except Exception as exc:
            if isinstance(exc, ImportError):
                message = "PaddleOCR-VL dependencies are missing or incompatible. Rebuild the API with OCR_INSTALL_LOCAL_MODELS=true and verify paddlepaddle/paddleocr versions."
            elif isinstance(exc, FileNotFoundError):
                message = "PaddleOCR-VL model assets or PDF renderer are missing. Verify both OCR_PADDLE_VL_MODEL_DIR and OCR_PADDLE_LAYOUT_MODEL_DIR mounts and the Poppler installation."
            else:
                message = "PaddleOCR-VL initialization failed. Verify complete local VL/layout checkpoints, CPU/GPU runtime compatibility and available memory in Provider Status."
            self._state("unavailable", message)
            raise ProviderInitializationError(str(exc), provider=self.provider_id, public_message=message) from exc
        self._state("ready")

    def extract(self, document: OCRDocument) -> OCRResult:
        self._require_ready(document)
        import numpy as np

        settings = self.settings
        count = get_pdf_page_count(document.path, poppler_path=settings.poppler_path, timeout=settings.operation_timeout)
        if count > settings.max_pages:
            raise InvalidDocumentError("PDF exceeds the configured page limit.", provider=self.provider_id)
        pages = []
        for number in range(1, count + 1):
            image = None
            try:
                image = render_pdf_page(document.path, number, dpi=settings.pdf_dpi,
                                        poppler_path=settings.poppler_path, timeout=settings.operation_timeout)
                # Paddle's ndarray input uses BGR; no resizing, grayscale, rotation or unwarping.
                predictions = list(self._pipeline.predict(np.asarray(image)[:, :, ::-1].copy()))
                if len(predictions) != 1:
                    raise ValueError("Expected one PaddleOCR-VL result for the rendered page.")
                pages.append(page_from_paddle(predictions[0], number))
            except Exception as exc:
                log_event(logging.getLogger(__name__), "page_failed", level=logging.WARNING,
                          provider=self.provider_id, page_number=number, error_type=type(exc).__name__)
                pages.append(OCRPage(page_number=number, errors=[OCRIssue(
                    code="page_extraction_failed", message=f"PaddleOCR-VL page extraction failed ({type(exc).__name__}). Check runtime/model compatibility and available inference memory.",
                    page_number=number)]))
            finally:
                if image is not None:
                    image.close()
        if all(p.errors for p in pages):
            raise ExtractionError("PaddleOCR-VL failed on every page.", provider=self.provider_id,
                                  public_message="PaddleOCR-VL could not extract any page. " + pages[0].errors[0].message)
        return self._result(document, pages, model_name="PaddleOCR-VL-1.6-0.9B", model_version=settings.paddle_model_revision,
                            provider_metadata={"package_version": package_version("paddleocr"),
                                               "pipeline_version": "v1.6", "layout_model": "PP-DocLayoutV3",
                                               "render_dpi": settings.pdf_dpi, "text_assembly": "provider block content; may contain markup"})
