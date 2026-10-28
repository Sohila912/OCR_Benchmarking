# OCR benchmarking suite

This isolated suite will compare nine OCR configurations across English and
Arabic text, layout, reading order, tables and charts using verified public
ground truth and auditable measurements. **Foundations, hardware/model research, dataset selection and local preparation are implemented.**
The two approved primary datasets are downloaded and validated. No model evaluation or accuracy comparison has been run.

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
- TASK-006: define/test text, layout, table, chart, reading-order and statistical
  metrics against the actual annotation types.
- TASK-007/008: hardware preflight, adapters/runner, cache/recovery, Windows
  launcher and equivalent Python CLI.
- TASK-009 through TASK-017: one approved model evaluation at a time, each
  ending with its own artifacts, quantitative report and stop.
- TASK-018 through TASK-021: stored-result comparisons, visualizations,
  reproducibility audit and final documentation.

Do not use the production launcher to bypass the hardware assessment: it can
provision assets. No new installs, CUDA/driver/WSL changes, paid services or large
downloads are part of the current checkpoint. Hardware-blocked models stay in
the plan as BLOCKED with reason BLOCKED_BY_HARDWARE.

## Methodology to implement

Use identical frozen documents, explicit versions/configuration and raw outputs.
Only independent trusted references support scores. Evaluate English/Arabic and
document categories separately; report missing annotations and unsupported
capabilities explicitly. No OCR model's output is ground truth. Reevaluate saved
predictions without repeating inference. Keep local/cloud hardware identities
and qualify throughput/resource comparisons across different hardware.

Metric formulas, empty-input policies, accuracy definitions, raw versus
normalized Arabic scores (Unicode, whitespace, diacritics, alef, hamza, tatweel),
matching/IoU/taxonomy/TEDS/statistics and justified display scales are TASK-006
deliverables. Existing historical evaluator policies remain unchanged and must
not be mixed with future scores without checking their definitions.

Dataset sources/licenses and proposed acquisition are documented in the selection
report; the approved primary payloads and frozen manifests are now validated. Model environments require
per-model setup and preflight despite the completed compatibility research. Windows menu, setup, single-model runs, smoke/resume/evaluation,
report generation and comparison commands will be documented with tested
examples when implemented in TASK-008/018/019. There is no run_benchmark.bat or
inference CLI yet. Do not execute the future commands in the implementation plan
until their owning task and hardware prerequisites are complete.

Results will be kept in unique model run directories with source/config/data
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
not a model minimum. Passing it still needs the model-specific TASK-007
preflight. Do not treat CUDA 13.0 in NVIDIA-SMI as installed CUDA-enabled Torch:
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
