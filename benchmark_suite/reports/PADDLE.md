# Standard PaddleOCR checkpoints

Latest: [200-page evaluation subset](PADDLE_EVALUATION_200.md) completed with
200 conversions, zero failures and 199 text-scored pages. Reviewed 2026-11-04.
935 evaluation pages remain; the development checkpoint below is historical.

# Standard PaddleOCR: completed 20-page development checkpoint

2026-11-03 (Africa/Cairo), TASK-012. The user clarified to advance to the next
model. Standard PaddleOCR was the remaining untested model in the plan. Baidu's
quota-blocked work was stopped; its seven hosted successes remain saved.

## Measured result

**20/20 frozen development pages converted and were text-scored, with zero
conversion failures.** This is 100% conversion completion, not 100% OCR accuracy.

| Language | Pages scored | Normalized CER | Normalized WER |
|---|---:|---:|---:|
| English | 10 | 7.98% | 23.75% |
| Arabic | 10 | 56.29% | 77.29% |

CER/WER are error rates: lower is better. The tested model fits this laptop's
memory budget, but Arabic recognition quality is weak on this cohort. No claim
about all PaddleOCR variants or all Arabic/English documents follows from it.
English scores use independently allocated reference text regions; Arabic uses
publisher page-content text. Their reference scopes differ. English unassigned
prediction blocks are recorded separately in the per-page metrics. The shared
normalization is NFC plus whitespace normalization; Arabic diacritics/alef/hamza/
tatweel folds are disabled, matching the existing evaluator policy. Page-bootstrap
intervals are recorded in JSON; source-document independence is unverified.

Run wall time: **424.38 seconds** (7.07 minutes). Fresh measured inference totaled
416.44 seconds, mean 20.82 seconds/page. Each page starts a fresh bounded worker,
so shared-runner inference includes imports, checksum verification, model startup,
native prediction, native JSON export and local IPC. Native initialization and
predict timings are retained separately in raw worker output. This boundary must
be disclosed when comparing a persistent worker or remote GPU service.

Peak sampled process-plus-descendants RSS: **593,149,952 bytes (0.55 GiB)**.
Sampling is every 50 ms; RSS includes shared pages and can miss short peaks.
It is not an allocator peak. Inference used the CPU, with no GPU allocation.

## Exact configuration and D: setup

PaddleOCR 3.6.0, PaddlePaddle 3.2.2 CPU, PaddleX 3.6.1, NumPy 2.3.5. These existing
installed versions were preserved. Independent copies of their resolved package
closure (69 packages) were placed in `D:/OCR_Benchmarking_Assets/paddle/venv`;
production packages were not upgraded. Pinned worker dependencies are in
configs/paddle-worker-requirements.txt. The small coordinator launcher/pyvenv
metadata is under the ignored suite environment; coordinator libraries are on D:.
The catalog reuses the existing lightweight coordinator requirements file.

The selected standard OCR variant uses:

- `PP-OCRv5_mobile_det@0d63e78e2b680928f6b1747d76a08db6e645efb7`.
- `en_PP-OCRv5_mobile_rec@267c36e24c331595590fe7bd72bde2436fd286f2`.
- `arabic_PP-OCRv5_mobile_rec@33d91636a65dca87f5562cc48860332ae367ee1b`.

All model files were fetched from the official PaddlePaddle Hugging Face
repositories at those revisions and hashed. The three parameter files total
20,388,091 bytes. Code/model licensing is Apache-2.0 according to installed source
headers and publisher model metadata. See PADDLE_ASSETS.json for exact file hashes,
byte counts and the copied runtime versions. The Arabic-script recognizer is
selected only for Arabic pages; the English recognizer is selected for English.

CPU FP32, two threads, recognition batch one, MKLDNN disabled. Document orientation,
unwarping and text-line orientation models are disabled. Original images are copied
byte-identically onto D:; native detector preprocessing limits the maximum side
to 960. Native recognition confidence threshold is 0.0. No reference-guided crop,
reordering, text correction or per-page tuning was introduced.

Preflight measured 12,606,803,968 bytes usable physical RAM and 4,834,988,032
available bytes. Two preliminary English/Arabic trials completed with maximum
sampled RSS 535,896,064 bytes. The registered run retained a conservative 2-GiB
available-RAM floor, a <=2-GiB Windows committed-memory job cap, 768-MiB reserve
and a 512-MiB live system-available abort. These are suite controls, not vendor
minimum requirements. Only owned worker process trees are terminated on failure.

## Supported output and evaluation scope

Native text, line confidences, quadrilateral polygons/rectangles and pipeline
settings are retained in PaddleX JSON on D:. Normalization uses the original-image
pixel envelope of each native line, retaining the polygon and emission order.
Those coordinates permit the shared English text-region allocation. This standard
text detector/recognizer does not supply semantic layout classes, independent
reading-order structure, table HTML or chart understanding in this configuration.
Those metrics keep NOT_SUPPORTED/NOT_EVALUATED and coverage states rather than
fabricated scores. Native line ordering is not promoted into a semantic-order
capability. See per-page/category/structure CSVs for exact availability.

The canonical completed development run is
`results/paddle/20261103T120728Z-45bb7cec`; offline evaluation is
`results/paddle/evaluations/20261103T120728Z-45bb7cec/6fa4c89f1d73-0760d4a5`.
A reviewed report/chart and canonical run/evaluation copies are on
`D:/OCR_Benchmarking_Assets/paddle/reports/development-20261103-reviewed`.
Native worker outputs are under the D: root's `development_outputs` directory.
No original source/reference or previous model output was overwritten.

TASK-012 remains IN_PROGRESS because the full 1,135-page evaluation is pending.
It is not hardware-blocked. No official full-evaluation selected-run marker exists.
At the observed fresh-worker mean, a simple linear extrapolation is about 6.57
CPU hours; that is an estimate, not a measured full-run duration. This saved
checkpoint covers development only. Existing TASK-012 authorization persists.
No subsequent model/task was automatically started.

## Verification and reproduction

214 suite tests passed; Ruff passed; isolated dependency check found no broken
requirements. Native bilingual inference and the registered shared-runner full
20-page development path both ran successfully. New tests cover native confidence,
order and rotated polygon preservation, plus rejection of mismatched native arrays.
The generated figure was visually reviewed. Predictions and offline metrics have
checksummed manifests; raw inputs/models/environments remain outside Git.

```powershell
benchmark_suite\environments\paddle\Scripts\python.exe -m benchmark_suite.cli run --model paddle --language both --mode quick --json
benchmark_suite\environments\paddle\Scripts\python.exe -m benchmark_suite.cli evaluate --model paddle --run-dir benchmark_suite/results/paddle/20261103T120728Z-45bb7cec --json
.venv-ocr\Scripts\python.exe benchmark_suite/scripts/try_paddle.py --python D:/OCR_Benchmarking_Assets/paddle/venv/Scripts/python.exe --asset-root D:/OCR_Benchmarking_Assets/paddle --max-memory-gib 4
```

Historical incomplete runs require their original recorded source identity to
resume. Current registered source pins can change when shared worker code is
reviewed; saved immutable run identities remain untouched.

Sources: [official mobile detector](https://huggingface.co/PaddlePaddle/PP-OCRv5_mobile_det),
[English recognizer](https://huggingface.co/PaddlePaddle/en_PP-OCRv5_mobile_rec),
[Arabic recognizer](https://huggingface.co/PaddlePaddle/arabic_PP-OCRv5_mobile_rec),
[multilingual model documentation](https://www.paddleocr.ai/main/en/version3.x/algorithm/PP-OCRv5/PP-OCRv5_multi_languages.html).
