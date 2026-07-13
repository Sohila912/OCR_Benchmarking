from pathlib import Path
import pandas as pd
from jiwer import wer, cer
import re

# ======================================================
# PATHS
# ======================================================

GROUND_TRUTH = Path("Datasets/Mix/Markdown_Reference")
OCR_OUTPUT = Path("Outputs/Mix/paddleocr")

# ======================================================


def normalize_text(text):
    """
    Normalize mixed Arabic-English text for OCR evaluation.
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
    # Join hyphenated words split across lines
    # --------------------------------------------------

    text = re.sub(r'(\S)-\s*\n\s*(\S)', r'\1\2', text)
    # Remove Unicode directionality / bidi control marks
    text = re.sub('[\u200e\u200f\u202a-\u202e\u2066-\u2069]', '', text)

    # --------------------------------------------------
    # Replace newlines with spaces
    # --------------------------------------------------

    text = text.replace("\n", " ")

    # --------------------------------------------------
    # Remove URLs
    # --------------------------------------------------

    text = re.sub(r'https?://\S+', ' ', text)

    # --------------------------------------------------
    # Remove email addresses
    # --------------------------------------------------

    text = re.sub(r'\S+@\S+', ' ', text)

    # --------------------------------------------------
    # Remove markdown formatting
    # --------------------------------------------------

    text = re.sub(r'[#*_>`~]', ' ', text)

    # --------------------------------------------------
    # Remove markdown links but keep visible text
    # --------------------------------------------------

    text = re.sub(r'\[(.*?)\]\((.*?)\)', r'\1', text)

    # --------------------------------------------------
    # Remove citations
    # --------------------------------------------------

    text = re.sub(r'\[\d+\]', ' ', text)

    # --------------------------------------------------
    # Arabic normalization
    # --------------------------------------------------

    # Normalize Alef only
    text = re.sub(r'[إأآٱ]', 'ا', text)

    # Normalize Alef Maqsura
    text = text.replace("ى", "ي")

    # Remove Tatweel
    text = text.replace("ـ", "")

    # Remove Arabic diacritics
    arabic_diacritics = re.compile("""
        ّ|َ|ً|ُ|ٌ|ِ|ٍ|ْ|ٰ
    """, re.VERBOSE)

    text = re.sub(arabic_diacritics, "", text)

    # --------------------------------------------------
    # Remove punctuation
    # Keep Arabic, English and numbers
    # --------------------------------------------------

    text = re.sub(r"[^\u0600-\u06FFA-Za-z0-9\s]", " ", text)

    # --------------------------------------------------
    # Collapse spaces
    # --------------------------------------------------

    text = re.sub(r"\s+", " ", text)

    return text.strip()


# ======================================================
# Evaluation
# ======================================================

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

    reference_clean = normalize_text(reference)
    prediction_clean = normalize_text(prediction)

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

output_path = "Evaluation Results/Mix/Paddle_OCR_Mix_Evaluation.xlsx"
df.to_excel(output_path, index=False)

print(df)

print("\n" + "=" * 60)
print("OVERALL RESULTS")
print("=" * 60)

print(f"Files Evaluated           : {len(df)}")
print(f"Average CER              : {df['CER'].mean():.4f}")
print(f"Average WER              : {df['WER'].mean():.4f}")
print(f"Average Character Accuracy: {df['Character Accuracy (%)'].mean():.2f}%")
print(f"Average Word Accuracy     : {df['Word Accuracy (%)'].mean():.2f}%")