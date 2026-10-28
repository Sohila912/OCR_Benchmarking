# Primary dataset acquisition and manifests

The primary sources and licenses are documented in [DATASET_SELECTION.md](DATASET_SELECTION.md).
The user approved bounded local acquisition, superseding the earlier Drive preference.
Only the pinned English OmniDocBench pages and Arabic Misraj-DocOCR source are acquired.
No supplements, models or paid resources are provisioned by this workflow.

## Reproduction

From the repository root, with the existing .venv-ocr dataset dependencies:

```powershell
.venv-ocr\Scripts\python.exe benchmark_suite/scripts/prepare_datasets.py --download
.venv-ocr\Scripts\python.exe benchmark_suite/scripts/prepare_datasets.py --build
.venv-ocr\Scripts\python.exe benchmark_suite/scripts/prepare_datasets.py --validate-only
.venv-ocr\Scripts\python.exe -m pytest benchmark_suite/tests/test_datasets.py -q
```

Reviewed dataset-tool versions are pinned in ../requirements-datasets.txt. No
package installation was needed on the inspected machine. This is a tested
set of installed direct dependencies, not a complete cross-platform lockfile.
Use an isolated environment for another machine; do not alter model environments
or install optional heavyweight upstream evaluator stacks to prepare references.

--download is an explicit network operation. It enforces pinned repository
revisions, per-file sizes, upstream LFS SHA-256 or Git blob checksums, a persisted
2.2-GB decimal cumulative payload/metadata budget and a 6-GiB free-disk reserve
plus the incoming file size. The budget conservatively charges reads before they
occur: abrupt termination can leave unused reservations charged, never a silent
reset. Existing verified bytes are rehashed/reused, range requests resume partial
files, and unhonored ranges or mismatched bytes stop without overwriting evidence.
Signed CDN URLs and credentials are not stored. Keep acquisition.json with its
files; do not delete it to reset a budget. Retry stopped transfers only after
resolving the logged cause, with the same source pins and approved budget.

There is one coordinator writer. Do not run two preparation commands concurrently.
Metadata parsing/Parquet preparation require at least 512 MiB free RAM as an
explicit conservative preparation policy. It is not a model-inference minimum
or an OOM guarantee. Decoding uses one Parquet row per batch without threaded
prefetch. Image verification reads formats/dimensions and verifies source bytes;
it does not invoke OCR. Do not stop user processes or switch environments
implicitly if resource checks fail.

## Local artifacts

- raw/objects/: stable short hashed filenames, avoiding Windows path limits;
  original publisher filenames/URLs/revisions remain in raw/acquisition.json.
- raw/catalog.json and raw/allowlist.json: exact pinned remote inventory and the
  English language selection. Documentation illustrations and non-English rows
  are excluded explicitly. raw/download.log preserves download diagnostics.
- english/references/: one preserved publisher region JSON record per English
  page; the original full annotation file is also retained.
- arabic/images/ and arabic/references/: original encoded image bytes and original
  Markdown transcriptions extracted from two preserved Parquet shards.
- manifest/: JSON Schema, development/evaluation JSONL, PROVENANCE.json and explicit
  LEGACY_ALIASES.json. Only metadata/hashes are committed, never source payloads.

Early local downloads created before the Windows filename fix are normalized to
short canonical storage before freezing. Original early copies are preserved;
they are not silently deleted. Fresh acquisition and this normalization produce
the same relative canonical paths. Future cleanup of redundant originals is a
separate explicit user action, not part of preparation.

## Frozen cohort and reference limits

--build creates immutable records only after validating the downloaded references
and image pairings. Published artifacts are exclusive/idempotent: an identical
rerun may validate existing bytes, but changed content is not overwritten. The
provenance file is written last as the completion marker. If publication is
interrupted, rerun with unchanged inputs; incompatible partial artifacts require
explicit diagnosis rather than overwriting a previous cohort.

--validate-only performs no network requests. It checks frozen artifact hashes,
record schema/source revisions/unique IDs/splits, image/reference content hashes,
exact-content split overlap, and preserved source archives/annotation checksums.
Counts are read from PROVENANCE.json; no OCR accuracy or model readiness is implied.

Development selection uses a recorded seed and stable SHA-256 ordering. Exact
image/reference duplicate groups stay in one split; conflicting references for
identical images block publication for review. Upstream source-document IDs are
not supplied reliably for both corpora. Splits therefore establish page/content
disjointness, not certified source-book independence. Near duplicates and prior
model training exposure remain unverified and must be disclosed in any results.

Invalid source polygons/order or malformed table markup are preserved with
per-record warnings and restricted metric eligibility; source annotations are
never clipped or rewritten to look valid. Table checks validate explicit nesting
and spans, not TEDS scores or every row/column geometry. Only actual supplied
annotation types enable capabilities. Text assembly/normalization and quantitative
metrics are TASK-006, not part of acquisition.

Arabic category, localized layout/order and numeric-chart annotations remain
unavailable where not supplied. A page_count of 1 denotes one benchmark image,
which may contain a facing-page spread; it is not a claim of one original PDF page.
LEGACY_ALIASES.json records the Mix invoice_5 / Invoice_5 pairing without renaming
originals; legacy samples are excluded from this official cohort pending verified
source permissions and reference provenance. No OCR-generated reference is created.

Preserve research-only OmniDocBench use restrictions and the Arabic dataset-card
Apache-2.0 attribution. Full license/source notices remain with downloaded originals.
Model inference stays blocked by the separate hardware assessment and future runner
preflight, regardless of successful acquisition.
