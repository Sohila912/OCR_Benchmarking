# Granite Docling 258M: CPU development checkpoint

2026-11-03 (Africa/Cairo), TASK-016, explicitly approved after the user saved
and deferred the full Docling + Tesseract evaluation. The preceding checkpoint
was pushed and remotely verified at `6b92577626686fb83ffe93ec17841474d122fdee`.

## Exact model and execution

`ibm-granite/granite-docling-258M`, revision
`982fe3b40f2fa73c365bdb1bcacf6c81b7184bfe`. Weight file 515,093,104 bytes,
SHA256 `1cdad234deb1cde18ee6a586f849057f19851daf1fedce2e40aff791dbe46f61`.
All 13 downloaded model/processor/tokenizer/template files have SHA256s in
GRANITE_DOCLING_ASSETS.json and the registered spec. Apache-2.0 model weights;
Docling code MIT. The publisher describes Arabic support as experimental.
Sources: [pinned model card](https://huggingface.co/ibm-granite/granite-docling-258M/blob/982fe3b40f2fa73c365bdb1bcacf6c81b7184bfe/README.md),
[IBM documentation](https://www.ibm.com/granite/docs/models/docling).

Models, worker environment, coordinator libraries, caches, byte-verified original
input copies and native outputs are on `D:/OCR_Benchmarking_Assets/granite_docling`.
The CPU worker reuses the isolated Docling runtime on D:, with Torch 2.14.1,
Torchvision 0.29.1, Transformers 5.22.1, Docling 2.143.1 and docling-core 2.105.0.
Full resolved worker pins are in configs/docling-easyocr-trial-requirements.txt.
A small coordinator Python launcher/pyvenv metadata lives under the ignored suite
model environment to satisfy strict CLI path validation; its libraries are on D:.
The production Python environment was not upgraded.

CPU float32, SDPA attention, two threads, batch one, native image processor
(default resize/splitting), greedy one-beam decoding with KV cache. Prompt:
`Convert this page to docling.` Maximum 8,192 new tokens and 600 seconds per
generation; natural/document stop required when a limit is reached. An owned
worker has a 15-minute outer deadline, a Windows job committed-memory cap of
at most 4 GiB, 768 MiB system reserve and a live 512-MiB available-RAM abort.
The available-RAM starting floor for development is 3 GiB: a conservative suite
policy, not an IBM minimum. No quantization, GPU, remote inference or automatic
fallback. Inputs retain original pixels; generated DocTags remain on D:.

Each development page starts a fresh worker. Shared-runner inference therefore
includes imports, asset verification, model initialization, native preprocessing,
generation, DocTags parsing, normalization/export and local IPC. Native model
initialization/generation times are also saved. These timing boundaries differ
from persistent-worker Docling + Tesseract and must be disclosed in comparisons.

## Feasibility attempts and setup issues

The initial attempt at `trials/20261103T103226Z-8b95b604` loaded the model but
failed before generation because the download filter omitted chat_template.jinja.
This was a setup error, not a RAM or inference failure. The 588-byte template was
retrieved from the same pinned revision and hashed; future download filters must
include `*.jinja` alongside `*.json`, `*.txt`, `*.safetensors` and `README.md`.

The corrected trial at `trials/20261103T103457Z-6e1e5c9a` completed one frozen
English and one Arabic development image. English: 484 generated tokens, 93.15 s
generation, 128.37 s supervised wall, 910 Markdown characters. Arabic: 102 tokens,
32.78 s generation, 44.89 s wall, 78 Markdown characters. Peak sampled process
plus descendants RSS was 2,256,871,424 bytes (2.10 GiB); private-memory peak was
2,704,494,592 bytes. RSS is sampled, includes shared pages and is not an allocator
peak. Both generations closed naturally, but the Arabic prediction contained only
five picture regions and no recognized text despite a nonempty reference.
Successful conversion does not establish correct recognition.

Before the development attempt, available RAM fell to about 1.6 GiB. The unrelated
Ollama desktop app used about 3.1 GiB RSS. Under the user's existing instruction to
end unrelated RAM consumers, only the identified Ollama app/server were stopped;
subsequent runner preflight measured 5,174,730,752 available bytes.

Development attempt `20261103T104517Z-8e470899` stalled during imports and its
owned worker was terminated at the 900-second deadline. No generation occurred.
The runner then hit WinError 5 publishing the failure bundle. The original staged
bundle was retained and its rename succeeded on retry. The run remains interrupted
and is not a completed evaluation. The isolated diagnostic retry completed imports,
generation and normalized export in 48.80 s; the import stall did not recur there.
Added a bounded retry for this specific transient Windows publication error;
existing result bundles are never overwritten. Periodic diagnostic thread dumps
were temporarily enabled for the next attempt, then removed after a native crash.

## Development evaluation

The fresh canonical run `20261103T110250Z-f24d0a5f` saved two page bundles:
one successful conversion (the first Arabic image with no recognized text), and
one failed worker. The Windows Application Error event identifies that worker
PID 5832 with exception `0xc0000005` in python313.dll. Its log ends during a
periodic diagnostic stack dump. This establishes a native Python crash, not its
root cause or a model RAM minimum. The coordinator stopped the next owned worker
and saved an interrupted checkpoint. No completed evaluation was generated.

The affected Arabic page was then retried without periodic stack dumps at
`diagnostics/page-two-no-stack-dump`, under a 4-GiB Windows job cap. It did not
crash, but generated **5,121 tokens** without EOS/closing DocTags. Of 2,725 decoded
characters, 2,515 were repeated Arabic tatweel (U+0640). The worker recorded
`INCOMPLETE / GenerationLimitReached`, zero completed documents. Generation took
620.87 seconds, total worker time 629.06 seconds. The configured 600-second
Transformers generation bound is checked between generation steps and is a soft
limit; actual duration is reported rather than rounded down. A separate parent
15-minute deadline remains enforced by the registered adapter.

TASK-016 is **BLOCKED: ARABIC_GENERATION_LIMIT_AND_RUNTIME_INSTABILITY** for
this tested configuration. It is not marked hardware-incompatible: bounded
English/Arabic loading and some conversions worked. Removing diagnostic dumps
allowed the affected page to run longer, but does not by itself prove the crash
cause. Reliable Arabic recognition/generation and a completed development run
remain unresolved. No decoding tweaks, quantization or silent model substitution
were introduced to improve the observed result.

The 20-page development evaluation is incomplete; the full 1,135-page evaluation
was not started. CER/WER, layout/table scores and official selected-run markers
remain unavailable for this checkpoint. Do not rank it against completed model
runs or treat missing scores as zeros. TASK-017 Baidu remains unapproved.

Verification: 210 suite tests passed and Ruff passed. Added tests cover corrupt
frozen inputs, rejecting truncated worker output, transient Windows publication
retry and preservation of existing bundles. Raw native outputs and all diagnostic
artifacts remain on D:. See GRANITE_DOCLING_RESULTS.json for exact outcomes and
source-evidence hashes. A reviewed copy is saved under
`D:/OCR_Benchmarking_Assets/granite_docling/reports/checkpoint-20261103`.


## Reproduction

From the repository root, with the pinned assets/runtime available:

```powershell
benchmark_suite\environments\granite_docling\Scripts\python.exe -m benchmark_suite.cli run --model granite_docling --language both --mode quick --json
.venv-ocr\Scripts\python.exe benchmark_suite\scripts\try_granite_docling.py --python D:/OCR_Benchmarking_Assets/docling_easyocr/venv/Scripts/python.exe --asset-root D:/OCR_Benchmarking_Assets/granite_docling --max-memory-gib 4
```

Execution additionally requires active TASK-016 approval in the validated tracker.
Historical interrupted runs need their original recorded code identity; preserve
their artifacts rather than bypass integrity checks or overwrite them.
