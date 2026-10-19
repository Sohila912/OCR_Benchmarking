# Readiness validation — 2026-10-14

- Existing regression baseline: 104 passing tests.
- Extended readiness suite: **123 passed**, one upstream Starlette/AnyIO
  deprecation warning, using `.venv-ocr` and dedicated
  `runtime/test-readiness-full-20261014`. A final compatibility check is recorded
  below after the last run.

Final handoff: **124 passed, zero failed**, one upstream deprecation warning;
correctness lint passed. Docker acceptance rendered all five views, evaluated
32 preserved English reference/output pairs, rejected corrupted PDFs and unsafe
paths, confirmed all-provider comparison isolates missing optional runtimes,
and verified request-upload cleanup. See `runtime/docker-validation.json` and
[startup instructions](QUICKSTART.md).
- Frontend AppTest: both entry points, Arabic text retention, future provider
  discovery, API outage retention, clear action, comparison failure isolation,
  reruns without duplicate extraction and invalid discovery response.
- Local wheel built successfully with `pip wheel . --no-deps --no-build-isolation`.
- Docker image build and Compose startup passed after Docker Desktop became
  available. Both containers report healthy. Real container Tesseract extraction
  passed with schema 1.0, dashboard AppTest rendering and benchmark scoring
  passed inside the frontend container, UID 10001 confirmed non-root execution,
  and the request PDF was removed after extraction.
- `git diff --check` found no whitespace errors; Git emitted normal CRLF notices.
- Ruff correctness lint passed.
- API and Streamlit started on temporary ports; all four providers registered
  and uninitialized. Only test-owned processes were stopped.
- Real Tesseract extraction passed on a generated scanned invoice (1.35 seconds
  in this environment); not an accuracy or comparative performance benchmark.
- Upload cleanup (success/failure/compare), private-log omission, nonzero CLI/UI
  metric parity, dashboard navigation, saved evaluation coverage and duplicate
  processing protection passed.

Paddle-VL, Docling and Qwen/Ollama inference and model quality were not rerun.
GitHub CI was added for Windows/Linux and Python 3.11/3.13;
those remote matrix runs remain unexecuted locally. AppTest verifies widget
behavior, not browser screenshot appearance. Publication/source permission and
dataset license review remain owner decisions. No files were committed.
