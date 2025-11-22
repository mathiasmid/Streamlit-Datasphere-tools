"""
Lineage analysis and management for SAP Datasphere objects.

Provides functions to fetch, parse, filter, and analyze object lineage.
"""

import logging
from typing import Optional, Dict, Any, List

from .models import AppConfig, LineageTree, LineageNode
from .api_client import DataspherAPIClient
from .error_handler import ActivityLogger

logger = logging.getLogger(__name__)


class LineageAnalyzer:
    """
    Analyzer for SAP Datasphere object lineage.

    Fetches lineage from API and provides analysis capabilities.
    """

    def __init__(self, config: AppConfig):
        """
        Initialize lineage analyzer.

        Args:
            config: Application configuration
        """
        self.config = config
        self.api_client = DataspherAPIClient(config)

    def fetch_lineage(
        self,
        object_id: str,
        object_name: Optional[str] = None,
        recursive: bool = True,
        include_impact: bool = True
    ) -> LineageTree:
        """
        Fetch complete lineage for an object.

        Args:
            object_id: Object ID (hex string)
            object_name: Optional object name for logging
            recursive: Include nested dependencies
            include_impact: Include impact analysis

        Returns:
            LineageTree with complete dependency graph

        Raises:
            APIError: If API call fails
        """
        logger.info(f"Fetching lineage for {object_name or object_id}")
        ActivityLogger.log(f"Fetching lineage for {object_name or object_id}", "info")

        lineage_tree = self.api_client.get_lineage(
            object_id=object_id,
            recursive=recursive,
            impact=include_impact,
            lineage=True
        )

        logger.info(f"Fetched lineage: {lineage_tree.count_objects()} total objects")
        ActivityLogger.log(
            f"Lineage loaded: {lineage_tree.count_objects()} objects",
            "success"
        )

        return lineage_tree

    def get_transactional_lineage(self, lineage_tree: LineageTree) -> Optional[LineageTree]:
        """
        Filter lineage to show only transactional (data-modifying) objects.

        Transactional objects include:
        - Replication Flows
        - Transformation Flows
        - Data Flows
        - Local Tables (with write operations)

        Args:
            lineage_tree: Complete lineage tree

        Returns:
            Filtered lineage tree or None if no transactional objects
        """
        logger.info("Filtering for transactional lineage")

        filtered_tree = lineage_tree.get_transactional_lineage()

        if filtered_tree:
            count = filtered_tree.count_objects()
            logger.info(f"Transactional lineage: {count} objects")
            ActivityLogger.log(f"Filtered to {count} transactional objects", "info")
            return filtered_tree
        else:
            logger.info("No transactional objects found in lineage")
            ActivityLogger.log("No transactional objects found", "warning")
            return None

    def analyze_lineage(self, lineage_tree: LineageTree) -> Dict[str, Any]:
        """
        Analyze lineage tree and return statistics.

        Args:
            lineage_tree: Lineage tree to analyze

        Returns:
            Dictionary with analysis results
        """
        all_objects = lineage_tree.get_all_objects()
        object_count = len(all_objects)
        type_counts = lineage_tree.count_by_type()

        # Count transactional vs non-transactional
        transactional_count = sum(1 for obj in all_objects if obj.is_transactional())
        non_transactional_count = object_count - transactional_count

        # Get dependency depth
        max_depth = self._calculate_max_depth(lineage_tree.root)

        # Identify source objects (no dependencies)
        source_objects = [
            obj for obj in all_objects
            if not obj.dependencies
        ]

        analysis = {
            'total_objects': object_count,
            'transactional_objects': transactional_count,
            'non_transactional_objects': non_transactional_count,
            'max_dependency_depth': max_depth,
            'source_object_count': len(source_objects),
            'object_type_counts': type_counts,
            'source_objects': [
                {'name': obj.name, 'kind': obj.kind}
                for obj in source_objects[:10]  # Limit to 10
            ]
        }

        logger.info(f"Lineage analysis: {analysis}")
        return analysis

    def _calculate_max_depth(self, node: LineageNode, current_depth: int = 0) -> int:
        """
        Calculate maximum depth of lineage tree.

        Args:
            node: Current node
            current_depth: Current depth level

        Returns:
            Maximum depth
        """
        if not node.dependencies:
            return current_depth

        max_child_depth = current_depth
        for dep in node.dependencies:
            child_depth = self._calculate_max_depth(dep, current_depth + 1)
            max_child_depth = max(max_child_depth, child_depth)

        return max_child_depth

    def get_lineage_path(
        self,
        lineage_tree: LineageTree,
        target_object_name: str
    ) -> Optional[List[LineageNode]]:
        """
        Find path from root to a specific object in lineage.

        Args:
            lineage_tree: Lineage tree to search
            target_object_name: Target object name

        Returns:
            List of nodes representing the path, or None if not found
        """
        path = []
        if self._find_path(lineage_tree.root, target_object_name, path):
            return path
        return None

    def _find_path(
        self,
        node: LineageNode,
        target_name: str,
        path: List[LineageNode]
    ) -> bool:
        """
        Recursive helper to find path to target object.

        Args:
            node: Current node
            target_name: Target object name
            path: Current path (modified in place)

        Returns:
            True if target found in this branch
        """
        path.append(node)

        if node.qualified_name == target_name or node.name == target_name:
            return True

        for dep in node.dependencies:
            if self._find_path(dep, target_name, path):
                return True

        path.pop()
        return False

    def export_lineage_json(self, lineage_tree: LineageTree) -> Dict[str, Any]:
        """
        Export lineage tree to JSON-serializable format.

        Args:
            lineage_tree: Lineage tree to export

        Returns:
            Dictionary representation
        """
        return {
            'root': self._node_to_dict(lineage_tree.root),
            'fetched_at': lineage_tree.fetched_at.isoformat(),
            'statistics': self.analyze_lineage(lineage_tree)
        }

    def _node_to_dict(self, node: LineageNode) -> Dict[str, Any]:
        """
        Convert LineageNode to dictionary recursively.

        Args:
            node: Node to convert

        Returns:
            Dictionary representation
        """
        return {
            'id': node.id,
            'qualified_name': node.qualified_name,
            'name': node.name,
            'kind': node.kind,
            'folder_id': node.folder_id,
            'dependency_type': node.dependency_type,
            'is_transactional': node.is_transactional(),
            'dependencies': [
                self._node_to_dict(dep)
                for dep in node.dependencies
            ]
        }

    def get_dependency_summary(self, lineage_tree: LineageTree) -> List[Dict[str, Any]]:
        """
        Get flat list of all dependencies with metadata.

        Args:
            lineage_tree: Lineage tree

        Returns:
            List of dependency dictionaries
        """
        all_objects = lineage_tree.get_all_objects()

        summary = []
        for obj in all_objects:
            summary.append({
                'name': obj.name,
                'qualified_name': obj.qualified_name,
                'kind': obj.kind,
                'dependency_type': obj.dependency_type,
                'is_transactional': obj.is_transactional(),
                'dependency_count': len(obj.dependencies),
                'folder_id': obj.folder_id
            })

        return summary


