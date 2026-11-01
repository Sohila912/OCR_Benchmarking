# Shared adapter and runner: TASK-007

Implemented 2026-11-01 (Africa/Cairo). This checkpoint implements shared execution
and evaluation infrastructure. **No real OCR model factory is registered, installed
or executed. Every individual model requires its own explicit user approval.**
Synthetic test fixtures are software checks, never OCR benchmarking evidence.

## Contracts and reuse

`adapters/base.py` defines initialize, prepare, predict, normalize_output,
get_capabilities, get_metadata and cleanup. Constructors and metadata calls must
not load models. Initialization uses existing assets only, with no download,
installation or engine/environment substitution. Individual model tasks must
review that contract and supply the exact verified factory/spec.

`runners/schemas.py` wraps production `OCR.schemas.OCRResult` without changing it.
It preserves page text/Markdown, original blocks, boxes, order, warnings/errors,
provider metadata and optional independently supplied table/chart structures.
`RawOutput` contains original bytes and media type; those bytes are retained even
when normalization subsequently fails. Unsupported fields remain null. The raw
boundary is explicit in `AdapterSpec.raw_level`.

`adapters/existing.py` is a lazy compatibility bridge around the existing
`OCRProvider` initialize/extract/unload contract. Its raw boundary is the
provider's OCRResult serialized to JSON, **not the vendor's internal raw engine
response**. Model tasks must disclose this limitation or implement a richer
adapter. The bridge does not extract table/chart structures from arbitrary
metadata. It imports no provider implementation and creates no model on import.

Production ResultCache was reviewed: its fingerprints depend on application
settings, native probes and a possible remote Ollama request. The isolated suite
store reuses its kernel-lock/atomic-publication principles while retaining raw
bytes, benchmark identity and the richer envelope. It does not call the production
service/cache or alter production/historical evaluator behavior.

## Approval and preflight

The runner accepts one `AdapterSpec`, never a model list. Before constructing a
real adapter, it loads the validated coordinator status and requires:

- Completed TASK-003/005/006/007/008 prerequisites.
- The selected model's corresponding TASK-009 through TASK-017 explicitly
  approved, current and IN_PROGRESS; that same model must be IN_PROGRESS.
- A known requested model ID. A preceding model approval does not authorize the
  next model. Existing BLOCKED_BY_HARDWARE and Baidu ambiguity remain blockers.

Fixture mode accepts only `model_id=fixture`; real candidate IDs cannot use it.
Injected probes and interruption hooks are permitted only in fixture mode.
Fixtures are a testing seam, not an execution sandbox: arbitrary caller Python
is trusted code. Model-specific factories require review in their own tasks.

Live preflight reads psutil RAM/disk, native NVIDIA inventory and installed
distribution/build metadata. It does not import torch/paddle or initialize CUDA.
It checks declared compatibility, model-specific additional RAM estimate,
available VRAM/compute capability, exact package versions and model/native/source
asset SHA256 hashes. CUDA configurations require a declared backend; PyTorch
requires metadata evidence of a CUDA build and Paddle requires a GPU distribution.
Driver/engine/precision/native compatibility must also be established by the
model-specific evidence/configuration review; a generic probe cannot certify
every binary/runtime combination.

Real runs enforce at least 2 GiB available RAM and 6 GiB disk reserve in addition
to the configured disk requirement. Available memory must meet the larger of
the policy floor and the declared RAM requirement. Unknown/incompatible, missing
estimates/assets, insufficient RAM/VRAM/disk and dependency mismatches fail closed.
Recheck before initialization and each uncached document, including after loading.
The full headroom requirement is conservatively checked again after loading;
document how the model-specific estimate accounts for resident memory.
These are resource guardrails, not a guarantee against other applications changing
memory availability. The runner never closes applications or provisions resources.

Initial refusal raises `PreflightBlocked` before model construction. A mid-run
resource refusal records BLOCKED_BY_HARDWARE and leaves the run incomplete for
inspection/resume. It does not manufacture an OCR failure or advance another model.
The coordinator/CLI must record justified tracker transitions; the runner does not
grant approvals or silently rewrite model states.

## Identity, persistence and recovery

`load_records` verifies the frozen manifest against provenance, strict record
schemas, unique IDs, approved source revisions and image/reference SHA256 hashes.
Paths must stay inside the suite's data root. Source/reference hashes are checked
again before each document and after normalization; changed inputs cannot enter
the successful prediction cache. Inputs are never repaired or renamed.

