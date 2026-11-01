@echo off
setlocal
rem No installation or model selection here. Python owns all approval/preflight gates.
pushd "%~dp0..\.." || exit /b 1
if defined OCR_BENCHMARK_PYTHON goto override
if exist ".venv-ocr\Scripts\python.exe" (
    set "BENCHMARK_PYTHON=%CD%\.venv-ocr\Scripts\python.exe"
    goto execute
)
if exist "benchmark_suite\environments\shared\Scripts\python.exe" (
    set "BENCHMARK_PYTHON=%CD%\benchmark_suite\environments\shared\Scripts\python.exe"
    goto execute
)
where py.exe >nul 2>nul
if not errorlevel 1 goto pylauncher
where python.exe >nul 2>nul
if not errorlevel 1 (
    set "BENCHMARK_PYTHON=python.exe"
    goto execute
)
echo Python 3.10+ was not found. Set OCR_BENCHMARK_PYTHON to an existing compatible python.exe.
set "BENCHMARK_EXIT=1"
goto finish

:override
if not exist "%OCR_BENCHMARK_PYTHON%" (
    echo OCR_BENCHMARK_PYTHON does not name an existing interpreter. Nothing was installed.
    set "BENCHMARK_EXIT=1"
    goto finish
)
set "BENCHMARK_PYTHON=%OCR_BENCHMARK_PYTHON%"

:execute
"%BENCHMARK_PYTHON%" -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)"
if errorlevel 1 goto badpython
"%BENCHMARK_PYTHON%" -m benchmark_suite.cli %*
set "BENCHMARK_EXIT=%ERRORLEVEL%"
goto finish

:pylauncher
py.exe -3 -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)"
if errorlevel 1 goto badpython
py.exe -3 -m benchmark_suite.cli %*
set "BENCHMARK_EXIT=%ERRORLEVEL%"
goto finish

:badpython
echo Python 3.10+ is required. Select an existing compatible interpreter; nothing was installed.
set "BENCHMARK_EXIT=1"

:finish
popd
endlocal & exit /b %BENCHMARK_EXIT%
