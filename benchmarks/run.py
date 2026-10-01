"""Generate distinctly named benchmark runs without overwriting historical OCR."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from OCR.config import load_settings
from OCR.errors import OCRError
from OCR.providers.base import OCRDocument
from OCR.service import OCRService, PROVIDER_TYPES


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--language", choices=("English", "Arabic", "Mix"), required=True)
    parser.add_argument("--provider", choices=tuple(PROVIDER_TYPES), required=True)
    parser.add_argument("--output-dir", type=Path, help="New, non-existing run directory")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
    output = args.output_dir or root / "outputs" / args.language / (args.provider + "-" + run_id)
    output.mkdir(parents=True, exist_ok=False)
    settings = load_settings().model_copy(update={"output_dir": output / "normalized"})
    service = OCRService(settings)
    records = []
    for source in sorted((root / "datasets" / args.language / "Dataset").glob("*.pdf")):
        document = OCRDocument(document_id=hashlib.sha256(source.read_bytes()).hexdigest(), filename=source.name,
                                path=source, source="benchmark:" + source.relative_to(root).as_posix(),
                                source_metadata={"dataset_language": args.language})
        try:
            result = service.extract(document, args.provider)
            if result.errors:
                records.append({"file": source.name, "errors": [i.model_dump() for i in result.errors]})
                continue
            content = result.markdown if result.markdown is not None else result.text
            if content is None:
                records.append({"file": source.name, "errors": [{"code": "no_content"}]})
                continue
            with (output / (source.stem + ".md")).open("x", encoding="utf-8") as handle:
                handle.write(content)
            records.append({"file": source.name, "document_id": result.document_id,
                            "provider": result.provider, "model_name": result.model_name,
                            "model_version": result.model_version, "provider_metadata": result.provider_metadata,
                            "export_field": "markdown" if result.markdown is not None else "text"})
        except OCRError as exc:
            records.append({"file": source.name, "errors": [{"code": exc.code, "message": str(exc)}]})
    (output / "run.json").write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Run outputs: {output}")
    return 1 if not records or any(r.get("errors") for r in records) else 0


if __name__ == "__main__":
    raise SystemExit(main())
