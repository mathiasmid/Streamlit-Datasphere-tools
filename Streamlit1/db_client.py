"""
SAP HANA database client with connection pooling and safe query execution.

This module provides a robust interface for HANA database operations,
including proper resource management, parameterized queries, and error handling.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from contextlib import contextmanager
from hdbcli import dbapi

from .models import AppConfig, DatabaseError, CSNDefinition

# Configure logging
logger = logging.getLogger(__name__)


class HANAClient:
    """
    Client for SAP HANA database operations.

    Provides connection management, parameterized queries, and CSN parsing.
    """

    def __init__(self, config: AppConfig):
        """
        Initialize HANA client with configuration.

        Args:
            config: Application configuration containing database credentials
        """
        self.config = config
        self._connection: Optional[dbapi.Connection] = None

    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections.

        Ensures proper connection cleanup even if errors occur.

        Yields:
            Database connection

        Raises:
            DatabaseError: If connection fails

        Example:
            >>> with client.get_connection() as conn:
            ...     cursor = conn.cursor()
            ...     cursor.execute("SELECT * FROM table")
        """
        connection = None
        try:
            logger.debug(f"Connecting to HANA at {self.config.hdb_address}:{self.config.hdb_port}")

            connection = dbapi.connect(
                address=self.config.hdb_address,
                port=self.config.hdb_port,
                user=self.config.hdb_user,
                password=self.config.hdb_password,
                encrypt=True,  # Use encryption
                sslValidateCertificate=False  # May need adjustment based on setup
            )

            logger.debug("HANA connection established")
            yield connection

        except dbapi.Error as e:
            error_msg = f"Database connection failed: {str(e)}"
            logger.error(error_msg)
            raise DatabaseError(error_msg)

        finally:
            if connection:
                try:
                    connection.close()
                    logger.debug("HANA connection closed")
                except Exception as e:
                    logger.warning(f"Error closing connection: {e}")

    def execute_query(
        self,
        query: str,
        params: Optional[Tuple] = None,
        fetch_size: Optional[int] = None
    ) -> List[Tuple]:
        """
        Execute SQL query with parameterized inputs.

        Args:
            query: SQL query with ? placeholders for parameters
            params: Tuple of parameter values
            fetch_size: Number of rows to fetch (None = all)

        Returns:
            List of result tuples

        Raises:
            DatabaseError: If query execution fails

        Example:
            >>> results = client.execute_query(
            ...     "SELECT * FROM table WHERE id = ?",
            ...     params=("123",)
            ... )
        """
        with self.get_connection() as conn:
            try:
                cursor = conn.cursor()

                logger.debug(f"Executing query: {query[:100]}...")
                if params:
                    logger.debug(f"Parameters: {params}")

                cursor.execute(query, params or ())

                # Fetch results
                if fetch_size:
                    results = cursor.fetchmany(fetch_size)
                else:
                    results = cursor.fetchall()

                logger.debug(f"Query returned {len(results)} rows")
                return results

            except dbapi.Error as e:
                error_msg = f"Query execution failed: {str(e)}"
                logger.error(error_msg)
                logger.error(f"Query: {query}")
                if params:
                    logger.error(f"Params: {params}")
                raise DatabaseError(error_msg, query=query)

    def execute_query_dict(
        self,
        query: str,
        params: Optional[Tuple] = None,
        fetch_size: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute SQL query and return results as dictionaries.

        Args:
            query: SQL query with ? placeholders
            params: Tuple of parameter values
            fetch_size: Number of rows to fetch (None = all)

        Returns:
            List of result dictionaries (column_name: value)

        Raises:
            DatabaseError: If query execution fails
        """
        with self.get_connection() as conn:
            try:
                cursor = conn.cursor()

                logger.debug(f"Executing query: {query[:100]}...")
                cursor.execute(query, params or ())

                # Get column names
                column_names = [desc[0] for desc in cursor.description]

                # Fetch results
                if fetch_size:
                    rows = cursor.fetchmany(fetch_size)
                else:
                    rows = cursor.fetchall()

                # Convert to dictionaries
                results = [
                    dict(zip(column_names, row))
                    for row in rows
                ]

                logger.debug(f"Query returned {len(results)} rows")
                return results

            except dbapi.Error as e:
                error_msg = f"Query execution failed: {str(e)}"
                logger.error(error_msg)
                raise DatabaseError(error_msg, query=query)

    # ==================== Space Operations ====================

    def get_spaces(self) -> List[Tuple[str]]:
        """
        Fetch all spaces from HANA SPACE_SCHEMAS table.

        Returns:
            List of tuples containing space IDs

        Raises:
            DatabaseError: If query fails
        """
        query = """
            SELECT DISTINCT SPACE_ID
            FROM SPACE_SCHEMAS
            ORDER BY SPACE_ID
        """

        try:
            results = self.execute_query(query)
            logger.info(f"Fetched {len(results)} spaces from database")
            return results

        except DatabaseError:
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to fetch spaces: {str(e)}")

    # ==================== Object/CSN Operations ====================

    def get_csn_definitions(self, space_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch CSN definitions from $$DEPLOY_ARTIFACTS$$ table.

        Args:
            space_id: Optional space filter

        Returns:
            List of CSN definition dictionaries

        Raises:
            DatabaseError: If query fails
        """
        if space_id:
            query = """
                SELECT ARTIFACT_NAME, ARTIFACT
                FROM "$$DEPLOY_ARTIFACTS$$"
                WHERE SCHEMA_NAME = ?
                ORDER BY ARTIFACT_NAME
            """
            params = (f"{space_id}$TEC",)
        else:
            query = """
                SELECT ARTIFACT_NAME, ARTIFACT, SCHEMA_NAME
                FROM "$$DEPLOY_ARTIFACTS$$"
                ORDER BY SCHEMA_NAME, ARTIFACT_NAME
            """
            params = None

        try:
            results = self.execute_query_dict(query, params)
            logger.info(f"Fetched {len(results)} CSN definitions")
            return results

        except DatabaseError:
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to fetch CSN definitions: {str(e)}")

    def get_object_csn(self, space_id: str, object_name: str) -> Optional[CSNDefinition]:
        """
        Fetch and parse CSN definition for a specific object.

        Args:
            space_id: Space ID
            object_name: Object technical name

        Returns:
            CSNDefinition instance or None if not found

        Raises:
            DatabaseError: If query fails
        """
        query = """
            SELECT ARTIFACT
            FROM "$$DEPLOY_ARTIFACTS$$"
            WHERE SCHEMA_NAME = ?
            AND ARTIFACT_NAME = ?
        """

        schema_name = f"{space_id}$TEC"
        params = (schema_name, object_name)

        try:
            results = self.execute_query(query, params)

            if not results:
                logger.warning(f"No CSN found for {object_name} in {space_id}")
                return None

            # Parse CSN JSON
            csn_json = results[0][0]
            if isinstance(csn_json, str):
                import json
                csn_data = json.loads(csn_json)
            else:
                csn_data = csn_json

            # Extract object definition from CSN
            definitions = csn_data.get('definitions', {})
            if object_name in definitions:
                csn_def = CSNDefinition.from_csn(object_name, definitions[object_name])
                logger.info(f"Parsed CSN for {object_name}: {len(csn_def.elements)} fields")
                return csn_def

            logger.warning(f"Object {object_name} not found in CSN definitions")
            return None

        except DatabaseError:
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to parse CSN for {object_name}: {str(e)}")

    # ==================== Dependency Operations ====================

    def get_object_dependencies(
        self,
        space_id: str,
        object_name: str
    ) -> List[Dict[str, Any]]:
        """
        Fetch object dependencies from OBJECT_DEPENDENCIES table.

        Args:
            space_id: Space ID
            object_name: Object technical name

        Returns:
            List of dependency dictionaries

        Raises:
            DatabaseError: If query fails
        """
        query = """
            SELECT
                BASE_SCHEMA_NAME,
                BASE_OBJECT_NAME,
                DEPENDENT_SCHEMA_NAME,
                DEPENDENT_OBJECT_NAME,
                DEPENDENCY_TYPE
            FROM OBJECT_DEPENDENCIES
            WHERE BASE_SCHEMA_NAME = ?
            AND BASE_OBJECT_NAME = ?
        """

        schema_name = f"{space_id}$TEC"
        params = (schema_name, object_name)

        try:
            results = self.execute_query_dict(query, params)
            logger.info(f"Found {len(results)} dependencies for {object_name}")
            return results

        except DatabaseError:
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to fetch dependencies: {str(e)}")

    # ==================== Column Search Operations ====================

    def find_column_usage(
        self,
        column_name: str,
        space_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Find all objects using a specific column.

        Args:
            column_name: Column name to search for
            space_id: Optional space filter

        Returns:
            List of objects containing the column

        Raises:
            DatabaseError: If query fails
        """
        if space_id:
            query = """
                SELECT
                    SCHEMA_NAME,
                    TABLE_NAME,
                    COLUMN_NAME,
                    DATA_TYPE_NAME,
                    LENGTH
                FROM M_CS_COLUMNS
                WHERE COLUMN_NAME = ?
                AND SCHEMA_NAME = ?
                ORDER BY TABLE_NAME
            """
            params = (column_name, f"{space_id}$TEC")
        else:
            query = """
                SELECT
                    SCHEMA_NAME,
                    TABLE_NAME,
                    COLUMN_NAME,
                    DATA_TYPE_NAME,
                    LENGTH
                FROM M_CS_COLUMNS
                WHERE COLUMN_NAME = ?
                ORDER BY SCHEMA_NAME, TABLE_NAME
            """
            params = (column_name,)

        try:
            results = self.execute_query_dict(query, params)
            logger.info(f"Found {len(results)} objects using column {column_name}")
            return results

        except DatabaseError:
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to find column usage: {str(e)}")

    def get_table_columns(
        self,
        space_id: str,
        table_name: str
    ) -> List[Dict[str, Any]]:
        """
        Get all columns for a specific table.

        Args:
            space_id: Space ID
            table_name: Table name

        Returns:
            List of column definitions

        Raises:
            DatabaseError: If query fails
        """
        query = """
            SELECT
                COLUMN_NAME,
                POSITION,
                DATA_TYPE_NAME,
                LENGTH,
                SCALE,
                IS_NULLABLE
            FROM M_CS_COLUMNS
            WHERE SCHEMA_NAME = ?
            AND TABLE_NAME = ?
            ORDER BY POSITION
        """

        schema_name = f"{space_id}$TEC"
        params = (schema_name, table_name)

        try:
            results = self.execute_query_dict(query, params)
            logger.info(f"Found {len(results)} columns for {table_name}")
            return results

        except DatabaseError:
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to fetch table columns: {str(e)}")

    # ==================== Test Connection ====================

    def test_connection(self) -> Dict[str, Any]:
        """
        Test database connection.

        Returns:
            Dictionary with test results:
                - success: bool
                - message: str
                - details: dict (optional)
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT CURRENT_USER, CURRENT_SCHEMA FROM DUMMY")
                result = cursor.fetchone()

                return {
                    'success': True,
                    'message': f'Database connection successful! Connected as {result[0]}',
                    'details': {
                        'user': result[0],
                        'schema': result[1]
                    }
                }

        except DatabaseError as e:
            return {
                'success': False,
                'message': f'Database connection failed: {e.message}',
                'details': {'error': str(e)}
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Unexpected error: {str(e)}',
                'details': {'error': str(e)}
            }
