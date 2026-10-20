"""Keep the UI responsive while a blocking API request runs."""
from concurrent.futures import ThreadPoolExecutor
import time
import streamlit as st


def run_with_progress(operation, label="Waiting for the OCR service"):
    started = time.monotonic()
    placeholder = st.empty()
    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(operation)
            while not future.done():
                elapsed = int(time.monotonic() - started)
                placeholder.info(f"{label} · {elapsed // 60:02d}:{elapsed % 60:02d} elapsed. Results appear when the provider finishes.")
                time.sleep(0.25)
            return future.result()
    finally:
        placeholder.empty()
