"""InkLight OCR on frozen images, preserving the native reading and line boxes."""

import json
import subprocess
import sys

from OCR.schemas import BoundingBox, OCRBlock, OCRPage, OCRResult

from .base import BenchmarkAdapter, RawOutput
from benchmark_suite.runners.schemas import Prediction


class InkLightAdapter(BenchmarkAdapter):
    def __init__(self, spec):
        self.spec = spec
        self.options = None

    def initialize(self, config):
        if not config.adapter_options.get("model_dir"):
            raise ValueError("InkLight requires the pinned local OCR weights directory")
        self.options = config.adapter_options

    def predict(self, document):
        request = dict(path=str(document.path), options=self.options,
                       revision=self.spec.native_versions["inklight_build"])
        reply = subprocess.run([sys.executable, "-B", "-m", "benchmark_suite.scripts.inklight_worker"],
                               input=json.dumps(request).encode("utf-8"), capture_output=True,
                               timeout=self.options["timeout_seconds"])
        if reply.returncode:
            detail = reply.stderr.decode("utf-8", errors="replace")[-1500:]
            raise RuntimeError(f"InkLight worker exited with {reply.returncode}: {detail}")
        return RawOutput(reply.stdout, "application/json")

    def normalize_output(self, raw, document):
        from inklight.frames import original_size, to_original
        from inklight.schemas import DocumentContent

        reading = DocumentContent.model_validate_json(raw.data)
        if reading.total_pages != 1 or len(reading.pages) != 1:
            raise ValueError("Expected one image page in the InkLight reading")
        page = reading.pages[0]
        if page.source == "error":
            raise RuntimeError(page.note or "InkLight reported a page error")
        width, height = original_size(page.rotation, page.width, page.height)
        if (width, height) != (document.source_metadata["width"], document.source_metadata["height"]):
            raise ValueError("InkLight page dimensions differ from the original image")
        blocks = []
        for index, line in enumerate(page.lines):
            bounds = None
            if line.bbox is not None:
                left, top, right, bottom = to_original(line.bbox, page.rotation, page.width, page.height)
                bounds = BoundingBox(x_min=left, y_min=top, x_max=right, y_max=bottom,
                                     units="pixels", origin="top_left")
            blocks.append(OCRBlock(block_id=f"line-{index}", block_type="text", text=line.text,
                                   reading_order=index, confidence=line.conf, bounding_box=bounds))
        result = OCRResult(document_id=document.document_id, filename=document.filename,
                           source=document.source, source_metadata=document.source_metadata,
                           provider="inklight", model_name="InkLight / Indra OCR",
                           model_version=self.spec.model_revision, language=document.source_metadata["language"],
                           text=page.text, markdown=page.markdown,
                           pages=[OCRPage(page_number=1, width=width, height=height, dimension_units="pixels",
                                          text=page.text, markdown=page.markdown, blocks=blocks)],
                           provider_metadata={"rotation": page.rotation, "page_source": page.source,
                                              "structure_enabled": False})
        return Prediction(result=result, text_format="plain",
                          coordinate_notes="Native OCR line order; upright boxes mapped to original-image pixels.")

    def get_metadata(self):
        return self.spec

    def get_capabilities(self):
        return self.spec.capabilities

    def cleanup(self):
        self.options = None


def create_adapter(spec):
    return InkLightAdapter(spec)
