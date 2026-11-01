# Evaluation policy: benchmark-metrics-v1

Implemented in TASK-006, 2026-11-01 (Africa/Cairo). These are tested calculators,
not OCR model results. Production OCR/evaluation.py and historical benchmark
evaluators are unchanged. Run from the repository root using the existing
`.venv-ocr\Scripts\python.exe`. Direct tested dependencies are pinned in
`benchmark_suite/requirements-metrics.txt`; no packages were installed.

## Reference scope and missingness

Frozen manifest capabilities are necessary gates, not certification that every
region/table is valid for every metric. Apply the manifest gate, the model's
declared capability and the relevant strict reference checks before scoring.
`availability()` returns `NOT_EVALUATED` for absent independent truth and
`NOT_SUPPORTED` for absent model capability; values remain null. Pure calculators
assume that callers have passed those gates. Empty output from a supported model
is a scored miss. A failed inference must be reported as a failure with coverage;
it must not disappear from the cohort or become a fabricated prediction.

English truth supplies individual regions. `references.english_regions` returns
only explicit nonignored `text` fields with original IDs, polygons and order.
It never constructs a certified whole-page transcript from partial text.
English CER/WER requires independent region matching or declared region-crop
evaluation. Match geometry independently of recognized text, use empty output
for missed eligible regions and disclose unmatched predictions and matching
coverage. The runner in TASK-007 must implement this routing. Do not use text
similarity to select the most favorable matching or compare a partial reference
to the model's full-page output. LaTeX-only equations, HTML-only tables and
untranscribed figures are excluded from this text scope and remain separate
tasks. This restricts what an eventual English OCR score will mean.

Arabic has publisher page Markdown. Keep source-serialization raw scores separate
from common-content scores. `markdown_content` defines the symmetric CommonMark
conversion for reference and prediction: retain textual/code content, link labels
and HTML visible cell text in source order; omit link URLs and image alt text;
insert block/cell boundaries; retain literal math/LaTeX source. No OCR, rendered
math conversion, visual reordering, numeral conversion or ghost/watermark text is
invented. Apply conversion to both sides only when both declare Markdown format;
plain-text predictions must not be interpreted as Markdown syntax. Raw scores
must always retain the unconverted strings. Record input formats and content
policy separately. Raw serialization measures formatting as well as OCR;
math-heavy results are representation-sensitive. Page images can contain spreads.

## Text formulas and Arabic transformations

Characters are Unicode code points, including whitespace in raw text, rather
than grapheme clusters. Words are Unicode whitespace-delimited, case-sensitive
tokens. Distance D is exact unit-cost Levenshtein distance via RapidFuzz.

| Metric | Definition | Direction |
|---|---|---|
| CER / WER | D(reference,prediction) / reference unit count | Lower |
| Character / word accuracy | max(0, 1 - corresponding error rate) | Higher |
| NED | Character D / max(reference length, prediction length, 1) | Lower |
| Exact match | Equality of the two strings; corpus rate is their mean | Higher |
| Bag-unit precision / recall / F1 | TP is multiset intersection; FP=predicted units-TP; FN=reference units-TP | Higher |

CER/WER may exceed one because insertions are unbounded. Accuracy is an explicitly
clipped error complement, not alignment hit rate. Bag-unit matching is available
for both code points and words; it ignores order and is not interchangeable with
CER/WER or detection F1. PR=TP/(TP+FP), RE=TP/(TP+FN),
F1=2TP/(2TP+FP+FN). Each zero denominator returns null.

Empty reference: its error rate and accuracy are null even if the prediction is
empty. Edit counts are retained. Empty/empty NED=0 and exact=true;
empty/nonempty NED=1 and exact=false. Nonempty/empty CER=WER=1 for applicable
units. Corpus micro error rates sum **all** edits, including insertions on empty
references, and divide by all reference units. If the total denominator is zero
the rate is null. Macro means exclude undefined per-item rates and count them.

`text.evaluate` always returns raw and normalized results plus every option.
Defaults normalize NFC and collapse whitespace only. Optional transformations,
in this order, are Unicode normalization (`none`, NFC or NFKC), Arabic mark
removal, alef folding, hamza folding, tatweel deletion and whitespace collapse.
The original strings/reference files are never changed.

- Diacritics: remove U+0610–061A, 064B–065F, 0670, 06D6–06DC,
  06DF–06E4, 06E7–06E8, 06EA–06ED. Other combining marks are retained.
- Alef: آأإٱ → ا. Hamza: ؤئأإ → وياا; standalone ء is retained.
- Tatweel: remove U+0640. Whitespace: Python Unicode split/join with one space.
- No default case folding, punctuation deletion, Arabic/Persian digit folding,
  ya/alif-maqsura folding, ta-marbuta folding or RTL string reversal.

These folds can erase meaningful distinctions. All are off by default and must
be recorded when enabled. `unicode=none` with diacritic removal can remove
decomposed hamza marks U+0654/0655; choose and disclose Unicode normalization
deliberately. Show Arabic raw and normalized CER/WER separately, never select
normalization after seeing a model's scores.

