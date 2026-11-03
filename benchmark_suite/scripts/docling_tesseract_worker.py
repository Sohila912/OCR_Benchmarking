"""Pinned CPU Docling/Tesseract worker; local JSON-line IPC, no downloads."""

import argparse
from contextlib import redirect_stdout
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import sys
import time
import traceback
from uuid import uuid4


def send(value):
    print(json.dumps(value, ensure_ascii=False), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset-root", type=Path, required=True)
    parser.add_argument("--cache-root", type=Path, required=True)
    parser.add_argument("--language", choices=("en", "ar"), required=True)
    parser.add_argument("--memory-limit", type=int, required=True)
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    suite = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(suite.parent))
    from benchmark_suite.runners.preflight import authorize_model
    authorize_model("docling_tesseract", suite / "BENCHMARK_STATUS.json")
    from windows_job import limit_current_process
    limit_current_process(args.memory_limit)
    started = time.perf_counter()
    root, cache = args.asset_root, args.cache_root
    (root / "tmp").mkdir(parents=True, exist_ok=True)
    os.environ.update(
        HF_HOME=str(cache / "hf"), TORCH_HOME=str(cache / "torch"),
        XDG_CACHE_HOME=str(cache / "cache"), HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1",
        TEMP=str(root / "tmp"), TMP=str(root / "tmp"),
        TESSDATA_PREFIX=str(root / "tessdata"), OMP_THREAD_LIMIT="1",
        OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", CUDA_VISIBLE_DEVICES="",
        TOKENIZERS_PARALLELISM="false",
    )
    with redirect_stdout(sys.stderr):
        import torch
        from docling.datamodel.accelerator_options import AcceleratorOptions
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import PdfPipelineOptions, TesseractCliOcrOptions
        from docling.datamodel.settings import settings
        from docling.document_converter import DocumentConverter, ImageFormatOption
        from OCR.providers.base import OCRDocument
        from OCR.providers.docling import normalize_docling
        from OCR.schemas import BoundingBox
        from benchmark_suite.runners.schemas import Prediction, Table

        if torch.version.cuda is not None:
            raise RuntimeError("Expected CPU-only Torch")
        torch.set_num_threads(1)
        torch.set_num_interop_threads(1)
        settings.cache_dir = cache / "docling"
        options = PdfPipelineOptions(
            do_ocr=True, do_table_structure=True, enable_remote_services=False,
            do_picture_classification=False, do_picture_description=False,
            do_code_enrichment=False, do_formula_enrichment=False, document_timeout=180,
            accelerator_options=AcceleratorOptions(device="cpu", num_threads=1),
            ocr_options=TesseractCliOcrOptions(
                lang=["eng"] if args.language == "en" else ["ara"], force_full_page_ocr=True,
                tesseract_cmd=str(root / "native/tesseract.exe"), path=str(root / "tessdata"), psm=3),
            layout_batch_size=1, ocr_batch_size=1, table_batch_size=1,
        )
        converter = DocumentConverter(allowed_formats=[InputFormat.IMAGE],
            format_options={InputFormat.IMAGE: ImageFormatOption(pipeline_options=options)})
        converter.initialize_pipeline(InputFormat.IMAGE)
    versions = {dist.metadata["Name"].lower().replace("_", "-"): dist.version
                for dist in importlib.metadata.distributions()}
    send({"event": "ready", "versions": versions, "language": args.language,
          "initialization_seconds": time.perf_counter() - started,
          "memory_limit_bytes": args.memory_limit, "pipeline_options": options.model_dump(mode="json")})
    for line in sys.stdin:
        try:
            request = json.loads(line)
            if request.get("operation") == "stop":
                break
            document = OCRDocument.model_validate(request["document"])
            if document.source_metadata["language"] != args.language:
                raise ValueError("Worker language mismatch")
            if hashlib.sha256(document.path.read_bytes()).hexdigest() != document.source_metadata["source_sha256"]:
                raise ValueError("Input checksum mismatch")
            phase = time.perf_counter()
            with redirect_stdout(sys.stderr):
                converted = converter.convert(document.path, raises_on_error=True)
            conversion_seconds = time.perf_counter() - phase
            if converted.status.value != "success" or converted.errors:
                raise RuntimeError(f"Docling conversion: {converted.status}; {converted.errors}")
            phase = time.perf_counter()
            with redirect_stdout(sys.stderr):
                vendor = converted.document.export_to_dict()
                markdown = converted.document.export_to_markdown()
                result = normalize_docling(document, converted, versions["docling"], request["model_revision"])
                for page in result.pages or []:
                    for order, block in enumerate(page.blocks or []):
                        block.reading_order = order
                result.provider_metadata.update(ocr_engine="tesseract_cli", psm=3,
                    native_languages=["eng"] if args.language == "en" else ["ara"],
                    osd_enabled=True, native_oem="auto; LSTM-only recognition data",
                    worker_job_memory_limit_bytes=args.memory_limit)
                tables = []
                for index, table in enumerate(converted.document.tables):
                    data = table.model_dump(mode="json")
                    provenance = data.get("prov", [])
                    if len(provenance) != 1:
                        raise ValueError("Single-image table requires unambiguous page provenance")
                    prov = provenance[0]
                    box = prov.get("bbox")
                    bounds = None
                    if box:
                        bounds = BoundingBox(x_min=min(box["l"], box["r"]), x_max=max(box["l"], box["r"]),
                            y_min=min(box["t"], box["b"]), y_max=max(box["t"], box["b"]), units="points",
                            origin="bottom_left" if box["coord_origin"] == "BOTTOMLEFT" else "top_left")
                    tables.append(Table(table_id=f"table-{index}", page_number=prov["page_no"],
                        html=table.export_to_html(doc=converted.document), bounding_box=bounds))
                prediction = Prediction(result=result, text_format="markdown", tables=tables,
                    coordinate_notes="Native Docling page points and provenance; hierarchy iteration order; table HTML is native export")
            payload = {"docling_document": vendor, "markdown": markdown,
                       "prediction": prediction.model_dump(mode="json"),
                       "backend_timings": {"conversion_seconds": conversion_seconds,
                                           "normalization_seconds": time.perf_counter() - phase}}
            output = root / "native_outputs" / uuid4().hex
            output.mkdir(parents=True, exist_ok=False)
            (output / "docling.json").write_text(json.dumps(vendor, ensure_ascii=False), encoding="utf-8")
            (output / "prediction.md").write_text(markdown, encoding="utf-8")
            (output / "prediction.json").write_text(prediction.model_dump_json(), encoding="utf-8")
            payload["native_output_directory"] = str(output)
            send({"ok": True, "payload": payload})
        except Exception as exc:
            traceback.print_exc(file=sys.stderr)
            send({"ok": False, "error_type": type(exc).__name__, "error": str(exc)})


if __name__ == "__main__":
    main()
