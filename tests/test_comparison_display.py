"""Display regressions only: no OCR calls or persistence."""
from types import SimpleNamespace
from unittest.mock import Mock

import streamlit as st
from streamlit.testing.v1 import AppTest

def test_benchmark_comparison_and_history_use_no_syntax_highlighter(monkeypatch):
    monkeypatch.setattr(st, 'code', Mock(side_effect=AssertionError('Syntax highlighter must not be used')))
    monkeypatch.setattr(st, 'json', Mock(side_effect=AssertionError('History should use plain text')))
    app = AppTest.from_string('''
import streamlit as st
from types import SimpleNamespace
from frontend.ground_truth import benchmarking
text = '# مَرْحَبًا <script>unsafe()</script>\\n' * 1000
row = {'id':'display-test','provider':'fixture','status':'success','reference':text,'output':text + 'added',
       'metrics':{'cer':0.1,'wer':0.2,'exact_match':False,'character_similarity':0.9},
       'diff':{'truncated':True,'changes':[{'operation':'delete','reference':'مفقود <b>','output':''},
               {'operation':'insert','reference':'','output':'مضاف & جديد'},
               {'operation':'replace','reference':'before','output':'after'}]}}
st.session_state['gt_result']={'results':[row]}
st.session_state['gt_history']=[{k:v for k,v in row.items() if k not in ('reference','output','diff')}]
benchmarking(SimpleNamespace(api_url='http://unused.invalid',max_upload_bytes=50000000),['fixture'])
''', default_timeout=15).run()
    assert not app.exception
    assert len(app.get('html')) == 1  # Benchmark chart only; no colored diff blocks.
    assert any(m.label == 'Match percentage' and m.value == '90.00%' for m in app.metric)
    assert not any(m.label == 'Exact match' for m in app.metric)
    assert 'مَرْحَبًا' in next(t.value for t in app.text_area if t.label=='Reference Markdown (original)')
    assert not any('Normalized text changes' in m.value or 'Substitution' in m.value for m in app.markdown)
    next(m for m in app.multiselect if m.label=='Runs to inspect and compare').set_value(['display-test']).run()
    assert not app.exception
    assert any(t.label=='Saved benchmark metadata' and 'display-test' in t.value for t in app.text_area)


def test_chart_contains_visible_bar_values_and_duration_toggle(monkeypatch):
    from frontend.design import benchmark_chart
    charts = []
    monkeypatch.setattr(st, "html", charts.append)
    monkeypatch.setattr(st, "caption", lambda *args: None)
    monkeypatch.setattr(st, "radio", lambda *args, **kwargs: "Error rates")
    rows = [{"provider": "tesseract", "status": "success", "metrics": {"cer": .0206, "wer": .0729}, "duration_seconds": 2.7032},
            {"provider": "docling", "status": "success", "metrics": {"cer": 0, "wer": 1.2}, "duration_seconds": 6.7433},
            {"provider": "<script>bad</script>", "status": "success", "metrics": {"cer": .1, "wer": .2}},
            {"provider": "failed", "status": "error"}]
    benchmark_chart(rows, "test")
    assert all(value in charts[-1] for value in ("2.06%", "7.29%", "0.00%", "120.00%", "width:100.0000%"))
    assert "<script>" not in charts[-1]
    assert "&lt;script&gt;" in charts[-1]
    monkeypatch.setattr(st, "radio", lambda *args, **kwargs: "Processing time")
    benchmark_chart(rows, "test")
    assert "2.70 s" in charts[-1] and "6.74 s" in charts[-1]


def test_verified_unloaded_provider_is_explained(monkeypatch):
    import requests
    monkeypatch.setattr(requests, "get", lambda *a, **k: Mock(
        raise_for_status=lambda: None, json=lambda: [{"provider": "docling", "state": "Ready",
        "inference_verified": True, "lifecycle": "uninitialized", "detail": "Actual extraction succeeded."}]))
    app = AppTest.from_string('''
from types import SimpleNamespace
from frontend.views import provider_settings
provider_settings(SimpleNamespace(api_url="http://unused", provider="docling", pdf_dpi=150,
 tesseract_lang="eng", max_upload_bytes=1000000, max_pages=10, retain_uploads=False),
 ["docling"], [{"provider":"docling", "status":"uninitialized"}])
''').run()
    assert not app.exception
    assert any("unloaded after successful test" in caption.value for caption in app.caption)
    assert app.success[0].value == "Ready"
