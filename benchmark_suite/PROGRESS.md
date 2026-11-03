# Benchmark progress

Updated: 2026-11-03 (Africa/Cairo).

## TASK-016 Granite Docling bounded checkpoint - 2026-11-03

Pinned Granite Docling 258M files and CPU float32/SDPA processing are on D:.
The corrected two-page feasibility trial completed English and Arabic conversions
(peak sampled RSS 2.10 GiB), but the Arabic prediction recognized no text.
The attempted development runs encountered an import timeout, a transient Windows
bundle-publication error and a native Python access violation. The affected page
retried without periodic stack dumps did not crash, but repeated Arabic tatweel
and reached the soft generation bound: 5,121 tokens, 620.87 seconds, no closing
DocTags, zero completed documents in that retry.

TASK-016 is BLOCKED: ARABIC_GENERATION_LIMIT_AND_RUNTIME_INSTABILITY, not a proven
whole-machine RAM failure. No completed 20-page/full evaluation, accuracy scores,
rankings or selected run. See reports/GRANITE_DOCLING.md, GRANITE_DOCLING_RESULTS.json
and GRANITE_DOCLING_ASSETS.json. The bounded CPU adapter is registered; 210 suite
tests and Ruff pass. TASK-015 was pushed and remotely verified at 6b92577; its
full evaluation remains user-deferred. TASK-017 is unapproved. Earlier next-task
and resume statements below are historical.

## TASK-015 development checkpoint; full evaluation deferred by user

Docling 2.143.1 + Tesseract CLI 5.4.0 with verified eng/ara/OSD assets on D:
completed the frozen 20-page development run: 19 succeeded and one Arabic image
hit Docling's 180-second timeout. Normalized CER/WER: English 26.69%/40.09%
(10 scored pages); Arabic 50.26%/67.47% (9 scored pages). These are development
scores with different language reference scopes, not full-evaluation accuracy.
Run wall time was 662.99 seconds; peak sampled process/descendant RSS 2.08 GiB.

Run: results/docling_tesseract/20261103T095733Z-880fa5ba; offline evaluation and
all per-page/category/structure/performance CSVs are saved. Native outputs, report,
charts and a canonical evaluation copy are on D:. See reports/DOCLING_TESSERACT.md,
DOCLING_TESSERACT_RESULTS.json and DOCLING_TESSERACT_ASSETS.json. A preliminary
two-page trial exposed missing OSD data, which was supplied/hashed before this run.

The shared runner adapter uses a pinned external CPU worker with bounded memory,
per-language startup, native coordinate/order/table exports and production normalizer
reuse. Production code/dependencies are unchanged. Common trial code was factored
for explicit backend selection; original EasyOCR entry point remains available.
Owned process-tree cleanup handles Windows venv launchers and their descendants.
206 suite tests and Ruff pass; native copies/hash checks and registered preflight pass.

The user explicitly requested saving/pushing this result, deferring the full 1,135
images, and advancing to Granite Docling TASK-016. TASK-015 is BLOCKED with reason
FULL_EVALUATION_DEFERRED_BY_USER; no full-evaluation selected-run marker exists.
TASK-016 is approved; TASK-017 is not. Preserve the prior Tesseract partial run and
prior model attempts; original recorded code identity is required for resumption.

## TASK-014 Docling + EasyOCR actual attempt

The user approved the next model, explicitly requested trying it and recording
failure, requested D: storage, and authorized ending unrelated RAM-heavy apps.
Installed Docling 2.143.1 / EasyOCR 1.7.2 in an isolated D: environment using
independent copies of existing CPU Torch/Torchvision. Production packages are
unchanged. Five downloaded model files on D: total 628,166,987 bytes; hashes,
resolved dependencies, options, source identities and actual logs are retained.

