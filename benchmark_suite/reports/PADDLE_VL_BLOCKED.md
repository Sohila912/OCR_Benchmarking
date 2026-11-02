# PaddleOCR-VL TASK-010: blocked preflight

Assessed 2026-11-02 (Africa/Cairo). The user explicitly approved TASK-010.
Status: BLOCKED / BLOCKED_BY_HARDWARE. Evaluation: NOT_EVALUATED.

The selected candidate remains paddleocr 3.7.0 and PaddleOCR-VL-1.6-0.9B
with PP-DocLayoutV3. Fresh PyPI metadata confirms 3.7.0 is still latest.
Publisher metadata confirms retained model revision
c5630abae1d940eafe0697512a0325494b02ab42 and Apache-2.0 license.
The main weight file is 1,917,255,968 bytes, excluding layout assets and
dependencies. Existing shared PaddleOCR 3.6.0 and CPU Paddle 3.2.2 remain unchanged.

## Resource decision

The fresh profile reports 11.74 GiB usable RAM and 3.14 GiB available
(3,373,334,528 bytes). The generic 2-GiB loading floor passes. Available RAM
is below the retained 8-GiB CPU process planning budget. This is an unmeasured
engineering estimate, not a publisher minimum or proof that the model cannot
ever fit on this laptop. No memory-fit trial was performed.

The MX350 has 2 GiB dedicated VRAM and compute capability 6.1. Official
Paddle/Transformers GPU requirements specify CC >=7.0. The GPU path is
incompatible. Driver/CUDA/WSL changes cannot change GPU architecture.
x64 CPU inference is documented, but current headroom fails the planned budget.
Free disk is about 36.12 GiB and exceeds the estimated 12-GiB storage budget
plus 6-GiB reserve; storage is not the current blocker.

## Outcome and next action

No installations, weight downloads, framework imports, model initialization or
inference occurred. Zero documents processed; accuracy, latency and model peak
memory remain unmeasured. No selected run or scores are created. The benchmark
adapter and isolated pinned environment remain unimplemented. Frozen datasets
and production source are unchanged.

Before a future CPU trial, recheck with at least the retained 8-GiB available
planning headroom, resolve isolated pins and measure one development page.
A 16-32-GiB CPU host is an engineering recommendation, not a vendor minimum.
A reviewed Linux A10G/L4 24-GiB GPU host with 32 GiB RAM is another engineering
starting point. Paid hosting may incur costs; none was provisioned.
No alternate environment was attempted. Stop here: TASK-011 Marker requires
separate approval. TASK-010 is blocked, not completed or inference-failed.

## Evidence

Fresh profile and metadata: `hardware_observations/paddle-vl-task010-20261102/`.
Metadata requests downloaded JSON only, not model weights.

- [Official hardware matrix and CPU guide](https://www.paddleocr.ai/main/en/version3.x/pipeline_usage/PaddleOCR-VL.html)
- [Publisher model card](https://huggingface.co/PaddlePaddle/PaddleOCR-VL-1.6)
- [Pinned package metadata](https://pypi.org/pypi/paddleocr/3.7.0/json)
