# Surya TASK-009 — blocked before installation

Assessed 2026-11-01 (Africa/Cairo), after explicit approval for Surya only.
**Task/model state: BLOCKED; reason: BLOCKED_BY_HARDWARE. Evaluation: NOT_EVALUATED.**
This is a preflight outcome, not a failed inference or a completed benchmark.
No model weights, packages or inference backend were downloaded/installed, no
framework/model was loaded, and no page was processed. No other model was started.

## Fresh laptop observation

The exclusive hardware collector saved a new observation at
2026-11-01T14:34:47+02:00 without replacing historical profiles.

| Item | Observed |
|---|---|
| CPU | Intel i7-1165G7, 4 cores / 8 threads |
| OS / interpreter | Windows 11 Pro build 26200, AMD64; existing Python 3.13.7 |
| Physical / available RAM | 8,311,836,672 / 737,169,408 bytes: 7.74 / **0.69 GiB** |
| Generic loading floor | 2 GiB available; shortfall about 1.31 GiB |
| GPU | NVIDIA MX350, 2 GiB dedicated VRAM, compute capability **6.1** |
| Free GPU memory / driver | 1,965 MiB at observation; driver 582.67 |
| Disk free | 34.33 GiB; disk is not the immediate blocker |
| Torch | 2.14.1+cpu; static metadata CUDA=null |
| Backend / package | llama-server not on PATH; surya-ocr not installed |
| WSL | docker-desktop and Ubuntu were stopped; neither was started |

Free resources are a snapshot, not a promise. No user application or service was
closed. CUDA 13.0 in NVIDIA-SMI is a driver ceiling, not evidence of a GPU-enabled
installed framework or compatible inference engine.

## Candidate and official-source recheck

The previously researched candidate remains **Surya 2, surya-ocr 0.22.1**, source
commit `3a70081f6a60013dab818c82ab99451aa290f389` (v0.22.1 tag). Its retained model
repository is datalab-to/surya-ocr-2 at
`3b3d4cdf88d6928b0acdc75181b13206ea67c4a3`. Metadata verifies the safetensors file
as 1,372,368,672 bytes with SHA256
`5755f82a997dd0b111964fa8b31cc2daef7aeb7a706bbd17d73d6a93ef3f723e`.
These are remote metadata checks, not downloaded weights or measured RAM needs.
[Pinned source](https://github.com/datalab-to/surya/tree/3a70081f6a60013dab818c82ab99451aa290f389),
[model metadata](https://huggingface.co/api/models/datalab-to/surya-ocr-2/revision/3b3d4cdf88d6928b0acdc75181b13206ea67c4a3?blobs=true).

Latest package metadata now reports **0.23.0**, and the current repository
documents **Surya 2.5**. This is version/variant drift since TASK-003; no automatic
upgrade or substitution was made. Any future switch must be explained and agreed
before creating a model environment or selecting assets.
[PyPI metadata](https://pypi.org/pypi/surya-ocr/json),
[current publisher README](https://github.com/datalab-to/surya/blob/master/README.md).

The pinned publisher documentation describes English/Arabic text, layout,
reading order and tables. Code is Apache-2.0; weights have modified AI Pubs
OpenRAIL-M terms, with research/personal use described as eligible. Full weight
terms must be reviewed before any future download/use; code licensing does not
replace the weight license. Dataset noncommercial restrictions also remain.
No publisher benchmark scores are presented as our own results.
[Pinned documentation](https://github.com/datalab-to/surya/blob/v0.22.1/README.md),
[pinned model card](https://huggingface.co/datalab-to/surya-ocr-2/blob/3b3d4cdf88d6928b0acdc75181b13206ea67c4a3/README.md).

## Blocking routes and dependency conflicts

1. **RAM:** current free RAM fails the suite's conservative 2-GiB safety floor.
   That floor is not a vendor minimum and passing it would not certify Surya.
   The existing Surya planning budget is 8+ GiB process headroom / 16+ GiB host
   RAM, explicitly an unmeasured engineering estimate. The laptop's entire
   physical RAM is below that process budget; merely closing enough applications
   to reach 2 GiB does not satisfy this selected conservative configuration.
2. **GPU serving:** current official vLLM needs compute capability >=7.5 and a
   Linux environment; MX350 provides 6.1. More free RAM, WSL or new drivers cannot
   change its GPU architecture/2-GiB VRAM. The present Torch build is CPU-only.
   [Official vLLM requirements](https://docs.vllm.ai/en/stable/getting_started/installation/gpu/).
3. **CPU serving/setup:** the pinned package documents llama.cpp/llama-server
   for CPU serving. No compatible server is established on PATH, and native
   Windows integration/asset conversion has not been validated here. Constructing
   the upstream inference manager can auto-start a backend; it was not imported
   or constructed. A detector-only run is not a substitute for Surya OCR.
   [Pinned backend documentation](https://github.com/datalab-to/surya/blob/v0.22.1/README.md#inference-backends).
4. **Main environment conflicts:** 0.22.1 metadata requires Transformers >=5.12.1
   versus installed 4.57.6, Pillow >=10.2,<11 versus 12.3.0, and huggingface-hub
   >=1.5,<2 versus 0.36.2. Other dependencies/assets are not fully resolved.
   No incompatible packages were installed into the application environment.
   [Versioned dependency metadata](https://pypi.org/pypi/surya-ocr/0.22.1/json).

Future setup needs an isolated, fully pinned compatible environment plus exact
backend/CPU-GGUF-and-projector assets or a compatible GPU server. The safetensors
file size alone is not the full CPU asset download or a memory bound. No complete
environment lock or executable adapter is claimed at this blocked checkpoint.

## Safe ways to revisit

- Prefer an already available machine with more RAM. The existing conservative
  CPU recommendation is 16+ GiB host RAM and enough measured free headroom for
  the selected backend, one page/concurrency at a time. Confirm the laptop's
  actual RAM upgradeability before assuming an upgrade is possible.
- A smaller/quantized CPU configuration may reduce memory, but needs explicit
  variant/precision approval, compatible pinned GGUF/projector/backend and a new
  measured budget. No claim is made that it fits this 8-GB laptop.
- If GPU execution is chosen, a reviewed Linux host with a modern compatible GPU
  is needed. The prior engineering starting profile is L4/A10G 24-GiB VRAM,
  32-GiB host RAM, 8 vCPUs and ample disk; this is a recommendation, not a vendor
  minimum. Prefer available/free resources first. Rental/storage/transfer can
  cost money and require approval of the actual environment/budget. None was
  provisioned. See MODEL_HARDWARE_COMPATIBILITY.md for all-nine-model remedies.

## Artifacts and checkpoint

Versioned evidence: [SURYA_BLOCKED.json](SURYA_BLOCKED.json). Original collector,
metadata and pinned text observations stay locally under
reports/hardware_observations/surya-task009-20261101, with SHA256 values recorded
in that evidence. A unique ignored results/surya/preflight/<id> stores the same
preflight, environment, source metadata, this report and null/not-evaluated metrics.
It is explicitly not a completed prediction run. No selected_run pointer or
fabricated predictions, error rates, latency or peak inference memory exists.

The dataset cohort and all source/reference bytes are unchanged. No executable
Surya adapter/config/environment was registered; the existing CLI keeps it blocked.
TASK-009 remains BLOCKED and the last completed task remains TASK-008. TASK-010
and all other models remain unapproved. Stop here; resolve Surya's execution plan
or explicitly authorize another model separately.
