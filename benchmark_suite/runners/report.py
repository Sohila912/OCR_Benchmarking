"""Reevaluate a completed run without constructing an adapter or reading cache."""

import csv
from io import StringIO
import json
from pathlib import Path
from uuid import uuid4

from benchmark_suite.dataset_io import digest, safe_path
from benchmark_suite.metrics import VERSION, layout, statistics
from .cache import IntegrityError, coordinator_lock, fingerprint, json_bytes, now, read_bundle, write_new
from .evaluate import evaluate_record
from .run import load_records
from .schemas import AdapterSpec, Prediction, RunConfig


def csv_bytes(rows):
    rows = list(rows)
    keys = sorted({k for row in rows for k in row}) or ["status", "reason"]
    stream = StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=keys)
    writer.writeheader()
    for row in rows:
        writer.writerow({k: json.dumps(v, ensure_ascii=False, allow_nan=False) if isinstance(v, (dict, list)) else v for k, v in row.items()})
    return stream.getvalue().encode("utf-8")


def evaluate_run(root, run_directory, evaluation_config=None):
    """Write a new uniquely identified sibling evaluation; leave the run intact."""
    root, directory = Path(root).resolve(), Path(run_directory).resolve()
    if not directory.is_relative_to(root/"results") or directory.parent.parent != root/"results":
        raise ValueError("Expected a run directory inside this suite's model results")
    with coordinator_lock(root/"cache/coordinator.lock"):
        completion = json.loads((directory/"completion.json").read_bytes())
        for name, expected in completion["files"].items():
            if digest(safe_path(directory, name)) != expected:
                raise IntegrityError("Run metadata checksum mismatch")
        descriptor = json.loads((directory/"run_manifest.json").read_bytes())
        if fingerprint(descriptor["identity"]) != descriptor["identity_hash"] or descriptor["identity_hash"] != completion["identity_hash"]:
            raise IntegrityError("Run identity checksum mismatch")
        spec = AdapterSpec.model_validate(descriptor["identity"]["spec"])
        config = RunConfig.model_validate(descriptor["identity"]["config"])
        cohort = descriptor["dataset"]
        splits = cohort["splits"]
        if len(splits) != 1:
            raise IntegrityError("A run must use exactly one frozen split")
        records, current = load_records(root, root/f"datasets/manifest/{splits[0]}.jsonl", config)
        if current != cohort:
            raise IntegrityError("Frozen cohort changed since inference")
        policy = evaluation_config or json.loads((root/"configs/evaluation.json").read_bytes())
        if policy["evaluator_version"] != VERSION:
            raise ValueError("Unknown evaluator version")
        metrics_root = Path(__file__).resolve().parents[1]/"metrics"
        code = {p.name: digest(p) for p in sorted(metrics_root.glob("*.py"))}
        code.update({"routing.py": digest(Path(__file__).with_name("evaluate.py")), "report.py": digest(Path(__file__))})
        evaluation_id = fingerprint({"policy": policy, "code": code, "completion": digest(directory/"completion.json")})
        output = directory.parent/"evaluations"/directory.name/(evaluation_id[:12]+"-"+uuid4().hex[:8])
        output.mkdir(parents=True, exist_ok=False)
        rows, outputs, failures, performance = [], [], [], []
        for record in records:
            short = fingerprint(record["document_id"])[:24]
            bundle = directory/"documents"/short
            expected = completion["documents"].get(short)
            if expected is None or digest(bundle/"bundle.json") != expected:
                raise IntegrityError("Document completion checksum mismatch")
            info = read_bundle(bundle)["metadata"]
            if info["document_id"] != record["document_id"] or info["source_sha256"] != record["file_hash"]:
                raise IntegrityError("Prediction is not for this frozen image")
            base = {"document_id": record["document_id"], "page": 1, "language": record["language"],
                    "document_category": record["document_category"], "status": info["status"]}
            performance.append(dict(base, cache_hit=info["cache_hit"],
                fresh_inference_seconds=None if info["cache_hit"] else info.get("inference_seconds"),
                original_inference_seconds=info.get("inference_seconds"),
                preprocess_seconds=None if info["cache_hit"] else info.get("preprocess_seconds"),
                postprocess_seconds=None if info["cache_hit"] else info.get("postprocess_seconds"),
                processing_seconds=None if info["cache_hit"] else info.get("processing_seconds"),
                inference_temperature=None if info["cache_hit"] else info.get("inference_temperature"),
                sampled_peak_rss_bytes=None if info["cache_hit"] else info.get("sampled_peak_rss_bytes"),
                peak_gpu_vram_bytes=None if info["cache_hit"] else info.get("gpu_vram_peak_bytes"),
                original_peak_gpu_vram_bytes=info.get("gpu_vram_peak_bytes"), gpu_measurement_status=info.get("gpu_measurement_status"),
                device=config.device, precision=config.precision, batch_size=config.batch_size, dpi=config.dpi,
                preprocessing=config.preprocessing, execution_location=config.location))
            if info["status"] != "SUCCESS":
                scores = {name: {"status": "NOT_EVALUATED", "reason": "INFERENCE_FAILED", "value": None}
                          for name in ("text", "layout", "reading_order", "tables", "figure_detection", "chart_type", "chart_numeric", "chart_text", "chart_components")}
                failures.append(dict(base, error_type=info.get("error_type"), error=info.get("error")))
            else:
                prediction = Prediction.model_validate_json((bundle/"prediction.json").read_bytes())
                outputs.append(prediction.model_dump(mode="json"))
                reference = safe_path(root, record["ground_truth_reference"]).read_text(encoding="utf-8")
                scores = evaluate_record(record, reference, prediction, spec, policy)
            rows.append(dict(base, metrics=scores))
        summaries = aggregate(rows, policy)
        session_files = {name: json.loads((directory/name).read_bytes()) for name in completion["files"] if name.startswith("sessions/")}
        fresh = [p for p in performance if not p["cache_hit"] and p["status"] == "SUCCESS" and p["fresh_inference_seconds"] is not None]
        fresh_seconds = sum(p["fresh_inference_seconds"] for p in fresh)
        report = {"evaluator_version": VERSION, "evaluation_id": evaluation_id, "policy": policy, "code": code,
                  "run_id": directory.name, "run_completion_sha256": digest(directory/"completion.json"),
                  "total_documents": len(records), "failed_documents": len(failures),
                  "success_rate": (len(records)-len(failures))/len(records),
                  "cached_documents": sum(p["cache_hit"] for p in performance),
                  "interval_unit": "page", "source_document_independence": "UNKNOWN", "strata": summaries,
                  "sessions": session_files,
                  "successful_fresh_pages": len(fresh), "successful_fresh_inference_seconds": fresh_seconds,
                  "seconds_per_successful_fresh_page": fresh_seconds/len(fresh) if fresh else None,
                  "successful_fresh_pages_per_minute": 60*len(fresh)/fresh_seconds if fresh_seconds else None,
                  "recorded_session_wall_seconds": sum(v["session_wall_seconds"] for k, v in session_files.items() if k.endswith("-end.json")),
                  "sessions_without_end_record": sum(k.endswith("-start.json") and k.replace("-start.json", "-end.json") not in session_files for k in session_files),
                  "cleanup_failures": [v["cleanup_error"] for k, v in session_files.items() if k.endswith("-end.json") and v.get("cleanup_error")]}
        files = {"metrics.json": json_bytes(report), "per_document_metrics.csv": csv_bytes(rows),
                 "per_page_metrics.csv": csv_bytes(rows), "failures.csv": csv_bytes(failures),
                 "performance_metrics.csv": csv_bytes(performance), "metrics.csv": csv_bytes(summaries),
                 "predictions.jsonl": b"".join(json_bytes(p)+b"\n" for p in outputs),
                 "config.json": json_bytes(policy), "environment.json": (directory/"environment.json").read_bytes(),
                 "errors.log": "\n".join(f"{r['document_id']}: {r['error_type']}: {r['error']}" for r in failures).encode("utf-8")}
        for language, name in (("en", "english_results.csv"), ("ar", "arabic_results.csv")):
            files[name] = csv_bytes(r for r in rows if r["language"] == language)
        for metric, name in (("layout", "layout_metrics.csv"), ("tables", "table_metrics.csv"),
                             ("reading_order", "reading_order_metrics.csv")):
            files[name] = csv_bytes({**{k: v for k, v in r.items() if k != "metrics"}, **r["metrics"][metric]} for r in rows)
        files["chart_metrics.csv"] = csv_bytes({"document_id": r["document_id"],
            **{k: v for k, v in r["metrics"].items() if k.startswith("chart") or k == "figure_detection"}} for r in rows)
        files["MODEL_REPORT.md"] = (f"# {spec.model_id} — {directory.name}\n\n"
            f"Evaluation: {evaluation_id}. {len(records)} image units; {len(failures)} failed; "
            f"{report['cached_documents']} cached. Success rate {report['success_rate']:.3f}.\n\n"
            f"Purpose: {config.purpose}. Fixture outputs are software tests, never model benchmark evidence.\n\n"
            "Inspect metrics.json and per-page CSV for exact scopes, gates and coverage. "
            "English scores use independently allocated explicit text regions; Arabic uses page content. "
            "Partial/unannotated content, raw serialization and common content are distinct. "
            "Chart numeric/type truth and Arabic order truth are unavailable in this cohort. "
            "Intervals resample pages; source-document independence is unverified. "
            "Cached timings are not new speed measurements. RSS peaks are sampled and GPU peaks may be unavailable. "
            "Do not rank across different hardware, coverage or preprocessing. "
            "See reports/METRICS.md and the versioned evaluation config for formulas and TEDS variant.\n").encode("utf-8")
        for name, data in files.items():
            write_new(output/name, data)
        write_new(output/"evaluation_manifest.json", json_bytes({"completed_at": now(), "evaluation_id": evaluation_id,
                  "files": {name: digest(output/name) for name in files}, "kind": "offline_evaluation"}))
        return output


