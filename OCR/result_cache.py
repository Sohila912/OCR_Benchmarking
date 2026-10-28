"""Persistent OCR jobs; SQLite claims plus OS locks fence live and crashed workers."""
import hashlib
import inspect
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import platform
import tempfile
import time
from contextlib import contextmanager
from functools import lru_cache
from importlib.metadata import distributions
from pathlib import Path
from uuid import uuid4

import requests

from OCR.errors import ExtractionError, ProviderInitializationError, ProviderNotReadyError
from OCR.schemas import OCRResult


def digest_json(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False, allow_nan=False).encode()).hexdigest()


@lru_cache(maxsize=8192)
def _file_digest(path, size, mtime, ctime, inode):
    with open(path, "rb") as stream:
        digest = hashlib.sha256()
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
        return digest.hexdigest()


def file_digest(path):
    path = Path(path).resolve()
    stat = path.stat()
    return _file_digest(str(path), stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns, stat.st_ino)


def assets(path):
    if path is None:
        return None
    root = Path(path)
    if not root.exists():
        return {"missing": str(root)}
    if root.is_file():
        return file_digest(root)
    return {p.relative_to(root).as_posix(): file_digest(p)
            for p in sorted(root.rglob("*")) if p.is_file()}


def fingerprint(settings, provider):
    """Resolve identity before inference, including mutable local assets and remote tags.

    Conservatively include installed package versions and OCR source (prompts,
    preprocessing and schema assembly). Never key on request filenames/reference text.
    """
    operational = {"upload_dir", "temp_dir", "output_dir", "benchmark_db", "benchmark_retention_days",
                   "api_url", "api_host", "api_port", "retain_uploads", "provider",
                   "cache_enabled", "cache_wait_seconds", "cache_pipeline_revision"}
    configuration = {k: v for k, v in settings.model_dump(mode="json").items() if k not in operational}
    name = provider.health().provider
    identity = {"provider": name, "class": type(provider).__module__ + "." + type(provider).__qualname__,
                "model_name": getattr(provider, "model_name", name),
                "model_version": getattr(provider, "model_version", None)}
    source = Path(__file__).parent
    pipeline = [source / p for p in ("service.py", "pdf.py", "schemas.py", "resources.py",
                                    "result_cache.py", "providers/base.py", "providers/common.py")]
    configuration["pipeline_sources"] = {p.relative_to(source).as_posix(): file_digest(p) for p in pipeline}
    try:
        implementation = inspect.getsourcefile(type(provider))
    except TypeError:
        implementation = None  # Dynamically supplied adapters use cache_identity().
    if implementation and Path(implementation).is_file():
        configuration["adapter_source"] = file_digest(implementation)
    configuration["adapter_configuration"] = provider.cache_identity()
    configuration["pipeline_revision"] = settings.cache_pipeline_revision
    configuration["packages"] = sorted((d.metadata.get("Name", ""), d.version) for d in distributions())
    configuration["runtime"] = [sys.version, platform.system(), platform.machine()]
    configuration["environment"] = {k: os.environ.get(k) for k in (
        "TESSDATA_PREFIX", "OMP_THREAD_LIMIT", "OMP_NUM_THREADS", "CUDA_VISIBLE_DEVICES",
        "FLAGS_use_mkldnn", "PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK")}
    # Custom providers can supply an explicit deterministic identity without loading a model.
    from OCR.providers.common import LocalProvider
    if isinstance(provider, LocalProvider):
        directories = {"docling": [settings.docling_artifacts_path],
                       "paddle_vl": [settings.paddle_vl_model_dir, settings.paddle_layout_model_dir]}
        configuration["assets"] = [assets(p) for p in directories.get(name, [])]
        configuration["native"] = {}
        for command in ("pdfinfo", "pdftoppm"):
            suffix = ".exe" if os.name == "nt" else ""
            path = str(settings.poppler_path / (command + suffix)) if settings.poppler_path else shutil.which(command)
            configuration["native"][command] = assets(path) if path else None
        if name in ("tesseract", "docling"):
            try:
                version = subprocess.run([settings.tesseract_cmd, "--version"], capture_output=True,
                                         text=True, encoding="utf-8", errors="replace", check=True, timeout=10)
                languages = subprocess.run([settings.tesseract_cmd, "--list-langs"], capture_output=True,
                                           text=True, encoding="utf-8", errors="replace", check=True, timeout=10)
                identity["model_version"] = version.stdout or version.stderr
                executable = shutil.which(settings.tesseract_cmd)
                configuration["native"]["tesseract"] = assets(executable) if executable else None
                configuration["native"]["tesseract_versions"] = identity["model_version"]
                listing = languages.stdout + languages.stderr
                match = re.search(r'List of available languages in "([^"]+)"', listing)
                if not match:
                    raise ValueError("Cannot resolve Tesseract language asset directory.")
                configuration["traineddata"] = assets(Path(match[1]))
            except (OSError, ValueError, subprocess.SubprocessError) as exc:
                raise ProviderInitializationError("Cannot resolve Tesseract cache identity.", provider=name) from exc
        if name == "docling":
            identity.update(model_name="Docling standard PDF + Tesseract", model_version=settings.docling_model_revision)
        elif name == "paddle_vl":
            identity.update(model_name="PaddleOCR-VL-1.6-0.9B", model_version=settings.paddle_model_revision)
        elif name == "qwen_ollama":
            from OCR.providers.qwen_ollama import OCR_PROMPT
            configuration["prompt"] = OCR_PROMPT
            try:
                response = requests.get(settings.ollama_host + "/api/tags", timeout=(3, 5))
                response.raise_for_status()
                model = next(m for m in response.json()["models"] if m.get("name") == settings.ollama_ocr_model)
                if not model.get("digest"):
                    raise ValueError("Missing model digest")
                identity.update(model_name=settings.ollama_ocr_model, model_version=model["digest"])
            except (requests.RequestException, ValueError, KeyError, TypeError, AttributeError, StopIteration) as exc:
                raise ProviderInitializationError("Cannot resolve Ollama model digest for safe cache lookup.", provider=name) from exc
    return {**identity, "config_hash": digest_json(configuration)}


