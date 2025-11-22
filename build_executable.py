"""
Build Executable for SAP Datasphere Tools using PyInstaller

This script creates a standalone Windows executable that includes:
- Python runtime
- All dependencies
- Streamlit framework
- The complete Datasphere Tools application

Usage:
    python build_executable.py

Requirements:
    pip install pyinstaller

Output:
    dist/DatasphereTools/DatasphereTools.exe
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

# Configuration
APP_NAME = "DatasphereTools"
VERSION = "2.0.0"
MAIN_SCRIPT = "streamlit_appV2.py"
ICON_FILE = None  # Set to path of .ico file if you have one

# Data files to include
DATA_FILES = [
    ('url.json', '.'),
    ('config_template.json', '.'),
    ('LICENSE', '.'),
    ('README.md', '.'),
    ('QUICK_START.md', '.'),
]

# Directories to include
DATA_DIRS = [
    ('Streamlit1', 'Streamlit1'),
    ('examples', 'examples'),
]

# Hidden imports (modules not automatically detected)
HIDDEN_IMPORTS = [
    'streamlit',
    'pandas',
    'hdbcli',
    'requests',
    'requests_oauthlib',
    'pydantic',
    'cryptography',
    'openpyxl',
    'python_docx',
    'cron_descriptor',
    'altair',
    'plotly',
    'PIL',
]

def clean_build():
    """Remove previous build artifacts."""
    print("Cleaning previous build artifacts...")
    dirs_to_remove = ['build', 'dist', '__pycache__']
    for dir_name in dirs_to_remove:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"  ✓ Removed {dir_name}/")

    # Remove .spec file
    spec_file = f"{APP_NAME}.spec"
    if os.path.exists(spec_file):
        os.remove(spec_file)
        print(f"  ✓ Removed {spec_file}")

def build_executable():
    """Build the executable using PyInstaller."""
    print("\n" + "="*60)
    print(f"Building {APP_NAME} v{VERSION}")
    print("="*60 + "\n")

    # Check if PyInstaller is installed
    try:
        import PyInstaller
        print(f"✓ PyInstaller {PyInstaller.__version__} found")
    except ImportError:
        print("✗ PyInstaller not found!")
        print("\nPlease install PyInstaller:")
        print("  pip install pyinstaller")
        sys.exit(1)

    # Check if main script exists
    if not os.path.exists(MAIN_SCRIPT):
        print(f"✗ Main script not found: {MAIN_SCRIPT}")
        sys.exit(1)

    print(f"✓ Main script found: {MAIN_SCRIPT}\n")

    # Build PyInstaller command
    cmd = [
        'pyinstaller',
        '--name', APP_NAME,
        '--onedir',  # Create a folder (not a single file - better for Streamlit)
        '--windowed',  # No console window (we'll create a wrapper)
        '--clean',
        '--noconfirm',
    ]

    # Add icon if available
    if ICON_FILE and os.path.exists(ICON_FILE):
        cmd.extend(['--icon', ICON_FILE])

    # Add data files
    for src, dest in DATA_FILES:
        if os.path.exists(src):
            cmd.extend(['--add-data', f'{src};{dest}'])
            print(f"  Including file: {src}")

    # Add data directories
    for src, dest in DATA_DIRS:
        if os.path.exists(src):
            cmd.extend(['--add-data', f'{src};{dest}'])
            print(f"  Including directory: {src}/")

    # Add hidden imports
    print("\n  Hidden imports:")
    for module in HIDDEN_IMPORTS:
        cmd.extend(['--hidden-import', module])
        print(f"    - {module}")

    # Add main script
    cmd.append(MAIN_SCRIPT)

    # Run PyInstaller
    print("\n" + "="*60)
    print("Running PyInstaller...")
    print("="*60 + "\n")
    print(f"Command: {' '.join(cmd)}\n")

    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        print("\n" + "="*60)
        print("✓ Build completed successfully!")
        print("="*60)
    except subprocess.CalledProcessError as e:
        print("\n" + "="*60)
        print("✗ Build failed!")
        print("="*60)
        print(f"\nError: {e}")
        sys.exit(1)

def create_launcher():
    """Create a launcher batch file that runs Streamlit correctly."""
    launcher_content = f"""@echo off
REM SAP Datasphere Tools Launcher
REM Version {VERSION}

echo ========================================
echo SAP Datasphere Tools v{VERSION}
echo ========================================
echo.
echo Starting application...
echo The app will open in your browser at:
echo http://localhost:8501
echo.
echo Press Ctrl+C to stop the server
echo ========================================
echo.

REM Set the working directory to the executable's location
cd /d "%~dp0"

