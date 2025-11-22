import pandas as pd
import streamlit as st
from . import utils
import json
import requests
from Streamlit1.config_helpers import get_credentials_from_session


def derive_space_from_object_name(object_name):
    """
    Derive the space ID from the object naming convention
    
    Objects are named with prefixes that map to spaces:
    - 01_ACQ* → 01_ACQUISITION
    - 02_DWH* → 02_DATAWAREHOUSE
    - 03_SAL* → 03_SALES
    - 03_FIN* → 03_FINANCE
    - 04_PBI* → 04_POWERBI
    
    Parameters:
    - object_name: Technical name of the object
    
    Returns:
    - Tuple: (space_id, prefix) if pattern matches, (None, None) otherwise
    """
    # Define prefix to space mapping
    prefix_to_space = {
        '01_ACQ': '01_ACQUISITION',
        '02_DWH': '02_DATAWAREHOUSE',
        '03_SAL': '03_SALES',
        '03_FIN': '03_FINANCE',
        '04_PBI': '04_POWERBI'
    }
    
    # Check each prefix
    for prefix, space in prefix_to_space.items():
        if object_name.startswith(prefix):
            return space, prefix
    
    # No matching prefix found
    return None, None


def search_object(object_name, space_id):
    """
    Search for an object in a specific space and get its details

    Parameters:
    - object_name: Technical name of the object to search for
    - space_id: The space ID where the object exists

    Returns:
    - Dictionary with object details or None if not found
    """
    # Get credentials from V2 app_config or V1 session state
    creds = get_credentials_from_session()
    header = utils.initializeGetOAuthSession(creds['token'], creds['secret'])

    # Try to get all design objects and find the matching one
    url = utils.get_url(creds['dsp_host'], 'all_design_objects').format(**{"spaceID": space_id})
    
    try:
        response = requests.get(url, headers=header)
        if response.status_code == 200:
            data = response.json()
            objects = data.get('results', [])
            
            # Search for the object by technical name
            for obj in objects:
                qualified_name = obj.get('qualified_name', obj.get('name', ''))
                if qualified_name == object_name or obj.get('name') == object_name:
                    return {
                        'id': obj.get('id'),
                        'technicalName': qualified_name,
                        'businessName': obj.get('business_name', ''),
                        'type': obj.get('kind', 'Unknown'),
                        'space_id': space_id
                    }
        return None
    except Exception as e:
        st.error(f"Error searching for object: {e}")
        return None


def search_object_smart(object_name, space_filter=None):
    """
    Smart search that derives space from object name or uses provided space
    
    Parameters:
    - object_name: Technical name of the object to search for
    - space_filter: Optional space ID to search in
    
    Returns:
    - Tuple: (object_info, derived_space, needs_space_input)
    """
    # If space is provided, use it
    if space_filter:
        obj_info = search_object(object_name, space_filter)
        return obj_info, space_filter, False
    
    # Try to derive space from object name
    derived_space, prefix = derive_space_from_object_name(object_name)
    
    if derived_space:
        # Found a matching prefix, search in that space
        obj_info = search_object(object_name, derived_space)
        return obj_info, derived_space, False
    else:
        # No prefix match, need user to provide space
        return None, None, True


def get_business_and_technical_names(artifact, space_id):
    """
    Get business and technical field names from CSN definition with extended metadata
    
    Parameters:
    - artifact: Technical name of the artifact
    - space_id: The space ID
    
    Returns:
    - DataFrame with Field, Description, Key, Type, Length, and Measure columns
    """
    query = f'''
        SELECT A.CSN
        FROM "{space_id}$TEC"."$$DEPLOY_ARTIFACTS$$" A
        INNER JOIN (
          SELECT ARTIFACT_NAME, MAX(ARTIFACT_VERSION) AS MAX_ARTIFACT_VERSION
          FROM "{space_id}$TEC"."$$DEPLOY_ARTIFACTS$$"
          WHERE SCHEMA_NAME = '{space_id}' AND ARTIFACT_NAME = '{artifact}'
          GROUP BY ARTIFACT_NAME
        ) B
        ON A.ARTIFACT_NAME = B.ARTIFACT_NAME
        AND A.ARTIFACT_VERSION = B.MAX_ARTIFACT_VERSION;
    '''
    
    try:
        csn_files = utils.database_connection(query)
        
        if not csn_files:
            return pd.DataFrame(columns=['Field', 'Description', 'Key', 'Type', 'Length', 'Measure'])
        
        for csn in csn_files:
            csn = csn[0]
            csn_loaded = json.loads(csn)
            objectName = list(csn_loaded['definitions'].keys())[0]
            
            # Get elements (fields)
            elements = csn_loaded["definitions"][objectName].get("elements", {})
            
            result = []
            for key, val in elements.items():
                # Get basic info
                description = val.get("@EndUserText.label", "No description")
                
                # Check if it's a key field
                is_key = "X" if val.get("key", False) else ""
                
                # Get data type
                data_type = val.get("type", "")
                # Simplify type display (remove "cds." prefix if present)
                if data_type.startswith("cds."):
                    data_type = data_type[4:]
                
                # Get length if available
                length = val.get("length", "")
                if length:
                    length = str(length)
                
                # Check if it's a measure (aggregation property)
                is_measure = ""
                # Check for various measure indicators
                if val.get("@Aggregation.default"):
                    is_measure = "X"
                elif val.get("@Analytics.measure"):
                    is_measure = "X"
                elif "@DefaultAggregation" in val:
                    is_measure = "X"
                # Check semantic usage for measures
                elif val.get("@Semantics.quantity") or val.get("@Semantics.amount"):
                    is_measure = "X"
                
                result.append((
                    key,
                    description,
                    is_key,
                    data_type,
                    length,
                    is_measure
                ))
            
            return pd.DataFrame(result, columns=['Field', 'Description', 'Key', 'Type', 'Length', 'Measure'])
    except Exception as e:
        # Return empty dataframe on error
        return pd.DataFrame(columns=['Field', 'Description', 'Key', 'Type', 'Length', 'Measure'])


