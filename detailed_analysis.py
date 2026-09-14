from pathlib import Path
from difflib import SequenceMatcher
import re

def normalize_text(text):
    text = text.replace("\u00AD", "")
    text = text.replace("–", "-")
    text = text.replace("—", "-")
    text = text.replace("−", "-")
    text = re.sub(r'(\w)-\s*\n\s*(\w)', r'\1\2', text)
    text = text.replace("\n", " ")
    text = text.lower()
    text = re.sub(r'https?://\S+', ' ', text)
    text = re.sub(r'[#*_>`~]', ' ', text)
    text = re.sub(r'\[\d+\]', ' ', text)
    text = re.sub(r'\S+@\S+', ' ', text)
    text = re.sub(r'\b(19|20)\d{2}\b', ' ', text)
    text = re.sub(r'\b\d{1,3}\b(?=\s)', ' ', text)
    text = re.sub(r'\b([a-z])\s+(?:\1\s+)+', r'\1 ', text)
    text = re.sub(r'\b(tm|reg|copy|pm|am)\b', ' ', text)
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

ref_path = Path("Datasets/English/Markdown_Reference/crowd_1.md")
ocr_path = Path("Outputs/English/paddleocr/crowd_1.md")

with open(ref_path, encoding="utf-8") as f:
    ref = f.read()
with open(ocr_path, encoding="utf-8") as f:
    ocr = f.read()

ref_norm = normalize_text(ref)
ocr_norm = normalize_text(ocr)

# Split into words for analysis
ref_words = ref_norm.split()
ocr_words = ocr_norm.split()

print("=" * 80)
print("CROWD_1.MD DETAILED ANALYSIS")
print("=" * 80)

print(f"\nCharacter count:")
print(f"  Reference: {len(ref_norm):,} chars / {len(ref_words):,} words")
print(f"  OCR:       {len(ocr_norm):,} chars / {len(ocr_words):,} words")
print(f"  Difference: {len(ocr_norm) - len(ref_norm):+,} chars / {len(ocr_words) - len(ref_words):+,} words")

# Find longest matching blocks
print(f"\nFinding content overlap...")
matcher = SequenceMatcher(None, ref_norm, ocr_norm)
matches = matcher.get_matching_blocks()
total_matching = sum(m.size for m in matches)
print(f"  Total matching characters: {total_matching:,} / {len(ref_norm):,} ({total_matching/len(ref_norm)*100:.1f}%)")

# Show unique words
ref_set = set(ref_words)
ocr_set = set(ocr_words)
only_in_ref = ref_set - ocr_set
only_in_ocr = ocr_set - ref_set

print(f"\nUnique content analysis:")
print(f"  Words only in reference: {len(only_in_ref)}")
print(f"  Words only in OCR: {len(only_in_ocr)}")

if only_in_ocr:
    # Count how many times unique OCR words appear
    ocr_word_counts = {}
    for word in only_in_ocr:
        ocr_word_counts[word] = ocr_words.count(word)
    
    print(f"\n  Top words unique to OCR (by frequency):")
    for word, count in sorted(ocr_word_counts.items(), key=lambda x: -x[1])[:15]:
        print(f"    '{word}': {count} times")
