# OCR Refactor Handoff

Updated: 2026-10-01. Repository: `OCR_Benchmarking`.

**Status: OCR refactor code/documentation delivered; 94 isolated tests passed. Real-model operational acceptance remains outstanding. STOP before RAG unless explicitly approved.**

This is the current continuity checkpoint. [OCR_REFACTOR_REPORT.md](OCR_REFACTOR_REPORT.md) is the final technical record; [README.md](../README.md) is the setup guide. The previous session's pending PDF-helper validation was completed before continuation.

## Decisions

- Keep `OCR/`, FastAPI and Streamlit. No microservices, queues, databases or RAG infrastructure.
- Exactly three providers: **PaddleOCR-VL-1.6** (`paddle_vl`), **Docling standard PDF + Tesseract CLI** (`docling`), **Tesseract 5** (`tesseract`). No substitutions.
- Paddle uses local native inference, VL-1.6-0.9B and PP-DocLayoutV3. Docling explicitly uses Tesseract, not default OCR or Granite-Docling. Standalone Tesseract uses CLI TSV to avoid pytesseract global configuration.
- Lifecycle: `initialize()`, `health()`, `extract(OCRDocument) -> OCRResult`. No loading at construction/startup/health. Successful initialization is repeat-safe.
- Languages default to `eng`; `ara+eng` is explicit. Do not invent detected language/confidence/layout. Default provider is lightweight Tesseract; Paddle remains the intended richer multilingual path.
- Preserve historical metrics/data/results/experiments. Do not relabel legacy predictions as new provider results.

## Completed

- Initial read-only recovery matched the previous handoff; no initial inspection edits.
- Approved PDF check: 8 unittest tests passed, import isolation passed; zero failures/errors/skips/warnings. No real OCR/PDF/binary execution.
- Three adapters, registry/service, safe uploads, structured errors, normalized API/UI, JSON persistence and root launcher.
- Schema 1.0 with source metadata, exact page/block text spans, validation and available raw provider provenance.
- Environment-backed settings and explicit `.env` loading; model/device/limits/temp/host/port configuration. No machine-specific paths in active source.
- All 23 approved move groups: 504 files verified immediately after moving. Final protected check: 491 files, zero mismatches. [Manifest](OCR_REFACTOR_MOVE_MANIFEST.json).
- Benchmark path/main-guard/overwrite updates. Three normalization functions preserved against baseline AST hashes. New-run extraction CLI records actual provider/metadata.
- Current-contract tests, isolated legacy tests, README, generated schema, final report and durable test summary.
- New Tasks 5–9 are complete at the implementation/documentation level, with operational limitations explicitly recorded.
- `Agentic_RAG/` untouched; `main.py` remains empty. No RAG added.
- Final source/document review: all 21 settings and required README sections are
  documented, local documentation links resolve, the report contains sections
  1–22, JSON Schema declares version 1.0, and JUnit confirms 94 tests with no
  failures/errors/skips. Active-source scan found no machine-specific paths or
  RAG imports. Preserved uploads are visible to Git; generated runtime XML is
  ignored. Staged diff and Agentic_RAG status are empty.

## Current structure

```text
OCR/                    Active API/config/service/schema/errors/PDF/UI
  providers/            base/common/tesseract/docling/paddle_vl
benchmarks/
  datasets/             English/Arabic/Mix originals
  outputs/              Historical predictions; separate new-run folders
  results/              Historical XLSX; fresh evaluations default to runs/
  evaluation/           Metric scripts and diagnostics
  legacy/               Original runners and app/requirements/launcher snapshots
  notebooks/            Historical benchmark notebooks
experiments/             Setup notebooks and Surya diagnostics
runtime/                 Six preserved uploads, generated test artifacts
tests/                  Focused suite plus legacy/ isolated tests
docs/                   Report, handoff, schema/evidence, research document
Agentic_RAG/             Unchanged placeholder
README.md                Windows setup and current usage
requirements*.txt        Core / dev / optional model declarations
run_app.bat              Root .venv launcher
pytest.ini               tests/ discovery only
.env.example             Portable complete settings reference
```

## Actual tests and environment

Approved command completed on **Python 3.13.7**, pytest **9.0.2**, Pydantic **2.11.9**, FastAPI **0.128.0**, httpx **0.28.1**:

```powershell
& 'C:/Users/Shrouk/Desktop/pythonInstalll/python.exe' -B -m pytest tests -q -p no:cacheprovider --basetemp=runtime/test-tmp-20261001 --junitxml=runtime/test-results.xml
```

