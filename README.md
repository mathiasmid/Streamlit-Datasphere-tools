# SAP Datasphere Tools

A comprehensive Streamlit application for managing and analyzing SAP Datasphere objects, with advanced lineage analysis and documentation generation capabilities.

## 🌟 Features

### Core Functionality
- **📊 Object Management** - Browse, search, and export Datasphere objects
- **🔗 Lineage Analysis** - Visualize complete object dependencies and data flows
- **📄 Documentation Generator** - Create Word documents from lineage with field mappings
- **🔍 Column Search** - Find column usage across all objects
- **👥 User Analytics** - Analyze user access and permissions
- **🏠 Housekeeping Tools** - DAC analysis, exposed views, orphaned objects

### Advanced Features
- **🔐 Encrypted Configuration** - Secure storage of credentials using Fernet encryption
- **⚡ Smart Caching** - Optional caching with global object/space dropdowns
- **🎯 Transactional Lineage** - Filter lineage to show only data-modifying objects
- **📝 Field-Level Documentation** - Complete CSN parsing with business names
- **🔄 Auto-Retry** - Robust API client with automatic retries and token refresh
- **📋 Activity Logging** - Track all operations with detailed logs

## 🚀 Quick Start

### Prerequisites
- Python 3.9 or higher
- SAP Datasphere access with OAuth credentials
- HANA database access (DWCDBUSER)

### Installation

#### Windows
```batch
# Double-click install.bat
# OR run in terminal:
install.bat
```

#### Mac/Linux
```bash
chmod +x install.sh run.sh
./install.sh
```

### Running the Application

#### Windows
```batch
# Double-click run.bat
# OR run in terminal:
run.bat
```

#### Mac/Linux
```bash
./run.sh
```

The application will open automatically in your browser at `http://localhost:8501`

## ⚙️ Configuration

### First Time Setup

1. **Run the application** using `run.bat` (Windows) or `./run.sh` (Mac/Linux)

2. **Go to Settings page** (in the sidebar)

3. **Configure SAP Datasphere connection:**
   - **Datasphere Host**: `https://your-tenant.hcs.cloud.sap`
   - **Default Space**: Optional default space ID

4. **Configure HANA Database:**
   - **Address**: `your-hana-address.hanacloud.ondemand.com`
   - **Port**: `443`
   - **User**: `DWCDBUSER#YOURUSER`
   - **Password**: Your database password

5. **Configure OAuth:**
   - **Client ID**: Your OAuth client ID
   - **Client Secret**: Your OAuth client secret
   - **Authorization URL**: `https://your-tenant.hcs.cloud.sap/oauth/authorize`
   - **Token URL**: `https://your-tenant.hcs.cloud.sap/oauth/token`

6. **Obtain OAuth Token:**
   - Click "Generate OAuth Token"
   - Follow the browser flow
   - Paste the authorization code back

7. **Test Connection:**
   - Click "Test API Connection"
   - Click "Test Database Connection"
   - Verify both are successful

8. **Save Configuration:**
   - Click "Save Configuration"
   - Configuration is encrypted and saved to disk

### Configuration Security

- All sensitive data (passwords, secrets, tokens) are **encrypted** using Fernet encryption
- Encryption key is automatically generated and stored in `.config_key` (hidden file)
- Configuration is saved in `saved_config.json` (encrypted format)
- **Never commit** `.config_key` or `saved_config.json` to version control

## 📖 Usage Guide

### Lineage Analyzer

1. **Navigate to** "Lineage Analyzer" in the sidebar

2. **Select Object:**
   - **Option A**: Load cache and select from dropdown
   - **Option B (Manual Entry)**:
     - Search by technical name (e.g., "02_DWH_CUBE_UNIVERSAL_LEDGER")
     - Optional: Specify space to limit search
     - Click "Find Object ID" to look up the ID
     - OR enter object ID directly if you know it

3. **Configure Options:**
   - ✅ **Recursive**: Include nested dependencies
   - ✅ **Include Impact**: Show impact analysis
   - ⚪ **Transactional Only**: Show only data flows

4. **Fetch Lineage:** Click "Fetch Lineage" button

5. **View Results:**
   - **Tree View**: Hierarchical dependency visualization
   - **Table View**: Flat list with filtering
   - **Analysis**: Statistics and metrics

