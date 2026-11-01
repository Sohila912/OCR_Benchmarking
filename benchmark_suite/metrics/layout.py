"""Class-aware confidence-greedy detection matching and all-points interpolated AP.

Boxes are axis-aligned [x0,y0,x1,y1] in the same page coordinate system.
Ignored truth suppresses unmatched same-class detections at the IoU threshold.
"""

import math

from . import prf


def box(value):
    if len(value) != 4 or not all(math.isfinite(x) for x in value):
        raise ValueError("Expected four finite coordinates")
    if value[2] <= value[0] or value[3] <= value[1]:
        raise ValueError("Box must have positive area")
    return value


def iou(a, b):
    a, b = box(a), box(b)
    intersection = max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))
    union = (a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - intersection
    return intersection / union


def canonicalize(regions, label_map):
    """Unknown labels raise: a model label map must be reviewed, never guessed."""
    return [dict(r, label=label_map[r["label"]]) for r in regions]


def detection(reference, prediction, classes, threshold=0.5):
    reference, prediction, classes = list(reference), list(prediction), list(classes)
    if not 0 < threshold <= 1 or len(set(classes)) != len(classes):
        raise ValueError("Invalid threshold or duplicate classes")
    for r in [*reference, *prediction]:
        box(r["box"])
    if any(not math.isfinite(p["score"]) or not 0 <= p["score"] <= 1 for p in prediction):
        raise ValueError("Detection scores must be finite in [0,1]")
    results, matches = {}, []
    for label in classes:
        refs = [(i, r) for i, r in enumerate(reference) if r["label"] == label and not r.get("ignore", False)]
        ignored = [r for r in reference if r["label"] == label and r.get("ignore", False)]
        preds = sorted(((i, p) for i, p in enumerate(prediction) if p["label"] == label), key=lambda v: (-v[1]["score"], v[0]))
        used, flags, overlaps = set(), [], []
        for pi, pred in preds:
            candidates = [(iou(r["box"], pred["box"]), -ri, ri) for ri, r in refs if ri not in used and r.get("page_id") == pred.get("page_id")]
            overlap, _, ri = max(candidates, default=(0, 0, -1))
            if overlap >= threshold:
                used.add(ri); flags.append(1); overlaps.append(overlap)
                matches.append({"reference_index": ri, "prediction_index": pi, "iou": overlap})
            elif any(r.get("page_id") == pred.get("page_id") and iou(r["box"], pred["box"]) >= threshold for r in ignored):
                continue
            else:
                flags.append(0)
        tp = sum(flags)
        ap = None
        if refs:
            precisions, hits = [], 0
            for rank, hit in enumerate(flags, 1):
                hits += hit
                precisions.append(hits / rank)
            for k in range(len(precisions)-2, -1, -1):
                precisions[k] = max(precisions[k], precisions[k+1])
            ap = sum(p for p, hit in zip(precisions, flags) if hit) / len(refs)
        results[label] = dict(prf(tp, len(flags)-tp, len(refs)-tp), ap=ap,
                              mean_matched_iou=sum(overlaps)/len(overlaps) if overlaps else None)
    aps = [r["ap"] for r in results.values() if r["ap"] is not None]
    counts = {k: sum(r[k] for r in results.values()) for k in ("tp", "fp", "fn")}
    return {"status": "SCORED", "threshold": threshold, "per_class": results,
            "micro": prf(**counts), "map": sum(aps)/len(aps) if aps else None,
            "matches": matches, "excluded_prediction_classes": sorted({p["label"] for p in prediction} - set(classes))}


def mean_ap(reference, prediction, classes, thresholds=tuple(0.5 + i*0.05 for i in range(10))):
    reference, prediction, classes, thresholds = list(reference), list(prediction), list(classes), tuple(thresholds)
    if not thresholds:
        raise ValueError("At least one IoU threshold is required")
    scores = [detection(reference, prediction, classes, t) for t in thresholds]
    available = [s["map"] for s in scores if s["map"] is not None]
    return {"thresholds": list(thresholds), "map": sum(available)/len(available) if available else None,
            "by_threshold": scores, "method": "all-points-envelope-v1; not COCO 101-point AP"}
