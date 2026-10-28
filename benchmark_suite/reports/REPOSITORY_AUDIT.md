# TASK-001 repository audit

Date: 2026-10-28 (Africa/Cairo). Scope: static repository audit only; no OCR execution, installations, dataset/model downloads, service startup or hardware certification.

## Git and safety evidence

- Initial branch: `refactor/production-readiness`; initial HEAD: `309383e`.
- Created requested branch `feature/ocr-comprehensive-benchmark` successfully.
- At first inspection, 18 tracked application/configuration/test files were modified; `Task_codex.txt` and `tests/test_result_cache.py` were untracked. Staging was empty.
- During the audit another process committed those changes as `4215badd51c760f6800ab590938aaf407f659a77` (`Feat: Improve UI`). This task did not author, stage or commit those application changes. The dedicated branch now includes that commit. No reset, stash, cherry-pick or history rewrite was attempted.
- Audited baseline after that external commit: 585 tracked files; aggregate SHA-256 `44d0e6c445f2dbcd5e18b9fde9c4808079a4193d83123829ebfba9323ad60a35`. Algorithm: sorted `git ls-files` paths for existing files; SHA-256 over each UTF-8 path followed by the binary SHA-256 of its bytes. Verify before staging TASK-001 additions.
- `Task_codex.txt` remains a user-owned untracked input and is excluded from this task's commit.
- No AGENTS.md was found in the repository file inventory or checked ancestors (C:/, C:/Users/, C:/Users/Shrouk/, C:/Users/Shrouk/Desktop/). No repository instruction requiring commit approval was found.
- Existing `.env`, model assets, environments, runtime data and historical benchmark files were preserved; secret contents were not read.

## Existing architecture and reuse

| Area | Observed implementation | Reuse decision / gap |
|---|---|---|
| Packaging | pyproject.toml: Python >=3.10, setuptools includes OCR*, frontend*, benchmarks* | New benchmark_suite package is not included by current discovery. TASK-002 must choose source-tree execution or narrowly reviewed packaging inclusion. |
| Production orchestration | OCR/service.py: lazy provider initialization, serialized execution, normalized results, timing and cache | Wrap through a benchmark adapter where appropriate; cache hits cannot count as fresh inference timings. |
| Adapter contract | OCR/providers/base.py: OCRDocument, initialize/health/extract/unload, cache_identity | Good reusable lifecycle; benchmark needs capabilities, metadata and raw-output preservation. |
| Normalized schema | OCR/schemas.py: schema 1.0, text/pages/blocks, explicit bbox coordinates, reading order, metadata, issues and spans | Reuse; add benchmark-specific structures for tables/charts/raw artifacts rather than manufacturing missing fields. |
| PDF utilities | OCR/pdf.py: page count, renderer checks, bounded page rendering | Reuse after confirming DPI/resolution equivalence and external Poppler requirements. |
| Production models | OCR/service.py PROVIDER_TYPES: tesseract, docling, paddle_vl, qwen_ollama | Qwen is outside the requested nine; do not substitute it for Granite or any other candidate. |
| Tesseract | OCR/providers/tesseract.py | Candidate for TASK-013 adapter; language packs and native executable must pass preflight. |
| Docling | OCR/providers/docling.py explicitly uses TesseractCliOcrOptions; table structure enabled | Maps to docling_tesseract only. EasyOCR and Granite require distinct verified configurations. |
| PaddleOCR-VL | OCR/providers/paddle_vl.py specifies pipeline v1.6, PaddleOCR-VL-1.6-0.9B, PP-DocLayoutV3; chart recognition disabled | Existing configuration is evidence of local integration, not proof of current official version/license/capabilities. Verify in TASK-003. Chart scores require a supported explicit configuration. |
| Cache | OCR/result_cache.py: source/config/package/asset identities, SQLite, OS locks, atomic publication | Reuse concepts/interface; benchmark needs immutable run provenance and auditable originals. No assumed reproduction guarantee from filenames alone. |
| Current evaluator | OCR/evaluation.py: jiwer character/word edits, explicit normalization, exact match and character similarity | Validate and reuse text metric primitives; Arabic-specific switches, structured metrics and statistical reporting need suite modules. |
| Historical evaluators | benchmarks/evaluation/{metrics,evaluate_english,evaluate_arabic,evaluate_mix}.py | Preserve existing language policies/formulas. Historical (1-CER/WER) accuracy and rounded values must not silently mix with new metric definitions. |
| Existing runner | benchmarks/run.py: one language/provider, exclusive output directory, JSON records | Useful naming/provenance reference; not a frozen-manifest resumable scientific runner. |
| Application history | OCR/benchmark_api.py and OCR/benchmark_store.py; frontend ground-truth workflow | Existing text evaluation/history useful; not a replacement for immutable full raw model runs. |
| Legacy adapters | benchmarks/legacy/runners/: Surya, Paddle, Marker, Tesseract | Inspect for reusable behavior; do not import/initialize unverified legacy model code during audit. Baidu/Granite output names do not identify a reproducible implementation. |
| Tests | tests/: schemas, providers, API, PDFs, ground truth, caching, benchmark policy guards | Preserve; focused no-inference checks can validate contracts in later tasks. |
| Provisioning | scripts/provision_models.py, check_models.py, launch.ps1, run_app.bat | Provisioning/normal launcher can download assets or start services; do not invoke as a read-only audit or bypass hardware assessment. |
| Documentation | docs/REPOSITORY_AUDIT.md and operational/readiness/ground-truth guides | Useful historical context; some older audit statements predate current cache/locking changes, so current code is authoritative. |

