# OCR benchmarking suite

Latest continuation (2026-11-04): Baidu Unlimited-OCR-2 completed five new
hosted development pages after the free quota reset. Total saved: 12 successes
(6 English/6 Arabic), all untruncated; seven prior successes were verified/reused.
The next request exhausted free quota (90 seconds requested versus 78 remaining;
service advised 23:54:01 until retry). Eight development pages remain. Results,
readable outputs and checksums are on D:. See [Baidu report](reports/BAIDU_UNLIMITED_OCR.md).
TASK-017 is BLOCKED by free quota. No paid service or official full evaluation
was started; hosted weight revision remains unverified. Paddle's completed
200-page subset is preserved; its remaining full evaluation is deferred while
following the user's Baidu request. Earlier next-action statements are historical.

Latest checkpoint (reviewed 2026-11-04): PaddleOCR completed the requested
200 additional evaluation pages (100 English, 100 Arabic), with zero conversion
failures. Text scores cover 99 English pages (one unavailable reference) and all
100 Arabic pages. Normalized CER/WER: English 14.17%/23.48%, Arabic 51.53%/71.34%;
reference scopes differ. Wall time 97.89 minutes; sampled peak RSS 0.71 GiB.
The deterministic subset is separate from the 20 development pages. Results and
canonical copies are saved on D:. See [the 200-page report](reports/PADDLE_EVALUATION_200.md).
TASK-012 remains IN_PROGRESS: 935 of 1,135 evaluation pages remain. No full
selected-run marker or subsequent model run was created. Earlier checkpoint and
next-action statements below are historical.

Latest model checkpoint (2026-11-03): the user clarified to move to the next
model. Standard PaddleOCR TASK-012 is approved and completed all 20 development
pages locally with zero conversion failures. English normalized CER/WER are
7.98%/23.75%; Arabic 56.29%/77.29% (10 pages scored per language, different reference
scopes). Sampled peak RSS 0.55 GiB; run wall 424.38 seconds. The isolated CPU
runtime, pinned mobile models, inputs, native outputs and reviewed report/charts
are on D:. See reports/PADDLE.md, PADDLE_RESULTS.json and PADDLE_ASSETS.json.
214 tests, Ruff and isolated dependency check pass. TASK-012 remains IN_PROGRESS
with full evaluation pending, not hardware-blocked. Baidu quota/offline work was
stopped as requested and its saved results retained. Earlier next-action and
approval statements below are historical. TASK-018 is not started.

Latest continuation (2026-11-03): Unlimited-OCR-2 now has 7 saved successful
hosted development pages (4 English, 3 Arabic), five more than the original two.
The helper reused earlier successes and used the user's local Hugging Face login
for four new calls. The next request hit the free account quota (90 s requested,
59 s left; the service advised retrying in about 24 hours). TASK-017 is BLOCKED:
HOSTED_FREE_QUOTA_EXHAUSTED. There are 13 pages remaining, including one quota-denied
page and 12 never attempted. Outputs and reviewed per-page CSV/Markdown copies are
on D:; see reports/BAIDU_UNLIMITED_OCR.md. No paid service or quota workaround was
used. Full evaluation and accuracy scoring remain incomplete; 212 suite tests
and Ruff pass. Earlier next-action/checkpoint statements below are history.

Latest checkpoint (2026-11-03): the user clarified Baidu means the free
open-source Unlimited-OCR repository. TASK-017 is approved. Its linked official
Hugging Face demo completed one frozen English and one Arabic image, with server
elapsed times 25.9/53.7 seconds and neither response truncated. Inputs, native
outputs and readable copies are on D:. See reports/BAIDU_UNLIMITED_OCR.md and
BAIDU_UNLIMITED_OCR_RESULTS.json. These are hosted feasibility results, not local
inference, accuracy scores or a completed 20-page/full evaluation. Local CUDA/VRAM
and formal hosted reproducibility remain blockers; TASK-017 is BLOCKED with
successful feasibility preserved. No paid Cloud API or credentials were used.
TASK-018 is not started. Earlier next-task/approval statements below are history.

Latest checkpoint: Granite Docling loaded on CPU using D: assets, but its Arabic
development attempt had a native runtime crash and a retry reached the generation
limit with repeated tatweel characters. No completed development/full evaluation
or accuracy scores. See [Granite evidence and limitations](reports/GRANITE_DOCLING.md).
Docling + Tesseract checkpoint 6b92577 was pushed; its full run remains deferred.
Earlier checkpoint notes below are history.

