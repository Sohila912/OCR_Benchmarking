"""Constructors/metadata must not load models. All loading follows preflight."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from OCR.providers.base import OCRDocument

from benchmark_suite.runners.schemas import AdapterSpec, Capabilities, Prediction, RunConfig


@dataclass(frozen=True)
class RawOutput:
    data: bytes
    media_type: str


class BenchmarkAdapter(ABC):
    @abstractmethod
    def initialize(self, config: RunConfig) -> None:
        """Use existing assets only; no implicit installs, downloads or fallback."""

    def prepare(self, document: OCRDocument):
        """Optional explicit preprocessing, timed separately; default is identity."""
        return document

    @abstractmethod
    def predict(self, prepared) -> RawOutput:
        """Return original output bytes; internal phases must be disclosed."""

    @abstractmethod
    def normalize_output(self, raw: RawOutput, document: OCRDocument) -> Prediction:
        """Retain input identity and provider fields; do not invent structure."""

    @abstractmethod
    def get_capabilities(self) -> Capabilities:
        pass

    @abstractmethod
    def get_metadata(self) -> AdapterSpec:
        """Return the exact immutable spec provided before construction."""

    @abstractmethod
    def cleanup(self) -> None:
        """Release resources, including after failed initialization/prediction."""
