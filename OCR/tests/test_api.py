from pathlib import Path

from fastapi.testclient import TestClient

from app import app


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_tools_endpoint_lists_supported_engines():
    response = client.get("/tools")
    assert response.status_code == 200
    payload = response.json()
    assert "tools" in payload
    assert {"marker", "paddle", "tesseract"}.issubset(set(payload["tools"]))


def test_extract_endpoint_returns_markdown_for_supported_engine(tmp_path: Path):
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"dummy pdf")

    response = client.post(
        "/extract",
        json={"engine": "tesseract", "pdf_path": str(pdf_path)},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["engine"] == "tesseract"
    assert payload["pdf_path"] == str(pdf_path)
    assert isinstance(payload["markdown"], str)


def test_compare_endpoint_returns_all_engines(tmp_path: Path):
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"dummy pdf")

    response = client.post(
        "/extract/compare",
        json={"pdf_path": str(pdf_path)},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["pdf_path"] == str(pdf_path)
    assert len(payload["results"]) >= 3


def test_extract_returns_helpful_message_when_engine_unavailable(tmp_path: Path):
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"dummy pdf")

    response = client.post(
        "/extract",
        json={"engine": "marker", "pdf_path": str(pdf_path)},
    )

    assert response.status_code == 200
    payload = response.json()
    assert "unavailable" in payload["markdown"].lower() or "not installed" in payload["markdown"].lower()
