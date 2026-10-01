"""Shared path/overwrite controls; metric policies remain in each evaluator."""
import argparse
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def evaluation_options(reference: Path, ocr_output: Path):
    parser = argparse.ArgumentParser(description="Evaluate existing Markdown outputs with the historical metric policy.")
    parser.add_argument("--reference", type=Path, default=reference)
    parser.add_argument("--ocr-output", type=Path, default=ocr_output)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
    parser.add_argument("--result", type=Path, default=Path(__file__).resolve().parents[1] / "results" / "runs" / (run_id + ".xlsx"))
    args = parser.parse_args()
    if not args.reference.is_dir() or not args.ocr_output.is_dir():
        parser.error("Reference and OCR output directories must exist.")
    if args.result.exists():
        parser.error("Result already exists; choose a new path to preserve previous results.")
    args.result.parent.mkdir(parents=True, exist_ok=True)
    print(f"Reference: {args.reference}\nOCR output: {args.ocr_output}\nNew result: {args.result}")
    return args
