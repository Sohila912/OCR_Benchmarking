import os
import tempfile

try:
    from pdf2image import convert_from_path
except Exception:  # pragma: no cover - optional dependency guard
    convert_from_path = None

try:
    import pytesseract
except Exception:  # pragma: no cover - optional dependency guard
    pytesseract = None


class TesseractRunner:

    def __init__(self):
        # Uncomment and modify this line if Tesseract is not in your PATH
        # pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"
        self.pytesseract = pytesseract

    def extract(self, pdf_path):
        if convert_from_path is None or self.pytesseract is None or not os.path.exists(pdf_path):
            return "Tesseract engine unavailable because the required OCR dependencies are not installed in this environment."

        try:
            pages = convert_from_path(pdf_path, dpi=300)
        except Exception:
            return ""

        markdown_parts = []

        for page in pages:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp:
                page.save(temp.name, "PNG")

                try:
                    text = self.pytesseract.image_to_string(
                        temp.name,
                        lang="ara+eng"  # For Arabic, use "ara" and for English, use "eng"
                    )

                    if text is not None and isinstance(text, str) and text.strip():
                        markdown_parts.append(text.strip())

                except Exception as e:
                    print(f"Error processing page: {e}")

                finally:
                    if os.path.exists(temp.name):
                        os.remove(temp.name)

        markdown = "\n\n".join(markdown_parts)
        if not markdown:
            return "Tesseract OCR produced no extractable text for this PDF."
        return markdown

    def run(self, pdf_path):
        return self.extract(pdf_path)