def text_counts(metrics, mode, units):
    if metrics.get("status") != "SCORED":
        return None
    entries = metrics.get("items", [metrics])
    values = [item["content"][mode][units] for item in entries if "content" in item]
    return (sum(v["edits"] for v in values), sum(v["reference_length"] for v in values)) if values else None


def aggregate(rows, policy):
    summaries = []
    groups = {(r["language"], None, "language") for r in rows} | {(r["language"], r["document_category"], "category") for r in rows}
    for language, category, level in sorted(groups, key=str):
        chosen = [r for r in rows if r["language"] == language and (level == "language" or r["document_category"] == category)]
        item = {"language": language, "document_category": category, "level": level, "total_pages": len(chosen),
                "failed_pages": sum(r["status"] != "SUCCESS" for r in chosen),
                "text_scope": "region edits pooled per image" if language == "en" else "page-content",
                "coverage": {name: {status: sum(r["metrics"][name]["status"] == status for r in chosen)
                                      for status in ("SCORED", "NOT_EVALUATED", "NOT_SUPPORTED")}
                             for name in chosen[0]["metrics"]}}
        for mode in ("raw", "normalized"):
            for units, rate in (("characters", "cer"), ("words", "wer")):
                values = [(r["document_id"], text_counts(r["metrics"]["text"], mode, units)) for r in chosen]
                counts = [v for _, v in values if v is not None]
                item[f"content_{mode}_{rate}"] = {**statistics.aggregate_ratio(counts),
                    "unscored_pages": len(chosen)-len(counts), "ci95_page_bootstrap": statistics.bootstrap(values,
                        unit="page", seed=policy["statistics"]["seed"], samples=policy["statistics"]["bootstrap_samples"], ratio=True)}
        layout_rows = [r for r in chosen if r["metrics"]["layout"]["status"] == "SCORED"]
        if layout_rows:
            gt, pred = [], []
            for row in layout_rows:
                data = row["metrics"]["layout"]["evaluation_inputs"]
                gt.extend(dict(region, page_id=row["document_id"]) for region in data["reference"])
                pred.extend(dict(region, page_id=row["document_id"]) for region in data["prediction"])
            classes = layout_rows[0]["metrics"]["layout"]["evaluation_inputs"]["classes"]
            corpus = layout.detection(gt, pred, classes, policy["layout"]["iou_threshold"])
            confidence = all(r["metrics"]["layout"]["evaluation_inputs"]["confidence_complete"] for r in layout_rows)
            if not confidence:
                corpus["map"] = None
                for cls in corpus["per_class"].values(): cls["ap"] = None
            item["layout"] = {"detection": corpus, "scored_pages": len(layout_rows),
                "unscored_pages": len(chosen)-len(layout_rows), "map": layout.mean_ap(gt, pred, classes, policy["layout"]["map_thresholds"]) if confidence else None}
        else:
            item["layout"] = {"status": "NOT_EVALUATED", "scored_pages": 0, "unscored_pages": len(chosen), "map": None}
        table_items = [t for r in chosen for t in r["metrics"]["tables"].get("items", [])]
        item["tables"] = {"reference_tables": len(table_items), "scored_tables": sum(t["status"] == "SCORED" for t in table_items),
                          "teds": statistics.summarize([t.get("teds") for t in table_items]),
                          "teds_structure": statistics.summarize([t.get("teds_structure") for t in table_items])}
        summaries.append(item)
    return summaries
