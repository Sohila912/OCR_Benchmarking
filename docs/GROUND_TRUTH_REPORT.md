# Ground-truth benchmarking and Docker provider report

Date: 2026-10-15. The existing application, provider registry and OCRResult schema
1.0 were retained. No model was replaced, no weights were downloaded, and no
commit or push was made.

## OCR provider diagnostics

The actual registry is `paddle_vl`, `docling`, `tesseract`,
`qwen_ollama`. The original core image installed none of `paddleocr`,
`paddle`, `docling`, `torch` or `ollama`. Compose supplied
no local model paths/mount, and the default Ollama URL targeted container localhost.
A successful HTTP health check did not test any OCR engine.

| Provider | Original failure and root cause | Fix | Actual verification | Remaining requirement |
|---|---|---|---|---|
| Tesseract | Already initialized successfully; native CLI and language packs were present | Preserve implementation; add inference evidence and timing metadata | Real Docker PDF extraction passed; final synthetic CER/WER 0, exact match true, 0.557 seconds | Required language packs must match the document |
| Docling | `Set OCR_DOCLING_ARTIFACTS_PATH to an existing, populated local model directory.` The package and Torch were also absent | Full CPU API dependencies, CPU torchvision, explicit read-only host assets and persistent writable cache | Real Docker initialization and extraction passed. Final synthetic CER/WER 0, exact match true; 23.916 seconds total, 16.090 setup, 7.825 extraction. First cold attempt took 56.625 seconds | Complete local layout/table assets; asset revision remains unknown unless configured |
| PaddleOCR-VL | `Set OCR_PADDLE_VL_MODEL_DIR to an existing, populated local model directory.` PaddleOCR/Paddle were absent too | Install PaddleOCR 3.6.0/Paddle 3.2.2 CPU dependencies; mount VL and PP-DocLayoutV3 assets. Add an early memory-capacity guard | Actual loading reached the local checkpoint, then Docker reported `OOMKilled=true`, exit 137. With the final guard, the benchmark records `provider_resources_unavailable` and the API remains healthy. No accuracy score was assigned | Successful inference remains unverified. Docker exposes 3.696 GiB, insufficient in the observed run. The CPU guard defaults to a configurable 6 GiB floor; this is not a proven sufficient capacity. Use a higher-memory environment and rerun actual inference |
| Qwen/Ollama | `No module named 'ollama'`; container-local URL would also fail | Include client, use host.docker.internal, verify server and exact installed tag, forward CPU/context/image/timeout preferences, record model digest | Host tags confirmed `qwen2.5vl:3b`; localhost refused connection. Real CPU Docker extraction through the host server passed. Synthetic CER/WER 0, exact match true; 225.100 seconds total | Existing host Ollama server and installed vision model must remain available; CPU execution can take minutes |

The host has approximately 7.7 GiB visible physical RAM. Do not allocate 8 GiB
to Docker on this host. The generic guard's suggested larger testing budget
requires a host with enough RAM for Windows and other processes as well. No
host/WSL memory settings were changed. GPU execution was not verified.

All scores above concern the generated 14-character reference `OCR test 12345`,
not dataset-level accuracy or provider rankings. Timing includes model setup and
memory release; extraction can include internal lazy loading. It excludes HTTP
transport and queueing. Unknown model revisions are null rather than invented.

The ML API image installs CPU Torch/torchvision and resolves core/model requirements
together. `pip check` passed; the combined resolver selected compatible
pydantic-settings 2.15.0 while retaining python-dotenv 1.2.1. The UI image omits
heavy model packages. Build/startup do not provision weights. Existing
`models/` assets mount read-only; `ocr-model-cache` persists writable caches.

`GET /providers/diagnostics` and Settings show missing dependencies,
unconfigured paths, unavailable models, unreachable servers, initialization or
inference failures, insufficient resources, and configured-but-untested engines.
**Ready requires complete actual extraction in the current API process.** Known
successful evidence survives model unloading within that process, with lifecycle
shown separately; it resets after API restart. Preflight never establishes Ready.

