# Benchmark progress

Updated: 2026-10-28 (Africa/Cairo).

## Checkpoint

- Completed: TASK-001 repository audit; TASK-002 architecture/tracking; TASK-003 hardware/model research; TASK-004 dataset selection; TASK-005 local acquisition and standardization.
- Current / first incomplete task: TASK-006, PENDING. Stop at the TASK-005 checkpoint before beginning metrics implementation.
- Last completed checkpoint: TASK-005.
- Branch: feature/ocr-comprehensive-benchmark, tracking origin.
- Previous checkpoints: 5da4946, 0db4fd4, f60742f, d9c8a15. Storage-preference note d53cb9f is superseded by the latest explicit user instruction to download locally and continue.
- TASK-005 implementation commit: 70125ea. Final checkpoint subject: `fix(benchmark): preserve frozen manifest checksums on Windows`. Resolve with `git log -1 --format=%H --grep="fix(benchmark): preserve frozen manifest checksums on Windows"` and verify the remote ref after final push. A commit hash is not embedded in its own commit.

## TASK-005 files created

- benchmark_suite/dataset_io.py
- benchmark_suite/dataset_preparation.py
- benchmark_suite/scripts/prepare_datasets.py
- benchmark_suite/tests/test_datasets.py
- benchmark_suite/requirements-datasets.txt
- benchmark_suite/datasets/README.md
- benchmark_suite/datasets/manifest/schema.json
- benchmark_suite/datasets/manifest/development.jsonl
- benchmark_suite/datasets/manifest/evaluation.jsonl
- benchmark_suite/datasets/manifest/PROVENANCE.json
- benchmark_suite/datasets/manifest/ACQUISITION_PROVENANCE.json
- benchmark_suite/datasets/manifest/LEGACY_ALIASES.json
- benchmark_suite/reports/DATASET_VALIDATION.md

Also created benchmark_suite/.gitattributes to preserve LF bytes for frozen JSON/JSONL on Windows checkout.

Modified: BENCHMARK_PLAN.md, BENCHMARK_STATUS.json, PROGRESS.md, suite README.md and datasets/DATASET_SELECTION.md. Downloaded source files, extracted images/transcriptions/references, catalog/allowlist/journal/logs are under ignored suite datasets/raw, datasets/english and datasets/arabic. They must not be committed. The manifest JSONL is metadata and hashes, not ground-truth text/image payloads.

Production files, existing curated datasets/references, historical outputs/results and model environments remain unchanged. Task_codex.txt remains a user-owned untracked input outside the task checkpoint.

## Acquisition and quantitative inventory

- User approved local download, overriding the Drive preference; no Drive upload or cloud worker was used. Existing direct dataset dependencies were available; no packages were installed.
- Original source revisions unchanged: OmniDocBench aa1ee96d106dbe53d0ae59474d75c6e6d9b53fec; Misraj-DocOCR 7177bf70f77ce259890d6af0bef53f18faf26ec9.
- 760 originals verified: 755 English images, two Arabic Parquet shards, the full English annotation JSON and two source READMEs.
- Verified source bytes: 1,397,890,070. Conservatively charged transfer including metadata/reservations: 1,398,615,726, below the approved 2,200,000,000-byte limit.
- Local raw + extracted data/reference + manifest metadata was approximately 2.03 GB decimal at validation. Free disk: 23.04 GiB at observation; no user data was deleted. Early downloaded copies were retained while canonical short storage paths were created.
- Publisher English annotation language counts: 755 English, 765 simplified Chinese, 116 mixed, 13 traditional Chinese, two other. Only English images were selected; six documentation illustrations are excluded.
- 1,155 frozen image/reference records: English 755, Arabic 400. Development 10 per language; official evaluation 745 English + 390 Arabic.
- 1,155 unique exact-content groups; no exact-image or reference-hash overlap across splits. Source-document/book identity remains unknown, so this is page/content-disjoint, not certified source-book-independent.
- Eligibility across the combined development/evaluation corpus: explicit text 750 English/400 Arabic; valid region geometry 753 English/0 Arabic; usable ordered regions 740 English/0 Arabic; explicit HTML nesting/span eligibility 146 English/56 Arabic. These are reference counts, not model results. Five English pages lack explicit text references and must not receive fabricated CER/WER.
- Source categories are retained for English; Arabic category remains null because it is not supplied. Chart numeric/type annotations remain unavailable. A benchmark image can contain a facing-page spread; page_count=1 is the image unit, not the original PDF-page count.

## Reference quality, preservation and limitations

Two English pages contain out-of-bounds source polygons; one English and two Arabic pages contain malformed table markup. Original annotations/references were preserved unchanged and affected metric eligibility restricted, not silently repaired or dropped. Every page remains in the image cohort for other available capabilities. Full source IDs/warnings are in reports/DATASET_VALIDATION.md and manifest JSONL.

All source/image identities and dimensions passed. Four English/Arabic image/reference examples were visually spot-checked (English scanned chart/text and scientific table; Arabic mixed-language tables and diacritized poetry/prose). Visible pairings/selected values correspond, but this is not a complete character-level human audit. Source scope, watermark/ghost text, mathematical notation and Arabic tatweel/diacritic conventions need explicit TASK-006 policies. No OCR-generated ground truth or missing annotation was invented.

