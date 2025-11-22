"""
Lineage visualization UI for SAP Datasphere Tools.

Provides interactive lineage analysis with filtering and export capabilities.
"""

import streamlit as st
import json
from typing import Optional, List, Dict
import pandas as pd

from .models import AppConfig, LineageTree, LineageNode
from .lineage import LineageAnalyzer, identify_data_flow_path, categorize_lineage_objects
from .error_handler import handle_errors, display_success, display_info, display_warning, display_error, ActivityLogger
from .cache_manager import CacheManager
from .config_manager_v2 import ConfigManager


def filter_out_associations(lineage_tree: LineageTree) -> LineageTree:
    """Remove csn.entity.association dependencies from tree."""
    def filter_node(node: LineageNode) -> Optional[LineageNode]:
        # Filter out association dependencies
        filtered_deps = []
        for dep in node.dependencies:
            if dep.dependency_type != 'csn.entity.association':
                filtered_dep = filter_node(dep)
                if filtered_dep:
                    filtered_deps.append(filtered_dep)

        # Return node with filtered dependencies
        return LineageNode(
            id=node.id,
            qualified_name=node.qualified_name,
            name=node.name,
            kind=node.kind,
            folder_id=node.folder_id,
            dependency_type=node.dependency_type,
            hash=node.hash,
            impact=node.impact,
            lineage=node.lineage,
            dependencies=filtered_deps
        )

    filtered_root = filter_node(lineage_tree.root)
    if filtered_root:
        return LineageTree(root=filtered_root, fetched_at=lineage_tree.fetched_at)
    return lineage_tree


def render_lineage_table(lineage_tree: LineageTree):
    """
    Render lineage as a flat table with deduplication and flow order.

    Args:
        lineage_tree: LineageTree to display
    """
    def collect_with_depth(node: LineageNode, depth: int = 0) -> List[Dict]:
        """Recursively collect nodes with depth level."""
        results = [{'node': node, 'depth': depth}]
        for dep in node.dependencies:
            results.extend(collect_with_depth(dep, depth + 1))
        return results

    # Collect all nodes with depth
    nodes_with_depth = collect_with_depth(lineage_tree.root)

    # Deduplicate: keep shallowest occurrence of each unique object
    unique_nodes = {}
    for item in nodes_with_depth:
        obj_id = item['node'].id
        if obj_id not in unique_nodes or item['depth'] < unique_nodes[obj_id]['depth']:
            unique_nodes[obj_id] = item

    # Build table data
    data = []
    for item in sorted(unique_nodes.values(), key=lambda x: x['depth']):
        obj = item['node']
        data.append({
            'Level': item['depth'],
            'Name': obj.name,
            'Type': obj.kind,
            'Transactional': '✅' if obj.is_transactional() else '❌',
            'Dependency Type': obj.dependency_type or 'Root',
            'ID': obj.id
        })

    df = pd.DataFrame(data)

    # Column configuration
    column_config = {
        'Level': st.column_config.NumberColumn('Level', help='0 = Query, higher = deeper sources'),
        'Name': st.column_config.TextColumn('Object Name', width='medium'),
        'Type': st.column_config.TextColumn('Object Type', width='medium'),
        'Transactional': st.column_config.TextColumn('Transactional', width='small'),
        'Dependency Type': st.column_config.TextColumn('Dependency Type', width='medium'),
        'ID': st.column_config.TextColumn('ID', width='small')
    }

    st.dataframe(df, column_config=column_config, use_container_width=True, hide_index=True)
    st.caption(f"📊 Showing {len(df)} unique objects (ordered by flow: Query → Source)")


def render_node_card(node: LineageNode):
    """Render a compact card for a single node."""
    # Icon based on type
    if node.dependency_type == 'csn.query.from':
        icon = "📥"
    elif 'replicationflow' in (node.dependency_type or ''):
        icon = "🔄"
    elif 'transformationflow' in (node.dependency_type or ''):
        icon = "⚙️"
    elif node.dependency_type == 'csn.entity.association':
        icon = "🔗"
    else:
        icon = "📊"

    # Card with border
    st.markdown(f"""
    <div style='border: 1px solid #ddd; padding: 10px; border-radius: 5px; margin: 5px 0;'>
        <div style='font-size: 20px;'>{icon}</div>
        <div style='font-weight: bold;'>{node.name}</div>
        <div style='font-size: 12px; color: #666;'>{node.kind}</div>
        <div style='font-size: 11px; color: #999;'>{node.dependency_type or 'Root'}</div>
    </div>
    """, unsafe_allow_html=True)


