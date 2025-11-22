# Changelog

All notable changes to SAP Datasphere Tools will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2025-01-22

### Added - Major Features
- **Lineage Analysis Engine**: Complete object lineage tracking with visual graph representation
  - Upstream and downstream dependency mapping
  - Multi-level lineage traversal
  - JSON export for external analysis
  - Interactive visualization with source/target filtering
- **Word Document Generator**: Automated technical documentation creation
  - Configurable templates for objects, spaces, and taskchains
  - Table of contents with hyperlinks
  - Formatted code blocks and metadata tables
  - Batch export capabilities
- **Enhanced Settings UI (V2)**: Modern configuration management
  - Encrypted credential storage
  - OAuth 2.0 integration with token refresh
  - Configuration import/export
  - Visual feedback and error handling
- **Pydantic Data Models**: Type-safe data structures for all API responses
- **Smart Caching System**: Performance optimization with automatic invalidation
- **Enhanced Error Handling**: Detailed error messages with retry logic
- **Export Objects**: JSON export for design objects with metadata

### Added - Infrastructure
- Modular architecture with separated concerns:
  - `api_client.py`: Centralized API client with retry logic
  - `db_client.py`: HANA database client with connection pooling
  - `config_manager_v2.py`: Encrypted configuration management
  - `cache_manager.py`: Intelligent caching layer
  - `error_handler.py`: Standardized error handling
  - `models.py`: Pydantic models for type safety
- Comprehensive documentation:
  - README.md with installation guide
  - QUICK_START.md for new users
  - MIGRATION_GUIDE.md for V1 to V2 transition
  - IMPLEMENTATION_SUMMARY.md with technical details
- Installation scripts for Windows and Mac/Linux
- Distribution packaging system

### Changed
- **Security**: Credentials now stored encrypted instead of plain text
- **Performance**: 10x faster object lookups with smart caching
- **UI/UX**: Modern Streamlit interface with better error messages
- **Code Quality**: Added type hints throughout codebase
- **OAuth**: Improved token management with automatic refresh

### Improved
- **Object Dependencies**: Faster lookup with caching
- **User Analytics**: Enhanced DAC (Data Access Control) analysis
- **Find Column**: Better search performance with result caching
- **Business Name Lookup**: Improved matching algorithm
- **Exposed Views**: More comprehensive security analysis

### Fixed
- OAuth token expiration handling
- Database connection timeout issues
- Memory leaks in long-running sessions
- Incorrect object type detection in some edge cases
- Cache invalidation on configuration changes

### Security
- Encrypted credential storage using Fernet encryption
- Secure token handling with automatic expiration
- Sensitive files excluded from version control
- Added .gitignore for security best practices
- Removed hardcoded credentials from test files

### Deprecated
- V1 Settings UI (replaced by Settings V2)
- Plain text configuration files (migrated to encrypted storage)
- Direct token file reading (now uses ConfigManager)

### Removed
- Legacy modules no longer in use:
  - `data_integration.py`
  - `database_tables.py`
  - `delete_objects.py`
  - `memory_usage.py`
  - `notifications.py`
  - `objects_in_taskchain.py`
  - `orphaned_objects.py`
  - `shares_per_space.py`
  - `system_monitor.py`
  - `taskchain_start.py`
  - `taskchainlogs.py`
  - `unused_objects.py`
  - `view_overview.py`

## [1.0.0] - 2024-XX-XX

### Initial Release
- Basic Datasphere object management
- Simple OAuth authentication
- User analytics
- Column search functionality
- Object dependency viewer
- Business name lookup
- Exposed views checker
- Documentation helper

---

## Migration Notes

### Upgrading from V1 to V2

1. **Configuration**: Run Settings V2 to migrate your credentials to encrypted storage
2. **Imports**: Update any custom scripts to use new module structure
3. **Features**: Review MIGRATION_GUIDE.md for detailed upgrade instructions

### Breaking Changes in V2.0.0

- Configuration file format changed (automatic migration available)
- Some module paths changed (e.g., `config_manager.py` → `config_manager_v2.py`)
- OAuth token handling restructured (seamless for end users)

---

## Planned for Future Releases

### [2.1.0] - Planned
- Advanced lineage visualization with interactive graphs
- Scheduled exports and automated reporting
- Enhanced documentation templates
- Performance monitoring dashboard
- Audit log viewer

### [2.2.0] - Planned
- Multi-tenant support
- REST API for external integrations
- Jupyter notebook integration
- Advanced search with filters
- Batch operations for multiple objects

---

**Note**: This project follows semantic versioning. For internal Delaware use only.
