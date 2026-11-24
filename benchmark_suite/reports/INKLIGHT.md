# InkLight OCR benchmark

The model selector and benchmark CLI expose InkLight 0.3.2 as `inklight` (TASK-022). This configuration runs Indra OCR on CPU with four threads, automatic per-line script detection and the original frozen images. The runner retains InkLight's complete native JSON and a normalized prediction for each image. It scores plain text, with line boxes mapped back to original-image coordinates. The optional Docling structure extension is disabled.

## Registered benchmark runs

The registered CPU worker completed all **20 development pages** with zero failures in 65.89 seconds. English normalized CER/WER were **7.29% / 23.63%** on 10 pages and Arabic normalized CER/WER were **25.85% / 41.41%** on 10 pages. The worker starts and loads its model for each page. Its 51.70 seconds of inference include that overhead. [Development evaluation](../results/inklight/evaluations/20261112T091727Z-718581fc/2a3869a2c115-d3c3e005/metrics.json)

The full evaluation converted **1,135/1,135 images** with zero OCR failures. The evaluator scored text on 1,127 pages. Of the eight English pages without a text score, five lacked reference text, two failed the reference geometry check, and one contained a zero-width predicted line box.

| Language | Converted | Text scored | Normalized CER | Normalized WER |
|---|---:|---:|---:|---:|
| English | 745 | 737 | 9.69% | 21.29% |
| Arabic | 390 | 390 | 25.06% | 37.67% |

The registered run recorded 60.06 minutes of session wall time and a peak sampled working set of 0.80 GiB for the coordinator and descendants. Inference includes native startup for each page. English uses annotated reference regions and Arabic uses whole-page content. [Full evaluation metrics](../results/inklight/evaluations/20261116T082501Z-61be2819/633486256392-4087b9c1/metrics.json) · [Page-level scores and coverage](../results/inklight/evaluations/20261116T082501Z-61be2819/633486256392-4087b9c1/per_page_metrics.csv)

## Earlier source-checkout review

| Split | English pages scored | English CER / WER | Arabic pages scored | Arabic CER / WER |
|---|---:|---:|---:|---:|
| Development | 10 | 7.29% / 23.63% | 10 | 25.45% / 41.25% |
| First 100 evaluation images per language | 99 | 10.68% / 21.07% | 100 | 26.12% / 42.42% |

These measurements came from the source checkout before CLI registration. All 200 evaluation images converted, and one English image lacked a text reference. The [results file](INKLIGHT_RESULTS.json) records the review environment, exact matched cohorts, source hashes and comparison with archived outputs. The registered interpreter pins its own dependencies in [the environment manifest](../configs/inklight-requirements.txt).

## Run locally

On the configured Windows machine, from the repository root:

```powershell
$python = 'benchmark_suite/environments/inklight/Scripts/python.exe'
& $python -m benchmark_suite.cli setup --model inklight
& $python -m benchmark_suite.cli run --model inklight --language both --mode quick
& $python -m benchmark_suite.cli run --model inklight --language both --mode full
```

Quick uses 20 development images. Full uses all 1,135 evaluation images. To reproduce the 200-image review cohort on the registered environment, append `--max-documents 200 --sampling language-round-robin` to the full command. A run interrupted by resource preflight can resume at the next missing page with `resume --model inklight --run-dir <saved-run-directory>`. Completed runs can be rescored with `evaluate` and the same arguments.

The [adapter spec](../configs/inklight-spec.json) pins twelve model files, totaling 76,089,598 bytes, and the source revision. For a fresh installation, build the Python package from [the reviewed commit](https://github.com/MahmoudYahiaAhmed/inklight/tree/97efb49e65068ed52a47e7dc4fd0d7cfe4513707) in the isolated interpreter. Install the remaining pinned requirements and place the [Indra model files](https://huggingface.co/datalab-to/indra-ocr/tree/bd02167fdf2005a19962cc15188f8496a2c87d3b) in the directory named by the [run configuration](../configs/inklight.json). The runner verifies the local weights and adapter before inference.