## Layout and detection

The versioned canonical source-label map is in `configs/evaluation.json`.
Publisher title maps to heading, text_block to paragraph; caption subclasses
share caption; equation and footnote subclasses have explicit mappings. Figure
is not silently relabeled chart. Model mappings require review in TASK-007;
unknown model labels raise in `canonicalize`. Unsupported/unannotated classes
must be disclosed and excluded consistently, not treated as negatives.

`layout_reference` converts source polygons to axis-aligned envelopes in source
pixel coordinates, rejecting invalid/out-of-page geometry without clipping.
This is box IoU, not polygon IoU. Source labels excluded from the map are returned
as explicit excluded regions. The runner must enforce evaluable scope and avoid
treating excluded/unlabeled content as background negatives. Mask-overlap policy
must be fixed before results; the metric function itself does not infer masks.

IoU = intersection area / union area. Boxes require finite, positive-area
coordinates. Match predictions in descending confidence, stable input-order ties,
to the highest-IoU unmatched truth of the same class and page. Accept IoU >= the
threshold, default 0.5; equal IoUs use the lower reference index. One truth can
match once. After valid truth matching, same-class/page ignored truth suppresses
otherwise unmatched overlapping predictions at that threshold.

Return per-class and micro PR/F1, TP/FP/FN, matched pairs and mean matched IoU.
Matched IoU alone excludes misses and must be accompanied by recall. AP uses
the all-points monotonically interpolated precision envelope, integrated at each
true-positive recall increment. Classes with zero nonignored truth have null AP;
their scoped false positives still affect micro detection counts. mAP is the mean
over classes with truth. `mean_ap` also averages over configured IoU thresholds
0.50:0.05:0.95. This is **not COCO 101-point AP**. Evaluate the full cohort together,
preserving page IDs/confidences; averaging per-page AP gives a different quantity.
Table/chart/figure detection reuse this calculator with their annotated classes.

## Reading order

Use independently geometry-matched truth block IDs. `ordered_reference` selects
nonignored publisher regions with explicit order, sorts those order values and
rejects ambiguous orders/IDs. Never infer truth from x/y position or RTL language.
Predicted order must contain unique reference IDs only; unmatched predictions are
reported by detection separately. Ties need an explicit independently justified
policy and are currently rejected, so this is Kendall tau-a without ties.

For M matched pairs and I inversions: normalized inversion rate=I/M;
Kendall tau=1-2I/M. Both are null if M=0. For P total reference pairs,
reading-order accuracy=(M-I)/P; missing pairs count as incorrect. Item coverage
and pair coverage M/P are mandatory. Exact order requires identical complete
lists. Multi-column or RTL strata use annotated source groups and these same
formulas; no special visual heuristic is a score. Arabic primary order truth is
absent, so Arabic reading-order accuracy remains NOT_EVALUATED.

## Tables

Evaluate independently paired table fragments; table localization/misses are
reported separately through detection. Plain text has no inferred structure and
is NOT_SUPPORTED for TEDS. HTML fragments must contain exactly one complete
table, with explicit table/section/tr/td/th nesting, balanced inline markup and
positive row/column spans. A strict logical grid rejects overlapping spans,
spans past the last row and ragged/empty grids. No browser repair occurs.

TEDS here is a genuine minimum-cost ordered tree edit similarity. Insertion and
deletion cost one and promote children. Rename costs one for unequal tag/spans;
otherwise td/th rename costs cell-content token Levenshtein distance divided by
the longer token sequence length. Inline markup tags are tokens and text is
code points. Structure-only TEDS sets cell-content rename cost to zero. The exact
ordered-forest dynamic program is independently tested against exhaustive valid
tree mappings. Similarity=max(0,1-distance/max(tree node counts)).