6. **Export:**
   - Download full lineage as JSON
   - Download summary as CSV
   - Download transactional lineage only

### Documentation Generator

1. **Navigate to** "Documentation Generator"

2. **Choose Lineage Source:**
   - **Use Existing**: If you just viewed lineage
   - **Fetch New**: Select object and fetch

3. **Configure Content:**
   - ✅ **Include Field Mappings**: Add CSN field definitions
   - ✅ **Include Transformations**: Document flows
   - ⚪ **Transactional Only**: Focus on data flows

4. **Generate:** Click "Generate Documentation"

5. **Download:** Save the Word document

6. **Customize in Word:**
   - Open the document
   - Right-click Table of Contents → Update Field
   - Customize formatting as needed

## 🏗️ Architecture

### Technology Stack
- **Frontend**: Streamlit 1.30+
- **Data Validation**: Pydantic 2.5+
- **Security**: Cryptography (Fernet)
- **Database**: SAP HANA (hdbcli)
- **HTTP Client**: Requests with retry logic
- **Documentation**: python-docx

### Project Structure

```
streamlitv2/
├── Streamlit1/                    # Core modules
│   ├── models.py                  # Pydantic data models
│   ├── api_client.py              # SAP Datasphere API client
│   ├── db_client.py               # HANA database client
│   ├── config_manager_v2.py       # Encrypted config management
│   ├── cache_manager_v2.py        # Enhanced cache system
│   ├── error_handler.py           # Error handling utilities
│   ├── lineage.py                 # Lineage analysis
│   ├── lineage_ui.py              # Lineage visualization UI
│   ├── documentation_builder.py   # Word doc generation
│   ├── documentation_ui.py        # Documentation UI
│   └── ... (other modules)
├── streamlit_appV2.py             # Main application
├── requirements.txt               # Python dependencies
├── install.bat / install.sh       # Installation scripts
├── run.bat / run.sh               # Run scripts
└── README.md                      # This file
```

### Key Design Patterns

- **Repository Pattern**: API and DB clients encapsulate data access
- **Service Layer**: Business logic in dedicated service modules
- **Decorator Pattern**: Error handling, auth, logging via decorators
- **Context Managers**: Safe resource management (DB connections, files)
- **Type Safety**: Pydantic models with full validation
- **Fallback Architecture**: Features work with or without cache

## 🔧 Development

### Setting Up Development Environment

```bash
# Clone repository
git clone <repo-url>
cd streamlitv2

# Install dependencies (including dev tools)
pip install -r requirements.txt

# Run tests
pytest

# Code formatting
black Streamlit1/

# Type checking
mypy Streamlit1/

# Linting
pylint Streamlit1/
```

## 📋 Troubleshooting

### Common Issues

**Issue**: "Configuration not found"
- **Solution**: Go to Settings page and configure the application

**Issue**: "Token expired"
- **Solution**: Go to Settings → OAuth and refresh your token

**Issue**: "Database connection failed"
- **Solution**: Check HANA credentials and network access

**Issue**: "Cache loading failed"
- **Solution**: Verify API and database access, check logs in `app.log`

**Issue**: "Import errors" when running
- **Solution**: Make sure virtual environment is activated and all dependencies installed

### Logs

Application logs are written to:
- **File**: `app.log` (detailed logs)
- **Console**: Standard output (info level)
- **UI**: Activity log in sidebar (recent activities)

## 🔒 Security Best Practices

1. **Never commit** sensitive files:
   - `.config_key` (encryption key)
   - `saved_config.json` (encrypted config)
   - `secret.json`, `token.json` (legacy files)

2. **Add to .gitignore:**
   ```
   .config_key
   saved_config.json
   secret.json
   token.json
   config.json
   app.log
   venv/
   __pycache__/
   *.pyc
   ```

3. **Rotate credentials** regularly
4. **Use environment-specific** configurations

## 📝 License

[Add your license here]

## 📚 Additional Resources

- [SAP Datasphere Documentation](https://help.sap.com/docs/SAP_DATASPHERE)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [Pydantic Documentation](https://docs.pydantic.dev/)

---

**Version**: 2.0
**Last Updated**: 2025-01-15