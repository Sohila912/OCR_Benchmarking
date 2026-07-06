from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict


class MarkerRunner:

    def __init__(self):
        self.converter = PdfConverter(
            artifact_dict=create_model_dict()
        )

    def run(self, pdf_path):
        try:
            result = self.converter(str(pdf_path))

            # Check that a result was returned
            if result is None:
                return ""

            # Check that the result contains markdown
            if not hasattr(result, "markdown"):
                return ""

            markdown = result.markdown

            # Check that markdown is a valid string
            if markdown is None:
                return ""

            if not isinstance(markdown, str):
                return ""

            return markdown

        except Exception as e:
            print(f"Error processing {pdf_path}: {e}")
            return ""