"""Application settings, loaded explicitly without changing the environment."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

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
    pdf_dpi: int = Field(default=300, gt=0)
    poppler_path: Path | None = None
    tesseract_cmd: str = Field(default="tesseract", min_length=1)
    tesseract_lang: str = Field(default="eng", min_length=1)
    api_url: str = Field(default="http://127.0.0.1:8000", min_length=1)
    provider: Literal["paddle_vl", "docling", "tesseract"] = "tesseract"
    temp_dir: Path = REPOSITORY_ROOT / "runtime" / "tmp"
    output_dir: Path = REPOSITORY_ROOT / "runtime" / "outputs"
    api_host: str = Field(default="127.0.0.1", min_length=1)
    api_port: int = Field(default=8000, ge=1, le=65535)
    max_upload_bytes: int = Field(default=50 * 1024 * 1024, gt=0)
    max_pages: int = Field(default=100, gt=0)
    operation_timeout: int = Field(default=120, gt=0)
    paddle_vl_model_dir: Path | None = None
    paddle_layout_model_dir: Path | None = None
    paddle_model_revision: str | None = None
    paddle_device: str = Field(default="cpu", min_length=1)
    docling_artifacts_path: Path | None = None
    docling_model_revision: str | None = None
    docling_device: str = Field(default="cpu", min_length=1)

    @field_validator("upload_dir", "temp_dir", "output_dir", "poppler_path", "paddle_vl_model_dir", "paddle_layout_model_dir", "docling_artifacts_path", mode="before")
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


def load_settings(env_file: Path | None = REPOSITORY_ROOT / ".env") -> Settings:
    """Read .env then environment overrides, without mutating os.environ.

    With no Poppler override, adapters should use system PATH discovery.
    Tesseract accepts a command on PATH or an explicit executable path.
    """
    environment_fields = {"OCR_" + field.upper(): field for field in Settings.model_fields}
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
