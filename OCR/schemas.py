"""Provider-neutral OCR results with optional, explicitly sourced metadata."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator


class BoundingBox(BaseModel):
    """Axis-aligned bounds in the declared page coordinate system.

    Coordinates are minimum/maximum values, regardless of origin. Normalized
    coordinates lie within [0, 1]; other coordinates retain provider values.
    """

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    x_min: float
    y_min: float
    x_max: float
    y_max: float
    units: Literal["pixels", "points", "normalized"]
    origin: Literal["top_left", "bottom_left"]

    @model_validator(mode="after")
    def validate_coordinates(self) -> BoundingBox:
        if self.x_min > self.x_max or self.y_min > self.y_max:
            raise ValueError("Bounding box minimums must not exceed maximums.")
        if self.units == "normalized":
            coordinates = (self.x_min, self.y_min, self.x_max, self.y_max)
            if any(value < 0 or value > 1 for value in coordinates):
                raise ValueError("Normalized coordinates must be within [0, 1].")
        return self


class OCRIssue(BaseModel):
    """An explicit warning or error, optionally associated with a page."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    page_number: int | None = Field(default=None, ge=1)


class OCRBlock(BaseModel):
    """A provider-reported block; absent information remains null.

    Reading order is zero-based when supplied. Confidence is normalized to
    [0, 1], not calibrated across providers. If an adapter rescales confidence,
    it must retain the original value and scale in provider_metadata.
    """

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    block_id: str | None = None
    text_start: int | None = Field(default=None, ge=0)
    text_end: int | None = Field(default=None, ge=0)
    block_type: str | None = None
    text: str | None = None
    markdown: str | None = None
    language: str | None = None
    reading_order: int | None = Field(default=None, ge=0)
    confidence: float | None = Field(default=None, ge=0, le=1)
    bounding_box: BoundingBox | None = None
    provider_metadata: dict[str, JsonValue] = Field(default_factory=dict)


class OCRPage(BaseModel):
    """A one-based page; null blocks mean block information is unavailable."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    page_number: int = Field(ge=1)
    text_start: int | None = Field(default=None, ge=0)
    text_end: int | None = Field(default=None, ge=0)
    text: str | None = None
    markdown: str | None = None
    language: str | None = None
    width: float | None = Field(default=None, gt=0)
    height: float | None = Field(default=None, gt=0)
    dimension_units: Literal["pixels", "points", "normalized"] | None = None
    blocks: list[OCRBlock] | None = None
    warnings: list[OCRIssue] = Field(default_factory=list)
    errors: list[OCRIssue] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_dimension_units(self) -> OCRPage:
        if (self.width is not None or self.height is not None) and self.dimension_units is None:
            raise ValueError("Page dimensions require explicit dimension_units.")
        return self


class OCRResult(BaseModel):
    """Document output and provenance, without inventing provider capabilities.

    The caller supplies document identity. Model/version are null when unknown;
    text, Markdown, language and page information are null when unavailable.
    Empty issue lists mean no issues were reported, not verified correctness.
    """

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    schema_version: Literal["1.0"] = "1.0"
    document_id: str = Field(min_length=1)
    filename: str = Field(min_length=1)
    source: str | None = None
    source_metadata: dict[str, JsonValue] = Field(default_factory=dict)
    provider: str = Field(min_length=1)
    model_name: str | None = None
    model_version: str | None = None
    text: str | None = None
    markdown: str | None = None
    language: str | None = None
    pages: list[OCRPage] | None = None
    warnings: list[OCRIssue] = Field(default_factory=list)
    errors: list[OCRIssue] = Field(default_factory=list)
    provider_metadata: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_provenance(self) -> OCRResult:
        numbers = [p.page_number for p in self.pages or []]
        if numbers != sorted(set(numbers)):
            raise ValueError("Pages must have unique, increasing page numbers.")
        for page in self.pages or []:
            ids = [b.block_id for b in page.blocks or [] if b.block_id is not None]
            if len(ids) != len(set(ids)):
                raise ValueError("Block IDs must be unique within a page.")
            self._check_span(self.text, page.text, page.text_start, page.text_end)
            for block in page.blocks or []:
                self._check_span(page.text, block.text, block.text_start, block.text_end)
            for issue in page.errors + page.warnings:
                if issue.page_number is not None and issue.page_number != page.page_number:
                    raise ValueError("Page issue must refer to its containing page.")
        return self

    @staticmethod
    def _check_span(parent: str | None, child: str | None, start: int | None, end: int | None) -> None:
        if start is None and end is None:
            return
        if (start is None or end is None or parent is None or child is None
                or not 0 <= start <= end <= len(parent) or parent[start:end] != child):
            raise ValueError("Text span must exactly identify the child text in its parent.")


def attach_text_provenance(result: OCRResult) -> OCRResult:
    """Attach exact Unicode character offsets, never inferred geometry or layout.

    Page spans address result.text; block spans address page.text. Missing block
    text stays unlocated. Full text is a lossless join of available page text.
    """
    pages = result.pages
    if pages is None:
        return result
    available = [p for p in pages if p.text is not None]
    result.text = "\n\n".join(p.text for p in available) if available else None
    position = 0
    for page in pages:
        if page.text is None:
            continue
        page.text_start, page.text_end = position, position + len(page.text)
        position = page.text_end + 2
        cursor = 0
        for block in page.blocks or []:
            if block.text is None:
                continue
            start = page.text.find(block.text, cursor)
            if start >= 0:
                block.text_start, block.text_end = start, start + len(block.text)
                cursor = block.text_end
    return OCRResult.model_validate(result.model_dump())
