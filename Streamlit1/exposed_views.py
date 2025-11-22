import json
import pandas as pd
import streamlit as st
from . import utils

def get_csn_files():
    # Get dsp_space from V2 app_config or V1 session state
    if 'app_config' in st.session_state:
        dsp_space = st.session_state['app_config'].dsp_space
    else:
        dsp_space = st.session_state.get('dsp_space')

    query = f'''
        SELECT A.ARTIFACT_NAME, A.CSN, A.ARTIFACT_VERSION
        FROM "{dsp_space}$TEC"."$$DEPLOY_ARTIFACTS$$" A
        INNER JOIN (
          SELECT ARTIFACT_NAME, MAX(ARTIFACT_VERSION) AS MAX_ARTIFACT_VERSION
          FROM "{dsp_space}$TEC"."$$DEPLOY_ARTIFACTS$$"
          WHERE SCHEMA_NAME = '{dsp_space}' AND ARTIFACT_NAME NOT LIKE '%$%' AND PLUGIN_NAME in ('tableFunction', 'InAModel')
          GROUP BY ARTIFACT_NAME

        ) B
        ON A.ARTIFACT_NAME = B.ARTIFACT_NAME
        AND A.ARTIFACT_VERSION = B.MAX_ARTIFACT_VERSION;
    '''
    return utils.database_connection(query)

def get_exposed_views():
    # Get dsp_space from V2 app_config or V1 session state
    if 'app_config' in st.session_state:
        dsp_space = st.session_state['app_config'].dsp_space
    else:
        dsp_space = st.session_state.get('dsp_space')

    exposedViews = []
    dac_objects = []
    dac_items = []

    # Get objects which are exposed
    csn_files = get_csn_files()

    for csn in csn_files:
        csn = csn[1]
        csn_loaded = json.loads(csn)
        dac_objects.clear()
        dac_items.clear()

        objectName = list(csn_loaded['definitions'].keys())[0]
        label = csn_loaded['definitions'][objectName]['@EndUserText.label']
        try:
            exposed = csn_loaded['definitions'][objectName]['@DataWarehouse.consumption.external']
        except KeyError:
            exposed = False

        # Only process if the view is exposed
        if not exposed:
            continue

        try:
            for dac in csn_loaded['definitions'][objectName]['@DataWarehouse.dataAccessControl.usage']:

                if len(dac['on']) == 3: # one column mapping
                    dac_items.append(dac['on'][0]['ref'][0])

                if len(dac['on']) == 7: # two column mapping
                    dac_items.append(dac['on'][0]['ref'][0])
                    dac_items.append(dac['on'][4]['ref'][0])

                dac_objects.append(dac["target"])

        except KeyError:
            dac_items.clear()
            dac_objects.clear()

        exposedViews.append((dsp_space, objectName, label, exposed, ', '.join(f'{item}' for item in dac_items), ', '.join(f'{object}' for object in dac_objects)))

    return pd.DataFrame(exposedViews, columns=['Space', 'Object', 'Description', 'Exposed', 'DAC Item', 'DAC Object'])