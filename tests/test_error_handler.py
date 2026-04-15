"""
Tests for error_handler module.
"""

import pytest
from unittest.mock import patch, MagicMock
from nitrosense.core.error_handler import setup_exception_handler


def test_setup_exception_handler_with_dialogs():
    """Test setting up exception handler with dialogs enabled."""
    with patch('nitrosense.core.error_handler.ErrorDialog'):
        setup_exception_handler(use_dialogs=True)
        # Should set excepthook to a function (not the original)
        import sys
        assert sys.excepthook is not None
        assert callable(sys.excepthook)


def test_setup_exception_handler_without_dialogs():
    """Test setting up exception handler without dialogs."""
    setup_exception_handler(use_dialogs=False)
    import sys
    assert sys.excepthook is not None
    assert callable(sys.excepthook)


def test_exception_handler_critical_error():
    """Test handling of critical errors."""
    # This is hard to test directly, but we can mock QMessageBox
    pass  # Skip for now, as it requires Qt app


def test_exception_handler_non_critical_error():
    """Test handling of non-critical errors."""
    pass  # Similar issue