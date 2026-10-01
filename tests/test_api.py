import io
import pytest
from fastapi.testclient import TestClient
from OCR.app import create_app
from OCR.errors import ExtractionError, ProviderInitializationError
from OCR.service import OCRService
from conftest import FakeProvider


def client_for(settings, providers=None):
    return TestClient(create_app(settings, OCRService(settings, providers or {'tesseract': FakeProvider()})))


def upload(client, **kwargs):
    return client.post('/extract', files={'file': ('sample.pdf', b'%PDF-1.4\nmock', 'application/pdf')}, **kwargs)


def test_extract_multipart_normalized_and_persisted(settings):
    with client_for(settings) as client:
        response = upload(client)
    assert response.status_code == 200
    body = response.json()
    assert body['schema_version'] == '1.0'
    assert body['text'] == 'Hello مرحبا'
    assert body['pages'][0]['blocks'][1]['text_start'] == 6
    assert body['source'].startswith('upload:')
    assert body['source_metadata']['sha256'] == body['document_id']
    assert len(list(settings.upload_dir.glob('*.pdf'))) == 1
    assert len(list(settings.output_dir.glob('*.json'))) == 1


def test_health_does_not_initialize(settings):
    fake = FakeProvider()
    with client_for(settings, {'tesseract': fake}) as client:
        body = client.get('/health').json()
        assert body['providers'][0]['status'] == 'uninitialized'
        assert client.get('/tools').json()['tools'] == ['tesseract']
    assert fake.initializations == 0


def test_unknown_provider_precedes_upload(settings):
    with client_for(settings) as client:
        response = upload(client, data={'engine': 'marker'})
    assert response.status_code == 400
    assert response.json()['detail']['code'] == 'unsupported_provider'
    assert not settings.upload_dir.exists()


@pytest.mark.parametrize('name,data', [('bad.txt', b'%PDF-1.4'), ('../bad.pdf', b'%PDF-1.4'), ('bad.pdf', b'not a pdf'), ('bad.pdf', b'')])
def test_invalid_upload(settings, name, data):
    with client_for(settings) as client:
        response = client.post('/extract', files={'file': (name, data)})
    assert response.status_code == 400
    assert not list(settings.upload_dir.glob('*.pdf'))


def test_file_size_limit(settings):
    settings = settings.model_copy(update={'max_upload_bytes': 8})
    with client_for(settings) as client:
        response = upload(client)
    assert response.status_code == 413
    assert not list(settings.upload_dir.glob('*.pdf'))


def test_whole_request_size_limit(settings):
    settings = settings.model_copy(update={'max_upload_bytes': 8})
    with client_for(settings) as client:
        response = client.post('/extract', content=b'x'*(1024*1024+9))
    assert response.status_code == 413


def test_old_json_contract_is_rejected(settings):
    with client_for(settings) as client:
        response = client.post('/extract', json={'pdf_path': 'sample.pdf', 'engine': 'tesseract'})
    assert response.status_code == 422


@pytest.mark.parametrize('error,status', [(ProviderInitializationError('secret path'),503), (ExtractionError('secret path'),500), (RuntimeError('secret path'),500)])
def test_structured_provider_failure(settings, error, status):
    with client_for(settings, {'tesseract': FakeProvider(failure=error)}) as client:
        response = upload(client)
    assert response.status_code == status
    assert 'secret path' not in response.text
    assert 'code' in response.json()['detail']


def test_compare_keeps_failures_out_of_text(settings):
    providers = {'tesseract': FakeProvider(), 'paddle_vl': FakeProvider('paddle_vl', ExtractionError('no model')),
                 'docling': FakeProvider('docling')}
    with client_for(settings, providers) as client:
        response = client.post('/extract/compare', files={'file': ('x.pdf', b'%PDF-1.4')})
    assert response.status_code == 200
    items = response.json()['results']
    assert items[1]['result'] is None and items[1]['errors'][0]['code'] == 'extraction_failed'
    assert items[0]['result']['document_id'] == items[2]['result']['document_id']
    assert len(list(settings.upload_dir.glob('*.pdf'))) == 1


def test_streaming_request_limit_without_content_length(settings):
    from OCR.app import RequestSizeLimit
    import asyncio
    from fastapi import HTTPException
    async def scenario():
        async def receive():
            return {'type': 'http.request', 'body': b'123456', 'more_body': False}
        async def inner(scope, recv, send):
            await recv()
        async def send(message):
            pass
        with pytest.raises(HTTPException) as caught:
            await RequestSizeLimit(inner, 5)({'type':'http', 'headers':[]}, receive, send)
        assert caught.value.status_code == 413
    asyncio.run(scenario())
