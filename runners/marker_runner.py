try:
    from marker.converters.pdf import PdfConverter
    from marker.models import create_model_dict
except Exception:  # pragma: no cover - optional dependency guard
    PdfConverter = None
    create_model_dict = None


class MarkerRunner:

    def __init__(self):
        self.converter = None
        if PdfConverter is not None and create_model_dict is not None:
            try:
                self.converter = PdfConverter(artifact_dict=create_model_dict())
            except Exception:
                self.converter = None

    def extract(self, pdf_path):
        try:
            if self.converter is None:
                return "Marker engine unavailable because the required 'marker' package is not installed in this environment."

            result = self.converter(str(pdf_path))

            if result is None or not hasattr(result, "markdown"):
                return ""

            markdown = result.markdown
            if markdown is None or not isinstance(markdown, str):
                return ""

            return markdown

        except Exception as e:
            print(f"Error processing {pdf_path}: {e}")
            return ""

    def run(self, pdf_path):
        return self.extract(pdf_path)