from pathlib import Path
import pandas as pd
from jiwer import wer, cer
import re

# ======================================================
# PATHS
# ======================================================

GROUND_TRUTH = Path("Datasets/English/Markdown_Reference")
OCR_OUTPUT = Path("Outputs/English/tesseractocr")

# ======================================================


def normalize_text(text):
    """
    Normalize OCR/reference text before evaluation.
    """

    # --------------------------------------------------
    # Unicode normalization
    # --------------------------------------------------

    # Remove soft hyphen (common in PDFs)
    text = text.replace("\u00AD", "")

    # Normalize different dash types
    text = text.replace("–", "-")
    text = text.replace("—", "-")
    text = text.replace("−", "-")

    # --------------------------------------------------
    # Join hyphenated words split across lines
    # Example:
    # multi-\ncolumn  -> multicolumn
    # dis-\ntract     -> distract
    # --------------------------------------------------

    text = re.sub(r'(\w)-\s*\n\s*(\w)', r'\1\2', text)

    # --------------------------------------------------
    # Replace remaining newlines with spaces
    # --------------------------------------------------

    text = text.replace("\n", " ")

    # --------------------------------------------------
    # Lowercase
    # --------------------------------------------------

    text = text.lower()

    # --------------------------------------------------
    # Remove URLs
    # --------------------------------------------------

    text = re.sub(r'https?://\S+', ' ', text)

    # --------------------------------------------------
    # Remove markdown formatting
    # --------------------------------------------------

    text = re.sub(r'[#*_>`~]', ' ', text)

    # --------------------------------------------------
    # Remove citations [1], [15], [28], etc.
    # --------------------------------------------------

    text = re.sub(r'\[\d+\]', ' ', text)

    # --------------------------------------------------
    # Remove email addresses
    # --------------------------------------------------

    text = re.sub(r'\S+@\S+', ' ', text)

    # --------------------------------------------------
    # Remove year patterns (1900-2099)
    # --------------------------------------------------

    text = re.sub(r'\b(19|20)\d{2}\b', ' ', text)

    # --------------------------------------------------
    # Remove isolated page numbers
    # (e.g. "7", "15")
    # --------------------------------------------------

    text = re.sub(r'\b\d{1,3}\b(?=\s)', ' ', text)

    # --------------------------------------------------
    # Remove repeated single letters/chars (OCR noise)
    # Examples: "l l l" -> "l", "i i i" -> "i"
    # --------------------------------------------------

    text = re.sub(r'\b([a-z])\s+(?:\1\s+)+', r'\1 ', text)

    # --------------------------------------------------
    # Remove common OCR garbage patterns
    # --------------------------------------------------

    # Remove sequences like "tm", "reg" at word boundaries
    text = re.sub(r'\b(tm|reg|copy|pm|am)\b', ' ', text)

    # --------------------------------------------------
    # Remove unreliable short tokens (OCR artifacts)
    # - Single letters after normalization (except 'a', 'i')
    # - Numbers less than 4 digits after normalization
    # - Fragments like "tion", "ce", "co", "io", "l2", etc.
    # --------------------------------------------------

    # Remove standalone single letters (except 'a' and 'i')
    text = re.sub(r'\b[b-hj-z]\b', ' ', text)
    
    # Remove standalone 1-3 digit numbers (page numbers, noise)
    text = re.sub(r'\b\d{1,3}\b', ' ', text)

    # --------------------------------------------------
    # Remove punctuation
    # Keep only letters, numbers and spaces
    # --------------------------------------------------

    text = re.sub(r'[^a-z0-9\s]', ' ', text)

    # --------------------------------------------------
    # Collapse multiple spaces
    # --------------------------------------------------

    text = re.sub(r'\s+', ' ', text)

    return text.strip()


results = []

reference_files = sorted(GROUND_TRUTH.glob("*.md"))

for ref_file in reference_files:

    pred_file = OCR_OUTPUT / ref_file.name

    if not pred_file.exists():
        print(f"Missing: {ref_file.name}")
        continue

    with open(ref_file, "r", encoding="utf-8") as f:
        reference = f.read()

    with open(pred_file, "r", encoding="utf-8") as f:
        prediction = f.read()

    # Normalize both texts
    reference_clean = normalize_text(reference)
    prediction_clean = normalize_text(prediction)

    # Metrics
    cer_score = cer(reference_clean, prediction_clean)
    wer_score = wer(reference_clean, prediction_clean)

    results.append({
        "File": ref_file.name,
        "CER": round(cer_score, 4),
        "WER": round(wer_score, 4),
        "Character Accuracy (%)": round((1 - cer_score) * 100, 2),
        "Word Accuracy (%)": round((1 - wer_score) * 100, 2),
        "Reference Characters": len(reference_clean),
        "OCR Characters": len(prediction_clean),
        "Reference Words": len(reference_clean.split()),
        "OCR Words": len(prediction_clean.split()),
        "Char Difference": len(prediction_clean) - len(reference_clean),
        "Word Difference": len(prediction_clean.split()) - len(reference_clean.split())
    })

# ======================================================
# Results
# ======================================================

df = pd.DataFrame(results)

df.to_excel("Evaluation Results/TesseractOCR_Evaluation.xlsx", index=False)

print(df)

print("\n" + "=" * 50)
print("OVERALL RESULTS")
print("=" * 50)

print(f"Average CER                : {df['CER'].mean():.4f}")
print(f"Average WER                : {df['WER'].mean():.4f}")
print(f"Average Character Accuracy : {df['Character Accuracy (%)'].mean():.2f}%")
print(f"Average Word Accuracy      : {df['Word Accuracy (%)'].mean():.2f}%")