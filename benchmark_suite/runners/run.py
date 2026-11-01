"""One explicitly approved model per invocation; fixtures exercise the runner only."""

from datetime import datetime, timezone
import csv
import json
import os
from pathlib import Path
import threading
import time
from uuid import uuid4

import psutil

from OCR.providers.base import OCRDocument
from benchmark_suite.dataset_io import digest, safe_path
from benchmark_suite.dataset_preparation import ManifestRecord, PINS
from . import preflight
from .cache import (IntegrityError, PredictionCache, coordinator_lock, fingerprint,
                    json_bytes, now, publish_bundle, read_bundle, save_progress, write_new)
from .schemas import Prediction


class MemorySample:
    """Sample this process plus descendants; sampled RSS is not allocator peak."""
    def __init__(self, device="cpu"):
        self.device = device

    def __enter__(self):
        self.peak = 0
        self.gpu_peak = None
        self.stop = threading.Event()

        def sample():
            while True:
                try:
                    root = psutil.Process()
                    total = 0
                    for process in [root, *root.children(recursive=True)]:
                        try:
                            total += process.memory_info().rss
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                    self.peak = max(self.peak, total)
                except psutil.Error:
                    pass
                if self.stop.wait(.05):
                    break
        self.thread = threading.Thread(target=sample, daemon=True)
        self.thread.start()
        def sample_gpu():
            while True:
                try:
                    process = psutil.Process()
                    pids = {process.pid, *(p.pid for p in process.children(recursive=True))}
                    reply = preflight.run_probe(["nvidia-smi", f"--id={self.device.split(':')[1]}",
                        "--query-compute-apps=pid,used_gpu_memory", "--format=csv,noheader,nounits"], timeout=1)
                    value = gpu_bytes(reply.get("stdout", ""), pids) if reply["status"] == "OK" else None
                    if value is not None:
                        self.gpu_peak = max(self.gpu_peak or 0, value)
                except (psutil.Error, ValueError, KeyError):
                    pass
                if self.stop.wait(1):
                    break
        self.gpu_thread = None
        if self.device.startswith("cuda:"):
            self.gpu_thread = threading.Thread(target=sample_gpu, daemon=True)
            self.gpu_thread.start()
        return self

    def __exit__(self, *_):
        self.stop.set(); self.thread.join()
        if self.gpu_thread is not None:
            self.gpu_thread.join()


def gpu_bytes(output, pids):
    """WDDM N/A or no observed own context yields null, never a fabricated zero."""
    values = []
    for row in csv.reader(output.splitlines()):
        if len(row) != 2:
            continue
        try:
            pid = int(row[0])
        except ValueError:
            continue
        if pid in pids:
            try:
                value = float(row[1])
                import math
                if not math.isfinite(value) or value < 0:
                    return None
                values.append(value*1024**2)
            except ValueError:
                return None
    return int(sum(values)) if values else None


def load_records(root, manifest, config):
    root, manifest = Path(root).resolve(), Path(manifest).resolve()
    provenance_path = root / "datasets/manifest/PROVENANCE.json"
    provenance = json.loads(provenance_path.read_bytes())
    expected = provenance["manifest_sha256"].get(manifest.name)
    if manifest.parent != provenance_path.parent or expected is None or digest(manifest) != expected:
        raise IntegrityError("Manifest is not the frozen provenance artifact")
    records = [ManifestRecord.model_validate_json(line).model_dump() for line in manifest.read_text(encoding="utf-8").splitlines()]
    if len({r["document_id"] for r in records}) != len(records):
        raise IntegrityError("Duplicate manifest document IDs")
    records = [r for r in records if config.language == "both" or r["language"] == config.language]
    if not records:
        raise ValueError("Empty selected cohort")
    for record in records:
        if config.purpose != "fixture" and (record["dataset_name"], record["dataset_version"]) not in PINS.values():
            raise IntegrityError("Unapproved dataset version")
        for path_key, hash_key in (("source_path", "file_hash"), ("ground_truth_reference", "reference_hash")):
            if digest(safe_path(root, record[path_key])) != record[hash_key]:
                raise IntegrityError("Frozen source/reference checksum mismatch")
    return records, {"manifest_sha256": expected, "provenance_sha256": digest(provenance_path),
                     "selected_document_ids": [r["document_id"] for r in records],
                     "splits": sorted({r["split"] for r in records})}


