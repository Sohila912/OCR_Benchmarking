# try:
#     from marker.converters.pdf import PdfConverter
#     from marker.models import create_model_dict
# except Exception:  # pragma: no cover - optional dependency guard
#     PdfConverter = None
#     create_model_dict = None


# class MarkerRunner:

#     def __init__(self):
#         self.converter = None
#         if PdfConverter is not None and create_model_dict is not None:
#             try:
#                 self.converter = PdfConverter(artifact_dict=create_model_dict())
#             except Exception:
#                 self.converter = None

#     def extract(self, pdf_path):
#         try:
#             if self.converter is None:
#                 return "Marker engine unavailable because the required 'marker' package is not installed in this environment."

#             result = self.converter(str(pdf_path))

#             if result is None or not hasattr(result, "markdown"):
#                 return ""

#             markdown = result.markdown
#             if markdown is None or not isinstance(markdown, str):
#                 return ""

#             return markdown

#         except Exception as e:
#             print(f"Error processing {pdf_path}: {e}")
#             return ""

#     def run(self, pdf_path):
#         return self.extract(pdf_path)

import os
import traceback
print("===== USING THIS MARKER_RUNNER.PY =====")

# Force Surya to use the local PyTorch backend instead of vLLM/Docker
os.environ["SURYA_INFERENCE_BACKEND"] = "torch"

try:
    from marker.converters.pdf import PdfConverter
    from marker.models import create_model_dict
except Exception:
    traceback.print_exc()
    PdfConverter = None
    create_model_dict = None


class MarkerRunner:
    def __init__(self):
        self.converter = None

        if PdfConverter is None or create_model_dict is None:
            print("Failed to import Marker.")
            return

        try:
            print("Initializing Marker...")

            self.converter = PdfConverter(
                artifact_dict=create_model_dict()
            )

            print("✓ Marker initialized successfully.")

        except Exception:
            print("Failed to initialize Marker:")
            traceback.print_exc()
            self.converter = None

    def extract(self, pdf_path):
        try:
            if self.converter is None:
                raise RuntimeError(
                    "Marker converter was not initialized. Check the initialization logs above."
                )

            result = self.converter(str(pdf_path))

            if result is None:
                return ""

            markdown = getattr(result, "markdown", "")

            if markdown is None:
                return ""

            return markdown

        except Exception:
            print(f"\nError processing {pdf_path}")
            traceback.print_exc()
            return ""

    def run(self, pdf_path):
        return self.extract(pdf_path)