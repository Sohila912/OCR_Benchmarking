"""Acquisition and manifest integrity tests use independent tiny fixtures."""

from copy import deepcopy
import hashlib
from io import BytesIO
import json
from pathlib import Path

import pytest

from benchmark_suite import dataset_io as io
from benchmark_suite import dataset_preparation as prep


class Response(BytesIO):
    def __init__(self, body, status=200, headers=None):
        super().__init__(body)
        self.status = status
        self.headers = headers or {"Content-Length": str(len(body))}


def item(body, name="images/page.png"):
    return {"rfilename": name, "size": len(body), "lfs": {"sha256": hashlib.sha256(body).hexdigest()}}


def test_verified_download_reused_without_network_and_tampering_preserved(tmp_path, monkeypatch):
    body = b"independent source bytes"
    calls = []
    def request(req, **kwargs):
        calls.append(req.full_url)
        return Response(body)
    monkeypatch.setattr(io, "urlopen", request)
    downloader = io.Downloader(tmp_path, budget=100, minimum_free=0)
    path = downloader.fetch("publisher/dataset", "a"*40, item(body))
    assert path.read_bytes() == body
    assert len(calls) == 1
    assert downloader.state["charged_bytes"] == len(body)
    resumed = io.Downloader(tmp_path, budget=100, minimum_free=0)
    assert resumed.fetch("publisher/dataset", "a"*40, item(body)) == path
    assert len(calls) == 1
    path.write_bytes(b"corrupted")
    with pytest.raises(ValueError, match="preserved"):
        resumed.fetch("publisher/dataset", "a"*40, item(body))
    assert path.read_bytes() == b"corrupted"


def test_windows_long_unicode_names_have_short_portable_storage(tmp_path, monkeypatch):
    body = b"page"
    monkeypatch.setattr(io, "urlopen", lambda *a, **k: Response(body))
    name = "images/" + "long_name_" * 30 + "\u0627\u0644\u0639\u0631\u0628\u064a\u0629.png"
    path = io.Downloader(tmp_path, minimum_free=0).fetch("owner/data", "a"*40, item(body, name))
    assert len(path.name) == 68
    assert path.read_bytes() == body


def test_partial_download_resumes_correct_range(tmp_path, monkeypatch):
    body = b"0123456789"
    path = io.object_path(tmp_path, "owner/data", "a"*40, "images/page.png")
    path.parent.mkdir(parents=True)
    path.with_name(path.name + ".part").write_bytes(body[:4])
    def request(req, **kwargs):
        assert req.get_header("Range") == "bytes=4-"
        return Response(body[4:], 206, {"Content-Length": "6", "Content-Range": "bytes 4-9/10"})
    monkeypatch.setattr(io, "urlopen", request)
    result = io.Downloader(tmp_path, minimum_free=0).fetch("owner/data", "a"*40, item(body))
    assert result.read_bytes() == body


def test_ignored_range_does_not_append_or_destroy_partial(tmp_path, monkeypatch):
    body = b"0123456789"
    path = io.object_path(tmp_path, "owner/data", "a"*40, "images/page.png")
    path.parent.mkdir(parents=True)
    partial = path.with_name(path.name + ".part")
    partial.write_bytes(body[:4])
    monkeypatch.setattr(io, "urlopen", lambda *a, **k: Response(body))
    with pytest.raises(RuntimeError, match="range"):
        io.Downloader(tmp_path, minimum_free=0).fetch("owner/data", "a"*40, item(body))
    assert partial.read_bytes() == body[:4]


def test_budget_exhaustion_persists_and_cannot_be_silently_increased(tmp_path, monkeypatch):
    body = b"123456"
    monkeypatch.setattr(io, "urlopen", lambda *a, **k: Response(body))
    downloader = io.Downloader(tmp_path, budget=5, minimum_free=0)
    with pytest.raises(RuntimeError, match="budget"):
        downloader.fetch("owner/data", "a"*40, item(body))
    assert downloader.state["charged_bytes"] == 0
    # Persist even a zero-byte attempt so another invocation cannot reset limits.
    io.atomic_json(downloader.path, downloader.state)
    with pytest.raises(ValueError, match="budget"):
        io.Downloader(tmp_path, budget=100, minimum_free=0)


def test_bad_checksum_preserves_evidence_and_no_published_file(tmp_path, monkeypatch):
    monkeypatch.setattr(io, "urlopen", lambda *a, **k: Response(b"bad"))
    downloader = io.Downloader(tmp_path, minimum_free=0)
    with pytest.raises(ValueError, match="SHA-256"):
        downloader.fetch("owner/data", "a"*40, item(b"good"[:3]))
    assert list(tmp_path.rglob("*.part"))[0].read_bytes() == b"bad"
    assert downloader.state["files"] == {}


@pytest.mark.parametrize("path", ["../outside", "/absolute", "C:/outside", "a/../../b", "a\\..\\b"])
def test_path_escape_rejected(tmp_path, path):
    with pytest.raises(ValueError):
        io.safe_path(tmp_path, path)


def test_publish_interruption_resumes_without_second_download(tmp_path, monkeypatch):
    body = b"source"
    calls = []
    def request(*args, **kwargs):
        calls.append(1)
        return Response(body)
    monkeypatch.setattr(io, "urlopen", request)
    original = io.os.replace
    def fail_publication(source, destination):
        if str(source).endswith(".part"):
            raise OSError("interrupted publication")
        return original(source, destination)
    monkeypatch.setattr(io.os, "replace", fail_publication)
    with pytest.raises(OSError):
        io.Downloader(tmp_path, minimum_free=0).fetch("owner/data", "a"*40, item(body))
    monkeypatch.setattr(io.os, "replace", original)
    path = io.Downloader(tmp_path, minimum_free=0).fetch("owner/data", "a"*40, item(body))
    assert path.read_bytes() == body and len(calls) == 1