def render_flow_diagram(lineage_tree: LineageTree, max_depth: int = 10):
    """Render lineage as a linear flow diagram: Query → Source."""

    def collect_by_level(node: LineageNode, depth: int = 0) -> Dict[int, List[LineageNode]]:
        """Group nodes by depth level."""
        levels = {depth: [node]}
        for dep in node.dependencies:
            dep_levels = collect_by_level(dep, depth + 1)
            for level, nodes in dep_levels.items():
                if level in levels:
                    levels[level].extend(nodes)
                else:
                    levels[level] = nodes
        return levels

    # Group objects by level
    levels = collect_by_level(lineage_tree.root)

    # Deduplicate within each level
    for level, nodes in levels.items():
        seen_ids = set()
        unique = []
        for node in nodes:
            if node.id not in seen_ids:
                seen_ids.add(node.id)
                unique.append(node)
        levels[level] = unique

    # Render each level
    for level in sorted(levels.keys()):
        if level > max_depth:
            st.info(f"⚠️ Stopping at level {max_depth}. Use slider to show deeper levels.")
            break

        nodes = levels[level]

        # Level header
        if level == 0:
            st.markdown(f"### 🎯 Query Object (Level {level})")
        else:
            st.markdown(f"### {'⬇️' * min(level, 3)} Level {level} - {len(nodes)} object(s)")

        # Show objects at this level in columns
        if len(nodes) <= 3:
            cols = st.columns(len(nodes))
            for idx, node in enumerate(nodes):
                with cols[idx]:
                    render_node_card(node)
        else:
            # Too many objects, use expander
            with st.expander(f"📦 {len(nodes)} objects at this level", expanded=level < 3):
                cols = st.columns(min(3, len(nodes)))
                for idx, node in enumerate(nodes):
                    with cols[idx % 3]:
                        render_node_card(node)

        # Arrow to next level
        if level < max(levels.keys()) and level < max_depth:
            st.markdown("<div style='text-align: center; font-size: 24px; margin: 10px 0;'>⬇️</div>", unsafe_allow_html=True)