Latest checkpoint: Docling + Tesseract completed the 20-page development run
(19 successes, one timeout). The user deferred full evaluation and approved
Granite Docling next. See [saved results and scope](reports/DOCLING_TESSERACT.md).
Model files/native outputs/reviewed report and charts are on D:; canonical runner
metadata is also preserved in this repository. Earlier checkpoint notes are history.

Latest checkpoint (2026-11-03): Docling + EasyOCR was installed and actually
attempted on CPU. Inference failed with a memory allocation error, including a
D: retry after unrelated apps were closed. The tested job-memory budget was
2.99 GiB; this is not a universal model minimum. Zero successful pages and no
full-evaluation score. See [actual attempt and failure report](reports/DOCLING_EASYOCR.md).
Environment, model cache, final trial input and outputs are on D:.

Tesseract TASK-013 successfully processed all 20 development pages and saved
437 evaluation pages with zero OCR failures. Full evaluation is incomplete:
available RAM repeatedly fell below the shared 2-GiB floor. The saved run is
resumable when stable headroom is available. See
[Tesseract configuration and evidence](reports/TESSERACT.md). Standard PaddleOCR
TASK-012 remains pending; no other model is selected. Older notes below are history.

Surya, PaddleOCR-VL and Marker remain blocked. Their dated assessments are
preserved in reports/SURYA_BLOCKED.md, reports/PADDLE_VL_BLOCKED.md and
reports/MARKER_BLOCKED.md. Standard PaddleOCR remains pending.

This isolated suite will compare nine OCR configurations across English and
Arabic text, layout, reading order, tables and charts using verified public
ground truth and auditable measurements. **Foundations, hardware/model research, dataset selection, local preparation, metrics, the shared adapter/runner and Windows menu/CLI are implemented.**
The two approved primary datasets are downloaded and validated. Tesseract has
completed development smoke and saved a partial frozen evaluation. No cross-model
accuracy comparison has been run.

Read [PROGRESS.md](PROGRESS.md), [BENCHMARK_STATUS.json](BENCHMARK_STATUS.json)
and [BENCHMARK_PLAN.md](BENCHMARK_PLAN.md) before resuming work. The
[architecture](ARCHITECTURE.md) defines reuse boundaries, state transitions,
artifact handling and the planned immutable output format.

## Available now

Run from the repository root with the existing Python interpreter (Python 3.10+
for the tracker). The module never imports an OCR package or starts a service.

```powershell
python -m benchmark_suite.tracking
python -m benchmark_suite.tracking --status benchmark_suite/BENCHMARK_STATUS.json
python -m pytest benchmark_suite/tests/test_tracking.py -q
```

The validator is read-only and exits 0 for a valid checkpoint, 1 for missing,
malformed or invalid state. It validates recorded state, not hardware, datasets,
Git commits or actual task artifact completeness; inspect those when resuming.
Tests require the existing pytest development dependency. IANA timezone
validation uses Python zoneinfo and the system timezone database or the tzdata
package (commonly needed on Windows); no dependencies were installed for this
checkpoint. The suite currently runs from source; installed distribution support
has not been added to pyproject.toml.

For a coordinator update, load a detached record, change only justified fields,
then save through the validated writer:

```python
from pathlib import Path
from benchmark_suite.tracking import load_status, save_status

path = Path("benchmark_suite/BENCHMARK_STATUS.json")
state = load_status(path)
# Record verified work and real approval; never infer or invent either.
state["next_action"] = "Inspect the artifacts for the current task."
save_status(path, state)
```

Serialize writes through one coordinator. Atomic saves protect against partial
JSON, not concurrent lost updates. Retry I/O failures after resolving their
cause. For corrupt state, preserve the file, inspect the last Git checkpoint and
outputs, and explicitly recover rather than overwriting with defaults. An
interrupted writer may leave an ignored temporary file; it is never loaded
automatically. Keep progress Markdown and plan aligned at each checkpoint.

## Windows launcher and equivalent CLI

From the repository root, open the menu (or double-click the batch file):

```powershell
.\benchmark_suite\scripts\run_benchmark.bat
```

It provides the exact 13 options requested in Task_codex.txt. Without arguments,
`python -m benchmark_suite.cli` opens the same menu. With arguments the batch
launcher forwards to the same CLI and returns its exit code. Paths containing
spaces and ampersands are tested. No packages or model assets are installed.

