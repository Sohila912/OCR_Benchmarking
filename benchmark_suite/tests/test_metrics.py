"""Hand-calculated examples and adverse inputs, without model-generated truth."""

import json
from itertools import combinations
from pathlib import Path

import pytest

from benchmark_suite.metrics import availability
from benchmark_suite.metrics import charts, layout, reading_order, references, statistics, tables, text


def test_text_hand_counts():
    s = text.score("cat dog", "cat fog !")
    assert s["characters"]["edits"] == 3
    assert s["cer"] == 3/7
    assert s["wer"] == 1
    assert s["word_accuracy"] == 0
    assert s["ned"] == 3/9
    assert s["words"]["bag_matching"]["f1"] == 2/5


@pytest.mark.parametrize("ref,pred,cer,ned,exact", [("", "", None, 0, True), ("", "a", None, 1, False), ("a", "", 1, 1, False), ("a", "aaaa", 3, 0.75, False)])
def test_text_empty_and_insertions(ref, pred, cer, ned, exact):
    s = text.score(ref, pred)
    assert (s["cer"], s["ned"], s["exact_match"]) == (cer, ned, exact)
    assert s["character_accuracy"] is None if cer is None else s["character_accuracy"] == max(0, 1-cer)


def test_bag_is_not_order_accuracy():
    s = text.score("a b", "b a")
    assert s["words"]["bag_matching"]["f1"] == 1
    assert s["wer"] == 1


def test_arabic_raw_preserved_and_folds_explicit():
    raw = "إِنَّ الـمُؤْمِن ئ ء ١٢"
    opts = text.Normalization(diacritics=True, alef=True, hamza=True, tatweel=True)
    normalized = "ان المومن ي ء ١٢"
    assert text.normalize(raw, opts) == normalized
    assert text.normalize(raw, text.Normalization()) == raw
    out = text.evaluate(raw, normalized, opts)
    assert out["raw"]["cer"] > 0
    assert out["normalized"]["cer"] == 0
    assert text.normalize("é", text.Normalization(diacritics=True)) == "é"
    assert text.normalize("أ", text.Normalization(diacritics=True)) == "أ"
    assert text.normalize("e\u0301", text.Normalization()) == "é"
    assert text.normalize(" a\n b ", text.Normalization(unicode="none", whitespace=False)) == " a\n b "
    with pytest.raises(ValueError):
        text.Normalization(unicode="bad")


def region(label="table", score=1, page_id="p", coords=(0, 0, 2, 2), **kw):
    return dict(label=label, score=score, box=coords, page_id=page_id, **kw)


def test_iou_and_duplicate_detection():
    assert layout.iou((0, 0, 2, 2), (1, 0, 3, 2)) == 1/3
    s = layout.detection([region()], [region(score=.9), region(score=.8)], ["table"])
    assert s["micro"] == {"tp": 1, "fp": 1, "fn": 0, "precision": .5, "recall": 1, "f1": 2/3}
    assert s["map"] == 1


def test_ap_hand_example_and_pages_classes():
    r = [region(page_id="a"), region(page_id="b")]
    p = [region(page_id="x", score=.9), region(page_id="a", score=.8), region(page_id="b", score=.7)]
    s = layout.detection(r, p, ["table", "heading"])
    assert s["map"] == pytest.approx(2/3)
    assert s["per_class"]["heading"]["ap"] is None
    assert layout.mean_ap(r, p, ["table"])["map"] == pytest.approx(2/3)
    assert layout.detection([region()], [region(label="figure")], ["table"])["micro"]["fn"] == 1


def test_ignored_truth_and_unannotated_classes():
    s = layout.detection([region(ignore=True)], [region(), region(label="unannotated")], ["table"])
    assert s["micro"]["fp"] == 0
    assert s["map"] is None
    assert s["excluded_prediction_classes"] == ["unannotated"]
    assert layout.detection([region()], [], ["table"])["map"] == 0
    with pytest.raises(ValueError):
        layout.iou((0, 0, 0, 1), (0, 0, 1, 1))
    with pytest.raises(ValueError):
        layout.detection([], [region(score=float("nan"))], ["table"])
    with pytest.raises(KeyError):
        layout.canonicalize([region()], {})


def test_order_hand_inversion_and_missing():
    s = reading_order.evaluate(["a", "b", "c"], ["a", "c", "b"])
    assert s["inversions"] == 1
    assert s["kendall_tau"] == pytest.approx(1/3)
    assert s["normalized_inversion_rate"] == 1/3
    assert s["reading_order_accuracy"] == 2/3
    missing = reading_order.evaluate(["a", "b", "c"], ["a", "b"])
    assert missing["kendall_tau"] == 1
    assert missing["reading_order_accuracy"] == 1/3
    assert missing["pair_coverage"] == 1/3
    assert reading_order.evaluate(["يمين", "يسار"], ["يسار", "يمين"])["kendall_tau"] == -1


