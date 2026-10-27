"""Focused lifecycle, privacy and historical-scoring acceptance tests."""
import importlib
import json
import logging
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest
import requests
from fastapi.testclient import TestClient
from jiwer import cer, wer
from pydantic import ValidationError
from streamlit.testing.v1 import AppTest

from OCR.app import create_app
from OCR.config import Settings
from OCR.errors import ExtractionError
from OCR.schemas import OCRResult
from OCR.service import OCRService
from benchmarks.evaluation.metrics import evaluate_directory, score_document
from conftest import FakeProvider

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("failure", [None, ExtractionError("secret document contents")])
@pytest.mark.parametrize("route", ["/extract", "/extract/compare"])
def test_opt_in_upload_cleanup_including_failures(settings, failure, route, caplog):
    settings = settings.model_copy(update={"retain_uploads": False})
    caplog.set_level(logging.INFO)
    with TestClient(create_app(settings, OCRService(settings, {"tesseract": FakeProvider(failure=failure)}))) as client:
        response = client.post(route, files={"file": ("private-filename.pdf", b"%PDF-1.4")})
    assert response.status_code in (200, 500)
    assert not list(settings.upload_dir.glob("*.pdf"))
    assert not list(settings.temp_dir.iterdir())
    assert "secret document contents" not in caplog.text
    assert "private-filename.pdf" not in caplog.text
    events = [json.loads(record.message) for record in caplog.records if record.name.startswith("OCR.")]
    assert all("event" in event for event in events)


@pytest.mark.parametrize("value", ["file:///tmp/server", "http://user:secret@localhost", "http://localhost?token=secret", "http://localhost:99999"])
def test_service_urls_reject_credentials_and_invalid_endpoints(value):
    with pytest.raises(ValidationError):
        Settings(api_url=value)


def test_ollama_standard_host_environment_syntax_remains_supported():
    assert Settings(ollama_host="127.0.0.1:11434").ollama_host == "http://127.0.0.1:11434"


@pytest.mark.parametrize("language,module_name", [("English", "english"), ("Arabic", "arabic"), ("Mix", "mix")])
def test_shared_metrics_match_cli_nonzero_results(language, module_name, tmp_path, monkeypatch):
    module = importlib.import_module(f"benchmarks.evaluation.evaluate_{module_name}")
    reference, prediction = "Hello world مرحبا بالعالم", "Hello wrong عالم"
    expected = score_document("sample.md", reference, prediction, language)
    ref, out = tmp_path / "ref", tmp_path / "out"
    ref.mkdir(); out.mkdir()
    (ref / "sample.md").write_text(reference, encoding="utf-8")
    (out / "sample.md").write_text(prediction, encoding="utf-8")
    (ref / "missing.md").write_text("missing", encoding="utf-8")
    rows, missing = evaluate_directory(ref, out, language)
    assert rows == [expected] and missing == ["missing.md"]
    ref_clean, pred_clean = module.normalize_text(reference), module.normalize_text(prediction)
    assert expected["WER"] == round(wer(ref_clean, pred_clean), 4)
    assert expected["CER"] == round(cer(ref_clean, pred_clean), 4)
    report = tmp_path / "metrics.xlsx"
    monkeypatch.setattr(sys, "argv", ["evaluate", "--reference", str(ref), "--ocr-output", str(out), "--result", str(report)])
    module.main()
    import pandas as pd
    assert pd.read_excel(report).iloc[0].to_dict() == expected


def api_inventory(monkeypatch):
    monkeypatch.setattr(requests, "get", lambda url, **kwargs: Mock(
        raise_for_status=lambda: None,
        json=lambda: {"tools": ["tesseract", "qwen_ollama"], "default": "tesseract"}
        if url.endswith("/tools") else {"providers": [{"provider": "qwen_ollama", "status": "unavailable"}]}))