The first worker was interrupted during a slow detector download. After the
detector was verified, initialization completed and CPU inference failed on the
first English development image with DefaultCPUAllocator unable to allocate
1,258,291,200 bytes under a 2.5-GiB job cap. Then Task Manager was opened and
15 background Edge/Bing Wallpaper processes were ended at the user's request.
The final retry copied and hashed the input on D: and put logs/outputs on D:.
It failed on the same allocation under the larger, availability-derived 2.99-GiB
cap. Sampled peak RSS was 2.49 GiB and private memory 2.66 GiB; system available
RAM never fell below 1.28 GiB in that retry. No claim of whole-machine RAM
exhaustion or universal model memory minimum is made.

Zero successful pages; two failed inference attempts on one unique English
image; Arabic not attempted. TASK-014 is BLOCKED_BY_HARDWARE for the tested
budget. No accuracy/full-evaluation/selected-run marker. See reports/DOCLING_EASYOCR.md
and DOCLING_EASYOCR_RESULTS.json. Final artifacts are in
D:/OCR_Benchmarking_Assets/docling_easyocr/trials/20261103T092226Z-b1c73300/.
All 204 suite tests, Ruff and isolated pip check pass; the job cap was verified
with a real rejected allocation in a disposable child process. Stop at this
checkpoint; TASK-015 is unapproved. Existing Tesseract partial results are intact.

## TASK-013 Tesseract verified; full evaluation incomplete

The user asked to move to a model that fits. Selected Tesseract, leaving
TASK-012 standard PaddleOCR pending. Registered native Tesseract 5.4.0,
pinned tessdata_fast English/Arabic (5.55 MB total), OEM 1 / PSM 3, one thread,
original frozen image pixels with a 300-DPI hint. The dedicated model virtual
environment leaves the production environment unchanged. All assets and native
executable/libraries are hashed; raw TSV/stderr and native line geometry survive.

Development run 20261102T113905Z-280b16d4 processed 20 pages without failures.
Full run 20261102T114008Z-48acf2b9 saved 437 of 1,135 pages (390 Arabic,
47 English), zero OCR failures. It is BLOCKED after available RAM repeatedly
fell below the unchanged 2-GiB safety floor. No final full-evaluation score,
completion or selected run is claimed. All published bundles/identities were
reverified. Sampled peak process/descendant RSS reached 694.4 MiB; no model OOM.
Existing approval persists for resuming after stable headroom is available.
All 203 suite tests pass (48.84 seconds); Ruff passed. CLI fixtures now reset temporary registrations
as well as approvals, so future real registrations do not affect authorization tests.
See reports/TESSERACT.md and configs/tesseract*. Do not start another model.

## TASK-011 Marker hardware checkpoint

User explicitly approved Marker. Fresh resources: 11.74 GiB usable RAM,
3.38 GiB available; MX350 2 GiB / CC 6.1. The generic floor passes but the
retained estimated 10-GiB process budget does not. Pinned Marker 2.0.0 still
requires Surya for scanned pages, even in CPU fast mode. Latest metadata is
2.1.0; no variant change occurred. Main-environment dependency conflicts and
isolated backend integration remain unresolved. See reports/MARKER_BLOCKED.md/json
and reports/hardware_observations/marker-task011-20261102/.

TASK-011 is BLOCKED_BY_HARDWARE, not completed. No model installation, weight
download, import or inference; no documents processed or scores measured.
Production dependencies and frozen data are unchanged. TASK-012 standard
PaddleOCR requires separate approval. This supersedes earlier next-task notes.

## TASK-010 PaddleOCR-VL hardware checkpoint

The user explicitly approved the next model. Fresh resources: 11.74 GiB usable,
3.14 GiB available, MX350 2 GiB VRAM / CC 6.1. Generic RAM floor passes;
the estimated 8-GiB CPU planning budget does not. Official GPU minimum is
CC 7.0. Verified paddleocr 3.7.0 and retained model revision through publisher
metadata only. See reports/PADDLE_VL_BLOCKED.md and fresh observations under
reports/hardware_observations/paddle-vl-task010-20261102/.

