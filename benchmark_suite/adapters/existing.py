"""Explicit bridge for already-configured production providers; no registry/load.

This bridge preserves the provider's OCRResult as raw JSON. It does not claim to
capture a vendor's internal raw engine response. Individual model tasks must
choose whether that raw boundary is sufficient and document any limitations.
"""

from OCR.schemas import OCRResult

from .base import BenchmarkAdapter, RawOutput
from benchmark_suite.runners.schemas import Prediction


class ExistingProviderAdapter(BenchmarkAdapter):
    def __init__(self, provider_factory, spec, text_format="plain"):
        self.factory, self.spec, self.text_format = provider_factory, spec, text_format
        self.provider = None
        if spec.raw_level != "production-provider-OCRResult":
            raise ValueError("The bridge only captures provider OCRResult, not vendor internals")

    def initialize(self, config):
        self.provider = self.factory(config)
        self.provider.initialize()

    def predict(self, document):
        if self.provider is None:
            raise RuntimeError("Adapter is not initialized")
        result = self.provider.extract(document)
        return RawOutput(result.model_dump_json().encode("utf-8"), "application/json")

    def normalize_output(self, raw, document):
        return Prediction(result=OCRResult.model_validate_json(raw.data), text_format=self.text_format,
                          coordinate_notes="Provider coordinate declarations preserved; no inferred geometry")

    def get_capabilities(self):
        return self.spec.capabilities

    def get_metadata(self):
        return self.spec

    def cleanup(self):
        if self.provider is not None:
            self.provider.unload()
            self.provider = None
