"""
Smart Retry Decorator for NitroSense Ultimate.

Provides exponential backoff retry logic with error reporting.
"""

import time
import math
import traceback
import sys
from typing import Callable, Any
from functools import wraps
from ..core.logger import logger

def smart_retry(max_retries: int = 3, base_delay: float = 0.5, backoff_factor: float = 2.0):
    """
    Decorator that retries a function with exponential backoff on failure.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds
        backoff_factor: Multiplier for delay on each retry
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    if attempt < max_retries:
                        delay = base_delay * (backoff_factor ** attempt)
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_retries + 1} failed for {func.__name__}: {e}. "
                            f"Retrying in {delay:.1f}s..."
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"All {max_retries + 1} attempts failed for {func.__name__}: {e}"
                        )
                        _log_error_details(func, e)
                        raise e

            # This should never be reached, but just in case
            raise last_exception

        return wrapper
    return decorator

def _log_error_details(func: Callable, exception: Exception):
    """Log detailed error information for debugging."""
    try:
        exc_type, exc_value, exc_tb = sys.exc_info()
        tb = traceback.extract_tb(exc_tb)
        if tb:
            frame = tb[-1]  # Last frame
            logger.error(
                f"Error in {func.__name__} at {frame.filename}:{frame.lineno} - {exception}"
            )
    except Exception as log_error:
        logger.error(f"Failed to log error details: {log_error}")

# Convenience decorators for common use cases
retry_hardware = smart_retry(max_retries=5, base_delay=0.1, backoff_factor=1.5)
retry_network = smart_retry(max_retries=3, base_delay=1.0, backoff_factor=2.0)
retry_file_io = smart_retry(max_retries=2, base_delay=0.5, backoff_factor=1.0)