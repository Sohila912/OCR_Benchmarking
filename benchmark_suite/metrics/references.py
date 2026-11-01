"""Reference scope contracts. Never invent complete English page transcripts."""

from html.parser import HTMLParser

from markdown_it import MarkdownIt

from .layout import box


class VisibleHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)

    def handle_starttag(self, tag, attrs):
        if tag in {"td", "th", "tr", "p", "br", "div", "li"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"td", "th", "tr", "p", "div", "li"}:
            self.parts.append("\n")


def markdown_content(source):
    """CommonMark content: preserve code/math source; omit link URLs/image alt.

    HTML cell text remains in source order. This is a versioned representation,
    not an inferred visual/RTL order or a LaTeX-to-Unicode transcription.
    """
    parts = []
    parser = MarkdownIt("commonmark", {"html": True})

    def visit(tokens):
        for token in tokens:
            if token.type == "image":
                continue
            if token.children:
                visit(token.children)
            elif token.type in {"text", "code_inline", "code_block", "fence"}:
                parts.append(token.content)
            elif token.type in {"html_inline", "html_block"}:
                html = VisibleHTML(); html.feed(token.content); html.close()
                parts.extend(html.parts)
            elif token.type in {"softbreak", "hardbreak"} or token.type.endswith("_close") and token.block:
                parts.append("\n")
    visit(parser.parse(source))
    return "".join(parts)


def english_regions(page):
    """Only explicit nonignored text fields; retain publisher IDs and polygons.

    Consumers must independently match regions/crops before text scoring. Do not
    compare this partial reference against full-page model output. LaTeX-only,
    table-HTML-only and untranscribed figure content have no text truth here.
    """
    regions = []
    for region in page["layout_dets"]:
        if not region.get("ignore", False) and isinstance(region.get("text"), str) and region["text"].strip():
            regions.append({"id": region["anno_id"], "raw": region["text"],
                            "content": markdown_content(region["text"]),
                            "polygon": region.get("poly"), "order": region.get("order"),
                            "label": region["category_type"]})
    return {"scope": "explicit_text_regions", "regions": regions,
            "full_page_text": None, "full_page_status": "NOT_EVALUATED",
            "reason": "No certified complete page transcription; independent region matching required"}


def layout_reference(page, label_map):
    """Convert valid publisher polygons to disclosed axis-aligned envelopes.

    Unknown source categories are returned as excluded regions. The runner must
    honor these masks and the manifest geometry gate before calling metrics.
    """
    regions, excluded = [], []
    width, height = page["page_info"]["width"], page["page_info"]["height"]
    for region in page["layout_dets"]:
        polygon = region["poly"]
        if len(polygon) < 6 or len(polygon) % 2:
            raise ValueError("Invalid source polygon")
        xs, ys = polygon[::2], polygon[1::2]
        coords = box((min(xs), min(ys), max(xs), max(ys)))
        if not all(0 <= x <= width for x in xs) or not all(0 <= y <= height for y in ys):
            raise ValueError("Source polygon outside page; never clip truth")
        item = {"id": region["anno_id"], "box": coords, "source_label": region["category_type"],
                "ignore": region.get("ignore", False)}
        if region["category_type"] in label_map:
            regions.append(dict(item, label=label_map[region["category_type"]]))
        else:
            excluded.append(item)
    return {"regions": regions, "excluded_regions": excluded, "box_policy": "axis-aligned polygon envelope"}


def ordered_reference(page):
    regions = [r for r in page["layout_dets"] if not r.get("ignore", False) and r.get("order") is not None]
    orders = [r["order"] for r in regions]
    ids = [r["anno_id"] for r in regions]
    if len(set(orders)) != len(orders) or len(set(ids)) != len(ids):
        raise ValueError("Ambiguous source order or IDs")
    return [r["anno_id"] for r in sorted(regions, key=lambda r: r["order"])]
