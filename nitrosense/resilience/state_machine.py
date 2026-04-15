"""
Thread-Safe State Machine with threading.RLock
Central state repository for all hardware metrics and system state
"""

import threading
from typing import Any, Dict
from ..core.logger import logger


class ThreadSafeStateMachine:
    """
    Centralized immutable state with thread-safe access.
    Eliminates duplicate sensor reads by caching values.
    """
    
    def __init__(self):
        self._lock = threading.RLock()
        self._state: Dict[str, Any] = {
            "cpu_temp": 0.0,
            "gpu_temp": 0.0,
            "fan_rpm": 0,
            "fan_speed_percent": 0,
            "cpu_usage": 0.0,
            "gpu_usage": 0.0,
            "memory_mb": 0,
            "power_mode": "AC",  # AC or Battery
            "thermal_state": "normal",  # normal, warning, critical
            "emergency_active": False,
            "last_update_ts": 0,
            "error_count": 0,
            "watchdog_fired": False,
        }
        logger.info("✅ ThreadSafeStateMachine initialized")
    
    def read_state(self, key: str) -> Any:
        """Atomic read with threading.RLock."""
        with self._lock:
            return self._state.get(key)
    
    def read_all(self) -> Dict[str, Any]:
        """Atomic read of entire state."""
        with self._lock:
            return dict(self._state)
    
    def update_state(self, key: str, value: Any) -> bool:
        """Atomic write with threading.RLock."""
        with self._lock:
            self._state[key] = value
            self._state["last_update_ts"] = __import__('time').time()
            return True
    
    def update_batch(self, updates: Dict[str, Any]) -> bool:
        """Atomic batch update."""
        with self._lock:
            self._state.update(updates)
            self._state["last_update_ts"] = __import__('time').time()
            return True


# Singleton instance
_machine = ThreadSafeStateMachine()

def get_state_machine() -> ThreadSafeStateMachine:
    """Get global state machine."""
    return _machine
