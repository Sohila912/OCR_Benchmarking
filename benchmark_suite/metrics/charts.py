"""Independent chart tasks, with caller-supplied, explicitly keyed truth."""

import math

from . import availability, prf
from .text import evaluate as text_evaluate
from .layout import detection as layout_detection


def detection(reference, prediction, classes=("chart", "figure"), threshold=0.5):
    return availability(False) if reference is None else layout_detection(reference, prediction, classes, threshold)


def classification(reference, prediction):
    """Reference and prediction keyed by independently matched chart ID."""
    if reference is None:
        return availability(False)
    return {"status": "SCORED", "count": len(reference),
            "accuracy": sum(prediction.get(k) == v for k, v in reference.items())/len(reference) if reference else None,
            "prediction_coverage": sum(k in prediction for k in reference)/len(reference) if reference else None,
            "extra_predictions": len(prediction.keys() - reference.keys())}


def numeric(reference, prediction, absolute_tolerance=0.0, relative_tolerance=0.01):
    """Keys encode chart/series/category/unit. Unmatched values count as errors."""
    if reference is None:
        return availability(False)
    if not all(math.isfinite(t) and t >= 0 for t in (absolute_tolerance, relative_tolerance)):
        raise ValueError("Tolerances must be finite and nonnegative")
    if not all(math.isfinite(v) for v in [*reference.values(), *prediction.values()]):
        raise ValueError("Numeric chart values must be finite")
    common = reference.keys() & prediction.keys()
    correct = sum(abs(reference[k]-prediction[k]) <= max(absolute_tolerance, relative_tolerance*abs(reference[k])) for k in common)
    return {"status": "SCORED", "values": prf(correct, len(prediction)-correct, len(reference)-correct),
            "accuracy": correct/len(reference) if reference else None,
            "matched_mae": sum(abs(reference[k]-prediction[k]) for k in common)/len(common) if common else None,
            "matched_coverage": len(common)/len(reference) if reference else None,
            "absolute_tolerance": absolute_tolerance, "relative_tolerance": relative_tolerance}


def chart_text(reference, prediction):
    return availability(False) if reference is None else text_evaluate(reference, prediction)


def completeness(reference, prediction):
    """Exact annotated component IDs; no inferred titles/axes/legends."""
    if reference is None:
        return availability(False)
    r, p = set(reference), set(prediction)
    return dict(status="SCORED", **prf(len(r & p), len(p-r), len(r-p)))
