"""
Enhanced Cache Manager for SAP Datasphere Tools.

Features:
- Non-blocking background loading with progress tracking
- All features work without cache (fallback to direct API/DB calls)
- Global cache availability across all tools
- Type-safe using Pydantic models
"""

import streamlit as st
import logging
from datetime import datetime
from typing import List, Optional, Dict, Tuple

from .models import Space, DataspherObject, CacheMetadata, AppConfig
from .api_client import DataspherAPIClient
from .error_handler import ActivityLogger

logger = logging.getLogger(__name__)


# Cache availability flag - set to True when ready
CACHE_AVAILABLE = True


class CacheManager:
    """
    Manages caching of spaces and objects with progress tracking.

    All features work without cache - this just improves performance.
    """

    # Cache keys
    SPACES_LIST_KEY = 'cache_spaces_list'
    SPACES_NAMES_KEY = 'cache_spaces_names'
    ALL_OBJECTS_KEY = 'cache_all_objects'
    SPACE_STATS_KEY = 'cache_space_stats'  # Per-space statistics
    METADATA_KEY = 'cache_metadata'
    PROGRESS_KEY = 'cache_progress'
    PROGRESS_MSG_KEY = 'cache_progress_msg'
    PROGRESS_DETAIL_KEY = 'cache_progress_detail'

    @staticmethod
    def initialize_cache():
        """Initialize cache state in session."""
        if CacheManager.METADATA_KEY not in st.session_state:
            st.session_state[CacheManager.METADATA_KEY] = CacheMetadata()

        if CacheManager.PROGRESS_KEY not in st.session_state:
            st.session_state[CacheManager.PROGRESS_KEY] = 0

        if CacheManager.PROGRESS_MSG_KEY not in st.session_state:
            st.session_state[CacheManager.PROGRESS_MSG_KEY] = ""

        if CacheManager.PROGRESS_DETAIL_KEY not in st.session_state:
            st.session_state[CacheManager.PROGRESS_DETAIL_KEY] = []

    @staticmethod
    def is_cache_loaded() -> bool:
        """Check if cache is loaded and ready."""
        metadata: CacheMetadata = st.session_state.get(CacheManager.METADATA_KEY)
        return metadata and metadata.loaded

    @staticmethod
    def is_cache_loading() -> bool:
        """Check if cache is currently loading."""
        metadata: CacheMetadata = st.session_state.get(CacheManager.METADATA_KEY)
        return metadata and metadata.loading

    @staticmethod
    def get_cache_metadata() -> CacheMetadata:
        """Get cache metadata."""
        return st.session_state.get(CacheManager.METADATA_KEY, CacheMetadata())

    @staticmethod
    def set_progress(percent: int, message: str, detail: Optional[str] = None):
        """
        Update progress tracking.

        Args:
            percent: Progress percentage (0-100)
            message: Progress message
            detail: Optional detail message to log
        """
        st.session_state[CacheManager.PROGRESS_KEY] = percent
        st.session_state[CacheManager.PROGRESS_MSG_KEY] = message

        if detail:
            details = st.session_state.get(CacheManager.PROGRESS_DETAIL_KEY, [])
            details.append(detail)
            # Keep only last 20 details
            if len(details) > 20:
                details = details[-20:]
            st.session_state[CacheManager.PROGRESS_DETAIL_KEY] = details

            ActivityLogger.log(detail, "info")

    @staticmethod
    def load_cache(config: AppConfig) -> bool:
        """
        Load all cache data with progress tracking.

        Args:
            config: Application configuration

        Returns:
            True if successful, False otherwise
        """
        try:
            # Update metadata - loading started
            metadata = CacheMetadata(loading=True, loaded=False, error=None)
            st.session_state[CacheManager.METADATA_KEY] = metadata

            # Create API client
            api_client = DataspherAPIClient(config)

            # Progress 0-10%: Initialize
            CacheManager.set_progress(5, "Initializing cache load...", "Starting cache load")

            # Progress 10-30%: Fetch spaces
            CacheManager.set_progress(10, "Fetching spaces list...", "Requesting spaces from API")
            spaces = api_client.get_spaces()
            st.session_state[CacheManager.SPACES_LIST_KEY] = spaces

            CacheManager.set_progress(20, f"Loaded {len(spaces)} spaces", f"Found {len(spaces)} spaces")

            # Progress 30-40%: Fetch space business names
            CacheManager.set_progress(30, "Fetching space business names...", "Requesting space metadata")
            business_names = api_client.get_space_business_names()
            st.session_state[CacheManager.SPACES_NAMES_KEY] = business_names

            CacheManager.set_progress(40, f"Loaded {len(business_names)} space names",
                                    f"Loaded business names for {len(business_names)} spaces")

            # Progress 40-100%: Fetch objects from all spaces
            all_objects: List[DataspherObject] = []
            space_stats = {}  # Track per-space statistics
            total_spaces = len(spaces)
            successful_spaces = 0
            failed_spaces = 0

            for idx, space in enumerate(spaces):
                space_id = space.space_id
                progress = 40 + int((idx / total_spaces) * 60)

                CacheManager.set_progress(
                    progress,
                    f"Loading {space_id} ({idx+1}/{total_spaces})...",
                    f"Fetching objects from space: {space_id}"
                )

                try:
                    objects = api_client.get_space_objects(space_id)
                    all_objects.extend(objects)

                    # Track space statistics
                    space_stats[space_id] = {
                        'object_count': len(objects),
                        'status': 'success',
                        'error': None
                    }
                    successful_spaces += 1

                    CacheManager.set_progress(
                        progress,
                        f"✓ {space_id}: {len(objects)} objects ({idx+1}/{total_spaces})",
                        f"Loaded {len(objects)} objects from {space_id}"
                    )

                except Exception as e:
                    logger.warning(f"Failed to load objects from {space_id}: {e}")

                    # Track failed space
                    space_stats[space_id] = {
                        'object_count': 0,
                        'status': 'error',
                        'error': str(e)[:100]
                    }
                    failed_spaces += 1

                    CacheManager.set_progress(
                        progress,
                        f"✗ {space_id}: Error ({idx+1}/{total_spaces})",
                        f"Error loading {space_id}: {str(e)[:100]}"
                    )

            # Store space statistics
            st.session_state[CacheManager.SPACE_STATS_KEY] = space_stats

            # Store all objects
            st.session_state[CacheManager.ALL_OBJECTS_KEY] = all_objects

            # Progress 100%: Complete
            summary_msg = f"✓ {successful_spaces} spaces, ✗ {failed_spaces} failed, {len(all_objects)} total objects"
            CacheManager.set_progress(100, "Cache loading complete!",
                                    f"Loaded {len(all_objects)} objects from {successful_spaces}/{total_spaces} spaces")

            # Update metadata - loading complete
            metadata = CacheMetadata(
                loaded=True,
                loading=False,
                timestamp=datetime.now(),
                error=None,
                object_count=len(all_objects),
                space_count=successful_spaces  # Only count successful spaces
            )
            st.session_state[CacheManager.METADATA_KEY] = metadata

            ActivityLogger.log(f"Cache loaded: {summary_msg}", "success")

            return True

        except Exception as e:
            logger.error(f"Cache loading failed: {e}", exc_info=True)

            # Update metadata - loading failed
            metadata = CacheMetadata(
                loaded=False,
                loading=False,
                error=str(e)
            )
            st.session_state[CacheManager.METADATA_KEY] = metadata

            ActivityLogger.log(f"Cache loading failed: {str(e)}", "error")

            return False

    @staticmethod
    def clear_cache():
        """Clear all cached data."""
        st.session_state[CacheManager.SPACES_LIST_KEY] = None
        st.session_state[CacheManager.SPACES_NAMES_KEY] = None
        st.session_state[CacheManager.ALL_OBJECTS_KEY] = None
        st.session_state[CacheManager.SPACE_STATS_KEY] = {}
        st.session_state[CacheManager.METADATA_KEY] = CacheMetadata()
        st.session_state[CacheManager.PROGRESS_KEY] = 0
        st.session_state[CacheManager.PROGRESS_MSG_KEY] = ""
        st.session_state[CacheManager.PROGRESS_DETAIL_KEY] = []

        ActivityLogger.log("Cache cleared", "info")

    # ==================== Cache Getters ====================

    @staticmethod
    def get_cached_spaces() -> Optional[List[Space]]:
        """Get cached spaces list."""
        if CacheManager.is_cache_loaded():
            return st.session_state.get(CacheManager.SPACES_LIST_KEY)
        return None

    @staticmethod
    def get_cached_space_names() -> Optional[Dict[str, str]]:
        """Get cached space business names."""
        if CacheManager.is_cache_loaded():
            return st.session_state.get(CacheManager.SPACES_NAMES_KEY)
        return None

    @staticmethod
    def get_cached_objects() -> Optional[List[DataspherObject]]:
        """Get all cached objects."""
        if CacheManager.is_cache_loaded():
            return st.session_state.get(CacheManager.ALL_OBJECTS_KEY)
        return None

    @staticmethod
    def get_cached_objects_by_space(space_id: str) -> Optional[List[DataspherObject]]:
        """
        Get cached objects for a specific space.

        Args:
            space_id: Space ID to filter by

        Returns:
            List of objects in the space, or None if cache not loaded
        """
        all_objects = CacheManager.get_cached_objects()
        if all_objects:
            return [obj for obj in all_objects if obj.space_id == space_id]
        return None

    @staticmethod
    def find_object_by_name(object_name: str) -> Optional[DataspherObject]:
        """
        Find an object by technical name in cache.

        Args:
            object_name: Object technical name

        Returns:
            DataspherObject if found, None otherwise
        """
        all_objects = CacheManager.get_cached_objects()
        if all_objects:
            for obj in all_objects:
                if obj.technical_name == object_name:
                    return obj
        return None

    # ==================== V1 Compatibility Methods ====================

    @staticmethod
    def is_config_ready() -> bool:
        """
        Check if configuration is ready (V1 compatibility).

        Checks for old session state keys for backward compatibility.
        """
        # Check if V2 config exists
        if 'app_config' in st.session_state:
            config = st.session_state['app_config']
            return config and config.dsp_host and config.access_token

        # Check old V1 session state keys
        required_keys = ['dsp_host', 'token', 'secret']
        for key in required_keys:
            value = st.session_state.get(key)
            if not value or value == '':
                return False
        return True

    @staticmethod
    def get_cache_stats() -> Dict:
        """
        Get cache statistics (V1 compatibility).

        Returns dict with: loaded, loading, total_spaces, total_objects, timestamp, error, progress
        """
        metadata = CacheManager.get_cache_metadata()

        # Count spaces
        spaces = st.session_state.get(CacheManager.SPACES_LIST_KEY, [])
        total_spaces = len(spaces) if spaces else 0

        # Get progress
        progress = st.session_state.get(CacheManager.PROGRESS_KEY, 0)
        progress_msg = st.session_state.get(CacheManager.PROGRESS_MSG_KEY, "")

        return {
            'loaded': metadata.loaded,
            'loading': metadata.loading,
            'total_spaces': total_spaces,
            'total_objects': metadata.object_count,
            'spaces_with_objects': total_spaces,  # Approximation
            'timestamp': metadata.timestamp,
            'error': metadata.error,
            'progress': progress,
            'progress_message': progress_msg
        }

    @staticmethod
    def get_progress() -> Tuple[int, str]:
        """
        Get current progress (V1 compatibility).

        Returns:
            Tuple of (progress_percent, message)
        """
        progress = st.session_state.get(CacheManager.PROGRESS_KEY, 0)
        message = st.session_state.get(CacheManager.PROGRESS_MSG_KEY, "")
        return (progress, message)

    @staticmethod
    def get_progress_details() -> List[str]:
        """
        Get detailed progress log (V1 compatibility).

        Returns:
            List of progress detail messages
        """
        return st.session_state.get(CacheManager.PROGRESS_DETAIL_KEY, [])

    @staticmethod
    def get_cached_objects_v1(space_id=None) -> List[Dict]:
        """
        Get cached objects in V1 dict format (V1 compatibility).

        Args:
            space_id: Optional space ID to filter by

        Returns:
            List of object dictionaries
        """
        if space_id:
            objects = CacheManager.get_cached_objects_by_space(space_id)
        else:
            objects = CacheManager.get_cached_objects()

        if not objects:
            return []

        # Convert Pydantic models to dicts for V1 compatibility
        return [
            {
                'technicalName': obj.technical_name,
                'object_type': obj.object_type,
                'space_id': obj.space_id,
                'object_name': obj.object_name
            }
            for obj in objects
        ]

    @staticmethod
    def start_cache_load():
        """
        Prepare cache loading (V1 compatibility).

        Sets loading flag to true. Actual loading happens in load_all_cache_with_progress().
        """
        metadata = CacheMetadata(loading=True, loaded=False, error=None)
        st.session_state[CacheManager.METADATA_KEY] = metadata
        CacheManager.set_progress(0, "Starting cache load...", "Initializing")

    @staticmethod
    def load_all_cache_with_progress() -> bool:
        """
        Load cache with progress tracking (V1 compatibility).

        This is a wrapper for the V2 load_cache() method.
        Requires app_config in session state with V2 configuration.

        Returns:
            True if successful, False otherwise
        """
        # Check if V2 config exists
        if 'app_config' not in st.session_state:
            logger.error("No app_config found in session state")
            metadata = CacheMetadata(loaded=False, loading=False, error="No configuration found")
            st.session_state[CacheManager.METADATA_KEY] = metadata
            return False

        config = st.session_state['app_config']
        return CacheManager.load_cache(config)


