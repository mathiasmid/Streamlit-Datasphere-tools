import streamlit as st
import requests
from . import utils
import json
import pandas as pd
from datetime import datetime
import zipfile
import io

# Import cache manager and config helpers
try:
    from Streamlit1 import cache_manager as cm
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


def init_export_session_state():
    """Initialize session state variables for export functionality"""
    if 'export_selected_spaces' not in st.session_state:
        st.session_state.export_selected_spaces = []
    if 'export_selected_objects' not in st.session_state:
        st.session_state.export_selected_objects = []
    if 'export_object_list' not in st.session_state:
        st.session_state.export_object_list = []


def get_all_spaces():
    """Get list of all spaces in the tenant with caching"""
    if CACHE_AVAILABLE and cm.CacheManager.is_cache_loaded():
        spaces = cm.get_list_of_space_cached()
        return [space[0] for space in spaces]
    
    # Fallback without caching
    creds = get_credentials_from_session()
    header = utils.initializeGetOAuthSession(creds['token'], creds['secret'])
    url = utils.get_url(creds['dsp_host'], 'list_of_spaces')
    
    try:
        response = requests.get(url, headers=header)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Failed to fetch spaces: {response.status_code}")
            return []
    except Exception as e:
        st.error(f"Error fetching spaces: {e}")
        return []


def get_all_objects(space_id, limit=250):
    """Get all objects from a space using cache"""
    if CACHE_AVAILABLE and cm.CacheManager.is_cache_loaded():
        # Get all cached objects and filter by space_id
        all_objects = cm.get_all_objects_cached()
        filtered = [obj for obj in all_objects if obj.get('space_id') == space_id]
        return filtered[:limit]

    # Fallback - fetch directly
    return get_all_objects_direct(space_id, limit)


