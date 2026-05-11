"""
Global constants and configuration maps for NitroSense Ultimate.
Serves as the single source of truth for all system-wide settings.
"""

import os
from enum import IntEnum
from pathlib import Path

# ============================================================================
# ERROR CODES
# ============================================================================

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
    HARDWARE_NOT_AVAILABLE = 110
    HARDWARE_INIT_FAILED = 111

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
    ErrorCode.HARDWARE_NOT_AVAILABLE: "❌ Required hardware or drivers not available",
    ErrorCode.HARDWARE_INIT_FAILED: "❌ Hardware backend initialization failed",

    # System
    ErrorCode.PERMISSION_DENIED: "❌ Insufficient permissions (root required)",
    ErrorCode.FILE_NOT_FOUND: "❌ Required system file not found",
    ErrorCode.CONFIG_CORRUPTED: "❌ Configuration file corrupted",
    ErrorCode.LOG_WRITE_FAILED: "❌ Failed to write to log file",
    ErrorCode.KERNEL_VERSION_INCOMPATIBLE: "❌ Kernel version incompatible",
    ErrorCode.DEPENDENCY_MISSING: "❌ Required dependency not installed",
    ErrorCode.SOCKET_ERROR: "❌ Network socket error",
    ErrorCode.NETWORK_UNREACHABLE: "❌ Network unreachable",

    # Thermal
    ErrorCode.TEMP_SENSOR_FAIL: "❌ Temperature sensor failure",
    ErrorCode.CRITICAL_TEMP_95C: "🔴 Critical temperature 95°C reached",
    ErrorCode.CRITICAL_TEMP_100C: "🔴 Critical temperature 100°C reached",
    ErrorCode.TEMP_SENSOR_INVALID: "❌ Invalid temperature sensor reading",
    ErrorCode.SENSOR_READ_ERROR: "❌ Failed to read sensor data",

    # UI/Threading
    ErrorCode.THREAD_CREATION_FAILED: "❌ Failed to create background thread",
    ErrorCode.THREAD_TIMEOUT: "❌ Thread operation timed out",
    ErrorCode.UI_RENDER_FAILED: "❌ UI rendering failed",
    ErrorCode.SIGNAL_EMIT_FAILED: "❌ Failed to emit Qt signal",
    ErrorCode.QPROCESS_FAILED: "❌ QProcess execution failed",

    # Configuration
    ErrorCode.CONFIG_SAVE_FAILED: "❌ Failed to save configuration",
    ErrorCode.CONFIG_LOAD_FAILED: "❌ Failed to load configuration",
    ErrorCode.CONFIG_INVALID_VALUE: "❌ Invalid configuration value",
    ErrorCode.SNAPSHOT_EXPORT_FAILED: "❌ Failed to export configuration snapshot",
    ErrorCode.SNAPSHOT_IMPORT_FAILED: "❌ Failed to import configuration snapshot",
    ErrorCode.BACKUP_CORRUPTED: "❌ Configuration backup corrupted",

    # Security
    ErrorCode.CHECKSUM_MISMATCH: "❌ File checksum verification failed",
    ErrorCode.INVALID_COMMAND_SYNTAX: "❌ Invalid command syntax",
    ErrorCode.UNSAFE_SHELL_INJECTION: "❌ Unsafe shell command detected",
    ErrorCode.UNAUTHORIZED_ACCESS: "❌ Unauthorized access attempt",
    ErrorCode.SIGNATURE_VERIFICATION_FAILED: "❌ Digital signature verification failed",

    # Process
    ErrorCode.PROCESS_KILL_FAILED: "❌ Failed to terminate process",
    ErrorCode.PROCESS_NOT_FOUND: "❌ Target process not found",
    ErrorCode.PROCESS_ZOMBIE_DETECTED: "⚠️  Zombie process detected",

    # Update
    ErrorCode.UPDATE_CHECK_FAILED: "❌ Failed to check for updates",
    ErrorCode.DOWNLOAD_FAILED: "❌ Update download failed",
    ErrorCode.HASH_VERIFICATION_FAILED: "❌ Update hash verification failed",
    ErrorCode.UPDATE_INSTALLATION_FAILED: "❌ Update installation failed",

    # Critical
    ErrorCode.UNKNOWN_ERROR: "❌ Unknown error occurred",
    ErrorCode.CRITICAL_SYSTEM_FAILURE: "🔴 Critical system failure - immediate shutdown required",
}

