"""
Tests for diagnostics module.
"""

import pytest
from unittest.mock import patch, MagicMock
from nitrosense.security.diagnostics import SecurityAndDiagnostics
from nitrosense.core.error_codes import ErrorCode


def test_security_diagnostics_initialization():
    """Test initialization of SecurityAndDiagnostics."""
    with patch('pathlib.Path.mkdir'):
        diagnostics = SecurityAndDiagnostics(None, None)
        assert diagnostics is not None


def test_system_dependency_check():
    """Test checking system dependencies."""
    with patch('nitrosense.security.diagnostics.subprocess.run') as mock_run:
        mock_run.return_value.returncode = 0
        with patch('pathlib.Path.mkdir'):
            diagnostics = SecurityAndDiagnostics(None, None)
            err, result = diagnostics.system_dependency_check()
            assert err == ErrorCode.SUCCESS
            # Result is wrapped by SafeOperation
            if isinstance(result, tuple) and len(result) == 2:
                inner_err, deps = result
                assert isinstance(deps, dict)
                assert len(deps) > 0
            else:
                assert isinstance(result, dict)
                assert len(result) > 0


def test_generate_diagnostic_report():
    """Test generating diagnostic report."""
    mock_hw = MagicMock()
    mock_hw.get_hardware_id.return_value = "TEST_HW_ID"
    with patch('pathlib.Path.mkdir'), patch('pathlib.Path.exists', return_value=True), patch('nitrosense.security.diagnostics.open', create=True), patch('nitrosense.security.diagnostics.subprocess.run') as mock_run:
        mock_run.return_value.returncode = 0
        diagnostics = SecurityAndDiagnostics(mock_hw, None)
        err, path = diagnostics.generate_diagnostic_report()
        assert err == ErrorCode.SUCCESS
        assert path is not None


def test_emergency_protocol_95c():
    """Test emergency protocol at 95C."""
    mock_hw = MagicMock()
    mock_hw.run_nbfc.return_value = (True, "success")
    with patch('nitrosense.security.diagnostics.psutil.process_iter', return_value=[]):
        with patch('pathlib.Path.mkdir'):
            diagnostics = SecurityAndDiagnostics(mock_hw, None)
            err, result = diagnostics.emergency_protocol_95c()
            assert err == ErrorCode.SUCCESS
            # Result is wrapped by SafeOperation
            if isinstance(result, tuple) and len(result) == 2:
                inner_err, triggered = result
                assert inner_err == ErrorCode.CRITICAL_TEMP_95C
                assert isinstance(triggered, bool)
            else:
                assert isinstance(result, bool)