import subprocess
import sys
import types
from pathlib import Path
from unittest.mock import Mock

import pytest
from OCR.errors import ExtractionError, InvalidDocumentError, ProviderInitializationError, ProviderNotReadyError
from OCR.providers.base import OCRDocument, OCRProvider
from OCR.providers.tesseract import TesseractProvider, page_from_tsv, probe_tesseract
from OCR.providers.paddle_vl import PaddleVLProvider, page_from_paddle
from OCR.providers.docling import DoclingProvider, normalize_docling
from OCR.schemas import OCRResult

TSV='level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n5\t1\t1\t1\t1\t1\t10\t20\t30\t12\t95\thello\n5\t1\t1\t1\t1\t2\t45\t20\t30\t12\t-1\tمرحبا\n'


@pytest.fixture
def document(tmp_path):
    path=tmp_path/'input.pdf'
    path.write_bytes(b'%PDF-1.4')
    return OCRDocument(document_id='doc',filename='input.pdf',path=path,source='fixture:input.pdf')


@pytest.mark.parametrize('provider_type',[TesseractProvider,DoclingProvider,PaddleVLProvider])
def test_provider_lifecycle_is_lazy_and_explicit(settings,document,provider_type):
    provider=provider_type(settings)
    assert isinstance(provider,OCRProvider)
    assert provider.health().status=='uninitialized'
    with pytest.raises(ProviderNotReadyError):
        provider.extract(document)


@pytest.mark.parametrize('provider_type',[DoclingProvider,PaddleVLProvider])
def test_missing_local_assets_never_import_models(settings,monkeypatch,provider_type):
    before=set(sys.modules)
    provider=provider_type(settings)
    with pytest.raises(ProviderInitializationError):
        provider.initialize()
    assert provider.health().status=='unavailable'
    assert not ({'docling','paddleocr'} & (set(sys.modules)-before))


def test_tesseract_mapping_preserves_scores_boxes_and_hierarchy():
    page=page_from_tsv(TSV,2,100,200)
    assert page.text=='hello مرحبا'
    word=page.blocks[0]
    assert word.confidence==0.95 and word.provider_metadata['confidence_raw']==95
    assert word.bounding_box.x_max==40
    assert word.provider_metadata['line_num']==1
    assert page.blocks[1].confidence is None
    assert word.language is word.reading_order is None


def test_tesseract_initialization_repeat_safe(settings,monkeypatch):
    import OCR.providers.tesseract as module
    monkeypatch.setattr(module,'require_pdf_renderer',lambda *args:None)
    probe=Mock(return_value='tesseract 5.5.0')
    monkeypatch.setattr(module,'probe_tesseract',probe)
    provider=TesseractProvider(settings)
    provider.initialize(); provider.initialize()
    probe.assert_called_once()
    assert provider.health().status=='ready'


def test_tesseract_probe_checks_languages(monkeypatch):
    import OCR.providers.tesseract as module
    def run(args,**kwargs):
        return types.SimpleNamespace(stdout='tesseract 5.5.0' if '--version' in args else 'List of languages:\neng\n',stderr='')
    monkeypatch.setattr(module.subprocess,'run',run)
    assert '5.5' in probe_tesseract('tesseract','eng',10)
    with pytest.raises(RuntimeError,match='ara'):
        probe_tesseract('tesseract','ara+eng',10)


def test_tesseract_partial_failure_closes_images(settings,document,monkeypatch):
    import OCR.providers.tesseract as module
    provider=TesseractProvider(settings)
    provider._version='tesseract 5.5.0'; provider._state('ready')
    monkeypatch.setattr(module,'get_pdf_page_count',lambda *a,**kw:2)
    image=Mock(width=100,height=100)
    monkeypatch.setattr(module,'render_pdf_page',Mock(side_effect=[image,RuntimeError('bad page')]))
    monkeypatch.setattr(module.subprocess,'run',lambda *a,**kw:types.SimpleNamespace(stdout=TSV))
    result=provider.extract(document)
    assert result.pages[1].text is None and result.errors[0].page_number==2
    assert 'bad page' not in result.text
    assert result.pages[0].blocks[1].text_start==6
    assert result.document_id==document.document_id
    image.close.assert_called_once()
    assert list(settings.temp_dir.iterdir())==[]


