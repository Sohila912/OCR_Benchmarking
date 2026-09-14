from pathlib import Path
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
    # Remove standalone single letters (except 'a' and 'i')
    text = re.sub(r'\b[b-hj-z]\b', ' ', text)
    # Remove standalone 1-3 digit numbers
    text = re.sub(r'\b\d{1,3}\b', ' ', text)
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

# Check all files
ref_dir = Path("Datasets/English/Markdown_Reference")
ocr_dir = Path("Outputs/English/paddleocr")

print("FILE COMPARISON")
print("=" * 80)

for ref_file in sorted(ref_dir.glob("*.md"))[:5]:
    ocr_file = ocr_dir / ref_file.name
    
    if not ocr_file.exists():
        print(f"⚠ MISSING: {ref_file.name}")
        continue
    
    with open(ref_file, encoding="utf-8") as f:
        ref = f.read()
    with open(ocr_file, encoding="utf-8") as f:
        ocr = f.read()
    
    ref_norm = normalize_text(ref)
    ocr_norm = normalize_text(ocr)
    
    ref_raw = len(ref)
    ocr_raw = len(ocr)
    ref_norm_len = len(ref_norm)
    ocr_norm_len = len(ocr_norm)
    
    diff = abs(ocr_norm_len - ref_norm_len)
    ratio = ocr_norm_len / ref_norm_len if ref_norm_len > 0 else 0
    
    status = "✓" if diff < 100 else "✗ BIG DIFF"
    
    print(f"\n{status} {ref_file.name}")
    print(f"  Raw:        Ref={ref_raw:6d}  OCR={ocr_raw:6d}  (diff={ocr_raw-ref_raw:+6d})")
    print(f"  Normalized: Ref={ref_norm_len:6d}  OCR={ocr_norm_len:6d}  (diff={ocr_norm_len-ref_norm_len:+6d}, ratio={ratio:.2f}x)")