@pytest.mark.parametrize("ref,pred", [([1, 1], [1]), ([1], [1, 1]), ([1], [2])])
def test_order_ambiguous_ids(ref, pred):
    with pytest.raises(ValueError):
        reading_order.evaluate(ref, pred)


def test_order_single_item():
    assert reading_order.evaluate([1], [1])["kendall_tau"] is None


A = "<table><tr><th>H</th><td>cat</td></tr></table>"


def test_table_exact_and_cell_text_tree_cost():
    assert tables.evaluate(A, A)["teds"] == 1
    s = tables.evaluate(A, A.replace("cat", "cut"))
    # Four nodes including root; one cell rename has cost 1/3.
    assert s["teds"] == pytest.approx(1-1/12)
    assert s["teds_structure"] == 1
    assert s["cell_text_exact_rate"] == .5
    assert s["headers"]["f1"] == 1


def test_tree_deletion_promotes_children():
    a = tables.parse_table("<table><tbody><tr><td>x</td></tr></tbody></table>")
    b = tables.parse_table("<table><tr><td>x</td></tr></table>")
    assert tables.tree_distance(a, b) == 1
    assert tables.tree_distance(b, a) == 1


def test_ordered_tree_distance_against_exhaustive_mapping_oracle():
    # Independent oracle: enumerate every valid ancestor/order-preserving node
    # mapping; unmatched nodes cost one. These tiny trees cover promoted children,
    # sibling insertions, ancestor constraints and label substitutions.
    def nodes(root, path=()):
        return [(path, root)] + [v for i, child in enumerate(root.children) for v in nodes(child, path+(i,))]

    def ancestor(a, b):
        return len(a) < len(b) and b[:len(a)] == a

    def brute(a, b):
        aa, bb = nodes(a), nodes(b)
        best = len(aa)+len(bb)
        for size in range(min(len(aa), len(bb))+1):
            for left in combinations(aa, size):
                for right in combinations(bb, size):
                    valid = all(ancestor(left[i][0], left[j][0]) == ancestor(right[i][0], right[j][0])
                                for i in range(size) for j in range(i+1, size))
                    if valid:
                        cost = len(aa)+len(bb)-2*size + sum(x.tag != y.tag for (_, x), (_, y) in zip(left, right))
                        best = min(best, cost)
        return best

    leaf = tables.Node("x")
    candidates = [leaf, tables.Node("y"), tables.Node("r", children=(leaf,)),
                  tables.Node("r", children=(leaf, leaf)),
                  tables.Node("r", children=(tables.Node("a", children=(leaf,)), leaf)),
                  tables.Node("r", children=(leaf, tables.Node("b", children=(leaf,))))]
    for a in candidates:
        for b in candidates:
            assert tables.tree_distance(a, b, structure_only=True) == brute(a, b)


def test_table_merge_header_and_grid():
    a = '<table><tr><th colspan="2">H</th></tr><tr><td>a</td><td>b</td></tr></table>'
    b = '<table><tr><td>H</td><td></td></tr><tr><td>a</td><td>b</td></tr></table>'
    s = tables.evaluate(a, b)
    assert s["merged_cells"]["recall"] == 0
    assert s["headers"]["recall"] == 0
    assert s["cells"]["f1"] == 4/7
    assert s["row_count_exact"] and s["column_count_exact"]
    assert tables.evaluate(a, a)["teds"] == 1
    rowspan = '<table><tr><td rowspan="2">x</td><td>a</td></tr><tr><td>b</td></tr></table>'
    assert tables.evaluate(rowspan, rowspan)["merged_cells"]["f1"] == 1


@pytest.mark.parametrize("bad", ["", "<table><tr><td>x</tr></table>", '<table><tr><td rowspan="0">x</td></tr></table>', '<table><tr><td rowspan="2">x</td></tr></table>', '<table><tr><td>x</td></tr><tr><td>x</td><td>y</td></tr></table>'])
def test_bad_table_reference_vs_prediction(bad):
    assert tables.evaluate(bad, A)["status"] == "NOT_EVALUATED"
    assert tables.evaluate(A, bad)["teds"] == 0


def test_table_resource_limits_and_inline_tokens():
    assert tables.evaluate(A, A, max_nodes=1)["reason"] == "TREE_EDIT_NODE_LIMIT"
    assert tables.evaluate(A, "", max_nodes=1)["reason"] == "TREE_EDIT_NODE_LIMIT"
    assert tables.evaluate(A, A, max_states=1)["reason"] == "TREE_EDIT_STATE_LIMIT"
    b = A.replace("cat", "<b>cat</b>")
    assert tables.evaluate(A, b)["teds"] < 1
    assert tables.evaluate(A, b)["cell_text_exact_rate"] == 1


