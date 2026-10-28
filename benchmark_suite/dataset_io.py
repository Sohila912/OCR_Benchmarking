"""Bounded, resumable downloads of explicitly pinned public dataset files."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import tempfile
import time
from typing import Any
from urllib.request import Request, urlopen
from urllib.parse import quote

GIB = 1024 ** 3


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def replace_file(source: Path, destination: Path) -> None:
    """Retry only transient Windows sharing locks without losing atomicity."""
    for attempt in range(7):
        try:
            os.replace(source, destination)
            return
        except PermissionError:
            if attempt == 6:
                raise
            time.sleep(0.05 * 2 ** attempt)


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        replace_file(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def safe_path(root: Path, relative: str) -> Path:
    parts = PurePosixPath(relative)
    if parts.is_absolute() or not parts.parts or any(p in {"..", "."} or ":" in p or "\\" in p for p in parts.parts):
        raise ValueError(f"Unsafe dataset path: {relative!r}")
    candidate = root.joinpath(*parts.parts).resolve()
    if not candidate.is_relative_to(root.resolve()):
        raise ValueError("Dataset path escapes its storage root.")
    return candidate


def object_path(root: Path, dataset: str, revision: str, name: str) -> Path:
    """Short stable storage name, independent of Windows long-path settings."""
    key = f"{dataset}/{revision}/{name}"
    safe_path(root, key)  # Validate remote paths even though storage is hashed.
    return root / "objects" / (hashlib.sha256(key.encode()).hexdigest() + PurePosixPath(name).suffix)


class Downloader:
    """One coordinator, with a persisted conservative payload-byte budget.

    Reserve bytes before each read so a killed process cannot lose budget
    accounting. A killed/failed read may consume its reservation without having
    delivered bytes. Retries never exceed the original cumulative budget.
    Signed CDN URLs are never persisted. No credentials or shared global cache.
    """

    def __init__(self, root: Path, budget: int = 2_200_000_000,
                 minimum_free: int = 6 * GIB):
        if type(budget) is not int or budget <= 0 or type(minimum_free) is not int or minimum_free < 0:
            raise ValueError("Budget/reserve must be valid nonnegative integer byte limits.")
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "acquisition.json"
        self.state = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {
            "schema_version": 1, "budget_bytes": budget, "charged_bytes": 0, "files": {}}
        if self.state["budget_bytes"] != budget:
            raise ValueError("Cannot silently change an acquisition budget.")
        if (self.state.get("schema_version") != 1 or not isinstance(self.state.get("files"), dict)
                or type(self.state.get("charged_bytes")) is not int
                or not 0 <= self.state["charged_bytes"] <= budget):
            raise ValueError("Malformed acquisition journal; do not reset budget or file history.")
        self.minimum_free = minimum_free
        if not self.path.exists():
            atomic_json(self.path, self.state)

    def fetch(self, dataset: str, revision: str, item: dict[str, Any]) -> Path:
        name, size = item["rfilename"], item["size"]
        if not isinstance(size, int) or size <= 0:
            raise ValueError("Remote file needs a positive declared size.")
        key = f"{dataset}/{revision}/{name}"
        expected = item.get("lfs", {}).get("sha256")
        entry = self.state["files"].get(key)
        destination = safe_path(self.root, entry["storage_path"]) if entry and "storage_path" in entry else (
            safe_path(self.root, key) if entry else object_path(self.root, dataset, revision, name))
        if destination.exists():
            actual = digest(destination)
            if destination.stat().st_size != size or (expected and actual != expected):
                raise ValueError(f"Existing file differs from pinned source; preserved: {name}")
            if not entry or entry.get("sha256") != actual:
                raise ValueError(f"Unjournaled or changed file; explicit recovery needed: {name}")
            return destination
        if shutil.disk_usage(self.root).free < self.minimum_free + size:
            raise RuntimeError("Insufficient disk: preserve reserve plus incoming file size.")
        destination.parent.mkdir(parents=True, exist_ok=True)
        partial = destination.with_name(destination.name + ".part")
        offset = partial.stat().st_size if partial.exists() else 0
        if offset > size:
            raise ValueError("Partial file is larger than pinned source; preserved for diagnosis.")
        url = f"https://huggingface.co/datasets/{quote(dataset, safe='/')}/resolve/{quote(revision, safe='')}/{quote(name, safe='/')}"
        if offset < size:
            headers = {"User-Agent": "OCR-Benchmark-Acquisition/1.0", "Accept-Encoding": "identity"}
            if offset:
                headers["Range"] = f"bytes={offset}-"
            with urlopen(Request(url, headers=headers), timeout=60) as response:
                if offset and (response.status != 206 or not response.headers.get("Content-Range", "").startswith(f"bytes {offset}-")):
                    raise RuntimeError("Server did not honor resume range; partial file preserved.")
                length = response.headers.get("Content-Length")
                if length and int(length) != size - offset:
                    raise ValueError("Remote length differs from pinned metadata.")
                with partial.open("ab") as stream:
                    while offset < size:
                        amount = min(1024 * 1024, size - offset)
                        if self.state["charged_bytes"] + amount > self.state["budget_bytes"]:
                            raise RuntimeError("Approved cumulative transfer budget exhausted.")
                        self.state["charged_bytes"] += amount
                        atomic_json(self.path, self.state)
                        block = response.read(amount)
                        self.state["charged_bytes"] -= amount - len(block)
                        atomic_json(self.path, self.state)
                        if not block:
                            raise IOError("Remote file ended before its declared size.")
                        stream.write(block)
                        stream.flush()
                        offset += len(block)
                    os.fsync(stream.fileno())
        actual = digest(partial)
        if expected and actual != expected:
            raise ValueError(f"Pinned SHA-256 mismatch; partial preserved: {name}")
        if not expected and item.get("blobId"):
            blob = hashlib.sha1(f"blob {size}\0".encode())
            with partial.open("rb") as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    blob.update(block)
            if blob.hexdigest() != item["blobId"]:
                raise ValueError(f"Git blob digest mismatch; partial preserved: {name}")
        entry = {"dataset": dataset, "revision": revision, "filename": name, "bytes": size,
                 "sha256": actual, "advertised_sha256": expected,
                 "advertised_git_blob": item.get("blobId"),
                 "storage_path": destination.relative_to(self.root).as_posix(),
                 "source_url": url, "downloaded_at": datetime.now(timezone.utc).isoformat(),
                 "verified": True}
        # Journal before publication: a kill here leaves a complete .part that
        # the next invocation rehashes and publishes without another transfer.
        self.state["files"][key] = entry
        atomic_json(self.path, self.state)
        replace_file(partial, destination)
        display = name.encode("ascii", errors="backslashreplace").decode("ascii")
        print(f"Verified {display} ({size:,} bytes); budget charged {self.state['charged_bytes']:,}", flush=True)
        return destination
