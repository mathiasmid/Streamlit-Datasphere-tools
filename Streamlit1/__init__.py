"""
SAP Datasphere Tools - Core Package
Version 2.0.0

A comprehensive toolkit for SAP Datasphere administration and analysis.
Includes features for object lineage, documentation generation, user analytics,
and database management.
"""

__version__ = "2.0.0"
__author__ = "Tobias Meyer, Delaware Consulting"

# Export key classes and functions for easier imports
from .models import (
    DataspherConfig,
    OAuthConfig,
    HANAConfig,
    DesignObject,
    TaskChain,
    Lineage
)

from .api_client import DatasphereAPIClient
from .db_client import HANAClient
from .config_manager_v2 import ConfigManager
from .cache_manager import CacheManager
from .error_handler import handle_api_error, handle_db_error

__all__ = [
    '__version__',
    '__author__',
    'DataspherConfig',
    'OAuthConfig',
    'HANAConfig',
    'DesignObject',
    'TaskChain',
    'Lineage',
    'DatasphereAPIClient',
    'HANAClient',
    'ConfigManager',
    'CacheManager',
    'handle_api_error',
    'handle_db_error',
]
