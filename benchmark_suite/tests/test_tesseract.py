import json
from types import SimpleNamespace

import pytest

from OCR.providers.base import OCRDocument
from benchmark_suite.adapters.base import RawOutput
from benchmark_suite.adapters.tesseract import TesseractAdapter


def document(language="ar"):
    return OCRDocument(document_id="test", filename="test.png", path="test.png",
                       source_metadata={"language": language, "width": 100, "height": 100})


def test_native_lines_preserve_unicode_order_and_pixel_geometry():
    tsv = "level\ttext\tconf\tleft\ttop\twidth\theight\tblock_num\tpar_num\tline_num\tword_num\n"
    tsv += "5\tمرحبا\t90\t50\t10\t20\t10\t1\t1\t1\t1\n"
    tsv += "5\tبكم\t85\t20\t10\t20\t10\t1\t1\t1\t2\n"
    tsv += "5\tالتالي\t80\t50\t30\t30\t10\t1\t1\t2\t1\n"
    adapter = TesseractAdapter(SimpleNamespace(model_revision="test"))
    prediction = adapter.normalize_output(RawOutput(json.dumps({"tsv": tsv, "language": "ara"}).encode(),
                                                    "application/json"), document())
    page = prediction.result.pages[0]
    assert page.text == "مرحبا بكم\nالتالي"
    assert [b.text for b in page.blocks] == ["مرحبا بكم", "التالي"]
    assert [b.reading_order for b in page.blocks] == [0, 1]
    assert page.blocks[0].bounding_box.x_min == 20
    assert page.blocks[0].bounding_box.x_max == 70
    assert prediction.result.document_id == "test"


@pytest.mark.parametrize("language,expected", [("ar", "ara"), ("en", "eng")])
def test_predict_pins_native_settings_without_shell(monkeypatch, language, expected):
    adapter = TesseractAdapter(None)
    adapter.options = {"executable": "tesseract", "tessdata": "data", "timeout_seconds": 120}
    adapter.environment = {"OMP_THREAD_LIMIT": "1"}
    calls = []

    def capture(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(stdout=b"tsv", stderr=b"warning")

    monkeypatch.setattr("benchmark_suite.adapters.tesseract.subprocess.run", capture)
    output = json.loads(adapter.predict(document(language)).data)
    command, kwargs = calls[0]
    assert command[command.index("-l") + 1] == expected
    assert command[command.index("--psm") + 1] == "3"
    assert command[command.index("--oem") + 1] == "1"
    assert kwargs["check"] and kwargs["timeout"] == 120
    assert kwargs["env"]["OMP_THREAD_LIMIT"] == "1"
    assert output == {"tsv": "tsv", "stderr": "warning", "language": expected}
    adapter.cleanup()
    with pytest.raises(RuntimeError, match="not initialized"):
        adapter.predict(document(language))


def test_initialize_rejects_changed_native_version(monkeypatch):
    adapter = TesseractAdapter(SimpleNamespace(native_versions={"tesseract": "tesseract v5.4.0"}))
    monkeypatch.setattr("benchmark_suite.adapters.tesseract.subprocess.run",
                        lambda *args, **kwargs: SimpleNamespace(stdout=b"tesseract v5.3.0\n"))
    with pytest.raises(RuntimeError, match="version differs"):
        adapter.initialize(SimpleNamespace(adapter_options={"executable": "tesseract"}))


def test_initialize_rejects_missing_arabic_without_language_fallback(monkeypatch):
    adapter = TesseractAdapter(SimpleNamespace(native_versions={"tesseract": "tesseract v5.4.0"}))
    responses = iter([b"tesseract v5.4.0\n", b"List of available languages (1):\neng\n"])
    monkeypatch.setattr("benchmark_suite.adapters.tesseract.subprocess.run",
                        lambda *args, **kwargs: SimpleNamespace(stdout=next(responses)))
    with pytest.raises(RuntimeError, match="English/Arabic language assets"):
        adapter.initialize(SimpleNamespace(adapter_options={"executable": "tesseract", "tessdata": "data"}))
