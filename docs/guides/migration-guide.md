# Migration Guide: V1 to V2

This guide helps you migrate from the legacy settings to the new V2 architecture with encrypted configuration.

## What's New in V2?

### 🔐 Encrypted Configuration
- All sensitive data (passwords, secrets, tokens) encrypted using Fernet encryption
- Single unified configuration file (`saved_config.json`)
- No more separate `secret.json` and `token.json` files
- Auto-generated encryption key (`.config_key`)

### 🔗 Lineage Analyzer
- Complete object dependency visualization
- Transactional lineage filtering
- Tree and table views
- Export to JSON/CSV

### 📄 Documentation Generator
- Generate Word documents from lineage
- Field-level CSN metadata
- Professional formatting
- One-click download

### ⚡ Enhanced Architecture
- Type-safe models with Pydantic
- Robust error handling
- Auto-retry with exponential backoff
- Context managers for resource safety
- Comprehensive logging

## Migration Steps

### Option 1: Fresh Start (Recommended)

1. **Backup your existing configuration**
   ```bash
   # Backup existing files
   copy saved_config.json saved_config.json.backup
   copy secret.json secret.json.backup
   copy token.json token.json.backup
   ```

2. **Use Settings V2**
   - Go to "Settings V2 (New)" in the navigation
   - Fill in your credentials manually OR
   - Use the automatic migration (see Option 2)

3. **Save configuration**
   - Click "Save Configuration"
   - Configuration will be encrypted automatically

4. **Verify**
   - Check that `saved_config.json` contains encrypted data
   - Check that `.config_key` file was created (hidden file)

### Option 2: Automatic Migration

The new config manager can automatically migrate from legacy files:

1. **Ensure legacy files exist:**
   - `config.json` - Datasphere and database settings
   - `secret.json` - OAuth credentials
   - `token.json` - OAuth token

2. **Run migration:**
   ```python
   from Streamlit1.config_manager_v2 import migrate_legacy_config

   # This will automatically detect and migrate legacy files
   success = migrate_legacy_config()
   ```

3. **Legacy files will be backed up:**
   - `config.json.backup`
   - `secret.json.backup`
   - `token.json.backup`

4. **New encrypted config created:**
   - `saved_config.json` (encrypted)
   - `.config_key` (encryption key, hidden)

### Option 3: Manual Configuration

1. **Go to Settings V2 page**

2. **Fill in Datasphere & Database tab:**
   - Datasphere Host URL
   - HANA database credentials

3. **Fill in OAuth Configuration tab:**
   - Client ID and Client Secret
   - Authorization and Token URLs
   - (Tip: Use "Auto-fill URLs from Host" button)

4. **OAuth Token tab:**
   - Click "Open Authorization URL"
   - Log in and authorize
   - Copy the authorization code
   - Paste and click "Exchange for Token"

5. **Save Configuration:**
   - Go back to first tab
   - Click "Save Configuration"

## Feature Comparison

| Feature | Legacy | V2 |
|---------|--------|-----|
| **Configuration Storage** | Plain text JSON | Encrypted JSON |
| **Files Required** | 3 files (config, secret, token) | 1 file (saved_config.json) |
| **Token Management** | Manual upload each session | Stored encrypted, auto-refresh |
| **Settings UI** | File upload based | Forms + file upload |
| **Connection Testing** | None | Built-in API & DB tests |
| **Cache Management** | Manual via Settings | Integrated with progress tracking |
| **Lineage Analysis** | Basic documentation helper | Advanced lineage analyzer |
| **Documentation** | Limited | Full Word document generation |
| **Error Handling** | Basic | Comprehensive with logging |
| **Type Safety** | None | Full Pydantic validation |

## Using New Features

### Lineage Analyzer

1. **Navigate to "Lineage Analyzer"**

2. **Select object:**
   - Load cache for dropdown selection, OR
   - Enter object ID manually

3. **Configure options:**
   - Recursive dependencies
   - Transactional only filter
   - Display mode (tree/table)

4. **View and export:**
   - Analyze statistics
   - Export to JSON/CSV

### Documentation Generator

1. **Navigate to "Documentation Generator"**

2. **Choose lineage source:**
   - Use existing (if you just viewed lineage), OR
   - Fetch new lineage

3. **Configure content:**
   - Include field mappings
   - Include transformations
   - Transactional only

