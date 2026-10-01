"""FastAPI entry point: multipart PDFs in, normalized OCR documents out."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from OCR.config import Settings, load_settings
from OCR.errors import (OCRError, ExtractionError, InvalidDocumentError, UploadTooLargeError,
                        UnsupportedProviderError, ProviderInitializationError, ProviderNotReadyError)
from OCR.schemas import OCRIssue, OCRResult
from OCR.service import OCRService, ingest_pdf

logger = logging.getLogger(__name__)


class CompareEntry(BaseModel):
    provider: str
    result: OCRResult | None = None
    errors: list[OCRIssue] = Field(default_factory=list)


class CompareResponse(BaseModel):
    document_id: str
    filename: str
    results: list[CompareEntry]


def error_status(exc: OCRError) -> int:
    if isinstance(exc, UploadTooLargeError):
        return 413
    if isinstance(exc, (InvalidDocumentError, UnsupportedProviderError)):
        return 400
    if isinstance(exc, (ProviderInitializationError, ProviderNotReadyError)):
        return 503
    return 500


def public_error(exc: OCRError) -> str:
    if error_status(exc) in (400, 413):
        return str(exc)
    return "OCR provider is unavailable or extraction failed. Check server logs and provider configuration."


class RequestSizeLimit:
    """Limit the whole multipart body before unbounded spooling can occur."""
    def __init__(self, app, max_bytes: int):
        self.app, self.max_bytes = app, max_bytes

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        size = 0
        headers = dict(scope.get('headers', []))
        length = headers.get(b'content-length')
        try:
            too_large = length is not None and int(length) > self.max_bytes
        except ValueError:
            too_large = False
        detail = {'code': 'upload_too_large', 'message': 'Request body exceeds the configured upload limit.'}
        if too_large:
            return await JSONResponse(status_code=413, content={'detail': detail})(scope, receive, send)

        async def bounded_receive():
            nonlocal size
            message = await receive()
            if message['type'] == 'http.request':
                size += len(message.get('body', b''))
                if size > self.max_bytes:
                    raise HTTPException(status_code=413, detail=detail)
            return message

        await self.app(scope, bounded_receive, send)


def create_app(settings: Settings | None = None, service: OCRService | None = None) -> FastAPI:
    settings = settings if settings is not None else load_settings()
    service = service if service is not None else OCRService(settings)

    @asynccontextmanager
    async def lifespan(application):
        # No models are initialized or downloaded on startup.
        settings.temp_dir.mkdir(parents=True, exist_ok=True)
        yield

    application = FastAPI(title='OCR Benchmarking / OCR Service', version='2.0.0', lifespan=lifespan)
    application.state.ocr_service = service
    application.add_middleware(RequestSizeLimit, max_bytes=settings.max_upload_bytes + 1024 * 1024)

    @application.exception_handler(OCRError)
    async def ocr_error_handler(request: Request, exc: OCRError):
        logger.warning('OCR request failed: %s', exc, exc_info=True)
        return JSONResponse(status_code=error_status(exc), content={'detail': {
            'code': exc.code, 'message': public_error(exc), 'provider': exc.provider}})

    @application.get('/')
    def root():
        return {'message': 'OCR Benchmarking / OCR Service', 'docs': '/docs', 'schema_version': '1.0'}

    @application.get('/health')
    def health():
        return {'status': 'ok', 'providers': [item.model_dump() for item in service.health()]}

    @application.get('/tools')
    def tools():
        return {'tools': list(service.providers), 'default': settings.provider}

    async def save(file: UploadFile):
        try:
            return await run_in_threadpool(ingest_pdf, file.file, file.filename, settings)
        except OSError as exc:
            raise ExtractionError('Could not store the upload.') from exc
        finally:
            await file.close()

    @application.post('/extract', response_model=OCRResult)
    async def extract(file: UploadFile = File(...), engine: str | None = Form(None)):
        service.select(engine)
        document = await save(file)
        return await run_in_threadpool(service.extract, document, engine)

    @application.post('/extract/compare', response_model=CompareResponse)
    async def compare(file: UploadFile = File(...)):
        document = await save(file)
        results = []
        for provider in service.providers:
            try:
                result = await run_in_threadpool(service.extract, document, provider)
                results.append(CompareEntry(provider=provider, result=result))
            except OCRError as exc:
                logger.warning('OCR comparison failed for %s: %s', provider, exc, exc_info=True)
                results.append(CompareEntry(provider=provider, errors=[OCRIssue(code=exc.code, message=public_error(exc))]))
        return CompareResponse(document_id=document.document_id, filename=document.filename, results=results)

    return application


app = create_app()
