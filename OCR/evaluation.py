"""Deterministic ground-truth evaluation; legacy CLI policies remain unchanged."""
import difflib
import re
import unicodedata
from typing import Literal
from pydantic import BaseModel, ConfigDict
from jiwer import process_characters, process_words

METHOD = "levenshtein-jiwer4-v1"
MAX_REFERENCE_BYTES = 2 * 1024 * 1024

class Normalization(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: Literal["raw_markdown", "plain_text"] = "plain_text"
    unicode: Literal["none", "NFC", "NFKC"] = "NFC"
    whitespace: bool = True
    line_breaks: bool = True
    casefold: bool = False
    punctuation: bool = False

def reference_upload(data: bytes, filename: str) -> str:
    if not filename.lower().endswith(".md") or len(data) > MAX_REFERENCE_BYTES:
        raise ValueError("Reference must be a .md file no larger than 2 MiB.")
    try:
        text = data.decode("utf-8-sig", errors="strict")
    except UnicodeError as exc:
        raise ValueError("Reference must contain valid UTF-8.") from exc
    if not text.strip() or "\x00" in text:
        raise ValueError("Reference must contain nonempty text without NUL characters.")
    return text

def normalize(text: str, options: Normalization) -> str:
    if options.unicode != "none":
        text = unicodedata.normalize(options.unicode, text)
    if options.mode == "plain_text":
        # Conservative Markdown syntax removal, retaining labels and code contents.
        text = re.sub(r"(?m)^\s{0,3}(?:```|~~~).*?$", "", text)
        text = re.sub(r"!?\[([^\]\[\n]*)\]\([^)(\n]*\)", r"\1", text)
        text = re.sub(r"(?m)^\s{0,3}(?:#{1,6}\s+|>\s?|[-+*]\s+|\d+[.)]\s+)", "", text)
        text = re.sub(r"(\*\*|__|~~|`)(.*?)\1", r"\2", text, flags=re.S)
        text = re.sub(r"(?<!\w)[*_]([^\n]+?)[*_](?!\w)", r"\1", text)
    if options.line_breaks:
        text = text.replace("\r\n", "\n").replace("\r", "\n")
    if options.casefold:
        text = text.casefold()
    if options.punctuation:
        text = "".join(c for c in text if not unicodedata.category(c).startswith("P"))
    if options.whitespace:
        text = " ".join(text.split())
    return text

def evaluate(reference: str, prediction: str, options: Normalization) -> dict:
    ref, pred = normalize(reference, options), normalize(prediction, options)
    if not ref.strip():
        raise ValueError("Reference is empty after normalization; error rates are undefined.")
    chars = process_characters(ref, pred)
    words = process_words(" ".join(ref.split()), " ".join(pred.split()))
    def counts(result, length):
        return {"substitutions": result.substitutions, "deletions": result.deletions,
                "insertions": result.insertions, "reference_length": length,
                "edits": result.substitutions + result.deletions + result.insertions}
    cc, wc = counts(chars, len(ref)), counts(words, len(ref.split()))
    return {"cer": cc["edits"] / cc["reference_length"], "wer": wc["edits"] / wc["reference_length"],
            "characters": cc, "words": wc, "exact_match": ref == pred,
            "character_similarity": 1 - cc["edits"] / max(len(ref), len(pred), 1),
            "normalization": options.model_dump(), "method": METHOD}

def differences(reference: str, prediction: str, options: Normalization) -> dict:
    ref, pred = normalize(reference, options), normalize(prediction, options)
    # Bound interactive diff work independently of full-document exact scoring.
    truncated = max(len(ref), len(pred)) > 12000
    a, b = ref[:12000].splitlines(), pred[:12000].splitlines()
    matcher = difflib.SequenceMatcher(None, a, b, autojunk=True)
    return {"truncated": truncated, "changes": [
        {"operation": tag, "reference": "\n".join(a[i:j]), "output": "\n".join(b[k:l])}
        for tag, i, j, k, l in matcher.get_opcodes() if tag != "equal"]}

def aggregate(rows):
    successful = [r for r in rows if r.get("status") == "success"]
    result = {"documents": len({r["document_id"] for r in successful}), "evaluations": len(successful), "failed_evaluations": sum(r.get("status") == "failed" for r in rows)}
    for key, metric in (("characters", "cer"), ("words", "wer")):
        denominator = sum(r["metrics"][key]["reference_length"] for r in successful)
        numerator = sum(r["metrics"][key]["edits"] for r in successful)
        result["micro_" + metric] = numerator / denominator if denominator else None
    return result
