"""Qwen2.5-VL OCR through a local Ollama server."""

from __future__ import annotations

import asyncio
import io
import math
import logging
import os
import tempfile
import requests
from pathlib import Path
from typing import Any

from OCR.errors import ExtractionError, InvalidDocumentError, ProviderInitializationError
from OCR.pdf import get_pdf_page_count, render_pdf_page
from OCR.providers.base import OCRDocument
from OCR.providers.common import LocalProvider, package_version
from OCR.schemas import OCRIssue, OCRPage, OCRResult

logger = logging.getLogger(__name__)

OCR_PROMPT = (
    "Extract every visible character from this document image. Preserve the original "
    "language, reading order, line breaks, punctuation, numbers, and symbols. "
    "Return only the transcription; do not summarize, translate, interpret, or invent "
    "text. If a region is unreadable, write [unreadable] rather than guessing."
)


def _response_text(response: Any) -> str:
    message = response.get("message") if isinstance(response, dict) else getattr(response, "message", None)
    content = message.get("content") if isinstance(message, dict) else getattr(message, "content", None)
    return content.strip() if isinstance(content, str) else ""


async def _parse_document(image_path: str, *, host: str, model: str,
                          keep_alive: int, timeout: int, client: Any | None = None,
                          num_ctx: int = 4096, max_image_pixels: int = 1000000,
                          num_gpu: int | None = None) -> str:
    path = Path(image_path)
    if not path.is_file():
        raise FileNotFoundError(f"Image file does not exist: {image_path}")
    payload = await asyncio.to_thread(path.read_bytes)
    if not payload:
        raise ValueError("Image file is empty.")
    try:
        from PIL import Image
        with Image.open(io.BytesIO(payload)) as image:
            image.load()
            original_size = image.size
            if image.width * image.height > max_image_pixels:
                scale = math.sqrt(max_image_pixels / (image.width * image.height))
                size = (max(1, int(image.width * scale)), max(1, int(image.height * scale)))
                image.thumbnail(size, Image.Resampling.LANCZOS)
                with io.BytesIO() as resized:
                    image.save(resized, format="PNG")
                    payload = resized.getvalue()
            logger.info("Qwen image: %s -> %s; context=%s; timeout=%ss",
                        original_size, image.size, num_ctx, timeout)
    except Exception as exc:
        raise ValueError(f"Image is unreadable: {image_path}") from exc

    try:
        from ollama import AsyncClient
    except ImportError as exc:
        raise RuntimeError("Install the Ollama Python client with: pip install ollama") from exc

    if client is None:
        client = AsyncClient(host=host, timeout=timeout)
    options = {"num_ctx": num_ctx, "temperature": 0}
    if num_gpu is not None:
        options["num_gpu"] = num_gpu
    response = await asyncio.wait_for(
        client.chat(
            model=model,
            messages=[{"role": "user", "content": OCR_PROMPT, "images": [payload]}],
            stream=False,
            keep_alive=keep_alive,
            options=options,
        ),
        timeout=timeout,
    )
    text = _response_text(response)
    if not text:
        raise ValueError("Ollama returned an empty OCR response.")
    return text


async def parse_document(image_path: str) -> str:
    """Extract text from a local image with the configured Ollama Qwen model."""
    return await _parse_document(
        image_path,
        host=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
        model=os.getenv("OLLAMA_OCR_MODEL", "qwen2.5vl:3b"),
        keep_alive=int(os.getenv("OLLAMA_KEEP_ALIVE", "300")),
        timeout=int(os.getenv("OLLAMA_OCR_TIMEOUT", "4000")),
        num_ctx=int(os.getenv("OLLAMA_NUM_CTX", "4096")),
        num_gpu=int(os.environ["OLLAMA_NUM_GPU"]) if "OLLAMA_NUM_GPU" in os.environ else None,
        max_image_pixels=int(os.getenv("OLLAMA_MAX_IMAGE_PIXELS", "1000000")),
    )


