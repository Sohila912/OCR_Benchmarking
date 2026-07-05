from pdf2image import convert_from_path
from paddleocr import PaddleOCR
import tempfile
class PaddleRunner:

    def __init__(self):

        self.ocr = PaddleOCR(
            use_angle_cls=True,
            lang="en"
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
            for line in result[0]:
                markdown += line[1][0] + "\n"
    return markdown