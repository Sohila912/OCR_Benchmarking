"""Streamlit workspace for normalized OCR extraction and provider comparison."""
from __future__ import annotations

import hashlib
import io
import json
import tempfile
import sys
import time
from pathlib import Path

import requests
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from OCR.config import load_settings
from frontend.client import extract_document, request_error
from frontend.views import overview, comparison, provider_settings
from frontend.ground_truth import benchmarking
from frontend.design import apply_theme, workflow, PROVIDER_NAMES


LABELS = {
    "tesseract": "Tesseract · fast reference",
    "docling": "Docling · document structure",
    "qwen_ollama": "Qwen · vision language model",
    "paddle_vl": "PaddleOCR-VL · multilingual layout",
}


def render_entry(entry: dict) -> None:
    provider = entry["provider"]
    st.subheader(LABELS.get(provider, provider))
    if entry.get("error"):
        st.error(entry["error"])
        return
    result = entry["result"]
    pages = result.get("pages")
    metrics = st.columns(3)
    metrics[0].metric("Pages returned", len(pages) if pages is not None else "Unknown")
    metrics[1].metric("Text characters", len(result.get("text") or ""))
    metrics[2].metric("Request duration", f"{entry['elapsed']:.1f}s")
    for issue in result.get("warnings", []):
        st.warning(issue["message"])
    for issue in result.get("errors", []):
        st.error(issue["message"])
    text_tab, markdown_tab, pages_tab, provenance_tab = st.tabs(
        ["Text", "Markdown", "Pages", "Provenance"]
    )
    with text_tab:
        st.text_area("Extracted text", result.get("text") or "", height=360,
                     key=f"{provider}_text_{hashlib.sha256((result.get('text') or '').encode()).hexdigest()}", disabled=True)
    with markdown_tab:
        if result.get("markdown") is not None:
            # Source view preserves OCR content and avoids untrusted link rendering.
            st.text_area("Markdown source", result["markdown"], height=360, disabled=True, key=f"{provider}_markdown_source")
        else:
            st.info("This provider did not return Markdown.")
    with pages_tab:
        if pages:
            for page in pages:
                with st.expander(f"Page {page['page_number']}"):
                    st.text(page.get("text") or "No page text returned.")
                    for issue in page.get("warnings", []):
                        st.warning(issue["message"])
                    for issue in page.get("errors", []):
                        st.error(issue["message"])
                    if page.get("blocks"):
                        st.dataframe([{key: block.get(key) for key in ("block_type", "text", "confidence", "reading_order")}
                                      for block in page["blocks"]], hide_index=True)
        else:
            st.info("Page details are unavailable.")
    with provenance_tab:
        st.dataframe([{"Field": key.replace("_", " ").title(), "Value": str(result.get(key) or "Unknown")} for key in (
            "schema_version", "document_id", "filename", "provider", "model_name",
            "model_version"
        )], hide_index=True)
        st.caption("Complete normalized provenance is preserved in the JSON export.")
    downloads = st.columns(3)
    downloads[0].download_button(
        "JSON", json.dumps(result, ensure_ascii=False, indent=2),
        file_name=f"{provider}.json", mime="application/json", key=f"{provider}_json"
    )
    if result.get("text") is not None:
        downloads[1].download_button("Text", result["text"], file_name=f"{provider}.txt",
                                     mime="text/plain", key=f"{provider}_txt")
    if result.get("markdown") is not None:
        downloads[2].download_button("Markdown", result["markdown"], file_name=f"{provider}.md",
                                     mime="text/markdown", key=f"{provider}_md")