**94 passed, 0 failed, 0 errors, 0 skipped, no warnings emitted; 2.37 seconds.** No fix reruns needed. No code or dependency failures in the mocked suite. [Durable results](OCR_TEST_RESULTS.json); detailed JUnit is under runtime/.

The user explicitly approved installation of **python-multipart==0.0.22**; pip succeeded. This was the only installed dependency. No packages were uninstalled. No models, OCR binaries, language packs, GPU dependencies or optional providers were installed. Optional targets: PaddleOCR 3.6.0 and Docling 2.80.0; a clean combined environment remains unverified.

Both existing venv configurations still point to the previous Python310 installation. Neither was repaired; the working explicit interpreter above was used. Nested `OCR/.python-version` (3.10.18) is historical. Existing Paddle 3.0.0 is below the native VL runtime requirement.

**Not run:** real provider/Poppler/Tesseract smoke tests, GPU tests, actual benchmark datasets, clean model installation, interactive Streamlit/launcher. These are not pytest skips. Do not claim provider accuracy or a functioning complete local model environment.

## API and provenance contract

- `python -m OCR`: API with configured host/port; direct entry point `OCR.app:app`.
- `python -m streamlit run OCR/streamlit_app.py`: current UI.
- `/extract`: multipart `file`, optional `engine`; direct OCRResult, `schema_version: "1.0"`.
- `/extract/compare`: one upload and shared identity, per-provider `{provider, result, errors}`.
- `/tools`: exact three IDs/default; support list is not readiness.
- `/health`: API and known provider state, no model initialization.
- Page numbers one-based; supplied reading order zero-based. Half-open Unicode character spans: pages index document text, blocks index page text. Text/blocks/geometry may be null.
- Tesseract retains TSV hierarchy/raw confidence, Docling retains item/provenance/table data, Paddle retains raw block metadata. No invented confidence/language/boxes.
- HTTP/benchmark document ID is SHA-256. Upload source metadata retains original filename and generated storage name. Result JSON has an independent generated filename; no schema-level extraction-run ID yet.
- Errors stay outside text; partial extraction/comparison failures may accompany HTTP 200. Consumers must inspect issue lists.
- Contract: [ocr-result.schema.json](ocr-result.schema.json).

## Configuration and runtime

`OCR/config.py` reads repo-root `.env`, then environment overrides. Relative directories anchor at repo root. Adapters require local assets and disable known remote/extra model paths; full offline behavior still needs a provisioned smoke check.

Core/dev/model declarations are separate. Tesseract/Paddle PDF paths need Poppler; Docling parses PDFs natively. Tesseract/Docling need Tesseract 5 and configured packs. Native Paddle inference lacks an enforced deadline. One process serializes inference; no multi-worker coordination.

## Git and artifact preservation

No stage, commit, reset, checkout or Git mutation. Filesystem moves remain unstaged: old paths can show deleted and destinations untracked. This is not lost content.

Pre-existing setup notebook edits moved byte-for-byte. Original modified launcher preserved in `benchmarks/legacy/run_app.original.bat`. `Tweet_24.pdf` and five other uploads retained; six names have explicit ignore exceptions so a later commit can preserve them. Generated runtime/model/.env files remain ignored.

Original runner/data/result/notebook contents unchanged. Empty source directories, old nested ignore/python-version files, venvs and inaccessible pytest cache remain. No cleanup/deletion was approved or performed.

## Remaining limitations/debt

- Real-provider acceptance on native/scanned English/Arabic/mixed PDFs, measured RTL/table/diacritic accuracy and resources.
- Reproducible Windows optional-model environment, verified asset revisions/checksums and transitive lockfile.
- Paddle deadline/cancellation, extreme-page resource controls and atomic persistence if operational use needs them.
- No retention/download API. Library/multipart temp storage may use OS locations outside the application temp setting.
- Multi-page Docling tables lacking page cell attribution have null per-page text plus warnings; raw metadata/Markdown preserve content. Markdown image assets are not exported.
- No detected-language policy, semantic cleanup or cross-engine confidence calibration.
- Historical aggressive normalization and notebook paths remain; no extraction-run ID in schema.

## Next action and approval policy

**STOP. Do not start RAG automatically.** Give the concise milestone report with actual results and limitations.

Recommended remaining OCR acceptance task: separately approve clean environment/model provisioning, real smoke checks and measured benchmarks. Recommended first RAG task after explicit approval: standalone ingestion-schema validation and citation round-trip fixtures, including partial-page policy and durable result-artifact identity.

Current user policy permits normal non-destructive edits within approved logical work. Ask before installing/removing dependencies, deleting files, changing selected providers, major deviations, destructive actions, Git mutations or running tests. Test approval covered the mocked suite and necessary failure-driven reruns; it did not authorize model downloads or real inference.
