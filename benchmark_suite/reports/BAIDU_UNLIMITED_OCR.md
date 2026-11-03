# Baidu Unlimited-OCR 2: working hosted feasibility checkpoint

2026-11-03 (Africa/Cairo), TASK-017. The user identified
https://github.com/baidu/Unlimited-OCR as the intended free implementation.
This replaces the earlier unresolved Baidu Cloud API assumption. No Baidu Cloud
credentials, subscription or paid API were used. The preceding Granite checkpoint
was pushed and remotely verified at `512fd4aaed7b3325348c255dc4afaa21b0a663d3`.

## Actual result

The repository-linked public Hugging Face demo completed the same frozen first
English and Arabic development images. Neither returned response was marked
truncated. This is **two successful hosted conversions**, not an accuracy score
or a completed 20-page/full evaluation.

| Language | Server-reported elapsed | Client request wall | Generated tokens | Returned Markdown characters |
|---|---:|---:|---:|---:|
| English | 25.9 s | 29.45 s | 366 | 964 |
| Arabic | 53.7 s | 57.07 s | 806 | 1,950 |

The Arabic output contains recognized Arabic text; the English output includes
text and mathematical notation. Recognition correctness and layout/table quality
have not been quantitatively evaluated. The demo's returned Markdown still
contains BLOCK/FORK grounding markers. Native output is preserved unchanged;
`display.md` only removes those wrapper markers for reading and is not scored.
No CER/WER, semantic layout F1, TEDS, chart score or cross-model rank is claimed.

## Reproducibility and execution boundaries

GitHub source inspected at `ea42e6d15ff93fdd0e8041fc0ac70880513453d3`.
The repository currently defaults to version 2. Version 1 metadata/source was
also inspected, but version 1 was not executed or silently substituted.

Model metadata/config/source inspected at
`baidu/Unlimited-OCR-2@0480966938291445591f69f08a13b041c073a96a`.
Its two BF16 checkpoint shards total 6,688,305,576 bytes; SHA256s and parameter
counts are recorded in the local metadata evidence. Code/model licensing is MIT
according to the published license and model card.

The hosted application deployment was
`78c27d176793811cf8b5e74b62ceb04dd773c29a`, unchanged in before/after metadata
checks. Space runtime metadata reported ZeroGPU `zero-a10g`. The inspected app
loads the model by repository name without pinning its weight revision; the
actual served weight commit and runtime package build are **unverified**. These
hosted results are consequently feasibility evidence, not an immutable official
benchmark run. Demo availability, anonymous access and free quotas can change.

The original public images were copied byte-identically onto D: and uploaded
anonymously to the repository-linked endpoint. Two single-page calls used native
defaults: empty instruction, auto image mode and max_page_tokens=20000. No
production packages were installed or changed. The helper uses the existing
requests package and validates active TASK-017 authorization before uploading.

Server elapsed time is supplied by the demo; client wall includes upload,
queueing/network and stream collection. No remote allocator/RAM/VRAM telemetry
was exposed. Remote peaks remain null. Do not compare these times directly with
CPU-only models without describing the different hardware and timing boundaries.

## Local route and D: storage

The laptop profile records 12,606,803,968 bytes usable RAM, 3,521,916,928 bytes
available at preflight, and an MX350 with 2 GiB dedicated VRAM. A tiny local CUDA
capability probe returned `Torch not compiled with CUDA enabled` in the existing
D: CPU runtime (Torch 2.14.1+cpu). This was not a model-inference attempt.

The published local example uses BF16 CUDA. The pinned multimodal source also
contains explicit `.cuda()` calls on image masks. The checkpoint weight payload
alone exceeds the laptop's GPU memory; FP32 expansion of the BF16 parameters
alone exceeds its total usable physical RAM. These are weight-derived lower
bounds, not measured peak requirements. Installing a CUDA build would not fix
insufficient VRAM. No unsupported CPU port/quantization was silently introduced,
no full weights were downloaded, and no local model OOM was fabricated.

Source/config/metadata, trial inputs, requests, event streams, raw output,
Markdown and readable displays are stored under:
`D:/OCR_Benchmarking_Assets/baidu_unlimited_ocr/demo_trials/20261103T112846Z-0540b88f`.
A reviewed report copy is under `reports/checkpoint-20261103` on the same D: root.
The 1-TB disk provides storage, not additional RAM or VRAM.

TASK-017 remains BLOCKED for a formal local/pinned benchmark, with successful
hosted feasibility retained. No 20-page development run, full 1,135-page run or
selected official run exists. A supported local port or an available reproducible
GPU environment is needed for the formal task. TASK-018 comparison is not started;
missing models/results must never be ranked as zeros.

## Reproduction

With active TASK-017 status/authorization and anonymous demo availability:

```powershell
.venv-ocr\Scripts\python.exe benchmark_suite/scripts/try_unlimited_ocr_demo.py
```

Each invocation creates a new D: trial; failures and truncation are retained.
The helper makes no paid calls and stops at the first unsuccessful request.
Source/evidence/response hashes and all exact trial outcomes are in
BAIDU_UNLIMITED_OCR_RESULTS.json. Hardware and registry/tracker validation are
read-only; no downloaded model code was executed locally.

Sources: [user-selected repository](https://github.com/baidu/Unlimited-OCR),
[pinned model card](https://huggingface.co/baidu/Unlimited-OCR-2/blob/0480966938291445591f69f08a13b041c073a96a/README.md),
[linked free demo](https://huggingface.co/spaces/baidu/Unlimited-OCR-2),
[pinned demo source](https://huggingface.co/spaces/baidu/Unlimited-OCR-2/blob/78c27d176793811cf8b5e74b62ceb04dd773c29a/app.py).
