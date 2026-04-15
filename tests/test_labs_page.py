"""
Tests for labs_page module.
"""

import pytest
from unittest.mock import patch, MagicMock
from PyQt6.QtWidgets import QApplication
from nitrosense.ui.pages.labs_page import LabsPage


def test_labs_page_initialization():
    """Test initialization of labs page."""
    app = QApplication.instance() or QApplication([])
    with patch('nitrosense.ui.pages.labs_page.SecurityAndDiagnostics'):
        page = LabsPage(None, None)
        assert page is not None


def test_labs_page_run_diagnostic():
    """Test running diagnostic report generation."""
    app = QApplication.instance() or QApplication([])
    with patch('nitrosense.ui.pages.labs_page.SecurityAndDiagnostics') as mock_diag:
        mock_diag.return_value.generate_diagnostic_report.return_value = (0, "/path")
        page = LabsPage(None, None)
        page._generate_report()
        # Should not raise


def test_labs_page_create_test_button():
    """Test creating status block."""
    app = QApplication.instance() or QApplication([])
    with patch('nitrosense.ui.pages.labs_page.SecurityAndDiagnostics'), patch('nitrosense.ui.pages.labs_page.QFrame'), patch('nitrosense.ui.pages.labs_page.QVBoxLayout'), patch('nitrosense.ui.pages.labs_page.QLabel'), patch('nitrosense.ui.pages.labs_page.QHBoxLayout'):
        page = LabsPage(None, None)
        block = page._create_status_block("Test Block", "test", "T")
        assert block is not None


def test_labs_page_update_progress():
    """Test updating status block."""
    app = QApplication.instance() or QApplication([])
    with patch('nitrosense.ui.pages.labs_page.SecurityAndDiagnostics'), patch('nitrosense.ui.pages.labs_page.QFrame'), patch('nitrosense.ui.pages.labs_page.QVBoxLayout'), patch('nitrosense.ui.pages.labs_page.QLabel'), patch('nitrosense.ui.pages.labs_page.QHBoxLayout'):
        page = LabsPage(None, None)
        # Create a mock block
        mock_block = MagicMock()
        page.test_blocks = {'test': mock_block}
        page._update_block('test', True, 'Passed', 'Details')
        # Should not raise