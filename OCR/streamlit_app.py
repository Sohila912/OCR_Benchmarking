import requests
import streamlit as st


# ============================================================
# CONFIGURATION
# ============================================================

API_URL = "http://127.0.0.1:8000"


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="OCR Benchmarker",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>

    .stApp {
        background-color: #f7f8fc;
    }

    .main-title {
        font-size: 2.7rem;
        font-weight: 800;
        color: #1f2937;
        margin-bottom: 0.2rem;
    }

    .subtitle {
        font-size: 1.05rem;
        color: #6b7280;
        margin-bottom: 2rem;
    }

    .card {
        background-color: white;
        padding: 1.5rem;
        border-radius: 16px;
        border: 1px solid #e5e7eb;
        margin-bottom: 1rem;
    }

    .card-title {
        font-size: 1.2rem;
        font-weight: 700;
        color: #1f2937;
        margin-bottom: 1rem;
    }

    .engine-card {
        background-color: white;
        border-radius: 14px;
        padding: 1rem;
        border: 1px solid #e5e7eb;
        text-align: center;
    }

    .footer {
        text-align: center;
        color: #9ca3af;
        padding: 2rem;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# API FUNCTIONS
# ============================================================

def check_api():

    try:

        response = requests.get(
            f"{API_URL}/health",
            timeout=3
        )

        return response.status_code == 200

    except:

        return False


def get_tools():

    try:

        response = requests.get(
            f"{API_URL}/tools",
            timeout=3
        )

        if response.status_code == 200:

            return response.json()["tools"]

    except:

        pass

    return []


def extract_single(engine, uploaded_file):

    files = {
        "file": (
            uploaded_file.name,
            uploaded_file.getvalue(),
            "application/pdf"
        )
    }

    data = {
        "engine": engine
    }

    response = requests.post(
        f"{API_URL}/extract",
        files=files,
        data=data,
        timeout=3600
    )

    response.raise_for_status()

    return response.json()


def compare_all(uploaded_file):

    files = {
        "file": (
            uploaded_file.name,
            uploaded_file.getvalue(),
            "application/pdf"
        )
    }

    response = requests.post(
        f"{API_URL}/extract/compare",
        files=files,
        timeout=3600
    )

    response.raise_for_status()

    return response.json()


# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="main-title">🔍 OCR Benchmarker</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Compare OCR engines and evaluate document extraction quality'
    '</div>',
    unsafe_allow_html=True
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown("## ⚙️ Configuration")

    st.markdown("---")

    st.markdown("### 🔌 Backend")

    if check_api():

        st.success("🟢 FastAPI Online")

    else:

        st.error("🔴 FastAPI Offline")

        st.caption(
            "The backend is not running."
        )

    st.markdown("---")

    st.markdown("### 🧠 OCR Engines")

    tools = get_tools()

    if tools:

        for tool in tools:

            if tool == "marker":
                st.write("🔵 Marker")

            elif tool == "paddle":
                st.write("🟢 PaddleOCR")

            elif tool == "tesseract":
                st.write("🟠 Tesseract")

            else:
                st.write(f"⚪ {tool.title()}")

    st.markdown("---")

    st.caption(
        "OCR Benchmarking Platform"
    )


# ============================================================
# UPLOAD
# ============================================================

st.markdown(
    """
    <div class="card">
        <div class="card-title">
            📄 Upload PDF
        </div>
    """,
    unsafe_allow_html=True
)

uploaded_file = st.file_uploader(
    "Drop your PDF here",
    type=["pdf"],
    help="Upload a PDF document for OCR processing."
)

st.markdown(
    "</div>",
    unsafe_allow_html=True
)


# ============================================================
# FILE INFORMATION
# ============================================================

if uploaded_file:

    file_size = (
        len(uploaded_file.getvalue())
        / (1024 * 1024)
    )

    col1, col2, col3 = st.columns(3)

    with col1:

        st.metric(
            "Document",
            uploaded_file.name
        )

    with col2:

        st.metric(
            "Size",
            f"{file_size:.2f} MB"
        )

    with col3:

        st.metric(
            "Format",
            "PDF"
        )

    st.markdown("")


    # ========================================================
    # ENGINE SELECTION
    # ========================================================

    st.markdown("### 🧠 Select OCR Engines")

    col1, col2, col3 = st.columns(3)

    with col1:

        marker = st.checkbox(
            "🔵 Marker",
            value=True
        )

    with col2:

        paddle = st.checkbox(
            "🟢 PaddleOCR",
            value=True
        )

    with col3:

        tesseract = st.checkbox(
            "🟠 Tesseract",
            value=True
        )


    selected_engines = []

    if marker:
        selected_engines.append("marker")

    if paddle:
        selected_engines.append("paddle")

    if tesseract:
        selected_engines.append("tesseract")


    # ========================================================
    # ACTIONS
    # ========================================================

    st.markdown("")

    col1, col2 = st.columns(2)

    with col1:

        run_selected = st.button(
            "🚀 Run Selected Engines",
            type="primary",
            use_container_width=True
        )

    with col2:

        run_benchmark = st.button(
            "⚡ Compare All Engines",
            use_container_width=True
        )


    # ========================================================
    # SELECTED ENGINE EXTRACTION
    # ========================================================

    if run_selected:

        if not selected_engines:

            st.warning(
                "Select at least one OCR engine."
            )

        elif not check_api():

            st.error(
                "FastAPI is offline."
            )

        else:

            st.markdown("---")

            st.markdown(
                "## 🔬 Extraction Results"
            )

            results = {}

            for engine in selected_engines:

                engine_display = {
                    "marker": "🔵 Marker",
                    "paddle": "🟢 PaddleOCR",
                    "tesseract": "🟠 Tesseract"
                }[engine]

                with st.spinner(
                    f"Running {engine_display}..."
                ):

                    try:

                        result = extract_single(
                            engine,
                            uploaded_file
                        )

                        results[engine] = result

                        st.success(
                            f"{engine_display} completed."
                        )

                    except Exception as e:

                        st.error(
                            f"{engine_display} failed: {e}"
                        )


            # =================================================
            # RESULTS
            # =================================================

            if results:

                tabs = st.tabs(
                    list(results.keys())
                )

                for tab, engine in zip(
                    tabs,
                    results.keys()
                ):

                    with tab:

                        markdown = results[
                            engine
                        ]["markdown"]

                        st.download_button(
                            "⬇️ Download Markdown",
                            markdown,
                            file_name=(
                                f"{engine}_output.md"
                            ),
                            mime="text/markdown",
                            key=f"single_{engine}"
                        )

                        st.markdown("---")

                        st.markdown(markdown)


    # ========================================================
    # FULL BENCHMARK
    # ========================================================

    if run_benchmark:

        if not check_api():

            st.error(
                "FastAPI is offline."
            )

        else:

            st.markdown("---")

            st.markdown(
                "## 🏆 OCR Benchmark"
            )

            with st.spinner(
                "Running all OCR engines..."
            ):

                try:

                    result = compare_all(
                        uploaded_file
                    )

                    results = result[
                        "results"
                    ]

                    st.success(
                        "Benchmark completed! 🎉"
                    )

                    # =========================================
                    # SUMMARY
                    # =========================================

                    st.markdown(
                        "### 📊 Extraction Summary"
                    )

                    cols = st.columns(
                        len(results)
                    )

                    for col, item in zip(
                        cols,
                        results
                    ):

                        with col:

                            engine = item[
                                "engine"
                            ]

                            st.markdown(
                                f"""
                                <div class="engine-card">

                                <h3>
                                {engine.title()}
                                </h3>

                                <p>
                                ✓ Completed
                                </p>

                                </div>
                                """,
                                unsafe_allow_html=True
                            )


                    st.markdown("")

                    # =========================================
                    # RESULTS
                    # =========================================

                    st.markdown(
                        "### 📑 Extracted Content"
                    )

                    tabs = st.tabs(
                        [
                            item["engine"].title()
                            for item in results
                        ]
                    )

                    for tab, item in zip(
                        tabs,
                        results
                    ):

                        with tab:

                            engine = item[
                                "engine"
                            ]

                            markdown = item[
                                "markdown"
                            ]

                            st.download_button(
                                "⬇️ Download Markdown",
                                markdown,
                                file_name=(
                                    f"{engine}_output.md"
                                ),
                                mime="text/markdown",
                                key=f"compare_{engine}"
                            )

                            st.markdown("---")

                            st.markdown(markdown)

                except Exception as e:

                    st.error(
                        f"Benchmark failed: {e}"
                    )


# ============================================================
# EMPTY STATE
# ============================================================

else:

    st.info(
        "👆 Upload a PDF above to start benchmarking."
    )


# ============================================================
# FOOTER
# ============================================================

st.markdown(
    """
    <div class="footer">
        OCR Benchmarker • FastAPI + Streamlit
    </div>
    """,
    unsafe_allow_html=True
)