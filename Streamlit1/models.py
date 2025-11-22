"""
Data models for SAP Datasphere Tools application.

This module contains Pydantic models for type safety, validation,
and structured data handling throughout the application.
"""

from typing import Optional, List, Dict, Any, Literal, ClassVar
from datetime import datetime
from pydantic import BaseModel, Field, validator, ConfigDict
from enum import Enum


class ObjectType(str, Enum):
    """SAP Datasphere object types."""
    ENTITY = "entity"
    VIEW = "sap.dwc.view"
    GRAPHICAL_VIEW = "sap.dwc.graphicalview"
    SQL_VIEW = "sap.dwc.sqlview"
    ANALYTIC_VIEW = "sap.dwc.analyticview"
    LOCAL_TABLE = "sap.dwc.localtable"
    REMOTE_TABLE = "sap.dwc.remotetable"
    REPLICATION_FLOW = "sap.dis.replicationflow"
    TRANSFORMATION_FLOW = "sap.dis.transformationflow"
    DATA_FLOW = "sap.dwc.dataflow"
    TASK_CHAIN = "sap.dwc.taskchain"
    ANALYTIC_MODEL = "sap.dwc.analyticmodel"
    DATA_ACCESS_CONTROL = "sap.dwc.dataaccesscontrol"


class DependencyType(str, Enum):
    """Types of dependencies between objects."""
    TARGET = "sap.dis.target"
    SOURCE = "sap.dis.source"
    TARGET_OF = "sap.dis.targetOf"
    ASSOCIATION = "csn.entity.association"
    QUERY_FROM = "csn.query.from"
    REPLICATION_SOURCE = "sap.dis.replicationflow.source"
    REPLICATION_TARGET = "sap.dis.replicationflow.targetOf"
    TRANSFORMATION_SOURCE = "sap.dwc.transformationflow.source"
    TRANSFORMATION_TARGET = "sap.dwc.transformationflow.targetOf"
    IDT_ENTITY = "sap.dwc.idtEntity"
    LOOKUP_ENTITY = "csn.derivation.lookupEntity"
    VALUE_HELP = "csn.valueHelp.entity"


class Space(BaseModel):
    """Represents a SAP Datasphere space."""
    model_config = ConfigDict(str_strip_whitespace=True)

    space_id: str = Field(..., description="Technical space ID")
    business_name: Optional[str] = Field(None, description="User-friendly business name")

    def __str__(self) -> str:
        """String representation for display."""
        if self.business_name:
            return f"{self.space_id} [{self.business_name}]"
        return self.space_id


class DataspherObject(BaseModel):
    """Represents a SAP Datasphere object (view, table, flow, etc.)."""
    model_config = ConfigDict(str_strip_whitespace=True)

    technical_name: str = Field(..., description="Technical object name")
    object_type: str = Field(..., description="Object type (entity, view, flow, etc.)")
    space_id: str = Field(..., description="Space the object belongs to")
    object_name: Optional[str] = Field(None, description="Display name (usually same as technical_name)")
    object_id: Optional[str] = Field(None, description="Unique object ID (hex string)")

    @validator('object_name', always=True)
    def set_object_name(cls, v, values):
        """Default object_name to technical_name if not provided."""
        return v or values.get('technical_name')

    def __str__(self) -> str:
        """String representation for display."""
        return f"{self.technical_name} ({self.object_type})"


