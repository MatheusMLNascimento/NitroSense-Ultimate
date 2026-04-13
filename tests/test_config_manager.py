import json
from pathlib import Path

import pytest

from nitrosense.core.config import ConfigManager
from nitrosense.core.constants import THERMAL_CONFIG


def test_config_manager_singleton_and_defaults(monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    config_manager = ConfigManager()

    assert config_manager is ConfigManager()
    assert config_manager.get("theme") == "dark"
    assert config_manager.get("ui_scale") == 1.0
    assert config_manager.get("thermal.temp_thresholds.High") == THERMAL_CONFIG["temp_thresholds"]["High"]

    config_manager.set("theme", "light", persist=False)
    assert config_manager.get("theme") == "light"

    config_manager.reset_to_defaults()
    assert config_manager.get("theme") == "dark"
    assert config_manager.get("ui_scale") == 1.0


def test_config_manager_persistence(monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    config_manager = ConfigManager()
    config_manager.set("notifications_enabled", False, persist=True)

    new_manager = ConfigManager()
    assert new_manager.get("notifications_enabled") is False


def test_snapshot_export_and_import(monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    config_manager = ConfigManager()
    assert config_manager.export_snapshot() is True

    snapshot_file = tmp_path / ".config" / "nitrosense" / "system_snapshot.nsbackup"
    assert snapshot_file.exists()

    config_manager.set("theme", "custom", persist=False)
    assert config_manager.get("theme") == "custom"

    assert config_manager.import_snapshot(snapshot_file) is True
    assert config_manager.get("theme") == "dark"


def test_config_manager_get_with_default():
    config_manager = ConfigManager()
    assert config_manager.get("nonexistent_key", "default_value") == "default_value"


def test_config_manager_set_invalid_key():
    config_manager = ConfigManager()
    config_manager.set("invalid.key", "value")
    assert config_manager.get("invalid.key") == "value"


def test_config_manager_persistence_file_creation(monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    config_manager = ConfigManager()
    config_file = tmp_path / ".config" / "nitrosense" / "config.json"
    assert config_file.exists()


def test_config_manager_load_invalid_json(monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    config_file = tmp_path / ".config" / "nitrosense" / "config.json"
    config_file.parent.mkdir(parents=True, exist_ok=True)
    config_file.write_text("invalid json")
    config_manager = ConfigManager()
    # Should handle invalid JSON gracefully
    assert config_manager.get("theme") == "dark"


def test_config_manager_export_snapshot_failure(monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    config_manager = ConfigManager()

    # Simulate snapshot file write failure to ensure export_snapshot returns False
    original_open = open

    from pathlib import Path as _Path

    def failing_open(*args, **kwargs):
        if args:
            target = args[0]
            if (isinstance(target, str) and target.endswith("system_snapshot.nsbackup")) or (
                isinstance(target, _Path) and target.name == "system_snapshot.nsbackup"
            ):
                raise IOError("Disk write error")
        return original_open(*args, **kwargs)

    monkeypatch.setattr("builtins.open", failing_open)
    assert config_manager.export_snapshot() is False


def test_config_manager_import_snapshot_invalid_file(monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    config_manager = ConfigManager()
    invalid_file = tmp_path / "invalid.json"
    invalid_file.write_text("not a snapshot")
    result = config_manager.import_snapshot(invalid_file)
    assert result is False


def test_config_manager_import_snapshot_missing_config(monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    config_manager = ConfigManager()
    invalid_file = tmp_path / "invalid.json"
    invalid_file.write_text('{"version": "1.0"}')  # Missing config
    result = config_manager.import_snapshot(invalid_file)
    assert result is False


def test_config_manager_reset_to_defaults():
    config_manager = ConfigManager()
    config_manager.set("theme", "custom", persist=False)
    config_manager.reset_to_defaults()
    assert config_manager.get("theme") == "dark"


def test_config_manager_get_thermal_config():
    config_manager = ConfigManager()
    thermal = config_manager.get_thermal_config()
    assert isinstance(thermal, dict)
    assert "temp_thresholds" in thermal
