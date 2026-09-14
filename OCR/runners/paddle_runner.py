# import os
# import tempfile

# try:
#     from pdf2image import convert_from_path
# except Exception:  # pragma: no cover - optional dependency guard
#     convert_from_path = None

# try:
#     from paddleocr import PaddleOCR
# except Exception:  # pragma: no cover - optional dependency guard
#     PaddleOCR = None


# class PaddleRunner:

#     def __init__(self):
#         self.ocr = None
#         if PaddleOCR is not None:
#             try:
#                 self.ocr = PaddleOCR(
#                     use_angle_cls=True,
#                     lang="ar"  # For Arabic, use "ar" and for English, use "en"
#                 )
#             except Exception:
#                 self.ocr = None

#     def _preprocess_image(self, image):
#         grayscale = image.convert("L")
#         width, height = grayscale.size
#         return grayscale.resize((max(width * 2, 1), max(height * 2, 1)))

#     def extract(self, pdf_path):
#         if convert_from_path is None or self.ocr is None:
#             return "Paddle engine unavailable because the required OCR dependencies are not installed in this environment."

#         if not os.path.exists(pdf_path):
#             return ""

#         try:
#             pages = convert_from_path(pdf_path, dpi=300)
#         except Exception:
#             return ""

#         markdown_parts = []
#         for page in pages:
#             with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp:
#                 processed = self._preprocess_image(page)
#                 processed.save(temp.name, "PNG")
#                 try:
#                     result = self.ocr.ocr(temp.name)
#                     if result and isinstance(result, list) and len(result) > 0 and result[0] is not None:
#                         for line in result[0]:
#                             if isinstance(line, list) and len(line) >= 2 and isinstance(line[1], tuple) and len(line[1]) >= 1:
#                                 markdown_parts.append(str(line[1][0]))
#                 finally:
#                     if os.path.exists(temp.name):
#                         os.remove(temp.name)

#         markdown = "\n".join(part for part in markdown_parts if part)
#         if not markdown:
#             return "Paddle OCR produced no extractable text for this PDF."
#         return markdown

#     def run(self, pdf_path):
#         return self.extract(pdf_path)
import os
import tempfile

# -------------------------------------------------------------------
# Poppler configuration for Windows
# -------------------------------------------------------------------
POPPLER_PATH = r"C:\poppler-26.02.0\Library\bin"


# -------------------------------------------------------------------
# pdf2image
# -------------------------------------------------------------------
try:
    from pdf2image import convert_from_path
except Exception as e:  # pragma: no cover - optional dependency guard
    convert_from_path = None
    PDF2IMAGE_ERROR = str(e)
else:
    PDF2IMAGE_ERROR = None


# -------------------------------------------------------------------
# PaddleOCR
# -------------------------------------------------------------------
try:
    from paddleocr import PaddleOCR
except Exception as e:  # pragma: no cover - optional dependency guard
    PaddleOCR = None
    PADDLEOCR_IMPORT_ERROR = str(e)
else:
    PADDLEOCR_IMPORT_ERROR = None


class PaddleRunner:

    def __init__(self):
        self.ocr = None
        self.initialization_error = None

        # Check pdf2image
        if convert_from_path is None:
            self.initialization_error = (
                f"pdf2image is unavailable: {PDF2IMAGE_ERROR}"
            )
            return

        # Check PaddleOCR
        if PaddleOCR is None:
            self.initialization_error = (
                f"PaddleOCR is unavailable: {PADDLEOCR_IMPORT_ERROR}"
            )
            return

        # Initialize PaddleOCR
        try:
            self.ocr = PaddleOCR(
                use_angle_cls=True,
                lang="en"  # Use "ar" for Arabic, "en" for English
            )
        except Exception as e:
            self.initialization_error = (
                f"PaddleOCR initialization failed: {type(e).__name__}: {e}"
            )
            self.ocr = None

    def _preprocess_image(self, image):
        """
        Convert image to grayscale and scale it up 2x.
        """
        grayscale = image.convert("L")
        width, height = grayscale.size

        return grayscale.resize(
            (
                max(width * 2, 1),
                max(height * 2, 1)
            )
        )

    def extract(self, pdf_path):
        """
        Convert PDF pages to images, run PaddleOCR,
        and return extracted text.
        """

        # Check dependencies / initialization
        if convert_from_path is None:
            return (
                "Paddle engine unavailable because pdf2image is not installed. "
                f"Details: {PDF2IMAGE_ERROR}"
            )

        if self.ocr is None:
            return (
                "Paddle engine unavailable because PaddleOCR could not be "
                f"initialized. Details: {self.initialization_error}"
            )

        # Check PDF exists
        if not os.path.exists(pdf_path):
            return f"PDF file does not exist: {pdf_path}"

        # ----------------------------------------------------------------
        # Convert PDF to images using Poppler
        # ----------------------------------------------------------------
        try:
            pages = convert_from_path(
                pdf_path,
                dpi=300,
                poppler_path=POPPLER_PATH
            )
        except Exception as e:
            return (
                "Failed to convert PDF to images using Poppler. "
                f"Error: {type(e).__name__}: {e}\n"
                f"Poppler path used: {POPPLER_PATH}"
            )

        markdown_parts = []

        # ----------------------------------------------------------------
        # Process each page
        # ----------------------------------------------------------------
        for page_number, page in enumerate(pages, start=1):

            temp_path = None

            try:
                # Preprocess
                processed = self._preprocess_image(page)

                # Create temporary PNG
                with tempfile.NamedTemporaryFile(
                    suffix=".png",
                    delete=False
                ) as temp:

                    temp_path = temp.name
                    processed.save(temp_path, "PNG")

                # --------------------------------------------------------
                # Run PaddleOCR
                # --------------------------------------------------------
                result = self.ocr.ocr(temp_path)

                if (
                    result
                    and isinstance(result, list)
                    and len(result) > 0
                    and result[0] is not None
                ):
                    for line in result[0]:

                        if (
                            isinstance(line, list)
                            and len(line) >= 2
                            and isinstance(line[1], tuple)
                            and len(line[1]) >= 1
                        ):
                            text = line[1][0]

                            if text:
                                markdown_parts.append(str(text))

            except Exception as e:
                # Keep processing the remaining pages
                markdown_parts.append(
                    f"[Page {page_number} OCR error: "
                    f"{type(e).__name__}: {e}]"
                )

            finally:
                # --------------------------------------------------------
                # Delete temporary PNG
                # --------------------------------------------------------
                if temp_path and os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except Exception:
                        pass

        # ----------------------------------------------------------------
        # Build final markdown
        # ----------------------------------------------------------------
        markdown = "\n".join(
            part for part in markdown_parts if part
        )

        if not markdown:
            return "Paddle OCR produced no extractable text for this PDF."

        return markdown

    def run(self, pdf_path):
        """
        Public entry point.
        """
        return self.extract(pdf_path)