class CSNElement(BaseModel):
    """Represents a field/element in a CSN definition."""
    model_config = ConfigDict(extra='allow')  # Allow extra fields from CSN

    technical_name: str = Field(..., description="Field technical name")
    label: Optional[str] = Field(None, description="Business label (@EndUserText.label)")
    type: str = Field(..., description="CDS data type (e.g., cds.String)")
    length: Optional[int] = Field(None, description="Field length")
    key: bool = Field(False, description="Is this a key field?")
    not_null: bool = Field(False, description="Is this field required?")
    association: Optional[str] = Field(None, description="Associated object name")
    semantics: Dict[str, Any] = Field(default_factory=dict, description="Semantic annotations")

    @classmethod
    def from_csn(cls, technical_name: str, csn_data: Dict[str, Any]) -> 'CSNElement':
        """
        Create CSNElement from CSN JSON structure.

        Args:
            technical_name: Field name
            csn_data: CSN element definition

        Returns:
            CSNElement instance
        """
        # Extract label
        label = csn_data.get('@EndUserText.label')

        # Extract association
        association_data = csn_data.get('@ObjectModel.foreignKey.association', {})
        association = association_data.get('=') if isinstance(association_data, dict) else None

        # Extract semantics
        semantics = {
            k: v for k, v in csn_data.items()
            if k.startswith('@Semantics.')
        }

        return cls(
            technical_name=technical_name,
            label=label,
            type=csn_data.get('type', 'unknown'),
            length=csn_data.get('length'),
            key=csn_data.get('key', False),
            not_null=csn_data.get('notNull', False),
            association=association,
            semantics=semantics
        )


class CSNDefinition(BaseModel):
    """Represents a complete CSN object definition."""
    model_config = ConfigDict(extra='allow')

    object_name: str = Field(..., description="Object name")
    kind: str = Field(..., description="CSN kind (entity, view, etc.)")
    label: Optional[str] = Field(None, description="Object business label")
    elements: List[CSNElement] = Field(default_factory=list, description="Object fields/elements")
    exposed: bool = Field(False, description="Is object exposed for consumption?")

    @classmethod
    def from_csn(cls, object_name: str, csn_data: Dict[str, Any]) -> 'CSNDefinition':
        """
        Create CSNDefinition from CSN JSON structure.

        Args:
            object_name: Object name
            csn_data: CSN definition data

        Returns:
            CSNDefinition instance
        """
        # Extract label
        label = csn_data.get('@EndUserText.label')

        # Check if exposed
        exposed = csn_data.get('@DataWarehouse.consumption.external', False)

        # Parse elements
        elements_data = csn_data.get('elements', {})
        elements = [
            CSNElement.from_csn(elem_name, elem_data)
            for elem_name, elem_data in elements_data.items()
        ]

        return cls(
            object_name=object_name,
            kind=csn_data.get('kind', 'unknown'),
            label=label,
            elements=elements,
            exposed=exposed
        )


