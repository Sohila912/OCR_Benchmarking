# Final OCR and interface verification

## PaddleOCR-VL: exact remaining blocker

The installed Docker runtime is PaddlePaddle 3.2.2 (CPU), PaddleOCR 3.6.0 and PaddleX 3.6.1. Both local PaddleOCR-VL-1.6 and PP-DocLayoutV3 checkpoints are mounted; missing downloads are not the current failure.

The VL safetensors checkpoint contains 958,588,736 BF16 parameters (1,917,255,968 bytes on disk). The installed PaddleX native loader chooses float32 when BF16 is unavailable on the device. Float32 parameters alone require 3,834,354,944 bytes. Docker exposes 3,968,045,056 bytes total, before loading overhead, inference buffers, other containers and model assets. A prior real initialization was OOM-killed (exit 137); lowering the guard would repeat that risk.

The CPU memory guard now returns an actionable public resource error to extraction and benchmarking. CPU-only Paddle configured as GPU also returns a clear runtime incompatibility message. Initialization messages distinguish missing dependencies and missing assets/renderer from other runtime failures without disclosing private paths. Prediction results accept iterators as well as lists, preserving the normalized schema.

**Paddle has not passed real inference on this machine.** Use a host/container with more memory and leave sufficient host RAM; the configured 6 GiB floor is a safety guard, not a tested peak-memory guarantee. This host has only about 7.7 GiB visible RAM. Do not assign all of it to Docker. GPU execution requires compatible hardware, drivers and Paddle GPU runtime; the current image is CPU-only. No model was replaced, quantized or downloaded.

## Interface changes

- Shared lightweight CSS for typography, cards, spacing, sidebar and native controls.
- Dashboard hero and honest successful-output counts.
- Four-step document workflow tied to actual upload/selection/results state; existing real processing status/progress retained.
- Friendly provider result tabs and plain Markdown source text areas, avoiding lazy syntax-highlighter loading.
- Interactive native Altair CER/WER and processing-duration charts using backend measurements only; rates can exceed 100%.
- Provider cards show API diagnostic states and explanations. API model diagnostics replace misleading frontend-local model-path checks.
- Existing escaped Unicode-safe insertion/deletion/substitution diffs, previews, history and exports remain intact.

No new dependency, OCR formula, saved-result mutation, or normalized schema change.

## Git hygiene

No tracked model checkpoint, database or .env file was found by the extension/path audit. Six legacy PDFs are already tracked under runtime/uploads (Tweet_20, Tweet_22, Tweet_23, Tweet_24, Tweet_25 and crowd_1). They were preserved. Review these before publishing; ignoring runtime does not remove files already tracked. New synthetic verification artifacts and browser profiles stay ignored. No commit or push was made.

Verification results are recorded below after the final checks complete.

## Final results (2026-10-15)

- Docker API and frontend rebuilt and started healthy.
- Real synthetic one-page PDF: Tesseract success (1.40s), Docling success (75.00s), Qwen/Ollama success (273.75s). All three returned CER=0, WER=0, exact match=true for this small fixture; this is not a general quality claim.
- Paddle request failed safely with provider_resources_unavailable and the measured 3.7 GiB capacity/6 GiB safety floor; real Paddle inference remains unverified.
- Synthetic UTF-8 Markdown benchmark upload, persistence, metadata-only history retrieval and same-document historical comparison passed; micro CER/WER=0.
- Full automated suite: 163 passed, three upstream deprecation warnings. A concurrent run during model inference had three 3-second Streamlit timeouts; rerunning after inference passed completely in 18.06s.
- Ruff passed; Git whitespace check passed.
- Fresh Edge profile: rebuilt Docker comparison rendered 65,600-character Arabic/Markdown reference and 65,609-character OCR output; two missing and two inserted colored regions covered deletion/insertion/substitution. Uploaded markup remained literal; no script execution. Zero JavaScript errors, zero syntax-highlighter requests with that module explicitly blocked; reload passed. Native HTML regions were scrolled into view to trigger Streamlit lazy mounting.
- Actual dashboard rendered in fresh Edge at 1440x1000 with no JavaScript errors and was visually inspected.
- Upload, results, exports, history and rerun behavior are covered by Streamlit integration tests with mocked OCR; the separate Docker acceptance used actual OCR as reported above. No customer document was used.

### Files touched for this focused pass

OCR/errors.py, OCR/app.py, OCR/benchmark_api.py, OCR/resources.py, OCR/providers/paddle_vl.py; frontend/design.py (new), frontend/app.py, frontend/views.py, frontend/ground_truth.py; tests/test_public_diagnostics.py (new), tests/test_providers.py; README.md and this report. Other working-tree changes predate this pass.
