"""Benchmark orchestration and repository dataset access through the backend."""
import hashlib
import json
import time
from importlib.metadata import version, PackageNotFoundError
from datetime import datetime, timezone
from uuid import uuid4
from fastapi import File, Form, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool
from OCR.config import REPOSITORY_ROOT
from OCR.service import ingest_pdf
from OCR.errors import OCRError, public_error_message
from OCR.evaluation import Normalization, evaluate, reference_upload, differences, METHOD
from OCR.benchmark_store import BenchmarkStore, compare_runs
from OCR.provider_diagnostics import diagnose

DATASETS = REPOSITORY_ROOT / "benchmarks" / "datasets"
OUTPUTS = REPOSITORY_ROOT / "benchmarks" / "outputs"

def child(root, *parts):
    candidate = root.joinpath(*parts).resolve()
    if not candidate.is_relative_to(root.resolve()):
        raise ValueError("Invalid dataset path.")
    return candidate

def catalog():
    rows = []
    for name in ("English", "Arabic", "Mix"):
        refs = DATASETS / name / "Markdown_Reference"
        pdfs = DATASETS / name / "Dataset"
        available_pdfs = list(pdfs.glob("*.pdf"))
        available_outputs = list((OUTPUTS / name).glob("*/*.md"))
        for ref in sorted(refs.glob("*.md")):
            if ref.is_symlink():
                continue
            # Existing mapping is presented for explicit user approval before reuse.
            candidates = [p for p in available_pdfs if p.stem.casefold() == ref.stem.casefold() and not p.is_symlink()]
            pdf = candidates[0] if len(candidates) == 1 else None
            outputs = [p.relative_to(OUTPUTS).as_posix() for p in available_outputs
                       if p.name.casefold() == ref.name.casefold() and not p.is_symlink()]
            rows.append({"dataset": name, "reference": ref.name,
                         "pdf": pdf.name if pdf is not None else None, "outputs": outputs})
    return rows

