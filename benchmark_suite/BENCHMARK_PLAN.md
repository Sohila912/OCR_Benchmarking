# OCR benchmark implementation plan

Source of requirements: repository-root `Task_codex.txt`. Created 2026-10-28 (Africa/Cairo).

## Execution and resume contract

TASK-001 through TASK-004 are complete. On 2026-10-28 the user approved local acquisition and continuation for TASK-005, superseding Drive storage. TASK-005 is complete: stop at its checkpoint before TASK-006. Hardware blockers still prevent model loading. Complete one task at a time. Every model task stops separately; never advance to another model without explicit approval. No model or dataset downloads in TASK-001.

At every new session read this plan, PROGRESS.md and BENCHMARK_STATUS.json; check Git branch/status and relevant artifacts; validate the last checkpoint before continuing the first incomplete approved task. Preserve existing files/results and user work. Commit only explicitly selected task files after checks. Never stage credentials, downloaded datasets or model weights. Do not use blanket staging.

All file paths below are relative to `benchmark_suite/` unless explicitly prefixed by the repository directory. Every task also updates PROGRESS.md and BENCHMARK_STATUS.json. Commands are planned acceptance commands, and are executable only once their task implements them. Do not run a model command until TASK-003 preflight and required approvals succeed.

Task/model state enum: PENDING, IN_PROGRESS, BLOCKED, COMPLETED, FAILED, SKIPPED. Store `BLOCKED_BY_HARDWARE` in the separate model/task reason field while state stays BLOCKED. Capability/evaluation statuses (`NOT_SUPPORTED`, `NOT_EVALUATED`) are distinct from task states. UNKNOWN hardware compatibility must never bypass preflight.

Future runtime layout is isolated under this directory. Reuse `OCR.schemas`, provider lifecycle, PDF helpers, logging and validated metric/cache components via a compatibility layer; production schema/pipeline remains unchanged unless a reviewed essential change is required. No full directory scaffold or runtime implementation is part of TASK-001.

General definition of done: stated acceptance criteria and checks pass (or blocker is accurately recorded without marking complete); artifacts persist; progress is coherent; a task-only Git checkpoint is created when permitted; completion report names files/tests/results/issues/commit/next task/resume prompt.

## TASK-001: Repository audit and branch creation

- Objective: Audit existing implementations; create the requested branch and initial resumable records.
- Dependencies: None.
- Files to create/modify: BENCHMARK_PLAN.md; PROGRESS.md; BENCHMARK_STATUS.json; reports/REPOSITORY_AUDIT.md.
- Acceptance criteria: Requested branch exists; reusable components and risks are documented; existing files are preserved; all 21 tasks and nine models are tracked.
- Verification commands: `git branch --show-current; git diff --check; python -m json.tool benchmark_suite/BENCHMARK_STATUS.json`
- Expected outputs: Audit report and initial checkpoint.
- Definition of done: acceptance criteria plus general definition above; model tasks require an explicit STOP.
- Next task: TASK-002 (requires user approval).

## TASK-002: Benchmark architecture and progress tracking

- Objective: Define benchmark boundaries and implement validated, atomic checkpoint persistence.
- Dependencies: TASK-001 and explicit user approval.
- Files to create/modify: README.md; ARCHITECTURE.md; __init__.py; tracking.py; tests/test_tracking.py; .gitignore; repository-root pytest.ini (include suite tests in default discovery).
- Acceptance criteria: Architecture reuses existing contracts; state transitions and schema are validated; same-directory temporary write plus os.replace protects status; interruption and invalid-state tests pass; ignore rules exclude datasets, weights, environments, secrets and run artifacts.
- Verification commands: `python -m pytest benchmark_suite/tests/test_tracking.py -q`
- Expected outputs: Architecture, state writer, tests and safe artifact policy.
- Definition of done: acceptance criteria plus general definition above; model tasks require an explicit STOP.
- Next task: TASK-003.

## TASK-003: Model capability, dependency and hardware research

