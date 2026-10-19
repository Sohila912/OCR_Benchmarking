from pathlib import Path
import pandas as pd
from jiwer import wer, cer
import re

# ======================================================
# PATHS
# ======================================================

GROUND_TRUTH = Path(__file__).resolve().parents[1] / "datasets/Arabic/Markdown_Reference"
OCR_OUTPUT = Path(__file__).resolve().parents[1] / "outputs/Arabic/tesseractocr"

# ======================================================


def normalize_text(text):
    """
    Normalize Arabic OCR/reference text before evaluation.
    """

    # --------------------------------------------------
    # Remove soft hyphen
    # --------------------------------------------------

    text = text.replace("\u00AD", "")

    # --------------------------------------------------
    # Normalize dashes
    # --------------------------------------------------

    text = (
        text.replace("–", "-")
            .replace("—", "-")
            .replace("−", "-")
    )

    # --------------------------------------------------
    # Join hyphenated words across lines
    # --------------------------------------------------

    text = re.sub(r'(\S)-\s*\n\s*(\S)', r'\1\2', text)

    # --------------------------------------------------
    # Replace newlines with spaces
    # --------------------------------------------------

    text = text.replace("\n", " ")

    # --------------------------------------------------
    # Remove URLs
    # --------------------------------------------------

    text = re.sub(r'https?://\S+', ' ', text)

    # --------------------------------------------------
    # Remove markdown formatting
    # --------------------------------------------------

    text = re.sub(r'[#*_>`~]', ' ', text)

    # --------------------------------------------------
    # Remove citations
    # --------------------------------------------------

    text = re.sub(r'\[\d+\]', ' ', text)

    # --------------------------------------------------
    # Remove email addresses
    # --------------------------------------------------

    text = re.sub(r'\S+@\S+', ' ', text)

    # --------------------------------------------------
    # Arabic normalization
    # --------------------------------------------------

    # Normalize Alef
    text = re.sub(r'[إأآٱا]', 'ا', text)

    # Normalize Yeh
    text = re.sub(r'[ىي]', 'ي', text)

    # Normalize Teh Marbuta
    text = text.replace("ة", "ه")

    # Normalize Hamza-on-Waw / Hamza-on-Yeh
    text = text.replace("ؤ", "و")
    text = text.replace("ئ", "ي")

    # Remove Tatweel
    text = text.replace("ـ", "")

    # Remove Arabic diacritics
    arabic_diacritics = re.compile("""
                             ّ    | # Shadda
                             َ    | # Fatha
                             ً    | # Tanwin Fath
                             ُ    | # Damma
                             ٌ    | # Tanwin Damm
                             ِ    | # Kasra
                             ٍ    | # Tanwin Kasr
                             ْ    | # Sukun
                             ٰ      # Superscript Alef
                         """, re.VERBOSE)

    text = re.sub(arabic_diacritics, "", text)

    # --------------------------------------------------
    # Remove years
    # --------------------------------------------------

    text = re.sub(r'\b(19|20)\d{2}\b', ' ', text)

    # --------------------------------------------------
    # Remove standalone page numbers
    # --------------------------------------------------

    text = re.sub(r'\b\d{1,3}\b(?=\s)', ' ', text)

    # --------------------------------------------------
    # Remove punctuation
    # Keep Arabic letters, English letters, numbers and spaces
    # --------------------------------------------------

    text = re.sub(r'[^\u0600-\u06FFa-zA-Z0-9\s]', ' ', text)

    # --------------------------------------------------
    # Collapse spaces
    # --------------------------------------------------

    text = re.sub(r'\s+', ' ', text)

    return text.strip()


def main():
    from benchmarks.evaluation.options import evaluation_options
    args = evaluation_options(GROUND_TRUTH, OCR_OUTPUT)
    ground_truth, ocr_output = args.reference, args.ocr_output
    from benchmarks.evaluation.metrics import evaluate_directory
    results, missing = evaluate_directory(ground_truth, ocr_output, "Arabic")
    for filename in missing:
        print(f"Missing: {filename}")
    df = pd.DataFrame(results)

    df.to_excel(args.result, index=False)

    print(df)

    print("\n" + "=" * 50)
    print("OVERALL RESULTS")
    print("=" * 50)

    print(f"Average CER                : {df['CER'].mean():.4f}")
    print(f"Average WER                : {df['WER'].mean():.4f}")
    print(f"Average Character Accuracy : {df['Character Accuracy (%)'].mean():.2f}%")
    print(f"Average Word Accuracy      : {df['Word Accuracy (%)'].mean():.2f}%")

if __name__ == "__main__":
    main()
