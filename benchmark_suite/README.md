# OCR benchmarking suite

This isolated suite will compare nine OCR configurations across English and
Arabic text, layout, reading order, tables and charts using verified public
ground truth and auditable measurements. **Foundations only are implemented.**
No new model evaluation, dataset download or accuracy comparison has been run.

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
Implementations, current official versions, licenses and actual Arabic/English
capabilities will be verified in TASK-003. Baidu API versus another
implementation must be resolved before its setup. Existing production adapters
do not establish all nine candidates' capabilities.

- TASK-003: laptop CPU/RAM/GPU/VRAM/CUDA/driver/Python/Windows/disk/WSL2 and
  model compatibility evidence, exact requirements and free local strategy.
- TASK-004/005: select licensed independent English/Arabic reference datasets,
  obtain required download approval, verify provenance/hashes and freeze splits.
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

Dataset sources/licenses and verified model environments remain pending their
research tasks. Windows menu, setup, single-model runs, smoke/resume/evaluation,
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
