import pytest
from unittest.mock import Mock, patch
from nitrosense.automation.ai_engine import PredictiveAIEngine
from nitrosense.core.constants import THERMAL_CONFIG


class DummyMonitoring:
    def get_temperature_delta(self):
        return 0.5


class DummyHardware:
    def run_nbfc(self, command):
        return True, "ok"


class DummyConfig:
    def get_thermal_config(self):
        return {
            "temp_thresholds": {"Low": 45, "Mid": 55, "High": 70},
            "speed_thresholds": {"Low": 30, "Mid": 60, "High": 90},
            "idle_speed": 20,
            "emergency_temp": 95,
            "emergency_speed": 100,
            "predictive_temp_delta": 3.0,
            "watchdog_fan_threshold": 60,
        }


def test_ai_engine_initialization():
    monitoring = DummyMonitoring()
    hardware = DummyHardware()
    config = DummyConfig()
    ai = PredictiveAIEngine(monitoring, hardware, config)
    assert ai.predictive_mode_active is False
    assert ai.active_profile is None
    assert ai.game_heat_state is False


def test_calculate_required_speed_normal():
    monitoring = DummyMonitoring()
    hardware = DummyHardware()
    config = DummyConfig()
    ai = PredictiveAIEngine(monitoring, hardware, config)
    speed = ai.calculate_required_speed(50.0, 0.5)
    assert 30 <= speed <= 60


def test_calculate_required_speed_high_temp():
    monitoring = DummyMonitoring()
    hardware = DummyHardware()
    config = DummyConfig()
    ai = PredictiveAIEngine(monitoring, hardware, config)
    speed = ai.calculate_required_speed(80.0, 0.5)
    assert speed >= 90


def test_calculate_required_speed_emergency():
    monitoring = DummyMonitoring()
    hardware = DummyHardware()
    config = DummyConfig()
    ai = PredictiveAIEngine(monitoring, hardware, config)
    speed = ai.calculate_required_speed(96.0, 0.5)
    assert speed == 100


def test_calculate_required_speed_predictive():
    monitoring = DummyMonitoring()
    hardware = DummyHardware()
    config = DummyConfig()
    ai = PredictiveAIEngine(monitoring, hardware, config)
    speed = ai.calculate_required_speed(60.0, 4.0)  # High delta
    assert speed > 60  # Should be higher due to anticipation


def test_get_cooldown_estimate():
    monitoring = DummyMonitoring()
    hardware = DummyHardware()
    config = DummyConfig()
    ai = PredictiveAIEngine(monitoring, hardware, config)
    estimate = ai.get_cooldown_estimate(80.0)
    assert isinstance(estimate, str)


def test_calculate_thermal_gradient():
    monitoring = DummyMonitoring()
    hardware = DummyHardware()
    config = DummyConfig()
    ai = PredictiveAIEngine(monitoring, hardware, config)
    gradient = ai.calculate_thermal_gradient(2.0)
    assert isinstance(gradient, str)


def test_refresh_profile_state(monkeypatch):
    monitoring = DummyMonitoring()
    hardware = DummyHardware()
    config = DummyConfig()
    ai = PredictiveAIEngine(monitoring, hardware, config)

    monkeypatch.setattr(PredictiveAIEngine, "detect_active_profile", lambda self: "gaming")
    state = ai.refresh_profile_state()
    assert state == "gaming"

    monkeypatch.setattr(PredictiveAIEngine, "detect_active_profile", lambda self: None)
    state = ai.refresh_profile_state()
    assert state == "closed"


def test_check_fan_watchdog_normal():
    monitoring = DummyMonitoring()
    hardware = DummyHardware()
    config = DummyConfig()
    ai = PredictiveAIEngine(monitoring, hardware, config)
    result = ai.check_fan_watchdog(70.0, 1500)
    assert result is False


def test_check_fan_watchdog_stall():
    monitoring = DummyMonitoring()
    hardware = DummyHardware()
    config = DummyConfig()
    ai = PredictiveAIEngine(monitoring, hardware, config)
    result = ai.check_fan_watchdog(80.0, 500)  # Low RPM for high temp
    assert result is True


def test_ai_engine_with_exception():
    monitoring = DummyMonitoring()
    hardware = DummyHardware()
    config = DummyConfig()
    ai = PredictiveAIEngine(monitoring, hardware, config)
    # Test with invalid input
    speed = ai.calculate_required_speed("invalid", 0.5)
    assert speed == 20  # Should return idle speed on error