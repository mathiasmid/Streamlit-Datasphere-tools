"""
Settings UI for SAP Datasphere Tools.

Provides configuration management with encryption, OAuth flow, and connection testing.
"""

import streamlit as st
import webbrowser
import requests
import urllib.parse
from datetime import datetime, timedelta
from typing import Optional

from .models import AppConfig
from .config_manager_v2 import ConfigManager
from .api_client import DataspherAPIClient
from .db_client import HANAClient
from .cache_manager import CacheManager
from .error_handler import (
    handle_errors, display_success, display_error,
    display_warning, display_info, ActivityLogger
)


@handle_errors(show_traceback=True)
def settings_page():
    """Main settings page with configuration management."""

    st.title("⚙️ Settings")
    st.markdown("Configure SAP Datasphere connection and credentials")

    # Initialize config manager
    config_manager = ConfigManager()

    # Load existing config if available
    if 'app_config' not in st.session_state:
        try:
            loaded_config = config_manager.load_config()
            if loaded_config:
                st.session_state['app_config'] = loaded_config
                display_info("Configuration loaded from disk")
        except Exception as e:
            display_warning(f"Could not load saved configuration: {str(e)}")

    # Tabs for different configuration sections
    tab1, tab2, tab3, tab4 = st.tabs([
        "🌐 Datasphere & Database",
        "🔐 OAuth Configuration",
        "🔑 OAuth Token",
        "💾 Cache & Advanced"
    ])

    # ==================== Tab 1: Datasphere & Database ====================
    with tab1:
        st.header("SAP Datasphere Connection")

        # Get current config or create default
        current_config = st.session_state.get('app_config')

        col1, col2 = st.columns([3, 1])

        with col1:
            dsp_host = st.text_input(
                "Datasphere Host URL",
                value=current_config.dsp_host if current_config else "",
                placeholder="https://your-tenant.eu10.hcs.cloud.sap",
                help="Full URL of your SAP Datasphere tenant"
            )

        with col2:
            dsp_space = st.text_input(
                "Default Space (optional)",
                value=current_config.dsp_space if current_config else "",
                placeholder="01_ACQUISITION",
                help="Default space ID for operations"
            )

        st.markdown("---")
        st.header("HANA Database Connection")

        col1, col2 = st.columns(2)

        with col1:
            hdb_address = st.text_input(
                "HANA Address",
                value=current_config.hdb_address if current_config else "",
                placeholder="xyz.hana.prod-eu10.hanacloud.ondemand.com",
                help="HANA Cloud database address"
            )

            hdb_user = st.text_input(
                "HANA User",
                value=current_config.hdb_user if current_config else "",
                placeholder="DWCDBUSER#USERNAME",
                help="Database user (usually DWCDBUSER#<username>)"
            )

        with col2:
            hdb_port = st.number_input(
                "HANA Port",
                value=current_config.hdb_port if current_config else 443,
                min_value=1,
                max_value=65535,
                help="Database port (usually 443)"
            )

            hdb_password = st.text_input(
                "HANA Password",
                value=current_config.hdb_password if current_config else "",
                type="password",
                help="Database password"
            )

        # Test database connection
        st.markdown("---")

        col1, col2, col3 = st.columns([1, 1, 2])

        with col1:
            if st.button("🧪 Test Database", use_container_width=True):
                if not all([hdb_address, hdb_user, hdb_password]):
                    display_error("Please fill in all database fields")
                else:
                    with st.spinner("Testing database connection..."):
                        try:
                            # Create temporary config for testing
                            test_config = AppConfig(
                                dsp_host=dsp_host or "https://placeholder.com",
                                hdb_address=hdb_address,
                                hdb_port=hdb_port,
                                hdb_user=hdb_user,
                                hdb_password=hdb_password,
                                client_id="test",
                                client_secret="test",
                                authorization_url="https://test.com",
                                token_url="https://test.com"
                            )

                            db_client = HANAClient(test_config)
                            result = db_client.test_connection()

                            if result['success']:
                                display_success(result['message'])
                                ActivityLogger.log("Database connection test successful", "success")
                            else:
                                display_error(result['message'])

                        except Exception as e:
                            display_error(f"Database test failed: {str(e)}")

    # ==================== Tab 2: OAuth Configuration ====================
    with tab2:
        st.header("OAuth Client Configuration")

        st.info("💡 These credentials are provided by your SAP Datasphere administrator")

        col1, col2 = st.columns(2)

        with col1:
            client_id = st.text_input(
                "Client ID",
                value=current_config.client_id if current_config else "",
                help="OAuth client ID"
            )

            authorization_url = st.text_input(
                "Authorization URL",
                value=current_config.authorization_url if current_config else "",
                placeholder="https://your-tenant.hcs.cloud.sap/oauth/authorize",
                help="OAuth authorization endpoint"
            )

        with col2:
            client_secret = st.text_input(
                "Client Secret",
                value=current_config.client_secret if current_config else "",
                type="password",
                help="OAuth client secret"
            )

            token_url = st.text_input(
                "Token URL",
                value=current_config.token_url if current_config else "",
                placeholder="https://your-tenant.hcs.cloud.sap/oauth/token",
                help="OAuth token endpoint"
            )

        # Auto-fill URLs button
        if st.button("🔧 Auto-fill URLs from Host"):
            if dsp_host:
                authorization_url = f"{dsp_host}/oauth/authorize"
                token_url = f"{dsp_host}/oauth/token"
                st.rerun()

    # ==================== Tab 3: OAuth Token ====================
    with tab3:
        st.header("OAuth Token Management")

        # Check if we have a token
        has_token = current_config and current_config.access_token

        if has_token and current_config.is_token_valid():
            st.success("✅ Valid OAuth token available")

            col1, col2, col3 = st.columns(3)

            with col1:
                if current_config.token_expire_time:
                    time_left = current_config.token_expire_time - datetime.now()
                    hours_left = time_left.total_seconds() / 3600
                    st.metric("Token Valid For", f"{hours_left:.1f} hours")

            with col2:
                st.metric("Token Status", "Valid ✅")

            with col3:
                if st.button("🔄 Refresh Token"):
                    with st.spinner("Refreshing token..."):
                        try:
                            api_client = DataspherAPIClient(current_config)
                            api_client.refresh_token()

                            # Update config in session
                            st.session_state['app_config'] = api_client.config

                            display_success("Token refreshed successfully!")
                            st.rerun()

                        except Exception as e:
                            display_error(f"Token refresh failed: {str(e)}")

        elif has_token:
            st.warning("⚠️ OAuth token has expired")
            st.info("Please generate a new token below")

        else:
            st.info("ℹ️ No OAuth token configured")

        st.markdown("---")
        st.subheader("Generate New Token")

        # Check if OAuth config is complete
        if not all([client_id, client_secret, authorization_url, token_url]):
            st.warning("⚠️ Please complete OAuth configuration in the OAuth Configuration tab first")
        else:
            st.markdown("""
            **Steps to generate OAuth token:**
            1. Click "Open Authorization URL" below
            2. Log in to SAP Datasphere in the browser
            3. Authorize the application
            4. After authorization, you'll be redirected to a URL containing a `code` parameter
            5. Copy the entire code value (between `code=` and `&` or end of URL)
            6. Paste it below and click "Exchange for Token"

            **Note:** If you get a "bad request" or redirect error in the browser, that's expected!
            Just copy the code from the URL bar anyway.
            """)

            # Generate authorization URL with proper encoding
            client_id_encoded = urllib.parse.quote(client_id)
            auth_url_full = f"{authorization_url}?response_type=code&client_id={client_id_encoded}"

            col1, col2 = st.columns([2, 1])

            with col1:
                st.code(auth_url_full, language="text")

            with col2:
                if st.button("🌐 Open Authorization URL", use_container_width=True):
                    webbrowser.open(auth_url_full)
                    display_info("Authorization URL opened in browser")

            # Code exchange
            auth_code = st.text_input(
                "Authorization Code",
                placeholder="Paste the code from the URL after authorization",
                help="Copy the 'code' parameter from the URL after authorizing"
            )

            if st.button("🔐 Exchange for Token", type="primary"):
                if not auth_code:
                    display_error("Please enter the authorization code")
                else:
                    with st.spinner("Exchanging code for token..."):
                        try:
                            # Exchange authorization code for access token
                            session = requests.session()
                            response = session.post(
                                token_url,
                                auth=(client_id, client_secret),
                                headers={
                                    "x-sap-sac-custom-auth": "true",
                                    "content-type": "application/x-www-form-urlencoded",
                                    "redirect_uri": "http://localhost"
                                },
                                data={
                                    'grant_type': 'authorization_code',
                                    'code': auth_code,
                                    'response_type': 'token'
                                },
                                timeout=30
                            )

                            if response.status_code == 200:
                                token_data = response.json()

                                # Calculate expiry time
                                expire_time = datetime.now()
                                if 'expires_in' in token_data:
                                    expire_time = expire_time + timedelta(seconds=token_data['expires_in'])

                                # Create/update config
                                new_config = AppConfig(
                                    dsp_host=dsp_host,
                                    dsp_space=dsp_space,
                                    hdb_address=hdb_address,
                                    hdb_port=hdb_port,
                                    hdb_user=hdb_user,
                                    hdb_password=hdb_password,
                                    client_id=client_id,
                                    client_secret=client_secret,
                                    authorization_url=authorization_url,
                                    token_url=token_url,
                                    access_token=token_data.get('access_token'),
                                    refresh_token=token_data.get('refresh_token'),
                                    token_expires_in=token_data.get('expires_in', 3600),
                                    token_expire_time=expire_time
                                )

                                st.session_state['app_config'] = new_config

                                display_success("✅ Token obtained successfully!")
                                ActivityLogger.log("OAuth token obtained", "success")
                                st.rerun()
                            else:
                                error_msg = f"Token exchange failed with status {response.status_code}"
                                try:
                                    error_data = response.json()
                                    if 'error_description' in error_data:
                                        error_msg += f": {error_data['error_description']}"
                                    elif 'error' in error_data:
                                        error_msg += f": {error_data['error']}"
                                except:
                                    error_msg += f": {response.text[:200]}"
                                display_error(error_msg)

                        except requests.exceptions.RequestException as e:
                            display_error(f"Token exchange request failed: {str(e)}")
                        except Exception as e:
                            display_error(f"Token exchange failed: {str(e)}")

        # Test API connection
        if has_token and current_config.is_token_valid():
            st.markdown("---")

            if st.button("🧪 Test API Connection", use_container_width=True):
                with st.spinner("Testing API connection..."):
                    try:
                        api_client = DataspherAPIClient(current_config)
                        result = api_client.test_connection()

                        if result['success']:
                            display_success(result['message'])
                            ActivityLogger.log("API connection test successful", "success")
                        else:
                            display_error(result['message'])

                    except Exception as e:
                        display_error(f"API test failed: {str(e)}")

    # ==================== Tab 4: Cache & Advanced ====================
    with tab4:
        st.header("Cache Management")

        CacheManager.initialize_cache()
        metadata = CacheManager.get_cache_metadata()

        # Cache status
        col1, col2, col3 = st.columns(3)

        with col1:
            status = "✅ Loaded" if metadata.loaded else "❌ Not Loaded"
            st.metric("Cache Status", status)

        with col2:
            st.metric("Objects Cached", metadata.object_count)

        with col3:
            if metadata.timestamp:
                age = metadata.age_minutes()
                st.metric("Cache Age", f"{age:.0f} min" if age else "N/A")

        # Show detailed cache statistics table if cache is loaded
        if metadata.loaded:
            st.markdown("---")
            st.subheader("📊 Cache Details by Space")

            # Get space statistics from session state
            space_stats = st.session_state.get(CacheManager.SPACE_STATS_KEY, {})
            space_names = st.session_state.get(CacheManager.SPACES_NAMES_KEY, {})

            if space_stats:
                import pandas as pd

                # Build table data
                table_data = []
                total_objects = 0
                successful_count = 0
                failed_count = 0

                for space_id, stats in space_stats.items():
                    business_name = space_names.get(space_id, "")
                    status = stats.get('status', 'unknown')
                    object_count = stats.get('object_count', 0)
                    error = stats.get('error', '')

                    # Count successes and failures
                    if status == 'success':
                        successful_count += 1
                        total_objects += object_count
                    else:
                        failed_count += 1

                    # Status emoji
                    status_icon = "✅" if status == 'success' else "❌"

                    table_data.append({
                        'Status': status_icon,
                        'Space ID': space_id,
                        'Business Name': business_name,
                        'Objects': object_count,
                        'Error': error if error else ""
                    })

                # Create DataFrame
                df = pd.DataFrame(table_data)

                # Sort by status (success first) then by object count (descending)
                df['_sort_status'] = df['Status'].map({'✅': 0, '❌': 1})
                df = df.sort_values(['_sort_status', 'Objects'], ascending=[True, False])
                df = df.drop(columns=['_sort_status'])

                # Display summary metrics
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Spaces", len(space_stats))
                with col2:
                    st.metric("✅ Successful", successful_count)
                with col3:
                    st.metric("❌ Failed", failed_count)
                with col4:
                    st.metric("Total Objects", total_objects)

                # Display table
                st.dataframe(
                    df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        'Status': st.column_config.TextColumn('Status', width='small'),
                        'Space ID': st.column_config.TextColumn('Space ID', width='medium'),
                        'Business Name': st.column_config.TextColumn('Business Name', width='medium'),
                        'Objects': st.column_config.NumberColumn('Objects', width='small'),
                        'Error': st.column_config.TextColumn('Error', width='large')
                    }
                )

                # Add expandable section for details
                with st.expander("📋 View Recent Cache Loading Details"):
                    details = st.session_state.get(CacheManager.PROGRESS_DETAIL_KEY, [])
                    if details:
                        for detail in reversed(details[-20:]):  # Show last 20, most recent first
                            st.text(detail)
                    else:
                        st.info("No details available")

        st.markdown("---")

        # Cache controls
        col1, col2 = st.columns(2)

        with col1:
            if st.button("🔄 Load Cache", use_container_width=True):
                if not st.session_state.get('app_config'):
                    display_error("Please save configuration first")
                else:
                    config = st.session_state['app_config']

                    # Check if token is valid
                    if not config.access_token:
                        display_error("No OAuth token found. Please generate a token in the OAuth Token tab.")
                    elif not config.is_token_valid():
                        display_error("OAuth token has expired. Please refresh the token in the OAuth Token tab.")
                    else:
                        # Start loading
                        with st.spinner("Loading cache..."):
                            try:
                                success = CacheManager.load_cache(config)

                                if success:
                                    display_success("Cache loaded successfully!")
                                    st.rerun()
                                else:
                                    metadata = CacheManager.get_cache_metadata()
                                    if metadata.error:
                                        display_error(f"Cache loading failed: {metadata.error}")
                                    else:
                                        display_error("Cache loading failed. Check logs for details.")
                            except Exception as e:
                                display_error(f"Cache loading error: {str(e)}")

        with col2:
            if st.button("🗑️ Clear Cache", use_container_width=True):
                CacheManager.clear_cache()
                display_info("Cache cleared")
                st.rerun()

        # Show loading progress if loading
        if metadata.loading:
            progress = st.session_state.get(CacheManager.PROGRESS_KEY, 0)
            message = st.session_state.get(CacheManager.PROGRESS_MSG_KEY, "Loading...")

            st.progress(progress / 100, text=message)

            # Auto-refresh while loading
            import time
            time.sleep(2)
            st.rerun()

        st.markdown("---")
        st.header("Advanced Settings")

        # Configuration file management
        col1, col2 = st.columns(2)

        with col1:
            if st.button("📥 Export Config Template", use_container_width=True):
                if config_manager.export_template("config_template.json"):
                    display_success("Template exported to config_template.json")

        with col2:
            if st.button("🗑️ Delete Saved Config", use_container_width=True):
                if config_manager.delete_config():
                    st.session_state.pop('app_config', None)
                    display_info("Configuration deleted")
                    st.rerun()

    # ==================== Save Configuration ====================
    st.markdown("---")
    st.header("💾 Save Configuration")

    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        if st.button("💾 Save Configuration", type="primary", use_container_width=True):
            # Validate required fields
            if not all([dsp_host, hdb_address, hdb_user, hdb_password, client_id, client_secret]):
                display_error("Please fill in all required fields")
            else:
                try:
                    # Create config object
                    config = AppConfig(
                        dsp_host=dsp_host,
                        dsp_space=dsp_space or None,
                        hdb_address=hdb_address,
                        hdb_port=hdb_port,
                        hdb_user=hdb_user,
                        hdb_password=hdb_password,
                        client_id=client_id,
                        client_secret=client_secret,
                        authorization_url=authorization_url,
                        token_url=token_url,
                        access_token=current_config.access_token if current_config else None,
                        refresh_token=current_config.refresh_token if current_config else None,
                        token_expires_in=current_config.token_expires_in if current_config else None,
                        token_expire_time=current_config.token_expire_time if current_config else None
                    )

                    # Save to disk
                    if config_manager.save_config(config):
                        st.session_state['app_config'] = config
                        display_success("✅ Configuration saved successfully (encrypted)")
                        ActivityLogger.log("Configuration saved", "success")
                    else:
                        display_error("Failed to save configuration")

                except Exception as e:
                    display_error(f"Failed to create configuration: {str(e)}")

    with col2:
        if st.button("🔄 Reset Form", use_container_width=True):
            st.session_state.pop('app_config', None)
            display_info("Form reset")
            st.rerun()

    with col3:
        config_exists = config_manager.config_exists()
        status_text = "✅ Saved" if config_exists else "❌ Not Saved"
        st.metric("Status", status_text)

    # Security notice
    st.markdown("---")
    st.info("""
    🔒 **Security Notice**
    - All sensitive data (passwords, secrets, tokens) are encrypted using Fernet encryption
    - Configuration is saved to `saved_config.json` (encrypted format)
    - Encryption key is stored in `.config_key` (auto-generated, hidden file)
    - **Never commit** these files to version control
    """)

    # Show activity log
    ActivityLogger.display()


if __name__ == "__main__":
    settings_page()
