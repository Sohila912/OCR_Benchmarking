# Operational scope

Use one API worker: models and inference locking are process-local. The API
does not provision models; the Windows launcher is a separate workflow that
can download missing Ollama assets or offer optional provider setup.

The Docker Compose base image runs as a non-root user and provides Tesseract,
Poppler and English/Arabic language packs. Optional providers require separate
packages/assets and Ollama connectivity. Host ports bind loopback. Runtime
data persists in a named volume. Do not mount Windows executable paths into
Linux containers. Container builds need independent verification.

Authentication, queues, cross-process locks, hard whole-request deadlines and
automatic retention are not implemented. Client timeouts do not cancel server
inference. Normalized results are retained. `OCR_RETAIN_UPLOADS=false` removes
only request-created PDFs after processing, including failures; the template and
Compose enable this, while the settings compatibility default retains inputs.
No existing upload is removed. Review these policies
before remote use. UI durations include queueing/loading and HTTP overhead.

Existing tracked documents remain tracked even when ignored. Review dataset
licenses, research documents, notebooks and upload samples before publishing.
No history rewrite, publication or license decision has been performed.
