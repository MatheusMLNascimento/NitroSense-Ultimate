"""
Tests for config_page module.
"""

import pytest
from unittest.mock import patch, MagicMock
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QPoint
from nitrosense.ui.pages.config_page import ConfigPage


def test_config_page_initialization():
    """Test initialization of config page."""
    app = QApplication.instance() or QApplication([])
    with patch('nitrosense.ui.pages.config_page.load_icon', return_value=MagicMock()):
        mock_hw = MagicMock()
        mock_config = MagicMock()
        mock_config.get.return_value = {}
        page = ConfigPage(mock_hw, mock_config)
        assert page is not None


def test_config_page_get_advanced_config():
    """Test getting advanced config."""
    app = QApplication.instance() or QApplication([])
    with patch('nitrosense.ui.pages.config_page.load_icon', return_value=MagicMock()):
        mock_hw = MagicMock()
        mock_config = MagicMock()
        mock_config.get.return_value = {}
        page = ConfigPage(mock_hw, mock_config)
        config = page._get_advanced_config()
        assert isinstance(config, dict)


def test_config_page_create_help_button():
    """Test creating help button."""
    app = QApplication.instance() or QApplication([])
    with patch('nitrosense.ui.pages.config_page.load_icon', return_value=MagicMock()):
        mock_hw = MagicMock()
        mock_config = MagicMock()
        mock_config.get.return_value = {}
        page = ConfigPage(mock_hw, mock_config)
        button = page._create_help_button("Title", "Description")
        assert button is not None


def test_config_page_show_help_card():
    """Test showing help card."""
    app = QApplication.instance() or QApplication([])
    with patch('nitrosense.ui.pages.config_page.load_icon', return_value=MagicMock()):
        mock_hw = MagicMock()
        mock_config = MagicMock()
        mock_config.get.return_value = {}
        page = ConfigPage(mock_hw, mock_config)
        mock_anchor = MagicMock()
        mock_anchor.mapToGlobal.return_value = QPoint(0, 0)
        page._show_help_card(mock_anchor, "Title", "Description")
        # Should not raise