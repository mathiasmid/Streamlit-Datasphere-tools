@echo off
REM Run script for SAP Datasphere Tools

echo ========================================
echo  SAP Datasphere Tools
echo ========================================
echo.

REM Check if virtual environment exists
if not exist "venv" (
    echo ERROR: Virtual environment not found
    echo Please run install.bat first
    pause
    exit /b 1
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Check if streamlit is installed
python -c "import streamlit" >nul 2>&1
if errorlevel 1 (
    echo ERROR: Streamlit not installed
    echo Please run install.bat first
    pause
    exit /b 1
)

REM Run the application
echo Starting SAP Datasphere Tools...
echo.
echo The application will open in your browser at:
echo http://localhost:8501
echo.
echo Press Ctrl+C to stop the application
echo.

streamlit run streamlit_appV2.py

REM If streamlit exits, deactivate venv
deactivate
