"""
Advanced Configuration Module (Functions 51-75)
Handles all customization, settings, and user preferences
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from PyQt6.QtCore import pyqtSignal, QObject
from ..core.logger import logger
from ..core.error_codes import ErrorCode, SafeOperation


class AdvancedConfigManager(QObject):
    """
    Manages advanced configuration options (Functions 51-75).
    Emits signals on config changes.
    """
    
    config_changed = pyqtSignal(str, object)  # key, value
    
    def __init__(self, config_manager):
        super().__init__()
        self.config = config_manager
        self.advanced_config = self._load_advanced_config()
        logger.info("AdvancedConfigManager initialized")
    
    def _load_advanced_config(self) -> Dict[str, Any]:
        """Load advanced configuration with defaults."""
        defaults = {
            # Function 51-60: Temperature & Speed Customization
            "temp_thresholds": {"Low": 50, "Mid": 65, "High": 80},
            "speed_thresholds": {"Low": 30, "Mid": 60, "High": 100},
            "ui_layout_type": "column",  # Fn 53: Column layout
            "ui_scale": 1.0,  # UI scale factor
            
            # Function 61-65: Theme & Display
            "theme": "macOS_Dark",  # Fn 54
            "ping_target": "8.8.8.8",  # Fn 55
            "frost_duration": 120,  # Fn 56: Custom Frost timer
            
            # Function 66-70: Notifications & Logging
            "notifications": {  # Fn 57
                "critical_temp": True,
                "fan_stall": True,
                "throttling": True,
                "update_available": False,
            },
            "log_directory": str(Path.home() / ".config/nitrosense/logs"),  # Fn 58
            "start_minimized": False,  # Fn 59
            "hide_graph": False,  # Fn 60: Toggle graph visibility
            
            # Function 71-75: Advanced Features
            "ai_sensitivity": 1.0,  # Fn 61: Slider 0-2.0
            "battery_charge_limit": 100,  # Fn 62: 0-100%
            "maintenance_scheduler_enabled": False,  # Fn 63
            "maintenance_hour": 4,  # 4 AM
            "debug_mode": False,  # Fn 76: Debug console
            "export_csv_enabled": False,  # Fn 67: CSV logging
        }
        
        try:
            # Try to load from config
            saved = self.config.get("advanced_config", {})
            defaults.update(saved)
        except Exception as e:
            logger.error(f"Failed to load advanced config: {e}")
        
        return defaults
    
    # ========================================================================
    # FUNCTION 51-55: Thermal Configuration & Display
    # ========================================================================
    
    @SafeOperation(ErrorCode.CONFIG_INVALID_VALUE)
    def set_temp_threshold(self, level: str, temp: int) -> bool:
        """Fn 51: Set temperature threshold (Low/Mid/High)."""
        if level not in ["Low", "Mid", "High"]:
            return False
        if not (20 <= temp <= 100):
            return False
        
        self.advanced_config["temp_thresholds"][level] = temp
        self.config_changed.emit(f"temp_threshold_{level}", temp)
        self._save_advanced_config()
        logger.info(f"Temp threshold {level} set to {temp}°C")
        return True
    
    @SafeOperation(ErrorCode.CONFIG_INVALID_VALUE)
    def set_speed_threshold(self, level: str, speed: int) -> bool:
        """Fn 52: Set fan speed threshold (0-100%)."""
        if level not in ["Low", "Mid", "High"]:
            return False
        if not (0 <= speed <= 100):
            return False
        
        self.advanced_config["speed_thresholds"][level] = speed
        self.config_changed.emit(f"speed_threshold_{level}", speed)
        self._save_advanced_config()
        logger.info(f"Speed threshold {level} set to {speed}%")
        return True
    
    def set_ui_layout(self, layout_type: str) -> bool:
        """Fn 53: Set UI layout type (column, row, compact)."""
        if layout_type not in ["column", "row", "compact"]:
            return False
        
        self.advanced_config["ui_layout_type"] = layout_type
        self.config_changed.emit("ui_layout", layout_type)
        self._save_advanced_config()
        logger.info(f"UI layout set to {layout_type}")
        return True
    
    def set_theme(self, theme: str) -> bool:
        """Fn 54: Switch theme (macOS_Dark, Ultra_Black, Light)."""
        valid_themes = ["macOS_Dark", "Ultra_Black", "Light"]
        if theme not in valid_themes:
            return False
        
        self.advanced_config["theme"] = theme
        self.config_changed.emit("theme", theme)
        self._save_advanced_config()
        logger.info(f"Theme changed to {theme}")
        return True
    
    def set_ping_target(self, host: str) -> bool:
        """Fn 55: Set custom ping target (e.g., 8.8.8.8, google.com)."""
        if not (1 <= len(host) <= 255):
            return False
        
        self.advanced_config["ping_target"] = host
        self.config_changed.emit("ping_target", host)
        self._save_advanced_config()
        logger.info(f"Ping target set to {host}")
        return True
    
    # ========================================================================
    # FUNCTION 56-60: Timers, Notifications & Display Options
    # ========================================================================
    
    def set_frost_duration(self, seconds: int) -> bool:
        """Fn 56: Set custom Frost Mode duration (10-600 seconds)."""
        if not (10 <= seconds <= 600):
            return False
        
        self.advanced_config["frost_duration"] = seconds
        self.config_changed.emit("frost_duration", seconds)
        self._save_advanced_config()
        logger.info(f"Frost duration set to {seconds}s")
        return True
    
    def set_notification(self, notification_type: str, enabled: bool) -> bool:
        """Fn 57: Toggle specific notifications."""
        valid_types = list(self.advanced_config["notifications"].keys())
        if notification_type not in valid_types:
            return False
        
        self.advanced_config["notifications"][notification_type] = enabled
        self.config_changed.emit(f"notification_{notification_type}", enabled)
        self._save_advanced_config()
        logger.info(f"Notification {notification_type} set to {enabled}")
        return True
    
    def set_log_directory(self, path: str) -> bool:
        """Fn 58: Set custom log directory."""
        log_path = Path(path)
        try:
            log_path.mkdir(parents=True, exist_ok=True)
            self.advanced_config["log_directory"] = str(log_path)
            self.config_changed.emit("log_directory", str(log_path))
            self._save_advanced_config()
            logger.info(f"Log directory set to {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to set log directory: {e}")
            return False
    
    def set_start_minimized(self, minimized: bool) -> bool:
        """Fn 59: Set app to start minimized in system tray."""
        self.advanced_config["start_minimized"] = minimized
        self.config_changed.emit("start_minimized", minimized)
        self._save_advanced_config()
        logger.info(f"Start minimized set to {minimized}")
        return True
    
    def set_hide_graph(self, hide: bool) -> bool:
        """Fn 60: Toggle graph visibility for minimal UI."""
        self.advanced_config["hide_graph"] = hide
        self.config_changed.emit("hide_graph", hide)
        self._save_advanced_config()
        logger.info(f"Graph visibility set to {not hide}")
        return True
    
    # ========================================================================
    # FUNCTION 61-65: AI Sensitivity, Battery, Scheduler
    # ========================================================================
    
    def set_ai_sensitivity(self, sensitivity: float) -> bool:
        """Fn 61: Set AI prediction sensitivity (0.1-2.0)."""
        if not (0.1 <= sensitivity <= 2.0):
            return False
        
        self.advanced_config["ai_sensitivity"] = sensitivity
        self.config_changed.emit("ai_sensitivity", sensitivity)
        self._save_advanced_config()
        logger.info(f"AI sensitivity set to {sensitivity}x")
        return True
    
    def set_battery_charge_limit(self, percent: int) -> bool:
        """Fn 62: Set battery charge limit (preserves battery health)."""
        if not (20 <= percent <= 100):
            return False
        
        self.advanced_config["battery_charge_limit"] = percent
        self.config_changed.emit("battery_charge_limit", percent)
        self._save_advanced_config()
        
        # Try to apply to system
        self._apply_battery_charge_limit(percent)
        logger.info(f"Battery charge limit set to {percent}%")
        return True
    
    def set_maintenance_scheduler(self, enabled: bool, hour: int = 4) -> bool:
        """Fn 63: Enable/disable maintenance scheduler (e.g., 4 AM)."""
        if not (0 <= hour <= 23):
            return False
        
        self.advanced_config["maintenance_scheduler_enabled"] = enabled
        self.advanced_config["maintenance_hour"] = hour
        self.config_changed.emit("maintenance_scheduler", enabled)
        self._save_advanced_config()
        logger.info(f"Maintenance scheduler set to {hour}:00 - {enabled}")
        return True
    
    def set_debug_mode(self, enabled: bool) -> bool:
        """Fn 66: Toggle debug mode with real-time console."""
        self.advanced_config["debug_mode"] = enabled
        self.config_changed.emit("debug_mode", enabled)
        self._save_advanced_config()
        logger.info(f"Debug mode set to {enabled}")
        return True
    
    def set_csv_export(self, enabled: bool) -> bool:
        """Fn 67: Enable/disable CSV data logging."""
        self.advanced_config["export_csv_enabled"] = enabled
        self.config_changed.emit("csv_export", enabled)
        self._save_advanced_config()
        logger.info(f"CSV export set to {enabled}")
        return True
    
    # ========================================================================
    # GETTERS
    # ========================================================================
    
    def get_theme(self) -> str:
        """Get current theme."""
        return self.advanced_config.get("theme", "macOS_Dark")
    
    def get_ui_scale(self) -> float:
        """Get UI scale factor."""
        return self.advanced_config.get("ui_scale", 1.0)
    
    def set_ui_scale(self, scale: float) -> bool:
        """Set UI scale factor (0.5-2.0)."""
        if not (0.5 <= scale <= 2.0):
            return False
        
        self.advanced_config["ui_scale"] = scale
        self.config_changed.emit("ui_scale", scale)
        self._save_advanced_config()
        logger.info(f"UI scale set to {scale}")
        return True
    
    # ========================================================================
    # FUNCTION 68-75: Advanced Options
    # ========================================================================
    
    def get_all_config(self) -> Dict[str, Any]:
        """Get all advanced configuration."""
        return self.advanced_config.copy()
    
    def reset_to_defaults(self) -> bool:
        """Fn 70: Reset all advanced config to factory defaults."""
        self.advanced_config = self._get_default_config()
        self._save_advanced_config()
        self.config_changed.emit("all_config_reset", True)
        logger.warning("Advanced configuration reset to defaults")
        return True
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "temp_thresholds": {"Low": 50, "Mid": 65, "High": 80},
            "speed_thresholds": {"Low": 30, "Mid": 60, "High": 100},
            "ui_layout_type": "column",
            "theme": "macOS_Dark",
            "ping_target": "8.8.8.8",
            "frost_duration": 120,
            "notifications": {
                "critical_temp": True,
                "fan_stall": True,
                "throttling": True,
                "update_available": False,
            },
            "log_directory": str(Path.home() / ".config/nitrosense/logs"),
            "start_minimized": False,
            "hide_graph": False,
            "ai_sensitivity": 1.0,
            "battery_charge_limit": 100,
            "maintenance_scheduler_enabled": False,
            "maintenance_hour": 4,
            "debug_mode": False,
            "export_csv_enabled": False,
        }
    
    def _save_advanced_config(self) -> None:
        """Save advanced config to disk."""
        try:
            self.config.set("advanced_config", self.advanced_config, persist=True)
        except Exception as e:
            logger.error(f"Failed to save advanced config: {e}")
    
    def _apply_battery_charge_limit(self, percent: int) -> bool:
        """Fn 62 implementation: Apply battery charge limit via sysfs."""
        try:
            import subprocess
            # Try to set battery charge limit (Linux)
            cmd = f"echo {percent} | tee /sys/class/power_supply/BAT0/charge_control_end_threshold"
            result = subprocess.run(
                ["sudo", "bash", "-c", cmd],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except Exception as e:
            logger.debug(f"Battery charge limit not applicable: {e}")
            return False
    
    def get_effective_ai_sensitivity(self) -> float:
        """Get actual AI sensitivity multiplier."""
        return self.advanced_config.get("ai_sensitivity", 1.0)