The launcher uses `OCR_BENCHMARK_PYTHON` when explicitly set, otherwise existing
`.venv-ocr`, then `benchmark_suite/environments/shared`, then `py -3` or Python
on PATH. It checks Python 3.10+. Help works without third-party packages; commands
that need the runner validate the direct tested requirements-runner.txt pins.
The current existing .venv-ocr passes these shared checks. Passing them does not
certify that an OCR model can run.

```powershell
.venv-ocr\Scripts\python.exe -m benchmark_suite.cli --help
.venv-ocr\Scripts\python.exe -m benchmark_suite.cli check-environment --json
.venv-ocr\Scripts\python.exe -m benchmark_suite.cli models
.venv-ocr\Scripts\python.exe -m benchmark_suite.cli progress
.venv-ocr\Scripts\python.exe -m benchmark_suite.cli validate-datasets --json
```

Environment checks inspect metadata/native tools without importing torch/paddle
or loading models. The RAM loading gate is separate from successful inventory.
Dataset validation rehashes all 1,155 frozen source/reference pairs without
network access, decoding models, or changing the data.

| Menu | CLI command | Behavior |
|---|---|---|
| 1 | `check-environment [--model MODEL]` | Python/dependency/live-resource inventory; optional selected-model readiness |
| 2 | `models` | All nine candidates with pending implementation, saved state and approval/blockers |
| 3 | `progress` | Validated saved task progress; no approval changes |
| 4 | `setup --model MODEL` | Audit the approved model's existing isolated setup; no installation |
| 5 | `validate-datasets` | Offline frozen dataset validation |
| 6 | `smoke --model MODEL --language en/ar/both` | One approved model on frozen development images |
| 7 | `run --model MODEL --language en/ar/both --mode quick/full` | One approved model and one selected split |
| 8 | `resume --model MODEL --run-dir PATH` | Original split/language/precision/settings; unfinished run only |
| 9 | `evaluate --model MODEL --run-dir PATH` | Fresh evaluation of saved predictions; no inference |
| 10 | `report --model MODEL --run-dir PATH` | Regenerate evaluation and individual report; no inference |
| 11 | `compare` | Explicit PENDING TASK-018, exit 4 |
| 12 | `final-report` | Explicit PENDING TASK-019, exit 4 |
| 13 | Exit | No additional action/model |

Every action accepts `--json` **after the command**, except the interactive menu.
Relative artifact paths use the caller's working directory; absolute paths are
also accepted. Explicit saved run paths are required: the CLI never silently
chooses the latest run. There is no `--all`, `--yes` or public fixture bypass.
Repeated `--model` is rejected. Menu cancellation returns without a model call.

### Model approval, setup and isolated environments

Tesseract is registered in configs/models.json with its dedicated environment;
the other eight implementations remain pending. Existing hardware/ambiguity
blockers remain. Selecting a
menu item is not model approval. `setup`, `smoke`, `run` and `resume` refuse until
the selected model's task is independently approved/current/IN_PROGRESS, its
implementation and pinned environment exist, and live preflight passes. A completed
shared framework or a previous model's approval never authorizes the next model.

At this checkpoint `setup` is an existing-setup/readiness audit. There are no
registered installation actions. Actual package/asset setup belongs to the
separately approved TASK-009 through TASK-017, after hardware/version/license
review. No pip/driver/CUDA/WSL installation is hidden in the launcher or CLI.

Those tasks must register reviewed spec/config/factory paths, exact requirements
and an interpreter under `benchmark_suite/environments/<model>/`. The CLI requires
that environment's sys.prefix; it will print the required interpreter and refuse
an automatic environment switch. Dependencies that conflict with the main
application belong in these isolated environments. For the launcher, explicitly
set `$env:OCR_BENCHMARK_PYTHON` to the already approved, existing model interpreter,
or invoke that interpreter directly. Do not add credentials to the catalog or
config; any future API credential handling requires its model-specific review.

The following commands describe future approved execution and currently return
BLOCKED because the model task/implementation/environment is not ready:

```powershell
python -m benchmark_suite.cli setup --model surya
python -m benchmark_suite.cli smoke --model surya --language both
python -m benchmark_suite.cli run --model surya --language en --mode quick
python -m benchmark_suite.cli run --model surya --language both --mode full
python -m benchmark_suite.cli resume --model surya --run-dir "benchmark_suite/results/surya/<run-id>"
```

Quick uses only the frozen development split (10 English + 10 Arabic images before
language filtering). Full uses evaluation (745 English + 390 Arabic). Language
is en, ar or both; quick is the default. Resume does not accept language/mode
changes. Version/config/source/hash changes invalidate reuse or prevent resume;
completed runs are immutable. No subsequent model starts automatically.

