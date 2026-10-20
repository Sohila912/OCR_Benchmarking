"""Ground-truth UI; scoring, datasets and persistence belong to the API."""
import csv
import io
import json
from html import escape
import requests
import streamlit as st
from frontend.design import benchmark_chart
from frontend.progress import run_with_progress


def api(settings, method, path, **kwargs):
    try:
        response = run_with_progress(lambda: requests.request(method, settings.api_url + path, timeout=(5, 7200), **kwargs), "Evaluating document" if method == "POST" else "Contacting benchmark service")
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        st.error("Benchmark request failed. Review provider diagnostics and input validation. A timeout may leave processing active; check history before retrying.")
        return None


def exports(rows, prefix):
    st.download_button("Metrics JSON", json.dumps(rows, ensure_ascii=False, indent=2), prefix + ".json", "application/json", key=prefix+"json")
    flattened = []
    for row in rows:
        flat = {k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v for k, v in row.items() if k not in ("reference", "output", "diff")}
        flat.update({k: (row.get("metrics") or {}).get(k) for k in ("cer", "wer", "exact_match")})
        flattened.append(flat)
    if flattened:
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=sorted({k for r in flattened for k in r}))
        writer.writeheader()
        for row in flattened:
            writer.writerow({k: "'" + v if isinstance(v, str) and v.startswith(("=", "+", "-", "@")) else v for k, v in row.items()})
        st.download_button("Metrics CSV", buffer.getvalue(), prefix + ".csv", "text/csv", key=prefix+"csv")


def diff_block(text, kind):
    """Escaped plain text with fixed colors; no Markdown/code-highlighter imports."""
    label, background, foreground = {
        "delete": ("Missing reference text", "#fff1f2", "#9f1239"),
        "insert": ("Inserted OCR text", "#ecfdf5", "#065f46"),
    }[kind]
    return (
        f'<div role="region" aria-label="{label}" style="background:{background};'
        f'color:{foreground};border-inline-start:4px solid {foreground};'
        'border-radius:6px;padding:12px;margin-block:8px;max-height:320px;overflow:auto;">'
        f'<strong>{label}</strong><pre dir="auto" style="white-space:pre-wrap;'
        'overflow-wrap:anywhere;unicode-bidi:plaintext;font-family:inherit;'
        f'margin:8px 0 0;">{escape(text)}</pre></div>'
    )


def results(response, prefix="") :
    rows = response["results"]
    summary = []
    for row in rows:
        m = (row.get("metrics") or {})
        summary.append({"Provider": row["provider"], "Status": row["status"], "CER": m.get("cer"), "WER": m.get("wer"),
                        "Match percentage": m.get("character_similarity") * 100 if m.get("character_similarity") is not None else None, "OCR seconds": row.get("duration_seconds")})
    st.subheader("Evaluation results")
    st.dataframe(summary, hide_index=True, column_config={
        "Match percentage": st.column_config.NumberColumn(format="%.2f%%"),
        "CER": st.column_config.NumberColumn(format="percent"),
        "WER": st.column_config.NumberColumn(format="percent"),
    })
    benchmark_chart(rows, prefix + "benchmark_result_chart")
    st.caption("Lower CER/WER is better; rates may exceed 1 (100%). OCR duration excludes HTTP and queueing. Initialization and inference are measured separately.")
    exports([{k:v for k,v in r.items() if k not in ("reference", "output", "diff")} for r in rows], prefix + "current_benchmark")
    for row in rows:
        with st.expander(row["provider"], expanded=len(rows)==1):
            st.caption("Saved benchmark run: " + row["id"])
            if row["status"] != "success":
                st.error(row.get("error", "Extraction failed"))
                continue
            m = row["metrics"]
            cards = st.columns(4)
            cards[0].metric("CER", f'{m["cer"]:.2%}')
            cards[1].metric("WER", f'{m["wer"]:.2%}')
            cards[2].metric("Match percentage", f'{m["character_similarity"]:.2%}')
            duration = row.get("duration_seconds")
            cards[3].metric("OCR duration", f"{duration:.2f}s" if duration is not None else "Unknown")
            st.caption(f'Initialization: {row.get("initialization_seconds")}s · Inference: {row.get("inference_seconds")}s')
            st.caption("Character similarity = 1 − Levenshtein edits / max(reference length, output length), after normalization. " + str(m["character_similarity"]))
            left, right = st.columns(2)
            left.text_area("Reference Markdown (original)", row["reference"], height=350, key=row["id"]+"ref")
            right.text_area("OCR extracted output", row["output"], height=350, key=row["id"]+"ocr")
            st.write("Normalized text changes")
            st.caption("Delete = missing reference text; insert = extra OCR text; replace = substitution. Line alignment is for inspection; metrics use exact character/word edit distance.")
            diff = row["diff"]
            if diff["truncated"]:
                st.info("Diff preview limited to the first 12,000 characters. Metrics cover the complete document.")
            for change in diff["changes"][:100]:
                color = {"delete": "🔴 Missing", "insert": "🟢 Inserted", "replace": "🟠 Substitution"}[change["operation"]]
                st.write(color)
                if change["reference"]:
                    st.html(diff_block(change["reference"], "delete"))
                if change["output"]:
                    st.html(diff_block(change["output"], "insert"))
            st.download_button("OCR extracted text", row["output"], row["provider"]+".txt", key=row["id"]+"txt")
            # Indented code blocks prevent uploaded Markdown from becoming report HTML.
            quote = lambda text: "\n".join("    " + line for line in text.splitlines())
            report = "# OCR comparison\n\n## Metadata and metrics\n\n" + quote(json.dumps({k:v for k,v in row.items() if k not in ("reference", "output", "diff")}, ensure_ascii=False, indent=2))
            report += "\n\n## Reference\n\n" + quote(row["reference"]) + "\n\n## OCR output\n\n" + quote(row["output"]) + "\n\n## Differences\n\n" + quote(json.dumps(diff, ensure_ascii=False, indent=2))
            st.download_button("Comparison report Markdown", report, "comparison.md", key=row["id"]+"report")


