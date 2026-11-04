# PaddleOCR: 200-page evaluation subset

Reviewed 2026-11-04 (Africa/Cairo); inference completed 2026-11-03. TASK-012.

**200/200 additional evaluation pages converted successfully; zero failures and
zero cache reuse.** The earlier 20 development pages remain separate and intact.

| Language | Converted | Text scored | Normalized CER | Normalized WER |
|---|---:|---:|---:|---:|
| English | 100 | 99 | 14.17% | 23.48% |
| Arabic | 100 | 100 | 51.53% | 71.34% |

CER/WER are error rates; lower is better. One English page has no available
text reference (`REFERENCE_UNAVAILABLE`), so its successful conversion contributes
no text score. Its document ID is recorded in PADDLE_RESULTS.json. English uses
independently allocated reference-region text; Arabic uses page-content text.
These reference scopes differ. Normalization is NFC and whitespace; optional
Arabic folding is disabled. Confidence intervals and coverage remain in JSON.
Page independence across source documents is unverified.

The cohort is a deterministic language round-robin selection of the first 100
pages per language in the unchanged frozen evaluation manifest. It is not a
random sample or an estimate of corpus-wide ranking. Both document IDs and source
image SHA256s were checked for overlap against all 20 development pages: none.
The full manifest has 745 English and 390 Arabic pages. **935 evaluation pages
remain (645 English, 290 Arabic)**. TASK-012 remains IN_PROGRESS; no completed
full-evaluation selected-run marker was created.

Recorded session wall time was **5,873.58 seconds (97.89 minutes)**. Fresh measured
inference totaled 5,420.98 seconds, mean 27.10 seconds/page, median 14.67 seconds.
These timings include per-page worker imports/startup, checksum verification,
preprocessing, native prediction/export and IPC. Slow wall-time outliers are
retained; this is elapsed time, not pure CPU compute time. Peak sampled process
and descendant RSS was **759,783,424 bytes (724.6 MiB, 0.71 GiB)**, sampled every
50 ms; short peaks may be missed. CPU inference used the same pinned mobile
models, two threads, batch one and bounded memory controls as development.
See [PADDLE.md](PADDLE.md) and PADDLE_ASSETS.json for exact configuration.
Semantic layout, reading order, table structure and chart understanding remain
unsupported, with explicit evaluator coverage states.

## Saved artifacts

- Run: `benchmark_suite/results/paddle/20261103T124313Z-fc565574`.
- Evaluation: `benchmark_suite/results/paddle/evaluations/20261103T124313Z-fc565574/d093025e6da5-6c9978f1`.
- Reviewed D: report, chart, summary and canonical run/evaluation copies:
  `D:/OCR_Benchmarking_Assets/paddle/reports/evaluation-200-20261104-reviewed`.
- D: selection identity and partial recovery snapshots:
  `D:/OCR_Benchmarking_Assets/paddle/evaluation_batches/20261103T124313Z-fc565574`.
- Native output and identical input copies remain under the D: Paddle asset root.
- Machine-readable results: [PADDLE_RESULTS.json](PADDLE_RESULTS.json),
  `evaluation_subset_200`. Canonical evaluation includes per-page/category/language
  metrics, predictions, coverage, failures, phase timings and checksummed manifests.

The bounded-subset implementation passed all 216 suite tests and Ruff before
inference. The report generator validated the completed run and evaluation;
the generated figure was visually reviewed. Final tracking, hardware and cohort
checks passed (73 tests), alongside Ruff and whitespace validation. Frozen sources/references and previous
model outputs were preserved. This checkpoint does not launch additional pages
or another model.

## Reproduce the cohort

```powershell
benchmark_suite\environments\paddle\Scripts\python.exe -m benchmark_suite.cli run --model paddle --language both --mode full --max-documents 200 --sampling language-round-robin --json
```

This command selects the same cohort; it does not skip these 200 pages to select
a subsequent batch. Incomplete historical runs require their recorded source
identity for resumption.
