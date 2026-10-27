"""Ground-truth regression tests use fake OCR; no model downloads."""
import io
import json
from datetime import datetime, timezone
from unittest.mock import Mock
import pytest
import requests
from fastapi.testclient import TestClient
from OCR.app import create_app
from OCR.service import OCRService
from OCR.evaluation import Normalization, evaluate, normalize, reference_upload, differences, aggregate
from OCR.benchmark_store import BenchmarkStore, compare_runs
from OCR.errors import ProviderInitializationError, ExtractionError
from conftest import FakeProvider

@pytest.mark.parametrize("ref,pred,edits", [("abc","abc",0),("abc","axc",1),("abc","ab",1),("abc","abcd",1),("abc","",3),("a","aaaa",3)])
def test_character_edits(ref,pred,edits):
    result=evaluate(ref,pred,Normalization())
    assert result["characters"]["edits"]==edits
    assert result["cer"]==edits/len(ref)
    assert result["exact_match"]==(ref==pred)

def test_words_arabic_unicode_and_markdown():
    options=Normalization()
    assert evaluate("one two", "one three four", options)["wer"]==1
    assert evaluate("مَرْحَبًا", "مرحبا", options)["cer"]>0
    assert evaluate("café", "cafe\u0301", options)["exact_match"]
    assert evaluate("# Hello **world**", "Hello world", options)["exact_match"]
    assert not evaluate("# Hello", "Hello", Normalization(mode="raw_markdown"))["exact_match"]
    assert evaluate("Hello\r\nworld", "Hello   world", options)["exact_match"]
    assert not evaluate("Hi!", "hi", options)["exact_match"]
    assert evaluate("Hi!", "hi", Normalization(casefold=True,punctuation=True))["exact_match"]
    assert normalize("a\r\nb", Normalization(whitespace=False))=="a\nb"

@pytest.mark.parametrize("reference", ["", "   ", "# "])
def test_empty_reference(reference):
    with pytest.raises(ValueError):
        evaluate(reference,"anything",Normalization())

@pytest.mark.parametrize("data,name", [(b"", "x.md"),(b"\xff", "x.md"),(b"x", "x.txt"),(b"a\x00b", "x.md"),(b"x"*(2*1024*1024+1), "x.md")], ids=["empty", "encoding", "extension", "nul", "oversize"])
def test_invalid_reference(data,name):
    with pytest.raises(ValueError): reference_upload(data,name)

def test_utf8_bom_and_bounded_diff():
    assert reference_upload("مرحبا".encode("utf-8-sig"),"ref.md")=="مرحبا"
    assert differences("x"*13000,"y",Normalization())["truncated"]
    assert differences("one","two",Normalization())["changes"][0]["operation"]=="replace"

def client(settings, failure=None):
    settings=settings.model_copy(update={"benchmark_db":settings.temp_dir/"history.sqlite3"})
    return TestClient(create_app(settings, OCRService(settings,{"tesseract":FakeProvider(failure=failure)})))

def submit(c, paired="true", reference=b"Hello \xd9\x85\xd8\xb1\xd8\xad\xd8\xa8\xd8\xa7"):
    return c.post("/benchmarks/run",files={"file":("test.pdf",b"%PDF-1.4 mock"),"reference":("truth.md",reference)},data={"providers":'["tesseract"]',"paired":paired,"dataset":"A"})

def test_api_history_compare_delete_and_no_content_retention(settings):
    with client(settings) as c:
        first=submit(c).json()["results"][0]
        second=submit(c).json()["results"][0]
        assert first["metrics"]["cer"]==0
        assert first["duration_seconds"]>=first["inference_seconds"]
        rows=c.get("/benchmarks/history",params={"provider":"tesseract","dataset":"A"}).json()
        assert len(rows)==2
        assert "reference" not in rows[0] and "output" not in rows[0]
        assert c.get("/benchmarks/history",params={"dataset":"B"}).json()==[]
        result=c.post("/benchmarks/compare",json=[first["id"],second["id"]]).json()
        assert result["same_document_and_reference"]
        assert result["summaries"][0]["micro_cer"]==0
        assert c.post("/benchmarks/compare",json=["invalid"]).status_code==400
        assert c.delete("/benchmarks/history/"+first["id"]).json()["deleted"]==1
    assert not list(settings.upload_dir.glob("*.pdf"))
    assert not list(settings.output_dir.glob("*.json"))

def test_pairing_and_invalid_reference(settings):
    with client(settings) as c:
        assert submit(c,paired="false").status_code==400
        assert submit(c,reference=b"\xff").status_code==400
        assert submit(c,reference=b" ").status_code==400