def test_table_reference_validation_preserves_merged_cell_markup():
    text = '<table><tr><th colspan="2">Title</th></tr><tr><td>A</td><td>B</td></tr></table>'
    assert prep.audit_tables(text) == {"tables": 1, "rows": 2, "cells": 3, "merged_span_attributes": 1, "errors": []}
    assert prep.audit_tables('<table><tr><td rowspan="0">x</td></tr></table>')["errors"] == ["INVALID_CELL_SPAN"]
    assert prep.audit_tables('<table><tr><td>x</tr></table>')["errors"]
    assert prep.audit_tables('| a | b |\n|---|---|')["tables"] == 0


def test_duplicate_groups_remain_disjoint_and_splits_reproducible():
    records = [{"document_id": str(n), "language": "ar" if n % 2 else "en", "file_hash": f"image-{n}",
                "reference_hash": f"ref-{n}"} for n in range(30)]
    records[1]["file_hash"] = records[3]["file_hash"]
    records[1]["reference_hash"] = records[3]["reference_hash"]
    reordered = deepcopy(list(reversed(records)))
    prep.split_records(records, development_per_language=3)
    prep.split_records(reordered, development_per_language=3)
    assert {r["document_id"]: r["split"] for r in records} == {r["document_id"]: r["split"] for r in reordered}
    assert records[1]["split"] == records[3]["split"]
    assert set(r["split"] for r in records) == {"development", "evaluation"}


def test_conflicting_truth_on_identical_images_needs_review():
    rows = [{"document_id": str(i), "language": "en", "file_hash": "same", "reference_hash": str(i)} for i in range(2)]
    with pytest.raises(ValueError, match="conflicting"):
        prep.split_records(rows)


def test_existing_frozen_output_never_overwritten(tmp_path):
    path = tmp_path / "original.md"
    prep.preserve(path, b"original truth")
    prep.preserve(path, b"original truth")
    with pytest.raises(ValueError, match="preserved"):
        prep.preserve(path, b"new convenient truth")
    assert path.read_bytes() == b"original truth"


def test_transient_windows_sharing_violation_retries_atomic_replace(tmp_path, monkeypatch):
    path = tmp_path / "journal.json"
    io.atomic_json(path, {"state": "old"})
    original, attempts = io.os.replace, []
    def replace(source, destination):
        attempts.append(1)
        if len(attempts) < 3:
            assert json.loads(path.read_text()) == {"state": "old"}
            raise PermissionError("temporary Windows file sharing lock")
        return original(source, destination)
    monkeypatch.setattr(io.os, "replace", replace)
    monkeypatch.setattr(io.time, "sleep", lambda duration: None)
    io.atomic_json(path, {"state": "new"})
    assert json.loads(path.read_text()) == {"state": "new"} and len(attempts) == 3


def test_early_windows_download_storage_normalized_without_deleting_bytes(tmp_path):
    root = tmp_path / "datasets/raw"
    repo, revision = prep.PINS["omnidocbench"]
    key = f"{repo}/{revision}/OmniDocBench.json"
    early = io.safe_path(root, key)
    early.parent.mkdir(parents=True)
    early.write_bytes(b"independent original annotation")
    io.atomic_json(root / "acquisition.json", {"schema_version": 1, "budget_bytes": 2200000000,
                                              "charged_bytes": 30, "files": {key: {
                                                  "dataset": repo, "revision": revision,
                                                  "filename": "OmniDocBench.json", "sha256": io.digest(early)}}})
    prep.canonicalize_storage(tmp_path)
    canonical = prep.source_path(tmp_path, "omnidocbench", "OmniDocBench.json")
    assert canonical == io.object_path(root, repo, revision, "OmniDocBench.json")
    assert canonical.read_bytes() == early.read_bytes() == b"independent original annotation"
    prep.canonicalize_storage(tmp_path)  # Recovery/repetition is idempotent.


def test_offline_validation_detects_payload_tampering(tmp_path):
    from pydantic import ValidationError
    image, reference = tmp_path / "image.png", tmp_path / "truth.md"
    image.write_bytes(b"fixture image identity")
    reference.write_bytes(b"independent truth")
    rows = []
    for n, split in enumerate(["development", "evaluation"]):
        source = tmp_path / f"image{n}.png"
        ref = tmp_path / f"truth{n}.md"
        source.write_bytes(image.read_bytes() + bytes([n]))
        ref.write_bytes(reference.read_bytes() + bytes([n]))
        record = prep.base_record(tmp_path, "omnidocbench", str(n), source, ref, 1, 1, "book")
        record.update(annotation_types=["publisher_region_json"], evaluation_capabilities=["text"],
                      split=split, split_group_id=str(n))
        rows.append(prep.ManifestRecord.model_validate(record).model_dump())
    with pytest.raises(ValidationError):
        prep.ManifestRecord.model_validate({**rows[0], "file_hash": "wrong"})
    root = tmp_path / "datasets/manifest"
    root.mkdir(parents=True)
    hashes = {}
    for row in rows:
        path = root / (row["split"] + ".jsonl")
        path.write_text(json.dumps(row) + "\n", encoding="utf-8")
        hashes[path.name] = io.digest(path)
    io.atomic_json(root / "PROVENANCE.json", {"status": "COMPLETED", "pins": prep.PINS,
                                             "manifest_sha256": hashes, "records": 2,
                                             "split_counts": {"development:en": 1, "evaluation:en": 1}})
    assert prep.validate(tmp_path)["records"] == 2
    (tmp_path / "truth1.md").write_bytes(b"altered")
    with pytest.raises(ValueError, match="changed"):
        prep.validate(tmp_path)