TASK-010 remains BLOCKED / BLOCKED_BY_HARDWARE, not completed. No installation,
weight download, framework import or inference occurred; no documents or scores.
Existing production environment and frozen data are unchanged. Next task is
TASK-011 Marker, requiring separate approval; last completed task is TASK-008.
This supersedes earlier next-action/approval statements in the history below.

## TASK-009 CPU setup preparation after another resource check

Prepared reports/SURYA_CPU_PLAN.md for review: retain Surya 2 / 0.22.1, propose
isolated Windows CPU llama.cpp, concurrency one, and future assets/caches on D:.
No executable adapter, environment, model directory or asset download was created.
Alternative execution environment approval remains required by Task_codex.txt.
Latest profile: reports/hardware_observations/surya-task009-20261102-recheck.
Available RAM was 1,111,896,064 bytes (1.04 GiB), still below the 2-GiB generic
floor. D: capacity does not remove this memory gate. CPU model-specific memory
fit is not measured. Hugging Face metadata request timed out; exact GGUF/projector
revision, sizes, precision and backend compatibility remain unresolved.
User asked whether moving the project would help; explained storage benefit only
and proposed D: for future large assets. No move was requested or performed.
No other model started. Next: free RAM, recheck, approve concrete CPU environment,
resolve pinned assets/dependencies and budget before downloading/loading.

## TASK-009 resource recheck after RAM upgrade — 2026-11-02

User requested removal of storage-inspection files and continuation of the approved
task. The cleanup command was rejected by automatic approval review with only
`blocked by policy`; the three files in logs/storage-inspection remain present.
No partition operations were attempted.

New exclusive collector evidence is preserved under
reports/hardware_observations/surya-task009-20261102/HARDWARE_PROFILE.json and .md.
Windows reports 12,606,803,968 bytes physical RAM (11.74 GiB), but only
1,023,102,976 bytes available (0.95 GiB), below the unchanged 2-GiB generic loading
floor. MX350 remains 2-GiB VRAM / compute capability 6.1. The previously documented
GPU-backend and unresolved CPU setup blockers have not been resolved by the upgrade.
D: is now NTFS, 999,284,535,296 bytes total / 999,146,557,440 bytes free at observation.
The repository and datasets remain on C:; nothing was moved.

Offline validation passed for all 1,155 frozen image/reference pairs. No package
installation, model download, inference or next-model execution occurred.
TASK-009 remains BLOCKED_BY_HARDWARE; last completed task remains TASK-008.
Next action: free RAM and recheck, then agree a compatible Surya CPU/backend plan
before loading. The generic floor alone does not certify Surya compatibility.
Other models still require separate approval. Historical observations below
describe the earlier 8-GB configuration and are retained as history.

## Checkpoint

- Completed: TASK-001 repository audit; TASK-002 architecture/tracking; TASK-003 hardware/model research; TASK-004 dataset selection; TASK-005 local acquisition and standardization; TASK-006 evaluation metrics; TASK-007 shared adapter/runner; TASK-008 Windows launcher/CLI.
- Current / first incomplete task: TASK-009 (Surya), BLOCKED_BY_HARDWARE after approved preflight. STOP; no next model approval.
- Last completed checkpoint: TASK-008.
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

All source/image identities and dimensions passed. Four English/Arabic image/reference examples were visually spot-checked (English scanned chart/text and scientific table; Arabic mixed-language tables and diacritized poetry/prose). Visible pairings/selected values correspond, but this is not a complete character-level human audit. Source scope, watermark/ghost text, mathematical notation and Arabic tatweel/diacritic conventions are covered by the explicit TASK-006 metric policies. No OCR-generated ground truth or missing annotation was invented.

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

## TASK-006 completed checkpoint

