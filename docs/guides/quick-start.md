# Quick Start Guide

Get up and running with SAP Datasphere Tools in 5 minutes!

## 📦 Installation (First Time Only)

### Windows
1. Double-click `install.bat`
2. Wait for installation to complete (~2-3 minutes)

### Mac/Linux
```bash
chmod +x install.sh run.sh
./install.sh
```

## 🚀 Running the Application

### Windows
Double-click `run.bat`

### Mac/Linux
```bash
./run.sh
```

The app opens automatically at: `http://localhost:8501`

## ⚙️ Initial Setup (5 Steps)

### Step 1: Open Settings V2
- Click **"Settings V2 (New)"** in the sidebar

### Step 2: Configure Datasphere & Database
Fill in the **Datasphere & Database** tab:
- **Datasphere Host**: `https://your-tenant.eu10.hcs.cloud.sap`
- **HANA Address**: `xyz.hana.prod-eu10.hanacloud.ondemand.com`
- **HANA Port**: `443`
- **HANA User**: `DWCDBUSER#YOURUSER`
- **HANA Password**: Your database password

### Step 3: Configure OAuth
Go to **OAuth Configuration** tab:
- **Client ID**: Your OAuth client ID
- **Client Secret**: Your OAuth client secret
- Click **"Auto-fill URLs from Host"** (if host is set)

### Step 4: Get OAuth Token
Go to **OAuth Token** tab:
1. Click **"Open Authorization URL"**
2. Log in to SAP Datasphere in browser
3. Authorize the application
4. Copy the authorization code from URL
5. Paste it back in the app
6. Click **"Exchange for Token"**

### Step 5: Save & Test
Go back to **Datasphere & Database** tab:
1. Click **"Test Database"** ✅
2. Click **"Test API Connection"** ✅
3. Click **"Save Configuration"** 💾

**Done!** Your configuration is encrypted and saved.

## 🎯 Try These Features

### 1. Load Cache (Optional, Recommended)
- Go to **Cache & Advanced** tab
- Click **"Load Cache"**
- Wait ~30-60 seconds
- Speeds up all operations 10x!

### 2. Analyze Lineage
- Go to **"Lineage Analyzer"** in Tools
- Load cache OR use manual entry:
  - Search by technical name (recommended)
  - OR enter object ID directly
- Click **"Fetch Lineage"**
- Explore tree/table views
- Export to JSON/CSV

### 3. Generate Documentation
- Go to **"Documentation Generator"** in Tools
- Use existing lineage OR fetch new
- Configure content options
- Click **"Generate Documentation"**
- Download Word document

### 4. Export Objects
- Go to **"Export Objects to JSON"** in Tools
- Select objects (filter by type/name)
- Choose format (separate/combined)
- Export and download ZIP

## 🔑 Important Files

### DO NOT Commit to Git
- `.config_key` - Encryption key (auto-generated)
- `saved_config.json` - Encrypted configuration
- `secret.json`, `token.json`, `config.json` - Legacy files

### Check .gitignore
Make sure these are ignored:
```gitignore
.config_key
saved_config.json
secret.json
token.json
config.json
```

## 🆘 Common Issues

### "Module not found" errors
**Solution:** Reinstall dependencies
```bash
pip install -r requirements.txt
```

### "Configuration not found"
**Solution:** Go to Settings V2 and configure

### "Token expired"
**Solution:**
- Settings V2 → OAuth Token tab
- Click "Refresh Token" OR generate new one

### "Database connection failed"
**Solution:**
- Verify credentials in Settings V2
- Click "Test Database" to diagnose
- Check VPN connection if required

## 💡 Pro Tips

1. **Always load cache first** - Makes everything 10x faster
2. **Use Settings V2** - Has encryption and better UX
3. **Test connections** before using tools
4. **Bookmark frequently used objects** - Note their IDs
5. **Export lineage to JSON** - Keep for documentation
6. **Generate docs regularly** - Keep documentation up to date

## 📖 Next Steps

- Read [README.md](README.md) for detailed documentation
- Read [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) if upgrading from V1
- Explore all tools in the sidebar
- Check logs in `app.log` if issues occur

## 🎉 You're Ready!

Start exploring your SAP Datasphere environment with powerful tools!

**Questions?** Contact your Delaware Datasphere team.