@handle_errors(show_traceback=True)
def lineage_analyzer_page():
    """Main lineage analyzer page."""

    st.title("🔗 Lineage Analyzer")
    st.markdown("Analyze object dependencies and data lineage in SAP Datasphere")

    # Initialize cache
    CacheManager.initialize_cache()

    # Get config from session state (with active OAuth token)
    if 'app_config' in st.session_state:
        config = st.session_state['app_config']
    else:
        # Fallback: load from disk (but won't have active token)
        config_manager = ConfigManager()
        config = config_manager.load_config()

    if not config:
        st.warning("⚠️ Configuration not found. Please go to Settings to configure the application.")
        st.stop()

    # Validate OAuth token
    if not config.is_token_valid():
        st.error("❌ OAuth token is invalid or expired. Please refresh token in Settings.")
        st.stop()

    # Sidebar controls
    st.sidebar.header("⚙️ Lineage Options")

    # Object selection method
    selection_method = st.sidebar.radio(
        "Object Selection Method",
        ["Dropdown (from cache)", "Manual Entry"],
        help="Choose how to select the object"
    )

    object_id = None
    object_name = None

    if selection_method == "Dropdown (from cache)":
        # Check cache status
        if not CacheManager.is_cache_loaded():
            st.sidebar.warning("⚠️ Cache not loaded. Please load cache in Settings or use Manual Entry.")

            if st.sidebar.button("🔄 Load Cache Now"):
                with st.spinner("Loading cache..."):
                    success = CacheManager.load_cache(config)
                    if success:
                        display_success("Cache loaded successfully!")
                        st.rerun()
                    else:
                        display_warning("Cache loading failed. Please use Manual Entry.")
        else:
            # Show cache info
            metadata = CacheManager.get_cache_metadata()
            st.sidebar.success(f"✅ Cache loaded: {metadata.object_count} objects")

            # Get cached objects
            cached_objects = CacheManager.get_cached_objects()

            if cached_objects:
                # Create dropdown options
                object_options = {
                    f"{obj.technical_name} ({obj.space_id})": obj
                    for obj in cached_objects
                }

                selected_option = st.sidebar.selectbox(
                    "Select Object",
                    options=list(object_options.keys()),
                    help="Select an object from the cache"
                )

                if selected_option:
                    selected_obj = object_options[selected_option]
                    object_id = selected_obj.object_id
                    object_name = selected_obj.technical_name

                    st.sidebar.info(f"📊 Type: {selected_obj.object_type}")

    else:  # Manual Entry
        st.sidebar.info("💡 Enter the object's technical name. Space will be auto-detected.")

        # Technical name input
        object_name = st.sidebar.text_input(
            "Technical Name",
            placeholder="02_DWH_CUBE_UNIVERSAL_LEDGER",
            help="Object's technical name - ID will be looked up automatically"
        )

        # Optional space override
        space_filter = st.sidebar.text_input(
            "Space (optional)",
            placeholder="Auto-detected from name prefix",
            help="Leave empty for auto-detection based on name prefix"
        )

        # Show derived space if we can detect it
        if object_name:
            from .documentation_helper import derive_space_from_object_name
            derived_space, prefix = derive_space_from_object_name(object_name)
            if derived_space and not space_filter:
                st.sidebar.success(f"✅ Auto-detected space: {derived_space}")
            elif not derived_space and not space_filter:
                st.sidebar.warning("⚠️ Could not auto-detect space. Please specify or expect slower search.")

        # ID will be looked up automatically during fetch
        object_id = None

    # Lineage options
    st.sidebar.subheader("Lineage Settings")

    recursive = st.sidebar.checkbox(
        "Recursive",
        value=True,
        help="Include nested dependencies"
    )

    include_impact = st.sidebar.checkbox(
        "Include Impact",
        value=True,
        help="Include impact analysis"
    )

    show_transactional_only = st.sidebar.checkbox(
        "Transactional Only",
        value=True,
        help="Show only transactional objects (flows, replications)"
    )

    show_associations = st.sidebar.checkbox(
        "Include Associations",
        value=False,
        help="Show foreign key associations (csn.entity.association)",
        disabled=not show_transactional_only
    )

    # Display options
    st.sidebar.subheader("Display Options")

    display_mode = st.sidebar.radio(
        "Display Mode",
        ["Flow Diagram", "Table View", "Both"],
        help="Choose how to display lineage"
    )

    max_depth = st.sidebar.slider(
        "Max Tree Depth",
        min_value=1,
        max_value=20,
        value=10,
        help="Maximum depth to display in tree view"
    )

    # Fetch lineage button
    fetch_button = st.sidebar.button("🔍 Fetch Lineage", type="primary", use_container_width=True)

    # Main content area
    if fetch_button:
        # Validate input
        if not object_name:
            st.error("❌ Please provide an object technical name")
            st.stop()

        # Auto-lookup object ID if needed (Manual Entry mode)
        if selection_method == "Manual Entry" and not object_id:
            with st.spinner(f"🔍 Looking up object: {object_name}..."):
                try:
                    from .api_client import DataspherAPIClient
                    from .documentation_helper import derive_space_from_object_name

                    # Try space derivation
                    derived_space, prefix = derive_space_from_object_name(object_name)
                    search_space = space_filter if space_filter else derived_space

                    # Lookup ID via API
                    api_client = DataspherAPIClient(config)
                    object_id = api_client.find_object_id_by_name(
                        technical_name=object_name,
                        space_id=search_space
                    )

                    if not object_id:
                        st.error(f"❌ Object '{object_name}' not found in accessible spaces")
                        if not search_space:
                            st.info("💡 Try specifying the space to speed up search")
                        st.stop()

                    # Show success
                    st.success(f"✅ Found object: {object_name}")

                    # Show lookup details in expander
                    with st.expander("🔍 Lookup Details", expanded=False):
                        st.code(f"Object ID: {object_id}")
                        st.code(f"Searched in: {search_space if search_space else 'all accessible spaces'}")
                        if derived_space:
                            st.info(f"Space auto-detected from prefix '{prefix}'")

                except Exception as e:
                    st.error(f"❌ Lookup failed: {str(e)}")
                    st.stop()

        # Fetch lineage
        with st.spinner(f"Fetching lineage for {object_name}..."):
            try:
                analyzer = LineageAnalyzer(config)
                lineage_tree = analyzer.fetch_lineage(
                    object_id=object_id,
                    object_name=object_name,
                    recursive=recursive,
                    include_impact=include_impact
                )

                # Store in session state
                st.session_state['current_lineage'] = lineage_tree
                st.session_state['lineage_object_name'] = object_name

                display_success(f"Lineage fetched successfully! Found {lineage_tree.count_objects()} objects.")
                ActivityLogger.log(f"Fetched lineage for {object_name}", "success")

            except Exception as e:
                st.error(f"❌ Failed to fetch lineage: {str(e)}")
                ActivityLogger.log(f"Lineage fetch failed for {object_name}: {str(e)}", "error")
                st.stop()

    # Display lineage if available
    if 'current_lineage' in st.session_state:
        lineage_tree: LineageTree = st.session_state['current_lineage']
        obj_name = st.session_state.get('lineage_object_name', 'Unknown')

        st.header(f"📊 Lineage for: {obj_name}")

        # Apply transactional filter if needed
        display_tree = lineage_tree
        if show_transactional_only:
            filtered_tree = lineage_tree.get_transactional_lineage()
            if filtered_tree:
                display_tree = filtered_tree
                st.info(f"ℹ️ Showing only transactional objects: {display_tree.count_objects()} of {lineage_tree.count_objects()} total")

                # Further filter associations if needed
                if not show_associations:
                    display_tree = filter_out_associations(display_tree)
            else:
                st.warning("⚠️ No transactional objects found in lineage")
                display_tree = lineage_tree

        # Statistics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Objects", display_tree.count_objects())

        with col2:
            transactional_count = sum(1 for obj in display_tree.get_all_objects() if obj.is_transactional())
            st.metric("Transactional", transactional_count)

        with col3:
            type_counts = display_tree.count_by_type()
            st.metric("Object Types", len(type_counts))

        with col4:
            metadata = CacheManager.get_cache_metadata()
            if metadata.timestamp:
                age = metadata.age_minutes()
                st.metric("Cache Age", f"{age:.0f} min" if age else "N/A")

        # Analysis section
        with st.expander("📈 Detailed Analysis", expanded=False):
            analyzer = LineageAnalyzer(config)
            analysis = analyzer.analyze_lineage(display_tree)

            col1, col2 = st.columns(2)

            with col1:
                st.subheader("Object Type Distribution")
                type_df = pd.DataFrame([
                    {'Type': k, 'Count': v}
                    for k, v in analysis['object_type_counts'].items()
                ])
                st.dataframe(type_df, hide_index=True, use_container_width=True)

            with col2:
                st.subheader("Lineage Metrics")
                st.metric("Max Dependency Depth", analysis['max_dependency_depth'])
                st.metric("Source Objects", analysis['source_object_count'])
                st.metric("Transactional Objects", analysis['transactional_objects'])

            # Source objects
            if analysis['source_objects']:
                st.subheader("Source Objects (Leaf Nodes)")
                source_df = pd.DataFrame(analysis['source_objects'])
                st.dataframe(source_df, hide_index=True, use_container_width=True)

        # Display lineage
        st.markdown("---")

        if display_mode in ["Flow Diagram", "Both"]:
            st.subheader("🌊 Data Flow Diagram")
            with st.container():
                render_flow_diagram(display_tree, max_depth=max_depth)

        if display_mode in ["Table View", "Both"]:
            st.subheader("📋 Table View")
            render_lineage_table(display_tree)

        # Export section
        st.markdown("---")
        st.subheader("💾 Export")

        col1, col2, col3 = st.columns(3)

        with col1:
            # Export full lineage as JSON
            analyzer = LineageAnalyzer(config)
            json_data = analyzer.export_lineage_json(display_tree)
            json_str = json.dumps(json_data, indent=2)

            st.download_button(
                label="📄 Download Full Lineage (JSON)",
                data=json_str,
                file_name=f"lineage_{obj_name}_{display_tree.fetched_at.strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )

        with col2:
            # Export dependency summary as CSV
            summary = analyzer.get_dependency_summary(display_tree)
            summary_df = pd.DataFrame(summary)
            csv = summary_df.to_csv(index=False)

            st.download_button(
                label="📊 Download Summary (CSV)",
                data=csv,
                file_name=f"lineage_summary_{obj_name}.csv",
                mime="text/csv"
            )

        with col3:
            # Export transactional lineage only
            if show_transactional_only:
                transactional_json = analyzer.export_lineage_json(display_tree)
            else:
                filtered = lineage_tree.get_transactional_lineage()
                if filtered:
                    transactional_json = analyzer.export_lineage_json(filtered)
                else:
                    transactional_json = {"message": "No transactional objects found"}

            trans_json_str = json.dumps(transactional_json, indent=2)

            st.download_button(
                label="🔄 Download Transactional Only (JSON)",
                data=trans_json_str,
                file_name=f"lineage_transactional_{obj_name}.json",
                mime="application/json"
            )

    else:
        # No lineage loaded yet - show instructions
        st.info("👆 Configure options in the sidebar and click 'Fetch Lineage' to start")

        st.markdown("""
        ### How to use:

        1. **Select Object**: Choose from cache dropdown or enter object ID manually
        2. **Configure Options**: Set lineage and display preferences
        3. **Fetch Lineage**: Click the button to fetch lineage from API
        4. **Analyze**: View tree/table visualization and detailed analysis
        5. **Export**: Download lineage data in JSON or CSV format

        ### Tips:
        - Enable **Transactional Only** to focus on data flows and transformations
        - Use **Tree View** to see hierarchical dependencies
        - Use **Table View** for a flat list with filtering capabilities
        - Adjust **Max Tree Depth** if the tree is too large to display
        """)

    # Show activity log in sidebar
    ActivityLogger.display()


if __name__ == "__main__":
    lineage_analyzer_page()
