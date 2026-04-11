"""
Singleton Configuration Manager for NitroSense Ultimate.
Handles reading, writing, and caching of application settings.
"""

import json
import threading
from pathlib import Path
from typing import Any, Dict, Optional
from .logger import logger
from .constants import THERMAL_CONFIG


class ConfigManager:
    """
    Thread-safe singleton configuration manager.
    Stores application state in JSON format with atomic writes.
    """

    _instance: Optional["ConfigManager"] = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.config_dir = Path.home() / ".config" / "nitrosense"
        self.config_file = self.config_dir / "config.json"
        self._lock = threading.RLock()
        self._cache: Dict[str, Any] = {}

        self.config_dir.mkdir(parents=True, exist_ok=True)
        self._load_config()
        self._initialized = True

        logger.info(f"ConfigManager initialized: {self.config_file}")

    def _load_config(self) -> None:
        """Load configuration from disk."""
        with self._lock:
            if self.config_file.exists():
                try:
                    with open(self.config_file, "r") as f:
                        self._cache = json.load(f)
                    logger.debug("Configuration loaded from disk")
                except Exception as e:
                    logger.error(f"Failed to load config: {e}")
                    self._cache = self._get_default_config()
            else:
                self._cache = self._get_default_config()
                self._save_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Return default configuration."""
        return {
            "thermal": THERMAL_CONFIG.copy(),
            "auto_curve_enabled": False,
            "ui_scale": 1.0,
            "theme": "dark",
            "notifications_enabled": True,
            "log_level": "INFO",
        }

    def _save_config(self) -> None:
        """Save configuration to disk atomically."""
        with self._lock:
            try:
                # Write to temporary file first
                temp_file = self.config_file.with_suffix(".tmp")
                with open(temp_file, "w") as f:
                    json.dump(self._cache, f, indent=2)
                # Atomically move to actual location
                temp_file.replace(self.config_file)
                logger.debug("Configuration saved to disk")
            except Exception as e:
                logger.error(f"Failed to save config: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot-notation key."""
        with self._lock:
            keys = key.split(".")
            value = self._cache

            for k in keys:
                if isinstance(value, dict):
                    value = value.get(k)
                    if value is None:
                        return default
                else:
                    return default

            return value if value is not None else default

    def set(self, key: str, value: Any, persist: bool = True) -> None:
        """Set configuration value by dot-notation key."""
        with self._lock:
            keys = key.split(".")

            # Navigate to parent
            current = self._cache
            for k in keys[:-1]:
                if k not in current:
                    current[k] = {}
                current = current[k]

            # Set value
            current[keys[-1]] = value

            if persist:
                self._save_config()
            logger.debug(f"Config updated: {key} = {value}")

    def get_thermal_config(self) -> Dict[str, Any]:
        """Get thermal management configuration.

        Returns a reference to the actual config dict. Modifications will be
        automatically persisted when made through set_thermal_config() or
        by calling _save_config() manually.

        WARNING: Direct modifications to the returned dict are NOT recommended.
        Use set_thermal_config() for proper persistence.
        """
        thermal_config = self.get("thermal", THERMAL_CONFIG.copy())
        # Return reference, not copy, so changes can be tracked
        return thermal_config

    def set_thermal_config(self, config: Dict[str, Any]) -> None:
        """Update thermal management configuration."""
        self.set("thermal", config, persist=True)

    def reload_config(self) -> None:
        """Reload configuration from disk."""
        with self._lock:
            self._load_config()
            logger.info("Configuration reloaded from disk")

    def export_snapshot(self) -> bool:
        """
        Export complete system snapshot for backup/restore.
        Includes config, fan curves, automation rules, and system state.
        """
        try:
            from datetime import datetime
            from ..core.constants import APP_CONFIG
            
            snapshot = {
                "version": APP_CONFIG["version"],
                "timestamp": datetime.now().isoformat(),
                "config": self._cache.copy(),
                # Note: fan_curves and automation_rules would be added by respective managers
                # This is a basic config-only snapshot for now
            }
            
            filepath = self.config_dir / "system_snapshot.nsbackup"
            with open(filepath, "w") as f:
                json.dump(snapshot, f, indent=2)
            
            logger.info(f"System snapshot exported: {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to export snapshot: {e}")
            return False

    def import_snapshot(self, filepath: Path) -> bool:
        """
        Import configuration from backup snapshot.
        
        Args:
            filepath: Path to .nsbackup file
            
        Returns:
            True if successful
        """
        try:
            with open(filepath, "r") as f:
                imported_config = json.load(f)

            # Validate structure
            if "config" in imported_config:
                self._cache = imported_config["config"]
                self._save_config()
                logger.info(f"Configuration snapshot imported: {filepath}")
                return True
            else:
                logger.error("Invalid snapshot format")
                return False
        except Exception as e:
            logger.error(f"Failed to import snapshot: {e}")
            return False

    def reset_to_defaults(self) -> None:
        """Reset all settings to defaults."""
        with self._lock:
            self._cache = self._get_default_config()
            self._save_config()
            logger.warning("Configuration reset to defaults")
