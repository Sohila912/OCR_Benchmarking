"""Versioned benchmark metrics, independent of OCR inference and legacy policies."""

VERSION = "benchmark-metrics-v1"


def availability(annotated: bool, supported: bool = True) -> dict | None:
    """Gate before scoring. An empty prediction is a scored miss, not missing truth."""
    if not annotated:
        return {"status": "NOT_EVALUATED", "reason": "REFERENCE_UNAVAILABLE", "value": None}
    if not supported:
        return {"status": "NOT_SUPPORTED", "reason": "MODEL_CAPABILITY_UNAVAILABLE", "value": None}
    return None


def prf(tp: int, fp: int, fn: int) -> dict:
    """Undefined zero denominators stay null; a scored miss has F1 zero."""
    return {"tp": tp, "fp": fp, "fn": fn,
            "precision": tp / (tp + fp) if tp + fp else None,
            "recall": tp / (tp + fn) if tp + fn else None,
            "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None}
