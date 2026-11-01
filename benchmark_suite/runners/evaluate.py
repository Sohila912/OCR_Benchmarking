"""Offline reference routing with capability, scope and independent geometry gates."""

import json
import re

from benchmark_suite.metrics import availability, charts, layout, reading_order, references, tables, text


def unavailable(reason):
    return {"status": "NOT_EVALUATED", "reason": reason, "value": None}


def pixels(bounds, page, record):
    if bounds is None or page is None:
        raise ValueError("Explicit geometry is required")
    w, h = record["width"], record["height"]
    if bounds.units == "normalized":
        sw, sh = 1, 1
    elif page.dimension_units == bounds.units and page.width and page.height:
        sw, sh = page.width, page.height
    else:
        raise ValueError("Coordinate units/dimensions unavailable")
    a, b, c, d = bounds.x_min, bounds.y_min, bounds.x_max, bounds.y_max
    if not (0 <= a < c <= sw and 0 <= b < d <= sh):
        raise ValueError("Invalid or outside-page predicted box")
    if bounds.origin == "bottom_left":
        b, d = sh-d, sh-b
    return layout.box((a*w/sw, b*h/sh, c*w/sw, d*h/sh))


def overlap_fraction(a, b):
    area = max(0, min(a[2], b[2])-max(a[0], b[0]))*max(0, min(a[3], b[3])-max(a[1], b[1]))
    return area/((a[2]-a[0])*(a[3]-a[1]))


