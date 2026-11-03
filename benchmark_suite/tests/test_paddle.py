import json
from types import SimpleNamespace

import pytest

from OCR.providers.base import OCRDocument
from benchmark_suite.adapters.base import RawOutput
from benchmark_suite.adapters.paddle import PaddleAdapter


def test_native_line_geometry_confidence_and_order_are_retained():
    document = OCRDocument(document_id="frozen", filename="page.png", path="page.png",
        source_metadata={"width": 100, "height": 200, "language": "ar"})
    adapter = PaddleAdapter(SimpleNamespace(model_revision="pinned"))
    native = {"res": {"rec_texts": ["نص", "English"], "rec_scores": [.8, .9],
        "rec_polys": [[[10, 20], [31, 22], [30, 40], [9, 38]], [[5, 50], [40, 50], [40, 60], [5, 60]]]}}
    payload = {"prediction": native, "worker_result": {"inference_seconds": 1.2},
               "native_output_directory": "D:/test"}
    raw = RawOutput(json.dumps(payload).encode(), "application/json")
    prediction = adapter.normalize_output(raw, document)
    lines = prediction.result.pages[0].blocks
    assert prediction.result.document_id == "frozen"
    assert prediction.result.text == "نص\nEnglish"
    assert [line.reading_order for line in lines] == [0, 1]
    assert lines[0].confidence == .8
    assert lines[0].bounding_box.x_min == 9
    assert lines[0].bounding_box.x_max == 31
    assert lines[0].provider_metadata["native_polygon"] == native["res"]["rec_polys"][0]
    assert prediction.tables is None


def test_inconsistent_native_array_lengths_are_rejected():
    adapter = PaddleAdapter(SimpleNamespace(model_revision="pinned"))
    data = {"prediction": {"rec_texts": ["lost"], "rec_scores": [], "rec_polys": []}}
    document = OCRDocument(document_id="frozen", filename="p.png", path="p.png")
    with pytest.raises(ValueError):
        adapter.normalize_output(RawOutput(json.dumps(data).encode(), "application/json"), document)