@pytest.mark.parametrize("failure",[ProviderInitializationError("secret"),ExtractionError("secret")])
def test_failure_saved_without_secrets_or_scores(settings,failure):
    with client(settings,failure) as c:
        row=submit(c).json()["results"][0]
        assert row["status"]=="failed" and "metrics" not in row
        assert "secret" not in json.dumps(c.get("/benchmarks/history").json())

def test_store_validation_and_retention(tmp_path):
    store=BenchmarkStore(tmp_path/"db.sqlite3")
    with pytest.raises(ValueError): store.save({"id":"broken"})
    row={"id":"old","timestamp":"2000-01-01T00:00:00+00:00","dataset_id":"A","provider":"p","document_id":"d","reference_hash":"h","status":"failed"}
    store.save(row)
    assert store.history()==[]

def test_micro_averaging():
    rows=[{"status":"success","document_id":"a","metrics":evaluate("abcdefghij","abcdefghij",Normalization())},
          {"status":"success","document_id":"b","metrics":evaluate("x","y",Normalization())}]
    assert aggregate(rows)["micro_cer"]==1/11

def test_diagnostics_dependencies_assets_server_and_model(settings,monkeypatch):
    import OCR.provider_diagnostics as diagnostic
    service=OCRService(settings)
    monkeypatch.setattr(diagnostic.importlib.util,"find_spec",lambda name:None)
    assert all(r["state"]=="Missing dependencies" for r in diagnostic.diagnose(service) if r["provider"]!="tesseract")
    monkeypatch.setattr(diagnostic.importlib.util,"find_spec",lambda name:object())
    assert diagnostic.diagnose(service)[0]["state"]=="Not configured"
    service.settings=settings.model_copy(update={"paddle_vl_model_dir":settings.temp_dir/"missing"})
    assert diagnostic.diagnose(service)[0]["state"]=="Model unavailable"
    monkeypatch.setattr(diagnostic.requests,"get",Mock(side_effect=requests.ConnectionError()))
    assert diagnostic.diagnose(service)[-1]["state"]=="Server unreachable"
    monkeypatch.setattr(diagnostic.requests,"get",lambda *a,**k:Mock(raise_for_status=lambda:None,json=lambda:{"models":[{"name":"other"}]}))
    assert diagnostic.diagnose(service)[-1]["state"]=="Model unavailable"

def test_ready_requires_inference(settings,monkeypatch):
    from OCR.provider_diagnostics import diagnose
    from OCR.providers.base import OCRDocument
    fake=FakeProvider()
    service=OCRService(settings,{"tesseract":fake})
    fake.initialize()
    assert diagnose(service)[0]["state"]!="Ready"
    service.extract(OCRDocument(document_id="x",filename="x.pdf",path=settings.temp_dir/"x.pdf"),"tesseract",persist_result=False)
    assert diagnose(service)[0]["state"]=="Ready"


def test_streamlit_uploaded_reference_results_exports_and_reruns(settings,monkeypatch):
    import streamlit as st
    from streamlit.testing.v1 import AppTest
    from pathlib import Path
    pdf=Mock(); pdf.name="sample.pdf"; pdf.size=15; pdf.getvalue.return_value=b"%PDF-1.4 mock"
    reference=Mock(); reference.name="truth.md"; reference.size=20; reference.getvalue.return_value="Hello مرحبا".encode()
    monkeypatch.setattr(st,"file_uploader",lambda label,**kwargs:pdf if "PDF" in label else reference)
    monkeypatch.setattr(requests,"get",lambda url,**kwargs:Mock(raise_for_status=lambda:None,json=lambda:{"tools":["tesseract"],"default":"tesseract"} if url.endswith("/tools") else {"providers":[]}))
    submissions=[]
    with client(settings) as c:
        def request(method,url,**kwargs):
            path="/"+url.split("/",3)[3]
            if method=="POST" and path=="/benchmarks/run": submissions.append(path)
            kwargs.pop("timeout",None)
            return c.request(method,path,**kwargs)
        monkeypatch.setattr(requests,"request",request)
        app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/"frontend/app.py"),default_timeout=15)
        app.session_state["workspace_navigation"]="Benchmarking"
        app.run()
        assert next(b for b in app.button if b.label=="Run Benchmark").disabled
        next(c for c in app.checkbox if c.label.startswith("I confirm the PDF")).check().run()
        assert app.multiselect[0].value == ["tesseract"], repr([(m.label,m.value) for m in app.multiselect])
        assert not next(b for b in app.button if b.label=="Run Benchmark").disabled, ([e.value for e in app.error], [(c.label,c.value) for c in app.checkbox], [(m.label,m.value) for m in app.multiselect], [(t.label,t.value) for t in app.text_input])
        next(b for b in app.button if b.label=="Run Benchmark").click().run()
        assert not app.exception
        assert app.session_state["gt_result"]["results"][0]["metrics"]["exact_match"]
        assert any(t.value=="Hello مرحبا" for t in app.text_area)
        assert len(app.get("download_button"))>=4
        app.run()
        assert not app.exception and len(submissions)==1
        next(b for b in app.button if b.label=="Refresh benchmark history").click().run()
        assert len(app.session_state["gt_history"])==1
        assert "output" not in app.session_state["gt_history"][0]


