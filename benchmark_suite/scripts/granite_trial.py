"""Bounded, pinned Granite Docling inference; raw DocTags are always local."""

import gc
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import sys
import time
import traceback


def worker(args):
    from docling_trial import SUITE, write_json
    from windows_job import limit_current_process

    root, output = args.asset_root, args.output
    state = {"scope": "bounded development-page feasibility trial; not a full evaluation",
             "model": "ibm-granite/granite-docling-258M",
             "revision": "982fe3b40f2fa73c365bdb1bcacf6c81b7184bfe", "language": args.language,
             "status": "RUNNING", "documents_processed": 0, "memory_limit_bytes": args.memory_limit,
             "dtype": "float32", "device": "cpu", "attention": "sdpa", "threads": 2,
             "maximum_new_tokens": 8192, "maximum_generation_seconds": 600,
             "decoding": "greedy; one beam", "accuracy_scores": None}
    phase = "memory_guard"
    started = time.perf_counter()
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
        limit_current_process(args.memory_limit)
        (root / "tmp").mkdir(parents=True, exist_ok=True)
        os.environ.update(HF_HOME=str(root / "hf"), TORCH_HOME=str(root / "torch"),
            HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", CUDA_VISIBLE_DEVICES="",
            OMP_NUM_THREADS="2", MKL_NUM_THREADS="2", TEMP=str(root / "tmp"), TMP=str(root / "tmp"),
            TOKENIZERS_PARALLELISM="false")
        print(f"Memory cap {args.memory_limit / 1024**3:.2f} GiB; importing pinned CPU model runtime", flush=True)
        phase = "imports"
        import torch
        from PIL import Image
        from transformers import AutoModelForImageTextToText, AutoProcessor, TextStreamer
        print("CPU Torch and Transformers imports complete", flush=True)

        torch.set_num_threads(2)
        torch.set_num_interop_threads(1)
        if torch.version.cuda is not None:
            raise RuntimeError("Expected the existing CPU-only Torch build")
        state["versions"] = {name: importlib.metadata.version(name) for name in
                             ("torch", "torchvision", "transformers", "docling-core", "docling")}
        phase = "asset_verification"
        model_path = root / "model"
        digest = hashlib.sha256()
        with (model_path / "model.safetensors").open("rb") as stream:
            while block := stream.read(1024**2):
                digest.update(block)
        if digest.hexdigest() != "1cdad234deb1cde18ee6a586f849057f19851daf1fedce2e40aff791dbe46f61":
            raise ValueError("Pinned model weight checksum mismatch")
        record = json.loads(args.record.read_text(encoding="utf-8"))
        original = SUITE / record["source_path"]
        source = root / "inputs" / (record["file_hash"] + original.suffix)
        source.parent.mkdir(parents=True, exist_ok=True)
        if not source.exists():
            with original.open("rb") as incoming, source.open("xb") as outgoing:
                shutil.copyfileobj(incoming, outgoing)
        if hashlib.sha256(source.read_bytes()).hexdigest() != record["file_hash"]:
            raise ValueError("Frozen D: input checksum mismatch")
        state.update(document_id=record["document_id"], source_sha256=record["file_hash"],
                     processing_input_path=str(source))
        phase = "model_initialization"
        print("Loading local processor and float32 model; no GPU or remote inference", flush=True)
        before = time.perf_counter()
        processor = AutoProcessor.from_pretrained(model_path, local_files_only=True, trust_remote_code=False)
        model = AutoModelForImageTextToText.from_pretrained(model_path, local_files_only=True,
            trust_remote_code=False, dtype=torch.float32, attn_implementation="sdpa").to("cpu").eval()
        state["initialization_seconds"] = time.perf_counter() - before
        phase = "image_preprocessing"
        with Image.open(source) as opened:
            image = opened.convert("RGB")
        messages = [{"role": "user", "content": [{"type": "image"},
                     {"type": "text", "text": "Convert this page to docling."}]}]
        prompt = processor.apply_chat_template(messages, add_generation_prompt=True)
        inputs = processor(text=prompt, images=[image], return_tensors="pt").to("cpu")
        prompt_length = inputs["input_ids"].shape[1]
        state["input_tensor_shapes"] = {key: list(value.shape) for key, value in inputs.items() if hasattr(value, "shape")}
        state["input_tokens"] = prompt_length
        write_json(output / "configuration.json", state)
        phase = "generation"
        print(f"Generating {args.language} DocTags, up to 8192 tokens / 600 seconds", flush=True)
        partial = (output / "doctags.partial.txt").open("x", encoding="utf-8")

        class ArtifactStreamer(TextStreamer):
            def __init__(self):
                super().__init__(processor.tokenizer, skip_prompt=True, skip_special_tokens=False)
                self.first = True
                self.count = 0

            def put(self, value):
                super().put(value)
                if self.first:
                    self.first = False
                else:
                    self.count += value.numel()
                    if self.count % 128 == 0:
                        print(f"Generated tokens: {self.count}", flush=True)

            def on_finalized_text(self, text, stream_end=False):
                partial.write(text)
                partial.flush()

        streamer = ArtifactStreamer()
        before = time.perf_counter()
        try:
            with torch.inference_mode():
                generated = model.generate(**inputs, max_new_tokens=8192, max_time=600,
                    do_sample=False, num_beams=1, use_cache=True, streamer=streamer,
                    stop_strings=["</doctag>", "<|end_of_text|>"], tokenizer=processor.tokenizer)
        finally:
            partial.close()
        state["generation_seconds"] = time.perf_counter() - before
        native_ids = generated[:, prompt_length:]
        state["generated_tokens"] = native_ids.shape[1]
        doctags = processor.batch_decode(native_ids, skip_special_tokens=False)[0]
        (output / "doctags.txt").write_text(doctags, encoding="utf-8")
        eos = model.generation_config.eos_token_id
        eos = eos if isinstance(eos, list) else [eos]
        ended = int(native_ids[0, -1]) in eos or "</doctag>" in doctags or "<|end_of_text|>" in doctags
        state["natural_or_document_stop"] = ended
        if not ended and (state["generated_tokens"] >= 8192 or state["generation_seconds"] >= 600):
            state.update(status="INCOMPLETE", phase="generation", error_type="GenerationLimitReached",
                         error="Output reached the token/time bound without a natural or closing-document stop")
        else:
            del model, inputs, generated, native_ids
            gc.collect()
            phase = "doctags_conversion"
            print("Generation ended; converting native DocTags to Docling JSON/Markdown", flush=True)
            from docling_core.types.doc import DoclingDocument
            from docling_core.types.doc.document import DocTagsDocument

            tagged = DocTagsDocument.from_doctags_and_image_pairs([doctags], [image])
            document = DoclingDocument.load_from_doctags(tagged, document_name=record["document_id"])
            write_json(output / "document.json", document.export_to_dict())
            markdown = document.export_to_markdown()
            (output / "prediction.md").write_text(markdown, encoding="utf-8")
            if "benchmark_document" in record:
                from types import SimpleNamespace
                from OCR.providers.base import OCRDocument
                from OCR.providers.docling import normalize_docling
                from OCR.schemas import BoundingBox
                from benchmark_suite.runners.schemas import Prediction, Table

                original_document = OCRDocument.model_validate(record["benchmark_document"])
                normalized = normalize_docling(original_document,
                    SimpleNamespace(document=document, errors=[], status="success"),
                    state["versions"]["docling-core"], state["revision"])
                normalized.model_name = state["model"]
                normalized.provider_metadata.update(dtype="float32", device="cpu", attention="sdpa",
                    generation_seconds=state["generation_seconds"], generated_tokens=state["generated_tokens"])
                for page in normalized.pages or []:
                    for order, block in enumerate(page.blocks or []):
                        block.reading_order = order
                tables = []
                for index, table in enumerate(document.tables):
                    prov = table.model_dump(mode="json")["prov"]
                    if len(prov) != 1:
                        raise ValueError("Single-image table requires unambiguous provenance")
                    box = prov[0]["bbox"]
                    bounds = BoundingBox(x_min=min(box["l"], box["r"]), x_max=max(box["l"], box["r"]),
                        y_min=min(box["t"], box["b"]), y_max=max(box["t"], box["b"]), units="points",
                        origin="bottom_left" if box["coord_origin"] == "BOTTOMLEFT" else "top_left")
                    tables.append(Table(table_id=f"table-{index}", page_number=prov[0]["page_no"],
                        html=table.export_to_html(doc=document), bounding_box=bounds))
                prediction = Prediction(result=normalized, text_format="markdown", tables=tables,
                    coordinate_notes="Native DocTags loc coordinates decoded by Docling into page points; hierarchy reading order; native table HTML")
                (output / "prediction.json").write_text(prediction.model_dump_json(), encoding="utf-8")
            state.update(status="SUCCESS", documents_processed=1, markdown_characters=len(markdown),
                         output_pages=len(document.pages), output_tables=len(document.tables))
    except Exception as exc:
        state.update(status="FAILED", phase=phase, error_type=type(exc).__name__, error=str(exc),
                     traceback=traceback.format_exc())
        traceback.print_exc()
    finally:
        state["wall_seconds"] = time.perf_counter() - started
        write_json(output / "result.json", state)
        print(json.dumps({key: state[key] for key in ("status", "language", "documents_processed")}), flush=True)
    return 0 if state["status"] == "SUCCESS" else 1
