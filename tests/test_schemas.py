import pytest
from pydantic import ValidationError
from OCR.schemas import BoundingBox, OCRBlock, OCRIssue, OCRPage, OCRResult, attach_text_provenance


def result(pages, **kwargs):
    return OCRResult(document_id='doc', filename='source.pdf', provider='tesseract', pages=pages, **kwargs)


def test_unicode_provenance_roundtrip_and_null_capabilities():
    document = attach_text_provenance(result([
        OCRPage(page_number=1, text='مرحبا hello', blocks=[OCRBlock(block_id='a',text='مرحبا'), OCRBlock(block_id='b',text='hello')]),
        OCRPage(page_number=2, text='next', blocks=None)]))
    restored = OCRResult.model_validate_json(document.model_dump_json())
    page = restored.pages[0]
    block = page.blocks[1]
    assert restored.text[page.text_start:page.text_end][block.text_start:block.text_end] == 'hello'
    assert restored.pages[1].text_start == len(page.text)+2
    assert restored.pages[1].blocks is None
    assert block.confidence is block.language is block.bounding_box is None
    assert restored.schema_version == '1.0'


@pytest.mark.parametrize('numbers', [[1,1],[2,1]])
def test_duplicate_or_unordered_pages_rejected(numbers):
    with pytest.raises(ValidationError):
        result([OCRPage(page_number=n) for n in numbers])


def test_duplicate_block_ids_rejected():
    with pytest.raises(ValidationError):
        result([OCRPage(page_number=1, blocks=[OCRBlock(block_id='a'),OCRBlock(block_id='a')])])


def test_invalid_text_span_rejected():
    with pytest.raises(ValidationError):
        result([OCRPage(page_number=1,text='different',text_start=0,text_end=2)],text='ok')


def test_issue_page_must_match_container():
    with pytest.raises(ValidationError):
        result([OCRPage(page_number=1,errors=[OCRIssue(code='bad',message='failed',page_number=2)])])


@pytest.mark.parametrize('changes', [{'x_min':2}, {'x_min':float('nan')}, {'x_max':2,'units':'normalized'}])
def test_invalid_geometry(changes):
    data=dict(x_min=0,y_min=0,x_max=1,y_max=1,units='pixels',origin='top_left')
    with pytest.raises(ValidationError):
        BoundingBox(**(data|changes))


def test_unavailable_text_is_not_fabricated():
    document = attach_text_provenance(result([OCRPage(page_number=1,blocks=None)]))
    assert document.text is None and document.pages[0].text_start is None


def test_unknown_schema_version_rejected():
    with pytest.raises(ValidationError):
        result([],schema_version='2.0')