User explicitly approved continuation on 2026-11-01. Implemented only TASK-006;
no models/dependencies were installed, no inference, dataset downloads or OCR API calls performed.
TASK-005 remote commit 254f06ee1f753d8de4783142538a20f5b5647cf6 was verified;
all 1,155 frozen image/reference pairs passed offline validation before work.

Created metrics/__init__.py, text.py, layout.py, reading_order.py, tables.py,
charts.py, statistics.py and references.py; configs/evaluation.json;
requirements-metrics.txt; tests/test_metrics.py; scripts/audit_metric_references.py;
reports/METRICS.md and reports/METRIC_REFERENCE_AUDIT.json. Modified this file,
BENCHMARK_PLAN.md, BENCHMARK_STATUS.json and suite README.md. Production and
historical evaluator code, frozen manifests, images and references are unchanged.

Implemented explicit raw/normalized code-point CER, whitespace-token WER, clipped
error-complement accuracies, NED, exact and bag-unit PR/F1; configurable Arabic
Unicode/marks/alef/hamza/tatweel/whitespace policies; class/page-aware box IoU,
confidence-greedy detection and all-points mAP; independent-ID order/tau/inversions
with missing-pair coverage; genuine bounded ordered-tree TEDS variant plus
span-aware cell/merge/header/text/row/column diagnostics; independently gated chart
detection/type/text/numeric/component calculators; micro/macro distributions and
seeded cluster bootstrap. See METRICS.md for precise formulas and null behavior.

English explicit text truth is regional, so full-page CER against a partial
transcript is prohibited. Raw Markdown serialization and converted content must
remain separate; literal math notation is representation-sensitive. CommonMark
conversion must only run on declared Markdown, not arbitrary plain text. Dataset
layout masks/unknown labels require explicit scoped routing in TASK-007. Chart
numeric/type truth and Arabic reading order remain NOT_EVALUATED. No source-book
independence is claimed: primary intervals must be explicitly page bootstrap.

TEDS is the named ordered-tree-teds-root-th-v1 variant, not official PubTabNet
numeric parity. Default 150 nodes / 200,000 states; limits return NOT_EVALUATED.
Reference-only audit: 243 English and 73 Arabic HTML fragments across both splits;
257 ready before state limits, 47 over node limit, three stricter grid/parser
invalid, nine blocked by the existing manifest table gate. IDs/reasons recorded
separately without mutating the frozen cohort. All 753 layout-eligible and 740
order-eligible English pages convert successfully. 11,373 explicit English text
regions are retained. Readiness is not a model result or guarantee of state budget.

Verification: 32 metric tests including an independent exhaustive tiny-tree edit
oracle; 122 total suite tests pass. Ruff passes; frozen-data validation passes;
reference audit reproduced deterministically. Empty-reference hallucinations
contribute to micro errors even though their individual CER/WER is undefined.
No unresolved test failures. Production integration tests are unchanged/unrun.

Final task commit subject: `feat(benchmark): implement annotation-aware evaluation metrics`.
Resolve it using Git log; verify the origin branch after push. No hash is embedded
in its own commit. Downloaded data and transcriptions remain local/ignored.
Task_codex.txt remains user-owned and untracked.

## TASK-007 completed checkpoint

User approved continuation on 2026-11-01 and explicitly required separate approval
for each model. Implemented the shared runner only. No real OCR factory was
registered, no model installed/downloaded/executed, no package installation or
paid/cloud/API execution. All existing model hardware/ambiguity blockers remain.
TASK-006 checkpoint a5a0eaf is the base; final remote verification is recorded by
Git. The user-owned untracked Task_codex.txt remains outside the commit.

Created:
- adapters/__init__.py, adapters/base.py and adapters/existing.py.
- runners/__init__.py, schemas.py, preflight.py, cache.py, run.py, evaluate.py,
  report.py.
- requirements-runner.txt, tests/test_runner.py and reports/RUNNER.md.

