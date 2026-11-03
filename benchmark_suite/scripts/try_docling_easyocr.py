"""Run the explicitly authorized Docling + EasyOCR CPU feasibility trial."""

from docling_trial import main


if __name__ == "__main__":
    raise SystemExit(main(default_model="docling_easyocr"))
