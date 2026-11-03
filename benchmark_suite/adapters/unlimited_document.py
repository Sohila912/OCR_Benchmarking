"""Normalize saved Unlimited-OCR native blocks without network or model loading."""

from pathlib import Path

from OCR.schemas import BoundingBox, OCRBlock, OCRPage, OCRResult
from benchmark_suite.metrics.references import markdown_content
from benchmark_suite.runners.schemas import Prediction, Table

LABEL_MAP = {"title": "heading", "text": "paragraph", "header": "header", "footer": "footer",
    "page_number": "page_number", "image": "figure", "figure": "figure", "picture": "figure",
    "chart": "figure", "table": "table", "equation": "equation", "ref_text": "reference",
    "image_caption": "caption", "page_footnote": "footnote", "image_footnote": "footnote"}


def normalize(record, response, upstream):
    if not response.get("done") or response.get("truncated") is not False:
        raise ValueError("Only complete, explicitly untruncated responses can be scored")
    raw = response["raw"]
    parsed = upstream._parse_blocks(raw)
    if not parsed or any(item["page"] != 1 for item in parsed):
        raise ValueError("Frozen image unit requires one native page with explicit blocks")
    blocks, tables = [], []
    for index, item in enumerate(parsed):
        coords = item["bbox"]
        bounds = None
        if coords and 0 <= coords[0] < coords[2] <= 1000 and 0 <= coords[1] < coords[3] <= 1000:
            bounds = BoundingBox(x_min=coords[0]/1000, y_min=coords[1]/1000,
                x_max=coords[2]/1000, y_max=coords[3]/1000, units="normalized", origin="top_left")
        label = upstream._base_type(item["label"])
        # Canonical upstream conversion preserves table HTML/math and strips its
        # own special tokens. Geometry/order remain the original native blocks.
        heading = f"<LEVEL{item['level']}>" if item.get("level") else ""
        box = "[" + ",".join(map(str, coords)) + "]" if coords else ""
        markdown = upstream.convert(f"<PAGE><BLOCK>{item['label']}{heading}{box}<FORK>{item['content']}")
        blocks.append(OCRBlock(block_id=f"native-{index}", block_type=label,
            text=markdown_content(markdown), markdown=markdown, reading_order=index,
            bounding_box=bounds, provider_metadata={"native": dict(item, bbox=list(coords) if coords else None)}))
        if label == "table":
            tables.append(Table(table_id=f"native-{index}", page_number=1,
                html=markdown, bounding_box=bounds))
    markdown = upstream.convert(raw)
    content = "\n\n".join(block.text for block in blocks)
    page = OCRPage(page_number=1, width=record["width"], height=record["height"],
        dimension_units="pixels", text=content, markdown=markdown, blocks=blocks)
    result = OCRResult(document_id=record["document_id"], filename=Path(record["source_path"]).name,
        source=record["source_path"], provider="baidu_unlimited_ocr_hosted",
        source_metadata={"language": record["language"], "source_sha256": record["file_hash"]},
        model_name="baidu/Unlimited-OCR-2", model_version=None,
        text=content, markdown=markdown, pages=[page], provider_metadata={
            "remote_weight_revision": "UNVERIFIED", "native_coordinate_scale": 1000,
            "order": "native block emission order; no truth-based reordering"})
    return Prediction(result=result, text_format="markdown", tables=tables,
        coordinate_notes="Native 0..1000 top-left boxes scaled to normalized units; invalid/missing boxes remain absent; no clamping or truth-based repair")
