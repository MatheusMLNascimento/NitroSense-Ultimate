"""
Tests for main_window module.
"""

import pytest
from unittest.mock import patch, MagicMock
from nitrosense.ui.main_window import NitroSenseApp


def test_main_window_initialization():
    """Test initialization of main window."""
    with patch('nitrosense.ui.main_window.QVBoxLayout'), patch('nitrosense.ui.main_window.QHBoxLayout'), patch('nitrosense.ui.main_window.QStackedWidget'), patch('nitrosense.ui.main_window.QStatusBar'), patch('nitrosense.ui.main_window.QScrollArea'), patch('nitrosense.ui.main_window.ToastManager'):
        window = NitroSenseApp(None)
        assert window is not None


def test_main_window_setup_ui():
    """Test setting up UI."""
    with patch('nitrosense.ui.main_window.QVBoxLayout'), patch('nitrosense.ui.main_window.QHBoxLayout'), patch('nitrosense.ui.main_window.QGuiApplication'), patch('nitrosense.ui.main_window.QStackedWidget'), patch('nitrosense.ui.main_window.QStatusBar'), patch('nitrosense.ui.main_window.QScrollArea'), patch('nitrosense.ui.main_window.ToastManager'):
        window = NitroSenseApp(None)
        window._init_ui()
        # Should not raise


def test_main_window_create_menu_bar():
    """Test creating menu bar - method doesn't exist, skipping."""
    # This method doesn't exist in the current implementation
    pass


def test_main_window_show_page():
    """Test showing a page."""
    with patch('nitrosense.ui.main_window.QVBoxLayout'), patch('nitrosense.ui.main_window.QHBoxLayout'), patch('nitrosense.ui.main_window.QStackedWidget'), patch('nitrosense.ui.main_window.QStatusBar'), patch('nitrosense.ui.main_window.QScrollArea'), patch('nitrosense.ui.main_window.ToastManager'):
        window = NitroSenseApp(None)
        window._switch_page(0)
        # Should not raise