class LineageNode(BaseModel):
    """Represents a node in the lineage tree."""
    model_config = ConfigDict(extra='allow')

    id: str = Field(..., description="Object ID")
    qualified_name: str = Field(..., description="Object qualified name")
    name: str = Field(..., description="Display name")
    kind: str = Field(..., description="Object kind/type")
    folder_id: str = Field(..., description="Folder/space ID")
    dependency_type: Optional[str] = Field(None, description="Type of dependency to parent")
    hash: Optional[str] = Field(None, description="Object hash")
    impact: bool = Field(False, description="Is this an impact dependency?")
    lineage: bool = Field(True, description="Is this a lineage dependency?")
    dependencies: List['LineageNode'] = Field(default_factory=list, description="Child dependencies")

    # Transactional dependency types (main data flow)
    TRANSACTIONAL_DEPENDENCY_TYPES: ClassVar[set] = {
        'csn.query.from',                          # Main query/view source (PRIMARY!)
        'sap.dis.replicationflow.source',          # Replication source
        'sap.dis.replicationflow.targetOf',        # Replication target
        'sap.dwc.transformationflow.source',       # Transformation source
        'sap.dwc.transformationflow.targetOf',     # Transformation target
        'sap.dis.target',                          # Data flow target
        'sap.dis.source',                          # Data flow source
        'sap.dis.targetOf',                        # Target reference
    }

    # Dimensional dependency types (reference/lookup data)
    DIMENSIONAL_DEPENDENCY_TYPES: ClassVar[set] = {
        'csn.entity.association',                  # Foreign key association
        'csn.valueHelp.entity',                    # Value help/dropdown
        'csn.derivation.lookupEntity',             # Lookup entity
        'sap.dwc.idtEntity',                       # IDT entity reference
    }

    def is_transactional(self) -> bool:
        """
        Check if this dependency represents a transactional (data-modifying) flow.

        Uses dependency_type field to accurately distinguish between:
        - Transactional flows (csn.query.from, replication/transformation flows)
        - Dimensional lookups (csn.entity.association, value helps)

        Strategy:
        1. Check dependency_type first (most reliable)
        2. Fall back to object kind for root nodes
        3. Default to False for unknown types

        Returns:
            True if transactional data flow, False if dimensional/reference
        """
        # Root node (no dependency type): check object kind
        if not self.dependency_type:
            transactional_kinds = {
                'sap.dis.replicationflow',
                'sap.dis.transformationflow',
                'sap.dwc.dataflow',
                'sap.dwc.localtable'
            }
            return self.kind in transactional_kinds

        # Primary check: dependency type (MOST IMPORTANT!)
        if self.dependency_type in self.TRANSACTIONAL_DEPENDENCY_TYPES:
            return True

        if self.dependency_type in self.DIMENSIONAL_DEPENDENCY_TYPES:
            return False

        # Fallback: check object kind for unknown dependency types
        transactional_kinds = {
            'sap.dis.replicationflow',
            'sap.dis.transformationflow',
            'sap.dwc.dataflow'
        }

        return self.kind in transactional_kinds

    def get_all_nodes(self) -> List['LineageNode']:
        """
        Get all nodes in the tree (depth-first traversal).

        Returns:
            Flat list of all nodes
        """
        nodes = [self]
        for dep in self.dependencies:
            nodes.extend(dep.get_all_nodes())
        return nodes

    def filter_transactional(self) -> Optional['LineageNode']:
        """
        Filter lineage tree to only transactional (data flow) dependencies.

        Recursively follows ONLY transactional dependency chains (csn.query.from),
        excluding dimensional associations, value helps, and lookup entities.

        This accurately identifies the main data flow path from source to destination.

        Returns:
            New LineageNode with only transactional descendants, or None if no transactional path
        """
        # Recursively filter child dependencies
        # KEY CHANGE: Only recurse into transactional dependencies!
        filtered_deps = []
        for dep in self.dependencies:
            # Check if dependency is transactional BEFORE recursing
            if dep.is_transactional():
                filtered_dep = dep.filter_transactional()
                if filtered_dep:
                    filtered_deps.append(filtered_dep)

        # Root node: always include if has transactional descendants
        if not self.dependency_type:
            if filtered_deps:
                return LineageNode(
                    id=self.id,
                    qualified_name=self.qualified_name,
                    name=self.name,
                    kind=self.kind,
                    folder_id=self.folder_id,
                    dependency_type=self.dependency_type,
                    hash=self.hash,
                    impact=self.impact,
                    lineage=self.lineage,
                    dependencies=filtered_deps
                )
            return None

        # Child nodes: include if transactional OR has transactional descendants
        if self.is_transactional() or filtered_deps:
            return LineageNode(
                id=self.id,
                qualified_name=self.qualified_name,
                name=self.name,
                kind=self.kind,
                folder_id=self.folder_id,
                dependency_type=self.dependency_type,
                hash=self.hash,
                impact=self.impact,
                lineage=self.lineage,
                dependencies=filtered_deps
            )

        return None


