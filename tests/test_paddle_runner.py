import importlib.util
import sys
import types
from pathlib import Path

from PIL import Image

MODULE_PATH = Path(__file__).resolve().parents[1] / "runners" / "paddle_runner.py"

fake_pdf2image_module = types.ModuleType("pdf2image")
fake_paddleocr_module = types.ModuleType("paddleocr")


class DummyPaddleOCR:
    def __init__(self, *args, **kwargs):
        pass

    def ocr(self, image_path, cls=True):
        return []


fake_pdf2image_module.convert_from_path = lambda pdf_path, dpi=300: []
fake_paddleocr_module.PaddleOCR = DummyPaddleOCR
sys.modules.setdefault("pdf2image", fake_pdf2image_module)
sys.modules.setdefault("paddleocr", fake_paddleocr_module)

SPEC = importlib.util.spec_from_file_location("paddle_runner", MODULE_PATH)
paddle_runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(paddle_runner)


def test_preprocess_image_upscales_and_grayscales_input():
    runner = paddle_runner.PaddleRunner()
    image = Image.new("RGB", (200, 200), color="white")

    processed = runner._preprocess_image(image)

    assert processed.mode == "L"
    assert processed.size[0] > image.size[0]
    assert processed.size[1] > image.size[1]
