@echo off
setlocal
cd /d "%~dp0"
title OCR Benchmarking
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\launch.ps1" %*
set "LAUNCH_EXIT_CODE=%ERRORLEVEL%"
if not "%LAUNCH_EXIT_CODE%"=="0" (
    echo.
    echo OCR could not start. Read the message above for the next step.
    pause
)
endlocal & exit /b %LAUNCH_EXIT_CODE%