class LineageTree(BaseModel):
    """Represents the complete lineage tree for an object."""
    root: LineageNode = Field(..., description="Root node of lineage tree")
    fetched_at: datetime = Field(default_factory=datetime.now, description="When lineage was fetched")

    def get_all_objects(self) -> List[LineageNode]:
        """Get flat list of all objects in lineage."""
        return self.root.get_all_nodes()

    def get_transactional_lineage(self) -> Optional['LineageTree']:
        """Get filtered tree with only transactional objects."""
        filtered_root = self.root.filter_transactional()
        if filtered_root:
            return LineageTree(root=filtered_root, fetched_at=self.fetched_at)
        return None

    def count_objects(self) -> int:
        """Count total objects in lineage."""
        return len(self.get_all_objects())

    def count_by_type(self) -> Dict[str, int]:
        """Count objects by type."""
        counts: Dict[str, int] = {}
        for node in self.get_all_objects():
            counts[node.kind] = counts.get(node.kind, 0) + 1
        return counts


class AppConfig(BaseModel):
    """Application configuration."""
    model_config = ConfigDict(str_strip_whitespace=True)

    # Datasphere settings
    dsp_host: str = Field(..., description="Datasphere host URL")
    dsp_space: Optional[str] = Field(None, description="Default space")

    # HANA database settings
    hdb_address: str = Field(..., description="HANA database address")
    hdb_port: int = Field(443, description="HANA database port")
    hdb_user: str = Field(..., description="HANA database user")
    hdb_password: str = Field(..., description="HANA database password")

    # OAuth settings
    client_id: str = Field(..., description="OAuth client ID")
    client_secret: str = Field(..., description="OAuth client secret")
    authorization_url: str = Field(..., description="OAuth authorization URL")
    token_url: str = Field(..., description="OAuth token URL")

    # OAuth token
    access_token: Optional[str] = Field(None, description="OAuth access token")
    refresh_token: Optional[str] = Field(None, description="OAuth refresh token")
    token_expires_in: Optional[int] = Field(None, description="Token expiry in seconds")
    token_expire_time: Optional[datetime] = Field(None, description="Token expiration timestamp")

    @validator('dsp_host')
    def validate_host(cls, v):
        """Ensure host URL is valid."""
        if not v.startswith('http://') and not v.startswith('https://'):
            raise ValueError('Host must start with http:// or https://')
        return v.rstrip('/')

    def is_token_valid(self) -> bool:
        """Check if OAuth token is valid and not expired."""
        if not self.access_token or not self.token_expire_time:
            return False
        return datetime.now() < self.token_expire_time

    def to_dict(self, exclude_secrets: bool = False) -> Dict[str, Any]:
        """
        Convert config to dictionary.

        Args:
            exclude_secrets: If True, exclude sensitive fields

        Returns:
            Dictionary representation
        """
        data = self.model_dump()
        if exclude_secrets:
            data.pop('hdb_password', None)
            data.pop('client_secret', None)
            data.pop('access_token', None)
            data.pop('refresh_token', None)
        return data


class CacheMetadata(BaseModel):
    """Metadata about cached data."""
    loaded: bool = Field(False, description="Is cache loaded?")
    loading: bool = Field(False, description="Is cache currently loading?")
    timestamp: Optional[datetime] = Field(None, description="When cache was loaded")
    error: Optional[str] = Field(None, description="Error message if load failed")
    object_count: int = Field(0, description="Number of objects cached")
    space_count: int = Field(0, description="Number of spaces cached")

    def age_minutes(self) -> Optional[float]:
        """Get cache age in minutes."""
        if self.timestamp:
            delta = datetime.now() - self.timestamp
            return delta.total_seconds() / 60
        return None


class APIError(Exception):
    """Custom exception for API errors."""
    def __init__(self, message: str, status_code: Optional[int] = None, response: Optional[Dict] = None):
        self.message = message
        self.status_code = status_code
        self.response = response
        super().__init__(self.message)


class DatabaseError(Exception):
    """Custom exception for database errors."""
    def __init__(self, message: str, query: Optional[str] = None):
        self.message = message
        self.query = query
        super().__init__(self.message)


class ConfigurationError(Exception):
    """Custom exception for configuration errors."""
    pass
