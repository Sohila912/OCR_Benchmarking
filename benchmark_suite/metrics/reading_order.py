"""Pairwise order uses independently matched reference IDs, never RTL heuristics."""


def evaluate(reference, prediction):
    if len(set(reference)) != len(reference) or len(set(prediction)) != len(prediction):
        raise ValueError("Order IDs must be unique")
    if set(prediction) - set(reference):
        raise ValueError("Map predicted blocks to truth IDs before order evaluation")
    positions = {v: i for i, v in enumerate(prediction)}
    inversions = compared = correct = 0
    for i, a in enumerate(reference):
        for b in reference[i+1:]:
            if a in positions and b in positions:
                compared += 1
                inversion = positions[a] > positions[b]
                inversions += inversion
                correct += not inversion
    pairs = len(reference)*(len(reference)-1)//2
    return {"status": "SCORED", "reference_items": len(reference), "matched_items": len(prediction),
            "item_coverage": len(prediction)/len(reference) if reference else None,
            "pair_coverage": compared/pairs if pairs else None,
            "inversions": inversions, "compared_pairs": compared,
            "normalized_inversion_rate": inversions/compared if compared else None,
            "kendall_tau": 1-2*inversions/compared if compared else None,
            "reading_order_accuracy": correct/pairs if pairs else None,
            "exact_order": list(reference) == list(prediction)}