@pytest.mark.parametrize("names,failed", [
    (["tesseract"], None),
    (["tesseract", "docling"], None),
    (["tesseract", "docling", "paddle_vl", "extra_engine"], None),
    (["tesseract", "docling"], "docling"),
])
def test_benchmark_models_reach_comparison_and_survive_navigation(settings, monkeypatch, names, failed):
    import streamlit as st
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    from OCR.schemas import OCRResult, OCRPage

    class DistinctProvider(FakeProvider):
        def extract(self, document):
            if self.name == failed:
                raise ExtractionError("private diagnostic")
            return OCRResult(document_id=document.document_id, filename=document.filename,
                             source=document.source, source_metadata=document.source_metadata,
                             provider=self.name, text=self.name + " text",
                             markdown="# " + self.name, model_name=self.name + " model",
                             pages=[OCRPage(page_number=1, text=self.name + " page")])

    pdf = Mock(name="pdf"); pdf.name = "sample.pdf"; pdf.size = 15
    pdf.getvalue.return_value = b"%PDF-1.4 mock"
    ref = Mock(name="ref"); ref.name = "truth.md"; ref.size = 5
    ref.getvalue.return_value = b"Hello"
    monkeypatch.setattr(st, "file_uploader", lambda label, **kw: pdf if "PDF" in label else ref)
    monkeypatch.setattr(requests, "get", lambda url, **kw: Mock(
        raise_for_status=lambda: None, json=lambda: {"tools": names, "default": names[0]}
        if url.endswith("/tools") else {"providers": []}))
    service = OCRService(settings, {name: DistinctProvider(name) for name in names})
    with TestClient(create_app(settings, service)) as c:
        responses = []
        def request(method, url, **kwargs):
            kwargs.pop("timeout", None)
            response = c.request(method, "/" + url.split("/", 3)[3], **kwargs)
            responses.append(response.json())
            return response
        monkeypatch.setattr(requests, "request", request)
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "frontend/app.py"), default_timeout=20)
        app.session_state["workspace_navigation"] = "Benchmarking"
        # Reproduce an earlier single-engine extraction being displayed.
        app.session_state["ocr_entries"] = [{"provider": "stale", "result": {"text": "old"}}]
        app.run()
        next(x for x in app.checkbox if x.label.startswith("I confirm the PDF")).check().run()
        next(x for x in app.multiselect if x.label == "OCR providers").set_value(names).run()
        next(x for x in app.button if x.label == "Run Benchmark").click().run()
        assert not app.exception
        rows = responses[0]["results"]
        assert [r["provider"] for r in rows] == names
        for row in rows:
            if row["provider"] != failed:
                assert row["ocr_result"]["text"] == row["provider"] + " text"
        history = c.get("/benchmarks/history").json()
        assert all("ocr_result" not in row and "output" not in row for row in history)
        for page in ["Results & Comparison", "Benchmarking", "Results & Comparison"]:
            app.radio(key="workspace_navigation").set_value(page).run()
            assert not app.exception
            assert [e["provider"] for e in app.session_state["ocr_entries"]] == names
            if page == "Benchmarking":
                continue
            assert [t.label for t in app.tabs if t.label in names] == names
            summary = app.dataframe[0].value
            assert list(summary["Engine"]) == names
            for name in names:
                if name == failed:
                    assert any("extraction_failed" in e.value for e in app.error)
                    assert summary.loc[summary.Engine == name, "Status"].iloc[0] == "Failed"
                else:
                    assert any(t.label == "Extracted text" and t.value == name + " text" for t in app.text_area)
                    assert any(t.label == "Markdown source" and t.value == "# " + name for t in app.text_area)
                    assert any(t.value == name + " page" for t in app.text)
                    assert any(name + " model" in str(df.value) for df in app.dataframe)
                    row = summary[summary.Engine == name].iloc[0]
                    assert row["Characters"] == len(name + " text") and row["Pages"] == 1
                    assert row["OCR seconds"] >= 0
        assert len(responses) == 1

