"""
Tests for status_page module.
"""

import pytest
from unittest.mock import patch, MagicMock
from PyQt6.QtWidgets import QApplication
from nitrosense.ui.pages.status_page import StatusPage


def test_status_page_initialization():
    """Test initialization of status page."""
    app = QApplication.instance() or QApplication([])
    with patch('nitrosense.ui.pages.status_page.MonitoringEngine'):
        page = StatusPage(None, None)
        assert page is not None


def test_status_page_update_status():
    """Test updating status."""
    app = QApplication.instance() or QApplication([])
    with patch('nitrosense.ui.pages.status_page.MonitoringEngine') as mock_monitoring:
        mock_monitoring.return_value.get_system_metrics.return_value = {'cpu_temp': 50}
        page = StatusPage(None, None)
        page._update_status()
        # Should not raise


def test_status_page_create_status_item():
    """Test creating status block."""
    app = QApplication.instance() or QApplication([])
    with patch('nitrosense.ui.pages.status_page.MonitoringEngine'), patch('nitrosense.ui.pages.status_page.QLabel'), patch('nitrosense.ui.pages.status_page.QFrame'), patch('nitrosense.ui.pages.status_page.QVBoxLayout'), patch('nitrosense.ui.pages.status_page.QHBoxLayout'):
        page = StatusPage(None, None)
        item = page._create_status_block("CPU", "cpu", "CPU")
        assert item is not None


def test_status_page_get_status_color():
    """Test getting status color - method doesn't exist, skipping."""
    # This method doesn't exist in the current implementation
    pass