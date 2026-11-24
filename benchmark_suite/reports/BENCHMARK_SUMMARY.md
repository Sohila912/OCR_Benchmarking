# OCR benchmark: management progress report

**As of 24 November 2026 · Arabic and English OCR · Interim results**

## Current position

InkLight completed the full frozen evaluation, converting all 1,135 images with zero failures. The evaluator scored text on 1,127 images. PaddleOCR has a separate 200-page evaluation checkpoint and Tesseract has 437 saved predictions. The other models have different coverage.

| Project area | Position |
|---|---|
| Shared framework | Foundation tasks 1–8 completed: research, frozen datasets, metrics, common runner, checkpoints and Windows execution tools |
| Dataset | 20 development pages: 10 English and 10 Arabic; separate frozen evaluation set: 1,135 pages, comprising 745 English and 390 Arabic |
| Model assessment | Ten candidates reviewed; some blocked before inference, others tested on development or partial evaluation cohorts |
| Full evaluation | InkLight completed 1,135 pages; nine other candidates have partial evaluations or feasibility records |
| Final deliverables | Comprehensive comparison, final visualizations and final benchmark report remain pending |

## Results by model

| Model | What has actually been achieved | Current limitation |
|---|---|---|
| **PaddleOCR** | 20/20 development conversions; **200/200 evaluation conversions**, with 199 text-scored pages | 935 evaluation pages remain; continuation was deferred to test other models |
| **Tesseract** | 20/20 development conversions; **437/1,135 evaluation predictions saved**: 390 Arabic and 47 English; zero OCR failures | Paused when available RAM fell below the runner's 2-GiB start floor; 698 evaluation pages remain |
| **Docling + Tesseract** | 19/20 development conversions; text scores for 10 English and 9 Arabic pages | One Arabic timeout; full evaluation deferred at the user's request |
| **Docling + EasyOCR** | At reduced OCR scale 1.0, **8/10 English development pages succeeded**; Arabic model downloaded and verified on D: | Two English pages repeatedly crashed; first Arabic page failed four attempts, including a memory-allocation error in an alternate CPU backend |
| **Baidu Unlimited-OCR-2** | **20/20** successful hosted development conversions (10 English and 10 Arabic pages scored) | 0/1,135 evaluation pages completed: first page aborted twice on the hosted worker on 24 November; hosted weight revision is unverified |
| **InkLight 0.3.2** | 20/20 development and **1,135/1,135 evaluation** conversions | 1,127 evaluation pages scored for text; optional structure disabled. [Results](INKLIGHT.md) |
| **Granite Docling** | Two bounded feasibility conversions produced output; the first Arabic output contained no recognized text | Subsequent generation/runtime instability; no completed development evaluation |
| **Surya OCR** | Hardware/backend readiness investigated; no successful OCR inference | Selected backend/environment could not be established within the tested hardware constraints |
| **PaddleOCR-VL** | Hardware/software feasibility assessed; no successful OCR inference | GPU/RAM/runtime constraints |
| **Marker** | Hardware/software feasibility assessed; no successful OCR inference | Hardware/runtime constraints before inference |

## Measured text recognition results

**CER and WER are character and word error rates; lower is better.** A successful
conversion means the pipeline produced a completed output, not that the text was
correct. These rows are separate checkpoints, not a performance ranking.

| Model and cohort | Text-scored pages, English / Arabic | English CER / WER | Arabic CER / WER |
|---|---:|---:|---:|
| InkLight — full registered evaluation | 737 / 390 | 9.69% / 21.29% | 25.06% / 37.67% |
| InkLight — source-checkout evaluation subset | 99 / 100 | 10.68% / 21.07% | 26.12% / 42.42% |
| InkLight — registered development set | 10 / 10 | 7.29% / 23.63% | 25.85% / 41.41% |
| Baidu — hosted development set | 10 / 10 | 5.85% / 19.63% | 18.59% / 30.20% |
| PaddleOCR — 200-page evaluation subset | 99 / 100 | **14.17% / 23.48%** | **51.53% / 71.34%** |
| PaddleOCR — 20-page development set | 10 / 10 | 7.98% / 23.75% | 56.29% / 77.29% |
| Tesseract — 20-page development set | 10 / 10 | 8.96% / 24.21% | 29.04% / 45.77% |
| Docling + Tesseract — development run | 10 / 9 | 26.69% / 40.09% | 50.26% / 67.47% |

All rates above use the shared text normalization policy. English is scored
against independently allocated reference-region text; Arabic uses page-content
text, so their reference scopes differ. Paddle's evaluation subset selected the
first 100 pages per language deterministically; it is not a random corpus sample.
In that PaddleOCR subset, one English page lacked a text reference. In the full InkLight run, five English pages lacked reference text, two lacked eligible reference geometry, and one had a zero-width predicted line box. The
Docling + Tesseract timeout is also excluded from text scoring, not zero-filled.
Source-document independence is unverified. These limits prevent an overall
accuracy ranking from these checkpoints.

EasyOCR's eight English successes **do not yet have
published text accuracy scores in their current reports**. No full-evaluation
score is available for Tesseract's incomplete 437-page run.

## Runtime, resources and evidence

Paddle's 200-page batch took **97.89 minutes**, with sampled peak process and
descendant RSS of **0.71 GiB**. Timings include fresh worker startup and related
processing overhead; sampled RSS can miss short peaks. These are measured local
CPU results, not projected full-run performance.

The laptop has 12 GB installed RAM (about 11.74 GiB usable) and an MX350 with
2-GiB VRAM. Available RAM varies with other applications. D: holds downloaded
assets, isolated runtimes, native outputs and reviewed copies; disk capacity does
not replace physical RAM. Windows paging settings have not been changed.

Baidu runs on a free external hosted demo, so its quota, hardware and timing
boundary differ from local CPU tests. No paid service was enabled. Model support
for layout, reading order and tables varies; unsupported outputs and missing
references are recorded explicitly rather than treated as zero scores.

## What remains to finish

1. **Complete consistent evaluation coverage.** Paddle has 935 pages remaining.
   Tesseract has 698 remaining; its saved run must be recovered with its recorded
   execution identity before continuation, or replaced by a clearly versioned run.
2. **Finish the development checkpoints.** Docling + Tesseract has one timeout to resolve. EasyOCR and
   Granite need their recorded native, memory or generation failures investigated.
3. **Score and review saved outputs.** In particular, distinguish EasyOCR
   conversion completion from text quality, and report failures and coverage.
4. **Produce the final comparison.** Use matching cohorts, disclose local versus
   hosted execution, and keep text, structure and resource results separate.

**Management takeaway:** the project has a working, checkpointed benchmark and
useful interim evidence. The remaining work is completing comparable evaluations
and resolving execution blockers.

## Supporting reports

- [Paddle: 200-page evaluation results](PADDLE_EVALUATION_200.md)
- [Tesseract: development and saved evaluation coverage](TESSERACT.md)
- [Docling + Tesseract](DOCLING_TESSERACT.md)
- [Docling + EasyOCR: English and Arabic attempts](DOCLING_EASYOCR.md)
- [Baidu Unlimited-OCR: completed 20-page development set](BAIDU_UNLIMITED_OCR.md)
- [Granite Docling](GRANITE_DOCLING.md)
- [Hardware compatibility assessment](MODEL_HARDWARE_COMPATIBILITY.md)

This report summarizes the saved project evidence as of the date above. Later
execution may change these counts; individual reports retain the underlying
configuration, artifact identities and failure records.
