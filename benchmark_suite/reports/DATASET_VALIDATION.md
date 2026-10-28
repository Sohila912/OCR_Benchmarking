# TASK-005 dataset validation report

Completed 2026-10-28 (Africa/Cairo). Local acquisition was explicitly approved by the user, superseding the Drive-storage preference. Only the two pinned primary sources were acquired for noncommercial research. No model downloads, OCR framework/model imports, inference, cloud/API execution, dependency installation or major system changes occurred.

## Acquired and frozen data

- Verified downloaded originals: **760 files, 1,397,890,070 bytes**. Conservative charged transfer including metadata/reservations: **1,398,615,726 bytes**, below the approved 2,200,000,000-byte budget.
- Source pins: OmniDocBench aa1ee96d106dbe53d0ae59474d75c6e6d9b53fec; Misraj-DocOCR 7177bf70f77ce259890d6af0bef53f18faf26ec9.
- Selected images: 755 English and 400 Arabic. The English images were selected from publisher language=english; the other 896 annotated pages and six card illustrations were not acquired as benchmark images. The full publisher annotation JSON and source notices remain preserved.
- Development: 10 English + 10 Arabic images. Official evaluation holdout: **745 English + 390 Arabic images**. No image/reference exact-content hash overlaps across these splits; all 1,155 exact-content groups are unique.
- Disk usage for raw, extracted source/reference files and frozen metadata: approximately **2.03 GB decimal** at validation, including the preserved Arabic source shards, extracted images and early original copies. Free disk at observation: 23.04 GiB. No existing user data was removed to free space.

The benchmark unit is one image, not a claim of one original PDF page or independent source document. No OCR accuracy or latency results were generated.

## Persistent evidence

[PROVENANCE.json](../datasets/manifest/PROVENANCE.json) is the final frozen-cohort completion marker. It includes manifest/schema hashes, source revisions, source archive/annotation hashes, environment versions, download dates, counts and limitations. [ACQUISITION_PROVENANCE.json](../datasets/manifest/ACQUISITION_PROVENANCE.json) is the earlier download-only checkpoint: its separate-preparation marker does not supersede final PROVENANCE.json. The complete per-file download history/checksums/URLs are retained locally in ignored datasets/raw/acquisition.json; no signed CDN links or credentials are saved.

Git stores manifests and reviewed source/audit metadata, not the downloaded images, transcriptions, annotations or Parquet payloads. References are preserved locally without model-generated replacements. Source licenses/notices remain with originals; OmniDocBench is restricted to noncommercial research and Misraj's dataset card declares Apache-2.0.

## Automated reference eligibility

| Annotation-backed capability | English pages | Arabic pages | Meaning |
|---|---:|---:|---|
| Explicit text references | 750 | 400 | Eligibility only; no model score |
| Validated region polygons/classes | 753 | 0 | Eligibility only; no model score |
| At least two ordered regions with accepted geometry | 740 | 0 | Eligibility only; no model score |
| Supplied HTML tables passing nesting/span checks | 146 | 56 | Eligibility only; no model score |

Five English pages have no explicit nonignored text fields and remain in the image cohort for other available metrics; they must not receive fabricated CER/WER scores. Arabic document categories, localized region geometry, reading-order graphs and numeric chart references are not supplied by the selected source. English categories are preserved from publisher metadata (scientific papers, books, presentations, magazines, newspapers, textbooks, exams, a report and a note). Arabic category remains null rather than a guessed label.

## Reference defects retained transparently

All 1,155 source/reference pairs passed byte identity, image format/dimension and nonempty Arabic-reference checks. Two English references contain polygons outside page bounds. Three pages (one English, two Arabic) contain table markup requiring review. Source bytes were not clipped, rewritten or silently dropped. Affected layout/reading-order or table eligibility is restricted; the pages remain eligible for other supported metrics. Structural HTML checks do not certify full cell geometry, semantic correctness or TEDS; those metrics belong to TASK-006.

