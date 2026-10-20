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
    """Render explicit bars without depending on the browser's Vega runtime."""
    from html import escape
    import math

    successful = [r for r in rows if r.get("status") == "success" and r.get("metrics")]
    if not successful:
        return
    view = st.radio("Comparison chart", ["Error rates", "Processing time"], horizontal=True, key=key)
    bars = []
    for row in successful:
        provider = PROVIDER_NAMES.get(row["provider"], row["provider"])
        metrics = (("CER", row["metrics"].get("cer"), "#2563eb"),
                   ("WER", row["metrics"].get("wer"), "#8b5cf6")) if view == "Error rates" else (
                   ("OCR time", row.get("duration_seconds"), "#2563eb"),)
        for metric, value, color in metrics:
            if isinstance(value, (int, float)) and math.isfinite(value) and value >= 0:
                bars.append((provider, metric, value, color))
    if not bars:
        st.info("Processing durations are unavailable for these runs.")
        return
    maximum = max((bar[2] for bar in bars), default=0) or 1
    content = []
    for provider, metric, value, color in bars:
        label = escape(f"{provider} · {metric}")
        display = f"{value:.2%}" if view == "Error rates" else f"{value:.2f} s"
        width = value / maximum * 100
        content.append(f'''<div style="margin:16px 0">
          <div style="display:flex;justify-content:space-between;gap:16px;margin-bottom:6px">
          <span>{label}</span><strong>{display}</strong></div>
          <div style="height:22px;background:#e8eef8;border-radius:5px;overflow:hidden">
          <div role="img" aria-label="{label}: {display}" style="width:{width:.4f}%;height:22px;background:{color};border-radius:5px"></div>
          </div></div>''')
    st.html('<section aria-label="Provider comparison chart" style="padding:8px 20px;border:1px solid #dce5f3;border-radius:12px">' + ''.join(content) + '</section>')
    st.caption("Error rate · lower is better. Each bar uses the same scale." if view == "Error rates" else "OCR processing time in seconds · lower is better. Each bar uses the same scale.")