After an actual completed run exists, offline evaluation/report commands work
without an active model, its weights, initialization or the prediction cache:

```powershell
python -m benchmark_suite.cli evaluate --model surya --run-dir "benchmark_suite/results/surya/<run-id>"
python -m benchmark_suite.cli report --model surya --run-dir "benchmark_suite/results/surya/<run-id>"
```

They verify completed bundles/frozen references and write a new sibling evaluation
with metrics/CSV/report files. If post-run evaluation fails, the CLI reports the
saved run path; retry evaluation without inference. Cached timing is provenance,
not a new speed measurement. Inspect coverage and the scope/TEDS/uncertainty
limitations in [RUNNER.md](reports/RUNNER.md) and [METRICS.md](reports/METRICS.md).

### Logs and troubleshooting

Recognized command invocations automatically create unique ignored JSON logs
under benchmark_suite/logs/cli; the response includes log_file. Help, argument
syntax rejection and closing the menu do not create action logs. Logs and model
runs remain local. The CLI never edits the coordinator approvals/status itself.

| Exit | Meaning |
|---|---|
| 0 | Command completed; shared inventory success does not approve inference |
| 1 | Missing/different dependencies, invalid/corrupt artifacts, failed documents, or another execution/evaluation/logging error |
| 2 | Invalid arguments (including all/repeated models) |
| 3 | Model approval, implementation/environment readiness or hardware preflight blocked |
| 4 | Comparison/final-report task is pending |
| 130 | Interrupted command; persisted work can be inspected/resumed |

If Python is not found, select an existing compatible interpreter through
OCR_BENCHMARK_PYTHON. If dependency pins differ, inspect requirements-runner.txt
and use a reviewed isolated environment; the CLI does not repair the main app.
If a model is blocked, read the named task/blocker and hardware report; do not
bypass the gate. Corrupt outputs are preserved for inspection. An incomplete run
can resume; a completed run can only be evaluated or retried as a new run with
successful prediction reuse.

## Planned evaluations and prerequisites

Candidates: Surya, PaddleOCR-VL, Marker, standard PaddleOCR, Tesseract,
Docling + EasyOCR, Docling + Tesseract, Granite Docling and Baidu OCR.
Official versions, licenses, declared Arabic/English capabilities and laptop
compatibility were researched in TASK-003; actual accuracy remains unmeasured. Baidu API versus another
implementation must be resolved before its setup. Existing production adapters
do not establish all nine candidates' capabilities.

- TASK-003 (complete): [hardware profile](reports/HARDWARE_PROFILE.md),
  [compatibility and resource strategy](reports/MODEL_HARDWARE_COMPATIBILITY.md),
  [capabilities/dependencies](reports/MODEL_CAPABILITIES.md) and
  [research-only model registry](MODEL_REGISTRY.yaml). Current low RAM blocks model loading.
- TASK-004 (complete): [dataset selection](datasets/DATASET_SELECTION.md) proposes
  OmniDocBench English pages and Misraj-DocOCR Arabic pages, with source/rights
  evidence, an existing-data audit and explicit missing-annotation coverage.
- TASK-005 (complete): [local data and reproduction](datasets/README.md),
  [frozen manifest provenance](datasets/manifest/PROVENANCE.json) and
  [validation report](reports/DATASET_VALIDATION.md). Evaluation contains
  745 English + 390 Arabic images; development contains 10 per language.
- TASK-006 (complete): [metric formulas and scope](reports/METRICS.md), versioned
  configs/evaluation.json, isolated metrics/ calculators and a reference-only
  [readiness audit](reports/METRIC_REFERENCE_AUDIT.json). 122 suite tests pass.
  English text requires independent region matching; Arabic numeric chart/order
  truth is unavailable. Calculators are implemented; model scores remain unmeasured.
- TASK-007 (complete): [shared runner and recovery](reports/RUNNER.md), explicit
  adapter lifecycle, single-model approval/preflight gates, immutable raw/normalized
  bundles, cache/timings, scoped metrics and independent offline evaluation.
  Tesseract was subsequently registered in TASK-013; the other real model factories remain pending.
- TASK-008 (complete): [13-option launcher](scripts/run_benchmark.bat), matching
  [Python CLI](cli.py), pending model catalog and [verification](reports/CLI_VALIDATION.md).
  Real setup/execution still needs each separately approved model task.