| Document ID | Preserved warning |
|---|---|
| misraj:7177bf70f77ce259890d6af0bef53f18faf26ec9:168c8ccb-6acb-4d91-8ece-3d6cd2bca72b | TABLE_MARKUP_NEEDS_REVIEW |
| misraj:7177bf70f77ce259890d6af0bef53f18faf26ec9:3e855d7f-a532-4b6c-97b2-f2ecff336065 | TABLE_MARKUP_NEEDS_REVIEW |
| omnidocbench:aa1ee96d106dbe53d0ae59474d75c6e6d9b53fec:5de02f7f2905ba50063694b6 | POLYGON_OUTSIDE_PAGE |
| omnidocbench:aa1ee96d106dbe53d0ae59474d75c6e6d9b53fec:93ea5e5a356f6be11684e9ea | POLYGON_OUTSIDE_PAGE |
| omnidocbench:aa1ee96d106dbe53d0ae59474d75c6e6d9b53fec:c0778a9e2b0ddf8663654baf | TABLE_MARKUP_NEEDS_REVIEW |

## Bounded manual spot checks

Four image/reference examples were visually inspected. This verifies selected visible pairings, not a full character-by-character audit of the dataset:

- English image hash 702835994e119e66842a6613c92fd4c25d4945764f978aea82e0353bddb8c113: scanned two-column page with two bar charts; visible headings/captions match the preserved region references. This does not supply numeric chart-value ground truth.
- English image hash 0a960c448e0df33fa6334000fc294354f09cd50dad1a23be04aad4d1954d9bbd: scientific page with a seven-row/five-column table; visible table layout and sample numbers correspond to the supplied HTML. Mathematical glyph/LaTeX conventions need an explicit future text-normalization policy.
- Arabic UUID 1e70bf91-ca63-4372-88f9-386b35222a27: two mixed Arabic/English tables; visible numeric/cell content corresponds to the preserved reference, with background mirrored/ghost text present in the image. Reference-scope effects must be documented in evaluation.
- Arabic UUID 1788cdde-c12e-499e-93b7-be2fe1b2cda5: diacritized poetry and prose; visible page number, opening lines and prose correspond to the reference. Tatweel/diacritic/markup conventions remain intact for raw and normalized scoring later.

No source image/text is reproduced in this Git report, and no human annotation was invented to fill missing capabilities. The independent publisher's expert-review claims remain provenance evidence, not a blanket accuracy certification by this task.

## Reproducibility and recovery checks

- 90 suite tests passed (54 tracking, 17 hardware, 19 dataset acquisition/integrity tests); Ruff passed.
- --verify-downloads rehashed all 760 originals against the persisted acquisition evidence and pinned source digest records; no network calls or reference decoding.
- --build published 1,155 records with strict schema/identity/path checks and validated local image/reference pairings; the original Parquet was read one row per batch with threaded prefetch disabled.
- --validate-only rehashed the frozen artifacts, every selected image/reference and preserved source archives/annotations. Counts and exact-content split isolation passed offline.
- Recovery tests cover interrupted publication, partial range resumes, ignored ranges, tampered bytes, hard transfer limits, transient Windows sharing locks, path escapes, long Unicode filenames, immutable outputs and deterministic duplicate grouping.
- Explicit manifest-specific .gitattributes LF rules prevent Windows automatic line-ending conversion from breaking frozen checksums. A real checkout-index with core.autocrlf=true preserved all expected manifest/schema/alias digests.
- Existing benchmarks/datasets, historical outputs/results and production files remain unchanged. LEGACY_ALIASES.json explicitly maps the case-different Mix invoice paths but excludes legacy data from this official cohort pending source/rights verification.

The download was interrupted by Windows path length, console encoding and transient sharing-lock issues; all were resolved with short canonical storage paths, safe diagnostics and bounded atomic replacement retries. Verified downloads were reused. Early newly downloaded copies remain preserved rather than being deleted. A reference-decoding preflight initially refused when free RAM fell below 512 MiB; after the user freed RAM and requested a retry, preparation and validation completed. No model hardware guard was relaxed.

## Limits and next task

The source document/book identities are unknown for this cohort, so the deterministic holdout is page/content-disjoint, not certified source-book-disjoint. Near duplicates, semantic grouping and public model-training exposure remain unverified. Do not claim document-independent confidence intervals; use an appropriate later grouping protocol or disclose a page-level analysis limitation. Counts alone are not full reference correctness certification.

TASK-006 implements tested metric calculators and explicit content/normalization/matching policies. Model execution remains blocked by the separate hardware assessment and requires the remaining shared framework tasks. No supplemental dataset or alternate model variant was acquired.