4. **Generate and download:**
   - Click "Generate Documentation"
   - Download Word document
   - Customize in Microsoft Word

## Security Considerations

### Encryption Details

- **Algorithm:** Fernet (symmetric encryption)
- **Key Storage:** `.config_key` file (hidden, auto-generated)
- **What's Encrypted:**
  - Database passwords
  - OAuth client secrets
  - OAuth tokens (access & refresh)

### Best Practices

1. **Never commit these files:**
   ```gitignore
   .config_key
   saved_config.json
   secret.json
   token.json
   config.json
   *.backup
   ```

2. **Protect encryption key:**
   - Keep `.config_key` secure
   - Losing it means losing access to encrypted config
   - Back it up separately if needed

3. **Rotate credentials regularly:**
   - Update passwords periodically
   - Refresh OAuth tokens
   - Re-save configuration after updates

## Troubleshooting

### "Import errors" when running

**Problem:** New modules not found

**Solution:**
```bash
# Reinstall dependencies
pip install -r requirements.txt

# Or manually install missing packages
pip install pydantic cryptography python-docx
```

### "Configuration not found"

**Problem:** No saved configuration

**Solution:**
- Go to Settings V2 and configure from scratch, OR
- Run automatic migration if you have legacy files

### "Token expired"

**Problem:** OAuth token no longer valid

**Solution:**
- Go to Settings V2 → OAuth Token tab
- Click "Refresh Token" (if you have refresh token), OR
- Generate new token via OAuth flow

### "Database connection failed"

**Problem:** Cannot connect to HANA

**Solution:**
- Verify database credentials in Settings V2
- Click "Test Database" button
- Check network connectivity
- Verify VPN connection if required

### "Decryption failed"

**Problem:** Encryption key mismatch

**Solution:**
- Check that `.config_key` file exists
- Don't mix config files from different systems
- Re-configure from scratch if key is lost

## Backward Compatibility

### Legacy Settings Still Available

The legacy settings page ("Settings (Legacy)") remains available for:
- Users who need gradual migration
- Compatibility with existing workflows
- Reference for configuration structure

### Gradual Migration Approach

You can use both legacy and V2 settings simultaneously:
1. Keep using legacy for existing workflows
2. Test V2 features with new configurations
3. Migrate fully when comfortable

### Legacy Features Still Work

All existing tools continue to work:
- Export Objects to JSON
- Documentation Helper (Legacy)
- Find Object Dependencies
- Column Search
- Business Names
- Exposed Views
- User Overview

## FAQ

**Q: Do I need to migrate immediately?**
A: No, legacy settings still work. Migrate when ready.

**Q: Can I use both legacy and V2 settings?**
A: Yes, but V2 is recommended for new configurations.

**Q: What happens to my existing config files?**
A: They're backed up during automatic migration (.backup files).

**Q: Is encryption mandatory?**
A: Yes, in V2. All sensitive data is encrypted automatically.

**Q: Can I export my configuration?**
A: Yes, but it will be encrypted. Keep the `.config_key` file safe.

**Q: How do I share configuration across machines?**
A: Copy both `saved_config.json` AND `.config_key` files.

**Q: What if I lose the encryption key?**
A: You'll need to reconfigure from scratch. Back up the key separately.

## Getting Help

If you encounter issues:

1. **Check logs:** Look in `app.log` for detailed error messages
2. **Test connections:** Use built-in test buttons in Settings V2
3. **Review documentation:** See README.md for detailed guides
4. **Reset if needed:** Delete `saved_config.json` and `.config_key`, start fresh

## Summary

### Quick Migration Checklist

- [ ] Backup existing configuration files
- [ ] Go to Settings V2 page
- [ ] Configure Datasphere & Database credentials
- [ ] Configure OAuth settings
- [ ] Generate/refresh OAuth token
- [ ] Save configuration
- [ ] Verify `.config_key` file created
- [ ] Test API connection
- [ ] Test Database connection
- [ ] Load cache (optional)
- [ ] Try new features (Lineage, Documentation)
- [ ] Add new files to .gitignore

### Files to Ignore in Git

```gitignore
# Encryption and configuration
.config_key
saved_config.json

# Legacy files (if migrating)
config.json
secret.json
token.json
*.backup

# Logs
app.log

# Python
venv/
__pycache__/
*.pyc
```

---

**Need Help?** Contact your Delaware Datasphere team for assistance.
