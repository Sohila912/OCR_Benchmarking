"""Explicit, repeatable download of the local assets used by the OCR adapters."""
import os
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ["HF_HOME"] = str(ROOT / "models" / ".cache")
os.environ["HF_HUB_OFFLINE"] = "0"
os.environ["TRANSFORMERS_OFFLINE"] = "0"


def main():
    from huggingface_hub import snapshot_download
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", choices=["paddle_vl", "docling"])
    args = parser.parse_args()
    for name in (() if args.provider == "docling" else ("PaddleOCR-VL-1.6", "PP-DocLayoutV3")):
        print(f"Downloading {name}", flush=True)
        snapshot_download(f"PaddlePaddle/{name}", local_dir=ROOT / "models" / name)
    if args.provider == "paddle_vl":
        return
    from docling.utils.model_downloader import download_models
    print("Downloading Docling layout and table models", flush=True)
    download_models(output_dir=ROOT / "models" / "docling", with_layout=True,
                    with_tableformer=True, with_code_formula=False,
                    with_picture_classifier=False, with_smolvlm=False,
                    with_granite_vision=False, with_easyocr=False, with_rapidocr=False,
                    progress=True)


if __name__ == "__main__":
    main()
