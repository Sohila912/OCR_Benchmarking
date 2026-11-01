"""Code-point edit distance; whitespace-token WER; optional explicit Arabic folds."""

from collections import Counter
from dataclasses import asdict, dataclass
import re
import unicodedata

from rapidfuzz.distance import Levenshtein

from . import prf


@dataclass(frozen=True)
class Normalization:
    unicode: str = "NFC"
    whitespace: bool = True
    diacritics: bool = False
    alef: bool = False
    hamza: bool = False
    tatweel: bool = False

    def __post_init__(self):
        if self.unicode not in {"none", "NFC", "NFKC"}:
            raise ValueError("unicode must be none, NFC or NFKC")


def normalize(text: str, options: Normalization) -> str:
    if options.unicode != "none":
        text = unicodedata.normalize(options.unicode, text)
    if options.diacritics:
        # Explicit Arabic vocalization/Quranic mark ranges, never all Unicode marks.
        text = re.sub("[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06dc\u06df-\u06e4\u06e7-\u06e8\u06ea-\u06ed]", "", text)
    if options.alef:
        text = text.translate(str.maketrans("آأإٱ", "اااا"))
    if options.hamza:
        # Fold seated hamza to its carrier; retain standalone hamza ء.
        text = text.translate(str.maketrans("ؤئأإ", "وياا"))
    if options.tatweel:
        text = text.replace("ـ", "")
    if options.whitespace:
        text = " ".join(text.split())
    return text


def score(reference: str, prediction: str) -> dict:
    def units(a, b):
        edits = Levenshtein.distance(a, b)
        rate = edits / len(a) if a else None
        common = sum((Counter(a) & Counter(b)).values())
        return {"edits": edits, "reference_length": len(a), "prediction_length": len(b),
                "error_rate": rate, "accuracy": max(0.0, 1 - rate) if rate is not None else None,
                "normalized_edit_distance": edits / max(len(a), len(b), 1),
                "bag_matching": prf(common, len(b) - common, len(a) - common)}
    chars, words = units(reference, prediction), units(reference.split(), prediction.split())
    return {"status": "SCORED", "cer": chars["error_rate"], "wer": words["error_rate"],
            "character_accuracy": chars["accuracy"], "word_accuracy": words["accuracy"],
            "ned": chars["normalized_edit_distance"], "exact_match": reference == prediction,
            "characters": chars, "words": words}


def evaluate(reference: str, prediction: str, options: Normalization = Normalization()) -> dict:
    return {"raw": score(reference, prediction),
            "normalized": score(normalize(reference, options), normalize(prediction, options)),
            "normalization": asdict(options)}
