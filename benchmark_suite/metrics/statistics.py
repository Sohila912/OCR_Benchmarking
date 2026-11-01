"""Distribution and paired-cluster bootstrap for macro means or micro ratios."""

import math
import random
import statistics


def summarize(values):
    values = list(values)
    known = [v for v in values if v is not None]
    if not all(math.isfinite(v) for v in known):
        raise ValueError("Non-finite metric")
    return {"count": len(known), "missing": len(values)-len(known),
            "mean": statistics.mean(known) if known else None,
            "median": statistics.median(known) if known else None,
            "sample_std": statistics.stdev(known) if len(known) > 1 else None,
            "minimum": min(known) if known else None, "maximum": max(known) if known else None}


def aggregate_ratio(rows):
    """Micro includes empty-reference insertions; macro excludes undefined rates."""
    rows = list(rows)
    if any(not math.isfinite(n) or not math.isfinite(d) or n < 0 or d < 0 for n, d in rows):
        raise ValueError("Expected finite nonnegative counts")
    known = [(n, d) for n, d in rows if d]
    return {"micro": sum(n for n, d in rows)/sum(d for n, d in rows) if known else None,
            "macro": summarize([n/d if d else None for n, d in rows]),
            "zero_reference_edits": sum(n for n, d in rows if not d)}


def bootstrap(rows, *, unit, seed=1729, samples=2000, ratio=False):
    """Rows (cluster_id,value), value=(numerator,denominator) for micro ratio.

    Caller supplies known source-document clusters or explicitly labels page
    resampling. Multiple pages within a document are resampled together.
    """
    if unit not in {"document", "page"} or samples < 2 or type(samples) is not int:
        raise ValueError("Explicit resampling unit and >=2 integer samples required")
    groups = {}
    missing = 0
    for group, value in rows:
        if group is None:
            raise ValueError("Unknown cluster ID; use explicit page IDs and unit='page'")
        if value is None:
            missing += 1
            continue
        if ratio:
            aggregate_ratio([value])
        elif not math.isfinite(value):
            raise ValueError("Non-finite metric")
        groups.setdefault(group, []).append(value)
    keys = sorted(groups)
    for key in keys:
        groups[key].sort()

    def estimate(values):
        if ratio:
            denominator = sum(d for n, d in values)
            return sum(n for n, d in values)/denominator if denominator else None
        return statistics.mean(values)

    result = {"unit": unit, "seed": seed, "samples": samples, "clusters": len(keys), "missing_rows": missing,
              "qualification": "Page bootstrap; source-document independence unverified" if unit == "page" else "Caller-supplied document clusters",
              "estimate": estimate([v for k in keys for v in groups[k]]) if keys else None}
    if len(keys) < 2:
        return dict(result, status="NOT_EVALUATED", reason="INSUFFICIENT_CLUSTERS", ci95=None)
    rng = random.Random(seed)
    replicates = [estimate([v for k in rng.choices(keys, k=len(keys)) for v in groups[k]]) for _ in range(samples)]
    estimates = sorted(v for v in replicates if v is not None)
    result["undefined_replicates"] = samples-len(estimates)
    if len(estimates) < 2 or result["estimate"] is None:
        return dict(result, status="NOT_EVALUATED", reason="UNDEFINED_RATIO", ci95=None)

    def quantile(q):
        position = q*(len(estimates)-1)
        lo = int(position)
        return estimates[lo] + (estimates[min(lo+1, len(estimates)-1)]-estimates[lo])*(position-lo)

    return dict(result, status="SCORED", ci95=[quantile(0.025), quantile(0.975)], method="percentile-linear-v1")
