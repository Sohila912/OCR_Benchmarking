# import os
# import tempfile

# try:
#     from pdf2image import convert_from_path
# except Exception:  # pragma: no cover - optional dependency guard
#     convert_from_path = None

# try:
#     import pytesseract
# except Exception:  # pragma: no cover - optional dependency guard
#     pytesseract = None


# class TesseractRunner:

#     def __init__(self):
#         # Uncomment and modify this line if Tesseract is not in your PATH
#         # pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"
#         self.pytesseract = pytesseract

#     def extract(self, pdf_path):
#         if convert_from_path is None or self.pytesseract is None or not os.path.exists(pdf_path):
#             return "Tesseract engine unavailable because the required OCR dependencies are not installed in this environment."

#         try:
#             pages = convert_from_path(pdf_path, dpi=300)
#         except Exception:
#             return ""

#         markdown_parts = []

#         for page in pages:
#             with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp:
#                 page.save(temp.name, "PNG")

#                 try:
#                     text = self.pytesseract.image_to_string(
#                         temp.name,
#                         lang="ara+eng"  # For Arabic, use "ara" and for English, use "eng"
#                     )

#                     if text is not None and isinstance(text, str) and text.strip():
#                         markdown_parts.append(text.strip())

#                 except Exception as e:
#                     print(f"Error processing page: {e}")

#                 finally:
#                     if os.path.exists(temp.name):
#                         os.remove(temp.name)

#         markdown = "\n\n".join(markdown_parts)
#         if not markdown:
#             return "Tesseract OCR produced no extractable text for this PDF."
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
# Tesseract configuration for Windows
# -------------------------------------------------------------------
# Change this if your Tesseract installation is somewhere else.
# A common installation path is:
# C:\Program Files\Tesseract-OCR\tesseract.exe
TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

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
# Tesseract / pytesseract
# -------------------------------------------------------------------
try:
    import pytesseract
except Exception as e:  # pragma: no cover - optional dependency guard
    pytesseract = None
    PYTESSERACT_ERROR = str(e)
else:
    PYTESSERACT_ERROR = None


class TesseractRunner:

    def __init__(self):
        self.pytesseract = None
        self.initialization_error = None

        # --------------------------------------------------------------
        # Check pdf2image
        # --------------------------------------------------------------
        if convert_from_path is None:
            self.initialization_error = (
                f"pdf2image is unavailable: {PDF2IMAGE_ERROR}"
            )
            return

        # --------------------------------------------------------------
        # Check pytesseract
        # --------------------------------------------------------------
        if pytesseract is None:
            self.initialization_error = (
                f"pytesseract is unavailable: {PYTESSERACT_ERROR}"
            )
            return

        # --------------------------------------------------------------
        # Configure Tesseract executable
        # --------------------------------------------------------------
        try:
            if not os.path.exists(TESSERACT_PATH):
                self.initialization_error = (
                    "Tesseract executable was not found.\n"
                    f"Expected path: {TESSERACT_PATH}"
                )
                return

            pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

            # Test Tesseract installation
            version = pytesseract.get_tesseract_version()

            print(f"Tesseract initialized successfully: {version}")

            self.pytesseract = pytesseract

        except Exception as e:
            self.initialization_error = (
                f"Tesseract initialization failed: "
                f"{type(e).__name__}: {e}"
            )

            self.pytesseract = None

    def extract(self, pdf_path):
        """
        Convert PDF pages to images using Poppler and run Tesseract OCR.
        """

        # --------------------------------------------------------------
        # Check dependencies / initialization
        # --------------------------------------------------------------
        if convert_from_path is None:
            return (
                "Tesseract engine unavailable because pdf2image is not "
                f"installed. Details: {PDF2IMAGE_ERROR}"
            )

        if self.pytesseract is None:
            return (
                "Tesseract engine unavailable because Tesseract could "
                f"not be initialized. Details: {self.initialization_error}"
            )

        # --------------------------------------------------------------
        # Check PDF exists
        # --------------------------------------------------------------
        if not os.path.exists(pdf_path):
            return f"PDF file does not exist: {pdf_path}"

        # --------------------------------------------------------------
        # Convert PDF to images using Poppler
        # --------------------------------------------------------------
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

        # --------------------------------------------------------------
        # Process each page
        # --------------------------------------------------------------
        for page_number, page in enumerate(pages, start=1):

            temp_path = None

            try:
                # ------------------------------------------------------
                # Save page as temporary PNG
                # ------------------------------------------------------
                with tempfile.NamedTemporaryFile(
                    suffix=".png",
                    delete=False
                ) as temp:

                    temp_path = temp.name
                    page.save(temp_path, "PNG")

                # ------------------------------------------------------
                # Run Tesseract OCR
                # ------------------------------------------------------
                text = self.pytesseract.image_to_string(
                    temp_path,
                    # lang="ara+eng"
                    lang = "eng"
                )

                if text and isinstance(text, str) and text.strip():
                    markdown_parts.append(text.strip())

            except Exception as e:

                # Don't stop the entire PDF if one page fails.
                markdown_parts.append(
                    f"[Page {page_number} OCR error: "
                    f"{type(e).__name__}: {e}]"
                )

            finally:
                # ------------------------------------------------------
                # Delete temporary file
                # ------------------------------------------------------
                if temp_path and os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except Exception:
                        pass

        # --------------------------------------------------------------
        # Build final markdown
        # --------------------------------------------------------------
        markdown = "\n\n".join(
            part for part in markdown_parts if part
        )

        if not markdown:
            return "Tesseract OCR produced no extractable text for this PDF."

        return markdown

    def run(self, pdf_path):
        return self.extract(pdf_path)