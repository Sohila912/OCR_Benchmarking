from pdf2image import convert_from_path
from paddleocr import PaddleOCR
import tempfile

class PaddleRunner:

    def __init__(self):
        self.ocr = PaddleOCR(
            use_angle_cls=True,
            lang="ar" #For Arabic, use "ar"
        )

    def run(self, pdf_path):
        pages = convert_from_path(pdf_path, dpi=300)
        markdown = ""
        for page in pages:
            with tempfile.NamedTemporaryFile(
                suffix=".png", delete=False
            ) as temp:
                page.save(temp.name, "PNG")
                result = self.ocr.ocr(temp.name)
                # Check if result is valid and its first element is not None before iterating
                if result and isinstance(result, list) and len(result) > 0 and result[0] is not None:
                    for line in result[0]:
                        # Ensure 'line' has the expected structure before accessing elements
                        if isinstance(line, list) and len(line) >= 2 and isinstance(line[1], tuple) and len(line[1]) >= 1:
                            markdown += line[1][0] + "\n"
        return markdown
