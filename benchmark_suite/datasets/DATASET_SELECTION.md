# Dataset selection and acquisition proposal

TASK-004 research checkpoint, 2026-10-28 (Africa/Cairo). **No dataset payloads were downloaded.** Browsing publisher documentation, fetching repository/file metadata and inspecting existing local files are the only acquisition-related actions in this task. No OCR or model inference occurred.

## Decision and scope

Select **Dataset A: the English-language subset of OmniDocBench** and **Dataset B: Misraj-DocOCR** as the primary pair, conditional on the acquisition/rights/quality gates below. This provides a rich English geometry/structure baseline and a manageable human-verified Arabic text/structure baseline. Neither pair alone supplies reliable numeric chart references or Arabic region-level reading-order annotations for every category. Supplements are proposed separately; unavailable categories remain NOT_EVALUATED, not zero.

OmniDocBench data is for noncommercial research under its publisher's copyright statement; the Apache-2.0 code license does not override that. Misraj's dataset card declares Apache-2.0. KITAB table/chart/layout cards lack explicit dataset license fields in the inspected revision; their MIT evaluator code license is not a blanket data grant. No license is inferred from public accessibility.

Primary factual evidence is linked below. [SOURCE_RESEARCH.json](SOURCE_RESEARCH.json) records access date, repository revisions, metadata-response hashes, advertised file sizes/digests and annotation schemas. Remote advertised digests are NOT locally verified dataset checksums. All dataset download dates and locally verified payload SHA-256 values are **null / NOT_DOWNLOADED** until TASK-005.

## Primary datasets at a glance

| Item | Dataset A: English | Dataset B: Arabic |
|---|---|---|
| Publisher repository | opendatalab/OmniDocBench | Misraj/Misraj-DocOCR |
| Role | English pages selected from multilingual document pages | Arabic text and structured Markdown/HTML fidelity |
| Source revision | aa1ee96d106dbe53d0ae59474d75c6e6d9b53fec | 7177bf70f77ce259890d6af0bef53f18faf26ec9 |
| Page/sample counts | 1,651 page images under images/ overall; English-eligible count unknown until annotation validation | 400 image/reference rows; count of unique source documents unknown |
| Whole-repository bytes from metadata | 1,550,688,430 (includes documentation/illustrations) | 537,043,557 (537,036,141 bytes in two data shards) |
| Language | English subset only; exclude Chinese and mixed-language rows from English scores | Arabic; mixed Arabic/English pages must be tagged separately after inspection |
| Ground truth | Structured annotation JSON with region content, polygons, semantic classes, order and HTML tables | uuid, image, markdown; publisher describes expert-verified text/structure |
| License/use restriction | Noncommercial research-only data statement; code separately Apache-2.0 | Dataset-card Apache-2.0; retain source/attribution and review source content rights |
| Current access observation | Public, API gated=false | Public, API gated=false |
| Download approval | Required (large and restricted-use source) | Required as part of the bounded large-data acquisition proposal |
| Payload downloaded/date/verified SHA-256 | No / null / null | No / null / null |

Byte totals describe remote files, not peak RAM, expanded disk needs or proof of license clearance. A row is not necessarily a unique source document. The page images can be benchmarked directly; rendering an image into a PDF wrapper does not create a new born-digital benchmark or add a text layer.

## Dataset A — OmniDocBench, English-only selection

### 1. Name and 2. source

