"""Real Docker smoke: generated public fixture only; no model downloads."""
import io
import os
import json
import time
from PIL import Image, ImageDraw, ImageFont
import requests

base = 'http://api:8000'
image = Image.new('RGB', (800, 220), 'white')
draw = ImageDraw.Draw(image)
font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 40)
reference = 'OCR test 12345'
draw.text((45, 65), reference, fill='black', font=font)
buffer = io.BytesIO()
image.save(buffer, format='PDF', resolution=150)
pdf = buffer.getvalue()
providers = requests.get(base + '/tools', timeout=10).json()['tools']
print('REGISTERED', providers, flush=True)
print('PREFLIGHT', requests.get(base+'/providers/diagnostics',timeout=30).json(), flush=True)
rows = []
for provider in json.loads(os.getenv('OCR_VERIFY_PROVIDERS', '["tesseract", "docling", "paddle_vl", "qwen_ollama"]')):
    print('START', provider, flush=True)
    started = time.monotonic()
    response = requests.post(base+'/benchmarks/run', files={'file':('smoke.pdf',pdf,'application/pdf'),
        'reference':('smoke.md',reference.encode(),'text/markdown')},
        data={'providers':json.dumps([provider]), 'paired':'true', 'dataset':'Docker synthetic smoke'}, timeout=(10,2100))
    response.raise_for_status()
    row=response.json()['results'][0]
    rows.append(row)
    print('RESULT', provider, row['status'], row.get('error'), row.get('metrics'),
          'duration', row.get('duration_seconds'), 'wall', round(time.monotonic()-started,2), flush=True)
first = next(r for r in rows if r['provider']=='tesseract')
assert first['status']=='success'
assert first['metrics']['cer']==0 and first['metrics']['wer']==0
second_response=requests.post(base+'/benchmarks/run', files={'file':('smoke.pdf',pdf,'application/pdf'),
    'reference':('smoke.md',reference.encode(),'text/markdown')},
    data={'providers':'["tesseract"]','paired':'true','dataset':'Docker synthetic smoke'},timeout=120)
second_response.raise_for_status()
second=second_response.json()['results'][0]
history=requests.get(base+'/benchmarks/history',params={'dataset':'Docker synthetic smoke'},timeout=30).json()
assert all('reference' not in r and 'output' not in r for r in history)
assert any(r['id']==first['id'] for r in history)
comparison=requests.post(base+'/benchmarks/compare',json=[first['id'],second['id']],timeout=30)
comparison.raise_for_status()
assert comparison.json()['same_document_and_reference']
assert comparison.json()['summaries'][0]['micro_cer']==0
print('HISTORY AND COMPARISON', comparison.json(), flush=True)
print('FINAL DIAGNOSTICS', requests.get(base+'/providers/diagnostics',timeout=30).json(), flush=True)
print('UI', requests.get('http://127.0.0.1:8501/_stcore/health',timeout=10).text, flush=True)
# Synthetic texts may be retained as explicit verification artifacts, never customer uploads.
from pathlib import Path
Path('/tmp/ground-truth-verification.json').write_text(json.dumps({'results':rows,'comparison':comparison.json()},ensure_ascii=False,indent=2),encoding='utf-8')
print('VERIFIED benchmark, save, retrieve, compare, healthy UI', flush=True)
