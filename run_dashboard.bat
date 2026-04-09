@echo off
REM Windows Startup Script for DinDin Quant Bot
REM Place this in your project root: C:\Path\To\DinDin_Quant_Bot\

set "VENV_DIR=%~dp0quant_env"
set "PYTHON_EXE=%VENV_DIR%\Scripts\python.exe"

echo ====================================
echo DinDin Quant Bot - Windows Mode
echo ====================================
echo.

IF NOT EXIST "%PYTHON_EXE%" (
    echo [ERROR] Virtual environment 'quant_env' not found!
    echo Please run the following commands first:
    echo 1. python -m venv quant_env
    echo 2. quant_env\Scripts\activate
    echo 3. pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

echo Starting Streamlit Dashboard...
REM This runs the launcher script with the correct python interpreter
"%PYTHON_EXE%" run_dashboard.py
