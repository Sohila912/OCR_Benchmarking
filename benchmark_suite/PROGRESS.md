# Benchmark progress

Updated: 2026-10-28 (Africa/Cairo).

## Checkpoint

- Completed: TASK-001 (audit), TASK-002 (tracking/architecture), TASK-003 (hardware/model research), TASK-004 (dataset research/selection).
- Current / first incomplete task: TASK-005, PENDING. Explicit primary-download approval is required before acquisition.
- Last completed checkpoint: TASK-004.
- Branch: feature/ocr-comprehensive-benchmark, tracking origin.
- Previous checkpoints: 5da4946, 0db4fd4, f60742f. Initial push check for this session: everything up-to-date.
- TASK-004 checkpoint subject: `docs(benchmark): select English and Arabic evaluation datasets`. Resolve its hash using `git log -1 --format=%H -- benchmark_suite/PROGRESS.md` and verify the matching origin branch after final push. The task hash is not embedded in its own commit.

## TASK-004 files

Created:
- benchmark_suite/datasets/DATASET_SELECTION.md
- benchmark_suite/datasets/SOURCE_RESEARCH.json
- benchmark_suite/datasets/EXISTING_DATA_AUDIT.json

Modified:
- benchmark_suite/.gitignore (allow only these reviewed research artifacts while preserving ignored raw data)
- benchmark_suite/BENCHMARK_PLAN.md
- benchmark_suite/BENCHMARK_STATUS.json
- benchmark_suite/PROGRESS.md
- benchmark_suite/README.md

No production pipeline/configuration/tests, source PDFs, references, historical predictions/results or model packages changed. User-owned Task_codex.txt remains outside the commit. No dataset acquisition or TASK-005 implementation occurred.

## Dataset decisions

- Dataset A: English-only subset of opendatalab/OmniDocBench revision aa1ee96d106dbe53d0ae59474d75c6e6d9b53fec. 1,651 page images plus six card illustrations (exclude the latter); English count must be read from actual annotations after acquisition. Remote whole-repository bytes: 1,550,688,430. Supports text/layout/order/table references; no numeric-chart capability inferred. Dataset statement is noncommercial research-only despite Apache-2.0 evaluator code.
- Dataset B: Misraj/Misraj-DocOCR revision 7177bf70f77ce259890d6af0bef53f18faf26ec9. 400 image/Markdown pairs, 537,036,141 bytes in two original Parquet shards; repository total 537,043,557. Card declares Apache-2.0, authors describe expert-verified references. Supports Arabic text and validated table structure; no independent localized order or region geometry is advertised.
- References remain independent of candidate inference. Model-assisted source creation followed by expert verification or source-before-render synthetic truth requires validation; unreviewed model OCR is never ground truth.
- Supplements proposed: KITAB tables/charts/BCE layout (explicit dataset license missing; no acquisition permitted until resolved), PlotQA English chart values/geometry, HITL Arabic line/title/page regions, and DocLayNet layout. Full DocLayNet core 28 GiB exceeds the last measured free disk; never download it here without a separately feasible approved plan.
- KITAB is a multi-task collection, not 8,809 unique fully annotated Arabic pages; DocLayNet-derived rows are not automatically Arabic. Chart/table source code is data to inspect, not code to execute. Dataset gaps remain NOT_EVALUATED.

## Existing-data audit

- English: 32 PDFs / 68 pages, 32 references; 32 exact-case basename pairs.
- Arabic: 30 PDFs / 30 pages, 30 references; 30 exact-case pairs.
- Mix: 10 PDFs / 10 pages, 10 references; 9 exact-case pairs. PDF invoice_5 and reference Invoice_5 differ in case; Windows can hide this portability issue.
- 72 references are nonempty valid UTF-8; 72 PDFs contain 108 pages; combined PDFs/references are 10,693,007 bytes. No duplicate PDF byte-content groups observed. This does not establish human correctness, source rights or semantic pairing.
- Source/license/version/human-validation provenance remains unverified. Formatting markers do not establish valid table topology or bounding-box/order annotations. No existing content was renamed or repaired.

## Verification and results

