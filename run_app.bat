@echo off
setlocal
cd /d "%~dp0"
set "OCR_PYTHON=%~dp0.venv\Scripts\python.exe"
if not exist "%OCR_PYTHON%" (
    echo Create and install the root .venv following README.md first.
    exit /b 1
)
"%OCR_PYTHON%" -c "import sys; print(sys.executable)"
if errorlevel 1 exit /b 1
start "OCR API" cmd /k ""%OCR_PYTHON%" -m OCR"
start "OCR Streamlit" cmd /k ""%OCR_PYTHON%" -m streamlit run OCR\streamlit_app.py --server.address 127.0.0.1"
endlocal