Modified configs/evaluation.json with explicit routing thresholds; updated suite
README, plan, architecture, this progress and validated status. Production source,
historical evaluators/results, frozen data/manifests/references are unchanged.

The benchmark envelope reuses production OCRResult, preserving raw bytes plus
optional typed tables/charts and explicit format/coordinates. The lazy existing
provider bridge captures provider OCRResult as its declared raw boundary, not
vendor internals. No built-in real model factory exists yet.

One candidate per invocation; every real model requires its corresponding task
explicitly approved/current/IN_PROGRESS and all shared prerequisites complete.
Preflight precedes factory construction and checks declared compatibility,
RAM/VRAM/compute capability, disk reserve, installed dependency versions, static
GPU build evidence and assets/source hashes. Model-specific binary/runtime
compatibility evidence remains required. Only synthetic fixture IDs can use test
probes. The runner does not grant approvals or update model states automatically.

Immutable unique runs, per-document raw/normalized checksummed bundles, atomic
progress, successful-only cache and kernel coordinator lock support resumption.
A real fixture process was terminated after cache publication; its next run
reused that saved output and completed the remaining documents without repeating
it. In-flight work without durable output can repeat. Completed runs are immutable;
failed pages can be retried in a new run while successes are reused. Corrupt or
changed artifacts/configs block. Errors and cleanup diagnostics are preserved.

Timing distinguishes initialization, prepare/predict/normalize and cold/warm
attempts, sampled own-process/descendant RSS and optional sampled GPU context
memory. WDDM N/A remains null. Cache hits retain original provenance but have null
fresh timing/resource exports. Hardware, device, precision, batch, DPI and resize
settings are retained; session wall time and missing session ends are disclosed.

Offline reevaluation works without an adapter/model/cache and creates a new sibling
evaluation with policy/code/data/run identity. Exports include full per-page/doc
metrics, language/category text aggregates, explicit page-bootstrap intervals,
structured metric CSVs, performance, failures, errors, predictions and a basic
individual report. Scope/coverage remain explicit: English uses independent region
geometry allocation, source masks are honored, confidence-less AP is withheld,
Arabic multiple-table pairing without truth alignment is unscored, and unavailable
chart/order annotations remain NOT_EVALUATED. No fixture score is a real model result.

Verification: 33 runner tests / 155 suite tests pass; Ruff and whitespace checks
pass. Tests cover approval gates for all nine candidates, real fixture process
termination/OS-lock recovery, repeated/cached/offline execution, raw preservation,
meaningful identity invalidation, failed initialization/pages/cleanup,
source/reference/cache/output tampering, input mutation during predict,
RAM/disk/package/asset/CUDA-build gates, coordinates/label masks, plain-vs-Markdown
routing, word-to-region allocation and Arabic table ambiguity. No production
pipeline source was changed. Read reports/RUNNER.md for exact contracts/limitations.

Final commit subject: `feat(benchmark): add gated single-model runner and recovery`.
Resolve the hash using Git log and compare with origin after push. No hash is
embedded in its own commit.

## TASK-008 completed checkpoint

The user approved TASK-008 on 2026-11-01. The earlier instruction to wait for
separate approval for each model remains in force. TASK-007 commit 0ae51d7 was
verified against origin before work. Implemented shared Windows menu/CLI only;
no model factory, isolated model environment, installation action, weight download
or inference was added or executed. No cloud/API calls or dependency installations.

Created cli.py, scripts/run_benchmark.bat, configs/models.json, tests/test_cli.py
and reports/CLI_VALIDATION.md. Updated README.md with the complete command/menu
mapping, environment selection, current pending setup behavior, single-model
approval requirements, quick/full/resume/offline semantics, logs and exit codes.
Also updated plan/status/architecture/this progress and .gitattributes for batch
CRLF checkout. preflight.authorize_model is now shared by CLI and runner. The
runner's existing approval test now uses a fixed temporary pre-model checkpoint,
so later real approvals cannot accidentally authorize a negative test.