def render_processing(settings, providers, default):
    st.title("Document processing")
    st.caption("Upload → Choose engines → Review options → Extract → Inspect & export")
    st.subheader("Document & engines")
    upload = st.file_uploader("PDF document", type=["pdf"], help="Upload a scanned or digital PDF.")
    mode = st.radio("Extraction mode", ["Single provider", "Compare providers"], horizontal=True)
    selected = []
    if providers:
        if mode == "Single provider":
            selected = [st.selectbox("OCR provider", providers,
                                    index=providers.index(default) if default in providers else 0,
                                    format_func=lambda p: LABELS.get(p, p))]
        else:
            selected = st.multiselect("Providers to compare", providers, default=providers,
                                      format_func=lambda p: LABELS.get(p, p))
            st.caption("Engines run sequentially to limit model memory. CPU vision models can take several minutes.")
    known_health = {h["provider"]: h["status"] for h in st.session_state.get("service_snapshot", {}).get("health", [])}
    if any(known_health.get(provider) in ("unavailable", "error") for provider in selected):
        st.warning("A selected engine previously reported unavailable. Check its model assets and runtime in Provider Status before retrying.")
    valid_upload = upload is not None and upload.size <= settings.max_upload_bytes
    if valid_upload:
        with st.expander("Document preview"):
            st.caption("Optional first-page preview uses the existing PDF renderer on this machine.")
            if st.button("Preview first page"):
                try:
                    from OCR.pdf import render_pdf_page
                    from OCR.errors import OCRError
                    settings.temp_dir.mkdir(parents=True, exist_ok=True)
                    with tempfile.TemporaryDirectory(dir=settings.temp_dir) as directory:
                        preview_path = Path(directory) / "preview.pdf"
                        preview_path.write_bytes(upload.getvalue())
                        image = render_pdf_page(preview_path, 1, dpi=100, poppler_path=settings.poppler_path, timeout=15)
                        try:
                            image.thumbnail((1400, 1400))
                            buffer = io.BytesIO()
                            image.save(buffer, format="PNG")
                            st.session_state["document_preview"] = {
                                "digest": hashlib.sha256(upload.getvalue()).hexdigest(), "image": buffer.getvalue()}
                        finally:
                            image.close()
                except (OCRError, OSError, ValueError):
                    st.info("Preview is unavailable. Configure local Poppler to enable it; API extraction remains available.")
            preview = st.session_state.get("document_preview")
            if preview and preview["digest"] == hashlib.sha256(upload.getvalue()).hexdigest():
                st.image(preview["image"], caption="Source PDF · first page")
    if upload is not None:
        st.caption(f"{upload.name} · {upload.size / (1024 ** 2):.2f} MiB")
        if not valid_upload:
            st.error("This PDF exceeds the configured API upload limit.")
    with st.expander("Processing options"):
        st.write(f"PDF raster resolution: {settings.pdf_dpi} DPI · page limit: {settings.max_pages}")
        st.write(f"Tesseract language configuration: {settings.tesseract_lang}")
        st.caption("Settings are applied by the API. Change environment configuration and restart to update them.")
        st.caption("No preprocessing or language detection is implied by these settings.")
    signature = None
    repeat_allowed = False
    if valid_upload and selected:
        signature = hashlib.sha256(upload.getvalue() + upload.name.encode() + json.dumps(sorted(selected)).encode()).hexdigest()
        if signature == st.session_state.get("ocr_last_submission"):
            st.info("This document/engine selection was already submitted. Existing results are retained.")
            repeat_allowed = st.checkbox("Submit again intentionally", help="A timeout may leave server inference running. Review status before retrying.")
    duplicate = signature is not None and signature == st.session_state.get("ocr_last_submission") and not repeat_allowed
    workflow(3 if st.session_state.get("ocr_entries") else 1 if valid_upload and selected else 0)
    if st.button("Run extraction", type="primary", disabled=not valid_upload or not selected or duplicate):
        payload = upload.getvalue()
        if not payload.startswith(b"%PDF-"):
            st.error("The uploaded file does not have a PDF header.")
        else:
            st.session_state["ocr_last_submission"] = signature
            st.session_state["ocr_entries"] = []
            st.session_state["ocr_run_filename"] = upload.name
            st.session_state["ocr_run_digest"] = hashlib.sha256(payload).hexdigest()
            # Reference engines first, then every additional discovered provider.
            order = [p for p in ("tesseract", "docling", "qwen_ollama", "paddle_vl") if p in selected]
            order += [p for p in selected if p not in order]
            bar = st.progress(0, text="Preparing extraction")
            for index, provider in enumerate(order):
                with st.status(f"{provider}: extracting", expanded=True) as status:
                    entry = extract_document(settings.api_url, upload.name, payload, provider)
                    result = entry.get("result")
                    status.update(label=f"{provider}: {'needs review' if entry.get('error') or result.get('errors') else 'complete'}",
                                  state="error" if entry.get("error") or result.get("errors") else "complete", expanded=False)
                    if entry.get("error"):
                        st.error(entry["error"])
                    st.session_state["ocr_entries"].append(entry)
                    if entry.get("result"):
                        render_entry(entry)
                bar.progress((index + 1) / len(order), text=f"Finished {index + 1} of {len(order)} engines")
            st.rerun()

    entries = st.session_state["ocr_entries"]
    st.subheader("Inspect & export")
    if not entries:
        st.info("Choose a PDF and run an extraction to inspect results here.")
        return
    st.caption(f"Results for {st.session_state['ocr_run_filename']}. Durations include HTTP, queueing and model initialization; they are not isolated inference benchmarks.")
    if upload is not None and hashlib.sha256(upload.getvalue()).hexdigest() != st.session_state.get("ocr_run_digest"):
        st.warning("These results belong to the previous document. Run extraction to process the current upload.")
    tabs = st.tabs([PROVIDER_NAMES.get(entry["provider"], entry["provider"]) for entry in entries])
    for tab, entry in zip(tabs, entries):
        with tab:
            render_entry(entry)