[Official dataset](https://huggingface.co/datasets/opendatalab/OmniDocBench), [author evaluator and schema](https://github.com/opendatalab/OmniDocBench), [research paper](https://arxiv.org/abs/2412.07626). Pin the dataset revision above. The current evaluator uses v1.6 terminology, but that is not used here as an unverified dataset-release label: the actual data snapshot is identified by its repository SHA.

### 3. Size/counts and 4. languages

Metadata lists 1,651 images under images/ and six additional root-level documentation illustrations. This explains why the generic image-folder viewer reports 1,657 rows: **do not evaluate those six illustrations**. The main annotation file is 42,208,096 bytes; the repository total is about 1.55 GB decimal. English-only page and unique-document counts will be computed from actual annotations after approved download, not guessed from filenames. The published collection includes multiple document/layout/language categories. [Dataset description and file view](https://huggingface.co/datasets/opendatalab/OmniDocBench).

### 5. License and restrictions

The dataset's copyright section restricts it to research and excludes commercial use. Obtain explicit approval for noncommercial research acquisition/use before downloading. Retain the pinned statement and attribution; do not redistribute source pages merely because evaluator code is Apache-2.0. If intended use is commercial, this selection stays blocked pending publisher permission or an approved replacement. [Publisher copyright statement](https://huggingface.co/datasets/opendatalab/OmniDocBench#copyright-statement).

### 6. Ground-truth format and 7. supported evaluation

The documented JSON includes page metadata, layout_dets, category_type, poly, ignore, order, annotation IDs, text/LaTeX/HTML where applicable, and relations. Available references support English text metrics, region detection with declared taxonomy/coordinate conversion, reading-order comparisons on ordered elements, and structural table scoring where HTML exists. Respect ignore regions and preserved relations. Document types include scientific/report/book/newspaper/exam material and scan-like pages. Figure localization does not imply chart-type or numeric-chart annotations. [Schema and evaluation description](https://github.com/opendatalab/OmniDocBench#dataset-introduction).

Publisher describes a mixture of assisted annotation, manual work and expert inspection; accept independent, reviewed references only. TASK-005 must spot-check image/reference fidelity and quarantine unverified or inconsistent records. Never generate truth by running a candidate OCR engine. Full-page CER/WER needs a documented, fixed policy for reference assembly, tables, formulas, headers/footers and ignored regions; do not compare concatenated text to incompatible reference content scopes.

### 8. Download procedure (proposal, not executed)

After approval, retrieve only OmniDocBench.json, page images under images/, source README/copyright material and necessary metadata at the pinned SHA, using the official Hugging Face repository. Do not load the generic image-folder viewer split: it can include card illustrations. Stream HTTP bytes to ignored local storage; verify each available advertised LFS SHA-256, then record independently computed hashes, actual byte totals and download timestamp. First inspect annotation language values and map them explicitly; docs show both en-like attribute values and english-like evaluator filters, so do not assume a spelling without reading the actual JSON. Select English pages by verified metadata, excluding mixed rows. A full repository transfer is the conservative upper budget; only English images may ultimately be needed once the annotation inventory is known.

### 9. Limitations and 10. rationale

English count, exact per-category coverage, original PDF access and source-document grouping are not verified from payloads yet. Pages may be correlated or publicly exposed during model training. Cropped image inputs are not end-to-end multipage PDFs. This is a suite protocol using OmniDocBench references, not automatically the publisher's official leaderboard protocol: metric definitions and matching policies may differ. Numeric charts and comprehensive chart taxonomy are gaps. It is selected because one well-documented source supports several independent English structure metrics without fabricating labels.

## Dataset B — Misraj-DocOCR

### 1. Name and 2. source

[Official dataset](https://huggingface.co/datasets/Misraj/Misraj-DocOCR), [publisher benchmark catalogue](https://misraj.ai/en/research/open-source), [author paper, benchmark section](https://arxiv.org/html/2509.18174v1). Pin revision 7177bf70f77ce259890d6af0bef53f18faf26ec9.

### 3. Size/counts and 4. languages

The dataset card/metadata reports 400 rows in the upstream split named train, with two Parquet shards of 247,992,106 and 289,044,035 bytes. This split name does not authorize training: this project uses it only as a frozen evaluation source. Each row is an image/reference pair; do not report 400 independent books/documents. It includes Arabic real and synthetic pages, with varied formatting; exact source-type counts and mixed-script proportions need payload inspection. [Dataset schema and count](https://huggingface.co/datasets/Misraj/Misraj-DocOCR).

### 5. License and restrictions

The publisher's dataset card declares Apache-2.0. Preserve the exact card/revision and attribution. This declaration is not a guarantee about every underlying scanned page; review source provenance, sensitive content and any accompanying notices when acquiring. Do not copy source images/transcriptions into Git or public reports without checking their permissions. [Dataset license declaration](https://huggingface.co/datasets/Misraj/Misraj-DocOCR).

### 6. Ground-truth format and 7. supported evaluation

Metadata exposes exactly uuid, image and markdown. The authors describe expert review of text and document structure. That supports raw/normalized Arabic text evaluation after a fixed Markdown-to-text policy, plus TEDS/cell-content comparisons **only for examples with validated structural table markup**. HTML rowspan/colspan must survive parsing where present; do not treat arbitrary plain Markdown similarity as structural correctness. [Author verification description](https://arxiv.org/html/2509.18174v1#S4).

No box coordinates, class-labelled regions, region IDs or explicit order edges are advertised in the exposed schema. Therefore do not compute layout IoU/mAP, table detection boxes, Kendall's tau or RTL block-order inversion metrics from this dataset alone. Markdown sequence can affect text fidelity but does not supply an independently localized reading-order graph. Numeric chart values, chart classes, and cell geometry remain unverified/NOT_EVALUATED. Numeral-specific metrics need explicit reference-token alignment; unlabelled occurrences are not a new annotated category.

### 8. Download procedure (proposal, not executed)

After approval, retrieve exactly the two original Parquet files and card/license metadata at the pinned revision; avoid an auto-converted duplicate or a third-party mirror. Download as streams and verify advertised plus independently computed checksums. Later read one row or bounded record batch at a time; do not materialize the whole corpus or decoded page images in memory. Preserve embedded image bytes and original Markdown unchanged. Validate uuid uniqueness, complete image/reference pairings, encoding, nonempty references and any table topology before creating manifests. The actual reference file and serialized image get separate content hashes.

### 9. Limitations and 10. rationale

Small source size improves acquisition practicality but is not a guarantee of statistically independent documents. It lacks explicit geometry/reading-order fields and broad structured chart labels. Source scans may have transcription conventions, watermarks or facing-page content that cause reference-scope mismatches; spot-check before freezing and record quarantine reasons. The publisher's human verification is evidence, not our own completed audit. It is selected because the human-reviewed Arabic text/structure source is compact and has a clear dataset-card license; it avoids adopting unreviewed OCR output as truth.

## Coverage matrix and honest gaps

Y = reference type documented; C = available only after row-level schema/quality checks; N = absent/unverified in the currently advertised schema. These describe data annotations, not model capability or scores.

| Evaluation category | English primary | Arabic primary | Proposed supplement / remaining restriction |
|---|---|---|---|
| Page/crop text CER/WER, raw and normalized | Y with fixed content assembly | Y with fixed Markdown policy | Human-check reference scope before freezing |
| Printed, varied and complex pages | Y | Y | True digital-PDF processing remains distinct from page-image OCR |
| Semantic boxes / IoU / class PR-F1 / mAP | Y | N | HITL Arabic line/title/page geometry; KITAB BCE only after rights/schema checks |
| Independent ordered regions / multi-column order | Y | N | Arabic localized order still missing; no fabricated order labels |
| Arabic RTL/mixed English text | N (English-only source) | Y/C | Localized RTL order needs a different verified reference source |
| Table structure / merged-cell fidelity | C: validated HTML | C: validated table rows | KITAB tables after rights and renderer-reference validation |
| Cell/table location, row-column geometry | C: only explicitly annotated fields | N | Deriving HTML topology does not produce geometric ground truth |
| Figure localization | Y | N | Do not relabel every figure as a chart |
| Chart type, chart text, numeric data | N unless explicit annotations found | N unless explicit annotations found | PlotQA for English; KITAB charts for Arabic after license clearance |
| Native multipage-PDF conversion | N/unverified access to original PDFs | N/image samples | KITAB PDF task potentially relevant; availability/rights not cleared |
| Broad category/handwriting coverage | C, measured after filtering | C, inspect actual rows | No claimed quota or zero score for an absent category |

No two selected sources fully cover every requested metric. Reports must carry per-model/per-dataset evaluated counts and NOT_EVALUATED categories. Some Arabic structural comparisons will remain unavailable until independently annotated, licensed supplements are acquired. Do not promote reference text order into an invented region annotation.

## Supplementary sources (not approved for download)

### S1. KITAB-Bench Arabic tables and charts

Official [project](https://mbzuai-oryx.github.io/KITAB-Bench/), [paper](https://aclanthology.org/2025.findings-acl.1135/), [dataset collection](https://huggingface.co/collections/ahmedheakl/kitab-bench). It is a multi-task collection, not 8,809 distinct pages with every annotation type. The authors describe references created before rendering synthetic images and then human checked; this can supply independent truth, unlike a model reading its own rendered image. Each selected row still needs source-to-render verification. Paper totals, viewer rows and collection revisions must be kept separate.

| Subset | Revision | Published rows / remote payload bytes | Reference fields and possible use | License/status |
|---|---|---|---|---|
| [arocrbench_tables](https://huggingface.co/datasets/ahmedheakl/arocrbench_tables) | 1fc7dbf1414f82f04c091087af31d30446bd1867 | 456 / 29,014,518 | image, code, data, category; verify HTML and merged cells for TEDS/cell matching | No dataset license field found; BLOCKED_PENDING_LICENSE |
| [arocrbench_charts](https://huggingface.co/datasets/ahmedheakl/arocrbench_charts) | 6b71105fd5bc6e4b1ff0545c3a5051fdd1a98b61 | 576 / 33,498,603 | image plus source data/code/category; parse documented source values for numeric chart evaluation | No dataset license field found; BLOCKED_PENDING_LICENSE |
| [arocrbench_bcelayout](https://huggingface.co/datasets/ahmedheakl/arocrbench_bcelayout) | a83c89723a300955aad352ff486661d34a3e0c6a | 1,701 / 682,479,522 | normalized_bounding_boxes, region_types, dimensions; check class mapping and language | No dataset license field found; BLOCKED_PENDING_LICENSE |

Download procedure if cleared later: retrieve pinned original Parquet files and notices from their author repositories; verify checksums, parse source references as data, and verify renderer/image alignment without running arbitrary dataset code. Synthetic charts/tables assess source-data recovery separately from scanned document OCR. Never execute a row's code field to generate a convenient answer. Collection code is MIT; it does not clear upstream datasets. The paper reports 1,700 BCE pages while current metadata reports 1,701; acquisition must reconcile without silently dropping a row. The collection's 400 DocLayNet rows are not automatically Arabic; language checks and upstream rights are mandatory. Chart-type totals also vary between publication and live category counts; freeze actual categories after acquisition.

The manually annotated PDF-to-Markdown task is described as 33 PDFs in the paper, but a complete usable package, exact pages, bytes and permissions were not verified. It is a future proposal, not an approved source or current coverage claim. No task totals are summed as unique documents because samples can overlap across tasks.

### S2. PlotQA — English numeric charts

[Official repository](https://github.com/NiteshMethani/PlotQA), [download and annotation schema](https://github.com/NiteshMethani/PlotQA/blob/master/PlotQA_Dataset.md). Documented 224,377 synthetic plot images and 28.9 million QA pairs overall; split-specific image counts/transfer bytes are UNKNOWN here. English-labelled plot text, source x/y data, plot types and element boxes enable chart classification, localization, text and numeric recovery on supported bar/line/dot-line classes. Do not assume pie/area/mixed coverage. The source declares data CC-BY-4.0 and code MIT. Source commit: e0f5c34acbe92753f70798aafda99184e3e0cd8c. Data links are separately hosted and not pinned by that code SHA: record archive checksums and timestamps on acquisition. Use the test image+annotation split, not millions of QA pairs for an OCR task. Exact archive size must be bounded before requesting a later download. Synthetic isolated plots are not page-level scanned chart ground truth.

### S3. Humans in the Loop Arabic documents OCR — region supplement

[Publisher source](https://humansintheloop.org/resources/datasets/arabic-documents-ocr-dataset/). Declares 10,000 images across 12 document categories under CC0-1.0; body-line boxes, page polygons and transcribed titles are described. Full-page transcripts, table topology, numeric chart data and reading-order graphs are NOT established by the description. This is a useful candidate for Arabic line/title/page geometry, not a substitute for complete text/layout semantics. Version: unversioned publisher release; bytes and exact annotation export format UNKNOWN until archive inspection. Later procedure: review the publisher-linked download/export, confirm labels/schema and permissions, record source/archive hashes, then select fixed evaluation images. No forms/private-content claims are made without sample review. Not included in the primary download request.

### S4. DocLayNet — English semantic layout / alternative if rights require

[Official repository](https://github.com/DS4SD/DocLayNet), [dataset license](https://github.com/DS4SD/DocLayNet/blob/main/LICENSE). Human box annotations: 80,863 pages, 11 classes, six document categories; COCO core with optional single-page PDFs and text-cell metadata. Code/documentation snapshot 66947398f04d050fed84e89e5509828f2ee17ecf. Data license CDLA-Permissive-1.0; preserve associated notices and original source provenance. Languages must be filtered, not treated as all Arabic or all English. Publisher lists 28 GiB core plus 7.5 GiB extras; even core exceeds the last measured 24.78 GiB free disk before extraction. **Do not download the full archive here.** A later approved publisher test subset/shard is preferable after size verification. It offers semantic layout, not table topology, reliable numeric charts or automatically human-verified OCR transcripts. Use publisher splits and document IDs; do not repartition source pages across train/test.

### Alternatives screened but not selected

ChartQA has author-provided chart/data material but its repository's GPL-3.0 code label does not by itself resolve source-image/data rights. PlotQA has an explicit dataset-license statement and is the clearer initial numeric-chart supplement. Historical local datasets and third-party reuploads are not selected as primary references without provenance. KITAB's multi-task breadth is valuable, but missing data licenses and mixed source tasks make it less suitable as a single cleared primary Arabic dataset. No dataset-card leaderboard values are imported as measurements of this suite.

## Existing repository data audit

[EXISTING_DATA_AUDIT.json](EXISTING_DATA_AUDIT.json) contains a read-only local audit (PDF metadata via installed pdfinfo, byte hashes and UTF-8 checks). It is not a standardized evaluation manifest and does not certify human ground truth.

| Existing folder | PDF files / pages | Markdown files | Exact-case stem pairs | Finding |
|---|---|---|---|---|
| English | 32 / 68 | 32 | 32 | 15 references have Markdown pipe-row syntax; no validated table topology implied |
| Arabic | 30 / 30 | 30 | 30 | No HTML-table tags or Markdown pipe-row patterns found |
| Mix | 10 / 10 | 10 | 9 | PDF invoice_5 versus reference Invoice_5 differs in case; Windows may resolve it while Linux exact-case lookup will not |

All 72 references decode as UTF-8 and are nonempty; no duplicate PDF byte groups were found across these 72 files. Total existing PDFs plus references: 10,693,007 bytes. This does not rule out rendered-content duplicates, cross-page overlap or bad reference pairings. No dedicated source/license/version or human-verification metadata files were found in the dataset directory inventory (only PDFs/Markdown); embedded PDF/Markdown provenance was not certified. Human spot-checks, dataset permissions and structured annotation availability remain UNVERIFIED. No files, spellings, references or historical scores were changed. Resolve the Mix alias through a reviewed manifest mapping in TASK-005; do not rename source files or silently normalize every identifier's case. Historical OCR outputs are predictions and never reference truth.

## Proposed TASK-005 acquisition and resource budget

**Approval request A (primary pair only):** use the two exact primary repository revisions above for noncommercial research. Conservative full-repository transfer bound: **2,087,731,987 bytes, about 2.09 GB decimal / 1.94 GiB**. Request a hard transfer budget of **2.2 GB decimal** for primary data and small notices, and at least **6 GiB available workspace disk** before beginning (working-storage estimate, not verified expansion size). Stop and ask if observed requirements exceed either approved budget or rights scope; do not replace a revision or source automatically.

No acquisition permission is inferred from approval of TASK-004. Approval of TASK-005 should explicitly include this bounded download and OmniDocBench's research-only use terms. Supplements, unresolved-license KITAB subsets, paid APIs, model downloads and full DocLayNet are outside request A. The published 24.78-GiB disk snapshot suggests primary acquisition may fit, but disk must be remeasured. Available RAM was only 0.61 GiB: this does not authorize heavy decoding or model loading. Stream files to disk; close large consumers voluntarily before row decoding and memory-check each step. Do not stop applications, start WSL/Docker, or install heavy evaluator dependencies automatically. Do not install OmniDocBench's optional TeX/CDM stack for text/table metrics.

After approval, first verify source licenses/revisions are unchanged and obtain only permitted bytes. A staged option is to fetch the English annotation JSON first, identify eligible image IDs, and acquire only those plus the 537-MB Arabic pair; freeze exact file allowlists before transfer. This should stay below the conservative full bound. No annotations/images were downloaded in TASK-004, so actual hashes, English counts and final samples remain pending.

## Standardization and leakage plan for TASK-005 (not implemented here)

1. Preserve original images/Parquet/annotations read-only; compute SHA-256 for each downloaded file and each extracted image/reference. Record source URL/revision, original split, timestamp, byte counts, language, document category, page count, annotation types and supported metrics.
2. Validate references independently of OCR: geometry bounds, IDs, order ties/ignore markers, HTML table structure and content scope. Record quarantines before any inference; do not fabricate annotations or quietly discard difficult pages. Any later repair versions the reference/manifest.
3. Establish source-document groups and exact/perceptual duplicate groups across development/evaluation/primary/supplements. Grouping may be unavailable for Misraj: do not invent source identities or claim document-independent confidence intervals. Record unknown grouping and page-correlated uncertainty limits.
4. Proposed deterministic development sample: up to 10 eligible pages per language, selected by SHA-256 ordering of a fixed seed plus source revision/group/document ID, stratified where verified labels exist. Freeze the seed, group policy and selected IDs before model outputs. Allocate development groups first and hold them out from official evaluation. If true source groups are unknown, byte-level disjointness alone is insufficient to claim no document overlap.
5. Freeze all remaining eligible groups as the full evaluation set, with explicit counts and source hashes. Use identical manifests for all models. The suite's full holdout will differ from publisher-wide results; label that protocol difference. Do not tune on the holdout or silently change pages after seeing model performance.
6. All raw/normalized Arabic scores use explicit versioned transformations. Preserve references unchanged; keep text, geometry, table topology, chart values and reading order as separate capabilities. Missing categories stay NOT_EVALUATED. Candidate model training exposure to public benchmarks is UNKNOWN and must be reported.

## Completion and remaining gates

TASK-004 is complete when this source/license/annotation/size/rationale proposal, metadata evidence and existing-data audit are verified and checkpointed. No claim is made that acquisition or annotation validation has completed. TASK-005 still needs approval request A, fresh disk/RAM checks, actual downloaded-byte checksums, source-level quality validation and frozen manifests. Model execution remains blocked by the earlier hardware assessment and future framework prerequisites.
