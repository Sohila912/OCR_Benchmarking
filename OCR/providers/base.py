"""Common input, health reporting, and lifecycle for local OCR providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from OCR.schemas import OCRResult


class OCRDocument(BaseModel):
    """Caller-supplied identity and local input path.

    Construction does not read the document or verify that the path exists.
    The source is optional provenance, distinct from a temporary upload path.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    document_id: str = Field(min_length=1)
    filename: str = Field(min_length=1)
    path: Path
    source: str | None = None
    source_metadata: dict[str, JsonValue] = Field(default_factory=dict)


class ProviderHealth(BaseModel):
    """The provider's known state, without performing inference."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: str = Field(min_length=1)
    status: Literal["uninitialized", "ready", "unavailable", "error"]
    detail: str | None = None


class OCRProvider(ABC):
    """Explicit lifecycle contract for the three application adapters.

    Constructing an adapter must not initialize models. Providers must not
    silently substitute another engine or embed failure messages in OCR text.
    """

    def unload(self) -> None:
        """Release cached inference resources when switching providers."""

    @abstractmethod
    def initialize(self) -> None:
        """Initialize using installed dependencies and existing local assets.

        Repeated calls after successful initialization must be safe. Missing
        dependencies or model assets must raise an explicit exception and be
        reflected in health(). Initialization must not download model assets.
        """

    @abstractmethod
    def health(self) -> ProviderHealth:
        """Return known state without loading models or triggering downloads."""

    @abstractmethod
    def extract(self, document: OCRDocument) -> OCRResult:
        """Extract after explicit initialization, preserving input identity.

        Return provider-neutral results with unsupported fields left null and
        useful provider-specific information retained in metadata. Fatal
        failures must raise explicit exceptions. Recoverable page failures
        belong in structured errors, not in extracted text or Markdown.
        Calling this method before initialization must raise an exception.
        """