def test_initialization_and_inference_diagnostic_evidence(settings):
    from OCR.provider_diagnostics import diagnose
    from OCR.providers.base import OCRDocument
    doc=OCRDocument(document_id="x",filename="x.pdf",path=settings.temp_dir/"x.pdf")
    service=OCRService(settings,{"tesseract":FakeProvider(failure=ExtractionError("secret"))})
    with pytest.raises(ExtractionError): service.extract(doc,"tesseract",persist_result=False)
    assert diagnose(service)[0]["state"]=="Inference failed"
    class Broken(FakeProvider):
        def initialize(self): raise ProviderInitializationError("secret")
    service=OCRService(settings,{"tesseract":Broken()})
    with pytest.raises(ProviderInitializationError): service.extract(doc,"tesseract",persist_result=False)
    assert diagnose(service)[0]["state"]=="Initialization failed"

def test_reject_inconsistent_imported_metrics(tmp_path):
    store=BenchmarkStore(tmp_path/"history.sqlite3")
    row={"id":"bad","timestamp":datetime.now(timezone.utc).isoformat(),"dataset_id":"A","provider":"p","document_id":"d","reference_hash":"h","status":"success","normalization":{},"method":"levenshtein-jiwer4-v1","metrics":evaluate("abc","abc",Normalization())}
    row["metrics"]["cer"]=0.5
    with pytest.raises(ValueError): store.save(row)


def test_dataset_case_mapping_and_unsafe_imports(settings,tmp_path,monkeypatch):
    import OCR.benchmark_api as backend
    dataset=tmp_path/"datasets"; outputs=tmp_path/"outputs"
    (dataset/"Mix/Markdown_Reference").mkdir(parents=True)
    (dataset/"Mix/Dataset").mkdir(parents=True)
    (outputs/"Mix/old").mkdir(parents=True)
    (dataset/"Mix/Markdown_Reference/Invoice_5.md").write_text("hello",encoding="utf-8")
    (dataset/"Mix/Dataset/invoice_5.pdf").write_bytes(b"%PDF-1.4 mock")
    (outputs/"Mix/old/invoice_5.md").write_text("hello",encoding="utf-8")
    monkeypatch.setattr(backend,"DATASETS",dataset)
    monkeypatch.setattr(backend,"OUTPUTS",outputs)
    with client(settings) as c:
        mapping=c.get("/benchmarks/datasets").json()[0]
        assert mapping["pdf"]=="invoice_5.pdf"
        assert mapping["outputs"]==["Mix/old/invoice_5.md"]
        payload={"dataset":"Mix","reference":"Invoice_5.md","output":"Mix/old/invoice_5.md","confirmed":True}
        row=c.post("/benchmarks/datasets/run",json=payload).json()["results"][0]
        assert row["metrics"]["cer"]==0 and row["duration_seconds"] is None
        assert row["origin"]=="rescored historical output"
        assert c.post("/benchmarks/datasets/run",json={**payload,"confirmed":False}).status_code==400
        assert c.post("/benchmarks/datasets/run",json={**payload,"output":"../../secret.md"}).status_code==400
        assert c.post("/benchmarks/datasets/run",json={**payload,"output":None,"providers":["tesseract"]}).status_code==200
        assert len(c.get("/benchmarks/history").json())==2

def test_comparison_tracks_coverage_and_policy():
    from OCR.evaluation import METHOD
    rows=[]
    for provider, document in (("p1","a"),("p1","b"),("p2","a"),("p2","b")):
        rows.append({"provider":provider,"document_id":document,"reference_hash":document,"dataset_id":"A","timestamp":"2026-10-15","normalization":Normalization().model_dump(),"method":METHOD,"status":"success","metrics":evaluate("abc","abc",Normalization())})
    result=compare_runs(rows)
    assert result["same_document_and_reference"] and all(s["documents"]==2 for s in result["summaries"])
    result=compare_runs(rows[:-1])
    assert not result["same_document_and_reference"]
    rows[-1]["normalization"]["casefold"]=True
    assert not compare_runs(rows)["same_evaluation_policy"]


