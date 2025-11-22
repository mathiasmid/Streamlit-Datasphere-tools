import streamlit as st
import utils
import requests
from datetime import datetime
import pandas as pd
from Streamlit1.config_helpers import get_credentials_from_session

def get_user_overview():
    # Get credentials from V2 app_config or V1 session state
    creds = get_credentials_from_session()

    header = utils.initializeGetOAuthSession(creds['token'], creds['secret'])
    today = datetime.now().date()
    url = utils.get_url(creds['dsp_host'], 'user_list')
    response = requests.get(url, headers=header)
    user_json = response.json()
    user_list = []
    for user in user_json:
        username = user['userName']
        for parameter in user['parameters']:
            if parameter['name'] == 'NUMBER_OF_DAYS_VISITED':
                days_visited = parameter['value']
            if parameter['name'] == 'LAST_LOGIN_DATE':
                value = parameter['value'][:10]
                last_login = datetime.fromtimestamp(int(value)).date()
                ago = today - last_login
            if parameter['name'] == 'FIRST_NAME':
                first_name = parameter['value']
            if parameter['name'] == 'LAST_NAME':
                last_name = parameter['value']
            if parameter['name'] == 'EMAIL':
                email = parameter['value']

        user_list.append((username,first_name,last_name,email,days_visited,last_login.strftime("%d.%m.%Y"), ago.days))
        days_visited = 0
        
        last_login = datetime.fromtimestamp(int(0)).date()
        ago = last_login -  datetime.fromtimestamp(int(0)).date()
        first_name = ''
        last_name = ''
        email = ''

    df = pd.DataFrame(user_list, columns=['User Name', 'First Name', 'Last Name', 'E-Mail', 'Days Visited', 'Last Login', 'Days ago'])
   # Change column B and C's values to integers
    return df.astype({'Days Visited': int, 'Days ago': int})
