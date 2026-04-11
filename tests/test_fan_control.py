import pytest
from unittest.mock import Mock
from nitrosense.automation.fan_control import FanController


class DummyHardware:
    def __init__(self):
        self.last_command = None

    def run_nbfc(self, command):
        self.last_command = command
        if "set -s" in command:
            return True, "Speed set"
        elif "config --apply" in command:
            return True, "Config applied"
        elif "start" in command:
            return True, "Started"
        elif "stop" in command:
            return True, "Stopped"
        return False, "Error"


class DummyConfig:
    def get_thermal_config(self):
        return {"idle_speed": 20}


def test_fan_controller_initialization():
    hardware = DummyHardware()
    config = DummyConfig()
    fc = FanController(hardware, config)
    assert fc.current_speed is None


def test_set_fan_speed_valid():
    hardware = DummyHardware()
    config = DummyConfig()
    fc = FanController(hardware, config)
    result = fc.set_fan_speed(75)
    assert result is True
    assert fc.current_speed == 75
    assert "set -s 75" in hardware.last_command


def test_set_fan_speed_clamp_high():
    hardware = DummyHardware()
    config = DummyConfig()
    fc = FanController(hardware, config)
    result = fc.set_fan_speed(150)
    assert result is True
    assert fc.current_speed == 100


def test_set_fan_speed_clamp_low():
    hardware = DummyHardware()
    config = DummyConfig()
    fc = FanController(hardware, config)
    result = fc.set_fan_speed(-10)
    assert result is True
    assert fc.current_speed == 0


def test_enable_auto_curve():
    hardware = DummyHardware()
    config = DummyConfig()
    fc = FanController(hardware, config)
    result = fc.enable_auto_curve("Test Config")
    assert result is True
    assert "config --apply 'Test Config'" in hardware.last_command


def test_frost_mode_engage():
    hardware = DummyHardware()
    config = DummyConfig()
    fc = FanController(hardware, config)
    result = fc.frost_mode_engage(120)
    assert result is True
    assert fc.current_speed == 100


def test_frost_mode_engage_custom_duration():
    hardware = DummyHardware()
    config = DummyConfig()
    fc = FanController(hardware, config)
    result = fc.frost_mode_engage(60)
    assert result is True


def test_get_current_speed():
    hardware = DummyHardware()
    config = DummyConfig()
    fc = FanController(hardware, config)
    fc.set_fan_speed(50)
    assert fc.get_current_speed() == 50


def test_get_current_speed_none():
    hardware = DummyHardware()
    config = DummyConfig()
    fc = FanController(hardware, config)
    assert fc.get_current_speed() is None


def test_fan_controller_hardware_failure():
    class FailingHardware:
        def run_nbfc(self, command):
            return False, "Hardware error"

    hardware = FailingHardware()
    config = DummyConfig()
    fc = FanController(hardware, config)
    result = fc.set_fan_speed(50)
    assert result is False
    assert fc.current_speed is None