The exact 13-option menu forwards to the same CLI functions. It selects only one
model and en/ar/both, quick/full, explicit resume/evaluation run paths. No all-model,
repeated-model, --yes or public fixture bypass exists. Help works without site
packages; required commands validate tested direct dependency pins. The launcher
selects an explicitly specified existing interpreter or detects existing shared
Python; it never installs packages. Registered model environments must be isolated
under environments/<model>, explicitly selected and pinned. Null model registrations
remain PENDING until their independently approved tasks implement them. Setup is
an audit of an approved existing setup, not an installation path at this checkpoint.

Actual checks: Windows launcher --help and default menu/exit work. Real cmd.exe
fixture paths with spaces and ampersands preserve arguments and exit codes 0/7.
check-environment metadata/native probes pass shared dependencies but show only
827,138,048 bytes (~0.77 GiB) free of 8,311,836,672 physical bytes, below the 2-GiB
loading policy floor; MX350 still has 2,048 MiB VRAM/CC 6.1 and Torch/Paddle GPU
support is unavailable in the inspected interpreter. Snapshot values are not a
promise of later availability. Hardware blockers were not cleared or relaxed.
validate-datasets rehashed all 1,155 original frozen source/reference pairs with
no network/inference. No data, references, historical results or production
pipeline source changed. Logs are local/ignored under logs/cli.

Verification: 43 CLI tests / 198 full suite tests pass; Ruff and whitespace pass.
Tests cover blocked setup/smoke/run for all nine candidates without factory imports,
exact menu/selection/cancel behavior, dependency failures/help without site packages,
single-model/language/split dispatch through fake shared boundaries, original config
on resume, completed-run immutability, offline report routing without active model,
path ownership, pinned environment checks, pending comparison commands, nonzero
failed-document exit codes and saved-run reporting after evaluation failure.
No fixture output was treated as real benchmark evidence.

Final commit subject: `feat(benchmark): add Windows menu and single-model CLI`.
Resolve it with Git log and compare origin after push. User-owned Task_codex.txt
remains untracked; generated logs/data/cache/results are excluded from Git.

## TASK-009 Surya blocked checkpoint

User explicitly approved Surya only on 2026-11-01. TASK-008 remote commit f0fca6c
was verified before work. TASK-009 is BLOCKED with reason BLOCKED_BY_HARDWARE;
last completed task remains TASK-008. This is not a completed benchmark or an
inference failure. All other model approvals remain absent.

Created reports/SURYA_BLOCKED.md and reports/SURYA_BLOCKED.json. Updated the
Surya-only recheck metadata in MODEL_REGISTRY.yaml, plan, README, this progress
and status. All executable factory/environment catalog fields remain null; no
placeholder adapter or runnable config was created. Production code, datasets,
reference/manifests, historical results and dependencies remain unchanged.

An exclusive fresh collector profile under ignored
reports/hardware_observations/surya-task009-20261101 records:
- i7-1165G7, 4 cores/8 threads, Windows 11 Pro 26200, Python 3.13.7.
- 7.74 GiB physical / 0.69 GiB available RAM (737,169,408 bytes); below 2-GiB
  conservative loading floor. The retained 8+ GiB process planning budget is an
  estimate, not a vendor minimum; closing apps to reach the generic floor does
  not certify this Surya configuration.
- MX350, 2 GiB VRAM, CC 6.1; current official vLLM requires >=7.5 and Linux.
  Driver/WSL changes cannot upgrade GPU architecture. Torch metadata is CPU-only.
- 34.33 GiB free disk; llama-server absent from PATH; Surya not installed.
  Both WSL distributions were stopped and were not started by this task.