def get_list_of_space_cached() -> List[Tuple[str]]:
    """
    Get list of spaces from cache or fallback to database.

    Returns:
        List of tuples containing space IDs
    """
    if CACHE_AVAILABLE and CacheManager.is_cache_loaded():
        spaces = CacheManager.get_cached_spaces()
        if spaces:
            return [(space.space_id,) for space in spaces]

    # Fallback to database query
    import utils
    return utils.get_list_of_space()


def get_space_business_names_cached() -> Dict[str, str]:
    """
    Get space business names from cache or fallback to API.

    Returns:
        Dictionary mapping space IDs to business names
    """
    if CACHE_AVAILABLE and CacheManager.is_cache_loaded():
        names = CacheManager.get_cached_space_names()
        if names:
            return names

    # Fallback to API
    import utils
    return utils.get_space_business_names()


def get_all_objects_cached() -> List[Dict]:
    """
    Get all objects from cache or fallback to database.

    Returns:
        List of object dictionaries
    """
    if CACHE_AVAILABLE and CacheManager.is_cache_loaded():
        objects = CacheManager.get_cached_objects()
        if objects:
            # Convert to dict format for backward compatibility
            return [
                {
                    'technicalName': obj.technical_name,
                    'object_type': obj.object_type,
                    'space_id': obj.space_id,
                    'object_name': obj.object_name
                }
                for obj in objects
            ]

    # Fallback to database query
    import utils
    return utils.get_all_objects()


# V1 Compatibility - add alias for old function name
get_space_names_cached = get_space_business_names_cached
