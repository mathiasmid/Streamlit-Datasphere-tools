"""
SAP Datasphere API client with robust error handling and retry logic.

This module provides a unified interface for all Datasphere REST API operations,
including automatic token refresh, retry logic, and comprehensive error handling.
"""

import requests
import time
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .models import (
    AppConfig, APIError, DataspherObject, Space, LineageNode, LineageTree
)

# Configure logging
logger = logging.getLogger(__name__)


class DataspherAPIClient:
    """
    Client for SAP Datasphere REST API operations.

    Handles authentication, retries, error handling, and token refresh.
    """

    def __init__(self, config: AppConfig):
        """
        Initialize API client with configuration.

        Args:
            config: Application configuration containing credentials and URLs
        """
        self.config = config
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """
        Create requests session with retry logic.

        Returns:
            Configured requests session
        """
        session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=3,  # Max retries
            backoff_factor=1,  # Wait 1, 2, 4 seconds
            status_forcelist=[408, 429, 500, 502, 503, 504],  # Retry on these HTTP codes
            allowed_methods=["GET", "POST", "PUT", "DELETE"]
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def _get_headers(self) -> Dict[str, str]:
        """
        Get HTTP headers with authorization token.

        Returns:
            Headers dictionary

        Raises:
            APIError: If token is invalid or expired
        """
        if not self.config.is_token_valid():
            raise APIError("OAuth token is invalid or expired. Please refresh token.")

        return {
            "Authorization": f"Bearer {self.config.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """
        Make HTTP request to Datasphere API.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path (e.g., '/dwaas-core/api/v1/spaces')
            params: Query parameters
            data: Request body data
            timeout: Request timeout in seconds

        Returns:
            Response JSON data

        Raises:
            APIError: If request fails
        """
        url = f"{self.config.dsp_host}{endpoint}"
        headers = self._get_headers()

        try:
            logger.debug(f"API {method} request: {url}")

            response = self.session.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=data,
                timeout=timeout
            )

            # Check for HTTP errors
            if response.status_code == 401:
                raise APIError(
                    "Authentication failed. Token may be expired.",
                    status_code=401
                )
            elif response.status_code == 403:
                raise APIError(
                    "Access forbidden. Check permissions.",
                    status_code=403
                )
            elif response.status_code == 404:
                raise APIError(
                    f"Resource not found: {endpoint}",
                    status_code=404
                )
            elif response.status_code >= 400:
                error_msg = f"API request failed with status {response.status_code}"
                try:
                    error_data = response.json()
                    if 'message' in error_data:
                        error_msg += f": {error_data['message']}"
                except:
                    error_msg += f": {response.text[:200]}"

                raise APIError(error_msg, status_code=response.status_code)

            # Parse JSON response
            try:
                return response.json()
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                raise APIError(f"Invalid JSON response from API: {str(e)}")

        except requests.exceptions.Timeout:
            raise APIError(f"Request timeout after {timeout} seconds")
        except requests.exceptions.ConnectionError as e:
            raise APIError(f"Connection error: {str(e)}")
        except requests.exceptions.RequestException as e:
            raise APIError(f"Request failed: {str(e)}")

    def refresh_token(self) -> None:
        """
        Refresh OAuth access token using refresh token.

        Raises:
            APIError: If token refresh fails
        """
        if not self.config.refresh_token:
            raise APIError("No refresh token available. Please re-authenticate.")

        try:
            logger.info("Refreshing OAuth token...")

            response = requests.post(
                self.config.token_url,
                data={
                    'grant_type': 'refresh_token',
                    'refresh_token': self.config.refresh_token,
                    'client_id': self.config.client_id,
                    'client_secret': self.config.client_secret
                },
                timeout=30
            )

            if response.status_code != 200:
                raise APIError(
                    f"Token refresh failed with status {response.status_code}",
                    status_code=response.status_code
                )

            token_data = response.json()

            # Update config with new token
            self.config.access_token = token_data['access_token']
            self.config.refresh_token = token_data.get('refresh_token', self.config.refresh_token)
            self.config.token_expires_in = token_data.get('expires_in', 3600)
            self.config.token_expire_time = datetime.now() + timedelta(
                seconds=self.config.token_expires_in
            )

            logger.info("Token refreshed successfully")

        except requests.exceptions.RequestException as e:
            raise APIError(f"Token refresh request failed: {str(e)}")

    # ==================== Space Operations ====================

    def get_spaces(self) -> List[Space]:
        """
        Fetch all spaces from Datasphere.

        Returns:
            List of Space objects

        Raises:
            APIError: If request fails
        """
        try:
            data = self._make_request("GET", "/dwaas-core/api/v1/spaces")

            # Parse space list - API returns simple list of space ID strings
            spaces = []
            if isinstance(data, list):
                for space_item in data:
                    if isinstance(space_item, str):
                        # Simple string space ID (actual API format)
                        spaces.append(Space(
                            space_id=space_item,
                            business_name=None  # Will be filled from business names endpoint
                        ))
                    elif isinstance(space_item, dict):
                        # Dict format (fallback for different API versions)
                        spaces.append(Space(
                            space_id=space_item.get('spaceId', space_item.get('id', space_item.get('name', ''))),
                            business_name=space_item.get('label')
                        ))
                    else:
                        logger.warning(f"Skipping unexpected space data type: {type(space_item)}")
            elif isinstance(data, dict) and 'spaces' in data:
                # Fallback: wrapped format
                for space_item in data['spaces']:
                    if isinstance(space_item, str):
                        spaces.append(Space(space_id=space_item))
                    elif isinstance(space_item, dict):
                        spaces.append(Space(
                            space_id=space_item.get('spaceId', space_item.get('id', '')),
                            business_name=space_item.get('label')
                        ))
            else:
                logger.error(f"Unexpected spaces response format: {type(data)}")
                logger.debug(f"Spaces response data: {data}")

            logger.info(f"Fetched {len(spaces)} spaces")
            return spaces

        except APIError:
            raise
        except Exception as e:
            logger.error(f"Error parsing spaces: {str(e)}, data type: {type(data) if 'data' in locals() else 'unknown'}")
            raise APIError(f"Failed to parse spaces response: {str(e)}")

    def get_space_business_names(self) -> Dict[str, str]:
        """
        Fetch space business names (qualified name -> business name mapping).

        Returns:
            Dictionary mapping space IDs to business names

        Raises:
            APIError: If request fails
        """
        try:
            # Use correct endpoint with query parameters from url.json
            params = {
                'inSpaceManagement': 'true',
                'details': 'id,name,business_name'
            }
            data = self._make_request(
                "GET",
                "/dwaas-core/repository/spaces",
                params=params
            )

            # Parse business names - API returns {"results": [...]}
            business_names = {}

            # Handle {"results": [...]} format
            results = []
            if isinstance(data, dict) and 'results' in data:
                results = data.get('results', [])
            elif isinstance(data, list):
                results = data

            for space in results:
                if isinstance(space, dict):
                    # Use 'name' field as key (this is the space ID)
                    space_id = space.get('name') or space.get('qualifiedName')
                    business_name = space.get('businessName') or space.get('business_name')
                    if space_id and business_name:
                        business_names[space_id] = business_name

            logger.info(f"Fetched {len(business_names)} space business names")
            return business_names

        except APIError:
            raise
        except Exception as e:
            raise APIError(f"Failed to parse space business names: {str(e)}")

    # ==================== Object Operations ====================

    def get_space_objects(self, space_id: str) -> List[DataspherObject]:
        """
        Fetch all objects from a specific space.

        Args:
            space_id: Space ID to fetch objects from

        Returns:
            List of DataspherObject instances

        Raises:
            APIError: If request fails
        """
        try:
            data = self._make_request(
                "GET",
                f"/deepsea/repository/{space_id}/designObjects"
            )

            # Parse objects - handle both direct list and {'results': [...]} format
            objects = []
            object_list = []

            if isinstance(data, dict) and 'results' in data:
                # Response format: {'results': [...]}
                object_list = data.get('results', [])
            elif isinstance(data, list):
                # Response format: [...]
                object_list = data
            else:
                logger.warning(f"Unexpected object list format for space {space_id}: {type(data)}")

            for obj_data in object_list:
                if isinstance(obj_data, dict):
                    objects.append(DataspherObject(
                        technical_name=obj_data.get('technicalName') or obj_data.get('qualified_name') or obj_data.get('name', ''),
                        object_type=obj_data.get('kind', obj_data.get('type', 'unknown')),
                        space_id=space_id,
                        object_name=obj_data.get('name', obj_data.get('technicalName', '')),
                        object_id=obj_data.get('id')
                    ))
                else:
                    logger.warning(f"Skipping non-dict object data in space {space_id}: {obj_data}")

            logger.info(f"Fetched {len(objects)} objects from space {space_id}")
            return objects

        except APIError:
            raise
        except Exception as e:
            raise APIError(f"Failed to parse objects from space {space_id}: {str(e)}")

    def get_object_definition(self, space_id: str, object_name: str) -> Dict[str, Any]:
        """
        Fetch object JSON definition.

        Args:
            space_id: Space ID
            object_name: Object technical name

        Returns:
            Object definition JSON

        Raises:
            APIError: If request fails
        """
        try:
            data = self._make_request(
                "GET",
                f"/deepsea/repository/{space_id}/objects/{object_name}"
            )

            logger.info(f"Fetched definition for {object_name} in space {space_id}")
            return data

        except APIError:
            raise
        except Exception as e:
            raise APIError(f"Failed to fetch object definition: {str(e)}")

    def find_object_id_by_name(self, technical_name: str, space_id: Optional[str] = None) -> Optional[str]:
        """
        Find object ID by technical name.

        Searches through spaces to find an object with the given technical name
        and returns its ID.

        Args:
            technical_name: Object technical name to search for
            space_id: Optional space ID to limit search

        Returns:
            Object ID if found, None otherwise

        Raises:
            APIError: If request fails
        """
        try:
            # If space_id is provided, search only in that space
            if space_id:
                spaces_to_search = [Space(space_id=space_id)]
            else:
                # Otherwise, search all spaces
                spaces_to_search = self.get_spaces()

            # Search each space for the object
            for space in spaces_to_search:
                try:
                    objects = self.get_space_objects(space.space_id)

                    for obj in objects:
                        if obj.technical_name == technical_name:
                            if obj.object_id:
                                logger.info(f"Found object {technical_name} with ID {obj.object_id} in space {space.space_id}")
                                return obj.object_id

                except APIError as e:
                    # Skip spaces we can't access
                    logger.warning(f"Could not search space {space.space_id}: {e}")
                    continue

            logger.warning(f"Object {technical_name} not found in any accessible space")
            return None

        except APIError:
            raise
        except Exception as e:
            raise APIError(f"Failed to find object ID: {str(e)}")

    # ==================== Lineage Operations ====================

    def get_lineage(
        self,
        object_id: str,
        recursive: bool = True,
        impact: bool = True,
        lineage: bool = True,
        dependency_types: Optional[List[str]] = None
    ) -> LineageTree:
        """
        Fetch object lineage/dependencies.

        Args:
            object_id: Object ID (hex string)
            recursive: Include nested dependencies
            impact: Include impact analysis
            lineage: Include lineage
            dependency_types: List of dependency types to include (None = all)

        Returns:
            LineageTree with complete dependency graph

        Raises:
            APIError: If request fails
        """
        # Default dependency types (all relevant types)
        if dependency_types is None:
            dependency_types = [
                'sap.dis.target',
                'csn.entity.association',
                'csn.query.from',
                'sap.dis.source',
                'sap.dis.targetOf',
                'sap.dis.replicationflow.source',
                'sap.dis.replicationflow.targetOf',
                'sap.dwc.transformationflow.source',
                'sap.dwc.transformationflow.targetOf',
                'sap.dwc.idtEntity',
                'csn.derivation.lookupEntity',
                'csn.valueHelp.entity'
            ]

        try:
            params = {
                'ids': object_id,
                'recursive': str(recursive).lower(),
                'impact': str(impact).lower(),
                'lineage': str(lineage).lower(),
                'dependencyTypes': ','.join(dependency_types)
            }

            data = self._make_request(
                "GET",
                "/deepsea/repository/dependencies/",
                params=params,
                timeout=60  # Lineage can take longer
            )

            # Parse lineage response
            if isinstance(data, list) and len(data) > 0:
                root_data = data[0]
                root_node = self._parse_lineage_node(root_data)
                tree = LineageTree(root=root_node)

                logger.info(f"Fetched lineage for {object_id}: {tree.count_objects()} total objects")
                return tree
            else:
                raise APIError("Empty lineage response")

        except APIError:
            raise
        except Exception as e:
            raise APIError(f"Failed to parse lineage response: {str(e)}")

    def _parse_lineage_node(self, data: Dict[str, Any]) -> LineageNode:
        """
        Recursively parse lineage node from API response.

        Args:
            data: Lineage node data from API

        Returns:
            LineageNode instance
        """
        # Parse child dependencies recursively
        dependencies = []
        for dep_data in data.get('dependencies', []):
            dependencies.append(self._parse_lineage_node(dep_data))

        return LineageNode(
            id=data.get('id', ''),
            qualified_name=data.get('qualifiedName', ''),
            name=data.get('name', data.get('qualifiedName', '')),
            kind=data.get('kind', 'unknown'),
            folder_id=data.get('folderId', ''),
            dependency_type=data.get('dependencyType'),
            hash=data.get('hash'),
            impact=data.get('impact', False),
            lineage=data.get('lineage', True),
            dependencies=dependencies
        )

    # ==================== User Operations ====================

    def get_users(self) -> List[Dict[str, Any]]:
        """
        Fetch all users from Datasphere.

        Returns:
            List of user dictionaries

        Raises:
            APIError: If request fails
        """
        try:
            data = self._make_request("GET", "/dwaas-core/api/v1/users")

            users = []
            if isinstance(data, dict) and 'users' in data:
                users = data['users']
            elif isinstance(data, list):
                users = data

            logger.info(f"Fetched {len(users)} users")
            return users

        except APIError:
            raise
        except Exception as e:
            raise APIError(f"Failed to parse users response: {str(e)}")

    # ==================== Test Connection ====================

    def test_connection(self) -> Dict[str, Any]:
        """
        Test API connection and credentials.

        Returns:
            Dictionary with test results:
                - success: bool
                - message: str
                - details: dict (optional)

        Raises:
            APIError: If connection test fails
        """
        try:
            logger.info("Testing API connection...")

            # Try to fetch spaces as a simple test
            spaces = self.get_spaces()

            logger.info(f"API connection test successful: {len(spaces)} spaces found")
            return {
                'success': True,
                'message': f'Connection successful! Found {len(spaces)} spaces.',
                'details': {
                    'space_count': len(spaces),
                    'token_valid': self.config.is_token_valid()
                }
            }

        except APIError as e:
            logger.error(f"API connection test failed: {e.message}")
            return {
                'success': False,
                'message': f'Connection failed: {e.message}',
                'details': {
                    'status_code': e.status_code,
                    'error': str(e)
                }
            }
        except Exception as e:
            logger.error(f"Unexpected error in API connection test: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'Unexpected error: {str(e)}',
                'details': {'error': str(e)}
            }
