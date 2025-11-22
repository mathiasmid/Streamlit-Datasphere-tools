"""
Distribution Package Creator for SAP Datasphere Tools
Run this script to automatically create a distribution package
"""
import os
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

# Files to include in distribution
REQUIRED_FILES = [
    'streamlit_appV2.py',  # Main application (V2)
    'url.json',            # API endpoints
    'config_template.json', # Configuration template
]

# Note: Streamlit1/ folder is copied automatically with all modules

# Files to EXCLUDE (sensitive data)
EXCLUDE_FILES = [
    'secret.json',
    'token.json',
    'config.json',
    'saved_config.json',
]

# Folders to EXCLUDE
EXCLUDE_FOLDERS = [
    'venv',
    '__pycache__',
    '.git',
    '.vscode',
    'dist',
    'build',
]

def create_requirements_txt():
    """Create requirements.txt file if it doesn't exist"""
    requirements_content = """streamlit
pandas
hdbcli
requests
requests-oauthlib
python-dateutil
cron-descriptor
openpyxl
"""
    with open('requirements.txt', 'w') as f:
        f.write(requirements_content)
    print("  ✓ requirements.txt created")

def create_distribution_package():
    """Create a distribution package"""
    
    # Get current directory
    current_dir = os.getcwd()
    print(f"Working directory: {current_dir}\n")
    
    # Create distribution folder name with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dist_folder = f"DatasphereTool_Distribution_{timestamp}"
    
    print("="*60)
    print("SAP Datasphere Tools - Distribution Package Creator")
    print("="*60)
    print()
    
    # Check if requirements.txt exists, if not create it
    if not os.path.exists('requirements.txt'):
        print("⚠ requirements.txt not found - creating it...")
        create_requirements_txt()
    
    # Create distribution folder
    if os.path.exists(dist_folder):
        shutil.rmtree(dist_folder)
    os.makedirs(dist_folder)
    print(f"✓ Created folder: {dist_folder}")
    
    # Copy requirements.txt first
    print("\nCopying files...")
    if os.path.exists('requirements.txt'):
        shutil.copy2('requirements.txt', dist_folder)
        print(f"  ✓ requirements.txt")
    
    # Copy required files
    copied_files = ['requirements.txt']
    missing_files = []
    
    for file in REQUIRED_FILES:
        if os.path.exists(file):
            shutil.copy2(file, dist_folder)
            copied_files.append(file)
            print(f"  ✓ {file}")
        else:
            missing_files.append(file)
            print(f"  ⚠ {file} (not found - skipping)")
    
    # Copy Streamlit1 folder if it exists
    if os.path.exists('Streamlit1'):
        dest_streamlit1 = os.path.join(dist_folder, 'Streamlit1')
        try:
            shutil.copytree('Streamlit1', dest_streamlit1, 
                           ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            print(f"  ✓ Streamlit1/ (folder)")
        except Exception as e:
            print(f"  ⚠ Streamlit1/ (error: {e})")
    
    # Create run_app.bat
    batch_content = """@echo off
echo ========================================
echo SAP Datasphere Tools - Starting...
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
    echo Virtual environment created successfully!
    echo.
)

REM Activate virtual environment
call venv\\Scripts\\activate.bat

REM Install/upgrade requirements
echo Installing dependencies (this may take a minute on first run)...
pip install -r requirements.txt --quiet --disable-pip-version-check
if %errorlevel% neq 0 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

REM Run the Streamlit app
echo.
echo ========================================
echo Starting Datasphere Tools...
echo The app will open in your browser at:
echo http://localhost:8501
echo.
echo Press Ctrl+C to stop the server
echo ========================================
echo.

streamlit run streamlit_appV2.py

pause
"""
    
    with open(os.path.join(dist_folder, 'run_app.bat'), 'w') as f:
        f.write(batch_content)
    print(f"  ✓ run_app.bat (created)")
    
    # Create USER_GUIDE.txt
    user_guide = """========================================
SAP DATASPHERE TOOLS - USER GUIDE
========================================

PREREQUISITES:
--------------
1. Python 3.8 or higher must be installed
   Download from: https://www.python.org/downloads/
   
   ⚠️ IMPORTANT: During installation, check the box:
      ☑ "Add Python to PATH"

2. Internet connection (for first-time setup only)


INSTALLATION & FIRST RUN:
--------------------------
1. Extract this ZIP file to a folder on your computer
   Example: C:\\DatasphereTool\\

2. Double-click "run_app.bat"
   
   First run will:
   - Create a virtual environment (takes ~1 minute)
   - Download and install dependencies (takes ~2-3 minutes)
   - Start the application
   - Open your browser automatically

3. The application opens at: http://localhost:8501


CONFIGURATION:
--------------
1. Go to "Settings" in the left sidebar

2. Choose ONE of these options:

   OPTION 1 - Manual Configuration:
   - Fill in the form fields:
     * DSP Host (your Datasphere URL)
     * Default Space
     * HDB Address (HANA database address)
     * HDB Port (usually 443)
     * HDB User (format: DWCDBUSER#USERNAME)
     * HDB Password
   - Click "Save Configuration"

   OPTION 2 - Upload Files:
   - Upload your config.json, secret.json, and token.json files
   - Configuration is saved automatically

3. For OAuth authentication:
   - Upload secret.json and token.json, OR
   - Click "Start OAuth" to get a new token


DAILY USE:
----------
1. Double-click "run_app.bat"
2. Wait for browser to open (takes ~5-10 seconds)
3. Use the tools from the sidebar
4. Close browser tab when done
5. Press Ctrl+C in the command window to stop


TROUBLESHOOTING:
----------------

Problem: "Python is not installed or not in PATH"
Solution: 
  - Install Python from https://www.python.org/downloads/
  - During installation, CHECK the box "Add Python to PATH"
  - Restart your computer
  - Try running run_app.bat again

Problem: "Module not found" errors
Solution:
  - Delete the "venv" folder
  - Run run_app.bat again

Problem: Browser doesn't open automatically
Solution:
  - Open your browser manually
  - Go to: http://localhost:8501

Problem: Port 8501 already in use
Solution:
  - Close any other Streamlit apps running
  - Or change the port by editing run_app.bat:
    Change last line to: streamlit run streamlit_appV2.py --server.port 8502

Problem: Connection errors to Datasphere
Solution:
  - Check your internet connection
  - Verify your credentials in Settings
  - Check if your OAuth token is expired (regenerate if needed)


UPDATING THE APPLICATION:
--------------------------
When you receive an updated version:
1. Close the running application (Ctrl+C)
2. Extract the new ZIP file
3. Copy your "saved_config.json" from the old folder to the new one
4. Run run_app.bat in the new folder


SECURITY NOTES:
---------------
⚠️ This application stores configuration locally in "saved_config.json"
⚠️ Keep your credentials secure and don't share this file
⚠️ For internal Delaware use only - do not share with clients


SUPPORT:
--------
For questions or issues, contact:
Delaware Datasphere Team

Based on original work by: Tobias Meyer


========================================
"""
    
    with open(os.path.join(dist_folder, 'USER_GUIDE.txt'), 'w', encoding='utf-8') as f:
        f.write(user_guide)
    print(f"  ✓ USER_GUIDE.txt (created)")
    
    # Create README for distributor
    readme = """========================================
FOR DISTRIBUTORS - READ THIS FIRST
========================================

SECURITY WARNING:
-----------------
DO NOT include these files in distribution:
  ❌ secret.json
  ❌ token.json  
  ❌ config.json
  ❌ saved_config.json
  
These files contain sensitive credentials!

Users will configure their own credentials through the Settings page.


WHAT'S INCLUDED:
----------------
✓ Application files (.py)
✓ requirements.txt (dependencies)
✓ url.json (API endpoints)
✓ run_app.bat (Windows launcher)
✓ USER_GUIDE.txt (end-user instructions)


DISTRIBUTION CHECKLIST:
-----------------------
Before sending to colleagues:

1. ✓ All sensitive files removed
2. ✓ USER_GUIDE.txt included
3. ✓ run_app.bat included
4. ✓ requirements.txt included
5. ✓ Tested on a clean machine


HOW TO DISTRIBUTE:
------------------
1. Create a ZIP file of this folder
2. Share the ZIP file with colleagues
3. Point them to USER_GUIDE.txt


TESTING:
--------
Before distributing, test on a clean machine:
1. Extract ZIP to a new folder
2. Ensure Python 3.8+ is installed
3. Double-click run_app.bat
4. Verify it works without errors


UPDATES:
--------
When distributing updates:
1. Users can keep their saved_config.json
2. Replace all other files with new versions
3. Delete the venv folder if there are dependency changes


========================================
"""
    
    with open(os.path.join(dist_folder, 'README_DISTRIBUTOR.txt'), 'w', encoding='utf-8') as f:
        f.write(readme)
    print(f"  ✓ README_DISTRIBUTOR.txt (created)")
    
    # Security check - warn if sensitive files exist
    print("\n" + "="*60)
    print("SECURITY CHECK:")
    print("="*60)
    found_sensitive = []
    for sensitive_file in EXCLUDE_FILES:
        if os.path.exists(sensitive_file):
            found_sensitive.append(sensitive_file)
            print(f"  ⚠ WARNING: {sensitive_file} found (NOT COPIED - GOOD!)")
    
    if not found_sensitive:
        print("  ✓ No sensitive files found in source directory")
    else:
        print(f"\n  ℹ️  {len(found_sensitive)} sensitive file(s) excluded from distribution (this is correct)")
    
    # List all files in distribution
    print("\n" + "="*60)
    print("FILES IN DISTRIBUTION:")
    print("="*60)
    for root, dirs, files in os.walk(dist_folder):
        # Remove excluded directories
        dirs[:] = [d for d in dirs if d not in EXCLUDE_FOLDERS]
        
        level = root.replace(dist_folder, '').count(os.sep)
        indent = ' ' * 2 * level
        print(f"{indent}{os.path.basename(root)}/")
        subindent = ' ' * 2 * (level + 1)
        for file in files:
            print(f"{subindent}{file}")
    
    # Create ZIP file
    print("\n" + "="*60)
    print("CREATING ZIP FILE:")
    print("="*60)
    zip_filename = f"{dist_folder}.zip"
    
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(dist_folder):
            # Remove excluded directories from dirs list
            dirs[:] = [d for d in dirs if d not in EXCLUDE_FOLDERS]
            
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.join(
                    os.path.basename(dist_folder),
                    os.path.relpath(file_path, dist_folder)
                )
                zipf.write(file_path, arcname)
    
    # Get ZIP file size
    zip_size_mb = os.path.getsize(zip_filename) / (1024 * 1024)
    print(f"  ✓ Created: {zip_filename}")
    print(f"  ✓ Size: {zip_size_mb:.2f} MB")
    
    # Summary
    print("\n" + "="*60)
    print("✅ DISTRIBUTION PACKAGE CREATED SUCCESSFULLY!")
    print("="*60)
    print(f"\n📁 Folder: {dist_folder}/")
    print(f"📦 ZIP file: {zip_filename} ({zip_size_mb:.2f} MB)")
    print(f"\n✓ Copied files: {len(copied_files)}")
    
    if missing_files:
        print(f"\n⚠ Missing files (skipped): {len(missing_files)}")
        for mf in missing_files:
            print(f"  - {mf}")
        print("\n  ℹ️  If these files are important, make sure they exist in:")
        print(f"     {current_dir}")
    
    print("\n" + "="*60)
    print("NEXT STEPS:")
    print("="*60)
    print("1. ✓ Review the contents of the distribution folder")
    print("2. ✓ Read README_DISTRIBUTOR.txt")
    print("3. ✓ Test the ZIP file on another computer if possible")
    print("4. ✓ Share the ZIP file with your colleagues")
    print("5. ✓ Point them to USER_GUIDE.txt for instructions")
    print("\n" + "="*60)
    
    return dist_folder, zip_filename

if __name__ == "__main__":
    try:
        dist_folder, zip_file = create_distribution_package()
        print(f"\n✅ SUCCESS! Your distribution package is ready:")
        print(f"   {zip_file}")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    input("\nPress Enter to exit...")