Full source checksums, download dates, notices and URLs are recorded locally in raw/acquisition.json; main archives/annotation and manifest hashes are versioned in provenance. ACQUISITION_PROVENANCE.json is the earlier download-only marker; final frozen PROVENANCE.json is authoritative for preparation completion. No signed CDN URLs or credentials are saved.

Original Mix invoice_5 versus Invoice_5 paths are explicitly mapped in LEGACY_ALIASES.json without renaming. Legacy samples remain excluded from the official cohort until their own provenance/rights/reference verification is resolved.

Public benchmark training exposure, perceptual near duplicates and true source-document grouping remain unknown. Do not claim document-independent confidence intervals from page-disjoint splits. HTML checks verify explicit syntax/spans, not every semantic/table-topology detail or a TEDS score. Publisher expert review is evidence, not our certification of every transcription. See reports/DATASET_VALIDATION.md for the measured inventory and limitations.

## Verification

Passed:
- `.venv-ocr\Scripts\python.exe -m pytest benchmark_suite/tests -q`: **90 passed** (54 tracking, 17 hardware, 19 dataset tests).
- `.venv-ocr\Scripts\python.exe -m ruff check benchmark_suite`: passed.
- `prepare_datasets.py --download`: completed pinned allowlist within budget, with verified originals, resumable partials and no model/alternate dataset fallback.
- `prepare_datasets.py --build`: published all 1,155 validated image/reference records and immutable split/schema/provenance files.
- `prepare_datasets.py --validate-only`: offline artifact/schema/identity/hash/count/split validation passed for all 1,155 records plus source archives/annotations.
- `prepare_datasets.py --verify-downloads`: independently rehashed all 760 originals after canonicalization; no network or decoding.
- Recovery/integrity tests cover partial ranges, ignored ranges, bad checksums, hard budget, interrupted publication, Windows sharing locks, long Unicode paths, path escape, canonical storage normalization, immutable outputs, deterministic groups and payload tampering.
- No application/inference tests executed because production code and model integrations were unchanged. No OCR scores or model reports generated.
- Manifest idempotence, source-payload ignore policy, exact stage scope, status validation and whitespace passed.
- A real `git -c core.autocrlf=true checkout-index` into ignored local scratch storage preserved every frozen manifest/schema/alias checksum after adding manifest-specific text eol=lf rules. This closes a fresh-Windows-checkout reproducibility risk. No runtime source changed after the 90 passing tests.

## Interruptions and resolution

- Windows long source filenames exceeded native path limits: use stable short object names with original filenames/revisions recorded in metadata. Preserve early copies and normalize before freeze so fresh acquisitions use identical canonical paths.
- Console diagnostics encountered Windows cp1252 Unicode issues: source files remain UTF-8 and download display names use safe escaping; later inspection uses explicit UTF-8.
- A transient Windows sharing lock interrupted atomic journal replacement: bounded retries preserve atomicity and the old journal; verified files were reused and reads remained budgeted.
- A decoding preflight refused insufficient RAM. The user explicitly freed RAM/requested retry; the preparation floor was retained and the next run completed. No user processes were stopped and no model hardware guard was relaxed.
- No unresolved unit-test/lint failures or missing dataset payloads. Source-reference warnings/coverage limitations remain explicit; no source bytes were altered to conceal them.

## Remaining tasks and exact next actions

All local model states stay BLOCKED with reason BLOCKED_BY_HARDWARE; Baidu stays BLOCKED pending implementation/API approval. Successful dataset preparation does not certify model memory/GPU compatibility or authorize inference.

After approving TASK-006:
1. Read Task_codex.txt, BENCHMARK_PLAN.md, this file and BENCHMARK_STATUS.json; validate the TASK-005 Git/remote checkpoint, provenance and frozen source/reference hashes.
2. Implement TASK-006 only: metric calculators with fixed, versioned text-content assembly, raw/normalized Arabic transformations, CER/WER/accuracy/NED/exact match and clear matching units/empty-reference behavior.
3. Add real structural metrics only when manifest capabilities and independent annotations permit them: layout IoU/matching/mAP, order inversions/tau, genuine TEDS/cell metrics and separately chart metrics on future valid references. No numeric chart scores exist for this primary cohort.
4. Preserve source inputs, historical policies and cached predictions; do not change frozen pages after model outputs. Treat warnings/missing labels explicitly. Statistical aggregation must disclose unknown document grouping and coverage, not silently assume independent books.
5. Run meaningful hand-checked unit/edge-case tests, document formulas/configurations, update progress and commit/push the task. Stop at the TASK-006 checkpoint; no model or extra dataset download or inference.

## Recommended next Codex prompt

“Read Task_codex.txt and benchmark_suite/BENCHMARK_PLAN.md, PROGRESS.md and BENCHMARK_STATUS.json. Validate the TASK-005 checkpoint and frozen dataset provenance. I approve TASK-006 only. Implement and test the annotation-supported metrics and explicit Arabic/text policies, preserve raw references and historical behavior, update progress and commit/push, then stop. Do not download or execute models.”
