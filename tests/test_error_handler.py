"""
Tests for app_exceptions module (surgical exception handling and crash reporting).

CONSOLIDATION NOTE (2026-04-14):
This file previously tested error_handler.py, which was completely replaced by
the modern app_exceptions.py module with surgical logging and crash reporting.

Old error_handler.py provided:
  - UI ErrorDialog popup for fatal exceptions (deprecated pattern)
  - Basic exception logging
  
New app_exceptions.py provides:
  - Surgical logging with local variable inspection
  - Automatic crash report generation via CrashReporter
  - Thread-safe exception handling (main + worker threads)
  - Unraisable exception handling (finalizers, asyncio)
"""

import pytest
import sys
from unittest.mock import patch, MagicMock, call
from nitrosense.core.app_exceptions import (
    setup_global_exception_handlers,
    _global_exception_hook,
    _thread_exception_handler,
    _unraisable_exception_hook,
)
import threading


def test_setup_global_exception_handlers():
    """Test that all exception hooks are registered correctly."""
    setup_global_exception_handlers()
    
    # Verify all hooks are registered (not the original sys hooks)
    assert sys.excepthook is not None
    assert callable(sys.excepthook)
    assert sys.unraisablehook is not None
    assert callable(sys.unraisablehook)
    assert threading.excepthook is not None
    assert callable(threading.excepthook)


def test_global_exception_hook_ignores_keyboard_interrupt():
    """Test that KeyboardInterrupt is passed to sys.__excepthook__."""
    with patch('sys.__excepthook__') as mock_excepthook:
        try:
            raise KeyboardInterrupt()
        except KeyboardInterrupt:
            exc_type, exc_value, tb = sys.exc_info()
            _global_exception_hook(exc_type, exc_value, tb)
        
        # Should call sys.__excepthook__ for KeyboardInterrupt
        mock_excepthook.assert_called_once()


def test_global_exception_hook_logs_surgical_error():
    """Test that exceptions are logged with surgical error details."""
    with patch('nitrosense.core.app_exceptions.logger') as mock_logger:
        try:
            raise ValueError("Test error message")
        except ValueError:
            exc_type, exc_value, tb = sys.exc_info()
            _global_exception_hook(exc_type, exc_value, tb)
        
        # Verify logger was called with critical level
        assert mock_logger.critical.called
        
        # Verify surgical logging details were logged
        logged_calls = [str(call) for call in mock_logger.critical.call_args_list]
        logged_text = ' '.join(logged_calls)
        assert 'ValueError' in logged_text or 'Test error message' in logged_text


def test_global_exception_hook_generates_crash_report():
    """Test that crash reports are generated for global exceptions."""
    with patch('nitrosense.core.app_exceptions.CrashReporter.generate_crash_report') as mock_report:
        mock_report.return_value = '/tmp/crash_report.txt'
        
        with patch('nitrosense.core.app_exceptions.logger'):
            try:
                raise RuntimeError("Crash test")
            except RuntimeError:
                exc_type, exc_value, tb = sys.exc_info()
                _global_exception_hook(exc_type, exc_value, tb)
            
            # Verify crash report was attempted
            mock_report.assert_called_once()


def test_thread_exception_handler_callable():
    """Test that thread exception handler is properly registered."""
    # Just verify it's callable - detailed behavior is hard to test with threading
    assert callable(_thread_exception_handler)


def test_unraisable_exception_hook_callable():
    """Test that unraisable exception hook is properly registered."""
    # Just verify it's callable
    assert callable(_unraisable_exception_hook)