def register(application, service, settings):
    store = BenchmarkStore(settings.benchmark_db, settings.benchmark_retention_days)
    store.recover_interrupted()

    @application.get("/providers/diagnostics")
    def diagnostics():
        return diagnose(service)

    @application.get("/benchmarks/datasets")
    def datasets():
        return catalog()

    def runtime_versions():
        versions = {}
        for package in ("jiwer", "paddleocr", "paddlepaddle", "docling", "torch", "torchvision", "ollama"):
            try:
                versions[package] = version(package)
            except PackageNotFoundError:
                pass
        return versions

    def execute(document, reference, reference_bytes, providers, options, dataset, origin="upload", output=None,
                force_reprocess=False):
        batch, rows = uuid4().hex, []
        for provider in providers:
            row = {"id": uuid4().hex, "batch_id": batch, "timestamp": datetime.now(timezone.utc).isoformat(),
                   "dataset_id": dataset, "dataset_name": dataset, "document_id": document.document_id,
                   "reference_hash": hashlib.sha256(reference_bytes).hexdigest(), "provider": provider,
                   "normalization": options.model_dump(), "method": METHOD, "status": "running", "origin": origin, "runtime_versions": runtime_versions()}
            store.save(row)
            row["status"] = "failed"
            started = time.monotonic()
            try:
                result = service.extract(document, provider, persist_result=False, force_reprocess=force_reprocess) if output is None else None
                if result and (result.errors or any(p.errors for p in result.pages or [])):
                    raise ValueError("Partial extraction excluded from scoring.")
                text = output if output is not None else (result.markdown if result.markdown is not None else result.text)
                if text is None:
                    raise ValueError("Provider returned no text.")
                row.update(status="success", metrics=evaluate(reference, text, options))
                if result:
                    cache = result.provider_metadata.get("cache", {})
                    row.update(cache_status=cache.get("status"), cache_key=cache.get("key"))
                    row.update(model_name=result.model_name, model_version=result.model_version,
                               package_version=result.provider_metadata.get("package_version"),
                               model_digest=result.provider_metadata.get("model_digest"))
                    for key in ("duration_seconds", "initialization_seconds", "inference_seconds"):
                        row[key] = result.provider_metadata.get(key)
                else:
                    row["duration_seconds"] = None  # Old files contain no trustworthy execution timing.
            except OCRError as exc:
                row["error"] = exc.code + ": " + public_error_message(exc)
            except ValueError as exc:
                row["error"] = str(exc)
            if row["status"] == "failed":
                row["duration_seconds"] = time.monotonic() - started
            store.save(row)
            if row["status"] == "success":
                row.update(reference=reference, output=text, diff=differences(reference, text, options))
                # Session response only: history remains metrics-only.
                if result is not None:
                    row["ocr_result"] = result.model_dump(mode="json")
            rows.append(row)
        return {"batch_id": batch, "results": rows}

    @application.post("/benchmarks/run")
    async def benchmark(file: UploadFile = File(...), reference: UploadFile = File(...),
                        providers: str = Form(...), normalization: str = Form("{}"),
                        dataset: str = Form("Uploaded documents"), paired: bool = Form(False),
                        force_reprocess: bool = Form(False)):
        document = None
        try:
            if not paired:
                raise ValueError("Confirm this PDF and reference describe the same document.")
            names = json.loads(providers)
            if not isinstance(names, list) or not names or len(names) > len(service.providers) or not all(isinstance(n, str) for n in names):
                raise ValueError("Select valid providers.")
            names = list(dict.fromkeys(names))
            for name in names:
                service.select(name)
            if not dataset.strip() or len(dataset) > 120:
                raise ValueError("Dataset name must contain 1–120 characters.")
            options = Normalization.model_validate_json(normalization)
            data = await reference.read(2 * 1024 * 1024 + 1)
            text = reference_upload(data, reference.filename or "")
            evaluate(text, "", options)  # Reject normalized-empty ground truth before OCR.
            document = await run_in_threadpool(ingest_pdf, file.file, file.filename, settings, True)
            return await run_in_threadpool(execute, document, text, data, names, options, dataset.strip(),
                                           force_reprocess=force_reprocess)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        finally:
            await file.close()
            await reference.close()
            if document:
                document.path.unlink(missing_ok=True)

    @application.post("/benchmarks/datasets/run")
    def dataset_run(payload: dict):
        from OCR.providers.base import OCRDocument
        try:
            if payload.get("confirmed") is not True:
                raise ValueError("Explicitly confirm the selected dataset mapping.")
            dataset, refname = payload["dataset"], payload["reference"]
            mapping = next((r for r in catalog() if r["dataset"] == dataset and r["reference"] == refname), None)
            if not mapping:
                raise ValueError("Unknown dataset reference.")
            path = child(DATASETS, dataset, "Markdown_Reference", refname)
            if path.stat().st_size > 2 * 1024 * 1024:
                raise ValueError("Reference too large.")
            data = path.read_bytes()
            reference = reference_upload(data, refname)
            options = Normalization.model_validate(payload.get("normalization", {}))
            force_reprocess = payload.get("force_reprocess", False)
            if not isinstance(force_reprocess, bool):
                raise ValueError("force_reprocess must be a boolean.")
            evaluate(reference, "", options)
            output_key = payload.get("output")
            if output_key:
                if output_key not in mapping["outputs"]:
                    raise ValueError("Output does not belong to selected mapping.")
                output_path = child(OUTPUTS, output_key)
                if output_path.stat().st_size > 2 * 1024 * 1024:
                    raise ValueError("Historical output too large.")
                output = output_path.read_text(encoding="utf-8-sig")
                # Identity explicitly denotes reference mapping; original PDF hash is unknown.
                document = OCRDocument(document_id="legacy-mapping:" + hashlib.sha256(data).hexdigest(), filename=refname, path=path)
                return execute(document, reference, data, ["legacy:" + output_path.parent.name], options, dataset, "rescored historical output", output)
            if not mapping["pdf"]:
                raise ValueError("No PDF available for this mapping.")
            pdf = child(DATASETS, dataset, "Dataset", mapping["pdf"])
            names = payload.get("providers", [])
            if not names or len(names) > len(service.providers):
                raise ValueError("Select providers.")
            for name in names:
                service.select(name)
            with pdf.open("rb") as stream:
                document = ingest_pdf(stream, pdf.name, settings, benchmark=True)
            try:
                return execute(document, reference, data, list(dict.fromkeys(names)), options, dataset,
                               "existing dataset", force_reprocess=force_reprocess)
            finally:
                document.path.unlink(missing_ok=True)
        except (ValueError, KeyError, OSError, UnicodeError) as exc:
            raise HTTPException(400, "Invalid dataset mapping, files or evaluation settings.") from exc

    @application.get("/benchmarks/history")
    def history(provider: str | None = None, dataset: str | None = None, since: str | None = None, until: str | None = None):
        return store.history(provider, dataset, since, until)

    @application.post("/benchmarks/compare")
    def compare(ids: list[str]):
        if not ids or len(ids) > 2000:
            raise HTTPException(400, "Select 1–2000 run IDs.")
        rows = [r for r in store.history() if r["id"] in ids]
        if len(rows) != len(set(ids)):
            raise HTTPException(400, "Unknown or expired run ID.")
        if any(r["status"] == "running" for r in rows):
            raise HTTPException(400, "Wait for active benchmarks to finish before comparing.")
        return compare_runs(rows)

    @application.delete("/benchmarks/history/{run_id}")
    def delete(run_id: str):
        return {"deleted": store.delete(run_id)}
