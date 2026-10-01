# OCR Refactor Technical Report

Date: 2026-10-01

The OCR refactor implementation and documentation are delivered, with **94 passing isolated tests**. The active application integrates the three approved adapters behind a versioned normalized result. **Real-model acceptance remains outstanding:** no new provider was exercised against real PDFs/models, no GPU run was made, and no clean optional-model environment was installed. Mocked integration is not measured OCR quality.

## 1. Original architecture

The prototype mixed application code, eight runner experiments, datasets, Markdown predictions, evaluation spreadsheets, notebooks, tests, and uploads under `OCR/`. `app.py` owned startup initialization, engine selection, upload persistence and HTTP schemas. Streamlit displayed strings labelled Markdown. The active engines were Marker, conventional PaddleOCR, and legacy Tesseract. Top-level `test*.py` files were spreadsheet-producing evaluation programs, not unit tests.

The previous session added disconnected settings, schemas, an abstract provider contract, errors and PDF helpers. It stopped immediately after writing `OCR/pdf.py`, before validating it. The current session verified that stopping point before editing.

## 2. Problems discovered

- Hard-coded Windows executable paths, UI URL and working-directory-dependent imports/benchmark paths.
- Stale API tests sent JSON `pdf_path`, while the active endpoint required multipart uploads.
- Upload filenames formed output paths directly, with overwrite/path traversal risk and no bounded size policy.
- Initialization and inference were tightly coupled to the API; errors could appear inside extracted text, and health did not reflect provider readiness.
- Text-only runner outputs discarded available page, box, confidence, hierarchy and source provenance.
- Dependency declarations did not describe a complete runtime/test environment. Both existing venv configurations referenced an old Python installation.
- Legacy files called Granite actually used generic Docling or EasyOCR-backed Docling, not explicitly Granite-Docling weights.
- Evaluation scripts could overwrite historical spreadsheets. Broad pytest discovery could execute evaluation code.

## 3. Goals of the refactor

Keep a small local OCR service with FastAPI and Streamlit, three approved providers, lazy model loading, safe ingestion, structured errors and truthful optional metadata. Preserve benchmark data and metric behavior. Make Windows setup and operation understandable from the repository. Expose a stable OCR-to-future-ingestion boundary without implementing RAG or adding its dependencies.

## 4. Major changes made

`OCRService` coordinates the `OCRProvider` interface (`initialize`, `health`, `extract`). Provider construction is cheap; first extraction explicitly initializes it. Inference is serialized within a process and invoked through FastAPI's threadpool. No queues or extra services were introduced.

Uploads use bounded staging, generated storage names, SHA-256 identity and original filename metadata. The multipart body has a separate size limit. Results are validated and persisted as new JSON files. Compare requests store the PDF once and isolate provider failures in structured entries.

All three adapters preserve supplied structure/provenance without substitutions. The normalized schema is version 1.0, with exact character spans, optional geometry/confidence/language and original provider metadata. Configuration is environment-backed, including explicit `.env` support.

The approved organization was implemented with pre/post-move SHA-256 verification. Historical evaluations gained path arguments, main guards and overwrite protection while preserving normalization and metric expressions. New benchmark output is labelled by its actual provider and saved in fresh run directories.

## 5. Files created

Foundation files from the previous session, completed/retained here:

- `OCR/__init__.py`, `OCR/config.py`, `OCR/schemas.py`, `OCR/errors.py`, `OCR/pdf.py`.
- `OCR/providers/__init__.py`, `OCR/providers/base.py`.
- `.env.example`, `docs/OCR_REFACTOR_HANDOFF.md`.

Created in this continuation:

- `OCR/__main__.py`, `OCR/service.py`.
- `OCR/providers/common.py`, `OCR/providers/tesseract.py`, `OCR/providers/docling.py`, `OCR/providers/paddle_vl.py`.
- `benchmarks/__init__.py`, `benchmarks/run.py`, `benchmarks/evaluation/__init__.py`, `benchmarks/evaluation/options.py`.
- `benchmarks/legacy/app.original.py`, `benchmarks/legacy/Requirements.original.txt`, `benchmarks/legacy/run_app.original.bat` (preservation snapshots).
- `tests/conftest.py`, `tests/test_schemas.py`, `tests/test_config_service.py`, `tests/test_pdf.py`, `tests/test_providers.py`, `tests/test_benchmarks.py`.
- `pytest.ini`, `requirements-dev.txt`, `requirements-models.txt`.
- `docs/OCR_REFACTOR_MOVE_MANIFEST.json`, `docs/OCR_BENCHMARK_NORMALIZATION_BASELINE.json`, `docs/ocr-result.schema.json`, `docs/OCR_TEST_RESULTS.json`, this report.

