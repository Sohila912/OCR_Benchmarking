"""Bounded Docling CPU trials with an explicitly authorized OCR backend."""

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import socket
import shutil
import subprocess
import sys
import time
import traceback
from uuid import uuid4

GIB = 1024**3
SUITE = Path(__file__).resolve().parents[1]


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")


def worker(args):
    if args.model == "granite_docling":
        from granite_trial import worker as granite_worker
        return granite_worker(args)
    from windows_job import limit_current_process

    output = args.output
    phase = "memory_guard"
    state = {"scope": "bounded feasibility trial, not benchmark evaluation", "language": args.language,
             "memory_limit_bytes": args.memory_limit, "status": "RUNNING", "documents_processed": 0}
    started = time.perf_counter()
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
        socket.setdefaulttimeout(30)
        limit_current_process(args.memory_limit)
        print(f"Memory cap applied: {args.memory_limit / GIB:.2f} GiB committed memory", flush=True)
        root = args.asset_root
        cache = args.cache_root or root
        (root / "tmp").mkdir(parents=True, exist_ok=True)
        for name, value in {
            "HF_HOME": str(cache / "hf"), "XDG_CACHE_HOME": str(cache / "cache"),
            "TORCH_HOME": str(cache / "torch"), "TEMP": str(root / "tmp"), "TMP": str(root / "tmp"),
            "EASYOCR_MODULE_PATH": str(root / "easyocr"), "CUDA_VISIBLE_DEVICES": "",
            "OMP_NUM_THREADS": "2", "MKL_NUM_THREADS": "2", "HF_HUB_DISABLE_XET": "1",
            "HF_HUB_DISABLE_SYMLINKS_WARNING": "1", "HF_HUB_DOWNLOAD_TIMEOUT": "30",
            "HF_HUB_ETAG_TIMEOUT": "20", "TOKENIZERS_PARALLELISM": "false",
        }.items():
            os.environ[name] = value
        phase = "imports"
        print(f"Importing pinned CPU Docling for {args.model}", flush=True)
        import torch
        from docling.datamodel.accelerator_options import AcceleratorOptions
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import EasyOcrOptions, PdfPipelineOptions, TesseractCliOcrOptions
        from docling.datamodel.settings import settings
        from docling.document_converter import DocumentConverter, ImageFormatOption

        threads = 1 if args.model == "docling_tesseract" else 2
        torch.set_num_threads(threads)
        torch.set_num_interop_threads(1)
        state["versions"] = {name: importlib.metadata.version(name) for name in
                             ("docling", "docling-slim", "torch", "torchvision", "transformers")}
        state["model"] = args.model
        state["torch_cuda"] = torch.version.cuda
        if torch.version.cuda is not None:
            raise RuntimeError("Expected the copied CPU-only Torch build")
        phase = "configuration"
        settings.cache_dir = cache / "docling"
        settings.cache_dir.mkdir(parents=True, exist_ok=True)
        if args.model == "docling_tesseract":
            os.environ["TESSDATA_PREFIX"] = str(root / "tessdata")
            os.environ["OMP_THREAD_LIMIT"] = "1"
            executable = str(root / "native" / "tesseract.exe")
            state["native_tesseract_version"] = subprocess.run(
                [executable, "--version"], capture_output=True, check=True, timeout=15
            ).stdout.decode("utf-8").splitlines()[0]
            ocr = TesseractCliOcrOptions(
                lang=["eng"] if args.language == "en" else ["ara"], force_full_page_ocr=True,
                tesseract_cmd=executable, path=str(root / "tessdata"), psm=3,
            )
        else:
            language = ["en"] if args.language == "en" else ["ar", "en"]
            ocr = EasyOcrOptions(lang=language, force_full_page_ocr=True, use_gpu=False,
                                 model_storage_directory=str(root / "easyocr" / "model"), download_enabled=True)
            state["versions"]["easyocr"] = importlib.metadata.version("easyocr")
        options = PdfPipelineOptions(
            do_ocr=True, do_table_structure=True,
            do_picture_classification=False, do_picture_description=False,
            do_code_enrichment=False, do_formula_enrichment=False,
            enable_remote_services=False, document_timeout=180,
            accelerator_options=AcceleratorOptions(device="cpu", num_threads=threads),
            ocr_options=ocr, layout_batch_size=1, ocr_batch_size=1, table_batch_size=1,
        )
        state["pipeline_options"] = options.model_dump(mode="json")
        write_json(output / "configuration.json", state)
        phase = "model_initialization_and_asset_download"
        print(f"Initializing standard image pipeline: {args.model}", flush=True)
        converter = DocumentConverter(allowed_formats=[InputFormat.IMAGE],
                                      format_options={InputFormat.IMAGE: ImageFormatOption(pipeline_options=options)})
        before = time.perf_counter()
        converter.initialize_pipeline(InputFormat.IMAGE)
        state["initialization_seconds_including_downloads"] = time.perf_counter() - before
        record = json.loads(args.record.read_text(encoding="utf-8"))
        frozen_source = SUITE / record["source_path"]
        if hashlib.sha256(frozen_source.read_bytes()).hexdigest() != record["file_hash"]:
            raise RuntimeError("Frozen image checksum mismatch")
        inputs = root / "inputs"
        inputs.mkdir(parents=True, exist_ok=True)
        source = inputs / (record["file_hash"] + frozen_source.suffix)
        if not source.exists():
            with frozen_source.open("rb") as incoming, source.open("xb") as outgoing:
                shutil.copyfileobj(incoming, outgoing)
        if hashlib.sha256(source.read_bytes()).hexdigest() != record["file_hash"]:
            raise RuntimeError("D: input-copy checksum mismatch")
        phase = "inference"
        state["document_id"] = record["document_id"]
        state["source_sha256"] = record["file_hash"]
        state["processing_input_path"] = str(source)
        print(f"Converting one frozen {args.language} development image", flush=True)
        before = time.perf_counter()
        result = converter.convert(source, raises_on_error=True)
        state["conversion_seconds"] = time.perf_counter() - before
        state["conversion_status"] = str(result.status)
        state["conversion_errors"] = [str(error) for error in result.errors]
        if str(result.status.value) != "success":
            raise RuntimeError(f"Conversion status: {result.status}")
        phase = "save_outputs"
        write_json(output / "document.json", result.document.export_to_dict())
        (output / "prediction.md").write_text(result.document.export_to_markdown(), encoding="utf-8")
        state.update(status="SUCCESS", documents_processed=1)
    except Exception as exc:
        state.update(status="FAILED", phase=phase, error_type=type(exc).__name__, error=str(exc),
                     traceback=traceback.format_exc())
        traceback.print_exc()
    finally:
        state["wall_seconds"] = time.perf_counter() - started
        write_json(output / "result.json", state)
        print(json.dumps({k: state[k] for k in ("status", "language", "documents_processed")}), flush=True)
    return 0 if state["status"] == "SUCCESS" else 1