The named **ordered-tree-teds-root-th-v1** variant includes the root in its
denominator, treats th as a content cell, and preserves explicit section tags.
These choices differ from the [PubTabNet reference implementation](https://github.com/ibm-aur-nlp/PubTabNet/blob/master/src/metric.py),
which uses APTED and excludes the table root in normalization. Do not publish this
variant as numerically interchangeable with official PubTabNet TEDS. The source
was consulted for metric semantics; the recurrence/parser here are independently
implemented. In particular no string similarity is substituted for tree edits.

Cells match exact (row,column,rowspan,colspan) in zero-based logical grids.
Return cell PR/F1; analogous sets produce merged-cell and explicit th-header
PR/F1. Header scores describe markup preservation, not inferred semantic headers
inside td cells. Row/column count exactness is separate from structure accuracy:
structure accuracy is the fraction of reference rows/columns whose complete
covering-cell span descriptors equal the predicted descriptors. Unmatched
reference cells are incorrect for cell-text exact rate; matched-cell CER/WER
are also returned with coverage. td content strips inline tags for this separate
cell-text diagnostic while TEDS retains them. Extra cells affect cell F1/TEDS.

Default limits: 150 tree nodes per table, 200,000 memo states per edit calculation.
Tables beyond limits receive NOT_EVALUATED with reason and null value, rather
than approximate scores. A malformed independent reference is NOT_EVALUATED;
a malformed/empty structured prediction on a valid reference scores TEDS zero.
These limits/settings and coverage must be identical across compared models;
resource-limit missingness can depend on prediction structure and must be
disclosed rather than silently excluded from rankings.

## Chart tasks

Detection/localization uses annotated boxes and layout functions. Type accuracy
uses exact class equality on independently matched chart IDs; missing predictions
are wrong and extras/coverage are disclosed. Chart-region text uses the text
metrics. Numeric values require independent keys encoding chart, series, category
and unit. A value matches if absolute error <= max(absolute tolerance,
relative tolerance * abs(reference)), defaults 0 and 0.01. Wrong values create
both FP and FN; unmatched values also count. Report PR/F1, reference-denominator
accuracy and matched MAE with coverage; MAE is null without matches. Completeness
is PR/F1 on explicitly annotated component IDs, not guessed axes/legends.
NaN/infinity and negative/nonfinite tolerances are rejected. The primary cohort
has no numeric/type/component truth, so these scores remain NOT_EVALUATED;
the existence of calculators does not imply that the datasets support them.

## Aggregation, uncertainty and reporting

Aggregate separately by language and supplied source category. Unknown Arabic
categories remain unknown. Report raw counts, missing/failure reasons and
eligible/attempted/scored coverage for every stratum. `summarize` returns count,
missing, mean, median, sample standard deviation (n-1), min and max. A singleton
has null sample standard deviation. `aggregate_ratio` returns micro and macro
separately; empty-reference insertions remain in micro. Apply scores at their
declared region/page/document unit and report that unit; don't combine region
and page means without explanation. No composite ranking is implemented.

`bootstrap` resamples entire supplied clusters with replacement, same number of
clusters each replicate, seed 1729, default 2,000 replicates. For micro ratios it
recomputes the summed numerator/denominator each replicate; for means it includes
all rows of the sampled clusters. The point estimate is the pooled row statistic,
not an equal-weight mean of document means. CI is the 2.5th/97.5th percentile with
linear interpolation. Unknown cluster IDs are rejected. Fewer than two clusters
cannot yield an uncertainty interval. Undefined zero-denominator ratio replicates
are excluded and counted, and fewer than two defined replicates yields null CI.
Use the same seed and aligned IDs for paired comparisons; a hypothesis test or
paired-difference interval needs an explicit future comparison implementation.

This corpus has UNKNOWN source-document grouping: use explicit **page** cluster
IDs, label the interval a page bootstrap and state that document independence
is unverified. Do not relabel image IDs as source books or claim document-level
confidence. Document bootstrap is available for future verified grouping only.
Nonfinite measurements are rejected; missing observations are never zero-filled.
Failure sensitivity and missingness must accompany intervals.

## Reference-only audit and verification

`scripts/audit_metric_references.py` reads all 1,155 frozen references and prints
only metadata in [METRIC_REFERENCE_AUDIT.json](METRIC_REFERENCE_AUDIT.json).
It does not run OCR or manufacture ground truth. The frozen manifest/source
files are unchanged; stricter grid/resource exclusions are recorded separately.

| Subset | Text regions (English) | HTML fragments | Ready before tree state limit | Node limit | Grid/parser invalid | Manifest gate |
|---|---:|---:|---:|---:|---:|---:|
| Development English | 114 | 2 | 1 | 1 | 0 | 0 |
| Evaluation English | 11,259 | 241 | 194 | 41 | 1 | 5 |
| Development Arabic | n/a | 4 | 3 | 0 | 0 | 1 |
| Evaluation Arabic | n/a | 69 | 59 | 5 | 2 | 3 |

HTML fragment counts are tables, not pages. READY is reference readiness only;
state limits and prediction validity are checked at scoring time. The three
additional invalid table grids do not change or remove frozen pages. All 753
manifest-eligible English layout pages and 740 order pages pass source conversion.

```powershell
.venv-ocr\Scripts\python.exe -m pytest benchmark_suite/tests/test_metrics.py -q
.venv-ocr\Scripts\python.exe -m pytest benchmark_suite/tests -q
.venv-ocr\Scripts\python.exe -m ruff check benchmark_suite
.venv-ocr\Scripts\python.exe benchmark_suite/scripts/audit_metric_references.py
.venv-ocr\Scripts\python.exe benchmark_suite/scripts/prepare_datasets.py --validate-only
```

Tests include hand-calculated edit/PR/AP/order/numeric cases; Arabic raw/folded
differences; empty inputs and hallucinated insertions; ignored/duplicate detections;
cell spans/headers/invalid grids; exhaustive tiny-tree mapping comparisons; missing
references and deterministic cluster bootstrap. Model integrations, output routing,
run manifests and timings remain TASK-007; no model was installed or executed.
