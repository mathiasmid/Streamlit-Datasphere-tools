import json
import dsp_token
from json.decoder import JSONDecodeError
from datetime import datetime, timedelta
from hdbcli import dbapi
import requests
import streamlit as st

# Import cache manager and config helpers
try:
    from Streamlit1 import cache_manager
    from Streamlit1.config_helpers import get_credentials_from_session
    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False
    # Fallback if imports fail
    def get_credentials_from_session():
        return {
            'token': st.session_state.get('token'),
            'secret': st.session_state.get('secret'),
            'dsp_host': st.session_state.get('dsp_host')
        }


def get_url(dsp_url, url_name):
    f = open('url.json')
    urls = json.load(f)
    return urls[url_name].replace("#dsp_url", dsp_url)


def initializeGetOAuthSession(token_file, secrets_file):
    # Handle both V2 (string token) and V1 (dict token) formats
    if isinstance(token_file, str) and not token_file.endswith('.json'):
        # V2: token_file is already the access token string
        token = token_file
    else:
        # V1: token_file is either a dict or a path to token file
        token = ''
        expire = datetime(1970, 1, 1)
        token = token_file

        try:
            expire = datetime.strptime(token['expire'], "%Y-%m-%d %H:%M:%S")
        except (JSONDecodeError, TypeError, KeyError):
            pass

        if token == '':
            dsp_token.get_initial_token(secrets_file, token_file)
        else:
            if expire + timedelta(days=30) <= datetime.now():
                token = ''

            if expire <= datetime.now() and token == '':
                dsp_token.get_initial_token(secrets_file, token_file)

            token = dsp_token.refresh_token(secrets_file, token_file)

    header = {'authorization': "Bearer " + token,
              "accept": "application/vnd.sap.datasphere.object.content+json"}
    return header


def initializePutOAuthSession(token_file, secrets_file):
    # Handle both V2 (string token) and V1 (dict token) formats
    if isinstance(token_file, str) and not token_file.endswith('.json'):
        # V2: token_file is already the access token string
        token = token_file
    else:
        # V1: token_file is a path to token file
        token = ''
        expire = datetime(1970, 1, 1)
        f = open(token_file)

        try:
            token = json.load(f)
            expire = datetime.strptime(token['expire'], "%Y-%m-%d %H:%M:%S")
        except JSONDecodeError:
            pass

        if token == '':
            dsp_token.get_initial_token(secrets_file, token_file)
        else:
            token = dsp_token.refresh_token(secrets_file, token_file)

            if expire <= datetime.now() and token == '':
                dsp_token.get_initial_token(secrets_file, token_file)

    header = {'authorization': "Bearer " + token,
              "content-type": "application/json"}
    return header


def get_list_of_space():
    """Get list of spaces from database (direct query - no caching)"""
    # This function is called by cache_manager as a fallback
    # It should NOT call cache_manager to avoid infinite recursion
    query = f'''
        SELECT SPACE_ID
        FROM "DWC_TENANT_OWNER"."SPACE_SCHEMAS"
        WHERE SCHEMA_TYPE = 'space_schema';
    '''
    return database_connection(query)


def get_space_business_names():
    """Get space business names from API (direct call - no caching)"""
    # This function is called by cache_manager as a fallback
    # It should NOT call cache_manager to avoid infinite recursion
    creds = get_credentials_from_session()
    header = initializeGetOAuthSession(creds['token'], creds['secret'])
    url = get_url(creds['dsp_host'], "spaces_name")

    try:
        response = requests.get(url, headers=header)
        if response.status_code == 200:
            data = response.json()
            data = data['results']
            return {e["qualifiedName"]: e["businessName"] for e in data}
        else:
            st.error(f"Failed to fetch space names: {response.status_code}")
            return {}
    except Exception as e:
        st.error(f"Error fetching space names: {e}")
        return {}


def database_connection(query):
    try:
        # Get database credentials from V2 or V1 config
        if 'app_config' in st.session_state:
            # V2 config
            config = st.session_state['app_config']
            address = config.hdb_address
            port = config.hdb_port
            user = config.hdb_user
            password = config.hdb_password
        else:
            # V1 session state keys
            address = st.session_state.hdb_address
            port = st.session_state.hdb_port
            user = st.session_state.hdb_user
            password = st.session_state.hdb_password

        conn = dbapi.connect(
            address=address,
            port=int(port),
            user=user,
            password=password
        )
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()
        return rows
    except Exception as e:
        st.error(f"Database connection failed: {e}")
        return []
    

def create_config_template():
    data = """{
                "DATASPHERE": {
                "dsp_host": "https://hcs.cloud.sap"
            },
            "HDB": {
                "hdb_address": ".hana.prod-eu10.hanacloud.ondemand.com",
                "hdb_port": 443,
                "hdb_user": "#",
                "hdb_password": ""
            },
            "SETTINGS": {
                "secrets_file": "PATH_TO_secret.json",
                "token_file": "PATH_TO_token.json"
            }
            }"""
    return data


def create_secret_template():
    data = """{

  "client_id": "",
  "client_secret": "",
  "authorization_url": "",
  "token_url": ""

}"""
    return data