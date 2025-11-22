"""
Documentation Generator UI for SAP Datasphere Tools.

Generates Word documentation from lineage with field mappings.
"""

import streamlit as st
import io
from datetime import datetime

from .models import AppConfig, LineageTree
from .lineage import LineageAnalyzer
from .documentation_builder import DocumentationBuilder
from .error_handler import handle_errors, display_success, display_info, ActivityLogger
from .cache_manager import CacheManager
from .config_manager_v2 import ConfigManager


@handle_errors(show_traceback=True)
def documentation_generator_page():
    """Main documentation generator page."""

    st.title("📄 Documentation Generator")
    st.markdown("Generate comprehensive Word documentation from object lineage")

    # Initialize
    CacheManager.initialize_cache()

    # Check config
    config_manager = ConfigManager()
    config = config_manager.load_config()

    if not config:
        st.warning("⚠️ Configuration not found. Please go to Settings.")
        st.stop()

    # Sidebar controls
    st.sidebar.header("⚙️ Documentation Options")

    # Check if we have lineage from lineage page
    has_existing_lineage = 'current_lineage' in st.session_state

    if has_existing_lineage:
        lineage_obj_name = st.session_state.get('lineage_object_name', 'Unknown')
        st.sidebar.success(f"✅ Using lineage for: {lineage_obj_name}")

        use_existing = st.sidebar.radio(
            "Lineage Source",
            ["Use Existing Lineage", "Fetch New Lineage"]
        )
    else:
        use_existing = "Fetch New Lineage"
        st.sidebar.info("ℹ️ No existing lineage found")

    # Object selection
    object_id = None
    object_name = None

    if use_existing == "Fetch New Lineage":
        st.sidebar.subheader("Object Selection")

        selection_method = st.sidebar.radio(
            "Selection Method",
            ["Dropdown (from cache)", "Manual Entry"]
        )

        if selection_method == "Dropdown (from cache)":
            if not CacheManager.is_cache_loaded():
                st.sidebar.warning("⚠️ Cache not loaded. Use Manual Entry or load cache.")

                if st.sidebar.button("🔄 Load Cache"):
                    with st.spinner("Loading cache..."):
                        if CacheManager.load_cache(config):
                            display_success("Cache loaded!")
                            st.rerun()
            else:
                metadata = CacheManager.get_cache_metadata()
                st.sidebar.success(f"✅ Cache: {metadata.object_count} objects")

                cached_objects = CacheManager.get_cached_objects()
                if cached_objects:
                    object_options = {
                        f"{obj.technical_name} ({obj.space_id})": obj
                        for obj in cached_objects
                    }

                    selected_option = st.sidebar.selectbox(
                        "Select Object",
                        options=list(object_options.keys())
                    )

                    if selected_option:
                        selected_obj = object_options[selected_option]
                        object_id = selected_obj.object_id
                        object_name = selected_obj.technical_name

        else:  # Manual Entry
            object_id = st.sidebar.text_input(
                "Object ID (hex)",
                placeholder="6E4175B207AC02FB18004E421859F770"
            )

            object_name = st.sidebar.text_input(
                "Object Name (optional)",
                placeholder="02_DWH_CUBE_UNIVERSAL_LEDGER"
            )

    # Documentation options
    st.sidebar.subheader("Content Options")

    include_field_mappings = st.sidebar.checkbox(
        "Include Field Mappings",
        value=True,
        help="Include detailed field-level information"
    )

    include_transformations = st.sidebar.checkbox(
        "Include Transformation Logic",
        value=True,
        help="Include transformation flow details"
    )

    transactional_only = st.sidebar.checkbox(
        "Transactional Objects Only",
        value=False,
        help="Document only data flows and transformations"
    )

    # Generate button
    generate_button = st.sidebar.button(
        "📝 Generate Documentation",
        type="primary",
        use_container_width=True
    )

    # Main content
    if generate_button:
        # Get lineage
        if use_existing == "Use Existing Lineage":
            lineage_tree: LineageTree = st.session_state['current_lineage']
            obj_name = st.session_state.get('lineage_object_name', 'Unknown')

            st.info(f"ℹ️ Using existing lineage for {obj_name}")

        else:
            # Fetch new lineage
            if not object_id:
                st.error("❌ Please provide an Object ID")
                st.stop()

            with st.spinner(f"Fetching lineage for {object_name or object_id}..."):
                try:
                    analyzer = LineageAnalyzer(config)
                    lineage_tree = analyzer.fetch_lineage(
                        object_id=object_id,
                        object_name=object_name,
                        recursive=True,
                        include_impact=True
                    )

                    obj_name = object_name or object_id

                    # Store for future use
                    st.session_state['current_lineage'] = lineage_tree
                    st.session_state['lineage_object_name'] = obj_name

                    display_success(f"Lineage fetched: {lineage_tree.count_objects()} objects")

                except Exception as e:
                    st.error(f"❌ Failed to fetch lineage: {str(e)}")
                    st.stop()

        # Generate documentation
        with st.spinner("📝 Generating documentation..."):
            try:
                builder = DocumentationBuilder(config)

                doc = builder.build_lineage_documentation(
                    lineage_tree=lineage_tree,
                    root_object_name=obj_name,
                    include_field_mappings=include_field_mappings,
                    include_transformations=include_transformations,
                    transactional_only=transactional_only
                )

                # Save to BytesIO
                doc_io = io.BytesIO()
                doc.save(doc_io)
                doc_io.seek(0)

                st.session_state['generated_doc'] = doc_io.getvalue()
                st.session_state['doc_filename'] = f"lineage_doc_{obj_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"

                display_success("✅ Documentation generated successfully!")
                ActivityLogger.log(f"Documentation generated for {obj_name}", "success")

            except Exception as e:
                st.error(f"❌ Failed to generate documentation: {str(e)}")
                ActivityLogger.log(f"Documentation generation failed: {str(e)}", "error")
                st.stop()

    # Display download button if doc is generated
    if 'generated_doc' in st.session_state:
        st.success("✅ Documentation ready for download!")

        col1, col2, col3 = st.columns([2, 1, 1])

        with col1:
            st.download_button(
                label="📥 Download Word Document",
                data=st.session_state['generated_doc'],
                file_name=st.session_state['doc_filename'],
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True
            )

        with col2:
            if st.button("🔄 Generate New", use_container_width=True):
                del st.session_state['generated_doc']
                del st.session_state['doc_filename']
                st.rerun()

        with col3:
            file_size = len(st.session_state['generated_doc']) / 1024
            st.metric("File Size", f"{file_size:.1f} KB")

        # Preview info
        st.markdown("---")
        st.subheader("📋 Document Contents")

        st.markdown("""
        The generated Word document includes:

        ### 1. Title Page
        - Document title and object name
        - Generation timestamp
        - Lineage statistics

        ### 2. Overview
        - Purpose and scope
        - Lineage summary statistics
        - Object type distribution

        ### 3. Object Details
        - Detailed information for each object
        - Field definitions (if enabled)
        - Data types, keys, and constraints

        ### 4. Field Mappings
        - Source to target field mappings
        - Transformation logic overview

        ### 5. Appendix
        - Complete object list
        - Glossary of terms

        ### 📝 Next Steps
        1. Download the Word document
        2. Open in Microsoft Word
        3. Right-click the Table of Contents and select "Update Field"
        4. Review and customize as needed
        """)

    else:
        # No document generated yet - show instructions
        st.info("👆 Configure options in the sidebar and click 'Generate Documentation'")

        st.markdown("""
        ## How to Generate Documentation

        ### Step 1: Select Lineage Source
        - **Use Existing Lineage**: If you just viewed lineage in the Lineage Analyzer page
        - **Fetch New Lineage**: Select an object from cache or enter object ID manually

        ### Step 2: Configure Content
        - ✅ **Include Field Mappings**: Add detailed field information from CSN definitions
        - ✅ **Include Transformation Logic**: Document transformation flows
        - ⚪ **Transactional Only**: Focus only on data flows (exclude views/associations)

        ### Step 3: Generate
        - Click "Generate Documentation" button
        - Wait for processing (may take 30-60 seconds for large lineages)
        - Download the Word document

        ### 💡 Tips
        - **Field Mappings** require database access to fetch CSN definitions
        - **Large lineages** (100+ objects) may take longer to process
        - Documents can be customized in Word after generation
        - Use **Transactional Only** for cleaner flow documentation

        ### 🎯 Use Cases
        - **Impact Analysis**: Document what would be affected by changing an object
        - **Onboarding**: Help new team members understand data flows
        - **Compliance**: Maintain audit trail of data lineage
        - **Migration Planning**: Document dependencies before system changes
        """)

        # Show example preview
        with st.expander("📖 Example Document Preview"):
            st.image(
                "https://via.placeholder.com/800x600/f0f0f0/333333?text=Example+Lineage+Documentation",
                caption="Example lineage documentation (illustration)"
            )

    # Show activity log
    ActivityLogger.display()


if __name__ == "__main__":
    documentation_generator_page()