def code_identity():
    root = Path(__file__).resolve().parents[2]
    files = [*sorted((root/"benchmark_suite/adapters").glob("*.py")),
             *(root/"benchmark_suite/runners"/name for name in ("schemas.py", "cache.py", "run.py", "preflight.py")),
             root/"OCR/schemas.py", root/"OCR/providers/base.py"]
    return {p.relative_to(root).as_posix(): digest(p) for p in files}


def _hardware_identity(observed):
    return {k: observed.get(k) for k in ("os", "cpu", "python", "logical_cpus", "physical_cpus")} | {
        "gpus": [{k: g.get(k) for k in ("name", "driver_version", "compute_capability", "vram_total_mib")} for g in observed.get("gpus", [])]}


def run(root, manifest, spec, config, factory, *, resume=None, probe=None, after_cache=None):
    """Execute a single candidate. No model factories are bundled in TASK-007.

    Injected probes/hooks are for synthetic fixture tests only. Real runs always
    read live resources. A completed run is immutable; retry failures in a new run
    and reuse only its validated successes. Resume accepts incomplete runs only.
    """
    session_started = time.perf_counter()
    root = Path(root).resolve()
    preflight.authorize(spec, config, root/"BENCHMARK_STATUS.json")
    if config.purpose != "fixture" and (probe is not None or after_cache is not None):
        raise ValueError("Live benchmark preflight cannot be replaced by test hooks")
    probe = probe or preflight.snapshot
    with coordinator_lock(root/"cache/coordinator.lock"):
        records, dataset = load_records(root, manifest, config)
        observed = probe(root)
        preflight.check(spec, config, observed, root.parent)
        environment = preflight.environment()
        identity = {"schema_version": 1, "spec": spec.model_dump(mode="json"),
                    "config": config.model_dump(mode="json"), "code": code_identity(),
                    "environment": environment, "hardware": _hardware_identity(observed)}
        identity_hash = fingerprint(identity)
        descriptor = {"identity": identity, "identity_hash": identity_hash, "dataset": dataset}
        runs = root/"results"/spec.model_id
        if resume is None:
            run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
            directory = runs/run_id
            directory.mkdir(parents=True, exist_ok=False)
            write_new(directory/"run_manifest.json", json_bytes(dict(descriptor, created_at=now())))
            write_new(directory/"config.json", json_bytes(config.model_dump(mode="json")))
            write_new(directory/"environment.json", json_bytes(dict(environment, hardware=observed)))
        else:
            directory = Path(resume).resolve()
            if directory.parent != runs or (directory/"completion.json").exists():
                raise ValueError("Resume requires an incomplete run under this model's results directory")
            original = json.loads((directory/"run_manifest.json").read_bytes())
            if {k: original[k] for k in descriptor} != descriptor:
                raise IntegrityError("Cannot resume changed data, config, model, code, environment or hardware identity")
        session = uuid4().hex[:12]
        sessions = directory/"sessions"
        sessions.mkdir(exist_ok=True)
        write_new(sessions/f"{session}-start.json", json_bytes({"time": now(), "hardware": observed}))
        cache = PredictionCache(root/"cache/predictions")
        adapter, initialized, initialization_seconds, inferred = None, False, None, 0
        completed, failures = 0, 0
        outcome = "INTERRUPTED"
        session_error = None
        try:
            for record in records:
                _verify_record(root, record)
                key = fingerprint({"identity": identity_hash, "document_id": record["document_id"], "source_sha256": record["file_hash"]})
                receipt_path = directory/"documents"/fingerprint(record["document_id"])[:24]
                if receipt_path.exists():
                    receipt = read_bundle(receipt_path)["metadata"]
                    if receipt["cache_key"] != key or receipt["document_id"] != record["document_id"]:
                        raise IntegrityError("Resume document identity mismatch")
                    completed += 1
                    failures += receipt["status"] != "SUCCESS"
                    continue
                cached = cache.get(key)
                if cached is not None:
                    prediction, raw, metadata = cached
                    _validate_prediction(prediction, record)
                    if metadata["document_id"] != record["document_id"] or metadata["source_sha256"] != record["file_hash"]:
                        raise IntegrityError("Cached document/source identity mismatch")
                    metadata = dict(metadata, cache_hit=True, replay_session=session)
                    files = {"raw.bin": raw, "prediction.json": json_bytes(prediction.model_dump(mode="json"))}
                else:
                    # Recheck immediately before loading and each uncached page.
                    current = probe(root)
                    preflight.check(spec, config, current, root.parent)
                    if adapter is None:
                        adapter = factory()
                        _validate_adapter(adapter, spec)
                        started = time.perf_counter()
                        try:
                            with MemorySample(config.device) as initialization_memory:
                                adapter.initialize(config)
                        finally:
                            initialization_seconds = time.perf_counter()-started
                        initialized = True
                        _validate_adapter(adapter, spec)
                        write_new(sessions/f"{session}-initialized.json", json_bytes({"seconds": initialization_seconds,
                                  "sampled_peak_rss_bytes": initialization_memory.peak,
                                  "sampled_peak_gpu_vram_bytes": initialization_memory.gpu_peak, "hardware": current}))
                        # Initialization can consume the available-memory budget.
                        # The requirement is peak additional headroom, conservatively
                        # rechecked in full; model tasks must document its estimate.
                        preflight.check(spec, config, probe(root), root.parent)
                    document = OCRDocument(document_id=record["document_id"], filename=Path(record["source_path"]).name,
                        path=safe_path(root, record["source_path"]), source=record["dataset_name"],
                        source_metadata={"source_sha256": record["file_hash"], "language": record["language"],
                                         "width": record["width"], "height": record["height"]})
                    started = time.perf_counter()
                    raw = b""
                    files = {}
                    metadata = {"document_id": record["document_id"], "cache_key": key, "source_sha256": record["file_hash"],
                                "origin_run": directory.name, "session": session, "cache_hit": False,
                                "inference_temperature": "cold" if inferred == 0 else "warm", "started_at": now(),
                                "gpu_vram_peak_bytes": None, "gpu_measurement_status": "NOT_MEASURED",
                                "memory_method": "sampled process+descendants RSS, 50ms; not allocator peak"}
                    try:
                        with MemorySample(config.device) as memory:
                            phase = time.perf_counter(); prepared = adapter.prepare(document)
                            metadata["preprocess_seconds"] = time.perf_counter()-phase
                            inferred += 1
                            phase = time.perf_counter(); output = adapter.predict(prepared)
                            metadata["inference_seconds"] = time.perf_counter()-phase
                            if not isinstance(output.data, bytes):
                                raise TypeError("Raw output must be bytes")
                            raw = output.data
                            metadata["raw_media_type"] = output.media_type
                            files["raw.bin"] = raw
                            phase = time.perf_counter(); prediction = adapter.normalize_output(output, document)
                            prediction = Prediction.model_validate(prediction)
                            metadata["postprocess_seconds"] = time.perf_counter()-phase
                            _validate_prediction(prediction, record)
                            _verify_record(root, record)
                            _validate_adapter(adapter, spec)
                            files["prediction.json"] = json_bytes(prediction.model_dump(mode="json"))
                            if prediction.result.errors or any(p.errors for p in prediction.result.pages or []):
                                raise RuntimeError("Provider reported document/page errors; output retained, not cached")
                        metadata.update(status="SUCCESS", sampled_peak_rss_bytes=memory.peak,
                                        gpu_vram_peak_bytes=memory.gpu_peak,
                                        gpu_measurement_status="SAMPLED" if memory.gpu_peak is not None else "UNAVAILABLE_OR_NO_CONTEXT_SAMPLE" if config.device.startswith("cuda:") else "NOT_APPLICABLE_CPU",
                                        processing_seconds=time.perf_counter()-started)
                        cache.put(key, prediction, raw, metadata)
                        if after_cache is not None:
                            after_cache(key)
                    except Exception as exc:
                        metadata.update(status="FAILED", error_type=type(exc).__name__, error=str(exc)[:2000],
                                        processing_seconds=time.perf_counter()-started)
                        files["error.json"] = json_bytes({"type": type(exc).__name__, "detail": str(exc)[:2000]})
                publish_bundle(receipt_path, files, metadata)
                completed += 1
                failures += metadata["status"] != "SUCCESS"
                save_progress(directory/"progress.json", {"state": "IN_PROGRESS", "completed": completed,
                              "failed": failures, "total": len(records), "session": session, "updated_at": now()})
            outcome = "COMPLETED_WITH_FAILURES" if failures else "COMPLETED"
        except preflight.PreflightBlocked:
            outcome = "BLOCKED_BY_HARDWARE"
            raise
        except Exception as exc:
            outcome = "ARTIFACT_INTEGRITY_ERROR" if isinstance(exc, IntegrityError) else "FAILED_INITIALIZATION" if adapter is not None and not initialized else "INTERRUPTED"
            session_error = {"error_type": type(exc).__name__, "error": str(exc)[:2000]}
            raise
        finally:
            cleanup = None
            if adapter is not None:
                try:
                    adapter.cleanup()
                except Exception as exc:
                    cleanup = {"error_type": type(exc).__name__, "error": str(exc)[:2000]}
            write_new(sessions/f"{session}-end.json", json_bytes({"time": now(), "state": outcome,
                      "initialized": initialized, "initialization_seconds": initialization_seconds,
                      "inferred_documents": inferred, "cleanup_error": cleanup, "error": session_error,
                      "session_wall_seconds": time.perf_counter()-session_started}))
            save_progress(directory/"progress.json", {"state": outcome, "completed": completed,
                          "failed": failures, "total": len(records), "session": session, "updated_at": now()})
        # Completion contains all document-bundle hashes, so later evaluation can
        # verify the run without any adapter, cache, CUDA or model resources.
        hashes = {p.parent.name: digest(p) for p in sorted((directory/"documents").glob("*/bundle.json"))}
        write_new(directory/"completion.json", json_bytes({"state": outcome, "finished_at": now(),
                  "identity_hash": identity_hash, "completed": completed, "failed": failures, "documents": hashes,
                  "files": {name: digest(directory/name) for name in ["run_manifest.json", "config.json", "environment.json",
                            *(p.relative_to(directory).as_posix() for p in sorted(sessions.glob("*.json")))]}}))
        return directory


def _validate_prediction(prediction, record):
    if prediction.result.document_id != record["document_id"]:
        raise IntegrityError("Adapter returned a different document identity")
    if prediction.result.pages is not None and [p.page_number for p in prediction.result.pages] != [1]:
        raise IntegrityError("The frozen image unit requires exactly one explicit page")
    if any(t.page_number != 1 for t in prediction.tables or []):
        raise IntegrityError("Table refers to a nonexistent image page")


def _verify_record(root, record):
    for path_key, hash_key in (("source_path", "file_hash"), ("ground_truth_reference", "reference_hash")):
        if digest(safe_path(root, record[path_key])) != record[hash_key]:
            raise IntegrityError("Source/reference changed before or during document execution")


def _validate_adapter(adapter, spec):
    if adapter.get_metadata() != spec or adapter.get_capabilities() != spec.capabilities:
        raise IntegrityError("Adapter metadata/capabilities changed from the preflight spec")
