@echo off
REM ==========================================
REM DinDin Quant Bot Intraday Monitor Launcher
REM ==========================================
REM This script is designed to be executed by Windows Task Scheduler
REM Scheduled to run at 17:45 PM (Vancouver time) / 08:45 AM (Taiwan time)

set "VENV_DIR=%~dp0quant_env"
set "PYTHON_EXE=%VENV_DIR%\Scripts\python.exe"

cd /d "%~dp0"

if not exist "%PYTHON_EXE%" (
    echo [ERROR] Virtual environment 'quant_env' not found!
    echo Ensure the bot is fully set up in: %~dp0
    timeout /t 10
    exit /b 1
)

echo === Starting DinDin Quant Bot Intraday Monitor ===
"%PYTHON_EXE%" scripts\run_intraday_monitor.py

echo.
echo Process finished. Window will close in 10 seconds.
timeout /t 10 >nul
