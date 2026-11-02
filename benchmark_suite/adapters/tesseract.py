"""Native Tesseract baseline on frozen images, with original TSV retained."""

import json
import os
import subprocess

from OCR.providers.tesseract import page_from_tsv
from OCR.schemas import BoundingBox, OCRBlock, OCRResult

from .base import BenchmarkAdapter, RawOutput
from benchmark_suite.runners.schemas import Prediction


class TesseractAdapter(BenchmarkAdapter):
    def __init__(self, spec):
        self.spec = spec
        self.options = None

    def initialize(self, config):
        self.options = dict(config.adapter_options)
        self.environment = dict(os.environ, OMP_THREAD_LIMIT="1")
        version = subprocess.run(
            [self.options["executable"], "--version"], capture_output=True,
            check=True, timeout=15, env=self.environment,
        ).stdout.decode("utf-8", errors="replace").splitlines()[0]
        if version != self.spec.native_versions["tesseract"]:
            raise RuntimeError("Native Tesseract version differs from the pinned spec")
        languages = subprocess.run(
            [self.options["executable"], "--tessdata-dir", self.options["tessdata"], "--list-langs"],
            capture_output=True, check=True, timeout=15, env=self.environment,
        ).stdout.decode("utf-8").splitlines()
        if not {"eng", "ara"}.issubset(languages):
            raise RuntimeError("Pinned English/Arabic language assets are missing")

    def predict(self, document):
        if self.options is None:
            raise RuntimeError("Adapter is not initialized")
        language = {"en": "eng", "ar": "ara"}[document.source_metadata["language"]]
        command = [
            self.options["executable"], str(document.path), "stdout",
            "--tessdata-dir", self.options["tessdata"], "-l", language,
            "--oem", "1", "--psm", "3", "--dpi", "300", "-c", "tessedit_create_tsv=1",
        ]
        process = subprocess.run(command, capture_output=True, check=True,
                                 timeout=self.options["timeout_seconds"], env=self.environment)
        return RawOutput(json.dumps({
            "tsv": process.stdout.decode("utf-8"),
            "stderr": process.stderr.decode("utf-8", errors="replace"),
            "language": language,
        }, ensure_ascii=False).encode("utf-8"), "application/json")

    def normalize_output(self, raw, document):
        output = json.loads(raw.data)
        page = page_from_tsv(output["tsv"], 1, document.source_metadata["width"],
                             document.source_metadata["height"])
        # Preserve native line order, without reference-informed segmentation.
        lines = {}
        for word in page.blocks:
            key = tuple(word.provider_metadata[k] for k in ("block_num", "par_num", "line_num"))
            lines.setdefault(key, []).append(word)
        blocks = []
        for index, (key, words) in enumerate(lines.items()):
            bounds = [word.bounding_box for word in words]
            blocks.append(OCRBlock(
                block_id=f"line-{index}", block_type="text",
                text=" ".join(word.text for word in words), reading_order=index,
                bounding_box=BoundingBox(
                    x_min=min(b.x_min for b in bounds), y_min=min(b.y_min for b in bounds),
                    x_max=max(b.x_max for b in bounds), y_max=max(b.y_max for b in bounds),
                    units="pixels", origin="top_left"),
                provider_metadata={"tsv_hierarchy": list(key), "word_count": len(words)},
            ))
        page.blocks = blocks
        result = OCRResult(
            document_id=document.document_id, filename=document.filename, source=document.source,
            source_metadata=document.source_metadata, provider="tesseract",
            model_name="Tesseract tessdata_fast", model_version=self.spec.model_revision,
            language=document.source_metadata["language"], text=page.text, pages=[page],
            provider_metadata={"oem": 1, "psm": 3, "dpi_hint": 300, "threads": 1,
                               "image_resampled": False, "recognition_language": output["language"]},
        )
        return Prediction(result=result, text_format="plain",
                          coordinate_notes="Original image pixels; native TSV words grouped by native line hierarchy; line boxes are word-box unions")

    def get_capabilities(self):
        return self.spec.capabilities

    def get_metadata(self):
        return self.spec

    def cleanup(self):
        self.options = None


def create_adapter(spec):
    return TesseractAdapter(spec)
