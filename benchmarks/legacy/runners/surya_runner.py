import importlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

try:
    from pdf2image import convert_from_path
except Exception:
    convert_from_path = None

try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None


class SuryaRunner:

    def __init__(self):
        self.rec_predictor = self._load_predictor()

    def _load_predictor(self):
        candidate_imports = [
            ("surya.ocr", "OCRPredictor"),
            ("surya.recognition", "RecognitionPredictor"),
            ("surya.model.recognition", "RecognitionPredictor"),
            ("surya.model.ocr", "OCRPredictor"),
        ]

        for module_name, class_name in candidate_imports:
            try:
                module = importlib.import_module(module_name)
                predictor_cls = getattr(module, class_name)
                return predictor_cls()
            except Exception:
                continue

        return None

    def _coerce_text(self, value, seen=None):
        if value is None:
            return ""

        if isinstance(value, str):
            return value.strip()

        if isinstance(value, (list, tuple)):
            if seen is None:
                seen = set()
            texts = []
            for item in value:
                text = self._coerce_text(item, seen)
                if text:
                    texts.append(text)
            return "\n".join(texts)

        if isinstance(value, dict):
            if seen is None:
                seen = set()
            texts = []
            for key in ("text", "content", "raw_text", "html", "value", "line", "word", "words", "blocks", "children", "lines", "markdown"):
                if key in value:
                    text = self._coerce_text(value[key], seen)
                    if text:
                        texts.append(text)
            if not texts:
                for key, item in value.items():
                    if key.startswith("_"):
                        continue
                    text = self._coerce_text(item, seen)
                    if text:
                        texts.append(text)
            if texts:
                return "\n".join(texts)

        if hasattr(value, "__dict__"):
            if seen is None:
                seen = set()
            obj_id = id(value)
            if obj_id in seen:
                return ""
            seen.add(obj_id)

            texts = []
            for attr in ("text", "content", "raw_text", "html", "value", "line", "word", "words", "markdown"):
                text = self._coerce_text(getattr(value, attr, None), seen)
                if text:
                    texts.append(text)

            if not texts:
                for key, item in vars(value).items():
                    if key.startswith("_"):
                        continue
                    if key in {"bbox", "polygon", "confidence", "label", "raw_label", "reading_order", "skipped", "error", "position", "count", "image_bbox", "raw"}:
                        continue
                    text = self._coerce_text(item, seen)
                    if text:
                        texts.append(text)

            if texts:
                return "\n".join(texts)

        return ""

    def _extract_text(self, result):
        markdown = ""

        if result is None:
            return markdown

        candidates = []
        if hasattr(result, "pages"):
            candidates.append(result.pages)
        if isinstance(result, (list, tuple)):
            candidates.append(result)
        if not candidates:
            candidates.append([result])

        for item in candidates:
            if isinstance(item, (list, tuple)):
                for page in item:
                    page_text = self._coerce_text(page)
                    if page_text:
                        markdown += page_text + "\n"
            else:
                page_text = self._coerce_text(item)
                if page_text:
                    markdown += page_text + "\n"

        return markdown

    def _predict(self, pages):
        if self.rec_predictor is None:
            return None

        attempts = [
            lambda: self.rec_predictor(pages, full_page=True),
            lambda: self.rec_predictor(pages),
            lambda: self.rec_predictor(pages, bboxes=False),
            lambda: self.rec_predictor(pages, full_page=False),
        ]

        for attempt in attempts:
            try:
                return attempt()
            except TypeError:
                continue
            except AttributeError as exc:
                if "PolygonBox" in str(exc) or "label" in str(exc):
                    continue
                raise

        return None

    def _run_cli(self, pdf_path):
        cli = shutil.which("surya_ocr")
        if not cli:
            return ""

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            cmd = [cli, str(pdf_path), "--output_dir", str(output_dir)]
            try:
                subprocess.run(cmd, check=True, capture_output=True, text=True)
            except Exception:
                return ""

            results_json = output_dir / "results.json"
            if not results_json.exists():
                return ""

            try:
                with results_json.open("r", encoding="utf-8") as handle:
                    payload = json.load(handle)
            except Exception:
                return ""

            text_parts = []
            if isinstance(payload, dict):
                for key, value in payload.items():
                    if isinstance(value, list):
                        for item in value:
                            if isinstance(item, dict):
                                for block in item.get("blocks", []):
                                    html = block.get("html")
                                    if isinstance(html, str) and html.strip():
                                        text_parts.append(html)
            return "\n".join(text_parts)

    def _pdf_fallback_text(self, pdf_path):
        if PdfReader is None:
            return ""

        try:
            reader = PdfReader(str(pdf_path))
        except Exception:
            return ""

        parts = []
        for page in reader.pages:
            try:
                text = page.extract_text() or ""
            except Exception:
                text = ""
            if text.strip():
                parts.append(text.strip())

        return "\n".join(parts)

    def run(self, pdf_path):
        if convert_from_path is None:
            return self._pdf_fallback_text(pdf_path)

        try:
            pages = convert_from_path(pdf_path, dpi=300)
        except Exception:
            fallback = self._pdf_fallback_text(pdf_path)
            if fallback.strip():
                return fallback
            return self._run_cli(pdf_path) or ""

        if not pages:
            fallback = self._pdf_fallback_text(pdf_path)
            if fallback.strip():
                return fallback
            return self._run_cli(pdf_path) or ""

        try:
            result = self._predict(pages)
        except Exception:
            result = None

        markdown = self._extract_text(result)
        if markdown.strip():
            return markdown

        fallback = self._pdf_fallback_text(pdf_path)
        if fallback.strip():
            return fallback

        return self._run_cli(pdf_path) or ""