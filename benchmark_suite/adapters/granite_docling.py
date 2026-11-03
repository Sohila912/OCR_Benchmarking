"""Fresh bounded CPU Granite worker per page; every startup is timed in inference."""

import hashlib
import json
from pathlib import Path
import subprocess
import time
from uuid import uuid4

import psutil

from .base import BenchmarkAdapter, RawOutput
from benchmark_suite.runners.schemas import Prediction
from benchmark_suite.scripts.windows_job import kill_owned_process_tree


class GraniteDoclingAdapter(BenchmarkAdapter):
    worker_model = "granite_docling"
    def __init__(self, spec):
        self.spec = spec
        self.process = None

    def initialize(self, config):
        self.config = config

    def predict(self, document):
        opts = self.config.adapter_options
        root = Path(opts["asset_root"])
        output = root / "development_outputs" / uuid4().hex
        output.mkdir(parents=True, exist_ok=False)
        digest = hashlib.sha256(document.path.read_bytes()).hexdigest()
        if digest != document.source_metadata["source_sha256"]:
            raise ValueError("Frozen source checksum mismatch")
        record = {"source_path": str(document.path.resolve()), "file_hash": digest,
                  "document_id": document.document_id, "benchmark_document": document.model_dump(mode="json")}
        (output / "input.json").write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
        available = psutil.virtual_memory().available
        if available < opts.get("minimum_available_ram_bytes", 3 * 1024**3):
            raise RuntimeError("Available RAM below the configured development worker floor")
        cap = min(opts["maximum_job_memory_bytes"], available - 768 * 1024**2)
        script = Path(__file__).resolve().parents[1] / "scripts/docling_trial.py"
        command = [opts["worker_python"], str(script), "--worker", "--model", self.worker_model,
                   "--asset-root", str(root), "--output", str(output), "--record", str(output / "input.json"),
                   "--language", document.source_metadata["language"], "--memory-limit", str(cap)]
        before = time.monotonic()
        try:
            with (output / "process.log").open("x", encoding="utf-8") as log:
                self.process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
                while self.process.poll() is None:
                    if psutil.virtual_memory().available < 512 * 1024**2:
                        raise MemoryError("System available RAM below 512 MiB")
                    if time.monotonic() - before > 900:
                        raise TimeoutError("Granite worker exceeded 15-minute page deadline")
                    time.sleep(.1)
            (output / "process_exit.json").write_text(json.dumps({"exit_code": self.process.returncode}), encoding="utf-8")
            if not (output / "result.json").is_file():
                raise RuntimeError(f"Granite worker exited ({self.process.returncode}) without a result; see {output / 'process.log'}")
            state = json.loads((output / "result.json").read_text(encoding="utf-8"))
            if self.process.returncode or state["status"] != "SUCCESS":
                raise RuntimeError(f"{state.get('error_type', state['status'])}: {state.get('error')}; {output}")
            if state["versions"] != opts["worker_versions"]:
                raise RuntimeError("Pinned Granite worker version mismatch")
            payload = {"prediction": json.loads((output / "prediction.json").read_text(encoding="utf-8")),
                       "worker_result": state, "native_output_directory": str(output)}
            return RawOutput(json.dumps(payload, ensure_ascii=False).encode("utf-8"), "application/json")
        finally:
            self.cleanup()

    def normalize_output(self, raw, document):
        return Prediction.model_validate(json.loads(raw.data)["prediction"])

    def get_capabilities(self):
        return self.spec.capabilities

    def get_metadata(self):
        return self.spec

    def cleanup(self):
        if self.process is not None:
            if self.process.poll() is None:
                kill_owned_process_tree(self.process.pid)
            self.process.wait(timeout=10)
        self.process = None


def create_adapter(spec):
    return GraniteDoclingAdapter(spec)