def test_dashboard_navigation_and_safe_settings(monkeypatch):
    api_inventory(monkeypatch)
    app = AppTest.from_file(str(ROOT / "frontend/app.py")).run()
    assert not app.exception
    assert app.metric[0].value == "2"
    next(b for b in app.button if b.label == "Process a document").click().run()
    assert not app.exception
    assert app.title[0].value == "Document processing"
    next(r for r in app.radio if r.label == "Navigation").set_value("Settings / Provider Status").run()
    assert not app.exception
    assert app.warning
    assert not app.json  # No raw environment or credential dictionaries.


def test_saved_benchmark_scores_fixture_and_survives_navigation(monkeypatch, tmp_path):
    import OCR.benchmark_api as backend
    api_inventory(monkeypatch)
    reference = tmp_path / "datasets/English/Markdown_Reference"
    output = tmp_path / "outputs/English/fixture"
    reference.mkdir(parents=True); output.mkdir(parents=True)
    (reference / "sample.md").write_text("hello world", encoding="utf-8")
    (output / "sample.md").write_text("hello world", encoding="utf-8")
    monkeypatch.setattr(backend, "DATASETS", tmp_path / "datasets")
    monkeypatch.setattr(backend, "OUTPUTS", tmp_path / "outputs")
    settings = Settings(benchmark_db=tmp_path / "history.sqlite3")
    with TestClient(create_app(settings, OCRService(settings, {"tesseract": FakeProvider()}))) as client:
        def request(method, url, **kwargs):
            response = client.request(method, "/" + url.split("/", 3)[3], **kwargs)
            return Mock(raise_for_status=lambda: response.raise_for_status(), json=lambda: response.json())
        monkeypatch.setattr(requests, "request", request)
        app = AppTest.from_file(str(ROOT / "frontend/app.py"))
        app.session_state["workspace_navigation"] = "Benchmarking"
        app.run()
        next(b for b in app.button if b.label == "Load existing datasets").click().run()
        assert not app.exception
        next(s for s in app.selectbox if s.label == "Source").set_value("English/fixture/sample.md").run()
        next(c for c in app.checkbox if c.label.startswith("I confirm this existing")).check().run()
        next(b for b in app.button if b.label == "Evaluate selected dataset document").click().run()
        assert not app.exception
        assert app.session_state["dataset_result"]["results"][0]["metrics"]["wer"] == 0
        assert app.session_state["ocr_entries"][0]["elapsed"] is None
        next(r for r in app.radio if r.label == "Navigation").set_value("Overview").run()
        assert not app.exception
        assert app.dataframe[0].value["Request seconds"].isna().all()
        next(r for r in app.radio if r.label == "Navigation").set_value("Results & Comparison").run()
        assert not app.exception
        assert app.dataframe[0].value["OCR seconds"].isna().all()
        assert any(metric.label == "OCR duration" and metric.value == "Unknown" for metric in app.metric)
        assert any(text.label == "Extracted text" and text.value == "hello world" for text in app.text_area)
        next(r for r in app.radio if r.label == "Navigation").set_value("Benchmarking").run()
        assert not app.exception
        assert app.session_state["dataset_result"]["results"][0]["metrics"]["wer"] == 0


def test_duplicate_processing_requires_explicit_intent(monkeypatch):
    import streamlit as st
    api_inventory(monkeypatch)
    upload = Mock()
    upload.name, upload.size = "sample.pdf", 15
    upload.getvalue.return_value = b"%PDF-1.4 fixture"
    monkeypatch.setattr(st, "file_uploader", lambda *a, **k: upload)
    result = OCRResult(document_id="doc", filename="sample.pdf", provider="tesseract", text="hello").model_dump(mode="json")
    post = Mock(return_value=Mock(raise_for_status=lambda: None, json=lambda: result))
    monkeypatch.setattr(requests, "post", post)
    app = AppTest.from_file(str(ROOT / "frontend/app.py"))
    app.session_state["workspace_navigation"] = "Document Processing"
    app.run()
    next(b for b in app.button if b.label == "Run extraction").click().run()
    assert not app.exception
    assert post.call_count == 1
    assert next(b for b in app.button if b.label == "Run extraction").disabled
    app.run()
    assert post.call_count == 1
    next(c for c in app.checkbox if c.label == "Submit again intentionally").check().run()
    assert not next(b for b in app.button if b.label == "Run extraction").disabled
