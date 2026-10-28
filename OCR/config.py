"""Application settings, loaded explicitly without changing the environment."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator


REPOSITORY_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseModel):
    """Configuration for application adapters, independent of legacy runners."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
        validate_default=True,
    )

    upload_dir: Path = REPOSITORY_ROOT / "runtime" / "uploads"
    benchmark_db: Path = REPOSITORY_ROOT / "runtime" / "benchmarks.sqlite3"
    benchmark_retention_days: int = Field(default=90, ge=1, le=3650)
    pdf_dpi: int = Field(default=300, gt=0)
    poppler_path: Path | None = None
    tesseract_cmd: str = Field(default="tesseract", min_length=1)
    tesseract_lang: str = Field(default="eng", min_length=1)
    api_url: str = Field(default="http://127.0.0.1:8000", min_length=1)
    provider: Literal["paddle_vl", "docling", "tesseract", "qwen_ollama"] = "tesseract"
    temp_dir: Path = REPOSITORY_ROOT / "runtime" / "tmp"
    output_dir: Path = REPOSITORY_ROOT / "runtime" / "outputs"
    cache_enabled: bool = True
    cache_wait_seconds: float = Field(default=7200, gt=0)
    cache_pipeline_revision: str = Field(default="1", min_length=1)
    api_host: str = Field(default="127.0.0.1", min_length=1)
    api_port: int = Field(default=8000, ge=1, le=65535)
    max_upload_bytes: int = Field(default=50 * 1024 * 1024, gt=0)
    max_pages: int = Field(default=100, gt=0)
    retain_uploads: bool = True
    operation_timeout: int = Field(default=120, gt=0)
    paddle_vl_model_dir: Path | None = None
    paddle_layout_model_dir: Path | None = None
    paddle_model_revision: str | None = None
    paddle_min_memory_gib: float = Field(default=6, ge=0, le=1024)
    paddle_device: str = Field(default="cpu", min_length=1)
    docling_artifacts_path: Path | None = None
    docling_model_revision: str | None = None
    docling_device: str = Field(default="cpu", min_length=1)
    ollama_host: str = Field(default="http://localhost:11434", min_length=1)
    ollama_ocr_model: str = Field(default="qwen2.5vl:3b", min_length=1)
    ollama_keep_alive: int = Field(default=300, ge=0)
    ollama_ocr_timeout: int = Field(default=1800, gt=0)
    ollama_num_gpu: int | None = Field(default=None, ge=0)
    ollama_num_ctx: int = Field(default=4096, gt=0)
    ollama_max_image_pixels: int = Field(default=1000000, gt=0)

    @field_validator("api_url", "ollama_host")
    @classmethod
    def validate_service_url(cls, value: str, info) -> str:
        if info.field_name == "ollama_host" and "://" not in value:
            value = "http://" + value
        parsed = urlsplit(value)
        if (parsed.scheme not in ("http", "https") or not parsed.hostname
                or parsed.username is not None or parsed.password is not None
                or parsed.query or parsed.fragment):
            raise ValueError("Service URLs require HTTP(S), a host, and no embedded credentials, query or fragment.")
        _ = parsed.port  # Validate malformed/out-of-range ports.
        return value.rstrip("/")

    @field_validator("upload_dir", "temp_dir", "output_dir", "benchmark_db", "poppler_path", "paddle_vl_model_dir", "paddle_layout_model_dir", "docling_artifacts_path", mode="before")
    @classmethod
    def reject_empty_directory(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip()
            if not value:
                raise ValueError("Directory paths must not be empty.")
        return value

    @field_validator("upload_dir", "temp_dir", "output_dir", "poppler_path", "paddle_vl_model_dir", "paddle_layout_model_dir", "docling_artifacts_path")
    @classmethod
    def resolve_directory(cls, value: Path | None) -> Path | None:
        if value is None:
            return None
        path = value.expanduser()
        if not path.is_absolute():
            path = REPOSITORY_ROOT / path
        return path.resolve()

    @field_validator("poppler_path")
    @classmethod
    def resolve_poppler_install_root(cls, value: Path | None) -> Path | None:
        if value is None:
            return None
        binary_directory = value / "Library" / "bin"
        suffix = ".exe" if os.name == "nt" else ""
        if all((binary_directory / f"{name}{suffix}").is_file() for name in ("pdfinfo", "pdftoppm")):
            return binary_directory
        return value


def load_settings(env_file: Path | None = REPOSITORY_ROOT / ".env") -> Settings:
    """Read .env then environment overrides, without mutating os.environ.

    With no Poppler override, adapters should use system PATH discovery.
    Tesseract accepts a command on PATH or an explicit executable path.
    """
    environment_fields = {"OCR_" + field.upper(): field for field in Settings.model_fields}
    environment_fields.update({
        "OLLAMA_HOST": "ollama_host",
        "OLLAMA_OCR_MODEL": "ollama_ocr_model",
        "OLLAMA_KEEP_ALIVE": "ollama_keep_alive",
        "OLLAMA_OCR_TIMEOUT": "ollama_ocr_timeout",
        "OLLAMA_NUM_CTX": "ollama_num_ctx",
        "OLLAMA_NUM_GPU": "ollama_num_gpu",
        "OLLAMA_MAX_IMAGE_PIXELS": "ollama_max_image_pixels",
    })
    file_values = {}
    if env_file is not None and env_file.is_file():
        from dotenv import dotenv_values
        file_values = dotenv_values(env_file, interpolate=False, encoding="utf-8-sig")
    merged = {**file_values, **os.environ}
    values = {
        field: merged[variable]
        for variable, field in environment_fields.items()
        if variable in merged
    }
    return Settings.model_validate(values)