def test_chart_truth_gating_and_numeric():
    assert charts.numeric(None, {})["value"] is None
    s = charts.numeric({"a": 100, "b": 0}, {"a": 101, "b": .1, "extra": 7})
    assert s["accuracy"] == .5
    assert s["values"]["f1"] == 2/5
    assert s["matched_mae"] == .55
    assert charts.classification({"a": "bar", "b": "pie"}, {"a": "bar"})["accuracy"] == .5
    assert charts.completeness({"axis", "legend"}, {"axis"})["recall"] == .5
    assert charts.chart_text(None, "x")["status"] == "NOT_EVALUATED"
    assert availability(True, False)["status"] == "NOT_SUPPORTED"
    with pytest.raises(ValueError):
        charts.numeric({"a": float("inf")}, {})


def test_micro_macro_and_zero_denominators():
    s = statistics.aggregate_ratio([(1, 2), (0, 8), (3, 0)])
    assert s["micro"] == .4
    assert s["macro"]["mean"] == .25
    assert s["macro"]["missing"] == 1
    assert s["zero_reference_edits"] == 3
    assert statistics.summarize([None])["mean"] is None


def test_seeded_cluster_bootstrap():
    rows = [("a", 1), ("a", 3), ("b", 8)]
    s = statistics.bootstrap(rows, unit="document", samples=100)
    assert s == statistics.bootstrap(rows[::-1], unit="document", samples=100)
    assert s["ci95"] == [2, 8]
    assert s["estimate"] == 4
    assert statistics.bootstrap([("a", 1)], unit="page")["ci95"] is None
    micro = statistics.bootstrap([("a", (1, 2)), ("b", (0, 8))], unit="page", samples=100, ratio=True)
    assert micro["estimate"] == .1
    assert "unverified" in micro["qualification"]
    with pytest.raises(ValueError):
        statistics.bootstrap([(None, 1)], unit="document")
    with pytest.raises(ValueError):
        statistics.summarize([float("nan")])


def test_bootstrap_preserves_empty_reference_insertions():
    rows = [("a", (1, 0)), ("b", (0, 2))]
    s = statistics.bootstrap(rows, unit="page", samples=100, ratio=True)
    assert s["estimate"] == .5
    assert s["undefined_replicates"] > 0
    empty = statistics.bootstrap([("a", (1, 0)), ("b", (2, 0))], unit="page", samples=100, ratio=True)
    assert empty["ci95"] is None
    assert empty["reason"] == "UNDEFINED_RATIO"


def test_reference_content_and_partial_scope():
    source = '# Title\n\n**bold** [link](https://example.com) ![not transcript](x.png)\n\n<table><tr><td>١</td><td>two</td></tr></table>'
    result = references.markdown_content(source)
    assert "Title" in result and "bold link" in result and "١ two" in " ".join(result.split())
    assert "example.com" not in result and "not transcript" not in result
    page = {"layout_dets": [{"anno_id": 1, "category_type": "title", "text": "Hi"},
                            {"anno_id": 2, "category_type": "text_block", "text": "ignore", "ignore": True},
                            {"anno_id": 3, "category_type": "equation_isolated", "latex": "x=1"}]}
    assembled = references.english_regions(page)
    assert len(assembled["regions"]) == 1
    assert assembled["full_page_text"] is None


def test_config_is_valid_and_defaults_match():
    config = json.loads((Path(__file__).parents[1]/"configs/evaluation.json").read_text())
    assert text.Normalization(**config["text"]["normalization"]) == text.Normalization()
    assert config["statistics"]["primary_resampling_unit"] == "page"


def test_reference_layout_scope_and_order():
    page = {"page_info": {"width": 100, "height": 100}, "layout_dets": [
        {"anno_id": "a", "category_type": "title", "poly": [0, 0, 10, 0, 10, 10, 0, 10], "order": 2},
        {"anno_id": "b", "category_type": "mask", "poly": [20, 0, 30, 0, 30, 10, 20, 10], "order": 1}]}
    r = references.layout_reference(page, {"title": "heading"})
    assert len(r["regions"]) == len(r["excluded_regions"]) == 1
    assert references.ordered_reference(page) == ["b", "a"]
    page["layout_dets"][0]["poly"][0] = -1
    with pytest.raises(ValueError):
        references.layout_reference(page, {"title": "heading"})
    page["layout_dets"][0]["order"] = 1
    with pytest.raises(ValueError):
        references.ordered_reference(page)