def test_tesseract_all_pages_fail_fatally(settings,document,monkeypatch):
    import OCR.providers.tesseract as module
    provider=TesseractProvider(settings);provider._state('ready')
    monkeypatch.setattr(module,'get_pdf_page_count',lambda *a,**kw:1)
    monkeypatch.setattr(module,'render_pdf_page',Mock(side_effect=RuntimeError('bad')))
    with pytest.raises(ExtractionError):
        provider.extract(document)


def test_page_limit_before_render(settings,document,monkeypatch):
    import OCR.providers.tesseract as module
    provider=TesseractProvider(settings);provider._state('ready')
    monkeypatch.setattr(module,'get_pdf_page_count',lambda *a,**kw:settings.max_pages+1)
    with pytest.raises(InvalidDocumentError):
        provider.extract(document)


def test_paddle_mapping_no_fabricated_confidence():
    raw=types.SimpleNamespace(json={'res':{'width':100,'height':200,'parsing_res_list':[
        {'block_label':'text','block_content':'مرحبا','block_bbox':[1,2,50,20],'block_id':7,'block_order':1}]}},markdown={'markdown_texts':'مرحبا'})
    page=page_from_paddle(raw,3)
    assert page.page_number==3
    assert page.blocks[0].reading_order==0
    assert page.blocks[0].provider_metadata['block_id']==7
    assert page.blocks[0].confidence is None
    assert page.blocks[0].bounding_box.units=='pixels'


def test_paddle_initialization_explicit_local_models(settings,tmp_path,monkeypatch):
    import OCR.providers.paddle_vl as module
    assets=tmp_path/'assets';assets.mkdir();(assets/'config.json').write_text('{}')
    settings=settings.model_copy(update={'paddle_vl_model_dir':assets,'paddle_layout_model_dir':assets})
    factory=Mock()
    monkeypatch.setitem(sys.modules,'paddleocr',types.SimpleNamespace(PaddleOCRVL=factory))
    monkeypatch.setattr(module,'require_pdf_renderer',lambda *args:None)
    # Undo the process environment changes after this mock-only check.
    for key in ['HF_HUB_OFFLINE','TRANSFORMERS_OFFLINE','PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK']:
        monkeypatch.setenv(key,'test')
    provider=PaddleVLProvider(settings);provider.initialize();provider.initialize()
    factory.assert_called_once()
    kwargs=factory.call_args.kwargs
    assert kwargs['pipeline_version']=='v1.6' and kwargs['vl_rec_backend']=='native'
    assert kwargs['vl_rec_model_dir']==str(assets)
    assert kwargs['use_doc_unwarping'] is False and kwargs['use_queues'] is False


def test_docling_mapping_preserves_page_item_provenance(document):
    item={'self_ref':'#/texts/0','label':'text','text':'helloمرحبا','prov':[
        {'page_no':1,'charspan':[0,5],'bbox':{'l':1,'t':20,'r':40,'b':2,'coord_origin':'BOTTOMLEFT'}},
        {'page_no':2,'charspan':[5,10],'bbox':{'l':1,'t':2,'r':40,'b':20,'coord_origin':'TOPLEFT'}}]}
    doc=types.SimpleNamespace(export_to_dict=lambda:{'pages':{'1':{'size':{'width':100,'height':200}},'2':{'size':{'width':100,'height':200}}}},
                              iterate_items=lambda:[(types.SimpleNamespace(model_dump=lambda **kw:item),0)],
                              export_to_markdown=lambda **kw:'provider markdown')
    result=normalize_docling(document,types.SimpleNamespace(document=doc,errors=[],status='success'),'2.80.0',None)
    assert result.text=='hello\n\nمرحبا'
    assert result.pages[0].blocks[0].bounding_box.origin=='bottom_left'
    assert result.pages[1].blocks[0].provider_metadata['source_ref']=='#/texts/0'
    assert result.pages[0].blocks[0].confidence is None
    assert result.model_version is None
    assert OCRResult.model_validate_json(result.model_dump_json()).pages[1].text_start==7


