# Model capabilities and dependency research

Research date: 2026-10-28 (Africa/Cairo). Official documentation and package/file metadata only; no model inference or third-party benchmark scores are represented as this suite's results. Sources can change; model repository revisions, artifact sizes and package dependencies observed are preserved in RESEARCH_METADATA.json and MODEL_REGISTRY.yaml.

## Versions and implementation boundaries

| Candidate | Latest official package/release observed | Existing local version | Proposed implementation boundary |
|---|---|---|---|
| Surya | surya-ocr 0.22.1, Surya 2 | Not installed | 650M VLM via explicit CPU llama-server or compatible Linux vLLM; replace legacy API usage only in suite adapter |
| PaddleOCR-VL | paddleocr 3.7.0; VL 1.6 0.9B | paddleocr 3.6.0 | Explicit VL 1.6 plus PP-DocLayoutV3; current production configuration preserved |
| Marker | marker-pdf 2.0.0 | Not installed | Surya 2-backed document converter; external LLM enhancement disabled for baseline |
| Standard PaddleOCR | paddleocr 3.7.0 | 3.6.0 | Explicit text detector/recognizer, without PP-Structure or VL additions |
| Tesseract | 5.5.4 reported by live GitHub release API | 5.4.0.20240606 | Existing CLI first; OEM/PSM and traineddata fixed per run |
| Docling + EasyOCR | docling 2.143.1; EasyOCR 1.7.2 | Docling 2.80.0; EasyOCR absent | Standard pipeline + explicit EasyOcrOptions with CPU setting |
| Docling + Tesseract | docling 2.143.1 | Docling 2.80.0 | Standard pipeline + TesseractCliOcrOptions, matching existing integration |
| Granite Docling | ibm-granite/granite-docling-258M | Weights not verified; Transformers 4.57.6 | Explicit Docling VLM pipeline/Transformers, not standard Docling OCR |
| Baidu | Hosted service; version not publicly pinned | Implementation/credentials unverified | Unresolved; proposed high-accuracy OCR API would be distinct from local PaddleOCR |

Latest-version research is not permission to upgrade the existing environment or change a variant. Exact evaluation pins and installed versions must be agreed/locked at setup; registry entries are research candidates. In particular, newer Docling package organization differs from the installed 2.80.0. Tesseract release API reported 5.5.4 at 2026-10-28T11:19:43Z, but the browser's release-tag fetch returned 404; treat that as observed API evidence, not a tested distributable. No upgrade is necessary for the existing 5.4.0 baseline.

## Capability matrix

S = documented support, C = configuration/endpoint dependent, H = heuristic or limited geometric segmentation, E = experimental, U = insufficient evidence, N = not supplied by this chosen baseline. Support does not mean measured accuracy. JSON output alone is not proof of semantic document understanding.

| Model | English | Arabic | Semantic layout | Reading order | Table structure | Numeric chart data | Structured output |
|---|---|---|---|---|---|---|---|
| Surya 2 | S | S | S | S | S | U | JSON/HTML |
| PaddleOCR-VL 1.6 | S | S (family language documentation) | S | S | S | C; chart module must be enabled/verified | JSON/Markdown |
| Marker 2 | S | S through multilingual backend | S | S | S | U; image extraction is not chart data | Markdown/JSON/HTML |
| Standard PaddleOCR | S | S with Arabic recognizer | N | H (line sequence) | N | N | Text/boxes/confidence JSON |
| Tesseract | S | S after ara assets | H (blocks/lines, not canonical semantic taxonomy) | H | N | N | TSV/hOCR/ALTO/text |
| Docling + EasyOCR | S | S with ar/en recognition | S | S | S | N in baseline | Docling document/JSON/Markdown |
| Docling + Tesseract | S | S after ara assets | S | S | S | N in baseline | Docling document/JSON/Markdown |
| Granite Docling | S | E, explicitly stated by IBM | S | S | S | U; no reliable numeric chart claim inferred | DocTags and converted structured document |
| Baidu | C | C, high-accuracy product documents Arabic | C | U | C, separate endpoint | C | Endpoint JSON |

