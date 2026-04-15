"""
Tests for system_integrity module.
"""

import pytest
from unittest.mock import patch, MagicMock
from nitrosense.resilience.system_integrity import SystemIntegrityCheck


def test_system_integrity_check_initialization():
    """Test initialization of SystemIntegrityCheck."""
    check = SystemIntegrityCheck()
    assert check is not None


def test_full_integrity_check():
    """Test full integrity check."""
    with patch('subprocess.run') as mock_run, patch('pathlib.Path.exists', return_value=True):
        mock_run.return_value.returncode = 0
        check = SystemIntegrityCheck()
        result = check.full_integrity_check()
        assert isinstance(result, dict)


def test_binary_dependency_check():
    """Test binary dependency check."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value.returncode = 0
        result = SystemIntegrityCheck.level_1_binary_check()
        assert isinstance(result, dict)


def test_kernel_module_check():
    """Test kernel module check."""
    with patch('pathlib.Path.exists', return_value=True), patch('builtins.open'):
        result, status = SystemIntegrityCheck.level_2_kernel_check()
        assert isinstance(result, bool)


def test_python_module_check():
    """Test Python module check."""
    result = SystemIntegrityCheck.level_3_python_check()
    assert isinstance(result, dict)