"""Native Streamlit dashboard, comparison, evaluation and settings views."""
from __future__ import annotations

import streamlit as st
from frontend.design import hero

REQUIREMENTS = {
    "tesseract": "Tesseract 5, language packs, Poppler. CPU reference engine.",
    "docling": "Docling packages, local layout/table assets, Tesseract language packs.",
    "paddle_vl": "PaddleOCR-VL, native Paddle runtime, local VL/layout assets, Poppler.",
    "qwen_ollama": "Ollama client/server, configured Qwen model tag, Poppler.",
}


def navigate(page):
    st.session_state["workspace_navigation"] = page


def overview(providers, health):
    st.title("Document intelligence workspace")
    hero()
    entries = st.session_state.get("ocr_entries", [])
    rows = (st.session_state.get("gt_result") or st.session_state.get("dataset_result") or {}).get("results", [])
    columns = st.columns(3)
    columns[0].metric("Registered engines", len(providers))
    columns[1].metric("Successful session results", sum(bool(e.get("result")) for e in entries))
    columns[2].metric("Evaluated document outputs", sum(r.get("status") == "success" for r in rows))
    left, right = st.columns(2)
    with left, st.container(border=True):
        st.subheader("Document processing")
        st.write("Upload a scanned or digital PDF. Choose an engine, inspect page text and structure, then export JSON, text or Markdown.")
        st.caption("Supported input: PDF. Engines initialize on first use.")
        st.button("Process a document", type="primary", on_click=navigate, args=("Document Processing",))
    with right, st.container(border=True):
        st.subheader("Benchmarking")
        st.write("Evaluate saved OCR runs or process a labeled dataset sample. Compare historical WER and CER with explicit coverage and failures.")
        st.caption("Upload UTF-8 Markdown ground truth or reuse English, Arabic and mixed-language datasets.")
        st.button("Open benchmarking", on_click=navigate, args=("Benchmarking",))
    st.subheader("Recent session activity")
    if entries:
        st.dataframe([{"Document": st.session_state.get("ocr_run_filename", "Document"),
                       "Engine": e["provider"], "Status": "Needs review" if e.get("error") or (e.get("result") or {}).get("errors") else "Complete",
                       "Request seconds": round(e["elapsed"], 2) if "elapsed" in e else None} for e in entries], hide_index=True)
    else:
        st.info("No documents processed in this session. Start with a PDF or evaluate an existing benchmark run.")
    if health:
        st.caption("Provider lifecycle: " + " · ".join(f"{h['provider']}: {h['status']}" for h in health))
    if rows:
        st.caption("Latest ground-truth evaluation")
        st.dataframe([{"Provider": r["provider"], "Status": r["status"], "CER": (r.get("metrics") or {}).get("cer"), "WER": (r.get("metrics") or {}).get("wer")} for r in rows], hide_index=True)


def comparison(render_entry):
    st.title("Results & comparison")
    entries = st.session_state.get("ocr_entries", [])
    if not entries:
        st.info("Run document processing to compare outputs here.")
        return
    st.caption(f"Document: {st.session_state.get('ocr_run_filename', 'Document')}")
    successful = [entry for entry in entries if entry.get("result")]
    benchmark = any(e.get("timing_source") == "benchmark" for e in entries)
    st.dataframe([{"Engine": e["provider"], "OCR seconds" if benchmark else "Request seconds": round(e["elapsed"], 2) if e.get("elapsed") is not None else None,
                   "Characters": len((e.get("result") or {}).get("text") or ""),
                   "Pages": len((e.get("result") or {}).get("pages") or []),
                   "Status": "Failed" if e.get("error") else "Partial" if e["result"].get("errors") else "Complete"}
                  for e in entries], hide_index=True)
    st.caption("OCR duration excludes HTTP and queueing; includes initialization and inference. Text length is not accuracy." if benchmark else "Duration includes transport, queueing and model loading. Text length is not accuracy.")
    if len(successful) >= 2:
        chosen = st.multiselect("Engines for side-by-side review", [e["provider"] for e in successful],
                                default=[e["provider"] for e in successful[:2]], max_selections=2)
        page_numbers = sorted({page["page_number"] for e in successful for page in e["result"].get("pages") or []})
        page = st.selectbox("Text scope", ["Full document", *page_numbers],
                            format_func=lambda p: f"Page {p}" if isinstance(p, int) else p)
        if chosen:
            for column, provider in zip(st.columns(len(chosen)), chosen):
                result = next(e["result"] for e in successful if e["provider"] == provider)
                text = result.get("text")
                if isinstance(page, int):
                    text = next((p.get("text") for p in result.get("pages") or [] if p["page_number"] == page), None)
                with column, st.container(border=True):
                    st.subheader(provider)
                    st.text(text if text is not None else "No text available for this scope.")
    tabs = st.tabs([e["provider"] for e in entries])
    for tab, entry in zip(tabs, entries):
        with tab:
            render_entry(entry)