def test_streamlit_history_keeps_failed_providers_visible(settings,monkeypatch):
    from streamlit.testing.v1 import AppTest
    from pathlib import Path
    monkeypatch.setattr(requests,"get",lambda url,**kwargs:Mock(raise_for_status=lambda:None,json=lambda:{"tools":["tesseract"],"default":"tesseract"} if url.endswith("/tools") else {"providers":[]}))
    with client(settings,ExtractionError("private")) as c:
        assert submit(c).status_code==200
        def request(method,url,**kwargs):
            kwargs.pop("timeout",None)
            return c.request(method,"/"+url.split("/",3)[3],**kwargs)
        monkeypatch.setattr(requests,"request",request)
        app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/"frontend/app.py"),default_timeout=15)
        app.session_state["workspace_navigation"]="Benchmarking"
        app.run()
        next(b for b in app.button if b.label=="Refresh benchmark history").click().run()
        assert not app.exception
        assert app.session_state["gt_history"][0]["status"]=="failed"


def test_qwen_initialization_distinguishes_unreachable_and_missing_tag(settings,monkeypatch):
    import sys, types
    from OCR.providers.qwen_ollama import QwenOllamaProvider
    monkeypatch.setitem(sys.modules,"ollama",types.SimpleNamespace(AsyncClient=Mock()))
    monkeypatch.setattr(requests,"get",Mock(side_effect=requests.ConnectionError()))
    with pytest.raises(ProviderInitializationError,match="server unreachable"):
        QwenOllamaProvider(settings).initialize()
    monkeypatch.setattr(requests,"get",lambda *a,**k:Mock(raise_for_status=lambda:None,json=lambda:{"models":[{"name":"different"}]}))
    with pytest.raises(ProviderInitializationError,match="model tag is unavailable"):
        QwenOllamaProvider(settings).initialize()
    monkeypatch.setattr(requests,"get",lambda *a,**k:Mock(raise_for_status=lambda:None,json=lambda:{"models":[{"name":settings.ollama_ocr_model,"digest":"sha256:test"}]}))
    provider=QwenOllamaProvider(settings)
    provider.initialize()
    assert provider._model_digest=="sha256:test"


def test_paddle_memory_guard_prevents_known_oom(settings,monkeypatch):
    import OCR.resources as resources
    from OCR.errors import ProviderResourceError
    from OCR.providers.paddle_vl import PaddleVLProvider
    monkeypatch.setattr(resources,"memory_capacity_bytes",lambda:4*1024**3)
    assert "safety floor" in resources.paddle_memory_issue(settings)
    with pytest.raises(ProviderResourceError): PaddleVLProvider(settings).initialize()
    monkeypatch.setattr(resources,"memory_capacity_bytes",lambda:16*1024**3)
    assert resources.paddle_memory_issue(settings) is None
    assert resources.paddle_memory_issue(settings.model_copy(update={"paddle_device":"gpu:0"})) is None


def test_interrupted_run_recovery_and_completed_rows_are_immutable(tmp_path):
    store=BenchmarkStore(tmp_path/"history.sqlite3")
    row={"id":"running","timestamp":datetime.now(timezone.utc).isoformat(),"dataset_id":"A","provider":"p","document_id":"d","reference_hash":"h","status":"running"}
    store.save(row)
    store.recover_interrupted()
    restored=store.history()[0]
    assert restored["status"]=="failed" and "interrupted" in restored["error"]
    with pytest.raises(ValueError): store.save({**row,"status":"failed"})

def test_startup_removes_only_owned_interrupted_benchmark_uploads(settings):
    settings.upload_dir.mkdir(parents=True)
    owned=settings.upload_dir/("benchmark-"+"a"*32+".pdf")
    existing=settings.upload_dir/"existing.pdf"
    owned.write_bytes(b"%PDF-1.4")
    existing.write_bytes(b"preserved")
    with client(settings): pass
    assert not owned.exists() and existing.exists()


def test_metric_export_serialization_and_csv_formula_safety(monkeypatch):
    import csv
    import streamlit as st
    from frontend.ground_truth import exports
    captured=[]
    monkeypatch.setattr(st,"download_button",lambda *args,**kwargs:captured.append(args))
    options=Normalization()
    row={"id":"run1","provider":"tesseract","dataset_id":"=SUM(1,1)","status":"success","normalization":options.model_dump(),"metrics":evaluate("مرحبا","مرحبا",options)}
    exports([row],"fixture")
    payload=json.loads(captured[0][1])
    assert payload[0]["metrics"]["cer"]==0 and payload[0]["normalization"]["unicode"]=="NFC"
    record=next(csv.DictReader(io.StringIO(captured[1][1])))
    assert record["dataset_id"]=="'=SUM(1,1)"
    assert record["cer"]=="0.0" and json.loads(record["metrics"])["method"]=="levenshtein-jiwer4-v1"
