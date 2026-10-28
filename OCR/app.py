"""FastAPI entry point: multipart PDFs in, normalized OCR documents out."""

import logging
import re
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from OCR.config import Settings, load_settings
from OCR.logging_utils import log_event
from OCR.errors import (OCRError, ExtractionError, InvalidDocumentError, UploadTooLargeError,
                        UnsupportedProviderError, ProviderInitializationError, ProviderNotReadyError, public_error_message)
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
    return public_error_message(exc)


class RequestSizeLimit:
    """Limit the whole multipart body before unbounded spooling can occur."""
    def __init__(self, app, max_bytes: int):
        self.app, self.max_bytes = app, max_bytes

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        limit = self.max_bytes + (2 * 1024 * 1024 if scope.get("path") == "/benchmarks/run" else 0)
        size = 0
        headers = dict(scope.get('headers', []))
        length = headers.get(b'content-length')
        try:
            too_large = length is not None and int(length) > limit
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
                if size > limit:
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
        # Single API worker: only request-owned benchmark files from interrupted jobs.
        for path in settings.upload_dir.glob("benchmark-*.pdf"):
            if re.fullmatch(r"benchmark-[0-9a-f]{32}\.pdf", path.name) and not path.is_symlink():
                path.unlink(missing_ok=True)
        yield

    application = FastAPI(title='OCR Benchmarking / OCR Service', version='2.0.0', lifespan=lifespan)
    application.state.ocr_service = service
    application.add_middleware(RequestSizeLimit, max_bytes=settings.max_upload_bytes + 1024 * 1024)

    @application.exception_handler(OCRError)
    async def ocr_error_handler(request: Request, exc: OCRError):
        log_event(logger, 'request_failed', level=logging.WARNING, code=exc.code, provider=exc.provider)
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

    def cleanup_upload(document):
        if not settings.retain_uploads:
            try:
                document.path.unlink(missing_ok=True)
            except OSError:
                log_event(logger, 'upload_cleanup_failed', level=logging.WARNING)

    @application.post('/extract', response_model=OCRResult)
    async def extract(file: UploadFile = File(...), engine: str | None = Form(None),
                      force_reprocess: bool = Form(False)):
        service.select(engine)
        document = await save(file)
        try:
            return await run_in_threadpool(service.extract, document, engine, force_reprocess=force_reprocess)
        finally:
            cleanup_upload(document)

    @application.post('/extract/compare', response_model=CompareResponse)
    async def compare(file: UploadFile = File(...), force_reprocess: bool = Form(False)):
        document = await save(file)
        results = []
        log_event(logger, 'comparison_started', providers=len(service.providers))
        try:
            for provider in service.providers:
                try:
                    result = await run_in_threadpool(service.extract, document, provider, force_reprocess=force_reprocess)
                    results.append(CompareEntry(provider=provider, result=result))
                except OCRError as exc:
                    log_event(logger, 'comparison_provider_failed', level=logging.WARNING,
                              provider=provider, code=exc.code)
                    results.append(CompareEntry(provider=provider, errors=[OCRIssue(code=exc.code, message=public_error(exc))]))
            log_event(logger, 'comparison_completed', providers=len(results))
            return CompareResponse(document_id=document.document_id, filename=document.filename, results=results)
        finally:
            cleanup_upload(document)

    from OCR.benchmark_api import register
    register(application, service, settings)
    return application


app = create_app()