## Benchmarking

- Explicit PDF + UTF-8 Markdown pairing, filename/size display, original source
  preview, 2 MiB reference limit, strict decoding and empty/NUL validation.
  References are ground truth and never processed through OCR.
- Backend `OCR/evaluation.py` uses Jiwer 4 Levenshtein edit counts. CER/WER
  are total substitutions + deletions + insertions divided by reference
  character/word counts. Rates may exceed 1; empty normalized references are
  rejected, and empty predictions score as deletions.
- Normalized exact match and character similarity
  `1 - edits / max(reference length, output length)`. Similarity is defined
  explicitly and is not an official accuracy percentage.
- Shared configurable NFC/NFKC/none, whitespace, line breaks, case folding,
  punctuation, raw Markdown and conservative plain-text Markdown modes.
  Defaults preserve Arabic letters/diacritics, case and punctuation.
  Both inputs use identical settings; originals are unchanged.
- Plain-text conversion handles common heading/list/emphasis/link/code-fence
  syntax. It is not a rendered-document parser; inspect complex Markdown/HTML
  and tables. Raw mode intentionally scores formatting differences.
- Measured setup/extraction/total service durations, model/package versions,
  Qwen digest, method version and normalization are exported and persisted.
- Safe line-aligned insert/delete/substitution inspection is limited to the
  first 12,000 normalized characters and 100 displayed changes. Exact scores
  cover full text. Uploaded Markdown is displayed as text/code, not HTML.

## Dataset support and historical comparison

The backend catalogs the actual 32 English, 30 Arabic and 10 mixed references
and their repository PDFs. Suggestions require explicit user confirmation.
Mixed-case `Invoice_5.md` / `invoice_5.pdf` associations work on Linux.
Existing datasets/outputs mount read-only and remain unchanged.

A selected dataset document can be rerun. Compatible saved OCR Markdown files
can be validated and rescored into new `legacy:<folder>` records. Their
original inference duration, timestamp and model revision are not reconstructed.
The new evaluation timestamp describes rescoring. Invalid mappings, traversal,
encoding and oversized imports are rejected. Existing CLI evaluators and their
historical language-specific normalization/formulas remain unchanged.

History filters provider, dataset and date; supports details, selected-run
comparison, JSON/CSV export and deletion. It displays at most the latest 2,000
filtered rows. Comparisons identify matching PDF/reference hashes and evaluation
policies. Provider/model/package/digest/dataset/policy groups remain distinct.
Micro CER/WER use total edits divided by total reference units, with evaluated
document counts. The newest selected result per document/reference/group is
used; failed outputs are excluded and coverage is visible. Different datasets
or policies are not presented as equivalent.

## Persistence and retention

`OCR/benchmark_store.py` uses standard-library SQLite at
`runtime/benchmarks.sqlite3`, configurable with `OCR_BENCHMARK_DB`. Docker
stores it on `ocr-runtime`. No external database/service was added.

Records include run/batch IDs, dataset association, PDF/reference hashes,
provider/model/runtime metadata, UTC timestamp, status/error, edit counts,
reference lengths, metrics, timing, normalization and method version. Only
metrics/provenance are retained. Reference text, OCR text and customer PDFs are
not stored in benchmark history.

Runs are saved as in progress before OCR, then completed with success/failure.
A restarted single API worker marks interrupted runs failed with no score.
Completed records cannot be overwritten; reruns always create new IDs. Tests
cover this recovery and immutability behavior.

Benchmark uploads are deleted in request cleanup regardless of extraction
retention settings. Generated benchmark-prefixed files from interrupted jobs
are removed at single-worker startup; unrelated existing uploads are preserved.
Text remains in the Streamlit session until cleared; export detailed reports
before clearing it. Default metrics retention is 90 days, configurable with
`OCR_BENCHMARK_RETENTION_DAYS`, applied on save/history access. Individual
records can be deleted, with SQLite secure deletion enabled. The separate
Document Processing workflow preserves its existing normalized-JSON retention.

## Frontend