def get_object_lineage(object_id, space_id):
    """
    Get the lineage information for an object (predecessors and successors)

    Parameters:
    - object_id: The ID of the object
    - space_id: The space ID

    Returns:
    - Dictionary with 'predecessors' and 'successors' lists
    """
    # Get credentials from V2 app_config or V1 session state
    creds = get_credentials_from_session()
    header = utils.initializeGetOAuthSession(creds['token'], creds['secret'])

    url = utils.get_url(creds['dsp_host'], "dependency").format(**{"ID": object_id})
    
    try:
        response = requests.get(url, headers=header)
        if response.status_code == 200:
            data = response.json()
            
            if not data:
                return {'predecessors': [], 'successors': []}
            
            # Get the first object (should be our target object)
            if isinstance(data, list) and len(data) > 0:
                obj_data = data[0]
                
                predecessors = []
                successors = []
                
                # Get dependencies (objects that this object depends on - predecessors)
                dependencies = obj_data.get('dependencies', [])
                for dep in dependencies:
                    predecessors.append({
                        'id': dep.get('id'),
                        'technicalName': dep.get('qualifiedName', dep.get('name', 'Unknown')),
                        'businessName': dep.get('businessName', ''),
                        'type': dep.get('kind', 'Unknown'),
                        'space': dep.get('spaceName', space_id)
                    })
                
                # Get impacts (objects that depend on this object - successors)
                impacts = obj_data.get('impacts', [])
                for imp in impacts:
                    successors.append({
                        'id': imp.get('id'),
                        'technicalName': imp.get('qualifiedName', imp.get('name', 'Unknown')),
                        'businessName': imp.get('businessName', ''),
                        'type': imp.get('kind', 'Unknown'),
                        'space': imp.get('spaceName', space_id)
                    })
                
                return {
                    'predecessors': predecessors,
                    'successors': successors
                }
        
        return {'predecessors': [], 'successors': []}
    except Exception as e:
        st.error(f"Error getting lineage: {e}")
        return {'predecessors': [], 'successors': []}


def get_object_metadata(artifact, space_id):
    """
    Get metadata about the object from CSN
    
    Parameters:
    - artifact: Technical name of the artifact
    - space_id: The space ID
    
    Returns:
    - Dictionary with metadata information
    """
    query = f'''
        SELECT A.CSN, A.ARTIFACT_VERSION
        FROM "{space_id}$TEC"."$$DEPLOY_ARTIFACTS$$" A
        INNER JOIN (
          SELECT ARTIFACT_NAME, MAX(ARTIFACT_VERSION) AS MAX_ARTIFACT_VERSION
          FROM "{space_id}$TEC"."$$DEPLOY_ARTIFACTS$$"
          WHERE SCHEMA_NAME = '{space_id}' AND ARTIFACT_NAME = '{artifact}'
          GROUP BY ARTIFACT_NAME
        ) B
        ON A.ARTIFACT_NAME = B.ARTIFACT_NAME
        AND A.ARTIFACT_VERSION = B.MAX_ARTIFACT_VERSION;
    '''
    
    try:
        csn_files = utils.database_connection(query)
        
        if not csn_files:
            return {'database_accessible': False}
        
        for csn_row in csn_files:
            csn_string = csn_row[0]
            version = csn_row[1]
            
            csn_loaded = json.loads(csn_string)
            objectName = list(csn_loaded['definitions'].keys())[0]
            obj_def = csn_loaded['definitions'][objectName]
            
            metadata = {
                'objectName': objectName,
                'businessName': obj_def.get('@EndUserText.label', 'No description'),
                'version': version,
                'exposed': obj_def.get('@DataWarehouse.consumption.external', False),
                'type': obj_def.get('kind', 'Unknown'),
                'database_accessible': True
            }
            
            # Check for Data Access Controls
            dac_usage = obj_def.get('@DataWarehouse.dataAccessControl.usage', [])
            if dac_usage:
                metadata['hasDAC'] = True
                metadata['dacObjects'] = [dac.get('target', 'Unknown') for dac in dac_usage]
            else:
                metadata['hasDAC'] = False
                metadata['dacObjects'] = []
            
            return metadata
    except Exception as e:
        # Database not accessible - return minimal info
        return {'database_accessible': False, 'error': str(e)}


def format_object_type(object_type):
    """
    Format object type for display
    """
    type_mapping = {
        'sap.dwc.taskChain': 'Task Chain',
        'sap.dis.transformationflow': 'Transformation Flow',
        'sap.dis.dataflow': 'Data Flow',
        'sap.dis.replicationflow': 'Replication Flow',
        'entity': 'Entity/View',
        'sap.dis.view': 'View',
        'sap.dwc.view': 'View',
        'sap.dis.localTable': 'Local Table',
        'sap.dis.remoteTable': 'Remote Table',
        'sap.dwc.analyticModel': 'Analytic Model'
    }
    
    return type_mapping.get(object_type, object_type)