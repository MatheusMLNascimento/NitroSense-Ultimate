"""
Global Exception Handlers

Sets up surgical exception logging and crash reporting for the application.
These handlers catch ALL unhandled exceptions before they crash the app.
"""

import sys
import threading
import traceback
from typing import Optional, Type

from .logger import logger
from .hotkeys import CrashReporter


def setup_global_exception_handlers(app: Optional['QApplication'] = None) -> None:
    """
    Setup all global exception handlers.
    
    Registers handlers for:
    - sys.excepthook (main thread exceptions)
    - threading.excepthook (thread exceptions)  
    - sys.unraisablehook (unraisable exceptions)
    
    Args:
        app: Optional QApplication instance for context
        
    Examples:
        >>> from PyQt6.QtWidgets import QApplication
        >>> app = QApplication([])
        >>> setup_global_exception_handlers(app)
    """
    sys.excepthook = _global_exception_hook
    threading.excepthook = _thread_exception_handler
    sys.unraisablehook = _unraisable_exception_hook


def _global_exception_hook(exc_type: Type[BaseException], exc_value: BaseException, exc_traceback) -> None:
    """
    Handle unhandled exceptions in the main thread.
    
    Logs detailed surgical error information and generates crash reports.
    Does NOT raise KeyboardInterrupt (allows clean Ctrl+C exit).
    
    Args:
        exc_type: Exception type
        exc_value: Exception instance
        exc_traceback: Traceback object
        
    Implementation:
        1. Ignore KeyboardInterrupt (allows Ctrl+C)
        2. Log surgical error details (file, line, locals)
        3. Generate crash report with telemetry
        4. Log resolution hints
    """
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    # SURGICAL LOGGING
    logger.critical("=" * 70)
    logger.critical("UNHANDLED EXCEPTION - SURGICAL ERROR LOG")
    logger.critical("=" * 70)
    logger.critical(f"Module: {exc_traceback.tb_frame.f_globals.get('__name__', 'unknown')}")
    logger.critical(f"Function: {exc_traceback.tb_frame.f_code.co_name}")
    logger.critical(f"Line {exc_traceback.tb_lineno}: {exc_traceback.tb_frame.f_code.co_filename}")
    logger.critical(f"Exception Type: {exc_type.__name__}")
    logger.critical(f"Exception Message: {exc_value}")
    
    # Log last 5 local variables
    frame = exc_traceback.tb_frame
    logger.critical("Local variables (last 5):")
    for var, value in list(frame.f_locals.items())[-5:]:
        try:
            logger.critical(f"  {var} = {repr(value)[:100]}")
        except:
            logger.critical(f"  {var} = <unprintable>")
    
    logger.critical("=" * 70)
    logger.critical("RESOLUTION HINTS:")
    logger.critical("  • Check system permissions (may need sudo)")
    logger.critical("  • Verify hardware sensor paths exist")
    logger.critical("  • Check disk space and write permissions")
    logger.critical("  • Review full traceback in logs directory")
    logger.critical("=" * 70)
    
    # Generate pre-death crash report with telemetry
    try:
        tb_str = traceback.format_exc()
        crash_report_path = CrashReporter.generate_crash_report(exc_value, tb_str)
        if crash_report_path:
            logger.critical(f"Crash report saved: {crash_report_path}")
    except Exception as e:
        logger.error(f"Failed to generate crash report: {e}")


def _thread_exception_handler(args: threading.ExceptHookArgs) -> None:
    """
    Handle unhandled exceptions in worker threads.
    
    Args:
        args: ExceptHookArgs containing exc_type, exc_value, exc_traceback, thread
        
    Implementation:
        Logs thread name, ID, and full exception details
    """
    exc_value = args.exc_value or Exception("Unknown thread exception")
    logger.critical(
        f"THREAD EXCEPTION (thread={args.thread.name}, id={args.thread.ident}): "
        f"{args.exc_type.__name__}: {exc_value}",
        exc_info=(args.exc_type, exc_value, args.exc_traceback),
    )


def _unraisable_exception_hook(unraisable) -> None:
    """
    Handle exceptions that can't be raised normally (e.g., in __del__ finalizers).
    
    Args:
        unraisable: UnraisableException object
        
    Implementation:
        Logs exception details with context information
    """
    logger.error(
        f"Unraisable exception: {unraisable.exc_value}",
        exc_info=(
            getattr(unraisable, 'exc_type', None),
            getattr(unraisable, 'exc_value', None),
            getattr(unraisable, 'exc_traceback', None)
        ),
    )