- Objective: Verify all nine exact model configurations using official sources and detect laptop resources before any model installation or execution.
- Dependencies: TASK-002.
- Files to create/modify: MODEL_REGISTRY.yaml; reports/HARDWARE_PROFILE.md; reports/HARDWARE_PROFILE.json; reports/RESEARCH_METADATA.json; reports/MODEL_HARDWARE_COMPATIBILITY.md; reports/MODEL_CAPABILITIES.md; scripts/check_hardware.py; tests/test_hardware.py; .gitignore (ignore preserved incomplete/repeated observations).
- Acceptance criteria: Record CPU/cores, total/available RAM, GPUs/VRAM, CUDA/driver, Windows/Python, disk, WSL2 and Torch/Paddle GPU support; cite dated official versions/licenses/languages/capabilities; distinguish documented requirements from estimates; assign COMPATIBLE/LIMITED/INCOMPATIBLE/UNKNOWN with concrete remedies and costs. Present free-local strategy and all nine compatibility assessments. Missing evidence remains UNKNOWN. Successful assessment is mandatory before ANY model setup/execution.
- Verification commands: `python benchmark_suite/scripts/check_hardware.py --output benchmark_suite/reports; python -m pytest benchmark_suite/tests/test_hardware.py -q`
- Expected outputs: Hardware evidence, compatibility matrix and verified model registry.
- Definition of done: acceptance criteria plus general definition above; model tasks require an explicit STOP.
- Next task: TASK-004.

## TASK-004: Dataset research and selection

- Objective: Select English and Arabic public ground-truth datasets and supplements for missing annotations.
- Dependencies: TASK-002.
- Files to create/modify: datasets/DATASET_SELECTION.md; datasets/SOURCE_RESEARCH.json; datasets/EXISTING_DATA_AUDIT.json; .gitignore (allow reviewed research metadata only); README.md (selection and acquisition gate).
- Acceptance criteria: Cite source/version/license, size/counts, languages, exact ground truth, categories, procedure and limitations; review existing datasets provenance; do not download large/restricted data; explicitly record download approval needed.
- Verification commands: `Get-Content benchmark_suite/datasets/DATASET_SELECTION.md`
- Expected outputs: Reviewable dataset selection and download proposal.
- Definition of done: acceptance criteria plus general definition above; model tasks require an explicit STOP.
- Next task: TASK-005.

## TASK-005: Dataset acquisition and standardization

- Objective: Acquire approved datasets and freeze identical deterministic evaluation manifests.
- Dependencies: TASK-004; approval for large/restricted downloads; disk check.
- Files to create/modify: dataset_io.py; dataset_preparation.py; scripts/prepare_datasets.py; tests/test_datasets.py; requirements-datasets.txt; datasets/README.md; datasets/manifest/schema.json; datasets/manifest/development.jsonl; datasets/manifest/evaluation.jsonl; datasets/manifest/PROVENANCE.json; datasets/manifest/ACQUISITION_PROVENANCE.json; datasets/manifest/LEGACY_ALIASES.json; datasets/DATASET_SELECTION.md; reports/DATASET_VALIDATION.md; README.md. Raw/decoded payloads and acquisition journals stay ignored.
- Acceptance criteria: Record source/version/date/checksums and document ID/path/hash/language/category/pages/reference/annotations/split/capabilities; validate all pairings and source permission; prevent leakage; freeze seed and subset; OCR outputs never become ground truth.
- Verification commands: `python benchmark_suite/scripts/prepare_datasets.py --validate-only; python -m pytest benchmark_suite/tests/test_datasets.py -q`
- Expected outputs: Validated frozen development/full manifests and acquisition provenance.
- Definition of done: acceptance criteria plus general definition above; model tasks require an explicit STOP.
- Next task: TASK-006.

## TASK-006: Evaluation metrics implementation

- Objective: Implement independently testable metrics only for available trusted annotations.
- Dependencies: TASK-002; TASK-004 annotation specification.
- Files to create/modify: metrics/__init__.py; metrics/text.py; metrics/layout.py; metrics/reading_order.py; metrics/tables.py; metrics/charts.py; metrics/statistics.py; configs/evaluation.json; tests/test_metrics.py.
- Acceptance criteria: Specify CER/WER, accuracy, NED, exact match, matching-unit PR/F1 and empty-input behavior; preserve raw/normalized Arabic scores (Unicode, whitespace, diacritics, alef, hamza, tatweel); define canonical labels/IoU/mAP and reading-order matching/tau/inversions; genuine TEDS/cell/merge/header metrics and separately chart detection/type/text/numeric metrics; explicit missing statuses; micro/macro distributions and document bootstrap 95% CI with seed. Preserve historical policies.
- Verification commands: `python -m pytest benchmark_suite/tests/test_metrics.py -q`
- Expected outputs: Documented formulas, metric calculators and hand-checked edge cases.
- Definition of done: acceptance criteria plus general definition above; model tasks require an explicit STOP.
- Next task: TASK-007.

