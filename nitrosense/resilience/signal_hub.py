"""
Global Signal Hub - Mediator Pattern
Centralizes all inter-module communication via signals
"""

from PyQt6.QtCore import pyqtSignal, QObject
from typing import Dict, Callable, Any
from ..core.logger import logger


class SignalHub(QObject):
    """
    Centralized event distribution system.
    Modules emit signals here; subscribers listen without direct coupling.
    """

    # System signals
    systemHealthChanged = pyqtSignal(dict)        # {cpu_temp, gpu_temp, fan_rpm, errors}
    powerModeChanged = pyqtSignal(bool)           # True = AC, False = Battery
    thermalStateChanged = pyqtSignal(str)         # normal, warning, critical
    fanProfileChanged = pyqtSignal(str)           # gaming, office, cinema, balanced
    hardwareErrorDetected = pyqtSignal(int, str)  # (error_code, description)
    emergencyProtocolTriggered = pyqtSignal(int)  # error_code
    watchdogTriggered = pyqtSignal()              # Hardware watchdog timeout

    def __init__(self):
        super().__init__()
        self._subscribers: Dict[str, list] = {}
        logger.info("✅ Global SignalHub initialized (Mediator Pattern)")

    def subscribe(self, signal_name: str, callback: Callable):
        """Subscribe to a signal."""
        if signal_name not in self._subscribers:
            self._subscribers[signal_name] = []
        self._subscribers[signal_name].append(callback)
        logger.debug(f"Subscribed to signal: {signal_name}")

    def unsubscribe(self, signal_name: str, callback: Callable):
        """Unsubscribe from a signal."""
        if signal_name in self._subscribers:
            try:
                self._subscribers[signal_name].remove(callback)
            except ValueError:
                pass

    def emit_event(self, signal_name: str, *args, **kwargs):
        """Emit event to all subscribers."""
        if signal_name in self._subscribers:
            for callback in self._subscribers[signal_name]:
                try:
                    callback(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Signal handler error: {e}")


# Global instance (not singleton to avoid threading issues)
_signal_hub = None

def get_signal_hub() -> SignalHub:
    """Get global signal hub."""
    global _signal_hub
    if _signal_hub is None:
        _signal_hub = SignalHub()
    return _signal_hub
