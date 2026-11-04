"""Bounded English development continuation; retain native outputs on D:."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
from uuid import uuid4

import psutil

from docling_trial import GIB, SUITE, write_json
from windows_job import kill_owned_process_tree


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset-root", type=Path, required=True)
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--reuse", type=Path, required=True,
                        help="Successful scale-1 English page or completed continuation directory")
    args = parser.parse_args()
    sys.path.insert(0, str(SUITE.parent))
    from benchmark_suite.runners.preflight import authorize_model

    authorize_model("docling_easyocr", SUITE / "BENCHMARK_STATUS.json")
    records = [json.loads(line) for line in
               (SUITE / "datasets/manifest/development.jsonl").read_text(encoding="utf-8").splitlines()]
    records = [record for record in records if record["language"] == "en"]
    pages = [args.reuse]
    if (args.reuse / "artifact_manifest.json").is_file():
        hashes = json.loads((args.reuse / "artifact_manifest.json").read_text(encoding="utf-8"))
        for name, expected in hashes.items():
            path = (args.reuse / name).resolve()
            if not path.is_relative_to(args.reuse.resolve()) or digest(path) != expected:
                raise ValueError("Prior continuation artifact checksum mismatch")
        pages = sorted(p.parent for p in args.reuse.glob("*/result.json"))
    reusable = {}
    for page in pages:
        prior_record = json.loads((page / "input.json").read_text(encoding="utf-8"))
        prior = json.loads((page / "result.json").read_text(encoding="utf-8"))
        if prior.get("status") != "SUCCESS":
            continue
        if (prior_record not in records or prior.get("source_sha256") != prior_record["file_hash"]
                or prior["pipeline_options"]["ocr_options"]["scale"] != 1.0
                or prior.get("model") != "docling_easyocr"
                or not (page / "document.json").is_file()
                or not (page / "prediction.md").is_file()):
            raise ValueError("Reuse requires a successful identical-input scale-1 EasyOCR result")
        reusable[prior_record["document_id"]] = (page, prior)
    if not reusable:
        raise ValueError("No successful verified English pages to reuse")
    directory = args.asset_root / "english_development" / (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8])
    directory.mkdir(parents=True, exist_ok=False)
    worker = Path(__file__).with_name("docling_trial.py")
    summary = {"scope": "English frozen development continuation; not full evaluation",
               "model": "docling_easyocr", "easyocr_scale": 1.0, "target_pages": len(records),
               "attempts": [], "accuracy_scores": None,
               "worker_sha256": digest(worker), "driver_sha256": digest(Path(__file__)),
               "manifest_sha256": digest(SUITE / "datasets/manifest/development.jsonl"),
               "python": str(args.python.resolve()), "status": "IN_PROGRESS"}
    shutil.copy2(worker, directory / "worker_source.py")
    shutil.copy2(__file__, directory / "driver_source.py")
    print(f"English development: {directory}", flush=True)
    for index, record in enumerate(records, 1):
        for key, checksum in (("source_path", "file_hash"), ("ground_truth_reference", "reference_hash")):
            if digest(SUITE / record[key]) != record[checksum]:
                raise ValueError("Frozen source/reference checksum mismatch")
        page = directory / f"{index:03}-en"
        page.mkdir()
        write_json(page / "input.json", record)
        if record["document_id"] in reusable:
            source, prior = reusable[record["document_id"]]
            for name in ("result.json", "document.json", "prediction.md", "configuration.json", "process.log"):
                shutil.copy2(source / name, page / name)
            attempt = {"document_id": record["document_id"], "status": "SUCCESS", "reused": True,
                       "reuse_source": str(source.resolve()),
                       "source_document_json_sha256": digest(source / "document.json"),
                       "worker_result": prior, "output_directory": str(page)}
        else:
            free = psutil.virtual_memory().available
            if free < 2 * GIB:
                summary["blocked_reason"] = "Available RAM below retained 2-GiB start floor"
                break
            limit = min(4 * GIB, free - int(.75 * GIB))
            command = [str(args.python), str(worker), "--worker", "--model", "docling_easyocr",
                       "--asset-root", str(args.asset_root), "--output", str(page),
                       "--record", str(page / "input.json"), "--language", "en",
                       "--memory-limit", str(limit), "--easyocr-scale", "1"]
            start = time.monotonic()
            rss_peak = private_peak = 0
            free_min, abort = free, None
            with (page / "process.log").open("x", encoding="utf-8") as log:
                process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
                while process.poll() is None:
                    try:
                        own = psutil.Process(process.pid)
                        infos = [p.memory_info() for p in [own, *own.children(recursive=True)]]
                        rss_peak = max(rss_peak, sum(info.rss for info in infos))
                        private_peak = max(private_peak, sum(getattr(info, "private", 0) for info in infos))
                    except psutil.Error:
                        pass
                    free_min = min(free_min, psutil.virtual_memory().available)
                    if free_min < .5 * GIB:
                        abort = "SYSTEM_AVAILABLE_RAM_BELOW_512_MIB"
                    elif time.monotonic() - start > 1200:
                        abort = "TWENTY_MINUTE_WORKER_TIMEOUT"
                    if abort:
                        kill_owned_process_tree(process.pid)
                        process.wait()
                        break
                    time.sleep(.1)
            result = json.loads((page / "result.json").read_text(encoding="utf-8")) if (page / "result.json").exists() else None
            success = process.returncode == 0 and result and result.get("status") == "SUCCESS"
            attempt = {"document_id": record["document_id"], "status": "SUCCESS" if success else "FAILED",
                       "reused": False, "exit_code": process.returncode, "memory_limit_bytes": limit,
                       "sampled_peak_rss_bytes": rss_peak, "sampled_peak_private_bytes": private_peak,
                       "minimum_system_available_bytes": free_min, "guard_abort": abort,
                       "wall_seconds": time.monotonic() - start, "worker_result": result,
                       "output_directory": str(page)}
        summary["attempts"].append(attempt)
        write_json(directory / "summary.json", summary)
        print(f"{index}/{len(records)} {attempt['status']} reused={attempt['reused']}", flush=True)
        if attempt.get("guard_abort"):
            summary["blocked_reason"] = attempt["guard_abort"]
            break
    summary["successes"] = sum(item["status"] == "SUCCESS" for item in summary["attempts"])
    summary["failed_pages"] = sum(item["status"] == "FAILED" for item in summary["attempts"])
    summary["unattempted_pages"] = len(records) - len(summary["attempts"])
    summary["status"] = "SUCCESS" if summary["successes"] == len(records) else "NOT_COMPLETED"
    write_json(directory / "summary.json", summary)
    write_json(directory / "artifact_manifest.json", {
        p.relative_to(directory).as_posix(): digest(p) for p in directory.rglob("*") if p.is_file()})
    print(f"English {summary['status']}: {summary['successes']}/{len(records)} successful", flush=True)
    return 0 if summary["status"] == "SUCCESS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
