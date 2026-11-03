"""Benchmark envelope reuses production OCRResult without modifying it."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from OCR.schemas import BoundingBox, OCRResult


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Capabilities(StrictModel):
    text: bool = False
    layout: bool = False
    reading_order: bool = False
    tables: bool = False
    chart_detection: bool = False
    chart_type: bool = False
    chart_text: bool = False
    chart_numeric: bool = False


class Table(StrictModel):
    table_id: str = Field(min_length=1)
    page_number: int = Field(ge=1)
    html: str
    bounding_box: BoundingBox | None = None


class Prediction(StrictModel):
    result: OCRResult
    text_format: Literal["plain", "markdown"]
    tables: list[Table] | None = None
    # Provider-specific chart structures survive without inferred annotations.
    charts: list[dict] | None = None
    coordinate_notes: str = Field(min_length=1)


class Requirements(StrictModel):
    compatibility: Literal["COMPATIBLE", "LIMITED", "INCOMPATIBLE", "UNKNOWN"]
    evidence: str = Field(min_length=1)
    ram_bytes: int = Field(ge=0)
    disk_bytes: int = Field(ge=0)
    vram_bytes: int = Field(default=0, ge=0)
    min_compute_capability: float = Field(default=0, ge=0)


class AdapterSpec(StrictModel):
    model_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    model_revision: str = Field(min_length=1)
    adapter_revision: str = Field(min_length=1)
    # Hashes of model/native assets and adapter source, checked before loading.
    assets: dict[str, str] = Field(default_factory=dict)
    source_files: dict[str, str] = Field(default_factory=dict)
    packages: dict[str, str] = Field(default_factory=dict)
    native_versions: dict[str, str] = Field(default_factory=dict)
    gpu_backend: Literal["none", "torch", "paddle", "native"] = "none"
    capabilities: Capabilities
    label_map: dict[str, str] = Field(default_factory=dict)
    requirements: Requirements
    raw_level: str = Field(min_length=1)


class RunConfig(StrictModel):
    purpose: Literal["benchmark", "fixture"] = "benchmark"
    device: str = Field(pattern=r"^(cpu|cuda:[0-9]+)$")
    precision: str = Field(min_length=1)
    batch_size: int = Field(default=1, ge=1)
    dpi: int | None = Field(default=None, gt=0)
    preprocessing: dict
    adapter_options: dict = Field(default_factory=dict)
    location: Literal["local"] = "local"
    language: Literal["both", "en", "ar"] = "both"
    max_documents: int | None = Field(default=None, ge=1)
    sampling: Literal["manifest", "language-round-robin"] = "manifest"
