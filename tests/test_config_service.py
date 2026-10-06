import io
import os
import pytest
from pathlib import Path
from pydantic import ValidationError
from OCR.config import Settings, load_settings, REPOSITORY_ROOT
from OCR.errors import InvalidDocumentError, UploadTooLargeError, UnsupportedProviderError, ExtractionError
from OCR.service import ingest_pdf, validate_upload_name, OCRService
from OCR.providers.base import OCRDocument
from conftest import FakeProvider


def test_env_file_and_environment_precedence(tmp_path, monkeypatch):
    dotenv = tmp_path/'.env'
    dotenv.write_text('OCR_PROVIDER=docling\nOCR_PDF_DPI=150\nOCR_TESSERACT_LANG=ara+eng\n',encoding='utf-8')
    monkeypatch.setenv('OCR_PDF_DPI','200')
    settings = load_settings(dotenv)
    assert settings.provider == 'docling' and settings.pdf_dpi == 200
    assert settings.tesseract_lang == 'ara+eng'
    assert load_settings(None).provider == 'tesseract'


def test_relative_paths_are_repo_relative(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    assert Settings(upload_dir='runtime/uploads').upload_dir == REPOSITORY_ROOT/'runtime/uploads'


def test_poppler_install_root_resolves_to_binary_directory(tmp_path):
    install_root = tmp_path/'poppler'
    binary_directory = install_root/'Library'/'bin'
    binary_directory.mkdir(parents=True)
    suffix = '.exe' if os.name == 'nt' else ''
    for executable in ('pdfinfo', 'pdftoppm'):
        (binary_directory/f'{executable}{suffix}').touch()
    assert Settings(poppler_path=install_root).poppler_path == binary_directory


@pytest.mark.parametrize('values',[{'provider':'marker'}, {'api_port':70000}, {'pdf_dpi':0}, {'temp_dir':''}, {'operation_timeout':0}])
def test_invalid_settings(values):
    with pytest.raises(ValidationError):
        Settings(**values)


@pytest.mark.parametrize('name', ['../x.pdf', r'..\x.pdf', '/x.pdf', 'C:\\x.pdf', 'x.pdf:stream', 'x.txt', '', None])
def test_unsafe_names(name):
    with pytest.raises(InvalidDocumentError):
        validate_upload_name(name)


def test_same_name_never_overwrites(settings):
    one = ingest_pdf(io.BytesIO(b'%PDF-one'), 'x.pdf', settings)
    two = ingest_pdf(io.BytesIO(b'%PDF-two'), 'x.pdf', settings)
    assert one.path != two.path and one.document_id != two.document_id
    assert one.path.read_bytes() == b'%PDF-one'
    assert list(settings.temp_dir.iterdir()) == []


def test_oversized_stream_is_bounded_and_not_persisted(settings):
    settings = settings.model_copy(update={'max_upload_bytes':5})
    with pytest.raises(UploadTooLargeError):
        ingest_pdf(io.BytesIO(b'%PDF-1.4'), 'x.pdf', settings)
    assert not list(settings.upload_dir.iterdir())
    assert not list(settings.temp_dir.iterdir())


def test_registry_is_exact_and_lazy(settings):
    service = OCRService(settings)
    assert set(service.providers) == {'paddle_vl','docling','tesseract'}
    assert all(p.status == 'uninitialized' for p in service.health())
    with pytest.raises(UnsupportedProviderError):
        service.select('paddle')


def test_result_identity_violation_is_rejected(settings):
    class WrongProvider(FakeProvider):
        def extract(self, document):
            result = super().extract(document)
            result.document_id = 'wrong'
            return result
    service = OCRService(settings, {'tesseract':WrongProvider()})
    with pytest.raises(ExtractionError):
        service.extract(OCRDocument(document_id='doc',filename='x.pdf',path=Path('x.pdf')))


def test_new_settings_are_all_environment_backed(tmp_path, monkeypatch):
    monkeypatch.setenv('OCR_TEMP_DIR','runtime/test-tmp')
    monkeypatch.setenv('OCR_API_PORT','8011')
    monkeypatch.setenv('OCR_PADDLE_VL_MODEL_DIR','models/vl')
    current = load_settings(None)
    assert current.api_port == 8011
    assert current.temp_dir == REPOSITORY_ROOT/'runtime/test-tmp'
    assert current.paddle_vl_model_dir == REPOSITORY_ROOT/'models/vl'


def test_switching_provider_releases_previous_model_before_loading(settings):
    resident = set()

    class MemoryProvider(FakeProvider):
        def initialize(self):
            assert not (resident - {self.name})
            resident.add(self.name)
            super().initialize()

        def unload(self):
            resident.discard(self.name)
            self.ready = False

    first, second = MemoryProvider('tesseract'), MemoryProvider('docling')
    service = OCRService(settings, {'tesseract': first, 'docling': second})
    document = OCRDocument(document_id='doc', filename='x.pdf', path=Path('x.pdf'))
    for name in ('tesseract', 'docling', 'tesseract'):
        service.extract(document, name)
        assert resident == {name}
    assert first.initializations == 2
