"""Ordered tree edit similarity and span-aware logical-grid cell matching.

TEDS variant v1 includes the table root in the normalization denominator,
recognizes th cells, preserves section tags and inline markup tokens. This is
not byte-identical to the PubTabNet reference implementation; see METRICS.md.
"""

from dataclasses import dataclass
from functools import lru_cache
from html.parser import HTMLParser

from rapidfuzz.distance import Levenshtein

from . import prf
from .text import score


@dataclass(frozen=True)
class Node:
    tag: str
    rowspan: int = 1
    colspan: int = 1
    tokens: tuple = ()
    children: tuple = ()


class TableParser(HTMLParser):
    """Strict supported table dialect; no browser recovery or source correction."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.roots = []
        self.inline = []
        self.cell = None

    def handle_starttag(self, tag, attrs):
        if self.cell is not None:
            if tag in {"table", "tr", "td", "th", "thead", "tbody", "tfoot"}:
                raise ValueError("Nested/unclosed table cell")
            self.cell["tokens"].append(f"<{tag}>")
            if tag not in {"br", "img", "hr", "wbr"}:
                self.inline.append(tag)
            return
        allowed = {None: {"table"}, "table": {"thead", "tbody", "tfoot", "tr"},
                   "thead": {"tr"}, "tbody": {"tr"}, "tfoot": {"tr"}, "tr": {"td", "th"}}
        parent = self.stack[-1]["tag"] if self.stack else None
        if tag not in allowed.get(parent, set()):
            raise ValueError("Unsupported table hierarchy")
        attrs = dict(attrs)
        rs, cs = int(attrs.get("rowspan", 1)), int(attrs.get("colspan", 1))
        if not 1 <= rs <= 1000 or not 1 <= cs <= 1000:
            raise ValueError("Invalid span")
        item = {"tag": tag, "rowspan": rs, "colspan": cs, "tokens": [], "children": []}
        self.stack.append(item)
        if tag in {"td", "th"}:
            self.cell = item

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in {"br", "img", "hr", "wbr"}:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if self.cell is not None and tag not in {"td", "th"}:
            if not self.inline or self.inline.pop() != tag:
                raise ValueError("Unbalanced inline content")
            self.cell["tokens"].append(f"</{tag}>")
            return
        if not self.stack or self.stack[-1]["tag"] != tag or self.inline:
            raise ValueError("Unbalanced table")
        item = self.stack.pop()
        node = Node(item["tag"], item["rowspan"], item["colspan"], tuple(item["tokens"]), tuple(item["children"]))
        if tag in {"td", "th"}:
            self.cell = None
        (self.stack[-1]["children"] if self.stack else self.roots).append(node)

    def handle_data(self, data):
        if self.cell is not None:
            self.cell["tokens"].extend(data)
        elif data.strip():
            raise ValueError("Text outside cells")


def parse_table(markup):
    parser = TableParser()
    parser.feed(markup); parser.close()
    if parser.stack or len(parser.roots) != 1:
        raise ValueError("Expected exactly one complete table fragment")
    return parser.roots[0]


def _size(node):
    return 1 + sum(_size(c) for c in node.children)


def tree_distance(a, b, structure_only=False, max_states=200000):
    """Exact ordered forest recurrence; delete/insert promotes children.

    A bounded memo prevents unexpectedly large tables exhausting laptop RAM.
    Exhaustion is NOT_EVALUATED, never an approximate structural score.
    """
    states = 0

    @lru_cache(maxsize=None)
    def distance(left, right):
        nonlocal states
        states += 1
        if states > max_states:
            raise RuntimeError("TREE_EDIT_STATE_LIMIT")
        if not left:
            return sum(_size(n) for n in right)
        if not right:
            return sum(_size(n) for n in left)
        x, y = left[0], right[0]
        rename = float((x.tag, x.rowspan, x.colspan) != (y.tag, y.rowspan, y.colspan))
        if not rename and x.tag in {"td", "th"} and not structure_only:
            rename = Levenshtein.distance(x.tokens, y.tokens)/max(len(x.tokens), len(y.tokens), 1)
        return min(1 + distance(x.children + left[1:], right),
                   1 + distance(left, y.children + right[1:]),
                   rename + distance(x.children, y.children) + distance(left[1:], right[1:]))

    try:
        return distance((a,), (b,))
    finally:
        distance.cache_clear()


def grid(table):
    def rows(node):
        if node.tag == "tr":
            return [node]
        return [row for child in node.children for row in rows(child)]
    row_nodes = rows(table)
    occupied, cells = set(), {}
    for r, row in enumerate(row_nodes):
        col = 0
        for cell in row.children:
            while (r, col) in occupied:
                col += 1
            key = (r, col, cell.rowspan, cell.colspan)
            slots = {(rr, cc) for rr in range(r, r+cell.rowspan) for cc in range(col, col+cell.colspan)}
            if occupied & slots or r+cell.rowspan > len(row_nodes):
                raise ValueError("Overlapping or out-of-table span")
            occupied.update(slots); cells[key] = cell; col += cell.colspan
    width = max((c+1 for _, c in occupied), default=0)
    if not occupied or len(occupied) != len(row_nodes)*width:
        raise ValueError("Empty or nonrectangular logical grid")
    return cells, len(row_nodes), width


def evaluate(reference, prediction, max_nodes=150, max_states=200000):
    if type(max_nodes) is not int or max_nodes < 1 or type(max_states) is not int or max_states < 1:
        raise ValueError("Tree resource limits must be positive integers")
    try:
        ref = parse_table(reference)
        rc, rr, rcol = grid(ref)
    except (ValueError, RecursionError):
        return {"status": "NOT_EVALUATED", "reason": "INVALID_REFERENCE_TABLE", "value": None}
    try:
        reference_nodes = _size(ref)
    except RecursionError:
        reference_nodes = max_nodes + 1
    if reference_nodes > max_nodes:
        return {"status": "NOT_EVALUATED", "reason": "TREE_EDIT_NODE_LIMIT", "value": None}
    try:
        pred = parse_table(prediction)
        pc, rows, cols = grid(pred)
    except (ValueError, RecursionError):
        return {"status": "SCORED", "reason": "INVALID_PREDICTION_TABLE", "teds": 0.0,
                "teds_structure": 0.0, "cells": prf(0, 0, len(rc))}
    try:
        n = max(reference_nodes, _size(pred))
    except RecursionError:
        return {"status": "NOT_EVALUATED", "reason": "TREE_EDIT_NODE_LIMIT", "value": None}
    if n > max_nodes:
        return {"status": "NOT_EVALUATED", "reason": "TREE_EDIT_NODE_LIMIT", "value": None}
    try:
        teds = max(0.0, 1-tree_distance(ref, pred, max_states=max_states)/n)
        structural = max(0.0, 1-tree_distance(ref, pred, True, max_states)/n)
    except (RuntimeError, RecursionError):
        return {"status": "NOT_EVALUATED", "reason": "TREE_EDIT_STATE_LIMIT", "value": None}
    common = rc.keys() & pc.keys()
    merges_r = {k for k in rc if k[2:] != (1, 1)}
    merges_p = {k for k in pc if k[2:] != (1, 1)}
    heads_r = {k for k, c in rc.items() if c.tag == "th"}
    heads_p = {k for k, c in pc.items() if c.tag == "th"}

    def matching(a, b):
        return prf(len(a & b), len(b-a), len(a-b))

    def content(cell):
        return "".join(t for t in cell.tokens if not (t.startswith("<") and t.endswith(">")))

    text_scores = [score(content(rc[k]), content(pc[k])) for k in sorted(common)]
    def boundaries(cells, axis, index):
        # Complete span descriptors of cells covering this row or column.
        return {k for k in cells if k[axis] <= index < k[axis] + k[axis+2]}

    return {"status": "SCORED", "method": "ordered-tree-teds-root-th-v1", "teds": teds,
            "teds_structure": structural, "cells": matching(set(rc), set(pc)),
            "merged_cells": matching(merges_r, merges_p),
            "headers": matching(heads_r, heads_p), "row_count_exact": rr == rows,
            "column_count_exact": rcol == cols,
            "row_structure_accuracy": sum(boundaries(rc, 0, i) == boundaries(pc, 0, i) for i in range(rr))/rr,
            "column_structure_accuracy": sum(boundaries(rc, 1, i) == boundaries(pc, 1, i) for i in range(rcol))/rcol,
            "cell_text_exact_rate": sum(s["exact_match"] for s in text_scores)/len(rc),
            "matched_cell_text_scores": text_scores,
            "matched_cell_coverage": len(common)/len(rc)}