Metadata-only official checks retain surya-ocr 0.22.1 / Surya 2, source commit
3a70081f6a60013dab818c82ab99451aa290f389 and model revision
3b3d4cdf88d6928b0acdc75181b13206ea67c4a3. The 1,372,368,672-byte safetensors metadata
checksum matches the earlier research. No weight download occurred. PyPI now
reports 0.23.0 and current upstream docs describe Surya 2.5; this variant was not
silently adopted. Code Apache-2.0 and modified weight OpenRAIL-M terms remain
separate; full weight terms must be reviewed before future download/use.

Pinned dependency conflicts include Transformers >=5.12.1 vs installed 4.57.6,
Pillow <11 vs 12.3.0, huggingface-hub >=1.5 vs 0.36.2. No main-environment changes
were made. A compatible isolated environment and verified backend/CPU asset set
remain unresolved, alongside the hardware blocker. Native Windows CPU integration
is not tested. Quantization, different model/version or another environment needs
a reviewed explicit plan/approval; no paid/free cloud host was provisioned.

Unique ignored local evidence at results/surya/preflight/20261101T123759Z-9f2b62ae
contains preflight.json, environment.json, source_metadata.json, metrics.json with
null/NOT_EVALUATED scores and MODEL_REPORT.md. This is not a prediction run and
has no completion/selected-run marker. Zero documents were processed; no failed
inference documents, invented latency/accuracy/peak model memory or fake outputs.
Versioned blocker evidence records source URLs and local evidence/data SHA256s.

Verification: existing 198 suite tests and Ruff pass, plus validated status,
whitespace and report/evidence consistency. No new algorithm/adapter was added,
so no model-inference tests were attempted. No unresolved check failures; the
hardware/environment/version decisions are the explicit remaining blockers.

Final blocker commit subject: `docs(benchmark): record Surya hardware-blocked preflight`.
Resolve via Git and verify origin after push. Raw observations/results remain
local/ignored; Task_codex.txt remains user-owned and untracked.

## Remaining tasks and exact next actions

STOP at the Surya blocker checkpoint. Surya TASK-009 approval is already recorded;
do not ask for the same approval again merely to inspect/recheck it. Loading still
requires sufficient measured resources plus an agreed compatible pinned setup.
Revisit on a more capable available machine or propose a separately reviewed
CPU/quantized configuration without claiming it fits this laptop. Existing RAM
upgradeability is unknown. Paid/cloud resources and environment/variant changes
require their own specified approval. Do not close the user's apps automatically.

Do not advance to TASK-010 (PaddleOCR-VL), or reorder to Tesseract/another model,
without that model's explicit user approval. Other tasks remain pending. Models
blocked by hardware stay in the plan for later evaluation; no zero-filled ranks.

## Recommended resume prompt

“Read Task_codex.txt, benchmark_suite/BENCHMARK_PLAN.md, PROGRESS.md,
BENCHMARK_STATUS.json and reports/SURYA_BLOCKED.md/json. TASK-009 Surya is already
approved but hardware-blocked. Inspect the saved checkpoint and recheck resources
before proposing any loading; preserve the retained 0.22.1 / Surya 2 candidate
unless I explicitly approve a different version/variant/environment. If still
blocked, stop. Do not start another model without my separate approval.”

## Final requested Surya retry — 2026-11-02

Fresh profile reports 12,606,803,968 bytes usable RAM and 3,392,053,248 bytes
available (3.16 GiB): the generic 2-GiB loading gate now passes. This does not
certify Surya memory fit. The explicit Surya smoke command exited 1 before
inference because the checkpoint is BLOCKED and the adapter and pinned isolated
environment remain unimplemented. The CPU llama.cpp plan remains a proposal.
No installation, download, model initialization, inference or next-model work
occurred. TASK-009 remains blocked; historical blocker reports are retained as
dated observations. Evidence: reports/hardware_observations/
surya-task009-20261102-final-retry/{HARDWARE_PROFILE.json,RETRY_RESULT.json};
CLI log logs/cli/20261102T112754Z-659d907d.json.