## TASK-007: Common model adapter and runner

- Objective: Add a benchmark compatibility layer, immutable runs, preflight and recovery around reusable production contracts.
- Dependencies: TASK-003, TASK-005, TASK-006.
- Files to create/modify: adapters/base.py; adapters/existing.py; runners/run.py; runners/preflight.py; runners/cache.py; runners/schemas.py; tests/test_runner.py.
- Acceptance criteria: Explicit initialize/predict/normalize/capabilities/metadata/cleanup lifecycle; raw outputs plus normalized schema; preflight blocks unsafe RAM/VRAM/disk configs before loading; unique exclusive run IDs, atomic progress, errors and resumable document/config/version/hash cache; invalidate meaningful changes; distinguish cache hits from inference and cold/warm timing; preserve resolution/DPI/precision/batch/device/local-cloud identity; interrupted/partial failures and no duplicate completed inference verified using fakes.
- Verification commands: `python -m pytest benchmark_suite/tests/test_runner.py -q`
- Expected outputs: Safe single-model runner, immutable manifests, logs and recovery.
- Definition of done: acceptance criteria plus general definition above; model tasks require an explicit STOP.
- Next task: TASK-008.

## TASK-008: Windows execution tools and README

- Objective: Provide the 13-option Windows launcher and matching Python CLI without implicit provisioning.
- Dependencies: TASK-003, TASK-005, TASK-006, TASK-007.
- Files to create/modify: scripts/run_benchmark.bat; cli.py; README.md; configs/models.json; tests/test_cli.py.
- Acceptance criteria: Menu matches Task_codex.txt; Python/dependency/dataset/readiness checks, one model and English/Arabic/both, quick/full/resume/evaluate/report/compare modes; logs and understandable failures; isolated pinned model environments; no silent all-model run, redundant installs or unsafe environment changes. Fake smoke tests need no weights. Clearly mark comparison commands pending TASK-018/019.
- Verification commands: `python -m pytest benchmark_suite/tests/test_cli.py -q; python -m benchmark_suite.cli --help`
- Expected outputs: Windows launcher, equivalent automation commands and initial usage documentation.
- Definition of done: acceptance criteria plus general definition above; model tasks require an explicit STOP.
- Next task: TASK-009.

## TASK-009: Surya OCR

- Objective: Set up and quantitatively evaluate exactly this selected model, then STOP.
- Dependencies: TASK-003 successful hardware assessment; TASK-005 through TASK-008; explicit approval before advancing from a preceding model.
- Files to create/modify: adapters/surya.py; configs/surya.json; tests/test_surya.py; results/surya/<unique_run_id>/; results/surya/selected_run.json.
- Acceptance criteria: Preflight before installation/loading; exact verified model/version/license and isolated pinned environment; same frozen documents and raw settings; save predictions/raw/normalized outputs, manifest/config/environment, per-document/page/language/category/structure/performance metrics CSV/JSON, failures/errors, visualizations, reproduction commands and MODEL_REPORT.md. Record initialization/preprocess/inference/postprocess timing, peak RAM/VRAM, success counts and missing categories. No invented values. Blocked execution is BLOCKED with reason BLOCKED_BY_HARDWARE when applicable, never a fabricated completed evaluation. Update progress and stop.
- Verification commands: `python -m pytest benchmark_suite/tests/test_surya.py -q; python -m benchmark_suite.cli check-environment --model surya; python -m benchmark_suite.cli run --model surya --language both --mode quick; python -m benchmark_suite.cli run --model surya --language both --mode full; python -m benchmark_suite.cli report --model surya`
- Expected outputs: Auditable individual model run/report, or explicit blocker report without invented scores.
- Definition of done: acceptance criteria plus general definition above; model tasks require an explicit STOP.
- Next task: TASK-010 (requires user approval).

