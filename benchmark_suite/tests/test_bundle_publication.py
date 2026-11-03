import pytest

from benchmark_suite.runners import cache


def test_transient_windows_access_denial_retries_without_losing_bundle(tmp_path, monkeypatch):
    original = cache.os.rename
    calls = []

    def rename(source, destination):
        calls.append(source)
        if len(calls) == 1:
            error = PermissionError("Scanner sharing conflict")
            error.winerror = 5
            raise error
        original(source, destination)

    monkeypatch.setattr(cache.os, "rename", rename)
    monkeypatch.setattr(cache.time, "sleep", lambda _: None)
    destination = tmp_path / "bundle"
    cache.publish_bundle(destination, {"raw.bin": b"original"}, {"status": "SUCCESS"})
    assert cache.read_bundle(destination)["metadata"]["status"] == "SUCCESS"
    assert (destination / "raw.bin").read_bytes() == b"original"
    assert len(calls) == 2
    with pytest.raises(FileExistsError):
        cache.publish_bundle(destination, {"raw.bin": b"replacement"}, {})
    assert (destination / "raw.bin").read_bytes() == b"original"


def test_other_permission_errors_are_preserved_without_retry(tmp_path, monkeypatch):
    def denied(*args):
        raise PermissionError("Not a transient Windows scanner error")

    monkeypatch.setattr(cache.os, "rename", denied)
    monkeypatch.setattr(cache.time, "sleep", lambda _: pytest.fail("Unexpected retry"))
    with pytest.raises(PermissionError):
        cache.publish_bundle(tmp_path / "bundle", {"raw.bin": b"retained"}, {})
    assert len(list(tmp_path.glob("*.tmp/raw.bin"))) == 1
