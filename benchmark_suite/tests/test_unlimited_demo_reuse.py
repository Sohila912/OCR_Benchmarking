import hashlib
import json

import pytest

from benchmark_suite.scripts import try_unlimited_ocr_demo as demo


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