class ResultCache:
    def __init__(self, output_dir, wait_seconds=7200):
        self.root = Path(output_dir)
        self.directory = self.root / "cache"
        self.directory.mkdir(parents=True, exist_ok=True)
        self.db = self.directory / "jobs.sqlite3"
        self.wait_seconds = wait_seconds
        # Changing journal mode can return SQLITE_BUSY immediately on a brand-new
        # database. Serialize first-use initialization across processes as well.
        with self.locked("schema"):
            with self.connect() as db:
                db.execute("PRAGMA journal_mode=WAL")
                db.execute("""CREATE TABLE IF NOT EXISTS ocr_jobs (
                    cache_key TEXT PRIMARY KEY, document_id TEXT NOT NULL, identity TEXT NOT NULL,
                    state TEXT NOT NULL CHECK(state IN ('pending','processing','completed','failed')),
                    owner TEXT, attempts INTEGER NOT NULL DEFAULT 0, updated REAL NOT NULL,
                    completed REAL, result_file TEXT, result_sha256 TEXT, error TEXT)""")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.db, timeout=30)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    @contextmanager
    def locked(self, key):
        """Kernel releases this lock after process death. Never steal a live job by age.

        Lock files must remain in place: unlinking a locked inode breaks exclusion.
        """
        path = self.directory / (key + ".lock")
        with path.open("a+b") as lock:
            lock.seek(0, os.SEEK_END)
            if lock.tell() == 0:
                lock.write(b"0")
                lock.flush()
            deadline = time.monotonic() + self.wait_seconds
            while True:
                try:
                    lock.seek(0)
                    if os.name == "nt":
                        import msvcrt
                        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
                    else:
                        import fcntl
                        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except OSError:
                    if time.monotonic() >= deadline:
                        message = "OCR job is still processing; retry later or increase OCR_CACHE_WAIT_SECONDS."
                        raise ProviderNotReadyError(message, public_message=message)
                    time.sleep(0.05)
            try:
                yield
            finally:
                lock.seek(0)
                if os.name == "nt":
                    msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

    def load(self, row, document_id, provider):
        try:
            # Never trust a DB path to address files outside the output directory.
            filename = row["result_file"]
            if not filename or Path(filename).name != filename:
                return None
            path = self.directory / filename
            if path.is_symlink():
                return None
            payload = path.read_bytes()
            if hashlib.sha256(payload).hexdigest() != row["result_sha256"]:
                return None
            result = OCRResult.model_validate_json(payload)
            if (result.document_id != document_id or result.provider != provider or result.errors
                    or any(p.errors for p in result.pages or [])):
                return None
            return result
        except (OSError, ValueError, TypeError):
            return None

    def run(self, document, identity, compute, force=False, requested_at=None):
        requested = time.time() if requested_at is None else requested_at
        key = digest_json({"document_id": document.document_id, **identity})
        with self.connect() as db:
            db.execute("INSERT OR IGNORE INTO ocr_jobs(cache_key, document_id, identity, state, updated) VALUES(?,?,?,'pending',?)",
                       (key, document.document_id, json.dumps(identity, sort_keys=True), requested))
        with self.locked(key):
            owner = uuid4().hex
            # Read/check files outside the write transaction, under the per-key lock.
            # Other document keys can still be claimed while a large result is validated.
            with self.connect() as db:
                row = db.execute("SELECT * FROM ocr_jobs WHERE cache_key=?", (key,)).fetchone()
            result = self.load(row, document.document_id, identity["provider"]) if row["state"] == "completed" else None
            if result is not None and (not force or (row["completed"] or 0) >= requested):
                return self.present(result, document, key, identity, "hit", row["completed"])
            with self.connect() as db:
                db.execute("BEGIN IMMEDIATE")
                # Lock ownership proves a previous processing owner is dead; recover immediately.
                changed = db.execute("UPDATE ocr_jobs SET state='processing', owner=?, attempts=attempts+1, updated=?, error=NULL WHERE cache_key=? AND state=? AND owner IS ?",
                                     (owner, time.time(), key, row["state"], row["owner"])).rowcount
                if changed != 1:
                    raise ExtractionError("OCR cache claim changed unexpectedly; retry the request.")
            try:
                self.clean_orphans(key, row["result_file"])
                result = compute()
                if result.errors or any(p.errors for p in result.pages or []):
                    self.fail(key, owner, "Partial extraction; not reusable.")
                    return self.present(result, document, key, identity, "not_cached", None)
                completed = time.time()
                # A generation-specific filename leaves the previous completed file intact on crash.
                filename = key + "-" + owner + ".json"
                payload = result.model_dump_json(indent=2).encode("utf-8")
                temporary = None
                try:
                    with tempfile.NamedTemporaryFile(dir=self.directory, prefix=key + "-", suffix=".tmp", delete=False) as stream:
                        temporary = Path(stream.name)
                        stream.write(payload)
                        stream.flush()
                        os.fsync(stream.fileno())
                    os.replace(temporary, self.directory / filename)
                    # Persist the rename before committing the completed DB state.
                    if os.name != "nt":
                        directory_fd = os.open(self.directory, os.O_RDONLY)
                        try:
                            os.fsync(directory_fd)
                        finally:
                            os.close(directory_fd)
                finally:
                    if temporary is not None:
                        temporary.unlink(missing_ok=True)
                with self.connect() as db:
                    changed = db.execute("UPDATE ocr_jobs SET state='completed', updated=?, completed=?, result_file=?, result_sha256=?, error=NULL WHERE cache_key=? AND owner=? AND state='processing'",
                                         (completed, completed, filename, hashlib.sha256(payload).hexdigest(), key, owner)).rowcount
                    if changed != 1:
                        raise ExtractionError("OCR cache claim was lost; result was not published.")
                self.clean_orphans(key, filename)
                return self.present(result, document, key, identity, "reprocessed" if force else "miss", completed)
            except BaseException:
                self.fail(key, owner, "OCR processing or persistence failed; retry is allowed.")
                raise

    def clean_orphans(self, key, keep):
        """Called only while owning this key's kernel lock, never delete live work."""
        for path in self.directory.glob(key + "-*"):
            if path.name != keep and path.suffix in (".json", ".tmp"):
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass  # Cleanup must not invalidate a successfully committed result.

    def fail(self, key, owner, error):
        with self.connect() as db:
            db.execute("UPDATE ocr_jobs SET state='failed', updated=?, error=? WHERE cache_key=? AND owner=? AND state='processing'",
                       (time.time(), error, key, owner))

    @staticmethod
    def present(result, document, key, identity, status, completed):
        result = result.model_copy(deep=True)
        # Cached OCR belongs to bytes, while upload provenance belongs to this request.
        result.filename, result.source = document.filename, document.source
        result.source_metadata = dict(document.source_metadata)
        result.provider_metadata["cache"] = {"status": status, "key": key, "identity": identity,
                                             "state": "failed" if status == "not_cached" else "completed",
                                             "completed_at": completed}
        return result
