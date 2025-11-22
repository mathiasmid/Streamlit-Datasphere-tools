# Streamlit1 imports
from Streamlit1 import object_dependencies, documentation_helper_ui, documentation_helper, export_objects, exposed_views, userlist, find_column, business_name
from Streamlit1 import cache_manager as cm
from Streamlit1 import config_manager_v2 as config_manager
from Streamlit1 import utils
# Import new V2 modules
from Streamlit1.settings_ui import settings_page as settings_v2
from Streamlit1.lineage_ui import lineage_analyzer_page
from Streamlit1.documentation_ui import documentation_generator_page

# Standard library imports
import streamlit as st
import json
import pandas as pd
from requests_oauthlib import OAuth2Session
import urllib.parse
import requests
from datetime import datetime, timedelta
import time

st.set_page_config(
    page_title="Datasphere Tools",
    page_icon="🛠️",
    layout="wide",
)

# Initialize cache
cm.CacheManager.initialize_cache()


def show_cache_indicator():
    """Show cache status in sidebar"""
    with st.sidebar:
        stats = cm.CacheManager.get_cache_stats()
        
        if stats['loading']:
            progress, msg = cm.CacheManager.get_progress()
            st.progress(progress / 100, text=f"{progress}%")
            st.caption(msg)
            
            # Add stop button
            if st.button("⏹️ Stop Loading", use_container_width=True):
                cm.CacheManager.clear_cache()
                st.rerun()
                
        elif stats['loaded']:
            st.success(f"✅ Cache: {stats['total_objects']} objects")
        elif cm.CacheManager.is_config_ready():
            if st.button("🚀 Load Cache", use_container_width=True):
                st.rerun()


def intro():
    show_cache_indicator()
    
    st.write("# SAP Datasphere Tools 👋")
    
    st.warning("""
    ⚠️ **DISCLAIMER - INTERNAL USE ONLY**
    
    This is a **prototype application** based on the original work by **Tobias Meyer**.
    
    **Important Notes:**
    - This tool is intended for **internal use by Delaware employees only**
    - This application is for **personal/internal analysis purposes**
    - **DO NOT share this tool or provide it to clients**
    - This is not a production-ready application
    
    For questions or issues, please contact your Delaware Datasphere team.
    """, icon="⚠️")
    
    st.markdown("---")
    
    st.markdown("""
    ### Welcome to SAP Datasphere Tools

    This application provides utilities to help you manage and analyze your SAP Datasphere environment.

    **Getting Started:**
    1. Go to **Settings V2 (New)** to configure your connection with encryption
    2. Configure your Datasphere host, database, and OAuth credentials
    3. Optionally load cache for faster performance
    4. Start exploring the tools!

    **✨ New Features (V2):**
    - 🔗 **Lineage Analyzer** - Visualize complete object dependencies and data flows
    - 📄 **Documentation Generator** - Create Word documents from lineage with field mappings
    - 🔐 **Encrypted Settings** - Secure credential storage with automatic encryption
    - ⚡ **Enhanced Cache** - Type-safe caching with progress tracking

    **Available Tools:**
    - 📦 Export objects to JSON format
    - 📚 Documentation helper for data lineage
    - 📦 Find object dependencies
    - 🤞 Search for columns across objects
    - 🥳 Get business and technical names
    - 👀 View exposed objects with DAC
    - 👥 User overview and analytics

    **⚡ Performance:**
    - All tools work without cache (direct API calls)
    - Load cache for 10x faster performance
    - Cache is optional but recommended

    **🔒 Security:**
    - All sensitive data encrypted on disk (V2 Settings)
    - No plain-text passwords stored
    - Auto-generated encryption keys
    """)
    
    # Show cache status
    st.markdown("---")
    stats = cm.CacheManager.get_cache_stats()
    if stats['loaded']:
        st.success(f"✅ Cache loaded: {stats['total_spaces']} spaces, {stats['total_objects']} objects")
    elif stats['loading']:
        progress, msg = cm.CacheManager.get_progress()
        st.info(f"⏳ Cache loading: {progress}%")
        st.progress(progress / 100)
        st.caption(msg)
    elif cm.CacheManager.is_config_ready():
        st.info("ℹ️ Configuration ready. Go to Settings to load cache (optional).")
    else:
        st.info("ℹ️ Please configure your connection in Settings first.")



# Legacy settings() function and OAuth helpers removed - replaced by settings_v2 (settings_ui.py)

def check_session_state():
    """Check if configuration is available (V2 or V1)."""
    # Check V2 config first
    if 'app_config' in st.session_state:
        config = st.session_state['app_config']
        if config and config.dsp_host and config.access_token:
            return False  # Config is ready

    # Check V1 session state keys
    required_v1 = ['hdb_address', 'token', 'secret']
    if all(st.session_state.get(key) for key in required_v1):
        return False  # Config is ready

    # No valid config found
    st.warning("Please go to the Settings page and configure your connection first.", icon="⚠️")
    return True