def main() -> None:
    st.set_page_config(page_title="OCR Benchmarking", page_icon=":material/description:", layout="wide")
    try:
        settings = load_settings()
    except ValueError:
        st.error("Application configuration is invalid. Review the environment template and restart the service.")
        return
    st.session_state.setdefault("ocr_entries", [])
    providers, default, health = [], None, []
    with st.sidebar:
        st.title("Document IQ")
        st.caption("AI DOCUMENT INTELLIGENCE")
        navigation = st.radio("Navigation", ["Overview", "Document Processing", "Benchmarking", "Results & Comparison", "Settings / Provider Status"], key="workspace_navigation")
        refresh = st.button("Refresh service status")
        snapshot = st.session_state.get("service_snapshot")
        if refresh or not snapshot or snapshot["url"] != settings.api_url or time.monotonic() - snapshot["time"] > 10:
            snapshot = {"url": settings.api_url, "time": time.monotonic(), "providers": [], "default": None, "health": [], "error": None}
            try:
                response = requests.get(f"{settings.api_url}/tools", timeout=(3, 5))
                response.raise_for_status()
                tools = response.json()
                inventory = tools["tools"]
                if not isinstance(inventory, list) or not inventory or not all(isinstance(p, str) for p in inventory) or len(set(inventory)) != len(inventory):
                    raise ValueError("Invalid provider inventory")
                snapshot.update(providers=inventory, default=tools.get("default"))
            except requests.RequestException as exc:
                snapshot["error"] = request_error(exc)
            except (ValueError, KeyError, TypeError):
                snapshot["error"] = "The service returned an invalid provider inventory. Verify the API version."
            if snapshot["providers"]:
                try:
                    response = requests.get(f"{settings.api_url}/health", timeout=(3, 5))
                    response.raise_for_status()
                    health = response.json()["providers"]
                    if not isinstance(health, list) or not all(isinstance(h, dict) and isinstance(h.get("provider"), str) and isinstance(h.get("status"), str) for h in health):
                        raise ValueError("Invalid health")
                    snapshot["health"] = health
                except (requests.RequestException, ValueError, KeyError, TypeError):
                    pass
            st.session_state["service_snapshot"] = snapshot
        providers, default, health = snapshot["providers"], snapshot["default"], snapshot["health"]
        if snapshot["error"]:
            st.error(snapshot["error"])
        else:
            st.success("Service connected")
        if st.button("Clear displayed results", disabled=not st.session_state["ocr_entries"]):
            st.session_state["ocr_entries"] = []
            st.session_state.pop("ocr_run_filename", None)
            st.rerun()
        st.caption("PDF input · JSON / text / Markdown exports")
    if navigation == "Overview":
        overview(providers, health)
    elif navigation == "Document Processing":
        render_processing(settings, providers, default)
    elif navigation == "Benchmarking":
        benchmarking(settings, providers)
    elif navigation == "Results & Comparison":
        comparison(render_entry)
    else:
        provider_settings(settings, providers, health)


if __name__ == "__main__":
    main()
