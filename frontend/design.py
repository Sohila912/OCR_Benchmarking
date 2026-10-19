"""Lightweight presentation helpers; all scores come from the backend."""
import streamlit as st

PROVIDER_NAMES = {"tesseract": "Tesseract", "docling": "Docling", "paddle_vl": "PaddleOCR-VL", "qwen_ollama": "Qwen · Ollama"}


def apply_theme():
    st.html('''<style>
    .stApp{background:#f7f9fd;color:#17243e}
    [data-testid="stMainBlockContainer"]{max-width:1440px;padding-top:2rem}
    [data-testid="stSidebar"]{background:#eef3fb;border-right:1px solid #dce5f3}
    h1,h2,h3{letter-spacing:-.035em}
    [data-testid="stMetric"]{background:white;border:1px solid #e0e7f1;border-radius:16px;padding:18px;box-shadow:0 4px 18px #18325a06}
    [data-testid="stMetricLabel"]{color:#526581}
    [data-testid="stMetricValue"]{font-weight:650;letter-spacing:-.04em}
    [data-testid="stButton"] button,[data-testid="stDownloadButton"] button{border-radius:10px}
    [data-testid="stExpander"]{background:white;border-radius:12px}
    [data-testid="stTabs"] [role="tab"]{padding:12px 18px}
    textarea{line-height:1.7!important}
    @media(max-width:640px){[data-testid="stMainBlockContainer"]{padding:1rem}}
    </style>''')


def hero():
    st.html('''<section style="background:linear-gradient(120deg,#142846,#244f85);color:white;padding:32px;border-radius:20px;margin-bottom:24px">
    <div style="font-size:12px;letter-spacing:.16em;color:#bcd7ff">AI DOCUMENT INTELLIGENCE</div>
    <h2 style="color:white;margin:12px 0">Turn documents into evidence.</h2>
    <p style="color:#d9e7fa">Extract content. Compare models. Measure recognition against your ground truth.</p>
    <div style="font-size:13px;color:#bcd7ff">PDF extraction · Multi-model comparison · Reproducible evaluation</div></section>''')


def workflow(active):
    for index, (column, label) in enumerate(zip(st.columns(4), ("Upload", "Select model", "Process", "Results"))):
        with column:
            st.caption(f"STEP {index + 1}")
            st.markdown(f"**{label}**")
            color = "#2563eb" if index <= active else "#dce5f3"
            st.html(f'<div style="height:4px;background:{color};border-radius:8px;margin-bottom:16px"></div>')


def benchmark_chart(rows, key):
    successful = [r for r in rows if r.get("status") == "success" and r.get("metrics")]
    if not successful:
        return
    import altair as alt
    view = st.radio("Comparison chart", ["Error rates", "Processing time"], horizontal=True, key=key)
    if view == "Error rates":
        data = [{"Provider": PROVIDER_NAMES.get(r["provider"], r["provider"]), "Metric": metric.upper(), "Value": r["metrics"][metric]} for r in successful for metric in ("cer", "wer")]
        chart = alt.Chart(alt.Data(values=data)).mark_bar(cornerRadiusEnd=4).encode(y="Provider:N", yOffset="Metric:N", x=alt.X("Value:Q", axis=alt.Axis(format=".0%"), title="Error rate · lower is better"), color=alt.Color("Metric:N", scale=alt.Scale(range=["#2563eb", "#8b5cf6"])), tooltip=["Provider:N", "Metric:N", alt.Tooltip("Value:Q", format=".2%")])
    else:
        data = [{"Provider": PROVIDER_NAMES.get(r["provider"], r["provider"]), "Seconds": r["duration_seconds"]} for r in successful if r.get("duration_seconds") is not None]
        if not data:
            st.info("Processing durations are unavailable for these runs.")
            return
        chart = alt.Chart(alt.Data(values=data)).mark_bar(color="#2563eb", cornerRadiusEnd=4).encode(y="Provider:N", x="Seconds:Q", tooltip=["Provider:N", alt.Tooltip("Seconds:Q", format=".2f")])
    st.altair_chart(chart.properties(height=max(140, len(successful) * 65)).interactive(), width="stretch")
