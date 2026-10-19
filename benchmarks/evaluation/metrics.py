"""Canonical historical scoring shared by CLI evaluators and the frontend."""
from importlib import import_module
from pathlib import Path

from jiwer import cer, wer

LANGUAGES = {"English": "english", "Arabic": "arabic", "Mix": "mix"}


def score_document(filename: str, reference: str, prediction: str, language: str) -> dict:
    normalize = import_module(
        f"benchmarks.evaluation.evaluate_{LANGUAGES[language]}"
    ).normalize_text
    reference_clean, prediction_clean = normalize(reference), normalize(prediction)
    cer_score, wer_score = cer(reference_clean, prediction_clean), wer(reference_clean, prediction_clean)
    return {
        "File": filename,
        "CER": round(cer_score, 4),
        "WER": round(wer_score, 4),
        "Character Accuracy (%)": round((1 - cer_score) * 100, 2),
        "Word Accuracy (%)": round((1 - wer_score) * 100, 2),
        "Reference Characters": len(reference_clean),
        "OCR Characters": len(prediction_clean),
        "Reference Words": len(reference_clean.split()),
        "OCR Words": len(prediction_clean.split()),
        "Char Difference": len(prediction_clean) - len(reference_clean),
        "Word Difference": len(prediction_clean.split()) - len(reference_clean.split()),
    }


def evaluate_directory(reference: Path, prediction: Path, language: str) -> tuple[list[dict], list[str]]:
    rows, missing = [], []
    for source in sorted(reference.glob("*.md")):
        target = prediction / source.name
        if not target.is_file():
            missing.append(source.name)
            continue
        rows.append(score_document(source.name, source.read_text(encoding="utf-8"),
                                   target.read_text(encoding="utf-8"), language))
    if not rows:
        raise ValueError("No matching reference/output files; no spreadsheet written.")
    return rows, missing
