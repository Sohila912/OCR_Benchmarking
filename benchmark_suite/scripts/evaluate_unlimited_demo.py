"""Offline conditional evaluation of saved successful hosted development outputs."""

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from uuid import uuid4

SUITE = Path(__file__).resolve().parents[1]
ROOT = Path("D:/OCR_Benchmarking_Assets/baidu_unlimited_ocr")
PARSER_SHA = "fb38738cd5f09625fb1095d201533b6059a85820bca99c4262347cc7b078a782"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--trial", type=Path, required=True)
    args = ap.parse_args()
    sys.path.insert(0, str(SUITE.parent))
    from benchmark_suite.adapters.unlimited_document import LABEL_MAP, normalize
    from benchmark_suite.runners.evaluate import evaluate_record
    from benchmark_suite.runners.preflight import environment
    from benchmark_suite.runners.report import aggregate, csv_bytes
    from benchmark_suite.runners.run import code_identity
    from benchmark_suite.runners.schemas import AdapterSpec, Capabilities, Requirements
    from benchmark_suite.scripts.try_unlimited_ocr_demo import reusable_results

    parser_path = ROOT / "preflight/github_utils_process_unlimitedOCR2.py"
    if digest(parser_path) != PARSER_SHA:
        raise ValueError("Pinned upstream postprocessor checksum mismatch")
    spec = importlib.util.spec_from_file_location("pinned_unlimited_postprocess", parser_path)
    upstream = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(upstream)
    policy_path = SUITE / "configs/evaluation.json"
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    manifest = SUITE / "datasets/manifest/development.jsonl"
    records = [json.loads(line) for line in manifest.read_text(encoding="utf-8").splitlines()]
    saved = reusable_results(args.trial, records)
    evidence = json.loads((SUITE / "reports/BAIDU_UNLIMITED_OCR_RESULTS.json").read_text(encoding="utf-8"))
    expected = {**evidence["trial_artifact_sha256"], **evidence["extended_development_trial"]["artifact_sha256"]}
    model = AdapterSpec(model_id="baidu", model_revision="HOSTED_WEIGHT_REVISION_UNVERIFIED",
        adapter_revision="offline-native-blocks-v1", capabilities=Capabilities(text=True, layout=True,
        reading_order=True, tables=True), label_map=LABEL_MAP, requirements=Requirements(
        compatibility="LIMITED", evidence="Offline saved outputs; no model loading", ram_bytes=0, disk_bytes=0),
        raw_level="Saved hosted raw PAGE/BLOCK/FORK stream; upstream canonical postprocessing")
    out = ROOT / "evaluations" / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8])
    out.mkdir(parents=True, exist_ok=False)
    rows, identities = [], []
    for record in records:
        state = saved.get(record["document_id"])
        if state is None:
            continue
        source = Path(state["source_directory"])
        response_path = source / "response.json"
        key = str(response_path.relative_to(ROOT))
        if key not in expected or digest(response_path) != expected[key]:
            raise ValueError("Saved response differs from versioned evidence")
        for path_key, hash_key in [("source_path", "file_hash"), ("ground_truth_reference", "reference_hash")]:
            if digest(SUITE / record[path_key]) != record[hash_key]:
                raise ValueError("Frozen source/reference checksum mismatch")
        response = json.loads(response_path.read_text(encoding="utf-8"))
        prediction = normalize(record, response, upstream)
        target = out / "predictions" / (hashlib.sha256(record["document_id"].encode()).hexdigest()[:24] + ".json")
        target.parent.mkdir(exist_ok=True)
        target.write_text(prediction.model_dump_json(), encoding="utf-8")
        reference = (SUITE / record["ground_truth_reference"]).read_text(encoding="utf-8")
        scores = evaluate_record(record, reference, prediction, model, policy)
        rows.append({"document_id": record["document_id"], "language": record["language"],
            "document_category": record["document_category"], "status": "SUCCESS", "metrics": scores})
        identities.append({"document_id": record["document_id"], "response_path": str(response_path),
            "response_sha256": digest(response_path), "source_sha256": record["file_hash"],
            "reference_sha256": record["reference_hash"]})
    summary = {"scope": "Conditional offline metrics on saved successful hosted development outputs; not a completed 20-page or full evaluation",
        "target_development_pages": len(records), "successful_pages_evaluated": len(rows),
        "pages_without_successful_output": len(records)-len(rows), "excluded_failures_policy": "Quota-denied/unattempted pages have no predictions or scores; never zero-filled",
        "remote_weight_revision": "UNVERIFIED", "strata": aggregate(rows, policy),
        "policy": policy, "spec": model.model_dump(mode="json"), "code": code_identity(),
        "manifest_sha256": digest(manifest), "evaluation_policy_sha256": digest(policy_path),
        "upstream_parser_sha256": PARSER_SHA, "upstream_commit": "ea42e6d15ff93fdd0e8041fc0ac70880513453d3",
        "outputs": identities, "selection_bias": "First completed pages of the interleaved frozen development sequence; not representative or an official cross-model comparison"}
    for name, data in [("metrics.json", summary), ("environment.json", environment())]:
        (out / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "per_page_metrics.csv").write_bytes(csv_bytes(rows))
    (out / "metrics.csv").write_bytes(csv_bytes(summary["strata"]))
    hashes = {str(p.relative_to(out)): digest(p) for p in out.rglob("*") if p.is_file()}
    (out / "evaluation_manifest.json").write_text(json.dumps(hashes, indent=2) + "\n", encoding="utf-8")
    print(str(out), flush=True)
    for row in summary["strata"]:
        if row["level"] == "language":
            print(json.dumps({key: row[key] for key in ["language", "total_pages", "content_normalized_cer", "content_normalized_wer"]}), flush=True)


if __name__ == "__main__":
    main()
