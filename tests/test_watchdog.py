import subprocess
from pathlib import Path

import pytest

from nitrosense.resilience.watchdog import HardwareWatchdog
from nitrosense.resilience import watchdog as watchdog_module


def test_watchdog_heartbeat_updates_last_time(monkeypatch):
    watchdog = HardwareWatchdog(timeout_sec=1)
    initial_timestamp = watchdog.last_heartbeat

    monkeypatch.setattr(watchdog_module.time, "time", lambda: initial_timestamp + 42)
    watchdog.heartbeat()

    assert watchdog.last_heartbeat >= initial_timestamp + 42


def test_watchdog_emergency_bus_reset_calls_subprocess(monkeypatch):
    watchdog = HardwareWatchdog(timeout_sec=1)
    calls = []

    def fake_run(command, *args, **kwargs):
        calls.append(command)
        return None

    monkeypatch.setattr(subprocess, "run", fake_run)
    watchdog._emergency_bus_reset()

    # Check that pkill command is in the calls (may not be first due to emergency mode)
    assert any(c == ["sudo", "pkill", "-9", "nbfc"] for c in calls)
    assert any(c[:2] == ["sudo", "modprobe"] for c in calls)
    assert any(c[:2] == ["sudo", "systemctl"] for c in calls)


def test_watchdog_stop_sets_running_false():
    watchdog = HardwareWatchdog(timeout_sec=1)
    watchdog.stop()
    assert watchdog.running is False


def test_watchdog_start():
    watchdog = HardwareWatchdog(timeout_sec=1)
    watchdog.start()
    assert watchdog.running is True
    watchdog.stop()


def test_watchdog_is_alive():
    watchdog = HardwareWatchdog(timeout_sec=1)
    watchdog.start()
    assert watchdog.is_alive() is True
    watchdog.stop()
    assert watchdog.is_alive() is False


def test_watchdog_timeout_detection(monkeypatch):
    watchdog = HardwareWatchdog(timeout_sec=1)
    watchdog.start()
    monkeypatch.setattr(watchdog_module.time, "time", lambda: watchdog.last_heartbeat + 2)
    assert not watchdog.is_alive()
    watchdog.stop()


def test_watchdog_emergency_reset_on_timeout(monkeypatch):
    watchdog = HardwareWatchdog(timeout_sec=1)
    calls = []

    def fake_run(command, *args, **kwargs):
        calls.append(command)
        return None

    monkeypatch.setattr(subprocess, "run", fake_run)
    watchdog._emergency_bus_reset()
    assert len(calls) > 0


def test_watchdog_initialization():
    watchdog = HardwareWatchdog(timeout_sec=5)
    assert watchdog.timeout_sec == 5
    assert watchdog.running is False
    assert watchdog.last_heartbeat > 0


def test_watchdog_multiple_heartbeats():
    watchdog = HardwareWatchdog(timeout_sec=1)
    watchdog.start()
    initial = watchdog.last_heartbeat
    watchdog.heartbeat()
    assert watchdog.last_heartbeat > initial
    watchdog.stop()


def test_watchdog_stop_twice():
    watchdog = HardwareWatchdog(timeout_sec=1)
    watchdog.start()
    watchdog.stop()
    watchdog.stop()  # Should not error
    assert watchdog.running is False


def test_watchdog_heartbeat_without_start():
    watchdog = HardwareWatchdog(timeout_sec=1)
    initial = watchdog.last_heartbeat
    watchdog.heartbeat()
    assert watchdog.last_heartbeat > initial
