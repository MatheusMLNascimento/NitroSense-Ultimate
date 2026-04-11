"""
Tests for advanced_config module.
"""

import pytest
from unittest.mock import patch, MagicMock
from nitrosense.core.advanced_config import AdvancedConfigManager


def test_advanced_config_manager_initialization():
    """Test initialization of AdvancedConfigManager."""
    mock_config = MagicMock()
    mock_config.get.return_value = {}
    manager = AdvancedConfigManager(mock_config)
    assert manager is not None


def test_get_theme():
    """Test getting theme setting."""
    mock_config = MagicMock()
    mock_config.get.return_value = {'theme': 'dark'}
    manager = AdvancedConfigManager(mock_config)
    assert manager.get_theme() == 'dark'


def test_set_theme():
    """Test setting theme."""
    mock_config = MagicMock()
    manager = AdvancedConfigManager(mock_config)
    assert manager.set_theme('Light') == True


def test_get_ui_scale():
    """Test getting UI scale."""
    mock_config = MagicMock()
    mock_config.get.return_value = {'ui_scale': 1.5}
    manager = AdvancedConfigManager(mock_config)
    assert manager.get_ui_scale() == 1.5


def test_set_ui_scale():
    """Test setting UI scale."""
    mock_config = MagicMock()
    manager = AdvancedConfigManager(mock_config)
    assert manager.set_ui_scale(1.2) == True