## TASK-010: PaddleOCR-VL

- Objective: Set up and quantitatively evaluate exactly this selected model, then STOP.
- Dependencies: TASK-003 successful hardware assessment; TASK-005 through TASK-008; explicit approval before advancing from a preceding model.
- Files to create/modify: adapters/paddle_vl.py; configs/paddle_vl.json; tests/test_paddle_vl.py; results/paddle_vl/<unique_run_id>/; results/paddle_vl/selected_run.json.
- Acceptance criteria: Preflight before installation/loading; exact verified model/version/license and isolated pinned environment; same frozen documents and raw settings; save predictions/raw/normalized outputs, manifest/config/environment, per-document/page/language/category/structure/performance metrics CSV/JSON, failures/errors, visualizations, reproduction commands and MODEL_REPORT.md. Record initialization/preprocess/inference/postprocess timing, peak RAM/VRAM, success counts and missing categories. No invented values. Blocked execution is BLOCKED with reason BLOCKED_BY_HARDWARE when applicable, never a fabricated completed evaluation. Update progress and stop.
- Verification commands: `python -m pytest benchmark_suite/tests/test_paddle_vl.py -q; python -m benchmark_suite.cli check-environment --model paddle_vl; python -m benchmark_suite.cli run --model paddle_vl --language both --mode quick; python -m benchmark_suite.cli run --model paddle_vl --language both --mode full; python -m benchmark_suite.cli report --model paddle_vl`
- Expected outputs: Auditable individual model run/report, or explicit blocker report without invented scores.
- Definition of done: acceptance criteria plus general definition above; model tasks require an explicit STOP.
- Next task: TASK-011 (requires user approval).

## TASK-011: Marker

- Objective: Set up and quantitatively evaluate exactly this selected model, then STOP.
- Dependencies: TASK-003 successful hardware assessment; TASK-005 through TASK-008; explicit approval before advancing from a preceding model.
- Files to create/modify: adapters/marker.py; configs/marker.json; tests/test_marker.py; results/marker/<unique_run_id>/; results/marker/selected_run.json.
- Acceptance criteria: Preflight before installation/loading; exact verified model/version/license and isolated pinned environment; same frozen documents and raw settings; save predictions/raw/normalized outputs, manifest/config/environment, per-document/page/language/category/structure/performance metrics CSV/JSON, failures/errors, visualizations, reproduction commands and MODEL_REPORT.md. Record initialization/preprocess/inference/postprocess timing, peak RAM/VRAM, success counts and missing categories. No invented values. Blocked execution is BLOCKED with reason BLOCKED_BY_HARDWARE when applicable, never a fabricated completed evaluation. Update progress and stop.
- Verification commands: `python -m pytest benchmark_suite/tests/test_marker.py -q; python -m benchmark_suite.cli check-environment --model marker; python -m benchmark_suite.cli run --model marker --language both --mode quick; python -m benchmark_suite.cli run --model marker --language both --mode full; python -m benchmark_suite.cli report --model marker`
- Expected outputs: Auditable individual model run/report, or explicit blocker report without invented scores.
- Definition of done: acceptance criteria plus general definition above; model tasks require an explicit STOP.
- Next task: TASK-012 (requires user approval).

## TASK-012: PaddleOCR

- Objective: Set up and quantitatively evaluate exactly this selected model, then STOP.
- Dependencies: TASK-003 successful hardware assessment; TASK-005 through TASK-008; explicit approval before advancing from a preceding model.
- Files to create/modify: adapters/paddle.py; configs/paddle.json; tests/test_paddle.py; results/paddle/<unique_run_id>/; results/paddle/selected_run.json.
- Acceptance criteria: Preflight before installation/loading; exact verified model/version/license and isolated pinned environment; same frozen documents and raw settings; save predictions/raw/normalized outputs, manifest/config/environment, per-document/page/language/category/structure/performance metrics CSV/JSON, failures/errors, visualizations, reproduction commands and MODEL_REPORT.md. Record initialization/preprocess/inference/postprocess timing, peak RAM/VRAM, success counts and missing categories. No invented values. Blocked execution is BLOCKED with reason BLOCKED_BY_HARDWARE when applicable, never a fabricated completed evaluation. Update progress and stop.
- Verification commands: `python -m pytest benchmark_suite/tests/test_paddle.py -q; python -m benchmark_suite.cli check-environment --model paddle; python -m benchmark_suite.cli run --model paddle --language both --mode quick; python -m benchmark_suite.cli run --model paddle --language both --mode full; python -m benchmark_suite.cli report --model paddle`
- Expected outputs: Auditable individual model run/report, or explicit blocker report without invented scores.
- Definition of done: acceptance criteria plus general definition above; model tasks require an explicit STOP.
- Next task: TASK-013 (requires user approval).