REM Run Streamlit with the bundled executable
REM The .exe runs streamlit internally
"%~dp0{APP_NAME}.exe" run streamlit_appV2.py

pause
"""

    dist_dir = Path(f"dist/{APP_NAME}")
    launcher_path = dist_dir / "Launch.bat"

    with open(launcher_path, 'w') as f:
        f.write(launcher_content)

    print(f"\n✓ Created launcher: {launcher_path}")

def create_readme():
    """Create a README for the distribution."""
    readme_content = f"""
========================================
SAP DATASPHERE TOOLS v{VERSION}
========================================

QUICK START:
-----------
1. Double-click "Launch.bat" to start the application
2. Your web browser will open to http://localhost:8501
3. Configure your credentials in Settings
4. Start using the tools!

REQUIREMENTS:
------------
- Windows 7 or later (64-bit)
- Internet connection (for first-time API access)
- No Python installation required!

FEATURES:
---------
- Object Lineage Analysis
- Documentation Generator (Word export)
- User Analytics
- Column Search
- Object Dependencies
- Business Name Lookup
- Exposed Views Analysis
- DAC Analysis
- Export Objects to JSON

CONFIGURATION:
-------------
On first run:
1. Click "Settings V2" in the sidebar
2. Enter your SAP Datasphere credentials:
   - DSP Host (e.g., https://your-tenant.hcs.cloud.sap)
   - HANA Database details
   - OAuth credentials (or upload secret.json/token.json)
3. Click "Save Configuration"

Your credentials are encrypted and stored locally in saved_config.json

TROUBLESHOOTING:
---------------
Problem: Application won't start
Solution:
  - Right-click Launch.bat and select "Run as administrator"
  - Check Windows Defender or antivirus hasn't blocked it
  - Make sure no other application is using port 8501

Problem: Browser doesn't open automatically
Solution:
  - Open your browser manually
  - Navigate to: http://localhost:8501

Problem: "Module not found" errors
Solution:
  - Re-extract the ZIP file completely
  - Make sure you didn't move files out of the folder

SECURITY:
---------
⚠️ For Delaware internal use only
⚠️ Keep your saved_config.json file secure
⚠️ Never share your OAuth tokens or passwords
⚠️ Report security issues to IT immediately

SUPPORT:
--------
For questions or issues:
Delaware Datasphere Team
delaware.com

Original Author: Tobias Meyer
Version: {VERSION}
Build Date: 2025-01-22

========================================
"""

    dist_dir = Path(f"dist/{APP_NAME}")
    readme_path = dist_dir / "README.txt"

    with open(readme_path, 'w') as f:
        f.write(readme_content)

    print(f"✓ Created README: {readme_path}")

def create_zip_distribution():
    """Create a ZIP file of the distribution."""
    import zipfile
    from datetime import datetime

    dist_folder = f"dist/{APP_NAME}"
    timestamp = datetime.now().strftime("%Y%m%d")
    zip_filename = f"{APP_NAME}_v{VERSION}_{timestamp}.zip"

    print(f"\nCreating distribution ZIP: {zip_filename}")

    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(dist_folder):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, 'dist')
                zipf.write(file_path, arcname)
                print(f"  Adding: {arcname}")

    zip_size_mb = os.path.getsize(zip_filename) / (1024 * 1024)
    print(f"\n✓ Created: {zip_filename} ({zip_size_mb:.1f} MB)")

    return zip_filename

def main():
    """Main build process."""
    print("\n" + "="*60)
    print(f"SAP DATASPHERE TOOLS - EXECUTABLE BUILDER")
    print(f"Version {VERSION}")
    print("="*60 + "\n")

    # Step 1: Clean previous builds
    clean_build()

    # Step 2: Build executable
    build_executable()

    # Step 3: Create launcher
    print("\nCreating launcher script...")
    create_launcher()

    # Step 4: Create README
    print("\nCreating distribution README...")
    create_readme()

    # Step 5: Create ZIP distribution
    print("\nCreating ZIP distribution...")
    zip_file = create_zip_distribution()

    # Final summary
    print("\n" + "="*60)
    print("✅ BUILD COMPLETE!")
    print("="*60)
    print(f"\n📁 Executable folder: dist/{APP_NAME}/")
    print(f"📦 Distribution ZIP: {zip_file}")
    print(f"\nTo test:")
    print(f"  1. Navigate to dist/{APP_NAME}/")
    print(f"  2. Double-click Launch.bat")
    print(f"  3. Check if the app opens in your browser")
    print(f"\nTo distribute:")
    print(f"  1. Share {zip_file} with colleagues")
    print(f"  2. They extract and run Launch.bat")
    print(f"  3. No Python installation required!")
    print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    main()