def evaluate_record(record, reference_payload, prediction, spec, config):
    """Single frozen image unit. No output fields become independent truth."""
    caps, eligible = spec.capabilities, record["evaluation_capabilities"]
    options = text.Normalization(**config["text"]["normalization"])
    threshold = config["layout"]["iou_threshold"]
    routing = config["routing"]
    if any(not 0 < value <= 1 for value in (threshold, routing["text_prediction_area_overlap"], routing["excluded_mask_prediction_area_overlap"], routing["table_pair_iou"])):
        raise ValueError("Routing overlap thresholds must be in (0,1]")
    scores = {name: availability(name in eligible, getattr(caps, name, False))
              for name in ("text", "layout", "reading_order", "tables")}
    scores["chart_type"] = charts.classification(None, {})
    scores["chart_numeric"] = charts.numeric(None, {})
    scores["chart_text"] = charts.chart_text(None, "")
    scores["chart_components"] = charts.completeness(None, [])
    page = next((p for p in prediction.result.pages or [] if p.page_number == 1), None)
    blocks = page.blocks or [] if page else []
    if record["language"] == "ar":
        if scores["text"] is None:
            value = prediction.result.markdown if prediction.text_format == "markdown" else prediction.result.text
            if value is None:
                scores["text"] = unavailable("PREDICTION_TEXT_FIELD_UNAVAILABLE")
            else:
                converted = references.markdown_content(value) if prediction.text_format == "markdown" else value
                scores["text"] = {"status": "SCORED", "scope": "page-content",
                    "serialization": text.evaluate(reference_payload, value, options),
                    "content": text.evaluate(references.markdown_content(reference_payload), converted, options)}
        if scores["tables"] is None:
            refs = re.findall(r"<table\b[^>]*>.*?</table\s*>", reference_payload, flags=re.I | re.S)
            preds = [t.html for t in prediction.tables or [] if t.page_number == 1]
            if not preds:
                scores["tables"] = table_result("all-reference-tables-missed", [table_score(r, "", config) for r in refs])
            elif len(refs) == len(preds) == 1:
                scores["tables"] = table_result("single-table-page", [table_score(refs[0], preds[0], config)])
            else:
                scores["tables"] = unavailable("TABLE_ALIGNMENT_UNAVAILABLE: no Arabic table boxes/order truth")
        scores["figure_detection"] = unavailable("REFERENCE_UNAVAILABLE")
        return scores

    source = json.loads(reference_payload)
    region_truth = references.english_regions(source)["regions"]
    if "layout" not in eligible:
        for key in ("text", "layout", "reading_order", "tables"):
            if scores[key] is None:
                scores[key] = unavailable("REFERENCE_GEOMETRY_GATE")
        scores["figure_detection"] = unavailable("REFERENCE_GEOMETRY_GATE")
        return scores
    truth = references.layout_reference(source, config["layout"]["omnidocbench_labels"])
    try:
        geometry = [(index, block, pixels(block.bounding_box, page, record)) for index, block in enumerate(blocks)]
    except ValueError:
        for key in ("text", "layout", "reading_order", "tables"):
            if scores[key] is None:
                scores[key] = unavailable("PREDICTION_GEOMETRY_UNAVAILABLE_OR_INVALID")
        scores["figure_detection"] = unavailable("PREDICTION_GEOMETRY_UNAVAILABLE_OR_INVALID")
        return scores
    # None means no geometry capability; [] with declared layout is a scored miss.
    if page is None or page.blocks is None:
        for key in ("text", "layout", "reading_order", "tables"):
            if scores[key] is None:
                scores[key] = unavailable("INDEPENDENT_BLOCK_GEOMETRY_UNAVAILABLE")
        scores["figure_detection"] = unavailable("INDEPENDENT_BLOCK_GEOMETRY_UNAVAILABLE")
        return scores

    if scores["text"] is None:
        allocated = {r["id"]: [] for r in region_truth}
        unassigned = 0
        for index, block, coords in geometry:
            candidates = []
            for ri, region in enumerate(region_truth):
                poly = region["polygon"]
                rect = (min(poly[::2]), min(poly[1::2]), max(poly[::2]), max(poly[1::2]))
                overlap = overlap_fraction(coords, rect)
                if overlap >= routing["text_prediction_area_overlap"]:
                    candidates.append((overlap, -ri, region["id"]))
            if candidates:
                allocated[max(candidates)[2]].append((index, block))
            else:
                unassigned += 1
        items = []
        for region in region_truth:
            assigned = allocated[region["id"]]
            # Preserve declared provider order; never sort spatially using truth.
            if assigned and all(b.reading_order is not None for _, b in assigned):
                assigned.sort(key=lambda item: (item[1].reading_order, item[0]))
            chunks = [(b.markdown, True) if prediction.text_format == "markdown" and b.markdown is not None else (b.text or "", False) for _, b in assigned]
            raw = "\n".join(value for value, _ in chunks)
            converted = "\n".join(references.markdown_content(value) if markdown else value for value, markdown in chunks)
            items.append({"reference_id": region["id"], "matched_blocks": len(assigned),
                          "serialization": text.evaluate(region["raw"], raw, options),
                          "content": text.evaluate(region["content"], converted, options)})
        scores["text"] = {"status": "SCORED", "scope": "independently-allocated-text-regions",
                          "items": items, "unassigned_prediction_blocks": unassigned,
                          "matched_reference_regions": sum(bool(allocated[r["id"]]) for r in region_truth),
                          "reference_regions": len(region_truth), "allocation": "prediction-area overlap; largest overlap; source-index tie",
                          "allocation_threshold": routing["text_prediction_area_overlap"]}

    preds, excluded, unknown_labels = [], 0, set()
    for index, block, coords in geometry:
        label = spec.label_map.get(block.block_type)
        if label is None:
            excluded += 1
            unknown_labels.add(str(block.block_type))
            continue
        valid_overlap = any(r["label"] == label and layout.iou(coords, r["box"]) >= threshold for r in truth["regions"] if not r["ignore"])
        if not valid_overlap and any(overlap_fraction(coords, r["box"]) >= routing["excluded_mask_prediction_area_overlap"] for r in truth["excluded_regions"]):
            excluded += 1
            continue
        preds.append({"label": label, "box": coords, "score": block.confidence,
                      "block_index": index})
    # The dataset-wide taxonomy defines annotated negative classes as well as
    # positives. A figure prediction on a paragraph-only page is still an FP.
    classes = sorted(set(config["layout"]["omnidocbench_labels"].values()))
    confidence_complete = all(p["score"] is not None for p in preds)
    if not confidence_complete:
        # Matching PR/order needs a fixed tie policy; AP is withheld without scores.
        preds = [dict(p, score=1.0) for p in preds]
    detected = layout.detection(truth["regions"], preds, classes, threshold)
    if unknown_labels:
        for key in ("layout", "reading_order"):
            if scores[key] is None:
                scores[key] = dict(unavailable("MODEL_LABEL_MAPPING_UNAVAILABLE"), labels=sorted(unknown_labels))
    if scores["layout"] is None:
        scores["layout"] = {"status": "SCORED", "detection": detected,
            "map": layout.mean_ap(truth["regions"], preds, classes, config["layout"]["map_thresholds"]) if confidence_complete else unavailable("DETECTION_CONFIDENCE_UNAVAILABLE"),
            "excluded_prediction_blocks": excluded,
            "evaluation_inputs": {"reference": truth["regions"], "prediction": preds, "classes": classes,
                                  "confidence_complete": confidence_complete},
            "confidence_policy": "provider confidence" if confidence_complete else "stable array order for PR; AP not evaluated"}
        if not confidence_complete:
            for v in detected["per_class"].values():
                v["ap"] = None
            detected["map"] = None
    if scores["reading_order"] is None:
        order = references.ordered_reference(source)
        matched = []
        for match in detected["matches"]:
            rid = truth["regions"][match["reference_index"]]["id"]
            pi = preds[match["prediction_index"]]["block_index"]
            if rid in order and blocks[pi].reading_order is not None:
                matched.append((blocks[pi].reading_order, pi, rid))
        if len({o for o, _, _ in matched}) != len(matched):
            scores["reading_order"] = unavailable("TIED_PREDICTED_READING_ORDER")
        else:
            scores["reading_order"] = reading_order.evaluate(order, [rid for _, _, rid in sorted(matched)])
    scores["figure_detection"] = availability(True, caps.chart_detection or caps.layout)
    if scores["figure_detection"] is None:
        scores["figure_detection"] = layout.detection(truth["regions"], preds, ["figure"], threshold) if not unknown_labels else unavailable("MODEL_LABEL_MAPPING_UNAVAILABLE")
        if not confidence_complete and not unknown_labels:
            scores["figure_detection"]["map"] = None
            scores["figure_detection"]["per_class"]["figure"]["ap"] = None
    if scores["tables"] is None:
        refs = [r for r in source["layout_dets"] if not r.get("ignore") and r.get("html")]
        truth_tables = [{"label": "table", "box": (min(r["poly"][::2]), min(r["poly"][1::2]), max(r["poly"][::2]), max(r["poly"][1::2]))} for r in refs]
        predicted_tables = [t for t in prediction.tables or [] if t.page_number == 1]
        try:
            pred_boxes = [{"label": "table", "score": 1.0, "box": pixels(t.bounding_box, page, record)} for t in predicted_tables]
            pairing = layout.detection(truth_tables, pred_boxes, ["table"], routing["table_pair_iou"])
            mapping = {m["reference_index"]: m["prediction_index"] for m in pairing["matches"]}
            scores["tables"] = table_result("geometry-paired-tables",
                [table_score(r["html"], predicted_tables[mapping[i]].html if i in mapping else "", config) for i, r in enumerate(refs)], detection=pairing)
            # No actual table confidence is provided by this structure envelope.
            pairing["map"] = None
            pairing["per_class"]["table"]["ap"] = None
        except ValueError:
            scores["tables"] = unavailable("TABLE_GEOMETRY_UNAVAILABLE_OR_INVALID")
    return scores


def table_score(reference, prediction, config):
    return tables.evaluate(reference, prediction, config["tables"]["max_nodes"], config["tables"]["max_states"])


def table_result(scope, items, **extra):
    scored = sum(item["status"] == "SCORED" for item in items)
    return {"status": "SCORED" if scored else "NOT_EVALUATED", "scope": scope,
            "reason": None if scored else "NO_SCORABLE_TABLE_REFERENCES", "items": items,
            "reference_tables": len(items), "scored_tables": scored, **extra}
