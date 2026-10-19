"""Display regressions only: no OCR calls or persistence."""
from html import unescape
from types import SimpleNamespace
from unittest.mock import Mock

import streamlit as st
from streamlit.testing.v1 import AppTest

from frontend.ground_truth import diff_block


def test_diff_html_escapes_source_and_preserves_unicode():
    text = '# مَرْحَبًا\n**Markdown** <script>alert("x")</script> & <img src=x onerror=alert(1)>\n' * 500
    for kind in ("delete", "insert"):
        html = diff_block(text, kind)
        assert '<script>' not in html and '<img' not in html
        assert '&lt;script&gt;' in html
        assert text in unescape(html)
        assert 'dir="auto"' in html and 'unicode-bidi:plaintext' in html
        assert 'overflow:auto' in html and 'pre-wrap' in html
    assert '#fff1f2' in diff_block('missing', 'delete')
    assert '#ecfdf5' in diff_block('inserted', 'insert')


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
''').run()
    assert not app.exception
    assert len(app.get('html')) == 4
    assert 'مَرْحَبًا' in next(t.value for t in app.text_area if t.label=='Reference Markdown (original)')
    assert any('Substitution' in m.value for m in app.markdown)
    next(m for m in app.multiselect if m.label=='Runs to inspect and compare').set_value(['display-test']).run()
    assert not app.exception
    assert any(t.label=='Saved benchmark metadata' and 'display-test' in t.value for t in app.text_area)