def identify_data_flow_path(lineage_tree: LineageTree) -> List[str]:
    """
    Identify the main data flow path through transactional objects.

    Traces the path from source systems to final target through
    replication flows, transformation flows, etc.

    Args:
        lineage_tree: Complete lineage tree

    Returns:
        List of object names in flow order
    """
    flow_path = []

    def traverse_transactional(node: LineageNode):
        """Recursively traverse only transactional nodes."""
        if node.is_transactional():
            flow_path.append(node.qualified_name)

        for dep in node.dependencies:
            traverse_transactional(dep)

    traverse_transactional(lineage_tree.root)

    return flow_path


def get_source_systems(lineage_tree: LineageTree) -> List[str]:
    """
    Identify source systems in lineage (leaf nodes).

    Args:
        lineage_tree: Lineage tree

    Returns:
        List of source object names
    """
    all_objects = lineage_tree.get_all_objects()

    source_objects = [
        obj.qualified_name
        for obj in all_objects
        if not obj.dependencies  # Leaf nodes
    ]

    return source_objects


def categorize_lineage_objects(lineage_tree: LineageTree) -> Dict[str, List[str]]:
    """
    Categorize lineage objects by type.

    Args:
        lineage_tree: Lineage tree

    Returns:
        Dictionary with categories as keys and object lists as values
    """
    categories = {
        'replication_flows': [],
        'transformation_flows': [],
        'views': [],
        'tables': [],
        'other': []
    }

    for obj in lineage_tree.get_all_objects():
        kind = obj.kind.lower()

        if 'replicationflow' in kind:
            categories['replication_flows'].append(obj.qualified_name)
        elif 'transformationflow' in kind:
            categories['transformation_flows'].append(obj.qualified_name)
        elif 'view' in kind:
            categories['views'].append(obj.qualified_name)
        elif 'table' in kind:
            categories['tables'].append(obj.qualified_name)
        else:
            categories['other'].append(obj.qualified_name)

    return categories
