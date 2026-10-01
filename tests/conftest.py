"""Reusable fake provider; no optional OCR packages imported."""
import pytest
from OCR.config import Settings
from OCR.providers.base import OCRProvider, ProviderHealth
from OCR.schemas import OCRResult, OCRPage, OCRBlock, attach_text_provenance


@pytest.fixture
def settings(tmp_path):
    return Settings(upload_dir=tmp_path/'uploads', temp_dir=tmp_path/'tmp', output_dir=tmp_path/'outputs')


class FakeProvider(OCRProvider):
    def __init__(self, name='tesseract', failure=None):
        self.name, self.failure = name, failure
        self.initializations = 0
        self.ready = False

    def initialize(self):
        if not self.ready:
            self.initializations += 1
            self.ready = True

    def health(self):
        return ProviderHealth(provider=self.name, status='ready' if self.ready else 'uninitialized')

    def extract(self, document):
        if self.failure:
            raise self.failure
        return attach_text_provenance(OCRResult(
            document_id=document.document_id, filename=document.filename, source=document.source,
            source_metadata=document.source_metadata, provider=self.name,
            pages=[OCRPage(page_number=1, text='Hello مرحبا', blocks=[
                OCRBlock(block_id='word1', text='Hello'), OCRBlock(block_id='word2', text='مرحبا')])]))
