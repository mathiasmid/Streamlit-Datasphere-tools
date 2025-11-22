import streamlit as st
from Streamlit1 import documentation_helper as doc_helper
import pandas as pd


def show_documentation_helper():
    """
    Main function to display the Documentation Helper UI
    """
    st.title("📚 Documentation Helper")
    st.markdown("Search for objects and navigate through their lineage")
    
    # Initialize session state
    if 'doc_current_object' not in st.session_state:
        st.session_state.doc_current_object = None
    if 'doc_current_space' not in st.session_state:
        st.session_state.doc_current_space = st.session_state.get('dsp_space', '')
    if 'doc_history' not in st.session_state:
        st.session_state.doc_history = []
    if 'doc_selected_object_info' not in st.session_state:
        st.session_state.doc_selected_object_info = None
    if 'doc_search_term' not in st.session_state:
        st.session_state.doc_search_term = ""
    
    # Search section
    st.subheader("🔍 Search Object")
    
    # Search form
    with st.form(key="search_form", clear_on_submit=False):
        col1, col2, col3 = st.columns([3, 2, 1])
        
        with col1:
            # Get history for dropdown options
            history_options = [obj for obj, space in st.session_state.doc_history[-10:]]  # Last 10 items
            
            # Use selectbox if there's history, otherwise text_input
            if history_options:
                search_term = st.selectbox(
                    "Technical Name",
                    options=[""] + history_options,
                    index=0 if st.session_state.doc_search_term not in history_options else history_options.index(st.session_state.doc_search_term) + 1,
                    key="doc_search_input_form",
                    help="Select from recent searches or type a new object name"
                )
                # Allow typing new value below
                if search_term == "":
                    search_term = st.text_input(
                        "Or type new object name:",
                        value="",
                        placeholder="e.g., 01_ACQ_LT_CUSTOMER, 02_DWH_CUBE_SALES",
                        label_visibility="visible"
                    )
            else:
                search_term = st.text_input(
                    "Technical Name",
                    value=st.session_state.doc_search_term,
                    placeholder="e.g., 01_ACQ_LT_CUSTOMER, 02_DWH_CUBE_SALES",
                    key="doc_search_input_form",
                    help="Space will be automatically derived from object name (01_ACQ, 02_DWH, etc.)"
                )
        
        with col2:
            space_filter = st.text_input(
                "Space (optional)",
                value="",
                key="doc_space_filter_form",
                placeholder="Leave empty for auto-detection",
                help="Only fill if object doesn't match naming convention (01_ACQ, 02_DWH, etc.)"
            )
        
        with col3:
            st.write("")  # Spacing
            st.write("")  # Spacing
            search_clicked = st.form_submit_button("🔎 Search", type="primary", use_container_width=True)
    
    # Handle search on form submission
    if search_clicked and search_term:
        # Derive space from object name
        detected_space, _ = doc_helper.derive_space_from_object_name(search_term)
        
        # Determine final space: manual input takes priority, otherwise use auto-detection
        if space_filter:
            final_space = space_filter
        elif detected_space:
            final_space = detected_space
        else:
            final_space = None
        
        if not final_space:
            st.error(f"❌ Could not determine space from object name: **{search_term}**")
            st.warning("""
            **Object name doesn't match expected naming convention.**
            
            Expected patterns:
            - `01_ACQ*` → 01_ACQUISITION
            - `02_DWH*` → 02_DATAWAREHOUSE
            - `03_SAL*` → 03_SALES
            - `03_FIN*` → 03_FINANCE
            - `04_PBI*` → 04_POWERBI
            
            **Please enter the space manually** in the "Space" field above and search again.
            """)
            st.session_state.doc_search_term = search_term
            st.rerun()
            return
        
        with st.spinner(f"Searching for {search_term} in {final_space}..."):
            obj_info, derived_space, needs_space = doc_helper.search_object_smart(search_term, final_space)
            
            if needs_space:
                st.error(f"❌ Could not determine space from object name: **{search_term}**")
                st.warning("**Object name doesn't match expected naming convention.** Please enter the space manually.")
                st.session_state.doc_search_term = search_term
                st.rerun()
                return
            
            if not obj_info:
                st.error(f"❌ Object '{search_term}' not found in space '{final_space}'")
                st.info(f"💡 **Tip**: Searched in `{final_space}`. Specify the space manually if the object is elsewhere.")
                st.session_state.doc_search_term = search_term
                st.rerun()
                return
            
            # Success - object found
            st.session_state.doc_selected_object_info = obj_info
            st.session_state.doc_current_object = obj_info['technicalName']
            st.session_state.doc_current_space = derived_space
            st.session_state.doc_search_term = obj_info['technicalName']
            
            # Add to navigation history
            if not st.session_state.doc_history or st.session_state.doc_history[-1] != (st.session_state.doc_current_object, st.session_state.doc_current_space):
                st.session_state.doc_history.append((st.session_state.doc_current_object, st.session_state.doc_current_space))
            
            st.success(f"✅ Found in space: **{derived_space}**")
            st.rerun()
    
    # Only proceed if we have an object to display
    if not st.session_state.doc_selected_object_info:
        st.info("""
        👆 **Enter an object name to get started**
        
        **How it works:**
        - Space is automatically detected from object name prefix
        - Supported prefixes: `01_ACQ`, `02_DWH`, `03_SAL`, `03_FIN`, `04_PBI`
        - Example: `01_ACQ_LT_CUSTOMER` → searches in `01_ACQUISITION`
        - Press **Enter** or click **Search** to find the object
        
        **If your object doesn't follow this pattern**, enter the space manually.
        """)
        return
    
    obj_info = st.session_state.doc_selected_object_info
    object_name = obj_info['technicalName']
    # Handle both 'space_id' and 'space' keys for compatibility
    space_id = obj_info.get('space_id') or obj_info.get('space')
    
    st.markdown("---")
    
    # Get object information
    with st.spinner(f"Loading information for {object_name}..."):
        metadata = doc_helper.get_object_metadata(object_name, space_id)
        
        if not metadata.get('database_accessible', True):
            st.warning(f"⚠️ Database access not available for space '{space_id}'. Showing limited information from API only.")
            st.info("💡 **Tip**: You may not have database permissions for this space. Contact your administrator.")
            field_info = pd.DataFrame(columns=['Key', 'Field', 'Description', 'Type', 'Length', 'Measure'])
        else:
            field_info = doc_helper.get_business_and_technical_names(object_name, space_id)
        
        lineage = doc_helper.get_object_lineage(obj_info['id'], space_id)
    
    # Field Details section with object info
    st.subheader(f"📊 Field Details - {object_name}")
    
    # Object metadata in columns
    info_col1, info_col2, info_col3 = st.columns(3)
    with info_col1:
        st.caption(f"**Type:** {doc_helper.format_object_type(obj_info['type'])}")
    with info_col2:
        st.caption(f"**Space:** {space_id}")
    with info_col3:
        if obj_info.get('businessName'):
            st.caption(f"**Business Name:** {obj_info['businessName']}")
    
    st.markdown("")  # Spacing
    
    if not field_info.empty:
        # Add search functionality for fields
        col_search, col_export = st.columns([3, 1])
        
        with col_search:
            field_search = st.text_input("🔍 Filter fields", "", key="field_search")
        
        if field_search:
            filtered_df = field_info[
                field_info['Field'].str.contains(field_search, case=False, na=False) |
                field_info['Description'].str.contains(field_search, case=False, na=False) |
                field_info['Type'].str.contains(field_search, case=False, na=False)
            ]
        else:
            filtered_df = field_info
        
        # Reorder columns to show Key first (for both display and export)
        column_order = ['Key', 'Field', 'Description', 'Type', 'Length', 'Measure']
        filtered_df = filtered_df[column_order]
        
        with col_export:
            # CSV Download button - with correct column order
            csv = filtered_df.to_csv(index=False)
            st.download_button(
                label="📥 CSV",
                data=csv,
                file_name=f"{object_name}_fields.csv",
                mime="text/csv",
                use_container_width=True
            )
            
            # Excel Download button - with correct column order
            from io import BytesIO
            excel_buffer = BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                filtered_df.to_excel(writer, index=False, sheet_name='Fields')
            excel_buffer.seek(0)
            
            st.download_button(
                label="📊 Excel",
                data=excel_buffer,
                file_name=f"{object_name}_fields.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        
        # Display field dataframe
        st.dataframe(
            filtered_df,
            use_container_width=True,
            height=400,
            hide_index=True,
            column_config={
                "Key": st.column_config.TextColumn("Key", help="X = Key field", width="small"),
                "Field": st.column_config.TextColumn("Field", help="Technical field name", width="medium"),
                "Description": st.column_config.TextColumn("Description", help="Business-friendly description", width="large"),
                "Type": st.column_config.TextColumn("Type", help="Data type", width="small"),
                "Length": st.column_config.TextColumn("Length", help="Field length", width="small"),
                "Measure": st.column_config.TextColumn("Measure", help="X = Measure/Metric field", width="small")
            }
        )
        
        # Field statistics
        key_count = len(filtered_df[filtered_df['Key'] == 'X'])
        measure_count = len(filtered_df[filtered_df['Measure'] == 'X'])
        
        stat_col1, stat_col2, stat_col3 = st.columns(3)
        with stat_col1:
            st.caption(f"🔢 Total: {len(field_info)} | Showing: {len(filtered_df)}")
        with stat_col2:
            st.caption(f"🔑 Key fields: {key_count}")
        with stat_col3:
            st.caption(f"📊 Measures: {measure_count}")
    else:
        if not metadata.get('database_accessible', True):
            st.warning("⚠️ **Database access required for field details**")
            st.info(f"Field information requires database access permissions for space `{space_id}`. Contact your administrator.")
        else:
            st.info("No field information available for this object")
    
    # Additional information section
    st.markdown("---")


def reset_documentation_helper():
    """Reset the documentation helper state"""
    st.session_state.doc_current_object = None
    st.session_state.doc_current_space = st.session_state.get('dsp_space', '')
    st.session_state.doc_history = []
    st.session_state.doc_search_term = ""