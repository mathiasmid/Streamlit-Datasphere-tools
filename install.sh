#!/bin/bash
# Installation script for SAP Datasphere Tools (Mac/Linux)
# This script sets up the Python environment and installs all dependencies

echo "========================================"
echo " SAP Datasphere Tools - Installation"
echo "========================================"
echo

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo "Please install Python 3.9 or higher"
    exit 1
fi

echo "Python found:"
python3 --version
echo

# Check Python version (must be 3.9+)
python3 -c "import sys; exit(0 if sys.version_info >= (3, 9) else 1)"
if [ $? -ne 0 ]; then
    echo "ERROR: Python 3.9 or higher is required"
    echo "Please upgrade Python"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "Virtual environment created."
    echo
else
    echo "Virtual environment already exists."
    echo
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
python -m pip install --upgrade pip
echo

# Install requirements
echo "Installing dependencies..."
echo "This may take a few minutes..."
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo
    echo "ERROR: Failed to install dependencies"
    echo "Please check the error messages above"
    exit 1
fi

echo
echo "========================================"
echo " Installation Complete!"
echo "========================================"
echo
echo "To run the application:"
echo "  1. Run: ./run.sh"
echo "  OR"
echo "  2. Run: streamlit run streamlit_appV2.py"
echo
echo "First time setup:"
echo "  1. Run the application"
echo "  2. Go to Settings page"
echo "  3. Configure your SAP Datasphere connection"
echo
