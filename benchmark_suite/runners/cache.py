"""Checksummed immutable bundles, serialized by one OS coordinator lock.

Production ResultCache was assessed: its settings/native/remote fingerprint is
application-specific. This store retains raw bytes and the benchmark envelope,
and uses the same kernel-lock/atomic-publication principles without HTTP probes.
"""

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time
from uuid import uuid4

from benchmark_suite.dataset_io import atomic_json, digest, safe_path
from .schemas import Prediction


def json_bytes(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def fingerprint(value):
    return hashlib.sha256(json_bytes(value)).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def write_new(path, data):
    with Path(path).open("xb") as stream:
        stream.write(data); stream.flush(); os.fsync(stream.fileno())


class IntegrityError(RuntimeError):
    pass


@contextmanager
def coordinator_lock(path):
    """Fail immediately if another runner holds the same suite lock.

    Persistent lock file is never removed; the OS releases ownership on death.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as stream:
        if stream.seek(0, os.SEEK_END) == 0:
            stream.write(b"0"); stream.flush()
        stream.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise RuntimeError("A benchmark coordinator is already active") from exc
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == "nt":
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def publish_bundle(destination, files, metadata):
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.parent / ("." + uuid4().hex + ".tmp")
    temporary.mkdir()
    checksums = {}
    for name, payload in files.items():
        path = safe_path(temporary, name)
        path.parent.mkdir(parents=True, exist_ok=True)
        write_new(path, payload)
        checksums[name] = hashlib.sha256(payload).hexdigest()
    write_new(temporary / "bundle.json", json_bytes({"files": checksums, "metadata": metadata}))
    # Caller holds the suite lock. Orphan temporary directories are preserved.
    # Windows scanners can briefly hold a just-written directory open. Retry
    # only this specific sharing/access error; never replace an existing bundle.
    for attempt in range(10):
        try:
            if destination.exists():
                raise FileExistsError(destination)
            os.rename(temporary, destination)
            break
        except PermissionError as exc:
            if getattr(exc, "winerror", None) != 5 or attempt == 9:
                raise
            time.sleep(.1)


def read_bundle(path):
    path = Path(path)
    try:
        manifest = json.loads((path / "bundle.json").read_bytes())
        for name, expected in manifest["files"].items():
            if digest(safe_path(path, name)) != expected:
                raise IntegrityError("Artifact checksum mismatch")
        return manifest
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise IntegrityError(f"Incomplete/corrupt bundle at {path}; preserved for inspection") from exc


class PredictionCache:
    def __init__(self, root):
        self.root = Path(root)

    def path(self, key):
        if len(key) != 64 or any(c not in "0123456789abcdef" for c in key):
            raise ValueError("Cache keys must be SHA256")
        return self.root / key

    def get(self, key):
        path = self.path(key)
        if not path.exists():
            return None
        manifest = read_bundle(path)
        if manifest["metadata"]["cache_key"] != key or manifest["metadata"]["status"] != "SUCCESS":
            raise IntegrityError("Cache identity/status mismatch")
        prediction = Prediction.model_validate_json((path / "prediction.json").read_bytes())
        return prediction, (path / "raw.bin").read_bytes(), manifest["metadata"]

    def put(self, key, prediction, raw, metadata):
        publish_bundle(self.path(key), {"raw.bin": raw,
                       "prediction.json": json_bytes(prediction.model_dump(mode="json"))},
                       dict(metadata, cache_key=key, status="SUCCESS"))


def save_progress(path, value):
    atomic_json(Path(path), value)
