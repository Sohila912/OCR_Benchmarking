# Running OCR Benchmarking

## Docker Desktop

From the repository root, with Docker Desktop's Linux engine running:

```powershell
docker compose up -d --build --wait
docker compose ps
```

Open http://localhost:8501; API documentation is at http://localhost:8000/docs.
Compose builds the full CPU API and a smaller frontend image. The first build
installs large runtime packages, but never downloads model weights. Existing
`models/` assets mount read-only. If assets are absent, see the explicit
provisioning commands in the README; only run them when you intend to download
weights. To build a core API without Docling/Paddle packages, set
`OCR_INSTALL_LOCAL_MODELS=false` before building; those providers will report
missing dependencies.

Qwen uses the existing host Ollama server at
`http://host.docker.internal:11434`, configurable with `OLLAMA_DOCKER_HOST`.
Verify `ollama list` contains the exact `OLLAMA_OCR_MODEL` tag. Compose
forwards `OLLAMA_NUM_GPU` (default 0 for CPU), context, image budget and timeout.
No second Ollama server is installed. Paddle CPU initialization requires the configured 6 GiB safety floor; the observed 3.7 GiB Docker budget caused an OOM kill. Use a higher-memory host or a suitably resourced Docker environment before testing Paddle. The tested host itself exposes only about 7.7 GiB of RAM; do not allocate 8 GiB to Docker on that machine. The safety floor is not a verified sufficient capacity. Set `OCR_TESSERACT_LANG=ara+eng` for
mixed Arabic/English Tesseract; both language packs are installed.

Settings / Provider Status shows preflight diagnostics. A healthy service or
initialized provider is not inference verification. Process a small PDF with
each selected engine, then refresh status. Inspect failures and partial outputs.

```powershell
docker compose logs --tail 50 api frontend
docker compose exec api python scripts/check_models.py --provider tesseract
docker compose stop
docker compose up -d --wait
```

The check script generates a synthetic PDF and supports every registered provider;
CPU model checks may take minutes. Its evidence belongs to its own process.
Use API/UI extraction to update API provider status. Do not delete named volumes
if you need existing history or caches.

## Ground-truth benchmarking

1. Open **Benchmarking → Ground-truth evaluation**.
2. Upload the original PDF and matching UTF-8 `.md` ground truth (maximum
   2 MiB). Confirm the pairing explicitly; filenames do not establish a match.
3. Select providers, dataset name, raw Markdown or plain-text comparison, and
   normalization options. Arabic diacritics and punctuation stay by default.
4. Click **Run Benchmark**. Review CER/WER (lower is better), exact match,
   execution timing, original texts, and normalized insertion/deletion changes.
5. Export JSON/CSV metrics, OCR text and the Markdown report.
6. Use **Existing datasets** to confirm a repository document/reference mapping,
   rerun that document, or rescore a preserved historical OCR file. Repeated
   runs create new records; old files remain unchanged.
7. Open **Benchmark history**, refresh/filter by provider, dataset and dates,
   select records to inspect/compare, export metrics or delete a record.

Micro dataset CER/WER divides total edit counts by total reference units.
Coverage and evaluation policy must match for direct comparisons. Historical
files have unknown original model versions and timings; rescoring does not
reconstruct those facts.

The API's `ocr-runtime` volume contains `benchmarks.sqlite3`. It retains
metrics/hashes for 90 days by default, configurable with
`OCR_BENCHMARK_RETENTION_DAYS`. Expiration is applied when saving or reading
history. Benchmark PDFs are removed after the request, and extracted/reference
text is session-only; export detailed reports before clearing the session.
The separate Document Processing workflow keeps its existing normalized-JSON
retention behavior.

## Local development

Install Python dependencies and native Tesseract/Poppler as described in the
[README](../README.md). Copy `.env.example` only when no `.env` exists;
do not overwrite existing configuration.

```powershell
python -m pip install -r requirements.txt -r requirements-benchmark.txt
python -m OCR
# In another terminal:
python -m streamlit run frontend/app.py
```

Optional local model runtimes are platform-specific; the existing Windows CPU
requirements remain available. Provisioning is always an explicit operator action.
See the [implementation and verification report](GROUND_TRUTH_REPORT.md) for
actual provider results and remaining requirements from this pass.
