"""
Configuration Helper Utilities for SAP Datasphere Tools.

Provides backward-compatible access to configuration from either:
- V2: app_config object (new encrypted config)
- V1: Direct session state keys (legacy)
"""

import streamlit as st
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)


def get_credentials_from_session() -> Dict[str, Optional[str]]:
    """
    Get credentials from session state with V2/V1 fallback.

    Returns dict with keys: dsp_host, dsp_space, token, secret, client_id, client_secret

    Returns:
        Dictionary with credential values (may contain None for missing values)
    """
    # Try V2 config first (new encrypted config)
    if 'app_config' in st.session_state:
        config = st.session_state['app_config']

        return {
            'dsp_host': config.dsp_host if hasattr(config, 'dsp_host') else None,
            'dsp_space': config.dsp_space if hasattr(config, 'dsp_space') else None,
            'token': config.access_token if hasattr(config, 'access_token') else None,
            'secret': config.client_secret if hasattr(config, 'client_secret') else None,
            'client_id': config.client_id if hasattr(config, 'client_id') else None,
            'client_secret': config.client_secret if hasattr(config, 'client_secret') else None,
        }

    # Fallback to V1 session state keys (legacy)
    return {
        'dsp_host': st.session_state.get('dsp_host'),
        'dsp_space': st.session_state.get('dsp_space'),
        'token': st.session_state.get('token'),
        'secret': st.session_state.get('secret'),
        'client_id': st.session_state.get('client_id'),
        'client_secret': st.session_state.get('secret'),  # V1 used 'secret' for client_secret
    }


def get_dsp_host() -> Optional[str]:
    """Get Datasphere host URL from session."""
    creds = get_credentials_from_session()
    return creds['dsp_host']


def get_access_token() -> Optional[str]:
    """Get OAuth access token from session."""
    creds = get_credentials_from_session()
    return creds['token']


def get_client_secret() -> Optional[str]:
    """Get OAuth client secret from session."""
    creds = get_credentials_from_session()
    return creds['secret']


def get_dsp_space() -> Optional[str]:
    """Get default Datasphere space from session."""
    creds = get_credentials_from_session()
    return creds['dsp_space']


def is_config_available() -> bool:
    """
    Check if configuration is available (either V2 or V1).

    Returns:
        True if minimum required credentials are present
    """
    creds = get_credentials_from_session()

    # Need at minimum: dsp_host and token
    return bool(creds.get('dsp_host') and creds.get('token'))


def get_app_config():
    """
    Get the AppConfig object if using V2, otherwise None.

    Returns:
        AppConfig object or None if using V1
    """
    return st.session_state.get('app_config')
