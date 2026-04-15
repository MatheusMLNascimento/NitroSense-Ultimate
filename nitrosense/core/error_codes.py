"""
Error Code System for NitroSense Ultimate
Centralizes all error handling with standardized codes for inter-module communication
"""

from enum import IntEnum
from typing import Tuple, Optional, Any
import time


class ErrorCode(IntEnum):
    """Standardized error codes (0-999)."""
    
    # Success codes
    SUCCESS = 0
    
    # Hardware errors (100-199)
    NBFC_TIMEOUT = 101
    NBFC_COMMAND_FAILED = 102
    EC_ACCESS_FAILED = 103
    EC_MODULE_LOAD_FAILED = 104
    NVIDIA_UNAVAILABLE = 105
    SENSORS_UNAVAILABLE = 106
    HARDWARE_ID_MISMATCH = 107
    FAN_STALL_DETECTED = 108
    THERMAL_THROTTLING = 109
    
    # System errors (200-299)
    PERMISSION_DENIED = 201
    FILE_NOT_FOUND = 202
    CONFIG_CORRUPTED = 203
    LOG_WRITE_FAILED = 204
    KERNEL_VERSION_INCOMPATIBLE = 205
    DEPENDENCY_MISSING = 206
    SOCKET_ERROR = 207
    NETWORK_UNREACHABLE = 208
    
    # Thermal errors (300-399)
    TEMP_SENSOR_FAIL = 301
    CRITICAL_TEMP_95C = 302
    CRITICAL_TEMP_100C = 303
    TEMP_SENSOR_INVALID = 304
    SENSOR_READ_ERROR = 305

    # UI/Threading errors (400-499)
    THREAD_CREATION_FAILED = 401
    THREAD_TIMEOUT = 402
    UI_RENDER_FAILED = 403
    SIGNAL_EMIT_FAILED = 404
    QPROCESS_FAILED = 405
    
    # Configuration errors (500-599)
    CONFIG_SAVE_FAILED = 501
    CONFIG_LOAD_FAILED = 502
    CONFIG_INVALID_VALUE = 503
    SNAPSHOT_EXPORT_FAILED = 504
    SNAPSHOT_IMPORT_FAILED = 505
    BACKUP_CORRUPTED = 506
    
    # Security errors (600-699)
    CHECKSUM_MISMATCH = 601
    INVALID_COMMAND_SYNTAX = 602
    UNSAFE_SHELL_INJECTION = 603
    UNAUTHORIZED_ACCESS = 604
    SIGNATURE_VERIFICATION_FAILED = 605
    
    # Process errors (700-799)
    PROCESS_KILL_FAILED = 701
    PROCESS_NOT_FOUND = 702
    PROCESS_ZOMBIE_DETECTED = 703
    
    # Update errors (800-899)
    UPDATE_CHECK_FAILED = 801
    DOWNLOAD_FAILED = 802
    HASH_VERIFICATION_FAILED = 803
    UPDATE_INSTALLATION_FAILED = 804
    
    # Unknown/Severe errors (900-1000)
    UNKNOWN_ERROR = 999
    CRITICAL_SYSTEM_FAILURE = 1000


