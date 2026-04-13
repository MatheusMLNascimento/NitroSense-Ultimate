"""
Global constants and configuration maps for NitroSense Ultimate.
Serves as the single source of truth for all system-wide settings.
"""

import os
from enum import Enum
from pathlib import Path

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
    "version": "3.0.5",
    "target_device": "Acer Nitro 5 (AN515-54)",
    "architecture": "Resilience Framework v3.0 + Performance Optimization",
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
# ERROR CODES
# ============================================================================

from .error_codes import ErrorCode

ERROR_MESSAGES = {
    ErrorCode.SUCCESS: "✅ Operation successful",
    ErrorCode.NBFC_TIMEOUT: "❌ NBFC service timeout after 5 retries",
    ErrorCode.NVIDIA_UNAVAILABLE: "⚠️  NVIDIA GPU driver communication failed",
    ErrorCode.SENSORS_UNAVAILABLE: "⚠️  lm-sensors not responding",
    ErrorCode.EC_ACCESS_FAILED: "❌ Cannot access Embedded Controller",
    ErrorCode.EC_MODULE_LOAD_FAILED: "❌ ec_sys kernel module failed to load",
    ErrorCode.PERMISSION_DENIED: "❌ Insufficient permissions (root required)",
    ErrorCode.FILE_NOT_FOUND: "❌ Required system file not found",
    ErrorCode.UNKNOWN_ERROR: "❌ Unknown error occurred",
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

# ============================================================================
# DEPENDENCIES
# ============================================================================

REQUIRED_DEPENDENCIES = {
    "nbfc": "Fan control service",
    "nvidia-smi": "NVIDIA GPU monitoring",
    "sensors": "lm-sensors for CPU temp",
    "git": "Version control (for auto-updates)",
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
}

# ============================================================================
# NOTIFICATION LEVELS
# ============================================================================

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