## 6. Files modified

- `OCR/app.py`: service-backed multipart endpoints, errors, size middleware, health and app factory.
- `OCR/streamlit_app.py`: configured URL, provider discovery, normalized results/errors and downloads.
- `OCR/config.py`: runtime/model/device/limit/host/port settings, `.env` precedence and portable paths.
- `OCR/schemas.py`: version, source metadata, spans and provenance validation.
- `OCR/providers/base.py`: input source metadata.
- `OCR/errors.py`: unsupported-provider/upload-limit errors.
- `OCR/pdf.py`: renderer availability check, retaining validated single-page rendering behavior.
- `.env.example`, root `.gitignore`, final handoff.
- Moved-and-updated `README.md`, `requirements.txt`, `run_app.bat`.
- Moved-and-updated API and two legacy test files.
- Moved-and-updated language evaluators, `diagnose.py`, `detailed_analysis.py`, and two Surya diagnostic scripts in `experiments/`.

Pre-existing launcher changes were retained in `benchmarks/legacy/run_app.original.bat` before replacing the active launcher. Pre-existing setup-notebook modifications and saved outputs were moved unchanged. The untracked `Tweet_24.pdf` was preserved.

## 7. Files moved/renamed

**504 files in 23 move groups** were hash-verified immediately after moving, before intentional reference/code edits. [The manifest](OCR_REFACTOR_MOVE_MANIFEST.json) records every source, destination and SHA-256.

| Original | Destination |
| --- | --- |
| `OCR/runners/` | `benchmarks/legacy/runners/` |
| `OCR/Datasets/` | `benchmarks/datasets/` |
| `OCR/Outputs/` | `benchmarks/outputs/` |
| `OCR/Evaluation Results/` | `benchmarks/results/` |
| `OCR/test.py`, `test_arabic.py`, `test_mix.py` | `benchmarks/evaluation/evaluate_english.py`, `evaluate_arabic.py`, `evaluate_mix.py` |
| `OCR/diagnose.py`, `detailed_analysis.py` | `benchmarks/evaluation/` |
| `OCR/benchmark.ipynb`, `benchmark_surya.ipynb` | `benchmarks/notebooks/` |
| `OCR/setup.ipynb`, `setup_executed.ipynb`, `tmp_*surya.py` | `experiments/` |
| `OCR/tests/test_api.py` | `tests/test_api.py` |
| Original Paddle/Surya tests | `tests/legacy/` |
| `OCR/uploads/` | `runtime/uploads/` |
| `OCR/Documentation/OCR Tools.docx` | `docs/OCR Tools.docx` |
| `OCR/run_app.bat`, `Requirements.txt`, `README.md` | Root `run_app.bat`, `requirements.txt`, `README.md` |

Final protected-artifact check: **491 files, zero mismatches** (datasets, historical outputs/results, eight original runners, benchmark/setup notebooks, six uploads and research document). Other moved files received documented code/path updates. Empty moved-from directories were not deleted.

## 8. Files removed

No standalone file was deliberately deleted. Old locations disappear because of approved moves. API/UI/launcher content was rewritten at its active destination; original API/launcher/dependency snapshots are retained. Legacy runners, data/results, PDFs, virtual environments and caches were not deleted. Git shows old paths as deleted and destinations as untracked until the user stages the migration; no index-changing Git operation was performed.

## 9. Dependency changes

Core requirements now describe FastAPI 0.128.0, Uvicorn, Pydantic, python-multipart 0.0.22, python-dotenv 1.2.1, pdf2image 1.17.0, Pillow, requests and Streamlit. Dev requirements add pytest 9.0.2, httpx 0.28.1, NumPy, pandas, jiwer 4.0.0 and openpyxl. Optional model requirements target PaddleOCR 3.6.0 with `doc-parser` and Docling 2.80.0. Paddle CPU/GPU native runtime provisioning is separate.

Standalone Tesseract uses a subprocess argument list and TSV output instead of pytesseract's global executable setting. This retains the approved Tesseract 5 engine; it is not a provider change. Old optional/experimental declarations remain in `benchmarks/legacy/Requirements.original.txt`.

