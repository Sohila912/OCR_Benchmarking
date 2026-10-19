import sys
import types
from pathlib import Path

import pytest
from PIL import Image

from OCR.config import Settings, load_settings
from OCR.providers.qwen_ollama import QwenOllamaProvider, parse_document
from OCR.service import OCRService, PROVIDER_TYPES


class FakeAsyncClient:
    calls = []
    response = {"message": {"content": "Invoice total: 123.45"}}

    def __init__(self, host=None, timeout=None):
        self.host = host
        self.timeout = timeout

    async def chat(self, **kwargs):
        self.calls.append((self.host, kwargs))
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


@pytest.fixture
def ollama_module(monkeypatch):
    FakeAsyncClient.calls = []
    FakeAsyncClient.response = {"message": {"content": "Invoice total: 123.45"}}
    monkeypatch.setitem(sys.modules, "ollama", types.SimpleNamespace(AsyncClient=FakeAsyncClient))
    return FakeAsyncClient


def image_file(tmp_path: Path) -> Path:
    path = tmp_path / "page.png"
    Image.new("RGB", (20, 20), "white").save(path)
    return path


@pytest.mark.anyio
async def test_parse_document_uses_non_streaming_qwen_request(tmp_path, ollama_module):
    result = await parse_document(str(image_file(tmp_path)))
    assert result == "Invoice total: 123.45"
    _, call = ollama_module.calls[0]
    assert call["model"] == "qwen2.5vl:3b"
    assert call["stream"] is False
    assert call["keep_alive"] == 300
    assert call["messages"][0]["images"]


@pytest.mark.anyio
async def test_parse_document_rejects_missing_and_invalid_files(tmp_path, ollama_module):
    with pytest.raises(FileNotFoundError):
        await parse_document(str(tmp_path / "missing.png"))
    bad = tmp_path / "bad.png"
    bad.write_bytes(b"not an image")
    with pytest.raises(ValueError, match="unreadable"):
        await parse_document(str(bad))


@pytest.mark.anyio
async def test_parse_document_surfaces_connection_and_empty_response(tmp_path, ollama_module):
    ollama_module.response = ConnectionError("Ollama is unavailable")
    with pytest.raises(ConnectionError):
        await parse_document(str(image_file(tmp_path)))
    ollama_module.response = {"message": {"content": ""}}
    with pytest.raises(ValueError, match="empty"):
        await parse_document(str(image_file(tmp_path)))


def test_qwen_is_selectable_without_changing_default_or_paddle(settings):
    assert Settings().provider == "tesseract"
    assert "paddle_vl" in PROVIDER_TYPES
    assert PROVIDER_TYPES["qwen_ollama"] is QwenOllamaProvider
    service = OCRService(settings)
    assert service.select("qwen_ollama").provider_id == "qwen_ollama"
    assert service.select("paddle_vl").provider_id == "paddle_vl"


def test_ollama_environment_configuration(monkeypatch):
    monkeypatch.setenv("OLLAMA_HOST", "http://127.0.0.1:11434")
    monkeypatch.setenv("OLLAMA_OCR_MODEL", "qwen2.5vl:3b")
    monkeypatch.setenv("OLLAMA_KEEP_ALIVE", "0")
    monkeypatch.setenv("OLLAMA_OCR_TIMEOUT", "90")
    settings = load_settings(None)
    assert settings.ollama_host == "http://127.0.0.1:11434"
    assert settings.ollama_ocr_model == "qwen2.5vl:3b"
    assert settings.ollama_keep_alive == 0
    assert settings.ollama_ocr_timeout == 90


@pytest.mark.anyio
async def test_qwen_caps_large_images_before_sending(tmp_path, ollama_module):
    import io
    from OCR.providers.qwen_ollama import _parse_document
    path = tmp_path / "large.png"
    Image.new("RGB", (2400, 3200), "white").save(path)
    await _parse_document(str(path), host="http://localhost:11434", model="qwen2.5vl:3b",
                          keep_alive=300, timeout=1800, num_ctx=4096,
                          max_image_pixels=1000000)
    _, call = ollama_module.calls[-1]
    with Image.open(io.BytesIO(call["messages"][0]["images"][0])) as sent:
        assert sent.width * sent.height <= 1000000
        assert abs(sent.width / sent.height - 0.75) < 0.01
    assert call["options"] == {"num_ctx": 4096, "temperature": 0}


def test_qwen_context_and_image_budget_load_from_dotenv(tmp_path):
    env = tmp_path / ".env"
    env.write_text("OLLAMA_NUM_CTX=6144\nOLLAMA_MAX_IMAGE_PIXELS=900000\n")
    settings = load_settings(env)
    assert settings.ollama_num_ctx == 6144
    assert settings.ollama_max_image_pixels == 900000


@pytest.mark.anyio
async def test_qwen_explicit_cpu_execution(tmp_path, ollama_module):
    from OCR.providers.qwen_ollama import _parse_document
    await _parse_document(str(image_file(tmp_path)), host="http://localhost:11434",
                          model="qwen2.5vl:3b", keep_alive=300, timeout=1800, num_gpu=0)
    assert ollama_module.calls[-1][1]["options"]["num_gpu"] == 0