def selectbox_space():
    spaces_display = get_space_names_display()
    if not spaces_display:
        st.error("No spaces available. Please check your connection or load cache.")
        return None
    return st.selectbox(label='Select Space', options=spaces_display, index=0).split(' ')[0]

def get_space_names_display():
    """Get formatted space names - works with or without cache"""
    list_of_spaces = []
    spaces = cm.get_list_of_space_cached()
    
    if not spaces:
        return []
    
    business_lookup = cm.get_space_names_cached()
    
    for space in spaces:
        try:
            list_of_spaces.append(str(space[0]) + " [" + business_lookup[space[0]] + "]")
        except KeyError:
            list_of_spaces.append(str(space[0]))
    
    return list_of_spaces

def exposed_views_gui():
    show_cache_indicator()
    if check_session_state():
        return
    st.write("# Exposed Views 👀")   
    st.markdown("Find views which are exposed for consumption and check if they have a Data Access Control assigned.")
    with st.container(width=2000, border=True):
        st.session_state.dsp_space = selectbox_space()
        if st.button('Get Exposed Views'):
            with st.spinner("Wait for it...", show_time=True):
                st.session_state.df = exposed_views.get_exposed_views()    
                st.session_state.display = not st.session_state.df.empty
                if st.session_state.df.empty:
                   st.info("No exposed views found.", icon="ℹ️")
    result = st.empty()
    if st.session_state.get('display', False):
        with result.container(width=2000, border=True):    
            st.dataframe(data=st.session_state.df, hide_index=True)   
            st.session_state.display = False

def object_dependencies_gui():
    show_cache_indicator()
    if check_session_state():
        return
    st.write("# Object Dependencies 📦")   
    st.markdown("Find the dependencies for a certain object")
    with st.container(width=2000, border=True):
        object_name = st.text_input(label='Enter Object Name', value='')  
        if st.button('Find Object Dependencies'):
            with st.spinner("Wait for it...", show_time=True):
                st.session_state.df = object_dependencies.get_object_dependencies(object_name)
                st.session_state.display = not st.session_state.df.empty
                if st.session_state.df.empty:
                   st.info("No dependencies found.", icon="ℹ️")
    result = st.empty()
    if st.session_state.get('display', False):
        with result.container(width=2000, border=True):    
            st.dataframe(data=st.session_state.df, hide_index=True)   
            st.session_state.display = False

def userlist_gui():
    show_cache_indicator()
    if check_session_state():
        return
    st.write("# User Overview 👥")
    st.markdown("Overview of all users in the tenant with time of login, last login and days since the last login.")
    with st.container(width=2000, border=True):
        with st.spinner("Wait for it...", show_time=True):
            df = userlist.get_user_overview()    
            st.dataframe(df, width="stretch")

def column_in_object_gui():
    show_cache_indicator()
    if check_session_state():
        return
    st.write("# Find column in Object 🤞")
    st.markdown("You can enter a technical column name and search overall objects in the Datasphere tenant!")
    with st.container(width=2000, border=True):   
        column = st.text_input(label='Enter Column Name', value='')
        if st.button('Find Objects'):
            with st.spinner("Wait for it...", show_time=True):
               st.session_state.df = find_column.find_objects(column)
               st.session_state.display = not st.session_state.df.empty
               if st.session_state.df.empty:
                   st.info("No object found.", icon="ℹ️")
    result = st.empty()
    if st.session_state.get('display', False):
        with result.container(width=2000, border=True):    
            st.dataframe(data=st.session_state.df, hide_index=True)   
            st.session_state.display = False

def business_names_gui():
    show_cache_indicator()
    if check_session_state():
        return
    st.write("# Get Business and Technical Name 🥳")
    st.markdown("Obtain the business and technical names of the columns of one object.")
    with st.container(width=2000, border=True):   
        st.session_state.dsp_space = selectbox_space()
        artifact = st.text_input(label='Enter technical Object Name', value='')
        if st.button("Get Business Name"):
            df = business_name.get_business_and_technical_name(artifact)
            st.dataframe(data=df, hide_index=True)  

