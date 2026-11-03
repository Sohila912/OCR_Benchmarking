# Docling + EasyOCR: TASK-014 actual-attempt record

Date: 2026-11-03 (Africa/Cairo). The user approved the next model and explicitly
requested an actual attempt, with any failure recorded in Markdown.

**Result: actual OCR inference failed with a CPU memory allocation error.**
TASK-014 is BLOCKED / BLOCKED_BY_HARDWARE for this tested configuration and
available-memory budget. There are zero successful pages and no accuracy scores.
The final retry used D: for its environment, models, caches, input copy and outputs.

## Configuration and scope

Selected candidate: Docling 2.143.1 + EasyOCR 1.7.2, standard layout/table
pipeline on CPU. Latest observed Docling is 2.146.0; it is not substituted.
The production Docling 2.80.0 environment is unchanged. The isolated trial
environment, model files and caches are under
`D:/OCR_Benchmarking_Assets/docling_easyocr/`.

Installed CPU Torch 2.14.1 / Torchvision 0.29.1 files are independently copied
into the isolated environment, not imported from a shared-site-package overlay.
The remaining dependencies are installed only there. Resolved dependency pins
and the runtime-copy provenance are recorded with the attempt evidence.

The trial targets one frozen English and one Arabic development image,
sequentially in separate disposable processes. It stops after a failed attempt.
English uses `en`; Arabic uses `ar,en` (EasyOCR supports English alongside Arabic).
Full-page OCR is enabled; GPU and optional external enrichment services are off.
Layout/OCR/table batch sizes are one. Original frozen image files are used.
Docling JSON and Markdown outputs are retained if conversion succeeds.
This is a feasibility attempt, not a completed benchmark or accuracy comparison.

## RAM and D: storage

Fresh usable RAM is 11.74 GiB; available RAM was 3.41 GiB. D: has
999,146,553,344 bytes free (about 999 GB decimal / 930.53 GiB). D: provides
storage for assets/caches; it does not increase physical RAM. No page-file,
driver, CUDA, WSL or global Windows setting is changed.

The previous 4-GiB process budget was an unmeasured planning estimate, not a
vendor minimum. The user's explicit request authorizes a bounded actual trial
despite that estimate. The official benchmark loading gate is not weakened.
The feasibility worker retains the 2-GiB available-RAM start floor and applies
a Windows job committed-memory limit, reduced if necessary
to leave 0.75 GiB free at launch. A supervisor records 100-ms RSS/private-memory
samples, stops the owned worker if system availability falls below 512 MiB, and
enforces a 20-minute wall limit. The job covers the worker and its descendants.
The first two trials requested at most 2.5 GiB. After the user requested closing
unrelated apps, the final retry requested up to 4 GiB; its actual available-memory
budget set the cap to 2.98784 GiB. A failure under these caps does not prove the
model cannot run with more available RAM or establish a universal model minimum.

Guard verification: an actual 128-MiB allocation was rejected under a 96-MiB
Windows job cap in a disposable self-test. No user application is closed.

## Outcome

The isolated environment installed successfully and `pip check` found no broken
requirements. Exact resolved pins are in configs/docling-easyocr-trial-requirements.txt.

First attempt: `20261103T084949Z-3b4e7736`. Imports succeeded and initialization
reached EasyOCR detector downloading. The owned worker was stopped after
617.11 seconds because that bulk transfer had not finished. Zero pages were
processed. The commit-memory cap was 1,953,288,192 bytes (1.82 GiB); sampled
peak RSS was 466,087,936 bytes (444.5 MiB), peak private memory 559,538,176 bytes,
and minimum observed system availability was 1,324,146,688 bytes. No model OOM
or inference exception was observed. This is a coordinator interruption during
asset acquisition, not an accuracy failure or a failed inference document.

A ranged-download fallback received HTTP 429 after about 30 seconds and was
not retried. A separate single-request detector prefetch completed in 323.30
seconds. Its 83,152,330-byte weight file matches the publisher's MD5
`2f8227d2def4037cdb3b34389dcf9ec1` and has SHA256
`4a5efbfb48b4081100544e75e1e2b57f8de3d84f213004b14b85fd4b3748db17`.
The native cached detector was also verified against that MD5.

Second attempt: `20261103T090228Z-ae16ec8b`, with the detector cached, UTF-8
worker output and a 30-second socket timeout. Initialization completed after
505.91 seconds, including remaining model downloads. Conversion of the first
English development image then failed with `ConversionError`, wrapping:

