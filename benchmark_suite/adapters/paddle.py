"""Standard PaddleOCR uses the shared bounded subprocess lifecycle on D:."""

import json

from OCR.schemas import BoundingBox, OCRBlock, OCRPage, OCRResult
from benchmark_suite.runners.schemas import Prediction
from .granite_docling import GraniteDoclingAdapter


class PaddleAdapter(GraniteDoclingAdapter):
    worker_model = "paddle"

    def normalize_output(self, raw, document):
        payload = json.loads(raw.data)
        data = payload["prediction"].get("res", payload["prediction"])
        blocks = []
        for index, (text, confidence, polygon) in enumerate(zip(
                data["rec_texts"], data["rec_scores"], data["rec_polys"], strict=True)):
            if len(polygon) != 4 or any(len(point) != 2 for point in polygon):
                raise ValueError("Expected native quadrilateral line geometry")
            xs, ys = zip(*polygon)
            blocks.append(OCRBlock(block_id=f"line-{index}", block_type="text", text=text,
                confidence=confidence, reading_order=index, bounding_box=BoundingBox(
                    x_min=min(xs), y_min=min(ys), x_max=max(xs), y_max=max(ys),
                    units="pixels", origin="top_left"), provider_metadata={"native_polygon": polygon}))
        content = "\n".join(block.text for block in blocks)
        page = OCRPage(page_number=1, width=document.source_metadata["width"],
            height=document.source_metadata["height"], dimension_units="pixels", text=content, blocks=blocks)
        result = OCRResult(document_id=document.document_id, filename=document.filename,
            source=document.source, source_metadata=document.source_metadata, provider="paddle",
            model_name="PP-OCRv5 mobile detection + language-specific mobile recognition",
            model_version=self.spec.model_revision, text=content, pages=[page],
            provider_metadata={"worker_result": payload["worker_result"],
                "native_output_directory": payload["native_output_directory"],
                "line_order": "native pipeline emission order; no truth-based sorting"})
        return Prediction(result=result, text_format="plain", coordinate_notes=
            "Original-image pixel envelopes of native quadrilateral text lines; native confidence/order; no semantic layout/table claims")


def create_adapter(spec):
    return PaddleAdapter(spec)
