# Baidu Unlimited-OCR 2: working hosted feasibility checkpoint

## Latest quota-reset continuation — 2026-11-04

**12 saved successful development pages: 6 English and 6 Arabic.** The free
quota reset allowed five additional completed conversions (three Arabic and two
English); seven earlier successes were checksum-verified and reused. All 12
saved successes report `truncated=false`. The same model, request parameters,
frozen images and inspected hosted app revision were retained.

| New page | Server-reported elapsed | Client request wall | Tokens |
|---|---:|---:|---:|
| Arabic, development position 8 | 83.2 s | 129.46 s | 1,418 |
| English, position 9 | 46.3 s | 70.95 s | 852 |
| Arabic, position 10 | 33.8 s | 56.44 s | 620 |
| English, position 11 | 11.6 s | 23.00 s | 186 |
| Arabic, position 12 | 40.2 s | 80.22 s | 728 |

The next English request was quota-denied: **90 seconds requested versus 78
seconds remaining**. The service advised retrying in **23:54:01** at rejection.
This is a free-service quota limit, not an OCR generation failure or laptop RAM
error. Eight development pages remain: one denied request and seven not attempted
in this continuation. No further requests were issued after the quota rejection.
No paid subscription, quota workaround or alternate account was used.

New trial: `D:/OCR_Benchmarking_Assets/baidu_unlimited_ocr/demo_trials/20261104T125515Z-b748224f`.
Reviewed readable outputs, native responses, copied inputs, timings CSV and SHA256
manifest: `D:/OCR_Benchmarking_Assets/baidu_unlimited_ocr/reports/development-20261104-12pages`.
The hosted app revision remained unchanged in before/after metadata checks.
The served model-weight revision and remote peak RAM/VRAM remain unverified.
Conversion completion alone is not an accuracy score. No new CER/WER or official
full-evaluation score is claimed; development and full evaluations remain incomplete.

TASK-017 returns to BLOCKED: HOSTED_FREE_QUOTA_EXHAUSTED. Its existing authorization
persists. A later continuation should use this newest trial as `--reuse`, preserving
all 12 verified outputs. Existing local login was used without logging credentials.
Final validation: 56 reuse/tracking tests passed; live tracker validated. No inference
code, source/reference documents or model parameters changed.

```powershell
.venv-ocr\Scripts\python.exe benchmark_suite/scripts/try_unlimited_ocr_demo.py --development --reuse D:/OCR_Benchmarking_Assets/baidu_unlimited_ocr/demo_trials/20261104T125515Z-b748224f --authenticated
```

Earlier seven-page and two-page checkpoints below are historical.

## Latest continuation: 7 successful pages; free account quota exhausted

The user requested more pages and then configured a local Hugging Face login.
The continuation targeted the same 20 frozen development images, alternating
English/Arabic and reusing verified successes instead of spending quota on them.
Native parameters and inspected demo deployment stayed the same.

The anonymous continuation completed one additional English page (9.0 seconds
server elapsed), then the next Arabic request hit the anonymous quota. After
login, the authenticated continuation reused all three prior successes and
completed four more pages: Arabic 34.8 s, English 51.8 s, Arabic 48.9 s and
English 100.4 s. Every saved success reported truncated=false.

**Total saved: 7 successful pages (4 English, 3 Arabic).** This is five additional
successes beyond the original two-page checkpoint. The next Arabic request was
rejected before model execution with the service message:
`You have exceeded your free ZeroGPU quota (90s requested vs. 59s left).`
It advised retrying in `23:55:25` at the time of rejection (about 24 hours).
This is a service quota denial, not a failed OCR generation or laptop RAM error.

Of the 20 targets, 7 succeeded, 1 was quota-denied in this continuation and 12
were never attempted. **13 remain**, including the denied page. Historical
anonymous quota errors are preserved separately rather than counted as extra
unique failed documents. No quota workaround, extra account, paid subscription,
GPU rental or model substitution was used.

Authenticated trial:
`D:/OCR_Benchmarking_Assets/baidu_unlimited_ocr/demo_trials/20261103T114536Z-118e8f19`.
Reviewed native outputs, readable displays, per-page timing CSV and SHA256
manifest: `D:/OCR_Benchmarking_Assets/baidu_unlimited_ocr/reports/development-20261103-7pages`.
Original two-page and anonymous continuation artifacts remain intact.

Use the following after quota resets and TASK-017 is active in the tracker:

```powershell
.venv-ocr\Scripts\python.exe benchmark_suite/scripts/try_unlimited_ocr_demo.py --development --reuse D:/OCR_Benchmarking_Assets/baidu_unlimited_ocr/demo_trials/20261103T114536Z-118e8f19 --authenticated
```

The helper follows and validates the saved reuse chain, checks original input
hashes and completion/truncation fields, and requires the same inspected app
revision. Authentication reads the existing local Hugging Face credential; it is
never printed or saved in request/report files. Failed requests are not reused
as successes. Two new tests cover chained reuse, corrupt source rejection and
cycle detection; all 212 suite tests and Ruff pass.

TASK-017 is currently BLOCKED with reason HOSTED_FREE_QUOTA_EXHAUSTED. The
20-page development and full 1,135-page evaluations are incomplete. The hosted
weight revision/remote resource-telemetry limitations below still apply. No OCR
accuracy or cross-model rank is inferred from seven successful conversions.

The original two-page checkpoint below is retained as history.

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