def benchmarking(settings, providers):
    st.title("Benchmarking")
    setup, datasets, history = st.tabs(["Ground-truth evaluation", "Existing datasets", "Benchmark history"])
    with setup:
        st.subheader("Evaluation setup")
        left, right = st.columns(2)
        with left:
            pdf = st.file_uploader("Original PDF", type=["pdf"], key="gt_pdf")
        with right:
            ref = st.file_uploader("Reference Markdown (.md)", type=["md"], key="gt_md")
        if ref:
            st.caption(f"Selected reference: {ref.name} · {ref.size} bytes (limit 2 MiB)")
            try:
                if ref.size > 2*1024*1024:
                    raise ValueError("Reference exceeds 2 MiB.")
                text = ref.getvalue().decode("utf-8-sig", errors="strict")
                if not text.strip() or "\x00" in text:
                    raise ValueError("Reference must contain nonempty UTF-8 text without NUL characters.")
                with st.expander("Preview original reference"):
                    st.text_area("Reference source", text, height=220)
            except (ValueError, UnicodeError) as exc:
                st.error(str(exc))
                ref = None
        paired = st.checkbox("I confirm the PDF and reference describe the same document")
        chosen = st.multiselect("OCR providers", providers, default=[providers[0]] if providers else [], key="gt_providers")
        dataset_name = st.text_input("Dataset name", "Uploaded documents", max_chars=120)
        mode = st.radio("Comparison mode", ["plain_text", "raw_markdown"], format_func=lambda x: "Plain text from Markdown" if x=="plain_text" else "Raw Markdown", horizontal=True)
        st.caption("Plain-text mode removes common Markdown markers, link destinations and code fences while preserving their text. Raw mode scores formatting too.")
        with st.expander("Normalization settings"):
            unicode_mode = st.selectbox("Unicode normalization", ["NFC", "none", "NFKC"])
            whitespace = st.checkbox("Normalize whitespace", True)
            breaks = st.checkbox("Normalize line breaks", True)
            case = st.checkbox("Ignore case", False)
            punctuation = st.checkbox("Remove punctuation", False)
            st.caption("Arabic characters and diacritics are preserved. Originals are never modified.")
        options = dict(mode=mode, unicode=unicode_mode, whitespace=whitespace, line_breaks=breaks, casefold=case, punctuation=punctuation)
        st.caption("Metrics and hashes are retained for 90 days by default; uploads and OCR text are not retained by benchmarking. Download comparison text before clearing the session.")
        if pdf and pdf.size > settings.max_upload_bytes:
            st.error("PDF exceeds upload limit.")
        if st.button("Run Benchmark", type="primary", disabled=not(pdf and ref and paired and chosen and dataset_name.strip()) or bool(pdf and pdf.size>settings.max_upload_bytes)):
            with st.status("Evaluating document against your reference…", expanded=True) as status:
                result = api(settings, "POST", "/benchmarks/run", files={"file": (pdf.name, pdf.getvalue(), "application/pdf"), "reference": (ref.name, ref.getvalue(), "text/markdown")}, data={"providers": json.dumps(chosen), "normalization": json.dumps(options), "dataset": dataset_name, "paired": "true"})
                status.update(label="Evaluation complete" if result else "Evaluation needs attention", state="complete" if result else "error", expanded=False)
            if result:
                st.session_state["gt_result"] = result
                st.toast("Benchmark ready. Explore the chart and text differences below.", icon="✅")
        if st.session_state.get("gt_result"):
            results(st.session_state["gt_result"])
            if st.button("Clear benchmark text from session"):
                del st.session_state["gt_result"]
                st.rerun()
    with datasets:
        st.caption("Existing mappings are suggestions from the repository. Confirm the document/reference association before reuse. Historical files are rescored now; original model versions and timings remain unknown.")
        if st.button("Load existing datasets"):
            st.session_state["gt_catalog"] = api(settings, "GET", "/benchmarks/datasets")
        catalog = st.session_state.get("gt_catalog") or []
        if catalog:
            mapping = st.selectbox("Dataset document", catalog, format_func=lambda r: r["dataset"]+" / "+r["reference"])
            source = st.selectbox("Source", ["Rerun PDF"] + mapping["outputs"])
            engines = st.multiselect("Dataset providers", providers, key="dataset_providers")
            confirmed = st.checkbox("I confirm this existing PDF/output and reference mapping")
            if st.button("Evaluate selected dataset document", disabled=not confirmed or (source=="Rerun PDF" and (not engines or not mapping["pdf"]))):
                result = api(settings,"POST","/benchmarks/datasets/run",json={**mapping,"providers":engines,"confirmed":True,"normalization":options,"output":None if source=="Rerun PDF" else source})
                if result:
                    st.session_state["dataset_result"] = result
            if st.session_state.get("dataset_result"):
                results(st.session_state["dataset_result"], "dataset_")
    with history:
        st.caption("Metrics-only history, capped at the latest 2,000 rows. Delete individual runs below. Different documents, datasets or normalization settings are not directly equivalent.")
        provider_filter = st.text_input("Filter provider (exact ID)")
        dataset_filter = st.text_input("Filter dataset (exact name)")
        use_dates = st.checkbox("Filter date range")
        start = st.date_input("From date")
        end = st.date_input("Through date")
        if st.button("Refresh benchmark history"):
            params = {"provider":provider_filter or None,"dataset":dataset_filter or None}
            if use_dates:
                params.update(since=str(start)+"T00:00:00", until=str(end)+"T23:59:59.999999+00:00")
            st.session_state["gt_history"] = api(settings,"GET","/benchmarks/history",params=params)
        rows = st.session_state.get("gt_history") or []
        if rows:
            st.dataframe([{**{k:r.get(k) for k in ("id","timestamp","dataset_id","provider","model_version","status")}, **{k:(r.get("metrics") or {}).get(k) for k in ("cer","wer")}, "Match percentage": f'{r["metrics"]["character_similarity"]:.2%}' if (r.get("metrics") or {}).get("character_similarity") is not None else None} for r in rows], hide_index=True)
            exports(rows,"benchmark_history")
            ids = st.multiselect("Runs to inspect and compare", [r["id"] for r in rows])
            for row in rows:
                if row["id"] in ids:
                    st.text_area("Saved benchmark metadata", json.dumps(row, ensure_ascii=False, indent=2),
                                 height=320, disabled=True, key="history_metadata_"+row["id"])
            if st.button("Compare selected runs", disabled=len(ids)<2):
                comparison = api(settings,"POST","/benchmarks/compare",json=ids)
                if comparison:
                    if not comparison["same_document_and_reference"] or not comparison["same_evaluation_policy"]:
                        st.warning("Selected runs differ in documents, ground truth or evaluation policy. Interpret dataset differences and coverage before drawing conclusions.")
                    st.dataframe(comparison["summaries"], hide_index=True)
                    st.caption(comparison["aggregation"])
            deletion = st.selectbox("Run to delete", [r["id"] for r in rows])
            confirm_delete = st.checkbox("Delete this metrics record permanently")
            if st.button("Delete selected record", disabled=not confirm_delete):
                if api(settings,"DELETE","/benchmarks/history/"+deletion):
                    st.session_state["gt_history"] = [r for r in rows if r["id"] != deletion]
                    st.rerun()
