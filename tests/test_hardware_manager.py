"""
Tests for hardware manager module.
"""

import pytest
from unittest.mock import patch, MagicMock
from nitrosense.hardware.manager import HardwareManager


def test_hardware_manager_initialization():
    """Test initialization of HardwareManager."""
    with patch('subprocess.run'), patch('pathlib.Path.exists', return_value=True):
        manager = HardwareManager()
        assert manager is not None


def test_run_nbfc_success():
    """Test successful NBFC command."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "output"
        manager = HardwareManager()
        success, output = manager.run_nbfc("status -a")
        assert success is True
        assert output == "output"


def test_run_nbfc_failure():
    """Test failed NBFC command."""
    import subprocess
    with patch('subprocess.run') as mock_run:
        mock_run.side_effect = subprocess.SubprocessError("error")
        manager = HardwareManager()
        success, output = manager.run_nbfc("status -a")
        assert success is False


def test_read_file():
    """Test reading a file."""
    with patch('pathlib.Path.exists', return_value=True), patch('pathlib.Path.read_text', return_value="content\n"):
        manager = HardwareManager()
        result = manager.read_file("/path/to/file")
        assert result == "content"


def test_check_dependencies():
    """Test checking dependencies."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value.returncode = 0
        manager = HardwareManager()
        deps = manager.check_dependencies()
        assert isinstance(deps, dict)