class QwenOllamaProvider(LocalProvider):
    provider_id = "qwen_ollama"

    def initialize(self) -> None:
        if self.health().status == "ready":
            return
        try:
            from ollama import AsyncClient
            try:
                response = requests.get(self.settings.ollama_host + "/api/tags", timeout=(3, 5))
                response.raise_for_status()
            except requests.RequestException as exc:
                self._state("unavailable", "Ollama server unreachable; verify host connectivity and server binding.")
                raise ProviderInitializationError("Ollama server unreachable.", provider=self.provider_id) from exc
            try:
                models = response.json()["models"]
                configured = next((model for model in models if model.get("name") == self.settings.ollama_ocr_model), None)
            except (ValueError, KeyError, TypeError, AttributeError) as exc:
                raise ProviderInitializationError("Ollama returned invalid model metadata.", provider=self.provider_id) from exc
            if configured is None:
                self._state("unavailable", "Configured Ollama model tag is unavailable on the target server.")
                raise ProviderInitializationError("Configured Ollama model tag is unavailable.", provider=self.provider_id)
            self._model_digest = configured.get("digest")
            self._client = AsyncClient(host=self.settings.ollama_host,
                                       timeout=self.settings.ollama_ocr_timeout)
        except Exception as exc:
            if self.health().status != "unavailable":
                self._state("unavailable", "Ollama client or initialization is unavailable.")
            raise ProviderInitializationError(str(exc), provider=self.provider_id) from exc
        self._state("ready")

    async def _extract_async(self, document: OCRDocument) -> OCRResult:
        settings = self.settings
        settings.temp_dir.mkdir(parents=True, exist_ok=True)
        count = get_pdf_page_count(document.path, poppler_path=settings.poppler_path, timeout=settings.operation_timeout)
        if count > settings.max_pages:
            raise InvalidDocumentError("PDF exceeds the configured page limit.", provider=self.provider_id)
        pages: list[OCRPage] = []
        with tempfile.TemporaryDirectory(dir=settings.temp_dir, prefix="qwen-ocr-") as directory:
            for number in range(1, count + 1):
                image = None
                try:
                    image = render_pdf_page(document.path, number, dpi=settings.pdf_dpi,
                                            poppler_path=settings.poppler_path, timeout=settings.operation_timeout)
                    image_path = Path(directory) / f"page-{number}.png"
                    image.save(image_path, "PNG")
                    text = await _parse_document(str(image_path), host=settings.ollama_host,
                                                  model=settings.ollama_ocr_model,
                                                  keep_alive=settings.ollama_keep_alive,
                                                  timeout=settings.ollama_ocr_timeout,
                                                  client=self._client,
                                                  num_ctx=settings.ollama_num_ctx,
                                                  num_gpu=settings.ollama_num_gpu,
                                                  max_image_pixels=settings.ollama_max_image_pixels)
                    pages.append(OCRPage(page_number=number, text=text, blocks=None,
                                         warnings=[OCRIssue(code="geometry_unavailable",
                                             message="Qwen returned transcription only; no boxes or confidence were supplied.",
                                             page_number=number)]))
                except asyncio.TimeoutError as exc:
                    raise ExtractionError(
                        f"Qwen/Ollama timed out on page {number} after "
                        f"{settings.ollama_ocr_timeout}s. CPU vision encoding can take several minutes; "
                        "reduce OLLAMA_MAX_IMAGE_PIXELS or increase OLLAMA_OCR_TIMEOUT.",
                        provider=self.provider_id) from exc
                except FileNotFoundError as exc:
                    raise InvalidDocumentError(str(exc), provider=self.provider_id) from exc
                except Exception as exc:
                    raise ExtractionError(f"Qwen/Ollama OCR failed on page {number}: {exc}", provider=self.provider_id) from exc
                finally:
                    if image is not None:
                        image.close()
        return self._result(document, pages, model_name="Qwen2.5-VL 3B via Ollama",
                            model_version=settings.ollama_ocr_model,
                            provider_metadata={"package_version": package_version("ollama"),
                                               "model_digest": self._model_digest,
                                               "ollama_host": settings.ollama_host,
                                               "keep_alive": settings.ollama_keep_alive,
                                               "num_ctx": settings.ollama_num_ctx,
                                               "num_gpu": settings.ollama_num_gpu,
                                               "max_image_pixels": settings.ollama_max_image_pixels,
                                               "text_assembly": "one Ollama transcription per rendered page"})

    def extract(self, document: OCRDocument) -> OCRResult:
        self._require_ready(document)
        try:
            return asyncio.run(self._extract_async(document))
        except ExtractionError:
            raise
        except Exception as exc:
            raise ExtractionError("Qwen/Ollama extraction failed.", provider=self.provider_id) from exc
