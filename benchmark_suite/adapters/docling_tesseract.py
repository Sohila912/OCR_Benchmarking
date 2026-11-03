"""Shared-runner bridge to a memory-capped CPU Docling/Tesseract worker on D:."""

import json
from pathlib import Path
import queue
import shutil
import subprocess
import threading
import time
from uuid import uuid4

import psutil

from .base import BenchmarkAdapter, RawOutput
from benchmark_suite.runners.schemas import Prediction
from benchmark_suite.scripts.windows_job import kill_owned_process_tree


class DoclingTesseractAdapter(BenchmarkAdapter):
    def __init__(self, spec):
        self.spec = spec
        self.process = None
        self.current_language = None
        self.stop = None
        self.log = None

    def _receive(self, timeout):
        try:
            line = self.messages.get(timeout=timeout)
        except queue.Empty as exc:
            self.cleanup()
            raise TimeoutError("Docling worker response deadline exceeded") from exc
        if line is None:
            code = self.process.poll() if self.process else None
            self.cleanup()
            raise RuntimeError(f"Docling worker exited ({code}); see {self.log_path}")
        return json.loads(line)

    def _start(self, language):
        self.cleanup()
        opts = self.config.adapter_options
        root = Path(opts["asset_root"])
        logs = root / "worker_logs"
        logs.mkdir(parents=True, exist_ok=True)
        self.log_path = logs / (uuid4().hex + ".log")
        self.log = self.log_path.open("x", encoding="utf-8")
        cap = min(opts["maximum_job_memory_bytes"], psutil.virtual_memory().available - 768 * 1024**2)
        if cap < 1024**3:
            raise RuntimeError("Insufficient RAM for bounded Docling worker")
        worker = Path(__file__).resolve().parents[1] / "scripts/docling_tesseract_worker.py"
        self.process = subprocess.Popen([opts["worker_python"], str(worker), "--asset-root", str(root),
            "--cache-root", opts["cache_root"], "--language", language, "--memory-limit", str(cap)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.log,
            text=True, encoding="utf-8", bufsize=1)
        self.messages = queue.Queue()
        process, messages = self.process, self.messages

        def read():
            for line in process.stdout:
                messages.put(line)
            messages.put(None)

        self.reader = threading.Thread(target=read, daemon=True)
        self.reader.start()
        self.stop = threading.Event()
        stop = self.stop

        def guard():
            while not stop.wait(.1) and process.poll() is None:
                if psutil.virtual_memory().available < 512 * 1024**2:
                    kill_owned_process_tree(process.pid)
                    return

        threading.Thread(target=guard, daemon=True).start()
        ready = self._receive(180)
        if ready.get("event") != "ready" or ready["versions"] != opts["worker_versions"]:
            self.cleanup()
            raise RuntimeError("Pinned worker version/initialization mismatch")
        self.ready = ready
        self.current_language = language

    def initialize(self, config):
        self.config = config
        # Frozen both-language cohorts start with Arabic; other cohorts are explicit.
        self._start("ar" if config.language == "both" else config.language)

    def prepare(self, document):
        language = document.source_metadata["language"]
        switch_seconds = 0.0
        if language != self.current_language or self.process is None or self.process.poll() is not None:
            started = time.perf_counter()
            self._start(language)
            switch_seconds = time.perf_counter() - started
        root = Path(self.config.adapter_options["asset_root"]) / "inputs"
        root.mkdir(parents=True, exist_ok=True)
        path = root / (document.source_metadata["source_sha256"] + document.path.suffix)
        if not path.exists():
            with document.path.open("rb") as incoming, path.open("xb") as outgoing:
                shutil.copyfileobj(incoming, outgoing)
        return document.model_copy(update={"path": path}), switch_seconds

    def predict(self, prepared):
        document, switch_seconds = prepared
        command = {"operation": "convert", "document": document.model_dump(mode="json"),
                   "model_revision": self.spec.model_revision}
        try:
            self.process.stdin.write(json.dumps(command, ensure_ascii=False) + "\n")
            self.process.stdin.flush()
            reply = self._receive(300)
            if not reply.get("ok"):
                raise RuntimeError(f"{reply.get('error_type')}: {reply.get('error')}")
            reply["payload"]["worker"] = {"log": str(self.log_path), "ready": self.ready,
                                           "language_switch_initialization_seconds": switch_seconds}
            return RawOutput(json.dumps(reply["payload"], ensure_ascii=False).encode("utf-8"), "application/json")
        except Exception:
            self.cleanup()
            raise

    def normalize_output(self, raw, document):
        return Prediction.model_validate(json.loads(raw.data)["prediction"])

    def get_capabilities(self):
        return self.spec.capabilities

    def get_metadata(self):
        return self.spec

    def cleanup(self):
        if self.stop is not None:
            self.stop.set()
        if self.process is not None:
            if self.process.poll() is None:
                kill_owned_process_tree(self.process.pid)
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                pass
            self.reader.join(timeout=2)
            for stream in (self.process.stdin, self.process.stdout):
                if stream:
                    stream.close()
        if self.log is not None:
            self.log.close()
        self.process = self.log = self.stop = None
        self.current_language = None


def create_adapter(spec):
    return DoclingTesseractAdapter(spec)
