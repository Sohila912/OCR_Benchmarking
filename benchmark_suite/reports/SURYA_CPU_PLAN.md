# Surya CPU preparation for the upgraded laptop

Prepared 2026-11-02 (Africa/Cairo). Proposal only; not an executable or approved
environment. TASK-009 is approved, but an alternative execution environment still
requires user approval under Task_codex.txt. No installation or inference occurred.

## Resource evidence

Latest collector: hardware_observations/surya-task009-20261102-recheck/HARDWARE_PROFILE.json.
Physical RAM is 12,606,803,968 bytes (11.74 GiB); available RAM was
1,111,896,064 bytes (1.04 GiB). The unchanged 2-GiB generic floor still blocks
loading. That floor is not proof of Surya compatibility. The earlier 8-GiB process
budget is an unmeasured planning estimate, not a documented model minimum.
The MX350 remains 2-GiB VRAM / compute capability 6.1.

D: is NTFS with about 930.53 GiB free. Storage is sufficient for preparation;
additional disk capacity cannot substitute for RAM or compatible GPU hardware.
Keep the existing repository, frozen datasets and Python environment on C:.
Moving a Windows virtual environment can break interpreter and launcher paths.
Use D:/OCR_Benchmarking_Assets for future model assets, caches and backend binaries;
this directory has not been created and no files have been moved.

## Proposed CPU setup

- Retain Surya 2 / surya-ocr 0.22.1; do not substitute Surya 2.5 or an older model.
- Use an isolated Python environment and a pinned Windows CPU llama-server build.
  Resolve dependency pins and native integration before installing. Leave the
  application environment unchanged.
- Proposed settings from the pinned Surya source:
  TORCH_DEVICE=cpu, SURYA_INFERENCE_BACKEND=llamacpp,
  SURYA_INFERENCE_PARALLEL=1, LLAMA_CPP_NGL=0,
  LLAMA_CPP_NO_MMPROJ_OFFLOAD=true, SURYA_INFERENCE_KEEP_ALIVE=false.
- Retain default context/token and image-resolution settings initially. Do not
  shrink context just to fit memory: truncation would invalidate comparisons.
- Use the publisher's GGUF model and multimodal projector. Before downloading,
  verify the repository revision, file sizes/hashes, precision, license and
  backend compatibility. Do not assume GGUF means a particular quantization.
- Store downloads and model caches on D: using explicit environment variables
  scoped to the model process, not global Windows settings. Record actual paths
  and immutable asset identities in each run.
- Start with one development page after a new memory preflight. Measure process
  and descendant RAM, latency, raw output and errors. Only proceed to the frozen
  evaluation if output schema and resource use are valid. Do not start another model.

## Remaining gates

1. Free sufficient RAM and recheck; 1.04 GiB available is not enough to begin.
2. Approve the proposed CPU llama.cpp execution environment.
3. Resolve/pin the Windows binary, GGUF/projector pair and isolated dependencies;
   determine their complete download/storage budget before large downloads.
4. Review asset license and obtain any required large-download approval.
5. Pass model-specific preflight and a measured one-page smoke run before ranking.

The publisher documents CPU llama.cpp support, but successful integration and
memory fit on this particular Windows laptop remain unverified. Metadata access
to Hugging Face timed out during this preparation; asset identities and total
download size are deliberately unresolved rather than invented.

Sources:
- https://github.com/datalab-to/surya/blob/v0.22.1/README.md#inference-backend-prerequisites
- https://github.com/datalab-to/surya/blob/v0.22.1/surya/settings.py