def get_all_objects_direct(space_id, limit=250):
    """Fetch objects directly from API (used by cache and as fallback)"""
    creds = get_credentials_from_session()
    header = utils.initializeGetOAuthSession(creds['token'], creds['secret'])
    url = utils.get_url(creds['dsp_host'], 'all_design_objects').format(**{"spaceID": space_id})

    try:
        response = requests.get(url, headers=header)

        if response.status_code == 200:
            data = response.json()
            objects = data.get('results', [])

            if not objects:
                st.warning(f"Space {space_id} returned no objects. The space might be empty.")
                return []

            # Limit to specified number of objects
            objects = objects[:limit]

            result = []
            for obj in objects:
                tech_name = obj.get('qualified_name', obj.get('name', ''))
                object_type = obj.get('kind', 'Unknown')

                result.append({
                    'technicalName': tech_name,
                    'object_type': object_type,
                    'space_id': space_id,
                    'object_name': tech_name
                })

            st.success(f"Successfully loaded {len(result)} objects from space {space_id}")
            return result
        else:
            st.error(f"API Error for space {space_id}: HTTP {response.status_code}")
            try:
                error_detail = response.json()
                st.error(f"Error details: {error_detail}")
            except:
                st.error(f"Response text: {response.text[:200]}")
            return []
    except Exception as e:
        st.error(f"Exception while fetching objects from space {space_id}: {type(e).__name__}: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        return []


def get_object_detail(space_id, object_name, object_type):
    """Get detailed JSON for a specific object"""
    creds = get_credentials_from_session()
    header = utils.initializeGetOAuthSession(creds['token'], creds['secret'])
    
    # Map 'kind' values to specific API types
    kind_to_api_type = {
        'sap.dwc.taskChain': 'taskchains',
        'sap.dis.transformationflow': 'transformation_flows',
        'sap.dis.dataflow': 'dataflows',
        'sap.dis.replicationflow': 'replication_flows',
    }
    
    # For 'entity' type, try to determine the actual type
    if object_type == 'entity':
        for api_type in ['views', 'local_tables', 'remote_tables', 'analytic_models']:
            detail = _try_fetch_object_detail(header, space_id, object_name, api_type)
            if detail:
                return detail
        return None
    
    # Map known types to API endpoints
    api_type = kind_to_api_type.get(object_type)
    if api_type:
        return _try_fetch_object_detail(header, space_id, object_name, api_type)
    
    # If we can't map the type, try to get the object using repository API
    try:
        creds = get_credentials_from_session()
        url = utils.get_url(creds['dsp_host'], 'all_design_objects').format(**{"spaceID": space_id})
        response = requests.get(url, headers=header)
        if response.status_code == 200:
            data = response.json()
            objects = data.get('results', [])
            for obj in objects:
                if obj.get('qualified_name') == object_name or obj.get('name') == object_name:
                    return obj
    except:
        pass
    return None


def _try_fetch_object_detail(header, space_id, object_name, api_type):
    """Helper function to try fetching object details from a specific API endpoint"""
    type_mapping = {
        'views': 'view_detail',
        'local_tables': 'local_table_detail',
        'remote_tables': 'remote_table_detail',
        'dataflows': 'data_flow_detail',
        'analytic_models': 'analytic_model_detail',
        'taskchains': 'task_chain_technical',
        'replication_flows': 'replication_flow_detail',
        'transformation_flows': 'transformation_flow_detail'
    }
    
    param_mapping = {
        'views': 'view',
        'local_tables': 'localtable',
        'remote_tables': 'remotetables',
        'dataflows': 'dataflow',
        'analytic_models': 'analyticmodel',
        'taskchains': 'technicalName',
        'replication_flows': 'replicationflow',
        'transformation_flows': 'technicalName'
    }
    
    endpoint_key = type_mapping.get(api_type)
    if not endpoint_key:
        return None
        
    param_name = param_mapping.get(api_type, 'objectName')

    try:
        creds = get_credentials_from_session()
        url = utils.get_url(creds['dsp_host'], endpoint_key).format(
            **{"spaceID": space_id, param_name: object_name}
        )
        response = requests.get(url, headers=header)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    
    return None


def export_objects_to_json(selected_objects, export_format='separate'):
    """Export selected objects to JSON format"""
    exported_files = {}
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for idx, obj in enumerate(selected_objects):
        space_id = obj['space_id']
        object_name = obj['object_name']
        object_type = obj['object_type']
        
        status_text.text(f"Exporting {object_name} ({idx + 1}/{len(selected_objects)})...")
        
        json_data = get_object_detail(space_id, object_name, object_type)
        
        if json_data:
            if export_format == 'separate':
                filename = f"{space_id}_{object_type}_{object_name}_{timestamp}.json"
                exported_files[filename] = json_data
            else:
                key = f"{space_id}_{object_type}_{object_name}"
                exported_files[key] = json_data
        
        progress_bar.progress((idx + 1) / len(selected_objects))
    
    status_text.text("Export completed!")
    progress_bar.empty()
    
    if export_format == 'combined':
        combined_filename = f"datasphere_export_{timestamp}.json"
        return {combined_filename: exported_files}
    
    return exported_files


def create_zip_download(exported_files):
    """Create a ZIP file containing all exported JSON files"""
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for filename, json_data in exported_files.items():
            json_string = json.dumps(json_data, indent=2, ensure_ascii=False)
            zip_file.writestr(filename, json_string)
    
    zip_buffer.seek(0)
    return zip_buffer


def get_objects_summary(selected_objects):
    """Create a summary DataFrame of selected objects"""
    summary_data = []
    
    for obj in selected_objects:
        summary_data.append({
            'Space': obj['space_id'],
            'Type': obj['object_type'],
            'Technical Name': obj['object_name']
        })
    
    return pd.DataFrame(summary_data)


def get_unique_object_types(objects):
    """Extract unique object types from the objects list for dynamic filtering"""
    types = set()
    for obj in objects:
        types.add(obj.get('object_type', 'Unknown'))
    
    return sorted(list(types))