## TASK-013: Tesseract

- Objective: Set up and quantitatively evaluate exactly this selected model, then STOP.
- Dependencies: TASK-003 successful hardware assessment; TASK-005 through TASK-008; explicit approval before advancing from a preceding model.
- Files to create/modify: adapters/tesseract.py; configs/tesseract.json; tests/test_tesseract.py; results/tesseract/<unique_run_id>/; results/tesseract/selected_run.json.
- Acceptance criteria: Preflight before installation/loading; exact verified model/version/license and isolated pinned environment; same frozen documents and raw settings; save predictions/raw/normalized outputs, manifest/config/environment, per-document/page/language/category/structure/performance metrics CSV/JSON, failures/errors, visualizations, reproduction commands and MODEL_REPORT.md. Record initialization/preprocess/inference/postprocess timing, peak RAM/VRAM, success counts and missing categories. No invented values. Blocked execution is BLOCKED with reason BLOCKED_BY_HARDWARE when applicable, never a fabricated completed evaluation. Update progress and stop.
- Verification commands: `python -m pytest benchmark_suite/tests/test_tesseract.py -q; python -m benchmark_suite.cli check-environment --model tesseract; python -m benchmark_suite.cli run --model tesseract --language both --mode quick; python -m benchmark_suite.cli run --model tesseract --language both --mode full; python -m benchmark_suite.cli report --model tesseract`
- Expected outputs: Auditable individual model run/report, or explicit blocker report without invented scores.
- Definition of done: acceptance criteria plus general definition above; model tasks require an explicit STOP.
- Next task: TASK-014 (requires user approval).

## TASK-014: Docling + EasyOCR

- Objective: Set up and quantitatively evaluate exactly this selected model, then STOP.
- Dependencies: TASK-003 successful hardware assessment; TASK-005 through TASK-008; explicit approval before advancing from a preceding model.
- Files to create/modify: adapters/docling_easyocr.py; configs/docling_easyocr.json; tests/test_docling_easyocr.py; results/docling_easyocr/<unique_run_id>/; results/docling_easyocr/selected_run.json.
- Acceptance criteria: Preflight before installation/loading; exact verified model/version/license and isolated pinned environment; same frozen documents and raw settings; save predictions/raw/normalized outputs, manifest/config/environment, per-document/page/language/category/structure/performance metrics CSV/JSON, failures/errors, visualizations, reproduction commands and MODEL_REPORT.md. Record initialization/preprocess/inference/postprocess timing, peak RAM/VRAM, success counts and missing categories. No invented values. Blocked execution is BLOCKED with reason BLOCKED_BY_HARDWARE when applicable, never a fabricated completed evaluation. Update progress and stop.
- Verification commands: `python -m pytest benchmark_suite/tests/test_docling_easyocr.py -q; python -m benchmark_suite.cli check-environment --model docling_easyocr; python -m benchmark_suite.cli run --model docling_easyocr --language both --mode quick; python -m benchmark_suite.cli run --model docling_easyocr --language both --mode full; python -m benchmark_suite.cli report --model docling_easyocr`
- Expected outputs: Auditable individual model run/report, or explicit blocker report without invented scores.
- Definition of done: acceptance criteria plus general definition above; model tasks require an explicit STOP.
- Next task: TASK-015 (requires user approval).

## TASK-015: Docling + Tesseract

