"""
Tests for validation module.
"""

import pytest
from unittest.mock import patch, MagicMock
from nitrosense.security.validation import BackendValidation


def test_backend_validation_initialization():
    """Test initialization of BackendValidation."""
    validation = BackendValidation()
    assert validation is not None


def test_global_exception_hook():
    """Test global exception hook."""
    with patch('nitrosense.security.validation.logger') as mock_logger:
        BackendValidation.global_exception_hook(ValueError, ValueError("test"), None)
        mock_logger.critical.assert_called()


def test_sha256_validation():
    """Test SHA-256 validation."""
    validation = BackendValidation()
    data = b"test data"
    hash_value = validation.sha256_hash(data)
    assert isinstance(hash_value, str)
    assert len(hash_value) == 64  # SHA-256 is 64 chars


def test_shell_sanitization():
    """Test shell sanitization."""
    validation = BackendValidation()
    safe_cmd = validation.sanitize_shell_command("ls -la")
    assert safe_cmd == "ls -la"

    # Test potentially dangerous command
    dangerous = validation.sanitize_shell_command("rm -rf /")
    assert dangerous != "rm -rf /"


def test_dmi_hardware_binding():
    """Test DMI hardware binding."""
    with patch('pathlib.Path.read_text', return_value="Test Hardware"):
        validation = BackendValidation()
        bound = validation.dmi_hardware_binding()
        assert bound is True