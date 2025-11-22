"""
Error handling utilities for Streamlit application.

Provides decorators and utilities for consistent error handling
and user-friendly error display throughout the application.
"""

import logging
import traceback
import functools
from typing import Callable, Any, Optional
import streamlit as st

from .models import APIError, DatabaseError, ConfigurationError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def display_error(
    message: str,
    error: Optional[Exception] = None,
    show_details: bool = False
):
    """
    Display error message to user in Streamlit.

    Args:
        message: User-friendly error message
        error: Optional exception object
        show_details: Show technical details in expander
    """
    st.error(f"❌ {message}")

    if error and show_details:
        with st.expander("Technical Details"):
            st.code(str(error))
            if hasattr(error, '__traceback__'):
                st.code(traceback.format_exc())


def display_warning(message: str):
    """Display warning message to user."""
    st.warning(f"⚠️ {message}")


def display_success(message: str):
    """Display success message to user."""
    st.success(f"✅ {message}")


def display_info(message: str):
    """Display info message to user."""
    st.info(f"ℹ️ {message}")


def handle_errors(
    show_traceback: bool = False,
    default_message: str = "An error occurred"
) -> Callable:
    """
    Decorator for handling errors in Streamlit page functions.

    Catches exceptions, logs them, and displays user-friendly messages.

    Args:
        show_traceback: Show technical details to user
        default_message: Default error message if none specified

    Returns:
        Decorated function

    Example:
        >>> @handle_errors(show_traceback=True)
        >>> def my_page():
        ...     # Page code that might raise exceptions
        ...     pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)

            except ConfigurationError as e:
                logger.error(f"Configuration error in {func.__name__}: {e}")
                display_error(
                    "Configuration Error: Please check your settings.",
                    error=e,
                    show_details=show_traceback
                )
                st.info("💡 Go to Settings page to configure the application.")

            except APIError as e:
                logger.error(f"API error in {func.__name__}: {e}")

                # Provide specific guidance based on error
                if e.status_code == 401:
                    display_error(
                        "Authentication failed. Your token may have expired.",
                        error=e,
                        show_details=show_traceback
                    )
                    st.info("💡 Go to Settings → OAuth to refresh your token.")

                elif e.status_code == 403:
                    display_error(
                        "Access forbidden. You don't have permission for this operation.",
                        error=e,
                        show_details=show_traceback
                    )

                elif e.status_code == 404:
                    display_error(
                        "Resource not found. The object or endpoint may not exist.",
                        error=e,
                        show_details=show_traceback
                    )

                else:
                    display_error(
                        f"API Error: {e.message}",
                        error=e,
                        show_details=show_traceback
                    )

            except DatabaseError as e:
                logger.error(f"Database error in {func.__name__}: {e}")
                display_error(
                    "Database Error: Failed to execute database query.",
                    error=e,
                    show_details=show_traceback
                )
                st.info("💡 Check your database connection settings.")

            except ValueError as e:
                logger.error(f"Value error in {func.__name__}: {e}")
                display_error(
                    f"Invalid input: {str(e)}",
                    error=e,
                    show_details=show_traceback
                )

            except FileNotFoundError as e:
                logger.error(f"File not found in {func.__name__}: {e}")
                display_error(
                    f"File not found: {str(e)}",
                    error=e,
                    show_details=show_traceback
                )

            except Exception as e:
                logger.error(f"Unexpected error in {func.__name__}: {e}", exc_info=True)
                display_error(
                    default_message,
                    error=e,
                    show_details=show_traceback
                )

        return wrapper
    return decorator


def safe_execute(
    func: Callable,
    error_message: str = "Operation failed",
    default_return: Any = None,
    log_errors: bool = True
) -> Any:
    """
    Safely execute a function and return default value on error.

    Useful for non-critical operations where you want to continue
    execution even if something fails.

    Args:
        func: Function to execute
        error_message: Error message to display
        default_return: Value to return on error
        log_errors: Log errors to file

    Returns:
        Function result or default_return on error

    Example:
        >>> result = safe_execute(
        ...     lambda: api_client.get_spaces(),
        ...     error_message="Failed to load spaces",
        ...     default_return=[]
        ... )
    """
    try:
        return func()

    except Exception as e:
        if log_errors:
            logger.warning(f"{error_message}: {e}")

        display_warning(error_message)
        return default_return


def require_config(config_keys: list) -> Callable:
    """
    Decorator to ensure required configuration is present.

    Args:
        config_keys: List of required session state keys

    Returns:
        Decorated function

    Example:
        >>> @require_config(['dsp_host', 'hdb_address'])
        >>> def my_page():
        ...     # This will only run if config is set
        ...     pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            missing_keys = [
                key for key in config_keys
                if not st.session_state.get(key)
            ]

            if missing_keys:
                st.warning(
                    f"⚠️ Configuration incomplete. Missing: {', '.join(missing_keys)}"
                )
                st.info("💡 Please go to Settings page to configure the application.")
                return None

            return func(*args, **kwargs)

        return wrapper
    return decorator


def with_spinner(message: str = "Loading...") -> Callable:
    """
    Decorator to show spinner during function execution.

    Args:
        message: Spinner message

    Returns:
        Decorated function

    Example:
        >>> @with_spinner("Fetching data...")
        >>> def fetch_data():
        ...     return api_client.get_spaces()
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            with st.spinner(message):
                return func(*args, **kwargs)

        return wrapper
    return decorator


class ActivityLogger:
    """
    Simple activity logger for tracking user actions.

    Maintains a log of activities in session state for display to user.
    """

    @staticmethod
    def log(message: str, level: str = "info"):
        """
        Log an activity message.

        Args:
            message: Activity message
            level: Log level (info, warning, error, success)
        """
        if 'activity_log' not in st.session_state:
            st.session_state['activity_log'] = []

        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")

        st.session_state['activity_log'].append({
            'timestamp': timestamp,
            'message': message,
            'level': level
        })

        # Keep only last 50 entries
        if len(st.session_state['activity_log']) > 50:
            st.session_state['activity_log'] = st.session_state['activity_log'][-50:]

        # Also log to file
        logger.info(f"Activity: {message}")

    @staticmethod
    def display():
        """Display activity log in sidebar."""
        if 'activity_log' in st.session_state and st.session_state['activity_log']:
            with st.sidebar.expander("📋 Activity Log", expanded=False):
                for entry in reversed(st.session_state['activity_log'][-10:]):
                    icon = {
                        'info': 'ℹ️',
                        'warning': '⚠️',
                        'error': '❌',
                        'success': '✅'
                    }.get(entry['level'], 'ℹ️')

                    st.text(f"{entry['timestamp']} {icon} {entry['message']}")

    @staticmethod
    def clear():
        """Clear activity log."""
        st.session_state['activity_log'] = []


def validate_input(
    value: Any,
    validator: Callable[[Any], bool],
    error_message: str
) -> bool:
    """
    Validate input and display error if invalid.

    Args:
        value: Value to validate
        validator: Validation function returning bool
        error_message: Error message to display if invalid

    Returns:
        True if valid, False otherwise

    Example:
        >>> if validate_input(
        ...     space_name,
        ...     lambda x: len(x) > 0,
        ...     "Space name cannot be empty"
        ... ):
        ...     # Process valid input
        ...     pass
    """
    try:
        if validator(value):
            return True
        else:
            display_error(error_message)
            return False

    except Exception as e:
        display_error(f"{error_message}: {str(e)}")
        return False