- Objective: Set up and quantitatively evaluate exactly this selected model, then STOP.
- Dependencies: TASK-003 successful hardware assessment; TASK-005 through TASK-008; explicit approval before advancing from a preceding model.
- Files to create/modify: adapters/docling_tesseract.py; configs/docling_tesseract.json; tests/test_docling_tesseract.py; results/docling_tesseract/<unique_run_id>/; results/docling_tesseract/selected_run.json.
- Acceptance criteria: Preflight before installation/loading; exact verified model/version/license and isolated pinned environment; same frozen documents and raw settings; save predictions/raw/normalized outputs, manifest/config/environment, per-document/page/language/category/structure/performance metrics CSV/JSON, failures/errors, visualizations, reproduction commands and MODEL_REPORT.md. Record initialization/preprocess/inference/postprocess timing, peak RAM/VRAM, success counts and missing categories. No invented values. Blocked execution is BLOCKED with reason BLOCKED_BY_HARDWARE when applicable, never a fabricated completed evaluation. Update progress and stop.
- Verification commands: `python -m pytest benchmark_suite/tests/test_docling_tesseract.py -q; python -m benchmark_suite.cli check-environment --model docling_tesseract; python -m benchmark_suite.cli run --model docling_tesseract --language both --mode quick; python -m benchmark_suite.cli run --model docling_tesseract --language both --mode full; python -m benchmark_suite.cli report --model docling_tesseract`
- Expected outputs: Auditable individual model run/report, or explicit blocker report without invented scores.
- Definition of done: acceptance criteria plus general definition above; model tasks require an explicit STOP.
- Next task: TASK-016 (requires user approval).

## TASK-016: Granite Docling

- Objective: Set up and quantitatively evaluate exactly this selected model, then STOP.
- Dependencies: TASK-003 successful hardware assessment; TASK-005 through TASK-008; explicit approval before advancing from a preceding model.
- Files to create/modify: adapters/granite_docling.py; configs/granite_docling.json; tests/test_granite_docling.py; results/granite_docling/<unique_run_id>/; results/granite_docling/selected_run.json.
- Acceptance criteria: Preflight before installation/loading; exact verified model/version/license and isolated pinned environment; same frozen documents and raw settings; save predictions/raw/normalized outputs, manifest/config/environment, per-document/page/language/category/structure/performance metrics CSV/JSON, failures/errors, visualizations, reproduction commands and MODEL_REPORT.md. Record initialization/preprocess/inference/postprocess timing, peak RAM/VRAM, success counts and missing categories. No invented values. Blocked execution is BLOCKED with reason BLOCKED_BY_HARDWARE when applicable, never a fabricated completed evaluation. Update progress and stop.
- Verification commands: `python -m pytest benchmark_suite/tests/test_granite_docling.py -q; python -m benchmark_suite.cli check-environment --model granite_docling; python -m benchmark_suite.cli run --model granite_docling --language both --mode quick; python -m benchmark_suite.cli run --model granite_docling --language both --mode full; python -m benchmark_suite.cli report --model granite_docling`
- Expected outputs: Auditable individual model run/report, or explicit blocker report without invented scores.
- Definition of done: acceptance criteria plus general definition above; model tasks require an explicit STOP.
- Next task: TASK-017 (requires user approval).

## TASK-017: Baidu OCR

- Objective: Set up and quantitatively evaluate exactly this selected model, then STOP. Confirm Baidu API versus other implementation and credentials/limits/cost; obtain approval before paid calls.
- Dependencies: TASK-003 successful hardware assessment; TASK-005 through TASK-008; explicit approval before advancing from a preceding model.
- Files to create/modify: adapters/baidu.py; configs/baidu.json; tests/test_baidu.py; results/baidu/<unique_run_id>/; results/baidu/selected_run.json.
- Acceptance criteria: Preflight before installation/loading; exact verified model/version/license and isolated pinned environment; same frozen documents and raw settings; save predictions/raw/normalized outputs, manifest/config/environment, per-document/page/language/category/structure/performance metrics CSV/JSON, failures/errors, visualizations, reproduction commands and MODEL_REPORT.md. Record initialization/preprocess/inference/postprocess timing, peak RAM/VRAM, success counts and missing categories. No invented values. Blocked execution is BLOCKED with reason BLOCKED_BY_HARDWARE when applicable, never a fabricated completed evaluation. Update progress and stop.
- Verification commands: `python -m pytest benchmark_suite/tests/test_baidu.py -q; python -m benchmark_suite.cli check-environment --model baidu; python -m benchmark_suite.cli run --model baidu --language both --mode quick; python -m benchmark_suite.cli run --model baidu --language both --mode full; python -m benchmark_suite.cli report --model baidu`
- Expected outputs: Auditable individual model run/report, or explicit blocker report without invented scores.
- Definition of done: acceptance criteria plus general definition above; model tasks require an explicit STOP.
- Next task: TASK-018.

