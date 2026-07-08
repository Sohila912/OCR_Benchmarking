from docling.document_converter import DocumentConverter

class GraniteRunner:

    def __init__(self):
        self.converter = DocumentConverter()

    def run(self, pdf_path):
        result = self.converter.convert(str(pdf_path))

        print(result)
        print(result.document)

        markdown = result.document.export_to_markdown()

        print(len(markdown))

        return markdown