Cache keys include document ID/image bytes, model/adapter revision, capabilities,
label map, requirements/evidence, asset/source hashes, all recorded configuration,
shared inference/normalization source files, installed package/Python versions
and stable hardware/driver identity. Free-RAM snapshots/timestamps do not affect
the key. This is deliberately conservative: unrelated package changes can
invalidate reuse. Reference/evaluator changes are separate from prediction
identity; saved outputs support independent offline reevaluation.

A single persistent OS lock at `cache/coordinator.lock` serializes runners and
evaluators for this suite root. A competing runner fails immediately. Windows
msvcrt / Unix flock ownership is released by the kernel after process death;
the lock file is never deleted or stolen by age. This is a local single-suite
coordinator, not a distributed lock across separate checkouts/machines.

Each run has an exclusive timestamp/random directory. Before loading it writes
immutable run/config/environment metadata. Each successful prediction is
published to an exclusive checksummed cache bundle, then copied to a checksummed
document receipt. Publication writes/fsyncs files in a unique staging directory
and renames it under the lock. The final receipt, rather than progress.json, is
the per-document commit. Atomic progress is a human-readable summary.

If killed after cache publication but before the receipt, resume verifies and
reuses that cached output. Existing valid receipts are skipped. If killed before
any durable successful publication, the in-flight document may need repeating;
exactly-once execution before persistence cannot be guaranteed. Unpublished
temporary directories are retained for inspection, never automatically promoted.
Atomic rename/fsync does not guarantee every filesystem's power-loss durability.

Only successful, schema/identity-valid outputs without provider page/document
errors enter cache. Failed predictions retain available raw/normalized output
and a typed error receipt; they count toward failure coverage. Corrupt cache or
receipts block rather than silently overwrite/reinfer. Failures are terminal
within a finished run; a new run retries failures and reuses successful cached
documents. An unfinished run can resume only with identical dataset selection,
model/config/code/package/hardware identity. Cleanup runs after initialized or
partly initialized adapters; cleanup errors remain explicit session diagnostics.

Completed runs have a completion manifest covering document-bundle manifests,
run/config/environment files and all session records. They are immutable and
cannot be resumed. Cryptographic hashes detect accidental changes relative to
these local manifests; they are not a signature proving third-party authenticity.

## Timings and resources

Every session records initialization duration and resource snapshot. Document
receipts distinguish explicit prepare, predict and normalize durations; record
the first predict attempt after initialization as cold and subsequent attempts
as warm. Provider-internal preprocessing/postprocessing remains inside predict
unless the adapter exposes it; do not pretend it was separately measured.
No installations/downloads are performed or included in inference duration.

RSS is sampled every 50 ms for the runner process and descendants. GPU execution
also samples NVIDIA per-process context memory approximately every second,
limited to the runner and its descendants on the selected device. These sampled
maxima are not allocator/hardware exact peaks and can miss short-lived peaks.
NVIDIA WDDM can report N/A; absent/unknown own context yields null, never zero.
The installed `nvidia-smi --help-query-compute-apps` documents that limitation.
Model tasks must verify CUDA device/visibility mapping and any external server
memory scope; unrelated server processes are not included by this sampler.

Cache hits never initialize an adapter or create a fresh speed measurement.
Original times/resources remain provenance; exported fresh timing/resource
columns are null on cache hits. Successful-fresh throughput is reported separately
from success rate/failure counts. Session wall time also includes preflight,
validation, cache and persistence work; it is not inference latency. Sessions
terminated without an end record have unknown full wall time and are counted.
Cold initialization logs from previous interrupted sessions remain preserved.

Config identity retains device, local execution, precision, batch size, DPI and
preprocessing/resize parameters. Source record width/height are passed to the
adapter and retained through dataset identity. No implicit cloud environment or
paid API execution route is implemented. Hardware differs => separate identity;
never directly rank speed across different hardware/configuration.

## Annotation-supported evaluation

`runners/evaluate.py` applies manifest/capability gates and the versioned routing
settings in `configs/evaluation.json`, using TASK-006 calculators/formulas.

- English text: allocate predicted text blocks to explicit nonignored transcript
  regions using >=50% prediction-area overlap, highest overlap and stable source
  index ties. Multiple word/line blocks may share a reference region. Use provider
  reading order when all assigned blocks supply it; otherwise retain provider
  array order. Never use recognized text for matching. Missed eligible regions
  receive empty output; unassigned predicted blocks and region coverage are
  disclosed separately because complete page text truth is unavailable.