Passed:
- Branch/prior checkpoint/status and push inspected before starting; real user approval recorded for TASK-004.
- Metadata revisions/access dates/source-response hashes, page/shard counts, license presence/absence and conservative transfer totals validated directly from publisher metadata.
- Source-research JSON preserves advertised LFS digests separately from local verification. Payload download date/checksum remain null; metadata only, no payload downloads.
- Native local PDF metadata counts, pairing differences, UTF-8 checks and existing-data preservation validated; no rendering, OCR or reference edits.
- All required selection sections, annotation/coverage gaps, bounded proposal and no placeholder text validated.
- Git ignore checks: the three reviewed research files are versionable; English image and Arabic Parquet payload paths stay ignored.
- git diff --check passed. Final status/schema, branch/base, exact stage scope and staged whitespace verified before commit/push.

Tests: no new unit tests or model/application inference tests were written/run for this documentation-only task. TASK-003's 71 suite tests and Ruff checks remain the last code-validation baseline; no suite runtime source changed in TASK-004.

Corrected research issue: the initial console diagnostic for two remote README metadata requests hit Windows cp1252 on emoji text. Repeated metadata-only requests without printing source text; final evidence contains successful source-response hashes, no unresolved source-request error records. No dataset file was fetched as a workaround.

Results generated: source-selection proposal and metadata/local audit only. No OCR metrics, model comparisons or acquired evaluation manifests.

## Current blockers and limits

- All eight local model readiness states remain BLOCKED with BLOCKED_BY_HARDWARE; Baidu remains BLOCKED pending exact implementation/API approval. The saved laptop profile has 0.61 GiB available RAM and a 2-GiB MX350 CC 6.1. Do not load a model or stop user processes automatically.
- Primary acquisition is not authorized by approval of dataset research. Await approval request A below. Actual data hashes, English language counts, source-document groups and row-level reference quality remain pending TASK-005.
- Public benchmark training contamination/source overlap is unknown. Freeze developer/evaluation groups before model outputs; do not infer independent documents from page counts.
- Arabic localized reading-order annotations and broad chart coverage remain gaps; proposed supplements are conditional and excluded from request A.

## Concrete next approval / TASK-005 scope

Request A: acquire only the two selected primary revisions for noncommercial research. Conservative full-repository total is 2,087,731,987 bytes (~2.09 GB decimal / 1.94 GiB). Proposed hard transfer limit: 2.2 GB decimal; minimum available workspace disk: 6 GiB (working-storage estimate). Verify current disk/RAM/terms/revisions before any transfer; stop if a budget or rights condition changes. Stream downloads; no full in-memory dataset materialization. Supplements, models, paid resources and heavy evaluator/system installs are excluded.

After approval:
1. Validate TASK-004 checkpoint and Git/remote state, source reports and exact permitted revisions/budget.
2. Complete TASK-005 only: implement bounded acquisition/validation and standard manifests per BENCHMARK_PLAN.md. No inference.
3. Obtain permitted original files, verify advertised plus locally calculated hashes and timestamps, preserve originals, validate independent references and coordinates/HTML, quarantine inconsistencies before models run.
4. Determine actual English pages, source groups and canonical IDs. Resolve Mix case alias explicitly in metadata; do not rename data. Freeze disjoint deterministic development/holdout groups and annotation-capability coverage. Do not invent absent group IDs or reference labels.
5. Validate manifest/schema/quality checks, update progress, make a task-only Git checkpoint and stop. If rights/resources prevent acquisition, accurately record BLOCKED rather than fabricating a complete manifest.

## Recommended next Codex prompt

“Read Task_codex.txt and benchmark_suite/BENCHMARK_PLAN.md, PROGRESS.md and BENCHMARK_STATUS.json. Validate TASK-004 and Git state. I approve TASK-005 and request A in datasets/DATASET_SELECTION.md: the two pinned primary sources only, for noncommercial research, with at most 2.2 GB decimal transfer and a 6-GiB free-disk reserve. Acquire and validate within those limits, build frozen manifests, update progress and commit/push the task, then stop. No supplements, model downloads, model inference, paid resources or major system installations.”