## Existing data and results inventory

Directory counts observed locally (counts are files, not page counts or verified dataset sizes):

| Language | Dataset files | Markdown reference files |
|---|---:|---:|
| English | 32 | 32 |
| Arabic | 30 | 30 |
| Mix | 10 | 10 |

`benchmarks/outputs/` contains historical per-engine Markdown; `benchmarks/results/` contains historical spreadsheets. Preserve these in place. Counts alone do not establish correct pairings, ground-truth authorship, licenses, test split independence or annotated layout/table/chart/reading-order labels. TASK-004/005 must verify those. Existing generated OCR is never ground truth. No historical scores were recalculated or represented as new measurements.

## Potential compatibility and reproducibility issues

1. Invoked system Python is 3.13.7. Both .venv and .venv-ocr interpreters exist, but their package versions and readiness were not probed. Repo Python lower bound is not proof every native model supports 3.13. Verify supported Python/wheels per model and isolate environments.
2. requirements-models.txt pins paddleocr[doc-parser]==3.6.0 and docling==2.80.0; Windows CPU file pins paddlepaddle==3.2.2. Other dependencies have ranges and a Windows lock exists. These are repository pins, not validated cross-model compatibility claims. Do not install all optional stacks together.
3. OCR/resources.py currently reads Linux cgroup/proc memory limits and returns None when unavailable. This does not establish safe memory capacity on Windows. Implement Windows-aware total/available RAM, VRAM and disk preflight before any model execution.
4. Hardware specifications, CUDA/driver compatibility, GPU availability and WSL2 readiness are unassessed. All nine hardware compatibility statuses remain UNKNOWN pending TASK-003. No model has been certified locally compatible by this audit.
5. Poppler/Tesseract executables and eng/ara language assets need explicit checks. Existing native paths and environment settings must remain private and portable configurations must avoid hardcoded machine paths.
6. Surya, Marker, standard PaddleOCR, Docling+EasyOCR and Granite lack equivalent registered production adapters. Legacy runners can depend on old APIs, instantiate models or download weights; adapt only after official-source research and preflight.
7. Baidu implementation is unresolved: API versus other integration. Do not infer it from historical folder names; clarify before setup or credential use. No paid API call is authorized implicitly.
8. Current output schema is insufficient as a complete typed table/chart/run contract. Preserve optional/null fields, actual raw outputs, label mappings and coordinate transforms in a suite compatibility layer.
9. Current benchmark dataset folders have no verified versioned public-source/license/annotation inventory from this audit. Do not infer table structure from plain Markdown or invent chart/reading-order ground truth.
10. Existing cache can return old measured inference time. Record cache reuse separately and perform explicit cold/warm measurements under the validated suite policy. Compare throughput only on qualified equivalent hardware/configuration.
11. Root ignore rules cover many assets, but no suite-specific data/run artifact policy exists yet. TASK-002 must add protection before downloads/runs; TASK-001 adds only reviewed Markdown and progress JSON.
12. Concurrent repository activity was observed. Before every checkpoint recheck branch, HEAD, staging and diffs; preserve unrelated work and commit only task-owned paths.

## TASK-001 acceptance evidence

Requested branch created; repository/provider/data/metric inventory completed; reuse and compatibility gaps documented; initial 21-task plan and persistent progress records created. Detailed current hardware/vendor/dataset research is deferred to TASK-003/004 as required by the task boundary. No quantitative model results exist for the new suite.
