# Repository audit — 2026-10-14

Pre-existing uncommitted provider, Qwen, configuration, launcher and test changes
are preserved. No dataset or historical benchmark report is disposable.

| Category | Findings and disposition |
| --- | --- |
| Essential application | `OCR/`: API/module CLI, settings, serialized service, PDF helpers, exceptions, schema 1.0; Tesseract, Docling, PaddleOCR-VL, Qwen/Ollama providers. Benchmark runner and language-specific evaluators retained. |
| Essential configuration and documentation | Requirements, Windows CPU lock, launcher, environment template, schema JSON, normalization baseline and migration manifest retained. |
| Essential tests | `tests/`, including legacy tests dynamically loading historical runners; those runners retained. |
| Generated or reproducible | Runtime logs/results, caches, new benchmark runs and packaging artifacts ignored. Uploaded documents preserved. |
| Duplicated or obsolete | Historical API/launcher/requirements snapshots retained as migration evidence in `benchmarks/legacy/`. |
| Temporary debugging | Two `experiments/tmp_*surya.py` standalone print-based probes have no runtime/test references; remove only these exact files. Legacy Surya tests retained. |
| Sensitive or machine-specific | Nested/root environment files, virtual environments and models stay local and ignored. Ignoring existing tracked upload samples does not remove them or their Git history. |
| Manual review | Research DOCX, executed notebooks, historical XLSX/Markdown, nested Python pin and sample uploads preserved. Review source permissions and dataset licenses before public publication. |

Keep the compact `OCR` backend layout to protect existing imports and CLI
workflows. Canonical UI moves to `frontend/app.py` with the old Streamlit path
as a compatibility entry point. No unused dependency removal is justified:
core imports, evaluation, legacy tests and optional models use existing sets.

API uploads are bounded, provider initialization is lazy, and inference is
serialized per process. Optional per-request upload removal now runs in `finally`
blocks; no historical files are removed. Health reports known lifecycle state, not installation
readiness. Use one API worker. Authentication, cross-process locking, queues,
whole-request deadlines and age-based retention policies are not implemented; remote
deployment needs additional design. Heavy model tests use mocks.

RAG remains a separate future consumer of schema 1.0, preserving Unicode
half-open spans, document/page/block identity, explicit geometry and null
unknowns. `Agentic_RAG/` is an inactive placeholder. Preserve all references,
Arabic labeled PDFs, normalized schemas and historical metric policies.

Follow-up audit: repeated metric-row assembly in three evaluators is now shared
in `benchmarks/evaluation/metrics.py`, while original normalization AST hashes
remain unchanged. Backend logs previously included filenames and exception
messages; application event logs now use safe JSON fields. The model-check font
was Windows-specific and now uses portable font discovery/fallback. Optional
benchmark dependencies have their own requirement set. New source modules are
functional UI views/transport and a small shared logging helper, not placeholders.
