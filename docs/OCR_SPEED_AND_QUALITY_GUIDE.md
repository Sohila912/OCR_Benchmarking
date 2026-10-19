# Make PaddleOCR-VL and Qwen faster without losing useful detail

This guide is for the current laptop: approximately 8 GB RAM, an NVIDIA MX350 with 2 GB VRAM, and CPU inference. The Paddle provider uses **PaddleOCR-VL-1.6**, rather than conventional PaddleOCR. These are suggested changes only; creating this guide does not apply them.

## 1. Reduce Paddle page resolution; keep Qwen's existing cap

**Start with Paddle at 200 DPI instead of 300.** In the project-root `.env` file, change:

```dotenv
OCR_PDF_DPI=200
```

Restart the application after editing settings. This setting affects PDF rendering for all providers, including Qwen; Qwen additionally applies its own pixel cap. At 200 DPI, a rendered page has about 56% fewer pixels than at 300 DPI. This reduces rendering, image copying, and preprocessing work; the inference speedup must be measured.

Keep Qwen's current setting initially:

```dotenv
OLLAMA_MAX_IMAGE_PIXELS=1000000
```

**Protect accuracy:** compare a few pages containing small text, Arabic, tables, and multiple columns. If 200 DPI loses important detail, return to 300 DPI. Try 150 DPI only if 200 DPI remains accurate. Lower resolution is a speed tradeoff, not an accuracy improvement. For Qwen, increasing the pixel cap may recover small text, but costs time and memory and may require a larger context.

## 2. Free RAM and process one model at a time

Before starting OCR:

1. Close unused browser tabs, other AI applications, and unnecessary Python processes.
2. Plug the laptop into power and choose Windows' performance power mode if available. Keep ventilation clear.
3. Process all selected documents with Paddle first, then all with Qwen, or the reverse. Avoid repeatedly switching models.

The service unloads other local provider pipelines when switching, so alternating models can repeat initialization. Ollama has a separate model lifecycle: Qwen can remain resident for its configured keep-alive period. If switching from Qwen to Paddle leaves memory tight, wait for Qwen to unload or manually unload it in Ollama before starting Paddle.

**Why it helps:** low available RAM can force Windows to move model data to disk. Reducing competing memory use can improve responsiveness and runtime without lowering image quality. It does not guarantee better recognition accuracy. Avoid parallel inference on this laptop.

Qwen currently stays loaded for 300 seconds after a request. Keeping requests close together can avoid cold starts; extending keep-alive retains RAM for longer and should only be considered when Qwen is the active model.

## 3. Choose settings using a small speed-and-quality comparison

Use 3–5 representative pages: a clean text page, a small-text page, a table, and Arabic or mixed-language content if relevant.

- Record the first request separately, because it includes model loading. Compare subsequent requests to measure warm inference.
- Compare Paddle at 300 and 200 DPI. Keep Qwen at its current one-million-pixel cap as the starting point.
- Check missing lines, wrong numbers, Arabic characters, table cells, and reading order. Choose the fastest setting that preserves the details you need.
- For difficult scans, use a sharp, upright source with good contrast and minimal skew. Crop unnecessary outer margins without cutting off content. Avoid enlarging blurry images: enlargement cannot restore missing detail.

Keep the same source pages across trials and record settings with results. For formal OCR benchmarks, disclose any preprocessing changes so accuracy comparisons remain interpretable.

## Suggested starting point

**Try 200 DPI, free RAM, and group work by model.** Keep Qwen's current image cap until the sample comparison shows a reason to change it. These steps need no new model downloads or hardware.

Qwen will still be slow on this CPU: the previous successful probe took about 547 seconds, including loading and inference. Increasing the timeout only lets a slow request finish; it does not accelerate it. If these steps are insufficient, more RAM can reduce memory pressure, while a GPU with enough VRAM or remote inference offers a larger potential improvement.

## References

- [PaddleOCR-VL parameters and inference backends](https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/pipeline_usage/PaddleOCR-VL.en.md)
- [Ollama model loading, keep-alive, and context settings](https://docs.ollama.com/faq)