The existing navigation and native professional styling remain. Benchmarking now
contains Ground-truth evaluation, Existing datasets and Benchmark history tabs.
It provides paired uploads, provider selection, normalization controls, summary
metrics/table, original side-by-side text, safe highlighted changes, saved run
IDs and JSON/CSV/text/Markdown downloads. Failed providers stay visible without
scores. Overview reflects the new benchmark results; Settings uses API preflight
and actual inference evidence. Scoring, orchestration, persistence and dataset
access are backend responsibilities; obsolete frontend scoring was removed.

## Verification

- **159 automated tests passed, zero failed/errors**, including preserved legacy
  checks. Three upstream TestClient/AnyIO deprecation warnings remain.
- Correctness lint passed for OCR, frontend, evaluation, scripts and tests.
- Both images built; combined ML dependency consistency check passed.
- Final API and Streamlit containers were healthy. Non-root UID 10001,
  writable cache, bounded uploads and current benchmark-upload cleanup passed.
- Real Docker Tesseract, Docling and Qwen inference passed on the synthetic PDF.
  Paddle's actual OOM was captured; the final memory guard returned a failed
  result without killing the API.
- A matching Markdown benchmark was saved, retrieved and compared with another
  run of the same PDF/reference. Micro CER/WER were verified as 0 on that fixture.
- All five Streamlit views rendered inside Docker. Real results, failed Paddle
  row, historical rows and export widgets rendered without exceptions.
- JSON/CSV serialization, metadata preservation, Unicode and CSV formula
  protection passed tests. Text/Markdown download paths were rendered by AppTest.
  Downloads/reruns did not resubmit OCR in the tested workflow.
- `git diff --check` passed (normal Windows CRLF notices only).

Evidence: [automated tests](GROUND_TRUTH_TEST_RESULTS.json) and
[metrics-only Docker results](GROUND_TRUTH_DOCKER_RESULTS.json).
Reproduce real checks from the repository root:

```powershell
docker compose up -d --build --wait
Get-Content scripts/verify_benchmark_docker.py -Raw | docker compose exec -T frontend python -
docker compose exec api python scripts/check_models.py --provider tesseract
python -m pytest tests -q
python -m ruff check OCR frontend benchmarks/evaluation benchmarks/run.py scripts tests
```

These tests do not verify Paddle inference with a larger memory budget, GPU
execution, full dataset quality, actual Arabic model accuracy, or browser pixel
appearance/manual download clicks. Arabic/Unicode evaluation behavior is covered
by deterministic tests. Job queues, authentication and multi-worker coordination
remain outside this local application's scope; use one API worker.

## GitHub readiness

This checkout already contained extensive uncommitted refactoring changes.
They were preserved. This pass touched or added:

- Backend: `OCR/app.py`, `config.py`, `errors.py`, `service.py`,
  `providers/paddle_vl.py`, `providers/qwen_ollama.py`; new
  `benchmark_api.py`, `benchmark_store.py`, `evaluation.py`,
  `provider_diagnostics.py` and `resources.py`.
- Frontend: `frontend/app.py`, `views.py` and new `ground_truth.py`.
- Runtime/config: `Dockerfile`, `docker-compose.yml`,
  `requirements.txt`, new `requirements-docker-models.txt`,
  `.env.example`, `scripts/check_models.py` and new
  `scripts/verify_benchmark_docker.py`.
- Tests/docs: `tests/conftest.py`, `test_providers.py`,
  `test_readiness.py`, new `test_ground_truth.py`, README, Quickstart,
  this report and the two evidence JSON files.

Jiwer and the Ollama client moved into core requirements for backend evaluation
and host connectivity. Paddle's CPU runtime is added only to the full API build;
CPU Torch/torchvision come from the official CPU wheel index. SQLite introduces
no dependency. No paid services, RAG implementation, secrets, customer text,
model weights or dataset deletion were introduced. No commit/push was performed.

The material remaining blocker is Paddle's memory requirement and unverified
inference on a sufficiently resourced machine. Repository-wide remote CI and
publication were not run.
