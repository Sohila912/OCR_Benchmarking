try:
    from docling.document_converter import DocumentConverter
except Exception:  # pragma: no cover - optional dependency guard
    DocumentConverter = None


class GraniteRunner:

    def __init__(self):
        self.converter = None
        if DocumentConverter is not None:
            try:
                self.converter = DocumentConverter()
            except Exception:
                self.converter = None

    def extract(self, pdf_path):
        if self.converter is None:
            return "Docling engine unavailable because the required 'docling' package is not installed in this environment."

        try:
            result = self.converter.convert(str(pdf_path))
            if result is None or not hasattr(result, "document"):
                return ""
            return result.document.export_to_markdown()
        except Exception:
            return ""

    def run(self, pdf_path):
        return self.extract(pdf_path)