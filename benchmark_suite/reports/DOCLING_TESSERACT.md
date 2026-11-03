# Docling + Tesseract: development checkpoint

2026-11-03 (Africa/Cairo), TASK-015. The user approved this model and then
explicitly requested saving/pushing the reached checkpoint and moving to
Granite Docling instead of running the multi-hour full evaluation.

## Measured result

The registered shared-runner development run attempted all 20 frozen images:
**19 succeeded, one timed out (95% conversion completion)**. This is not a claim
of 95% OCR accuracy. The timed-out Arabic image was not assigned an accuracy score.

| Language | Attempted | Text scored | Normalized CER | Normalized WER |
|---|---:|---:|---:|---:|
| English | 10 | 10 | 26.69% | 40.09% |
| Arabic | 10 | 9 | 50.26% | 67.47% |

CER/WER are error rates; lower is better. English uses independently allocated
reference-region text; Arabic uses page-content text from publisher Markdown.
These scopes differ. Scores are conditional on the scored subset, and do not
include the failed page as a zero. Page bootstrap intervals are recorded in the
JSON report; source-document independence is unknown.

English layout micro F1 at IoU 0.5 was 0.48731 (48 TP, 43 FP, 58 FN). Native
per-block confidence is unavailable, so mAP is not reported. Arabic independent
layout/order truth is unavailable. Table reference coverage is very small:
one scored English table (TEDS 0.01224; another reference table unscored) and
one scored Arabic table (TEDS 0.0). Inspect per-page/category/structure CSVs before
interpreting these numbers. Chart understanding is disabled.

The recorded run wall time was 662.99 seconds (about 11 minutes). Successful
fresh inference calls totaled 360.64 seconds, averaging 18.98 seconds/page.
Those calls include native conversion, normalization/export and local IPC;
separate backend measurements are retained in the raw JSON. Peak sampled
benchmark-process-plus-descendants RSS was 2,228,310,016 bytes (2.08 GiB).
RSS is sampled every 50 ms and includes shared pages; it is not an allocator peak.

## Timeout and scope

The failed image is
`misraj:7177bf70f77ce259890d6af0bef53f18faf26ec9:1e70bf91-ca63-4372-88f9-386b35222a27`.
Docling returned PARTIAL_SUCCESS with a 180-second document timeout, incomplete
pipeline stages and reading-order separator extraction exceeding its time budget.
The adapter recorded a failure and restarted its owned worker for subsequent
images. Partial output was not silently treated as a complete prediction.
This run did not fail from the EasyOCR allocation error observed in TASK-014.

**The 1,135-image evaluation split was not run, at the user's explicit request.**
No official evaluation selected-run marker is created. TASK-015 remains a saved
partial task with full evaluation deferred; it is not marked fully completed or
hardware-incompatible. The next model, TASK-016, was explicitly approved.

## Configuration and storage

- Docling 2.143.1, CPU standard image pipeline with layout and table processing.
- Tesseract CLI 5.4.0.20240606, PSM 3, OEM auto with LSTM-only `tessdata_fast`.
  English uses `eng`, Arabic uses `ara`; no mixed-language recognition fallback.
- One CPU/OpenMP thread, one page/worker at a time, batch sizes one. Full-page
  OCR and the upstream internal OCR scale 3.0 are retained. Original frozen image
  files are copied byte-identically to D: and verified by SHA256.
- Native executable, DLLs, English/Arabic traineddata, OSD and TSV config are on
  D:/OCR_Benchmarking_Assets/docling_tesseract/. Their hashes are recorded in
  DOCLING_TESSERACT_ASSETS.json and configs/docling_tesseract-spec.json.
- The already-installed, separately pinned CPU Docling runtime and cached
  layout/table weights on D:/OCR_Benchmarking_Assets/docling_easyocr/ are reused
  read-only. This backend selects Tesseract CLI; no EasyOCR inference runs.
  No package upgrades or model downloads were needed for this task.
- A small dedicated shared-runner/evaluation environment is registered under
  environments/docling_tesseract/ in the existing repository. All model loading,
  native processing inputs, temporary files, worker logs and native outputs use D:.
  Canonical shared-runner receipts/evaluation metadata remain in the repository;
  a complete evaluation copy and charts are also saved on D:.
- Windows jobs cap worker/descendant committed memory at up to 4 GiB, bounded
  by measured availability minus 0.75 GiB at start. A supervisor stops owned
  processes if system availability drops below 512 MiB. Generic 2-GiB and model
  3-GiB preflight floors remain. No Windows page-file/security settings changed.

The preliminary one-page-per-language trial succeeded, but its logs revealed
missing OSD data. OSD was copied and hashed before the registered 20-page run.
That preliminary calibration is not substituted for clean development metrics.

## Artifacts and reproduction

- Run: results/docling_tesseract/20261103T095733Z-880fa5ba/.
- Offline evaluation: results/docling_tesseract/evaluations/20261103T095733Z-880fa5ba/a4e76676858e-29c9d1da/.
- D: report, PNG/SVG charts, summary and canonical copy:
  D:/OCR_Benchmarking_Assets/docling_tesseract/reports/development-20261103-reviewed/.
- Versioned quantitative summary: DOCLING_TESSERACT_RESULTS.json.
- Native document JSON, Markdown and normalized output: D:/OCR_Benchmarking_Assets/docling_tesseract/native_outputs/.
- Worker logs: D:/OCR_Benchmarking_Assets/docling_tesseract/worker_logs/.

Raw envelopes retain unmodified DoclingDocument exports and Markdown, native
table HTML, original coordinates/hierarchy, worker versions and detailed backend
timings. The production normalizer is reused, without changing production code.
Native hierarchy iteration supplies order; reference geometry is never used to
construct predictions. Unsupported label mappings/reference gaps remain explicit.
Language-switch worker initialization is timed in external preprocessing; initial
worker startup is timed in initialization. Native Tesseract starts per-page within
conversion. These boundaries qualify latency comparisons with other configurations.

Saved predictions can be reevaluated without loading a model:

```powershell
benchmark_suite\environments\docling_tesseract\Scripts\python.exe -m benchmark_suite.cli report --model docling_tesseract --run-dir benchmark_suite/results/docling_tesseract/20261103T095733Z-880fa5ba --json
```

Inference requires reactivating the already-approved task through the validated
tracker, verifying exact source/model/runtime hashes and passing live preflight.
The development run is complete and immutable; rerunning creates a new run.
The full evaluation is intentionally deferred. Existing Tesseract partial data
and all prior model outcomes are preserved; resumption requires their original
recorded code/configuration identity.

Verification: 206 suite tests pass; Ruff, native/asset copy checks, the real
Windows memory-guard test, registered environment preflight and offline evaluation
passed. The raw timeout remains visible as a model-run failure, not a software-test
failure. No other model was executed during this task.