**Only python-multipart 0.0.22 was actually installed**, after explicit approval, into the working Python interpreter. No package was uninstalled. No models, language packs, OCR binaries or GPU dependencies were installed. Existing Paddle 3.0.0 is below the upstream native VL requirement documented in README. No venv was repaired. Optional pins are reviewed API targets, not a complete resolved/transitively locked or locally smoke-tested installation.

## 10. Selected OCR models/providers

| ID | Implementation |
| --- | --- |
| `paddle_vl` | `PaddleOCRVL(pipeline_version="v1.6", vl_rec_backend="native")`, VL-1.6-0.9B plus PP-DocLayoutV3, both explicit local paths |
| `docling` | Standard PDF pipeline, `TesseractCliOcrOptions`, configured languages/executable, local artifacts, table structure enabled |
| `tesseract` | Tesseract 5 CLI TSV recognition on sequential rendered PDF pages |

All three implement the common lifecycle. The registry contains exactly these IDs. Marker and conventional `paddle` are no longer active. Missing assets/dependencies fail explicitly; application code does not provision models. Explicit paths/offline options are configured, but complete third-party offline behavior needs a real provisioned smoke check.

## 11. Why these models were selected

The preceding session approved these selections. PaddleOCR-VL supplies richer multilingual layout/table extraction; Docling supplies native PDF structure and provenance while reusing Tesseract for scanned content; standalone Tesseract provides a simpler CPU reference/fallback. They are complementary providers, not three independent recognition engines.

The rationale was documentary, not a local accuracy contest. English/Arabic/mixed-language performance was not measured for these adapters. Published figures were not re-labelled as local character accuracy. Tesseract is the lightweight application default; users explicitly select/provision richer providers.

## 12. Models considered but rejected and why

The prior handoff lists Marker, Surya, conventional PaddleOCR/PP-StructureV3, Granite-Docling-258M, DeepSeek-OCR/OCR-2, GLM-OCR, MinerU, olmOCR and Chandra as considered but unselected. Recorded concerns were overlap, Arabic evidence gaps, deployment complexity, hardware needs, experimental Arabic support, and model/commercial license restrictions. It did **not** provide an individually sourced rejection rationale for every model; this report does not invent one or claim a new comparative evaluation.

Concrete distinctions retained: conventional PaddleOCR differs from VL-1.6; Granite-Docling is not the selected standard Docling pipeline; the retained Arabic Docling experiment used EasyOCR; the DeepSeek experiment used DeepSeek-OCR, not OCR-2. Original experiments/results remain available for a separately approved comparison. Unselected does not mean experimentally proven inferior.

## 13. New architecture

```text
Streamlit / HTTP multipart client
  -> FastAPI upload validation and persistence
  -> OCRService (registry, initialization, serialized inference, identity checks)
     -> PaddleOCR-VL -> shared Poppler rendering -> local VL/layout
     -> Docling -> native standard PDF pipeline + Tesseract CLI
     -> Tesseract -> shared Poppler rendering -> Tesseract TSV
  -> OCRResult 1.0 (document/page/block provenance and issues)
  -> normalized JSON artifact + HTTP response
```

`OCR/` owns application behavior. `benchmarks/` owns data/evaluation/legacy experiments; `experiments/` retains setup history; root `tests/` controls discovery. `Agentic_RAG/` is unchanged, including empty `main.py`. OCR imports no LangGraph, embeddings, vector stores, retrieval or generation orchestration.

## 14. New OCR request flow

1. Resolve the explicit provider ID or configured default; reject unknown IDs before saving.
2. Enforce multipart/PDF size limits, validate a plain `.pdf` filename and PDF header, compute SHA-256 while staging, and persist under a generated name. Backend parsing performs actual PDF validation.
3. Carry original filename, storage reference, size, media type and identity in `OCRDocument`.
4. Under the service lock, initialize the selected provider if necessary and extract. Initialization is repeat-safe after success; health is side-effect-free.
5. Normalize supplied structure and exact spans. Preserve recoverable page errors outside content; fatal failures use typed exceptions.
6. Validate returned identity/provenance, write a new JSON artifact and return it. Uploads/results are retained; no retention job exists.

