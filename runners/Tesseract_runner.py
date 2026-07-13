from pdf2image import convert_from_path
import pytesseract
import tempfile
import os


class TesseractRunner:

    def __init__(self):
        # Uncomment and modify this line if Tesseract is not in your PATH
        # pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"
        pass

    def run(self, pdf_path):
        pages = convert_from_path(pdf_path, dpi=300)

        markdown = ""

        for page in pages:
            with tempfile.NamedTemporaryFile(
                suffix=".png",
                delete=False
            ) as temp:

                page.save(temp.name, "PNG")

                try:
                    text = pytesseract.image_to_string(
                        temp.name,
                        lang="ara"  # For Arabic, use "ara" and for English, use "eng"
                    )

                    # Validate the OCR output
                    if text is not None and isinstance(text, str):
                        markdown += text + "\n"

                except Exception as e:
                    print(f"Error processing page: {e}")

                finally:
                    os.remove(temp.name)

        return markdown