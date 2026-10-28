# Benchmark architecture

TASK-002 checkpoint, 2026-10-28 (Africa/Cairo). The tracker is implemented;
inference, metrics, datasets and reports below describe the planned contracts.

## Boundaries and reuse

The suite runs from the repository root as `python -m benchmark_suite.<module>`.
It is deliberately separate from the production API and frontend. Current
setuptools discovery does not package this directory; no packaging or production
changes are needed for the source-tree entry point. TASK-008 must document or
review distribution support before claiming installed-package CLI support.

| Component | Responsibility | Existing code to assess/reuse |
|---|---|---|
| tracking.py (implemented) | Validate and atomically persist coordinator state | Standard library; no OCR imports |
| adapters/ (TASK-007 and model tasks) | Explicit model lifecycle, capabilities, raw output and normalization | OCR.providers.base, existing Tesseract/Docling-Tesseract/Paddle-VL providers |
| runners/ (TASK-007) | Hardware/storage preflight, one-model jobs, manifests, timing, recovery and cache policy | OCR.service, OCR.result_cache, OCR.resources, OCR.logging_utils |
| datasets/manifest/ (TASK-005) | Versioned document identities, verified reference pairings, annotations and frozen splits | Existing benchmarks/datasets reviewed for provenance first |
| metrics/ (TASK-006) | Pure prediction/reference scoring, configurable policies and statistics | OCR.evaluation primitives after verification; preserve historical evaluators |
| scripts/ and CLI (TASK-008) | Windows menu and equivalent single-model commands | Existing native checks reviewed; never call provisioning implicitly |
| reports/ (TASK-003 onward) | Hardware, capabilities, methodology and measured conclusions | Existing docs as context, with current code/source evidence |

`OCR.schemas.OCRResult` schema 1.0 is the normalized document boundary. A
benchmark envelope will preserve the unmodified raw result, typed table/chart
structures where supplied, capability statuses, model/configuration revisions,
and file hashes. Unsupported fields remain absent/null with explicit evaluation
status. Do not infer structure or references from generated OCR. Coordinate
systems and any transforms must be recorded. `docling` currently means
Docling with Tesseract; EasyOCR and Granite are separate candidate configurations.
Qwen/Ollama is outside the requested nine. Baidu remains unresolved.

## Planned run flow

1. Read and validate the last checkpoint, Git state, approval and dependencies.
2. Select exactly one model and frozen document manifest.
3. Validate official model configuration, environment, RAM/VRAM/storage and
   native tools before installing or loading it. TASK-003 must be complete;
   UNKNOWN compatibility cannot authorize execution. Alternative environments,
   paid resources and large/restricted downloads require the specified approval.
4. Create an exclusive unique run directory. Record source/model/configuration,
   dataset hashes, dependency versions, hardware, precision, DPI, image size,
   batch size and local/cloud location before inference.
5. Reuse only validated successful cache entries matching document bytes,
   model/adapter versions, configuration, assets and relevant preprocessing.
   A cache hit is not a new latency measurement. Initialization, cold/warm
   inference, preprocessing and postprocessing timings remain distinguishable.
6. Persist raw and normalized outputs/errors per document before marking it
   finished. Resume incomplete records without repeating completed combinations.
7. Evaluate stored predictions against independent references. Metric reruns
   never require OCR. Missing annotations yield NOT_EVALUATED; unsupported model
   capabilities yield NOT_SUPPORTED, with no fabricated zero scores.
8. Generate an individual report, update progress and create the task checkpoint.
   Stop before advancing to another model.

Hardware preflight and immutable run/cache behavior are TASK-007 work. The
TASK-002 tracker alone does not certify resources or implement inference safety.

## Immutable run layout (planned)

```text
results/<model>/<UTC timestamp>-<random ID>/
    run_manifest.json          # source/config/dataset identity and completion
    config.yaml
    environment.json
    predictions.jsonl
    raw_outputs/
    normalized_outputs/
    metrics.json, metrics.csv
    per_document_metrics.csv, per_page_metrics.csv
    english_results.csv, arabic_results.csv
    layout_metrics.csv, table_metrics.csv, chart_metrics.csv
    reading_order_metrics.csv, performance_metrics.csv
    failures.csv, errors.log
    visualizations/
    MODEL_REPORT.md
results/<model>/selected_run.json
results/comparisons/model_comparison.csv, model_comparison.json
```

