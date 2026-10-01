import os
import shutil
import tempfile

import torch
from pdf2image import convert_from_path
from transformers import AutoTokenizer, AutoModel


class DeepSeekRunner:

    def __init__(self):

        self.model_name = "deepseek-ai/DeepSeek-OCR"

        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_name,
            trust_remote_code=True
        )

        self.model = AutoModel.from_pretrained(
            self.model_name,
            trust_remote_code=True,
            use_safetensors=True,
        )

        self.model = (
            self.model
            .eval()
            .cuda()
            .to(torch.bfloat16)
        )

    def run(self, pdf_path):

        pages = convert_from_path(pdf_path, dpi=300)

        markdown = ""

        with tempfile.TemporaryDirectory() as tmpdir:

            for i, page in enumerate(pages):

                image_path = os.path.join(
                    tmpdir,
                    f"page_{i}.png"
                )

                page.save(image_path)

                output_dir = os.path.join(
                    tmpdir,
                    f"output_{i}"
                )

                os.makedirs(output_dir, exist_ok=True)

                self.model.infer(
                    self.tokenizer,
                    prompt="<image>\n<|grounding|>Convert the document to markdown.",
                    image_file=image_path,
                    output_path=output_dir,
                    base_size=1024,
                    image_size=640,
                    crop_mode=True,
                    save_results=True,
                    test_compress=True,
                )

                md_file = os.path.join(
                    output_dir,
                    "result.md"
                )

                txt_file = os.path.join(
                    output_dir,
                    "result.txt"
                )

                if os.path.exists(md_file):

                    with open(md_file, encoding="utf-8") as f:
                        markdown += f.read() + "\n"

                elif os.path.exists(txt_file):

                    with open(txt_file, encoding="utf-8") as f:
                        markdown += f.read() + "\n"

        return markdown