```text
DefaultCPUAllocator: not enough memory: you tried to allocate 1258291200 bytes.
```

The failure occurred in EasyOCR's CPU convolution during actual inference.
It requested about 1.26 GB decimal (1.171875 GiB) for one allocation. The job
cap was 2.50 GiB. Sampled peak RSS was 1,409,699,840 bytes and peak private
memory 1,588,551,680 bytes. No page completed successfully. EasyOCR uses its
default CPU dynamic quantization; the Docling OCR scale remains its default 3.0.

## Task Manager cleanup and final D: retry

The user explicitly requested ending unrelated RAM-consuming tasks. Task Manager
was opened and inspected. The UI's higher Windows integrity limited direct input,
so process termination used the native process API after checking names/parents.
Ended background Microsoft Edge and Bing Wallpaper, including only Bing's own
WebView descendants: 15 processes. Codex/project processes, Windows Search's
separate WebView processes, Windows services and security processes were retained.
The cleanup snapshot recorded available RAM increasing from 3,788,845,056 to
4,130,107,392 bytes (about 3.85 GiB); a later check showed 3.87 GiB. Task Manager
remained open. No global Windows or virtual-memory settings were changed.

Final attempt: `D:/OCR_Benchmarking_Assets/docling_easyocr/trials/20261103T092226Z-b1c73300/`.
The original frozen image was copied byte-for-byte to D: and its SHA256 checked
before conversion. The environment, caches, model files, processing input and
trial output/log directory were all on D:. Repository code and historical
evidence remain in the existing workspace on C:.

The cached pipeline initialized in 8.19 seconds. It reached OCR and failed on
the same 1,258,291,200-byte allocation. Actual job cap: 3,208,167,424 bytes
(2.98784 GiB). Sampled peak RSS: 2,669,887,488 bytes (2.49 GiB); sampled peak
private memory: 2,850,996,224 bytes (2.66 GiB). Minimum observed system available
RAM: 1,370,910,720 bytes (1.28 GiB). No supervisor low-RAM abort occurred.
The attempt ended in 20.88 seconds with exit code 1. This is an allocation
failure within the controlled commit-memory budget, not a disk-space failure
or evidence that all installed physical RAM was exhausted.

Two actual conversion attempts failed on the same unique English image. Zero
successful pages; Arabic was not attempted after the English failure. The first
trial was interrupted during asset acquisition and is counted separately.
No full evaluation, completion marker, selected run or accuracy result is created.
Model weights remain cached on D:; five model files total 628,166,987 bytes,
including both TableFormer files downloaded by the upstream loader. Their SHA256s
and exact cache paths are recorded in DOCLING_EASYOCR_RESULTS.json.

All 204 benchmark-suite tests and Ruff passed. The primary application environment
was not changed. A future trial needs more stable free RAM for the same settings,
or a separately disclosed lower OCR raster scale/configuration with its accuracy
implications. Stop here; TASK-015 has not been approved.

## Evidence and reproduction

- Hardware/source metadata: `hardware_observations/docling-easyocr-task014-20261103/`.
- Driver: `scripts/try_docling_easyocr.py`; Windows guard: `scripts/windows_job.py`.
- First two trial logs are in unique `results/docling_easyocr/feasibility/` directories;
  the final trial logs and inputs/outputs are on D: at the path above.
- Consolidated results, source-artifact hashes, model file hashes and RAM-cleanup
  evidence are in DOCLING_EASYOCR_RESULTS.json and RAM_CLEANUP.json in the dated
  hardware-observation directory.
- EasyOCR code/license: Apache-2.0. Docling code: MIT. Complete downloaded model
  asset identities and their separate terms must be recorded before official evaluation.

```powershell
.venv-ocr\Scripts\python.exe benchmark_suite/scripts/try_docling_easyocr.py --python D:/OCR_Benchmarking_Assets/docling_easyocr/venv/Scripts/python.exe --asset-root D:/OCR_Benchmarking_Assets/docling_easyocr --max-memory-gib 4
```

Sources: [EasyOCR 1.7.2 CPU use and language compatibility](https://github.com/JaidedAI/EasyOCR/blob/v1.7.2/README.md),
[Docling selected package metadata](https://pypi.org/pypi/docling/2.143.1/json),
[Docling dependency metadata](https://pypi.org/pypi/docling-slim/2.143.1/json).
