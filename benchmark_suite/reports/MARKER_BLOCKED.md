# Marker TASK-011: blocked preflight

Assessed 2026-11-02 (Africa/Cairo). The user explicitly approved Marker.
TASK-011 is BLOCKED / BLOCKED_BY_HARDWARE. Evaluation is NOT_EVALUATED.

## Candidate and backend

Retain marker-pdf 2.0.0, Surya 2 backend, with no optional external LLM.
Fresh PyPI metadata reports latest version 2.1.0; it was not substituted.
Pinned 2.0.0 requires surya-ocr >=0.22.1,<0.23.0, Transformers >=5.12.1,<6,
Pillow >=10.1.0,<11 and Torch >=2.7.0,<3. Existing shared Transformers 4.57.6
and Pillow 12.3.0 conflict; an isolated resolved environment would be needed.
Marker and Surya are not installed in the inspected environment. Benchmark
adapter/environment registration remains pending. Code is Apache-2.0; dependent
weights have separate modified OpenRAIL-M terms requiring asset-specific review
before download. Exact complete asset identities and download budget are unresolved.

The pinned README documents CPU fast mode and GPU balanced mode. Both use the
Surya VLM for scanned pages. Fast mode does not remove the scanned-page model
requirement. The server is vLLM/Docker on NVIDIA GPUs and llama.cpp elsewhere.
The existing Surya CPU binary/asset integration remains unresolved. No backend
was installed or started. Disabling OCR would omit the requested recognition
work and is not a valid scanned-page benchmark. No OCR-disable fallback was used.

## Resources and decision

Usable RAM: 11.74 GiB. Available: 3,626,500,096 bytes (3.38 GiB).
The generic 2-GiB floor passes, but the retained 10-GiB process planning budget
does not. This is an unmeasured suite engineering estimate, not an official
minimum or a measured impossibility result. Model-specific memory fit remains
unverified. No installation or memory-fit trial was attempted.

MX350 has 2 GiB VRAM and CC 6.1. The planned vLLM GPU route remains unsuitable
under the existing Surya assessment (CC >=7.5 and a compatible Linux runtime;
native Windows vLLM is unsupported). Driver updates cannot change GPU architecture.
About 36.12 GiB disk is free, above the estimated 12-GiB storage budget plus
6-GiB reserve. Storage is not the current blocker.

## Outcome and next action

No installations, weight downloads, framework imports, initialization or inference.
Zero processed documents; accuracy, latency and peak model RAM/VRAM are unmeasured.
No selected run or fabricated scores. Production dependencies and frozen data
remain unchanged. TASK-011 is blocked, not completed or inference-failed.

For a future CPU trial, provide sufficient available headroom against the retained
10-GiB planning budget, resolve a pinned isolated environment and Surya llama.cpp
assets, then measure one development page. A 24-32-GiB host is an engineering
recommendation, not a vendor minimum. A reviewed Linux A10G/L4 host with 24 GiB
VRAM and 32 GiB RAM is an alternative planning profile; cloud use may incur costs.
No alternate environment or paid service was provisioned.
Stop here. TASK-012 standard PaddleOCR requires separate approval.

## Evidence and sources

Fresh local evidence: `hardware_observations/marker-task011-20261102/` contains
HARDWARE_PROFILE.json, OFFICIAL_METADATA.json, pinned_readme.txt and pinned_settings.txt.
MARKER_BLOCKED.json records evidence hashes. Only source/metadata was downloaded.

- [Pinned Marker 2.0.0 README](https://github.com/datalab-to/marker/blob/v2.0.0/README.md)
- [Pinned dependency metadata](https://pypi.org/pypi/marker-pdf/2.0.0/json)
- [Latest package metadata](https://pypi.org/pypi/marker-pdf/json)
- [vLLM GPU installation requirements](https://docs.vllm.ai/en/stable/getting_started/installation/gpu/)
