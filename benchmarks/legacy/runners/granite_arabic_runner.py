from docling.document_converter import (
    DocumentConverter,
    PdfFormatOption,
)
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    EasyOcrOptions,
)


class GraniteRunner:

    def __init__(self):

        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = True

        pipeline_options.ocr_options = EasyOcrOptions(
            lang=["ar"]
        )

        self.converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=pipeline_options
                )
            }
        )

    def run(self, pdf_path):
        result = self.converter.convert(str(pdf_path))

        markdown = result.document.export_to_markdown()

        return markdown