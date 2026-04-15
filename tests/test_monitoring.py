import pytest
import time
from unittest.mock import Mock, patch
from collections import deque
from nitrosense.core.monitoring import MonitoringEngine


class DummyHardware:
    def __init__(self):
        self.temp_data = {"cpu": 45.0, "gpu": 40.0}
        self.rpm_data = 1200
        self.binary_paths = {}

    def get_cpu_temp(self):
        return self.temp_data["cpu"]

    def read_acpi_raw_data(self, filepath):
        return b"45000\n"

    def get_gpu_temp(self):
        return self.temp_data["gpu"]

    def get_fan_rpm(self):
        return self.rpm_data

    def run_nbfc(self, command):
        return True, "ok"

    def get_system_load(self):
        return 0.5


def test_monitoring_engine_initialization():
    hardware = DummyHardware()
    me = MonitoringEngine(hardware)
    assert me.last_temp == 0.0
    assert me.monitoring_active is False
    assert isinstance(me.temp_history, deque)


def test_get_system_metrics():
    hardware = DummyHardware()
    me = MonitoringEngine(hardware)
    metrics = me.get_system_metrics()
    assert "cpu_temp" in metrics
    assert "gpu_temp" in metrics
    assert "fan_rpm" in metrics
    assert metrics["cpu_temp"] == 45.0


def test_get_temperature_delta():
    hardware = DummyHardware()
    me = MonitoringEngine(hardware)
    # First call
    me.get_system_metrics()
    time.sleep(0.1)
    # Second call
    me.get_system_metrics()
    delta = me.get_temperature_delta()
    assert isinstance(delta, float)


def test_get_temperature_trend():
    hardware = DummyHardware()
    me = MonitoringEngine(hardware)
    for i in range(10):
        hardware.temp_data["cpu"] = 40.0 + i
        me.get_system_metrics()
        time.sleep(0.01)
    trend = me.get_temperature_trend()
    assert len(trend) > 0
    assert all(isinstance(t, float) for t in trend)


def test_start_monitoring():
    hardware = DummyHardware()
    me = MonitoringEngine(hardware)
    me.start_monitoring()
    assert me.monitoring_active is True


def test_stop_monitoring():
    hardware = DummyHardware()
    me = MonitoringEngine(hardware)
    me.start_monitoring()
    me.stop_monitoring()
    assert me.monitoring_active is False


def test_get_average_temp():
    hardware = DummyHardware()
    me = MonitoringEngine(hardware)
    avg = me.get_average_temperature()
    assert isinstance(avg, float)


def test_get_peak_temp():
    hardware = DummyHardware()
    me = MonitoringEngine(hardware)
    peak = me.get_peak_temperature()
    assert isinstance(peak, float)


def test_reset_history():
    hardware = DummyHardware()
    me = MonitoringEngine(hardware)
    me.get_system_metrics()
    me.reset_history()
    assert len(me.temp_history) == 0


def test_monitoring_with_hardware_failure():
    class FailingHardware:
        def get_cpu_temp(self):
            raise Exception("Sensor error")

        def get_gpu_temp(self):
            return 40.0

        def get_fan_rpm(self):
            return 1200

        def run_nbfc(self, command):
            return True, "ok"

        def get_system_load(self):
            return 0.5

    hardware = FailingHardware()
    me = MonitoringEngine(hardware)
    metrics = me.get_system_metrics()
    # Should handle exception gracefully
    assert "cpu_temp" in metrics
    assert metrics["cpu_temp"] is None or isinstance(metrics["cpu_temp"], float)


