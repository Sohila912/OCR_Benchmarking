"""Pinned CPU standard PaddleOCR with local mobile detector/recognizers on D:."""

import hashlib
import importlib.metadata
import json
import os
import shutil
import time
import traceback


def worker(args):
    from docling_trial import SUITE, write_json
    from windows_job import limit_current_process

    root, output = args.asset_root, args.output
    state = {"model": "Standard PaddleOCR 3.6.0 / PaddlePaddle 3.2.2 CPU",
        "scope": "bounded development trial; not a full evaluation", "language": args.language,
        "status": "RUNNING", "documents_processed": 0, "memory_limit_bytes": args.memory_limit,
        "accuracy_scores": None}
    start = time.perf_counter()
    phase = "memory_guard"
    try:
        limit_current_process(args.memory_limit)
        (root / "tmp").mkdir(exist_ok=True)
        os.environ.update(HF_HOME=str(root / "hf"), PADDLE_PDX_CACHE_HOME=str(root / "paddlex"),
            PADDLE_HOME=str(root / "paddle"), XDG_CACHE_HOME=str(root / "cache"),
            TEMP=str(root / "tmp"), TMP=str(root / "tmp"), CUDA_VISIBLE_DEVICES="",
            OMP_NUM_THREADS="2", MKL_NUM_THREADS="2", HF_HUB_OFFLINE="1")
        phase = "asset_verification"
        for asset in json.loads((root / "PADDLE_ASSETS.json").read_text(encoding="utf-8")):
            from pathlib import Path
            if hashlib.sha256(Path(asset["path"]).read_bytes()).hexdigest() != asset["sha256"]:
                raise ValueError("Model checksum mismatch")
        phase = "imports"
        print("Importing isolated CPU Paddle runtime", flush=True)
        import paddle
        from paddleocr import PaddleOCR

        if paddle.is_compiled_with_cuda():
            raise RuntimeError("Expected CPU Paddle build")
        state["versions"] = {name: importlib.metadata.version(name) for name in
                             ("paddleocr", "paddlepaddle", "paddlex", "numpy")}
        rec = "en_PP-OCRv5_mobile_rec" if args.language == "en" else "arabic_PP-OCRv5_mobile_rec"
        options = dict(text_detection_model_name="PP-OCRv5_mobile_det",
            text_detection_model_dir=str(root / "models/PP-OCRv5_mobile_det"),
            text_recognition_model_name=rec, text_recognition_model_dir=str(root / "models" / rec),
            use_doc_orientation_classify=False, use_doc_unwarping=False, use_textline_orientation=False,
            text_recognition_batch_size=1, device="cpu", cpu_threads=2, enable_mkldnn=False,
            text_det_limit_side_len=960, text_det_limit_type="max", text_rec_score_thresh=0.0)
        write_json(output / "configuration.json", options)
        phase = "initialization"
        before = time.perf_counter()
        model = PaddleOCR(**options)
        state["initialization_seconds"] = time.perf_counter() - before
        record = json.loads(args.record.read_text(encoding="utf-8"))
        source = SUITE / record["source_path"]
        target = root / "inputs" / (record["file_hash"] + source.suffix)
        target.parent.mkdir(exist_ok=True)
        if not target.exists():
            with source.open("rb") as incoming, target.open("xb") as outgoing:
                shutil.copyfileobj(incoming, outgoing)
        if hashlib.sha256(target.read_bytes()).hexdigest() != record["file_hash"]:
            raise ValueError("Frozen input checksum mismatch")
        state.update(document_id=record["document_id"], processing_input_path=str(target))
        phase = "inference"
        before = time.perf_counter()
        results = list(model.predict(str(target)))
        state["inference_seconds"] = time.perf_counter() - before
        if len(results) != 1:
            raise ValueError("Expected one image result")
        native = output / "native"
        native.mkdir()
        results[0].save_to_json(str(native))
        payload = results[0].json
        write_json(output / "prediction.json", payload)
        data = payload.get("res", payload)
        texts = data["rec_texts"]
        (output / "prediction.txt").write_text("\n".join(texts), encoding="utf-8")
        state.update(status="SUCCESS", documents_processed=1, recognized_lines=len(texts),
            text_characters=sum(map(len, texts)), recognizer=rec)
        model.close()
    except Exception as exc:
        state.update(status="FAILED", phase=phase, error_type=type(exc).__name__, error=str(exc),
                     traceback=traceback.format_exc())
        traceback.print_exc()
    finally:
        state["wall_seconds"] = time.perf_counter() - start
        write_json(output / "result.json", state)
        print(json.dumps({k: state[k] for k in ("status", "language", "documents_processed")}), flush=True)
    return 0 if state["status"] == "SUCCESS" else 1
