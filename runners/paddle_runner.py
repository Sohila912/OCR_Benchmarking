import os
import tempfile

try:
    from pdf2image import convert_from_path
except Exception:  # pragma: no cover - optional dependency guard
    convert_from_path = None

try:
    from paddleocr import PaddleOCR
except Exception:  # pragma: no cover - optional dependency guard
    PaddleOCR = None


class PaddleRunner:

    def __init__(self):
        self.ocr = None
        if PaddleOCR is not None:
            try:
                self.ocr = PaddleOCR(
                    use_angle_cls=True,
                    lang="ar"  # For Arabic, use "ar" and for English, use "en"
                )
            except Exception:
                self.ocr = None

    def _preprocess_image(self, image):
        grayscale = image.convert("L")
        width, height = grayscale.size
        return grayscale.resize((max(width * 2, 1), max(height * 2, 1)))

    def extract(self, pdf_path):
        if convert_from_path is None or self.ocr is None:
            return "Paddle engine unavailable because the required OCR dependencies are not installed in this environment."

        if not os.path.exists(pdf_path):
            return ""

        try:
            pages = convert_from_path(pdf_path, dpi=300)
        except Exception:
            return ""

        markdown_parts = []
        for page in pages:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp:
                processed = self._preprocess_image(page)
                processed.save(temp.name, "PNG")
                try:
                    result = self.ocr.ocr(temp.name)
                    if result and isinstance(result, list) and len(result) > 0 and result[0] is not None:
                        for line in result[0]:
                            if isinstance(line, list) and len(line) >= 2 and isinstance(line[1], tuple) and len(line[1]) >= 1:
                                markdown_parts.append(str(line[1][0]))
                finally:
                    if os.path.exists(temp.name):
                        os.remove(temp.name)

        markdown = "\n".join(part for part in markdown_parts if part)
        if not markdown:
            return "Paddle OCR produced no extractable text for this PDF."
        return markdown

    def run(self, pdf_path):
        return self.extract(pdf_path)
