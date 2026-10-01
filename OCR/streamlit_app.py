"""Streamlit client for the normalized multipart API."""
import json
import sys
from pathlib import Path

import requests
import streamlit as st

# Streamlit executes this filename as a script; anchor package imports to the repo.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from OCR.config import load_settings

settings = load_settings()
st.set_page_config(page_title='OCR Service', layout='wide')
st.title('OCR Benchmarking / OCR Service')
st.caption('Extract a PDF with a local provider and download its text and provenance.')

try:
    response = requests.get(f'{settings.api_url}/tools', timeout=5)
    response.raise_for_status()
    tools = response.json()
except requests.RequestException as exc:
    st.error(f'API unavailable at {settings.api_url}: {exc}')
    st.stop()

providers = tools['tools']
selected = st.selectbox('OCR provider', providers, index=providers.index(tools['default']))
upload = st.file_uploader('PDF document', type=['pdf'])
compare = st.checkbox('Compare all three providers')

if st.button('Extract', disabled=upload is None):
    with st.spinner('Running OCR...'):
        try:
            endpoint = '/extract/compare' if compare else '/extract'
            response = requests.post(settings.api_url + endpoint,
                                     files={'file': (upload.name, upload.getvalue(), 'application/pdf')},
                                     data={} if compare else {'engine': selected}, timeout=3600)
            response.raise_for_status()
            payload = response.json()
            entries = payload['results'] if compare else [{'provider': payload['provider'], 'result': payload}]
            for entry in entries:
                st.subheader(entry['provider'])
                for issue in entry.get('errors', []):
                    st.error(issue['message'])
                result = entry.get('result')
                if result is None:
                    continue
                for issue in result['warnings']:
                    st.warning(issue['message'])
                for issue in result['errors']:
                    st.error(issue['message'])
                st.text_area('Extracted text', result['text'] or '', height=300, key=entry['provider']+'text')
                st.download_button('Download normalized JSON', json.dumps(result, ensure_ascii=False, indent=2),
                                   file_name=f"{entry['provider']}.json", mime='application/json', key=entry['provider']+'json')
                if result['markdown'] is not None:
                    st.download_button('Download Markdown', result['markdown'], file_name=f"{entry['provider']}.md",
                                       key=entry['provider']+'md')
        except requests.RequestException as exc:
            st.error(f'Extraction request failed: {exc}')
            if exc.response is not None:
                st.code(exc.response.text)