def export_json_gui():
    """Export using cache if available, otherwise direct API calls"""
    show_cache_indicator()
    if check_session_state():
        return
    
    st.write("# Export Objects to JSON 📦")
    
    # Check if cache is available
    stats = cm.CacheManager.get_cache_stats()
    if stats['loaded']:
        st.caption(f"⚡ Using cache: {stats['total_spaces']} spaces, {stats['total_objects']} objects")
        all_objects = cm.CacheManager.get_cached_objects()
    else:
        st.info("💡 Cache not loaded. Select spaces to load objects on-demand (slower).")
        
        # Get spaces for selection
        spaces = cm.get_list_of_space_cached()
        if not spaces:
            st.error("Could not load spaces. Please check your connection.")
            return
        
        space_list = [s[0] for s in spaces]
        selected_spaces = st.multiselect("Select spaces to load objects from:", options=space_list)
        
        if not selected_spaces:
            st.info("Select one or more spaces to continue.")
            return
        
        # Load objects for selected spaces
        all_objects = []
        with st.spinner(f"Loading objects from {len(selected_spaces)} space(s)..."):
            for space in selected_spaces:
                objs = export_objects.get_all_objects_direct(space, limit=250)
                all_objects.extend(objs)
        
        st.success(f"Loaded {len(all_objects)} objects from {len(selected_spaces)} space(s)")
    
    if not all_objects:
        st.warning("No objects available.")
        return

    # Convert Pydantic models to dicts if needed
    # Check if objects have Pydantic model attributes and convert to dicts
    if all_objects and hasattr(all_objects[0], 'technical_name'):
        all_objects = [
            {
                'technicalName': obj.technical_name,
                'object_type': obj.object_type,
                'space_id': obj.space_id,
                'object_name': obj.object_name if hasattr(obj, 'object_name') else obj.technical_name
            }
            for obj in all_objects
        ]

    # Create DataFrame
    df = pd.DataFrame(all_objects)

    # Check if DataFrame has required columns
    required_columns = ['object_type', 'technicalName', 'space_id']
    missing_columns = [col for col in required_columns if col not in df.columns]

    if missing_columns:
        st.error(f"Error: Objects are missing required fields: {missing_columns}")
        st.info("This might be due to an API error. Please check your connection and try again.")
        if len(all_objects) > 0:
            st.write("Sample object structure:", all_objects[0])
        return

    with st.container(border=True):
        st.write("### Select Objects")
        col1, col2 = st.columns([2, 1])
        with col1:
            search = st.text_input("🔍 Search:", placeholder="Filter by name...")
        with col2:
            types = sorted(df['object_type'].unique())
            type_filter = st.multiselect("🏷️ Type:", options=types)
        
        filtered = df.copy()
        if search:
            filtered = filtered[filtered['technicalName'].str.contains(search, case=False, na=False)]
        if type_filter:
            filtered = filtered[filtered['object_type'].isin(type_filter)]
        
        st.write(f"**Showing {len(filtered)} of {len(df)} objects**")
        
        selection_df = filtered[['space_id', 'object_type', 'technicalName']].copy()
        selection_df.insert(0, 'Select', False)
        
        edited = st.data_editor(selection_df, hide_index=True, height=400, 
            column_config={"Select": st.column_config.CheckboxColumn("Select", width="small")})
        
        selected = edited[edited['Select'] == True]
        
        if len(selected) > 0:
            st.info(f"**✓ {len(selected)} objects selected**")
            format_choice = st.radio("Format:", ['separate', 'combined'], 
                format_func=lambda x: "📄 Separate files" if x == 'separate' else "📦 Combined file", horizontal=True)
            
            if st.button("🚀 Export JSON", type="primary"):
                with st.spinner("Exporting..."):
                    selected_objs = []
                    for _, row in selected.iterrows():
                        match = [o for o in all_objects if o['space_id'] == row['space_id'] 
                                and o['object_type'] == row['object_type'] and o['technicalName'] == row['technicalName']]
                        selected_objs.extend(match)
                    
                    files = export_objects.export_objects_to_json(selected_objs, format_choice)
                    if files:
                        zip_buf = export_objects.create_zip_download(files)
                        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                        st.success(f"✅ Exported {len(files)} file(s)!")
                        st.download_button("📥 Download ZIP", data=zip_buf, 
                            file_name=f"datasphere_export_{ts}.zip", mime="application/zip")

def documentation_helper_gui():
    show_cache_indicator()
    if check_session_state():
        return
    documentation_helper_ui.show_documentation_helper()


pages = {
    "General": [
        st.Page(intro, title="Home"),
        st.Page(settings_v2, title="Settings", icon="⚙️"),
    ],
    "Tools": [
        st.Page(export_json_gui, title="Export Objects to JSON", icon="📦"),
        st.Page(lineage_analyzer_page, title="Lineage Analyzer", icon="🔗"),
        st.Page(documentation_generator_page, title="Documentation Generator", icon="📄"),
        st.Page(documentation_helper_gui, title="Documentation Helper (Legacy)", icon="📚"),
        st.Page(object_dependencies_gui, title="Find Object Dependencies", icon="📦"),
        st.Page(column_in_object_gui, title="Column in Object", icon="🤞"),
        st.Page(business_names_gui, title="Get Business/Technical Name", icon="🥳")
    ],
    "HouseKeeping": [
        st.Page(exposed_views_gui, title="Exposed Views", icon="👀"),
        st.Page(userlist_gui, title="User Overview", icon="👥")
    ]
}

pg = st.navigation(pages)
pg.run()