# ============================================================================
# CONFIGURATION DIRECTORIES
# ============================================================================

CONFIG_DIRS = {
    "base": Path.home() / ".config" / "nitrosense",
    "logs": Path.home() / ".config" / "nitrosense" / "logs",
    "dashboard": Path.home() / ".config" / "nitrosense" / "dashboard.json",
    "install_prefs": Path.home() / ".config" / "nitrosense" / "install_preferences.json",
    "crash_report": Path.home() / ".config" / "nitrosense" / "last_crash_report.txt",
    "telemetry": Path.home() / ".config" / "nitrosense" / "telemetry.json",
    "snapshots": Path.home() / ".config" / "nitrosense" / "snapshots",
    "presets": Path.home() / ".config" / "nitrosense" / "presets",
}

# ============================================================================
# SYSFS PATHS REGISTRY
# ============================================================================

SYSFS_PATHS = {
    "thermal_zones": "/sys/class/thermal/thermal_zone*/temp",
    "hwmon_sensors": "/sys/class/hwmon/hwmon*/temp*_input",
    "ec_io": "/sys/kernel/debug/ec/ec0/io",
    "dmi_product": "/sys/class/dmi/id/product_name",
    "backlight": "/sys/class/backlight/*/brightness",
    "battery": "/sys/class/power_supply/BAT*/uevent",
    "cpu_freq": "/sys/devices/system/cpu/cpu*/cpufreq/scaling_cur_freq",
    "fan_speed": "/sys/class/hwmon/hwmon*/fan*_input",
}

# ============================================================================
# SYSTEM PATHS
# ============================================================================

SYSTEM_PATHS = {
    "EC_IO": "/sys/kernel/debug/ec/ec0/io",
    "EC_SYS": "/sys/module/ec_sys",
    "THERMAL": "/sys/class/thermal/",
    "BACKLIGHT": "/sys/class/backlight/",
    "BATTERY": "/sys/class/power_supply/BAT0/",
    "CPUINFO": "/proc/cpuinfo",
    "UPTIME": "/proc/uptime",
    "CPU_TEMP_SYSFS": "/sys/class/thermal/thermal_zone0/temp",
    "CPU_TEMP_HWMON": "/sys/class/hwmon/hwmon0/temp1_input",
    "DMI_PRODUCT": "/sys/class/dmi/id/product_name",
    "KDE_GLOBALS": str(Path.home() / ".config" / "kdeglobals"),
}

# ============================================================================
# APPLICATION SETTINGS
# ============================================================================

APP_CONFIG = {
    "app_name": "NitroSense Ultimate",
    "version": "3.1.0",
    "target_device": "Acer Nitro 5 and compatible laptops",
    "architecture": "Resilience Framework v3.1 + Performance Optimization",
    "min_python_version": "3.12",
    "window_width": 1200,
    "window_height": 800,
    "ui_update_interval": 2000,  # ms
    "hardware_update_interval": 1500,  # ms
}

# ============================================================================
# THERMAL MANAGEMENT
# ============================================================================

THERMAL_CONFIG = {
    "temp_thresholds": {
        "Low": 50,
        "Mid": 65,
        "High": 80,
    },
    "speed_thresholds": {
        "Low": 30,
        "Mid": 60,
        "High": 100,
    },
    "idle_speed": 20,
    "emergency_temp": 95,
    "emergency_speed": 100,
    "predictive_temp_delta": 3.0,  # °C per 1.5s
    "predictive_activation_speed": 80,
    "watchdog_fan_threshold": 75,
    "frost_mode_duration": 120,  # seconds
}

# ============================================================================
# COLORS & STYLING
# ============================================================================

COLOR_SCHEME = {
    "background": "#1e1e1e",
    "surface": "#2d2d2d",
    "primary": "#007aff",
    "success": "#34c759",
    "warning": "#ff9500",
    "danger": "#ff3b30",
    "text_primary": "#ffffff",
    "text_secondary": "#a0a0a0",
}