def test_docling_initialization_uses_tesseract_not_defaults(settings,tmp_path,monkeypatch):
    import OCR.providers.docling as module
    assets=tmp_path/'assets';assets.mkdir();(assets/'config.json').write_text('{}')
    settings=settings.model_copy(update={'docling_artifacts_path':assets,'tesseract_lang':'ara+eng'})
    converter=Mock();factory=Mock(return_value=converter)
    def options(**kwargs):return types.SimpleNamespace(**kwargs)
    modules={
      'docling.datamodel.base_models':{'InputFormat':types.SimpleNamespace(PDF='pdf')},
      'docling.datamodel.accelerator_options':{'AcceleratorOptions':options},
      'docling.datamodel.pipeline_options':{'PdfPipelineOptions':options,'TesseractCliOcrOptions':options},
      'docling.document_converter':{'DocumentConverter':factory,'PdfFormatOption':options}}
    for name,attrs in modules.items():
        fake=types.ModuleType(name);fake.__dict__.update(attrs);monkeypatch.setitem(sys.modules,name,fake)
    for key in ['HF_HUB_OFFLINE','TRANSFORMERS_OFFLINE']:monkeypatch.setenv(key,'test')
    monkeypatch.setattr(module,'probe_tesseract',lambda *a:'tesseract 5.5.0')
    provider=DoclingProvider(settings);provider.initialize();provider.initialize()
    factory.assert_called_once();converter.initialize_pipeline.assert_called_once_with('pdf')
    actual=factory.call_args.kwargs['format_options']['pdf'].pipeline_options
    assert actual.ocr_options.lang==['ara','eng']
    assert actual.artifacts_path==assets and actual.enable_remote_services is False
    assert actual.do_picture_description is False

def test_paddle_extraction_restores_document_page_numbers(settings,document,monkeypatch):
    import OCR.providers.paddle_vl as module
    import numpy as np
    provider=PaddleVLProvider(settings);provider._state('ready')
    raw=types.SimpleNamespace(json={'res':{'width':2,'height':2,'parsing_res_list':[
        {'block_label':'text','block_content':'hello','block_bbox':[0,0,2,2],'block_order':1}]}},markdown={'markdown_texts':'hello'})
    provider._pipeline=Mock()
    provider._pipeline.predict.side_effect=[[raw],RuntimeError('failed')]
    monkeypatch.setattr(module,'get_pdf_page_count',lambda *a,**kw:2)
    class Image:
        def __init__(self):self.closed=False
        def __array__(self,dtype=None,copy=None):return np.zeros((2,2,3),dtype=np.uint8)
        def close(self):self.closed=True
    images=[Image(),Image()]
    monkeypatch.setattr(module,'render_pdf_page',Mock(side_effect=images))
    result=provider.extract(document)
    assert [p.page_number for p in result.pages]==[1,2]
    assert result.pages[0].blocks[0].text_start==0
    assert result.pages[1].text is None and result.errors[0].page_number==2
    assert all(image.closed for image in images)


def test_docling_failure_status_is_fatal(settings,document):
    provider=DoclingProvider(settings);provider._state('ready')
    provider._converter=Mock()
    provider._converter.convert.return_value=types.SimpleNamespace(status='failure')
    with pytest.raises(ExtractionError,match='failure'):
        provider.extract(document)

def test_application_import_does_not_load_ocr_models():
    process=subprocess.run([sys.executable,'-B','-c',
        "import sys; import OCR.service; assert not ({'torch','paddle','paddleocr','docling','pytesseract','transformers'} & set(sys.modules))"],
        capture_output=True,text=True,check=False)
    assert process.returncode==0,process.stderr
