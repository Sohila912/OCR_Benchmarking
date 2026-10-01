import sys
import types
from pathlib import Path
from unittest.mock import Mock

import pytest
from OCR import pdf
from OCR.errors import InvalidDocumentError, ExtractionError, ProviderInitializationError


@pytest.fixture
def backend(monkeypatch):
    errors=types.SimpleNamespace(**{n:type(n,(Exception,),{}) for n in ['PDFInfoNotInstalledError','PopplerNotInstalledError','PDFPageCountError','PDFSyntaxError','PDFPopplerTimeoutError']})
    backend=types.SimpleNamespace(pdfinfo_from_path=Mock(return_value={'Pages':2}),convert_from_path=Mock())
    monkeypatch.setattr(Path,'is_file',lambda self:True)
    monkeypatch.setattr(pdf,'_load_backend',lambda:(backend,errors))
    return backend,errors


def test_forwarding_and_returned_image_ownership(backend):
    engine,_=backend
    assert pdf.get_pdf_page_count(Path('x.pdf'),poppler_path=Path('tools'),timeout=12)==2
    engine.pdfinfo_from_path.assert_called_once_with('x.pdf',poppler_path='tools',timeout=12)
    image=Mock()
    engine.convert_from_path.return_value=[image]
    assert pdf.render_pdf_page(Path('x.pdf'),2,dpi=150,timeout=13) is image
    engine.convert_from_path.assert_called_once_with('x.pdf',first_page=2,last_page=2,dpi=150,poppler_path=None,timeout=13,grayscale=False,thread_count=1)
    image.close.assert_not_called()


@pytest.mark.parametrize('value',[0,-1,True,1.5,'2',None])
def test_invalid_arguments(backend,value):
    with pytest.raises(ValueError):
        pdf.get_pdf_page_count(Path('x.pdf'),timeout=value)
    for name in ['page_number','dpi','timeout']:
        args=dict(page_number=1,dpi=300,timeout=60)
        args[name]=value
        with pytest.raises(ValueError):
            pdf.render_pdf_page(Path('x.pdf'),**args)


@pytest.mark.parametrize('value',[0,-1,True,'2',None])
def test_invalid_page_counts(backend,value):
    engine,_=backend
    engine.pdfinfo_from_path.return_value={'Pages':value}
    with pytest.raises(InvalidDocumentError):
        pdf.get_pdf_page_count(Path('x.pdf'))


@pytest.mark.parametrize('name,expected',[('PDFInfoNotInstalledError',ProviderInitializationError),('PopplerNotInstalledError',ProviderInitializationError),('PDFPageCountError',InvalidDocumentError),('PDFSyntaxError',InvalidDocumentError),('PDFPopplerTimeoutError',ExtractionError)])
def test_error_translation(backend,name,expected):
    engine,errors=backend
    for method,call in [(engine.pdfinfo_from_path,lambda:pdf.get_pdf_page_count(Path('x.pdf'))),(engine.convert_from_path,lambda:pdf.render_pdf_page(Path('x.pdf'),1))]:
        method.side_effect=getattr(errors,name)('mock')
        with pytest.raises(expected):
            call()


def test_unexpected_images_are_closed(backend):
    engine,_=backend
    images=[Mock(),Mock()]
    engine.convert_from_path.return_value=images
    with pytest.raises(ExtractionError):
        pdf.render_pdf_page(Path('x.pdf'),1)
    for image in images:
        image.close.assert_called_once_with()


def test_missing_renderer_is_explicit(backend,monkeypatch):
    monkeypatch.setattr(pdf.shutil,'which',lambda *a,**kw:None)
    with pytest.raises(ProviderInitializationError):
        pdf.require_pdf_renderer()
