import importlib.util
import sys
import types
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "runners" / "surya_runner.py"

fake_surya_module = types.ModuleType("surya")
fake_recognition_module = types.ModuleType("surya.recognition")
fake_pdf2image_module = types.ModuleType("pdf2image")


class DummyRecognitionPredictor:
    pass


fake_recognition_module.RecognitionPredictor = DummyRecognitionPredictor
fake_pdf2image_module.convert_from_path = lambda pdf_path, dpi=300: ["page"]
sys.modules.setdefault("surya", fake_surya_module)
sys.modules.setdefault("surya.recognition", fake_recognition_module)
sys.modules.setdefault("pdf2image", fake_pdf2image_module)

SPEC = importlib.util.spec_from_file_location("surya_runner", MODULE_PATH)
surya_runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(surya_runner)


class DummyLine:
    def __init__(self, text):
        self.text = text


class DummyPage:
    def __init__(self, lines=None):
        self.text_lines = lines or []


class DummyBlock:
    def __init__(self, html):
        self.html = html


class DummyResults:
    def __init__(self, pages):
        self.pages = pages

    def __iter__(self):
        return iter(self.pages)


def test_run_handles_text_lines_without_label(monkeypatch, tmp_path):
    class DummyPredictor:
        def __call__(self, pages, full_page=True):
            assert full_page is True
            return DummyResults([DummyPage([DummyLine("hello"), DummyLine("world")])])

    class DummyModule:
        RecognitionPredictor = DummyPredictor

    monkeypatch.setattr(surya_runner, "importlib", importlib)
    monkeypatch.setattr(surya_runner, "convert_from_path", lambda pdf_path, dpi=300: ["page"])
    monkeypatch.setattr(importlib, "import_module", lambda name: DummyModule())

    runner = surya_runner.SuryaRunner()
    markdown = runner.run(tmp_path / "sample.pdf")

    assert markdown == "hello\nworld\n"


def test_run_extracts_html_from_surya_blocks(monkeypatch, tmp_path):
    class DummyPageWithBlocks:
        def __init__(self):
            self.blocks = [DummyBlock("<p>hello</p>"), DummyBlock("<p>world</p>")]

    class DummyPredictor:
        def __call__(self, pages, full_page=True):
            return [DummyPageWithBlocks()]

    class DummyModule:
        RecognitionPredictor = DummyPredictor

    monkeypatch.setattr(surya_runner, "importlib", importlib)
    monkeypatch.setattr(surya_runner, "convert_from_path", lambda pdf_path, dpi=300: ["page"])
    monkeypatch.setattr(importlib, "import_module", lambda name: DummyModule())

    runner = surya_runner.SuryaRunner()
    markdown = runner.run(tmp_path / "sample.pdf")

    assert "hello" in markdown
    assert "world" in markdown


def test_run_falls_back_to_pdf_text_extraction(monkeypatch, tmp_path):
    class DummyPdfReader:
        def __init__(self, path):
            self.path = path
            self.pages = [self._make_page()]

        def _make_page(self):
            class DummyPage:
                def extract_text(self):
                    return "fallback text"

            return DummyPage()

    monkeypatch.setattr(surya_runner, "convert_from_path", lambda pdf_path, dpi=300: (_ for _ in ()).throw(RuntimeError("poppler missing")))
    monkeypatch.setattr(surya_runner, "PdfReader", DummyPdfReader)
    monkeypatch.setattr(surya_runner, "Path", Path)

    runner = surya_runner.SuryaRunner()
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    markdown = runner.run(pdf_path)

    assert isinstance(markdown, str)
    assert "fallback text" in markdown


def test_run_returns_empty_string_instead_of_none(monkeypatch, tmp_path):
    monkeypatch.setattr(surya_runner, "convert_from_path", lambda pdf_path, dpi=300: (_ for _ in ()).throw(RuntimeError("poppler missing")))
    monkeypatch.setattr(surya_runner, "PdfReader", None)
    monkeypatch.setattr(surya_runner, "shutil", type("S", (), {"which": staticmethod(lambda name: None)}))

    runner = surya_runner.SuryaRunner()
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    markdown = runner.run(pdf_path)

    assert isinstance(markdown, str)
    assert markdown == ""
