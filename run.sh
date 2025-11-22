#!/bin/bash
# Run script for SAP Datasphere Tools (Mac/Linux)

echo "========================================"
echo " SAP Datasphere Tools"
echo "========================================"
echo

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "ERROR: Virtual environment not found"
    echo "Please run ./install.sh first"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Check if streamlit is installed
python -c "import streamlit" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "ERROR: Streamlit not installed"
    echo "Please run ./install.sh first"
    exit 1
fi

# Run the application
echo "Starting SAP Datasphere Tools..."
echo
echo "The application will open in your browser at:"
echo "http://localhost:8501"
echo
echo "Press Ctrl+C to stop the application"
echo

streamlit run streamlit_appV2.py

# If streamlit exits, deactivate venv
deactivate
