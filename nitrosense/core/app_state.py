"""
Application State Management

Handles session locks, crash detection, and application-level state persistence.
These functions are called early in the startup sequence before QApplication.
"""

import os
import time
from pathlib import Path
from typing import Optional

from .logger import logger


SESSION_LOCK_DIR = Path.home() / ".config" / "nitrosense"
SESSION_LOCK_FILE = SESSION_LOCK_DIR / ".session_lock"


def ensure_session_lock() -> None:
    """
    Create a session lock file to detect unexpected shutdowns.
    
    This file is used to determine if the previous execution crashed.
    Format: pid=<pid>\nstarted=<timestamp>\n
    
    Raises:
        Any file system exceptions are logged but not raised
        
    Examples:
        >>> ensure_session_lock()  # Creates ~/.config/nitrosense/.session_lock
    """
    try:
        SESSION_LOCK_DIR.mkdir(parents=True, exist_ok=True)
        SESSION_LOCK_FILE.write_text(
            f"pid={os.getpid()}\nstarted={time.time()}\n",
            encoding="utf-8",
        )
        logger.info(f"Session lock created: {SESSION_LOCK_FILE}")
    except Exception as exc:
        logger.warning(f"Unable to create session lock: {exc}")


def clear_session_lock() -> None:
    """
    Remove the session lock file on clean shutdown.
    
    This should be called in atexit handlers to ensure proper cleanup.
    
    Examples:
        >>> clear_session_lock()
    """
    try:
        SESSION_LOCK_FILE.unlink(missing_ok=True)
        logger.info("Session lock cleared")
    except Exception as exc:
        logger.warning(f"Unable to clear session lock: {exc}")


def check_previous_crash() -> bool:
    """
    Return True if the previous app instance terminated unexpectedly.
    
    If the session lock file exists, it means the app didn't exit cleanly
    in the previous run. This triggers crash recovery mode in the UI.
    
    Returns:
        True if previous session lock found (crash detected)
        False if previous shutdown was clean
        
    Raises:
        Exceptions are logged but not raised
        
    Examples:
        >>> if check_previous_crash():
        ...     print("Enabling crash recovery mode")
    """
    try:
        if SESSION_LOCK_FILE.exists():
            logger.warning("Previous session lock found, last shutdown may have been unclean")
            return True
    except Exception as exc:
        logger.warning(f"Unable to verify previous crash state: {exc}")
    return False
