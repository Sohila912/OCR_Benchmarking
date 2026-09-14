@echo off

title OCR Benchmarking Platform

echo.
echo ============================================
echo       OCR BENCHMARKING PLATFORM
echo ============================================
echo.

REM ------------------------------------------------
REM Move to project directory
REM ------------------------------------------------

cd /d "%~dp0"

echo Project directory:
echo %CD%
echo.

REM ------------------------------------------------
REM Check virtual environment
REM ------------------------------------------------

if exist ".venv\Scripts\python.exe" (

    echo Using virtual environment...
    set PYTHON=.venv\Scripts\python.exe
    set UVICORN=.venv\Scripts\uvicorn.exe

) else (

    echo No .venv found.
    echo Using system Python...

    set PYTHON=python
    set UVICORN=uvicorn
)

echo.

REM ------------------------------------------------
REM Start FastAPI
REM ------------------------------------------------

echo ============================================
echo Starting FastAPI backend...
echo ============================================
echo.

start "OCR FastAPI Backend" cmd /k ^
"%UVICORN%" app:app --host 127.0.0.1 --port 8000

REM ------------------------------------------------
REM Wait for FastAPI
REM ------------------------------------------------

echo.
echo Waiting for FastAPI to start...

timeout /t 50 /nobreak >nul

REM ------------------------------------------------
REM Start Streamlit
REM ------------------------------------------------

echo.
echo ============================================
echo Starting Streamlit frontend...
echo ============================================
echo.

start "OCR Streamlit Frontend" cmd /k ^
"%PYTHON%" -m streamlit run streamlit_app.py --server.address 127.0.0.1 --server.port 8501

REM ------------------------------------------------
REM Wait for Streamlit
REM ------------------------------------------------

timeout /t 5 /nobreak >nul

REM ------------------------------------------------
REM Open browser
REM ------------------------------------------------

echo.
echo ============================================
echo OCR Benchmarking Platform is running!
echo ============================================
echo.

start http://127.0.0.1:8501

echo.
echo Frontend:
echo http://127.0.0.1:8501
echo.
echo Backend:
echo http://127.0.0.1:8000
echo.
echo API Docs:
echo http://127.0.0.1:8000/docs
echo.

exit