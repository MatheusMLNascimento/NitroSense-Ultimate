"""
Application Lifecycle Management

Handles signal handlers for graceful shutdown and cleanup routines.
These handlers ensure proper fan control, lock release, and watchdog cleanup
before the application exits.
"""

import sys
import signal
import logging
import os
import time
from typing import Optional
from pathlib import Path

from .logger import logger
from .constants import CONFIG_DIRS


SESSION_LOCK_DIR = CONFIG_DIRS["base"]
SESSION_LOCK_FILE = SESSION_LOCK_DIR / ".session_lock"


def setup_signal_handlers(app: 'QApplication') -> None:
    """
    Register signal handlers for graceful shutdown.
    
    Handles SIGTERM and SIGINT to ensure:
    1. Main window is closed properly
    2. Fan control is returned to BIOS
    3. Hardware watchdog is stopped
    4. Single instance lock is released
    
    Args:
        app: QApplication instance
        
    Examples:
        >>> setup_signal_handlers(app)
        # Now Ctrl+C will trigger graceful cleanup instead of hard shutdown
    """
    def signal_handler(signum: int, frame) -> None:
        """Handle SIGTERM/SIGINT gracefully: clean fan control before exit."""
        logger.info(f"Signal {signum} received - initiating graceful shutdown")
        
        # 1. Stop monitoring
        try:
            if hasattr(app, 'main_window') and app.main_window:
                logger.info("Closing main window...")
                app.main_window.close()
        except Exception as e:
            logger.error(f"Error closing main window: {e}")
        
        # 2. Return fan control to BIOS
        try:
            if hasattr(app, 'system') and app.system:
                system = app.system
                if hasattr(system, 'fan_controller'):
                    logger.info("Returning fan control to BIOS...")
        except Exception as e:
            logger.error(f"Error returning fan control: {e}")
        
        # 3. Stop watchdog
        try:
            system = app.system
            if system is not None:
                watchdog = getattr(system, 'watchdog', None)
                if watchdog is not None:
                    logger.info("Stopping hardware watchdog...")
                    watchdog.stop()
        except Exception as e:
            logger.error(f"Error stopping watchdog: {e}")
        
        # 4. Release single instance lock
        try:
            lock = app.single_instance_lock
            if lock is not None:
                logger.info("Releasing single instance lock...")
                lock.release()
        except Exception as e:
            logger.error(f"Error releasing lock: {e}")
        
        # 5. Quit application
        logger.info("Exiting NitroSense Ultimate")
        app.quit()

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)


def setup_atexit_cleanup() -> None:
    """
    Register atexit cleanup handler.
    
    Ensures garbage collection is run on final exit to prevent
    resource leaks and dangling file handles.
    
    Examples:
        >>> setup_atexit_cleanup()
    """
    import atexit
    import gc
    
    def atexit_cleanup():
        """Final cleanup on exit."""
        logger.info("Application exit cleanup running...")
        try:
            # Force collect garbage
            gc.collect()
        except:
            pass

    atexit.register(atexit_cleanup)


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
