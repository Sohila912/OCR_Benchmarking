"""Create an additional report/figure from an explicit completed local model run."""

import argparse
import csv
import hashlib
import importlib.metadata
import json
from pathlib import Path
import statistics
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--evaluation-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="New directory; never overwritten")
    parser.add_argument("--plot-libs", type=Path, help="Optional isolated matplotlib package directory")
    parser.add_argument("--model", choices=("tesseract", "docling_tesseract"), default="tesseract")
    args = parser.parse_args()
    run, evaluation = args.run_dir.resolve(), args.evaluation_dir.resolve()
    descriptor = json.loads((run / "run_manifest.json").read_bytes())
    completion_path = run / "completion.json"
    completion = json.loads(completion_path.read_bytes())
    metrics = json.loads((evaluation / "metrics.json").read_bytes())
    if descriptor["identity"]["spec"]["model_id"] != args.model:
        parser.error("Selected model and saved run differ")
    title = "Tesseract tessdata_fast" if args.model == "tesseract" else "Docling + Tesseract"
    if metrics["run_completion_sha256"] != hashlib.sha256(completion_path.read_bytes()).hexdigest():
        parser.error("Evaluation does not match the completed run")
    evaluation_manifest = json.loads((evaluation / "evaluation_manifest.json").read_bytes())
    for name, expected in evaluation_manifest["files"].items():
        if hashlib.sha256((evaluation / name).read_bytes()).hexdigest() != expected:
            parser.error(f"Evaluation artifact checksum mismatch: {name}")
    with (evaluation / "performance_metrics.csv").open(encoding="utf-8", newline="") as handle:
        performance = list(csv.DictReader(handle))
    fresh = [row for row in performance if row["status"] == "SUCCESS" and row["cache_hit"] == "False"]
    latency = [float(row["fresh_inference_seconds"]) for row in fresh]
    peaks = [int(row["sampled_peak_rss_bytes"]) for row in fresh if row["sampled_peak_rss_bytes"]]
    strata = [row for row in metrics["strata"] if row["level"] == "language"]
    summary = {
        "model": descriptor["identity"]["spec"]["model_revision"], "run_id": run.name,
        "splits": descriptor["dataset"]["splits"], "evaluation_id": metrics["evaluation_id"],
        "total_documents": metrics["total_documents"], "failed_documents": metrics["failed_documents"],
        "success_rate": metrics["success_rate"], "cached_documents": metrics["cached_documents"],
        "fresh_ocr_seconds": metrics["successful_fresh_inference_seconds"],
        "mean_fresh_ocr_seconds": metrics["seconds_per_successful_fresh_page"],
        "median_fresh_ocr_seconds": statistics.median(latency) if latency else None,
        "sampled_peak_rss_bytes": max(peaks) if peaks else None,
        "recorded_session_wall_seconds": metrics["recorded_session_wall_seconds"],
        "languages": strata, "completion_sha256": hashlib.sha256(completion_path.read_bytes()).hexdigest(),
        "evaluation_metrics_sha256": hashlib.sha256((evaluation / "metrics.json").read_bytes()).hexdigest(),
        "memory_method": "50 ms sampled process and descendants RSS; not allocator peak",
        "source_document_independence": "UNKNOWN", "completion_status": completion["state"],
    }
    if args.plot_libs:
        sys.path.insert(0, str(args.plot_libs.resolve()))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    args.output.mkdir(parents=True, exist_ok=False)
    figure, axes = plt.subplots(1, 3, figsize=(13, 4.6), layout="constrained")
    for axis, language in zip(axes[:2], ("en", "ar")):
        row = next(item for item in strata if item["language"] == language)
        names, values, errors = [], [], [[], []]
        for metric in ("cer", "wer"):
            item = row[f"content_normalized_{metric}"]
            value = item["micro"]
            if value is None:
                continue
            names.append(metric.upper())
            values.append(value * 100)
            interval = item["ci95_page_bootstrap"].get("ci95")
            errors[0].append(max(0, value - interval[0]) * 100 if interval else 0)
            errors[1].append(max(0, interval[1] - value) * 100 if interval else 0)
        bars = axis.bar(names, values, yerr=errors, capsize=5, color=["#285c93", "#2b8175"][:len(names)])
        axis.bar_label(bars, labels=[f"{value:.1f}%" for value in values], padding=6)
        axis.set_ylim(0, max([v + error for v, error in zip(values, errors[1])] + [1]) * 1.22)
        axis.set_ylabel("Normalized error rate (%) — lower is better")
        scope = "English: reference-region text" if language == "en" else "Arabic: page-content text"
        scored = row["coverage"]["text"]["SCORED"]
        axis.set_title(f"{scope}\n{scored}/{row['total_pages']} pages scored; 95% page bootstrap CI", fontsize=10)
    axes[2].hist(latency, bins=min(30, max(5, len(latency) // 10)), color="#65758a", edgecolor="white")
    axes[2].set(xlabel="Fresh measured inference time (seconds)", ylabel="Pages", title="CPU inference time per page")
    if not latency:
        axes[2].text(.5, .5, "No fresh OCR timing measurements", ha="center", transform=axes[2].transAxes)
    figure.suptitle(f"{title} — {','.join(summary['splits'])} split", fontsize=14)
    figure.supxlabel("Reference scopes differ. Page independence is unverified. Inference excludes initialization, external preprocessing and evaluation.", fontsize=9)
    figure.savefig(args.output / "text_errors_and_latency.png", dpi=180)
    figure.savefig(args.output / "text_errors_and_latency.svg")
    plt.close(figure)
    summary["plot_packages"] = {name: importlib.metadata.version(name) for name in
                                ("matplotlib", "numpy", "pillow", "contourpy", "cycler", "fonttools", "kiwisolver", "packaging", "pyparsing", "python-dateutil", "tzdata")}
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    lines = [f"# {title} — {run.name}", "", f"Split: {summary['splits']}. "
             f"Processed {summary['total_documents']} pages; {summary['failed_documents']} failed; "
             f"{summary['cached_documents']} reused from cache.", "",
             "| Language | Pages | Raw CER | Normalized CER | Raw WER | Normalized WER |",
             "|---|---:|---:|---:|---:|---:|"]
    def rate(value):
        return f"{value:.2%}" if value is not None else "NOT_EVALUATED"
    for row in strata:
        values = [rate(row[f"content_{mode}_{metric}"]["micro"])
                  for metric in ("cer", "wer") for mode in ("raw", "normalized")]
        lines.append(f"| {row['language']} | {row['total_pages']} | " + " | ".join(values) + " |")
    mean_seconds = f"{summary['mean_fresh_ocr_seconds']:.3f}" if summary['mean_fresh_ocr_seconds'] is not None else "NOT_MEASURED"
    peak_mib = f"{summary['sampled_peak_rss_bytes'] / 1024**2:.1f}" if summary['sampled_peak_rss_bytes'] is not None else "NOT_MEASURED"
    lines.extend(["", "English uses reference-region text; Arabic uses page content. "
                  "These scores do not share a common reference scope. "
                  "CER/WER are error rates, not document success or generic accuracy.", "",
                  f"Fresh measured inference time: {summary['fresh_ocr_seconds']:.2f} seconds; "
                  f"mean {mean_seconds} seconds/page. "
                  f"Recorded session wall time: {summary['recorded_session_wall_seconds']:.2f} seconds.",
                  f"Sampled peak process/descendant RSS: {peak_mib} MiB. "
                  "Sampling can miss short peaks; GPU inference was not used.", "",
                  ("Semantic layout, reading order, table structure and chart understanding are unsupported. "
                   if args.model == "tesseract" else
                   "Native layout, reading-order and table predictions are evaluated where independent references exist; chart understanding is disabled. ") +
                  "Missing truth and unsupported outputs retain the shared evaluator's explicit statuses. "
                  "Page-bootstrap intervals do not establish source-document independence.", "",
                  "![Text errors and OCR latency](text_errors_and_latency.png)", "",
                  "See the original evaluation directory for per-page/category metrics, raw/normalized outputs, "
                  "coverage, failures and phase timings. summary.json records artifact identities and figure dependencies."])
    (args.output / "MODEL_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(args.output.resolve())


if __name__ == "__main__":
    main()