`/extract` returns the normalized document directly. `/extract/compare` returns per-provider `{provider, result, errors}` entries over one shared upload. HTTP 200 may contain recoverable OCR issues or failed comparison entries. HTTP 400/413/422/503/500 distinguish input, size, request-validation, unavailable-provider and fatal failures. API version is 2.0.0; payload schema version is independently 1.0.

## 15. Normalized OCR output schema

Authoritative Pydantic models are in `OCR/schemas.py`; generated [JSON Schema](ocr-result.schema.json) is included.

```text
OCRResult
  schema_version: "1.0"
  document_id, filename, source?, source_metadata
  provider, model_name?, model_version?, provider_metadata
  text?, markdown?, language?
  pages?: [
    page_number (one-based), text?, markdown?, language?
    text_start?, text_end?                 # within document text
    width?, height?, dimension_units?
    blocks?: [
      block_id?, block_type?, text?, markdown?, language?
      text_start?, text_end?               # within page text
      reading_order?, confidence?, bounding_box?, provider_metadata
    ]
    warnings[], errors[]
  ]
  warnings[], errors[]
```

Issues contain code, message and optional page number. Bounding boxes have finite min/max coordinates, explicit units (`pixels`, `points`, `normalized`) and origin (`top_left`, `bottom_left`). Supplied reading order is zero-based. Unsupported fields remain null. `blocks: null` means unavailable; an empty list represents known empty structure.

Model revisions stay null unless known/configured. Configured asset revisions are operator assertions, not cryptographic verification. Package versions are separate metadata where available. Tesseract's binary version comes from its version output. Full text joins available page text with two newlines; Paddle block content may contain markup. No semantic cleanup occurs.

## 16. Provenance strategy

HTTP/benchmark inputs use SHA-256 as `document_id`; direct callers supply identity. Results preserve source references and metadata. Provenance is scoped by result artifact/provider and document, then page and block. Adapter-generated block IDs address actual reported words/items/blocks; they are technical handles, not fabricated layout observations.

Page offsets index `result.text`; block offsets index `page.text`. Half-open offsets use Unicode code points, not UTF-8 bytes or UTF-16 string indices. An exact nested slice identifies block text. Validation rejects duplicate/out-of-order pages, duplicate block IDs within a page, invalid spans and mismatched page issue references.

Tesseract preserves TSV row/hierarchy fields, boxes and original 0–100 confidence alongside its 0–1 representation; -1 remains unknown. Docling preserves `self_ref`, hierarchy depth, raw provenance, original coordinate origin and supplied character spans. Multi-page table text lacking page-level cell attribution stays in raw item metadata/Markdown with warnings. Paddle preserves raw block IDs/order/boxes/polygon metadata and invents no confidence.

Offsets cover normalized `text`, not provider Markdown/raw metadata. Consumers must retain the exact result artifact: reruns can change text/order and the schema has no separate extraction-run ID. A local source reference is not a public download URL. Boxes and confidence are not guaranteed for every provider/block.

## 17. Tests added/updated

- Provider construction, explicit/repeated initialization, health, missing assets, registry selection, Docling Tesseract options, Paddle local-model options and import isolation.
- Tesseract TSV confidence/geometry/hierarchy; Paddle block mapping and partial pages; Docling item/page/character-span mapping and failed conversion status.
- Versioned serialization, Unicode provenance, null values, invalid geometry/spans, page uniqueness/order and block uniqueness.
- Settings, `.env` precedence, limits and portable/model paths.
- Unsafe filenames, content/size validation, unique uploads, content identity and unexpected provider errors.
- Multipart extraction/compare, JSON persistence, health without loading, old request rejection and structured errors.
- PDF argument/timeout forwarding, page counts, exception mapping, renderer discovery and cleanup.
- Normalization functions checked against AST hashes from Git HEAD; temporary identical-text fixtures exercise all three evaluators and overwrite protection.
- Five original Paddle/Surya tests relocated with isolated fake modules; no persistent fake-module pollution or real model loading.

## 18. Actual test results

Approved command, from repository root, using working Python 3.13.7:

```powershell
& 'C:/Users/Shrouk/Desktop/pythonInstalll/python.exe' -B -m pytest tests -q -p no:cacheprovider --basetemp=runtime/test-tmp-20261001 --junitxml=runtime/test-results.xml
```