Run creation must fail if a directory exists. Completed runs are immutable;
resuming changes only an unfinished run. Reevaluation writes a new evaluation
artifact identified by evaluator/normalization/reference hashes. The separately
updated selected-run pointer identifies the official audited run without
overwriting its predecessors. Comparisons consume saved selected runs, disclose
coverage and qualify speed/resource comparisons across different hardware.

## Checkpoint schema and transitions (implemented)

`BENCHMARK_STATUS.json` schema v1 requires exactly the documented fields already
present in the file. IDs cover TASK-001 through TASK-021 and the nine requested
models. Unknown/missing IDs, malformed types, duplicate JSON keys, NaN and
unsupported states are rejected. Date is YYYY-MM-DD; timezone uses an IANA name.
The latest completed task ID must agree with `last_completed_checkpoint`.
One task and one model may be IN_PROGRESS at a time. An active task must match
`current_task`; active/completed tasks require recorded approval. Approval
records describe actual user instructions; software must never manufacture
authorization. Hardware assessment completion is necessary before active or
completed model records; each active/completed model must also match its approved
evaluation task state. Actual environment safety belongs to the runner.

| From | Allowed different states |
|---|---|
| PENDING | IN_PROGRESS, BLOCKED, SKIPPED |
| IN_PROGRESS | COMPLETED, BLOCKED, FAILED |
| BLOCKED | IN_PROGRESS, SKIPPED |
| FAILED | IN_PROGRESS, SKIPPED |
| COMPLETED | None |
| SKIPPED | None |

Same-state metadata updates are allowed. Completed/skipped work cannot regress.
Retry blocked/failed work through IN_PROGRESS. For hardware blocks, use
`models.<id> = BLOCKED` and `model_block_reasons.<id> = BLOCKED_BY_HARDWARE`.
Every blocked model needs a nonempty reason, and reasons cannot persist after
the model leaves BLOCKED. Task blockers are explained in next_action, verification
and PROGRESS.md. Verification uses the same state enum (COMPLETED means checks
passed); TASK-001's older PASSED label was migrated during TASK-002. Verification
metadata is extensible finite JSON, while top-level schema changes require an
explicit migration. Branch/base identity and recorded approvals cannot be
silently erased on updates, and dates cannot go backwards.

`load_status(path)` reads explicit UTF-8 and validates. `save_status(path, state)`
validates proposed data and existing state transitions before touching disk,
serializes to a uniquely named temporary file in the destination directory,
flushes and fsyncs it, closes it, then calls os.replace. The parent must exist.
Catchable I/O errors remove only that writer's temporary file. A missing
checkpoint raises FileNotFoundError on read; a corrupt one is never replaced
by a default. First-time creation requires a complete valid supplied state.

There is one human/agent coordinator writer. Callers serialize updates; atomic
replacement is not multi-writer conflict detection. Readers see complete old or
new JSON on supported local filesystems. File fsync does not guarantee directory
entry durability after power loss on all filesystems. A hard process kill can
leave a `.BENCHMARK_STATUS.json.<random>.tmp` orphan. Readers ignore it; inspect
it only after confirming its writer is dead, and validate any recovered state
against the last checkpoint before an explicit recovery. Do not automatically
delete or promote orphan files.

PROGRESS.md and BENCHMARK_PLAN.md are human-readable companions, not part of a
multi-file transaction. Record IN_PROGRESS early, persist outputs and checks,
update the companion documents, then publish final validated JSON and commit
the task-owned paths. After interruption, inspect artifacts and Git history to
resolve any disagreement; a COMPLETED label alone is not sufficient evidence.

## Artifact policy (implemented)

The suite's .gitignore excludes downloaded dataset content, model weights,
environments, secrets, caches, logs, temporary checkpoints and generated runs.
Reviewed dataset manifests/source/license notes, source code, configuration
examples and Markdown reports remain versionable. Do not put source code or
ground-truth payloads into the manifest directory as an ignore workaround.
Large or private artifacts remain local/external with checksum and retrieval
metadata in reviewed manifests. Reports need review for sensitive excerpts.
Ignored files already tracked elsewhere remain tracked; nothing is deleted by
this policy. Never force-add ignored assets or stage the entire repository.

## Validation boundary

Tests use temporary files, process-exit/I/O failure injection and Git ignore
queries. They need no OCR services or model downloads. Repository pytest.ini now
includes benchmark_suite/tests in default discovery alongside the existing
tests/. TASK-020 will validate integration and reproducibility of real runs.
