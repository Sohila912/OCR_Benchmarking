# Tesseract CPU benchmark

TASK-013 was selected on 2026-11-02 after the user asked to proceed with a model
that fits the laptop. TASK-012 standard PaddleOCR remains pending; this does not
approve any subsequent model. Surya, PaddleOCR-VL and Marker retain their blockers.

## Selected configuration

- Installed Windows native Tesseract 5.4.0, CPU only, one image/process at a time.
- Official `tessdata_fast` English and Arabic from revision
  `87416418657359cb625c412a48b6e1d6d41c29bd`, Apache-2.0.
- Files total 5,545,144 bytes. Download URLs, sizes and SHA256 are preserved in
  TESSERACT_ASSETS.json; no global language-data installation was changed.
- LSTM engine (`--oem 1`), automatic segmentation (`--psm 3`), one OpenMP thread,
  300-DPI hint, 120-second page timeout. Original image dimensions and pixels
  remain unchanged. Each manifest language selects `eng` or `ara` exclusively;
  mixed-language recognition is not a separately evaluated configuration.
- Native TSV and stderr are preserved in a JSON raw envelope. Normalization
  reuses the production TSV parser, groups words into their native lines, and
  retains native line order. Line geometry is the union of native word boxes.
  No ground truth informs segmentation, preprocessing or recognition.
- Only text capability is declared. Semantic layout, general reading order,
  table topology and chart understanding are not provided by this baseline.
  Native text-line ordering is used for text assembly without claiming a
  semantic reading-order capability.

Every page launches a new native Tesseract process. The inference timer includes
native process startup, language-data loading and OCR; adapter initialization
times only version/language probes. The shared runner's cold/warm labels refer
to invocation order, not a persistent warmed Tesseract model. Phase timings must
be interpreted at that boundary when comparing this baseline with other engines.
Internal native image preprocessing/decoding phases are included in the OCR
subprocess timer and cannot be separately measured through this CLI boundary.
External preprocessing is identity; postprocessing measures TSV normalization.

## Environment and resource gate

`environments/tesseract` is a separate Python 3.13.7 virtual environment.
Exact installed runtime pins are in configs/tesseract-requirements.txt.
No Torch/Paddle model runtime, GPU dependency or global application package was
installed or modified. The existing native executable/DLLs and both traineddata
files are hashed in configs/tesseract-spec.json, along with adapter/helper source.

The fresh hardware profile is under
hardware_observations/tesseract-task013-20261102/. Available RAM was above the
generic 2-GiB floor and the estimated 0.5-GiB additional process budget. The shared
runner rechecks live headroom and hashes before each uncached page; no gate was
weakened. It samples process/descendant RSS every 50 ms; a sampled peak can miss
short allocations. CPU operation has no applicable model GPU-VRAM measurement.

## Smoke and evaluation protocol

Development run `20261102T113905Z-280b16d4` processed all 20 frozen pages
(10 English, 10 Arabic), with zero failed documents. OCR subprocess time totaled
20.6469463 seconds (1.03235 seconds per page); this excludes initialization,
preprocessing, normalization, integrity checks and evaluation.

Development-only text results (10 pages per language; not full-evaluation scores):

| Language | Raw CER | Normalized CER | Raw WER | Normalized WER |
|---|---:|---:|---:|---:|
| English | 10.91% | 8.96% | 24.21% | 24.21% |
| Arabic | 33.78% | 29.04% | 45.81% | 45.77% |

CER/WER are character/word error rates; lower is better. English reference-region
and Arabic page-content scopes differ. See the supplemental development report
under visualizations/tesseract-smoke-20261102/ for confidence intervals and figures.

The frozen evaluation run is `20261102T114008Z-48acf2b9`, on 745 English and
390 Arabic pages. It is currently incomplete with 437 saved predictions
(390 Arabic, 47 English) and zero OCR failures. Available system RAM dropped
below the shared 2-GiB floor; no full-evaluation score or selected run is claimed.
One earlier Windows directory rename denial was recovered by resuming and
reusing its verified cached prediction. The orphan temporary bundle is preserved.
Development scores are not evaluation scores.

The published partial bundles were rehashed and their predictions validated.
Largest sampled process/descendant RSS across those pages was 728,166,400 bytes
(694.4 MiB). This exceeds the original 0.5-GiB planning estimate; the estimate
was not a measured maximum. The generic 2-GiB floor still dominates the effective
preflight requirement. No model OOM was observed. TASK-013 is BLOCKED rather than
completed, and no official evaluation run is selected. All 390 Arabic evaluation
predictions are saved, but no partial result is presented as a completed full run.
Machine-readable development scores and partial coverage are in TESSERACT_RESULTS.json.

Resume the exact saved run after the live resource gate passes and the coordinator
restores TASK-013/tesseract to IN_PROGRESS through the validated tracker, removing
its model_block_reasons entry. Existing TASK-013 approval persists; no new approval
is needed to resume this same task:

```powershell
benchmark_suite\environments\tesseract\Scripts\python.exe -m benchmark_suite.cli resume --model tesseract --run-dir benchmark_suite/results/tesseract/20261102T114008Z-48acf2b9 --json
```

English text uses independently allocated reference regions. Arabic uses
page-content text derived from publisher Markdown. These scopes differ, and no
cross-language accuracy average is claimed. Source-document grouping is unknown;
page bootstrap intervals do not establish source-document independence.
Unsupported structures and absent annotations remain explicit statuses, not zeros.

## Reproduction on this machine

From the repository root, use the dedicated interpreter:

```powershell
benchmark_suite\environments\tesseract\Scripts\python.exe -m benchmark_suite.cli setup --model tesseract --json
benchmark_suite\environments\tesseract\Scripts\python.exe -m benchmark_suite.cli smoke --model tesseract --language both --json
benchmark_suite\environments\tesseract\Scripts\python.exe -m benchmark_suite.cli run --model tesseract --language both --mode full --json
```

For an incomplete run, use `resume --model tesseract --run-dir` with its exact
saved directory. Resume enforces the original config, code, environment and
hardware identity. Completed runs are immutable; use `evaluate` or `report` with
the saved run directory to recompute metrics without repeating OCR. Config/spec
contain local executable and asset paths; another machine requires explicit
path review, asset verification and its own recorded hardware preflight.

For a fresh isolated environment, create it with `python -m venv` and install
`-r benchmark_suite/configs/tesseract-requirements.txt`. Obtain the native engine
separately and verify the recorded executable/library identities. Download the
two language files using the immutable URLs in TESSERACT_ASSETS.json and verify
their checksums before placing them under the configured private tessdata path.

The supplemental figure/report generator is
`scripts/summarize_tesseract.py --run-dir RUN --evaluation-dir EVALUATION --output NEW_DIRECTORY`.
It verifies the evaluation checksums and completion identity before reporting.
Install configs/tesseract-report-requirements.txt into a separate reporting
environment or package directory; `--plot-libs DIRECTORY` selects the latter.
These plotting dependencies are separate from the pinned OCR environment.
Both PNG and SVG figures and a JSON summary are saved without overwriting runs.

Sources: [official language-data guidance](https://tesseract-ocr.github.io/tessdoc/Data-Files.html)
and [official fast models](https://github.com/tesseract-ocr/tessdata_fast).