- TASK-009 (Surya): [hardware-blocked assessment](reports/SURYA_BLOCKED.md),
  approved on 2026-11-01 but no installation/download/inference. Candidate remains
  Surya 2 / 0.22.1; latest 0.23.0 drift is recorded. All scores remain unmeasured.
- TASK-009 through TASK-017: one approved model evaluation at a time, each
  ending with its own artifacts, quantitative report and stop.
- TASK-018 through TASK-021: stored-result comparisons, visualizations,
  reproducibility audit and final documentation.

Do not use the production launcher to bypass the hardware assessment: it can
provision assets. No new installs, CUDA/driver/WSL changes, paid services or large
downloads are part of the current checkpoint. Hardware-blocked models stay in
the plan as BLOCKED with reason BLOCKED_BY_HARDWARE.

## Measurement methodology

Use identical frozen documents, explicit versions/configuration and raw outputs.
Only independent trusted references support scores. Evaluate English/Arabic and
document categories separately; report missing annotations and unsupported
capabilities explicitly. No OCR model's output is ground truth. Reevaluate saved
predictions without repeating inference. Keep local/cloud hardware identities
and qualify throughput/resource comparisons across different hardware.

Metric formulas, empty-input policies, accuracy definitions, raw versus
normalized Arabic scores (Unicode, whitespace, diacritics, alef, hamza, tatweel),
matching/IoU/taxonomy/TEDS/statistics are documented in
[METRICS.md](reports/METRICS.md), with shared routing in [RUNNER.md](reports/RUNNER.md). Existing historical evaluator policies remain unchanged and must
not be mixed with future scores without checking their definitions.

Dataset sources/licenses and proposed acquisition are documented in the selection
report; the approved primary payloads and frozen manifests are now validated. Model environments require
per-model setup and preflight despite the completed compatibility research. Windows menu, setup, single-model runs, smoke/resume/evaluation,
report generation are exposed by the launcher/CLI below. Comparison/final-report
commands explicitly remain pending TASK-018/019. Real model factories and isolated
environments are not yet registered. Do not bypass model approval or hardware gates.

The shared runner keeps results in unique model run directories with source/config/data
hashes, raw and normalized predictions, per-document/page/category metrics,
timing/resource measurements, errors and reports; see ARCHITECTURE.md. Downloaded
content and generated runs are ignored by Git. Preserve local outputs and record
their checksums; do not force-add them. Source notes, reviewed manifests and
Markdown reports can be versioned without duplicating historical datasets.

## Repeat a read-only hardware observation

From the repository root, use the existing environment to inspect its package
metadata. No framework/model import or inference occurs:

```powershell
.venv-ocr\Scripts\python.exe benchmark_suite/scripts/check_hardware.py --output benchmark_suite/reports/hardware_observations/new-check
.venv-ocr\Scripts\python.exe -m pytest benchmark_suite/tests -q
```

Choose a new output directory each time; the helper refuses to overwrite an
existing profile. Store measurements before any eventual model trial. The
saved TASK-003 profile has 7.74 GiB total RAM, 0.61 GiB available and a 2-GiB
MX350 (CC 6.1). The 2-GiB available-RAM stop is a conservative suite policy,
not a model minimum. Passing it still needs the implemented model-specific
runner preflight, with a separately approved model task. Do not treat CUDA 13.0 in NVIDIA-SMI as installed CUDA-enabled Torch:
the inspected Torch/Paddle builds are CPU-only. No API/cloud environment was
used. See the reports for evidence, limits, remedies and cost/approval gates.

## Dataset acquisition checkpoint

The user approved local acquisition, superseding the Drive preference. The
pinned English OmniDocBench subset and all 400 Arabic Misraj pages are stored
under ignored datasets/raw, datasets/english and datasets/arabic paths. Transfer
was about 1.40 GB decimal, below 2.2 GB, with about 2.03 GB local data/metadata
including preserved original shards and extracted images. Supplements and models
were not downloaded. Original license restrictions and source notices remain.

See [datasets/README.md](datasets/README.md) for explicit download, build and
offline verification commands. The manifests contain 1,155 source/reference pairs:
20 development and 1,135 evaluation images. Per-page metric eligibility and source
warnings are preserved. Source document/book grouping remains unknown; do not
claim source-document-independent splits or confidence intervals.

The historical curated data remains unchanged and unverified for publication.
Its Mix invoice_5 / Invoice_5 case alias is recorded explicitly without renaming
source files. Only reviewed manifests/provenance are versioned; payloads and
transcriptions stay local and ignored. Low RAM can still block preprocessing;
passing preparation checks does not authorize model inference.
