"""Run real OCR on a small scanned PDF and save per-provider evidence."""
import argparse
import json
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    from PIL import Image, ImageDraw, ImageFont
    from OCR.config import load_settings
    from OCR.providers.base import OCRDocument
    from OCR.service import OCRService

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", choices=["tesseract", "docling", "paddle_vl"])
    args = parser.parse_args()
    folder = ROOT / "runtime" / "model-check"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "sample.pdf"
    with Image.new("RGB", (1000, 400), "white") as image:
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 36)
        draw.text((50, 70), "OCR model verification", fill="black", font=font)
        draw.text((50, 150), "Invoice total: 123.45", fill="black", font=font)
        image.save(path, "PDF", resolution=150)
    service = OCRService(load_settings())
    document = OCRDocument(document_id="model-check", filename=path.name,
                           path=path, source="local:model-check")
    report = {}
    # Match /extract/compare order, including releasing Paddle before Docling.
    for provider in ([args.provider] if args.provider else ["paddle_vl", "docling", "tesseract"]):
        started = time.monotonic()
        print(f"Checking {provider}...", flush=True)
        try:
            result = service.extract(document, provider)
            (folder / f"{provider}.json").write_text(result.model_dump_json(indent=2), encoding="utf-8")
            if result.errors or not result.text or "123.45" not in result.text:
                raise RuntimeError("Expected invoice text was not extracted cleanly")
            report[provider] = {"status": "passed", "seconds": round(time.monotonic()-started, 2)}
        except Exception as exc:
            traceback.print_exc()
            report[provider] = {"status": "failed", "error": str(exc)}
        print(json.dumps(report[provider]), flush=True)
    (folder / f"report-{args.provider or 'all'}.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return int(any(item["status"] != "passed" for item in report.values()))


if __name__ == "__main__":
    raise SystemExit(main())