## TASK-018: Cross-model comparison engine

- Objective: Compare stored selected official runs without repeating inference.
- Dependencies: At least two valid model runs; TASK-006 and TASK-007.
- Files to create/modify: runners/compare.py; results/comparisons/model_comparison.csv; results/comparisons/model_comparison.json; tests/test_compare.py.
- Acceptance criteria: Validate frozen dataset, evaluator, preprocessing and version compatibility; rank selected metric with direction and coverage; PENDING models are never zeros; local/cloud speed and resource comparisons qualified by hardware; configurable justified composite only with disclosed weights and missingness.
- Verification commands: `python -m pytest benchmark_suite/tests/test_compare.py -q; python -m benchmark_suite.cli compare`
- Expected outputs: Sortable comparison CSV/JSON with provenance and coverage.
- Definition of done: acceptance criteria plus general definition above; model tasks require an explicit STOP.
- Next task: TASK-019.

## TASK-019: Visualizations and comparative reports

- Objective: Generate measured comparisons across languages, categories, layout, tables, charts, reading order, runtime and resources.
- Dependencies: TASK-018.
- Files to create/modify: reports/COMPARATIVE_REPORT.md; reports/visualizations/; runners/report.py; tests/test_reports.py.
- Acceptance criteria: Report CER/WER, layout F1, TEDS, chart metrics when annotated, success rates and coverage; charts/heatmaps/speed-accuracy plots label hardware/missingness; support distributions/CI; regenerate entirely from saved metrics.
- Verification commands: `python -m pytest benchmark_suite/tests/test_reports.py -q; python -m benchmark_suite.cli final-report`
- Expected outputs: Reviewable comparative report and metric visualizations.
- Definition of done: acceptance criteria plus general definition above; model tasks require an explicit STOP.
- Next task: TASK-020.

## TASK-020: Reproducibility and audit tests

- Objective: Audit end-to-end reproducibility, metric validity, recovery and result completeness.
- Dependencies: TASK-018 and TASK-019; all approved model attempts recorded.
- Files to create/modify: tests/test_reproducibility.py; tests/test_audit.py; reports/REPRODUCIBILITY_AUDIT.md.
- Acceptance criteria: Verify source/dataset/config/environment hashes, identical metric recomputation, missing/failure handling, interruption recovery, cached-versus-new timings, all required model artifacts and no secrets/large assets in Git. No claim that unavailable models were evaluated.
- Verification commands: `python -m pytest benchmark_suite/tests -q; python -m pytest tests -q; git diff --check`
- Expected outputs: Reproducibility audit with exact successful/failed/skipped checks.
- Definition of done: acceptance criteria plus general definition above; model tasks require an explicit STOP.
- Next task: TASK-021.

## TASK-021: Final documentation

- Objective: Complete reproducible usage and evidence-based conclusions.
- Dependencies: TASK-020.
- Files to create/modify: README.md; reports/COMPARATIVE_REPORT.md; reports/LIMITATIONS.md.
- Acceptance criteria: README covers all required purpose/models/data/licenses/methods/formulas/Arabic normalization/environment/install/Windows/CLI/smoke/resume/interpretation/comparison/reports/troubleshooting topics; verify commands on documented environment; conclusions cite measured artifacts; document blockers and unsupported categories.
- Verification commands: `python -m benchmark_suite.cli --help; python -m pytest benchmark_suite/tests -q; git diff --check`
- Expected outputs: Reproduction guide and final measured conclusions.
- Definition of done: acceptance criteria plus general definition above; model tasks require an explicit STOP.
- Next task: None; project checkpoint.
