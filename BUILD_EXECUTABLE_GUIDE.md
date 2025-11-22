# Building Executable Distribution

This guide explains how to create a standalone Windows executable for SAP Datasphere Tools.

## Prerequisites

1. **Python 3.8+** installed
2. **All dependencies** installed: `pip install -r requirements.txt`
3. **PyInstaller**: `pip install pyinstaller`
4. **Windows OS** (for building Windows executables)

## Quick Start

### Option 1: Automated Build (Recommended)

```bash
python build_executable.py
```

This will:
- Clean previous builds
- Build the executable with PyInstaller
- Create launcher scripts
- Generate a distribution README
- Package everything into a ZIP file

Output: `DatasphereTools_v2.0.0_YYYYMMDD.zip`

### Option 2: Manual Build

If you need more control:

```bash
# Install PyInstaller
pip install pyinstaller

# Build the executable
pyinstaller --name DatasphereTools ^
    --onedir ^
    --windowed ^
    --clean ^
    --add-data "url.json;." ^
    --add-data "config_template.json;." ^
    --add-data "Streamlit1;Streamlit1" ^
    --hidden-import streamlit ^
    --hidden-import pandas ^
    --hidden-import hdbcli ^
    streamlit_appV2.py
```

## Build Output

After building, you'll find:

```
dist/
└── DatasphereTools/
    ├── DatasphereTools.exe       # Main executable
    ├── Launch.bat                # Launcher script
    ├── README.txt                # User guide
    ├── _internal/                # Python runtime & dependencies
    ├── url.json                  # API endpoints
    ├── config_template.json      # Config template
    ├── Streamlit1/               # Application modules
    └── examples/                 # Example files
```

## Distribution

### Create Distribution Package

The `build_executable.py` script automatically creates a ZIP file:

```
DatasphereTools_v2.0.0_20250122.zip
```

This ZIP contains everything needed to run the application.

### Share with Users