- Raw serialization stays separate from common content. Each declared Markdown
  field is converted; a plain block-text fallback remains literal even inside
  an otherwise Markdown envelope. Arabic page text is scored against publisher
  page Markdown content; plain predictions are not parsed as Markdown.
- Coordinate conversion requires declared normalized bounds or matching page
  dimensions/units. Scale explicitly to source pixels and convert bottom-left
  origins. Missing/invalid geometry withholds geometry-dependent metrics, rather
  than inventing a reading order or full-page English text score.
- Source masks/excluded labels suppress otherwise unmatched predictions covering
  >=50% of their own area in an excluded region. Valid same-class truth matches
  take precedence. Unknown model-label mappings withhold layout/order metrics;
  counts are disclosed. The dataset-wide canonical taxonomy defines negative
  classes too; a false figure on a paragraph-only page counts as a false positive.
  Missing detection confidence permits stable-order PR
  matching but withholds AP/mAP. Thresholds are configurable and recorded.
- Reading order uses independently matched canonical blocks and explicit source
  order IDs; tied predicted orders remain unscored. Arabic order truth is absent.
- English table structures pair by geometry at the configured IoU (default 0.5).
  Missing eligible tables score as empty structured output; extras/misses are
  retained in table detection. No table confidence is inferred for AP. Arabic
  HTML table pairing is allowed only on a single-table reference/prediction page;
  multiple unaligned tables receive TABLE_ALIGNMENT_UNAVAILABLE. If all tables
  are absent, valid reference tables can be scored as misses. Strict grid/tree
  gates and resource-limit reasons remain visible in each table result.
- Figure detection stays separate from chart type/text/numeric/components.
  Primary numeric/type/component truth is unavailable. No generated structure or
  prediction becomes ground truth. Inference failures have null metrics and
  explicit counts, never zero-filled accuracy.

Offline `report.evaluate_run` needs completed run bundles and frozen references,
not an adapter, model, CUDA or prediction cache. It writes a new exclusive sibling
evaluation directory keyed by policy/code/reference/run identity plus a random
suffix. It verifies hashes before scoring; incomplete evaluations have no final
evaluation_manifest.json and are not eligible for comparison.

Exports include predictions.jsonl, metrics.json/CSV, per-document/page and language
CSV, layout/table/chart/order/performance CSV, failures.csv, errors.log, policy,
environment and MODEL_REPORT.md. Per-page structured metrics retain their full
gates/counts. Text summaries separate language and supplied category, pool English
region edits within each image, report micro/macro distributions and explicitly
page-level seeded confidence intervals. Source-document independence is unknown.
Layout mAP is also recomputed across each complete scored stratum, preserving
page identities; it is not an average of per-page AP. Table summaries count actual
scored fragments and expose resource/reference exclusions; a page with no scored
table is not counted as scored table coverage. General cross-model selection,
comparison and visualization remain later tasks.

```text
results/<model>/<unique-run>/
    run_manifest.json, config.json, environment.json, progress.json
    sessions/<session>-start.json, *-initialized.json, *-end.json
    documents/<hashed-document>/raw.bin, prediction.json, bundle.json
        # error.json also exists on failed prediction/normalization
    completion.json
results/<model>/evaluations/<unique-run>/<policy-code-id>-<random>/
    metrics.json, metrics.csv, predictions.jsonl, per_page_metrics.csv, ...
    evaluation_manifest.json
cache/predictions/<prediction-key>/raw.bin, prediction.json, bundle.json
```

All generated runs/caches remain ignored/local. No selected_run pointer is
automatically changed. Model tasks must review an official run before selection.

## Verification and next checkpoint

```powershell
.venv-ocr\Scripts\python.exe -m pytest benchmark_suite/tests/test_runner.py -q
.venv-ocr\Scripts\python.exe -m pytest benchmark_suite/tests -q
.venv-ocr\Scripts\python.exe -m ruff check benchmark_suite
.venv-ocr\Scripts\python.exe -m benchmark_suite.tracking
```

33 synthetic runner tests cover lifecycle/raw output, cache hits/invalidation,
actual worker process termination after cache publication, OS lock release,
resume without duplicate persisted inference, initialization/document failures,
cleanup, source/reference/output/cache tampering, source mutation during predict,
one-model approvals, hardware/assets/packages/disk gates, geometry/text/mask routing,
Arabic table alignment, confidence withholding, WDDM null samples and deterministic
offline reevaluation without cache. No real-model execution is part of these tests.

TASK-008 remains the Windows menu/CLI integration. It must call these shared
functions with exactly one explicitly approved model factory and retain all gates.
Every model task still stops for a new, model-specific approval.