ERROR_DESCRIPTIONS = {
    ErrorCode.SUCCESS: "✅ Operation successful",
    
    # Hardware
    ErrorCode.NBFC_TIMEOUT: "❌ NBFC service timeout after 5 retries",
    ErrorCode.NBFC_COMMAND_FAILED: "❌ NBFC command execution failed",
    ErrorCode.EC_ACCESS_FAILED: "❌ Cannot access Embedded Controller",
    ErrorCode.EC_MODULE_LOAD_FAILED: "❌ ec_sys kernel module failed to load",
    ErrorCode.NVIDIA_UNAVAILABLE: "⚠️  NVIDIA GPU driver not available",
    ErrorCode.SENSORS_UNAVAILABLE: "⚠️  lm-sensors not available",
    ErrorCode.HARDWARE_ID_MISMATCH: "⚠️  Device is not Acer Nitro 5 compatible",
    ErrorCode.FAN_STALL_DETECTED: "🔴 Fan stall detected - possible hardware failure",
    ErrorCode.THERMAL_THROTTLING: "⚠️  CPU thermal throttling active",
    
    # System
    ErrorCode.PERMISSION_DENIED: "❌ Insufficient permissions (root required)",
    ErrorCode.FILE_NOT_FOUND: "❌ Required system file not found",
    ErrorCode.CONFIG_CORRUPTED: "❌ Configuration file corrupted",
    ErrorCode.LOG_WRITE_FAILED: "⚠️  Could not write to log file",
    ErrorCode.KERNEL_VERSION_INCOMPATIBLE: "⚠️  Kernel version has known compatibility issues",
    ErrorCode.DEPENDENCY_MISSING: "❌ Required system dependency not installed",
    ErrorCode.SOCKET_ERROR: "❌ Network socket error",
    ErrorCode.NETWORK_UNREACHABLE: "⚠️  Network unreachable",
    
    # Thermal
    ErrorCode.TEMP_SENSOR_FAIL: "🔴 Temperature sensor read failure",
    ErrorCode.CRITICAL_TEMP_95C: "🔴 CRITICAL: Temperature ≥ 95°C - Emergency protocol engaged",
    ErrorCode.CRITICAL_TEMP_100C: "🔴 EXTREME: Temperature ≥ 100°C - Thermal shutdown imminent",
    ErrorCode.TEMP_SENSOR_INVALID: "❌ Invalid temperature reading",
    ErrorCode.SENSOR_READ_ERROR: "❌ Sensor read failure",
    
    # Threading
    ErrorCode.THREAD_CREATION_FAILED: "❌ Failed to create worker thread",
    ErrorCode.THREAD_TIMEOUT: "⏱️ Worker thread timeout",
    ErrorCode.UI_RENDER_FAILED: "⚠️  UI rendering failed",
    ErrorCode.SIGNAL_EMIT_FAILED: "⚠️  Signal emission failed",
    ErrorCode.QPROCESS_FAILED: "❌ QProcess execution failed",
    
    # Configuration
    ErrorCode.CONFIG_SAVE_FAILED: "❌ Failed to save configuration",
    ErrorCode.CONFIG_LOAD_FAILED: "❌ Failed to load configuration",
    ErrorCode.CONFIG_INVALID_VALUE: "❌ Invalid configuration value",
    ErrorCode.SNAPSHOT_EXPORT_FAILED: "❌ Failed to export backup",
    ErrorCode.SNAPSHOT_IMPORT_FAILED: "❌ Failed to import backup",
    ErrorCode.BACKUP_CORRUPTED: "❌ Backup file corrupted",
    
    # Security
    ErrorCode.CHECKSUM_MISMATCH: "🔒 Security: Checksum verification failed",
    ErrorCode.INVALID_COMMAND_SYNTAX: "🔒 Security: Invalid command syntax detected",
    ErrorCode.UNSAFE_SHELL_INJECTION: "🔒 Security: Potential shell injection blocked",
    ErrorCode.UNAUTHORIZED_ACCESS: "🔒 Security: Unauthorized access attempt",
    ErrorCode.SIGNATURE_VERIFICATION_FAILED: "🔒 Security: Signature verification failed",
    
    # Process
    ErrorCode.PROCESS_KILL_FAILED: "⚠️  Failed to terminate process",
    ErrorCode.PROCESS_NOT_FOUND: "⚠️  Process not found",
    ErrorCode.PROCESS_ZOMBIE_DETECTED: "⚠️  Zombie process detected and cleaned",
    
    # Update
    ErrorCode.UPDATE_CHECK_FAILED: "⚠️  Failed to check for updates",
    ErrorCode.DOWNLOAD_FAILED: "❌ Download failed",
    ErrorCode.HASH_VERIFICATION_FAILED: "🔒 Hash verification failed",
    ErrorCode.UPDATE_INSTALLATION_FAILED: "❌ Update installation failed",
    
    # Unknown
    ErrorCode.UNKNOWN_ERROR: "❌ Unknown error occurred",
    ErrorCode.CRITICAL_SYSTEM_FAILURE: "🔴 CRITICAL: System failure",
}


def get_error_description(code: ErrorCode) -> str:
    """Get human-readable error description."""
    return ERROR_DESCRIPTIONS.get(code, "❓ Unknown error code")


def is_critical(code: ErrorCode) -> bool:
    """Check if error code is critical (requires immediate attention)."""
    critical_codes = {
        ErrorCode.CRITICAL_TEMP_95C,
        ErrorCode.CRITICAL_TEMP_100C,
        ErrorCode.CRITICAL_SYSTEM_FAILURE,
        ErrorCode.EC_MODULE_LOAD_FAILED,
        ErrorCode.FAN_STALL_DETECTED,
    }
    return code in critical_codes


def is_recoverable(code: ErrorCode) -> bool:
    """Check if error is recoverable (app can continue)."""
    unrecoverable = {
        ErrorCode.CRITICAL_TEMP_100C,
        ErrorCode.CRITICAL_SYSTEM_FAILURE,
    }
    return code not in unrecoverable


class SafeOperation:
    """Decorator for safe operation execution with error code return."""
    
    def __init__(self, default_code: ErrorCode = ErrorCode.UNKNOWN_ERROR):
        self.default_code = default_code
    
    def __call__(self, func):
        def wrapper(*args, **kwargs) -> Tuple[ErrorCode, Optional[Any]]:
            try:
                result = func(*args, **kwargs)
                return ErrorCode.SUCCESS, result
            except TimeoutError:
                return ErrorCode.THREAD_TIMEOUT, None
            except PermissionError:
                return ErrorCode.PERMISSION_DENIED, None
            except FileNotFoundError:
                return ErrorCode.FILE_NOT_FOUND, None
            except Exception as e:
                # Log the exception
                from ..core.logger import logger
                logger.error(f"Error in {func.__name__}: {e}")
                return self.default_code, None
        
        return wrapper


class CircuitBreaker:
    """Circuit breaker pattern for fault tolerance."""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._failure_count = 0
        self.last_failure_time = 0
        self._state = "closed"  # closed, open, half_open
    
    @property
    def failure_count(self):
        return self._failure_count
    
    @failure_count.setter
    def failure_count(self, value):
        self._failure_count = value
    
    @property
    def state(self):
        return self._state
    
    @state.setter
    def state(self, value):
        self._state = value
    
    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if self.state == "open":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "half_open"
            else:
                raise CircuitBreakerOpenException("Circuit breaker is OPEN")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e
    
    def _on_success(self):
        """Handle successful call."""
        self._failure_count = 0
        self.state = "closed"
    
    def _on_failure(self):
        """Handle failed call."""
        self._failure_count += 1
        self.last_failure_time = time.time()
        if self._failure_count >= self.failure_threshold:
            self.state = "open"


class CircuitBreakerOpenException(Exception):
    """Exception raised when circuit breaker is open."""
    pass
