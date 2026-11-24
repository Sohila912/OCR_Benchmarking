import hashlib
import json

import pytest

from benchmark_suite.scripts import try_unlimited_ocr_demo as demo


def test_evaluation_order_retains_unequal_language_counts(tmp_path, monkeypatch):
    monkeypatch.setattr(demo, "SUITE", tmp_path)
    records = [{"document_id": name, "language": lang, "split": "evaluation"}
               for name, lang in [("a1", "ar"), ("a2", "ar"), ("a3", "ar"), ("e1", "en")]]
    manifest = tmp_path / "datasets/manifest/evaluation.jsonl"
    manifest.parent.mkdir(parents=True)
    manifest.write_text("\n".join(json.dumps(r) for r in records), encoding="utf-8")
    _, ordered = demo.load_records("evaluation")
    assert [r["document_id"] for r in ordered] == ["e1", "a1", "a2", "a3"]


@pytest.mark.parametrize("arguments", [["--evaluation"], ["--evaluation", "--max-new-pages", "0"]])
def test_evaluation_requires_positive_request_budget(monkeypatch, arguments):
    monkeypatch.setattr("sys.argv", ["demo", *arguments])
    with pytest.raises(SystemExit) as exc:
        demo.main()
    assert exc.value.code == 2


def test_session_budget_stops_requests(tmp_path, monkeypatch):
    from benchmark_suite.runners import preflight

    monkeypatch.setattr(demo, "ROOT", tmp_path)
    monkeypatch.setattr(demo, "SUITE", tmp_path)
    monkeypatch.setattr(preflight, "authorize_model", lambda *args: None)
    records = []
    for name in ("first", "second"):
        source = tmp_path / f"{name}.png"
        source.write_bytes(name.encode())
        records.append({"document_id": name, "language": "en", "file_hash": hashlib.sha256(source.read_bytes()).hexdigest(),
                        "source_path": source.name})
    manifest = tmp_path / "manifest.jsonl"
    manifest.write_text("frozen", encoding="utf-8")
    monkeypatch.setattr(demo, "load_records", lambda split: (manifest, records))

    class Reply:
        def __init__(self, data):
            self.data = data
        def raise_for_status(self):
            pass
        def json(self):
            return self.data
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def iter_lines(self, **kwargs):
            return iter(['event: complete', 'data: [{"done": true, "truncated": false}]'])

    posts = []
    class Session:
        def get(self, url, **kwargs):
            return Reply({"sha": "78c27d176793811cf8b5e74b62ceb04dd773c29a"})
        def post(self, url, **kwargs):
            posts.append(url)
            return Reply(["uploaded.png"] if url.endswith("upload") else {"event_id": "test"})

    monkeypatch.setattr(demo.requests, "Session", Session)
    monkeypatch.setattr("sys.argv", ["demo", "--evaluation", "--max-new-pages", "1"])
    assert demo.main() == 1  # Partial split is never reported complete.
    saved = json.loads(next((tmp_path / "demo_trials").glob("*/trial.json")).read_text(encoding="utf-8"))
    assert len(posts) == 2  # One upload and one inference request.
    assert saved["fresh_successes"] == 1
    assert saved["unattempted_documents"] == 1
    assert saved["stop_reason"] == "SESSION_PAGE_BUDGET_REACHED"


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def trial(root, name, record=None, previous=None):
    directory = root / "demo_trials" / name
    write(directory / "trial.json", {"host": demo.HOST, "model": "baidu/Unlimited-OCR-2",
        "parameters": {"instruction": "", "mode": "auto", "max_page_tokens": 20000},
        "reuse_source": str(previous) if previous else None})
    if record:
        page = directory / "page"
        write(page / "input.json", record)
        write(page / "result.json", {"status": "SUCCESS", "document_id": record["document_id"],
            "source_sha256": record["file_hash"]})
        write(page / "response.json", {"done": True, "truncated": False})
        (page / (record["file_hash"] + ".png")).write_bytes(record["document_id"].encode())
    return directory


def test_reuse_chain_retains_prior_and_new_successes_without_requests(tmp_path, monkeypatch):
    monkeypatch.setattr(demo, "ROOT", tmp_path)
    records = [{"document_id": name, "file_hash": hashlib.sha256(name.encode()).hexdigest(),
                "source_path": "original.png"} for name in ("first", "next")]
    old = trial(tmp_path, "old", records[0])
    latest = trial(tmp_path, "latest", records[1], old)
    results = demo.reusable_results(latest, records)
    assert set(results) == {"first", "next"}
    assert all(item["reused"] for item in results.values())
    (old / "page" / (records[0]["file_hash"] + ".png")).write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="verification"):
        demo.reusable_results(latest, records)


def test_cyclic_reuse_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(demo, "ROOT", tmp_path)
    directory = tmp_path / "demo_trials" / "cycle"
    trial(tmp_path, "cycle", previous=directory)
    with pytest.raises(ValueError, match="Cyclic"):
        demo.reusable_results(directory, [])
