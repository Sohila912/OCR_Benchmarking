"""Frontend regressions with real Streamlit reruns and mocked HTTP/OCR."""
from pathlib import Path
from unittest.mock import Mock

import pytest
import requests
from streamlit.testing.v1 import AppTest

from OCR.schemas import OCRResult


ROOT = Path(__file__).resolve().parents[1]


def mock_api(monkeypatch):
    def get(url, **kwargs):
        payload = ({"tools": ["tesseract", "qwen_ollama", "future_engine"], "default": "missing"}
                   if url.endswith("/tools") else {"providers": []})
        return Mock(json=lambda: payload, raise_for_status=lambda: None)
    monkeypatch.setattr(requests, "get", get)


@pytest.mark.parametrize("entrypoint", ["frontend/app.py", "OCR/streamlit_app.py"])
def test_entrypoints_discover_future_providers_and_keep_results(monkeypatch, entrypoint):
    mock_api(monkeypatch)
    result = OCRResult(document_id="doc", filename="sample.pdf", provider="tesseract",
                       text="مرحبا OCR", markdown="مرحبا OCR").model_dump(mode="json")
    app = AppTest.from_file(str(ROOT / entrypoint))
    app.session_state["workspace_navigation"] = "Document Processing"
    app.session_state["ocr_entries"] = [{"provider": "tesseract", "result": result, "elapsed": 1.2}]
    app.session_state["ocr_run_filename"] = "sample.pdf"
    app.run()
    assert not app.exception
    assert app.selectbox[0].value == "tesseract"
    assert app.text_area[0].value == "مرحبا OCR"
    next(radio for radio in app.radio if radio.label == "Extraction mode").set_value("Compare providers").run()
    assert not app.exception
    assert "future_engine" in app.multiselect[0].value
    assert app.text_area[0].value == "مرحبا OCR"
    next(button for button in app.button if button.label == "Refresh service status").click().run()
    assert not app.exception
    assert app.session_state["ocr_entries"][0]["result"]["text"] == "مرحبا OCR"
    next(button for button in app.button if button.label == "Clear displayed results").click().run()
    assert not app.exception
    assert app.session_state["ocr_entries"] == []


def test_api_outage_preserves_downloadable_results(monkeypatch):
    def offline(*args, **kwargs):
        raise requests.ConnectionError("offline")
    monkeypatch.setattr(requests, "get", offline)
    result = OCRResult(document_id="doc", filename="sample.pdf", provider="tesseract", text="saved").model_dump(mode="json")
    app = AppTest.from_file(str(ROOT / "frontend/app.py"))
    app.session_state["workspace_navigation"] = "Document Processing"
    app.session_state["ocr_entries"] = [{"provider": "tesseract", "result": result, "elapsed": 1}]
    app.session_state["ocr_run_filename"] = "sample.pdf"
    app.run()
    assert not app.exception
    assert app.error
    assert app.text_area[0].value == "saved"


def test_comparison_continues_after_failure_and_download_rerun_does_not_extract(monkeypatch):
    import streamlit as st
    mock_api(monkeypatch)
    upload = Mock(name="upload")
    upload.name = "sample.pdf"
    upload.size = 20
    upload.getvalue.return_value = b"%PDF-1.4 fake fixture"
    monkeypatch.setattr(st, "file_uploader", lambda *args, **kwargs: upload)
    calls = []

    def post(url, **kwargs):
        provider = kwargs["data"]["engine"]
        calls.append(provider)
        if provider == "qwen_ollama":
            raise requests.ConnectionError("provider offline")
        result = OCRResult(document_id="doc", filename=upload.name, provider=provider,
                           text=f"text from {provider}").model_dump(mode="json")
        return Mock(json=lambda: result, raise_for_status=lambda: None)

    monkeypatch.setattr(requests, "post", post)
    app = AppTest.from_file(str(ROOT / "frontend/app.py"))
    app.session_state["workspace_navigation"] = "Document Processing"
    app.run()
    next(radio for radio in app.radio if radio.label == "Extraction mode").set_value("Compare providers").run()
    next(button for button in app.button if button.label == "Run extraction").click().run()
    assert not app.exception
    assert calls == ["tesseract", "qwen_ollama", "future_engine"]
    assert len(app.session_state["ocr_entries"]) == 3
    assert app.session_state["ocr_entries"][1]["error"]
    app.run()
    assert not app.exception
    assert len(calls) == 3


def test_invalid_inventory_has_actionable_error(monkeypatch):
    monkeypatch.setattr(requests, "get", lambda *a, **k: Mock(
        json=lambda: {"tools": []}, raise_for_status=lambda: None))
    app = AppTest.from_file(str(ROOT / "frontend/app.py")).run()
    assert not app.exception
    assert any("invalid provider inventory" in issue.value for issue in app.error)
