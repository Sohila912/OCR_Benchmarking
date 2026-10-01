import ast
import hashlib
import importlib
import json
import sys
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('language',['english','arabic','mix'])
def test_historical_normalization_unchanged(language):
    baseline=json.loads((ROOT/'docs/OCR_BENCHMARK_NORMALIZATION_BASELINE.json').read_text(encoding='utf-8'))
    module=ast.parse((ROOT/f'benchmarks/evaluation/evaluate_{language}.py').read_text(encoding='utf-8-sig'))
    function=next(n for n in module.body if isinstance(n,ast.FunctionDef) and n.name=='normalize_text')
    assert hashlib.sha256(ast.dump(function,include_attributes=False).encode()).hexdigest()==baseline[language]


@pytest.mark.parametrize('language',['english','arabic','mix'])
def test_evaluation_writes_only_new_fixture_results(language,tmp_path,monkeypatch):
    module=importlib.import_module('benchmarks.evaluation.evaluate_'+language)
    ref=tmp_path/'ref';out=tmp_path/'out';ref.mkdir();out.mkdir()
    for folder in (ref,out):
        (folder/'sample.md').write_text('Hello world مرحبا',encoding='utf-8')
    result=tmp_path/'metrics.xlsx'
    monkeypatch.setattr(sys,'argv',['evaluate','--reference',str(ref),'--ocr-output',str(out),'--result',str(result)])
    module.main()
    import pandas as pd
    metrics=pd.read_excel(result)
    assert metrics.iloc[0]['CER']==0 and metrics.iloc[0]['WER']==0
    before=result.read_bytes()
    with pytest.raises(SystemExit):
        module.main()
    assert result.read_bytes()==before