1. **Upload** the ZIP file to a shared drive or distribution platform
2. **Instruct users** to:
   - Extract the ZIP file to a folder (e.g., `C:\DatasphereTools\`)
   - Double-click `Launch.bat` to start
   - Configure credentials in Settings V2

### No Installation Required

Users do NOT need:
- Python installed
- pip or package management
- Technical knowledge
- Admin rights (usually)

## How It Works

### PyInstaller Process

1. **Analyzes** your Python script and dependencies
2. **Bundles** Python runtime + all libraries
3. **Creates** an executable that:
   - Extracts itself to a temp folder on first run
   - Runs Python internally
   - Launches Streamlit server
   - Opens browser to http://localhost:8501

### Launcher Script

The `Launch.bat` file:
- Sets the working directory
- Runs the executable
- Shows status messages
- Keeps console window open for debugging

## Troubleshooting Build Issues

### Issue: "Module not found" during build

**Solution**: Add the module to `HIDDEN_IMPORTS` in `build_executable.py`:

```python
HIDDEN_IMPORTS = [
    'streamlit',
    'pandas',
    'your_missing_module',  # Add here
]
```

### Issue: Build takes forever

**Cause**: PyInstaller analyzes all dependencies

**Solutions**:
- Normal for first build (~5-10 minutes)
- Subsequent builds are faster
- Use `--clean` flag to force fresh build

### Issue: Large executable size (~300-500 MB)

**Cause**: Bundles entire Python runtime + all dependencies

**Solutions**:
- This is normal for PyInstaller
- Consider excluding unused packages
- ZIP compression helps for distribution
- Alternative: Keep using install.bat/run.bat approach

### Issue: Antivirus flags the executable

**Cause**: PyInstaller executables sometimes trigger false positives

**Solutions**:
- Add exclusion in Windows Defender
- Sign the executable (requires code signing certificate)
- Distribute via approved internal channels
- Add to corporate antivirus whitelist

### Issue: Application doesn't start

**Debugging**:

1. Run from command line to see errors:
   ```cmd
   cd dist\DatasphereTools
   DatasphereTools.exe
   ```

2. Check for missing data files:
   - Verify `url.json` exists
   - Verify `Streamlit1/` folder exists
   - Check console for error messages

3. Test on a clean machine:
   - VM or colleague's computer
   - Fresh Windows installation
   - No Python pre-installed

## Advanced Customization

### Add an Icon

1. Create or obtain a `.ico` file (256x256 recommended)
2. Place it in the project root as `icon.ico`
3. Update `build_executable.py`:
   ```python
   ICON_FILE = "icon.ico"
   ```

### Customize Launcher

Edit the `create_launcher()` function in `build_executable.py`:

```python
launcher_content = f"""@echo off
REM Add your custom startup message
echo Welcome to Datasphere Tools!
echo.

REM Add custom environment variables if needed
set STREAMLIT_SERVER_PORT=8501

"%~dp0{APP_NAME}.exe" run streamlit_appV2.py
"""
```

### Single-File Executable (Not Recommended for Streamlit)

If you want a single `.exe` file instead of a folder:

```python
cmd = [
    'pyinstaller',
    '--name', APP_NAME,
    '--onefile',  # Single file instead of folder
    '--windowed',
    # ... rest of options
]
```

**Warning**: Single-file mode:
- Takes longer to start (extracts to temp each time)
- Can cause issues with Streamlit's file watchers
- Larger memory footprint
- Not recommended for this application

## Alternative: Keep Python-Based Distribution

If executable builds are problematic, the existing approach works great:

### Pros of Python-Based Distribution
- Smaller download size
- Easier to update (replace .py files)
- No build process needed
- Better for developers

### Cons
- Users need Python installed
- More setup steps
- Potential version conflicts

### When to Use Each

**Use Executable** when:
- Users are non-technical
- No Python installation allowed
- Corporate environment restrictions
- Need simplest possible distribution

**Use Python/Scripts** when:
- Users are developers
- Active development/frequent updates
- Need easy debugging
- Size matters

## Testing the Executable

### Pre-Distribution Checklist

- [ ] Build completes without errors
- [ ] Executable runs on build machine
- [ ] Application opens in browser
- [ ] Can configure settings
- [ ] Can connect to Datasphere API
- [ ] Can connect to HANA database
- [ ] All features work (lineage, docs, etc.)
- [ ] Test on clean VM/machine
- [ ] Test with fresh configuration
- [ ] Check for data file dependencies
- [ ] Verify error messages are helpful
- [ ] Test ZIP extraction and run
- [ ] Document any known issues

### Test on Clean Machine

1. **Use a VM** or colleague's computer
2. **Extract ZIP** to `C:\Test\DatasphereTools\`
3. **Run Launch.bat**
4. **Expected behavior**:
   - Console window opens
   - "Starting application..." message
   - Browser opens to localhost:8501
   - Streamlit UI loads
5. **Test core features**:
   - Settings configuration
   - API connection
   - Database connection
   - Run a simple query/search

## Continuous Distribution

### Version Management

Update version in:
1. `build_executable.py` → `VERSION = "2.1.0"`
2. `Streamlit1/__init__.py` → `__version__ = "2.1.0"`
3. `CHANGELOG.md` → Add new version entry

### Automated Builds (Optional)

For frequent releases, create `build_and_distribute.bat`:

```batch
@echo off
echo Building Datasphere Tools...

REM Build executable
python build_executable.py

REM Copy to distribution folder
set DIST_FOLDER=\\shared\drive\DatasphereTools
copy DatasphereTools_v*.zip "%DIST_FOLDER%\"

echo.
echo Distribution complete!
pause
```

## Summary

**Recommended Workflow**:

1. **Development**: Use `run.bat` for testing
2. **Before Release**: Run `python build_executable.py`
3. **Test**: Extract ZIP and verify on clean machine
4. **Distribute**: Share ZIP with users
5. **Support**: Provide README and quick start guide

**Key Files**:
- `build_executable.py` - Automated build script
- `BUILD_EXECUTABLE_GUIDE.md` - This guide
- `dist/DatasphereTools/` - Built application
- `DatasphereTools_v2.0.0_YYYYMMDD.zip` - Distribution package

---

**Need Help?**

Contact: Delaware Datasphere Team