TEMP_COLORS = {
    "cold": "#0099ff",      # < 45°C
    "normal": "#34c759",    # 45-60°C
    "warm": "#ff9500",      # 60-75°C
    "hot": "#ff3b30",       # 75-90°C
    "critical": "#ff0033",  # > 90°C
}

# ============================================================================
# PROCESS PROFILES
# ============================================================================

PROCESS_PROFILES = {
    "gaming": {
        "name": "High Performance Gaming",
        "processes": ["steam", "proton", "lutris", "heroicgameslauncher"],
        "fan_speed": 100,
        "priority": "high",
    },
    "video_editing": {
        "name": "Video Editing",
        "processes": ["davinci", "blender", "kdenlive", "premiere"],
        "fan_speed": 90,
        "priority": "high",
    },
    "office": {
        "name": "Office Work",
        "processes": ["soffice", "libreoffice", "code", "vscode"],
        "fan_speed": 40,
        "priority": "low",
    },
    "cinema": {
        "name": "Cinema / Media Playback",
        "processes": ["vlc", "mpv", "kodi", "firefox"],
        "fan_speed": 30,
        "priority": "low",
    },
}

PYTHON_DEPENDENCIES = [
    "PyQt6>=6.4.0",
    "psutil>=5.9.0",
    "matplotlib>=3.7.0",
    "numpy>=1.24.0",
    "markdown>=3.4.0",
]

# ============================================================================
# RETRY LOGIC
# ============================================================================

RETRY_CONFIG = {
    "max_retries": 5,
    "base_delay": 0.5,  # seconds
    "exponential_base": 2.0,
}

# ============================================================================
# LOGGING
# ============================================================================

LOG_CONFIG = {
    "log_dir": os.path.expanduser("~/.config/nitrosense/logs"),
    "log_file": "nitrosense.log",
    "max_size": 5 * 1024 * 1024,  # 5MB
    "backup_count": 5,
    "date_format": "%Y-%m-%d %H:%M:%S",
    "log_level": "INFO",
}

# ============================================================================
# PERFORMANCE
# ============================================================================

PERFORMANCE_CONFIG = {
    "gc_interval": 100,  # Collect garbage every 100 UI updates
    "cache_size": 5,  # Keep last 5 sensor readings
    "graph_points": 30,  # Historical graph points
    "thread_pool_size": 4,
    "cache_ttl": 2.0,  # Sensor cache time-to-live in seconds
    "watchdog_timeout": 10.0,  # Watchdog timeout in seconds
    "watchdog_reset_cooldown": 60.0,  # Minimum delay between emergency resets
    "sensor_failure_threshold": 3,  # Consecutive failures before emergency mode
    "profile_detection_cache_ttl": 5.0,  # Seconds to cache active profile detection
    "debounce_delay": 300,  # Config save debounce delay in ms
}

# ============================================================================
# HARDWARE SUPPORT
# ============================================================================

SUPPORTED_MODELS = {
    "Acer Nitro AN515-54": {
        "ec_paths": ["/sys/kernel/debug/ec/ec0/io"],
        "thermal_zones": ["/sys/class/thermal/thermal_zone0/temp"],
        "description": "Acer Nitro 5 (AN515-54) - Primary supported model",
    },
    "Acer Nitro AN515-51": {
        "ec_paths": ["/sys/kernel/debug/ec/ec0/io"],
        "thermal_zones": ["/sys/class/thermal/thermal_zone0/temp"],
        "description": "Acer Nitro 5 (AN515-51) - Compatible model",
    },
    # Add more models as support expands
}

class NotificationLevel(Enum):
    """Notification urgency levels for libnotify."""
    LOW = 0
    NORMAL = 1
    CRITICAL = 2

# ============================================================================
# DEVICE VALIDATION
# ============================================================================

DEVICE_VALIDATION = {
    "accepted_models": [
        "Acer Nitro 5",
        "Acer AN515",
    ],
    "dmi_product_path": "/sys/class/dmi/id/product_name",
}
