"""
Tests for config_tester module.
"""

import pytest
from unittest.mock import patch, MagicMock
from nitrosense.core.config_tester import ConfigTester


def test_config_tester_initialization():
    """Test initialization of ConfigTester."""
    mock_config = MagicMock()
    tester = ConfigTester(mock_config)
    assert tester is not None


def test_start_test():
    """Test starting a config test."""
    mock_config = MagicMock()
    mock_config.get_all.return_value = {'thermal_thresholds': {'Low': 50}}
    tester = ConfigTester(mock_config)
    success, message = tester.start_test({'thermal_thresholds': {'Low': 60}})
    assert success == True


def test_get_test_status():
    """Test getting test status."""
    mock_config = MagicMock()
    mock_config.get_all.return_value = {}
    tester = ConfigTester(mock_config)
    status = tester.get_test_status()
    assert isinstance(status, dict)
    assert status['is_testing'] == False


def test_confirm_test():
    """Test confirming a test."""
    mock_config = MagicMock()
    mock_config.get_all.return_value = {}
    tester = ConfigTester(mock_config)
    success, message = tester.confirm_test()
    assert success == False  # No test in progress


def test_revert_test():
    """Test reverting a test."""
    mock_config = MagicMock()
    mock_config.get_all.return_value = {}
    tester = ConfigTester(mock_config)
    success, message = tester.revert_test()
    assert success == False  # No test in progress