def provider_settings(settings, providers, health):
    st.title("Settings & provider status")
    st.caption("Read-only runtime configuration. Credentials and machine-specific paths are not displayed.")
    import requests
    diagnostics = {}
    try:
        response = requests.get(settings.api_url + "/providers/diagnostics", timeout=(3, 30))
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, list):
            diagnostics = {item["provider"]: item for item in payload if isinstance(item, dict) and "provider" in item}
        with st.expander("Runtime diagnostic details"):
            display = []
            for item in diagnostics.values():
                lifecycle = item.get("lifecycle", "Unknown")
                if lifecycle == "uninitialized" and item.get("inference_verified"):
                    lifecycle = "Unloaded after successful test"
                elif lifecycle == "uninitialized":
                    lifecycle = "Not loaded"
                display.append({"Provider": item["provider"], "Verification": item.get("state"),
                                "Model memory": lifecycle, "Details": item.get("detail")})
            st.dataframe(display, hide_index=True)
    except (requests.RequestException, ValueError):
        st.warning("Provider diagnostics unavailable.")
    st.caption("Ready requires successful actual inference in the current API process. Upload a small PDF in Document Processing to smoke-test a provider; refresh this page afterward.")
    states = {item["provider"]: item["status"] for item in health}
    for provider in providers:
        with st.container(border=True):
            st.subheader(provider)
            st.write(REQUIREMENTS.get(provider, "Registered service integration."))
            diagnostic = diagnostics.get(provider, {})
            state = diagnostic.get("state", "Not tested")
            message = diagnostic.get("message") or diagnostic.get("detail") or "Run extraction to verify this engine."
            if state == "Ready":
                st.success(state)
            elif "failed" in state.lower():
                st.error(state)
            elif state != "Not tested":
                st.warning(state)
            else:
                st.info(state)
            st.caption(message)
            lifecycle = diagnostic.get("lifecycle", states.get(provider, "Unknown"))
            if lifecycle == "uninitialized" and diagnostic.get("inference_verified"):
                st.caption("Model memory: unloaded after successful test. It will reload automatically on the next extraction.")
            elif lifecycle == "uninitialized":
                st.caption("Model memory: not loaded yet.")
            else:
                st.caption(f"Model memory: {lifecycle}")
            if states.get(provider) in ("unavailable", "error"):
                st.warning("This engine is unavailable. Review its installed packages, model assets and native runtime before retrying.")
    st.info("Verification records successful inference in this API process. Model memory is separate: switching engines can unload a tested model to free RAM; it reloads on the next request.")
    st.subheader("Processing policy")
    st.dataframe([
        {"Setting": "Default engine", "Value": settings.provider},
        {"Setting": "PDF raster DPI", "Value": str(settings.pdf_dpi)},
        {"Setting": "Recognition language packs", "Value": settings.tesseract_lang},
        {"Setting": "Upload limit (MiB)", "Value": f"{settings.max_upload_bytes / 1024**2:g}"},
        {"Setting": "Page limit", "Value": str(settings.max_pages)},
        {"Setting": "Retention policy", "Value": "Retain uploads" if settings.retain_uploads else "Remove request uploads after processing"},
    ], hide_index=True)
    st.caption("These are frontend-local settings. The API environment governs extraction; keep both service configurations aligned.")
    st.caption("Model paths and runtime checks above come from the API, where extraction runs.")