def supervise(args):
    import psutil

    args.asset_root.mkdir(parents=True, exist_ok=True)
    records = [json.loads(line) for line in (SUITE / "datasets/manifest/development.jsonl").read_text(encoding="utf-8").splitlines()]
    directory = args.asset_root / "trials" / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8])
    directory.mkdir(parents=True, exist_ok=False)
    outcome = {"scope": "bounded feasibility trial, not benchmark evaluation", "directory": str(directory),
               "asset_root": str(args.asset_root), "python": str(args.python), "attempts": [],
               "maximum_memory_limit_gib": args.max_memory_gib, "model": args.model,
               "user_authorization": "Selected model task is explicitly approved; record actual trial outcome", "accuracy_scores": None}
    print(f"Trial artifacts: {directory}", flush=True)
    for language in ("en", "ar"):
        available = psutil.virtual_memory().available
        if available < 2 * GIB:
            outcome["blocked_reason"] = "Available RAM below retained 2-GiB generic floor before worker start"
            break
        limit = min(int(args.max_memory_gib * GIB), available - int(.75 * GIB))
        current = directory / language
        current.mkdir()
        record = next(item for item in records if item["language"] == language)
        write_json(current / "input.json", record)
        command = [str(args.python), str(Path(__file__).resolve()), "--worker", "--asset-root", str(args.asset_root),
                   "--output", str(current), "--record", str(current / "input.json"), "--language", language,
                   "--memory-limit", str(limit), "--model", args.model]
        if args.cache_root:
            command.extend(["--cache-root", str(args.cache_root)])
        start = time.monotonic()
        rss_peak = private_peak = 0
        free_min = available
        abort = None
        with (current / "process.log").open("x", encoding="utf-8") as log:
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
            while process.poll() is None:
                try:
                    own = psutil.Process(process.pid)
                    infos = [child.memory_info() for child in [own, *own.children(recursive=True)]]
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
                    from windows_job import kill_owned_process_tree
                    kill_owned_process_tree(process.pid)
                    process.wait()
                    break
                time.sleep(.1)
        attempt = {"language": language, "exit_code": process.returncode, "memory_limit_bytes": limit,
                   "sampled_peak_rss_bytes": rss_peak, "sampled_peak_private_bytes": private_peak,
                   "minimum_system_available_bytes": free_min, "guard_abort": abort,
                   "wall_seconds": time.monotonic() - start}
        if (current / "result.json").exists():
            attempt["worker_result"] = json.loads((current / "result.json").read_text(encoding="utf-8"))
        outcome["attempts"].append(attempt)
        write_json(directory / "trial.json", outcome)
        print(json.dumps(attempt, default=str), flush=True)
        if process.returncode:
            break
    outcome["status"] = "SUCCESS" if len(outcome["attempts"]) == 2 and all(x["exit_code"] == 0 for x in outcome["attempts"]) else "NOT_COMPLETED"
    write_json(directory / "trial.json", outcome)
    print(f"Trial {outcome['status']}: {directory}", flush=True)
    return 0 if outcome["status"] == "SUCCESS" else 1


def main(default_model="docling_easyocr"):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", type=Path)
    parser.add_argument("--asset-root", type=Path, required=True)
    parser.add_argument("--cache-root", type=Path)
    parser.add_argument("--model", choices=("docling_easyocr", "docling_tesseract", "granite_docling"), default=default_model)
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--record", type=Path)
    parser.add_argument("--language", choices=("en", "ar"))
    parser.add_argument("--memory-limit", type=int)
    parser.add_argument("--max-memory-gib", type=float, default=2.5)
    args = parser.parse_args()
    if not 0 < args.max_memory_gib <= 4:
        parser.error("Maximum trial commit-memory cap must be positive and at most 4 GiB")
    sys.path.insert(0, str(SUITE.parent))
    from benchmark_suite.runners.preflight import authorize_model
    authorize_model(args.model, SUITE / "BENCHMARK_STATUS.json")
    if args.worker:
        if not all((args.output, args.record, args.language, args.memory_limit)):
            parser.error("Worker requires output, record, language and memory limit")
        return worker(args)
    if not args.python:
        parser.error("Supervisor requires the explicit isolated --python")
    return supervise(args)


if __name__ == "__main__":
    raise SystemExit(main())