Chart region detection, chart text OCR, chart classification and numeric recovery remain distinct metrics. UNKNOWN becomes NOT_EVALUATED pending reliable capability/reference evidence. For N entries, use NOT_SUPPORTED in the selected baseline, not zero accuracy. Reading-order claims need annotated tests, especially RTL/mixed pages.

## Per-model evidence and configuration cautions

### Surya

The release README documents full-page OCR, semantic regions, ordered layout and tables, with CPU llama.cpp or a GPU inference server. Legacy FoundationPredictor/text_lines assumptions do not match Surya 2. Pin its server version and model revision; do not let automatic backend selection spawn a GPU container. The package metadata requires Python >=3.10, torch >=2.7 and Transformers >=5.12.1. Installed Transformers 4.57.6 is incompatible with that declared constraint. Use an isolated environment. Code and model weights have different licenses; retain both notices and verify use terms for the pinned weights. [Release README](https://github.com/datalab-to/surya/blob/v0.22.1/README.md), [package metadata](https://pypi.org/pypi/surya-ocr/json), [weight card](https://huggingface.co/datalab-to/surya-ocr-2).

### PaddleOCR-VL

Official platform documentation supports local x64 CPU inference. It specifies GPU compute capability >=7.0 with CUDA >=11.8 for Paddle/Transformers, and >=8.0/CUDA >=12.6 for its vLLM route. Windows does not natively support the listed accelerated server backends. Avoid mixing server/library stacks in one environment. The repository's existing adapter explicitly disables chart recognition; documenting model-family chart support does not enable it. Family language documentation includes Arabic; verify actual 1.6 Arabic behavior in its own run. [Platform requirements](https://www.paddleocr.ai/main/en/version3.x/pipeline_usage/PaddleOCR-VL.html), [1.6 model card](https://huggingface.co/PaddlePaddle/PaddleOCR-VL-1.6), [family language list](https://www.paddleocr.ai/main/en/version3.x/algorithm/PaddleOCR-VL/PaddleOCR-VL.html).

### Marker

Marker 2 depends on surya-ocr >=0.22.1,<0.23 and Transformers >=5.12.1,<6, so the legacy converter cannot be assumed compatible. It combines a text-layer path with OCR and structural processing. Record fast versus balanced mode and whether pages used embedded text; disable_ocr would skip scanned-page recognition and is not an equivalent OCR trial. Disable optional external LLM calls unless separately selected and approved. Preserve actual model-weight terms in addition to Apache-2.0 code terms. [Release README](https://github.com/datalab-to/marker/blob/v2.0.0/README.md), [package dependencies](https://pypi.org/pypi/marker-pdf/json).

### Standard PaddleOCR

Do not equate its text detector/recognizer with PP-Structure or PaddleOCR-VL. Release 3.7.0 source selects PP-OCRv6 medium for English by default and an Arabic PP-OCRv5 recognizer for ar; that difference must be explicit in evaluation configuration. A smaller detector/recognizer or older PP-OCR version is a different configuration requiring disclosure, not a silent fallback. Newest package requires compatible PaddleX 3.7.x; the existing 3.6.0 stack is preserved. Use CPU Paddle only in a CPU environment, and never coinstall its GPU distribution. [Pinned selection logic](https://github.com/PaddlePaddle/PaddleOCR/blob/v3.7.0/paddleocr/_pipelines/ocr.py), [Arabic recognition](https://www.paddleocr.ai/main/en/version3.x/algorithm/PP-OCRv5/PP-OCRv5_multi_languages.html), [PP-OCRv6](https://www.paddleocr.ai/main/en/version3.x/algorithm/PP-OCRv6/PP-OCRv6.html).

### Tesseract

Installations need engine and language data separately. The detected native binary is present, with eng/osd only; Arabic evaluation cannot proceed until independently sourced ara data is available. Tesseract provides geometric/text outputs but no general table topology or chart-value recovery in this baseline. Keep language pack family (fast/best), exact checksum, OEM, PSM, page rendering and thread settings constant. PDF image rendering here already has Poppler. [Installation/platform guide](https://tesseract-ocr.github.io/tessdoc/Installation.html), [official engine releases API](https://api.github.com/repos/tesseract-ocr/tesseract/releases/latest), [fast language data repository](https://github.com/tesseract-ocr/tessdata_fast).

### Docling + EasyOCR

Docling supports Windows and selectable OCR engines. Add EasyOCR deliberately; do not rely on changing defaults. EasyOCR documents CPU use and multilingual recognition; v1.7.2 config identifies an Arabic-family recognizer distinct from english_g2. Separate English-only and ar/en configurations must be recorded rather than called the same model. Native OCR recognition alone does not produce Docling's layout/table structure; record the accompanying layout/TableFormer revisions as well. [Docling installation](https://github.com/docling-project/docling/blob/main/docs/getting_started/installation.md), [EasyOCR usage](https://github.com/JaidedAI/EasyOCR/blob/v1.7.2/README.md), [Arabic checkpoint config](https://github.com/JaidedAI/EasyOCR/blob/v1.7.2/easyocr/config.py).

### Docling + Tesseract

Reuse the current standard pipeline + CLI backend, with explicit languages eng/ara and local layout/table assets. Tesseract OCR and Docling layout/table models have separate roles, versions and licenses. Avoid replacing the CLI with tesserocr without disclosing it; compiled Python bindings create different Windows dependency requirements. Docling code uses MIT; the referenced model collection declares Apache-2.0 and CDLA-Permissive-2.0, so record each selected artifact rather than labeling all weights MIT. [Docling code license](https://github.com/docling-project/docling/blob/v2.143.1/LICENSE), [selectable engines](https://github.com/docling-project/docling/blob/main/docs/getting_started/installation.md), [model collection](https://huggingface.co/docling-project/docling-models).

### Granite Docling

IBM's 258M checkpoint is a separate end-to-end VLM producing DocTags. The model card includes CPU execution and labels Arabic support experimental. Use English and Arabic scores separately; do not present experimental Arabic as equivalent validated coverage. On this older CPU/GPU, prefer a future reviewed CPU float32/SDPA configuration over copying a bf16/FlashAttention GPU example. That dtype change must be measured and recorded. The model is Apache-2.0; do not substitute a generic Granite or SmolDocling model. [IBM model card](https://huggingface.co/ibm-granite/granite-docling-258M), [IBM model documentation](https://www.ibm.com/granite/docs/models/docling).

### Baidu

Implementation is unresolved. The proposed hosted high-accuracy product documents English and Arabic; the standard product has a narrower language set. Positions, tables and document parsing are different API variants, not free interchangeable capabilities. Confirm exact endpoint, supported request language code, source image/PDF limits, account region, credentials, quotas, request budget and terms before TASK-017. Some documentation requests timed out; account limits/costs were not verified and no request was made. [Product family](https://cloud.baidu.com/product/ocr/general), [high-accuracy endpoint documentation](https://cloud.baidu.com/doc/OCR/s/1k3h7y3db), [pricing](https://cloud.baidu.com/doc/OCR/s/9k3h7xuv6), [trial policy](https://cloud.baidu.com/doc/OCR/s/fk3h7xu7h).

## Dependency and licensing gate

Prefer isolated per-model environments (research baseline Python 3.12 if wheels support it), leaving the working production 3.13.7 CPU environment intact. Python lower bounds in PyPI metadata do not guarantee every transitive wheel/native backend. Verify a lock and compatible runtime at setup. WSL2/Docker is already present but switching execution environment still requires approval and cannot increase physical capacity. Surya/Marker CPU llama-server integration on Windows remains untested; this report establishes research evidence, not installation readiness.

The reports summarize official license identifiers, not a legal suitability determination. No vendor benchmark percentages are copied into suite results. Capability claims need independent annotation-backed validation later.