| Measure | Actual result |
| --- | --- |
| Passed | **94** |
| Failed | **0** |
| Test errors | **0** |
| Skipped | **0** |
| Warnings emitted | **0** |
| Code-caused failures | **0** |
| Missing dependency failures | **0 in this mocked suite** |
| Pytest duration | **2.37 seconds** |
| Failure-driven reruns | None needed |

JUnit: `runtime/test-results.xml`; durable summary: [OCR_TEST_RESULTS.json](OCR_TEST_RESULTS.json). Separately, the approved predecessor PDF-helper check ran **8 successful unittest tests**, zero failures/errors/skips/warnings and a passing import-isolation assertion. Prior-session inline configuration/schema/interface checks were reported passed; they are not added to this suite's count.

**Not run, not skipped tests:** real OCR, real Poppler/Tesseract smoke checks, model-backed English/Arabic/mixed accuracy, GPU validation, clean optional-model installation, interactive Streamlit/launcher verification and historical dataset evaluation. Missing model packages were mocked, not counted as functioning installations.

Final source/document inspection confirmed every required README heading and all
21 settings, valid local documentation links, the version 1.0 schema artifact,
and unchanged JUnit counts. Active-source scanning found no machine-specific
paths or RAG imports. Agentic_RAG Git status and the staged diff are empty;
preserved uploads are not hidden by ignore rules. These are static/read-only
checks, not additional model or interactive launch tests.

## 19. Known limitations

- Real model accuracy, language assets, performance, GPU compatibility and complete offline behavior remain unverified.
- Native Paddle inference has no enforced deadline/cancellation. The timeout covers shared rendering/Tesseract and Docling's own document timeout, not a request waiting on the inference lock.
- Page dimensions can make rendering memory-intensive. Upload/page limits do not bound every pathological PDF or all concurrent upload resource use.
- No retention policy, source/result retrieval API, authentication or production deployment controls. Partial OS writes may leave an incomplete artifact for manual cleanup.
- Docling multi-page tables without per-page cell attribution cannot supply precise per-page table text; raw structure/Markdown is retained with warnings. Markdown image references may lack exported image assets.
- No detected-language policy or cross-provider confidence calibration. Arabic/RTL ordering, diacritics and mixed scripts need actual validation.
- Optional packages were not installed; combined Windows resolution and a transitive lockfile remain outstanding.
- Legacy hard-coded paths, notebook environments and behavior remain preserved outside active application logic. No historical metric-policy changes were silently introduced.

## 20. Remaining technical debt

Provision verified model assets/runtime wheels on the target machine; validate complete offline inference; record revisions/checksums, RAM/VRAM/latency and quality. Establish a durable extraction-run artifact identity and retention policy before downstream persistence needs it. Add enforceable deadlines/cancellation and atomic persistence if operational use requires them.

Old venvs, nested `OCR/.python-version`/ignore file, cache access restriction and empty source directories remain. Cleanup needs separate approval. Historical evaluations keep aggressive normalization and missing-file skipping; changes should be explicit future benchmark work. No Git staging/commit was performed; review the migration before committing.

## 21. Recommended next steps

1. Separately approve a clean target environment, Tesseract/Poppler/model provisioning, exact installed versions and asset revisions.
2. Run small native/scanned English, Arabic and mixed PDFs through all three real adapters. Inspect missing pages, boxes, table provenance and failures; measure resources and quality under the preserved metric policy.
3. Review and commit the refactor when satisfied. Consult the manifest/new paths rather than treating old-path removal as lost artifacts.
4. After explicit RAG authorization, implement the ingestion-contract task below. Do not start retrieval/generation automatically.

## 22. Exact OCR -> RAG integration boundary

```text
OCR (ingestion, recognition, normalization, provenance, issues)
  -> serialized OCRResult with schema_version == "1.0"
  -> separate future RAG ingestion
```

RAG must validate this contract and retain immutable original JSON/source references. It should reject unsupported versions, deliberately handle partial/error results and preserve `(result artifact, document_id, provider, page_number, block_id, text spans)` where available. Null block/geometry fields require honest page/source-level citation. Cleanup must retain mappings to original OCR spans.

**Recommended first RAG task, not implemented:** an independent ingestion-schema validator plus citation round-trip fixtures for a multi-page English/Arabic document and an errored page. Decide partial-document handling and durable artifact identity before chunking. RAG owns semantic cleanup, chunking, embeddings, vector storage, retrieval, reranking, LangGraph, generation and citation rendering. OCR depends on none of those stages.
