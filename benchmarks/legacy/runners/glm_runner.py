# import torch
# from pdf2image import convert_from_path
# from transformers import AutoProcessor, AutoModelForImageTextToText


# class GLMOCRRunner:

#     def __init__(self):

#         self.model_name = "zai-org/GLM-OCR"

#         self.processor = AutoProcessor.from_pretrained(
#             self.model_name,
#             trust_remote_code=True
#         )

#         self.model = AutoModelForImageTextToText.from_pretrained(
#             self.model_name,
#             torch_dtype=torch.bfloat16,
#             device_map="auto",
#             trust_remote_code=True
#         )

#     def run(self, pdf_path):

#         pages = convert_from_path(pdf_path, dpi=300)

#         markdown = ""

#         for page in pages:

#             messages = [
#                 {
#                     "role": "user",
#                     "content": [
#                         {
#                             "type": "image",
#                             "image": page,
#                         },
#                         {
#                             "type": "text",
#                             "text": (
#                                 "Recognize all text in this image. "
#                                 "Output the result as Markdown while preserving layout."
#                             ),
#                         },
#                     ],
#                 }
#             ]

#             prompt = self.processor.apply_chat_template(
#                 messages,
#                 tokenize=False,
#                 add_generation_prompt=True,
#             )

#             inputs = self.processor(
#                 text=[prompt],
#                 images=[page],
#                 return_tensors="pt",
#             ).to(self.model.device)

#             with torch.no_grad():

#                 outputs = self.model.generate(
#                     **inputs,
#                     max_new_tokens=4096,
#                 )

#             result = self.processor.batch_decode(
#                 outputs,
#                 skip_special_tokens=True,
#             )[0]

#             markdown += result + "\n"

#         return markdown
import torch
from pdf2image import convert_from_path
from transformers import AutoProcessor, AutoModelForImageTextToText, BitsAndBytesConfig


class GLMOCRRunner:

    def __init__(self):

        self.model_name = "zai-org/GLM-OCR"

        self.processor = AutoProcessor.from_pretrained(
            self.model_name,
            trust_remote_code=True
        )

        # Configure 4-bit quantization
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True,
        )

        self.model = AutoModelForImageTextToText.from_pretrained(
            self.model_name,
            torch_dtype=torch.bfloat16,
            device_map="auto",
            quantization_config=quantization_config, # Apply quantization
            trust_remote_code=True
        )

    def run(self, pdf_path):

        pages = convert_from_path(pdf_path, dpi=300)

        markdown = ""

        for page in pages:

            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "image": page,
                        },
                        {
                            "type": "text",
                            "text": (
                                "Recognize all text in this image. "
                                "Output the result as Markdown while preserving layout."
                            ),
                        },
                    ],
                }
            ]

            prompt = self.processor.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )

            inputs = self.processor(
                text=[prompt],
                images=[page],
                return_tensors="pt",
            ).to(self.model.device)

            with torch.no_grad():

                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=4096,
                )

            result = self.processor.batch_decode(
                outputs,
                skip_special_tokens=True,
            )[0]

            markdown += result + "\n"

        return markdown