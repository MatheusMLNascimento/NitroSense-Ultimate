"""
Optional anonymous telemetry support for NitroSense Ultimate.
Designed to collect lightweight usage metrics without personal data.
"""

import json
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

from .logger import logger


class TelemetryClient:
    """Collects anonymous metrics and writes local telemetry snapshots."""

    def __init__(self, enabled: bool = False, storage_dir: Optional[Path] = None) -> None:
        self.enabled = enabled
        self.storage_dir = storage_dir or Path.home() / ".config" / "nitrosense"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.storage_path = self.storage_dir / "telemetry.json"
        self._lock = threading.Lock()
        self._events: list[Dict[str, Any]] = []

    def track_event(self, event_name: str, properties: Optional[Dict[str, Any]] = None) -> None:
        """Store an anonymous event locally."""
        if not self.enabled:
            return

        event = {
            "event": event_name,
            "properties": properties or {},
            "timestamp": time.time(),
        }

        with self._lock:
            self._events.append(event)
            if len(self._events) >= 20:
                self.flush()

    def flush(self) -> None:
        """Persist collected telemetry events to disk."""
        if not self.enabled:
            return

        with self._lock:
            try:
                existing = []
                if self.storage_path.exists():
                    with open(self.storage_path, "r", encoding="utf-8") as f:
                        existing = json.load(f)
                existing.extend(self._events)
                with open(self.storage_path, "w", encoding="utf-8") as f:
                    json.dump(existing[-100:], f, indent=2)
                self._events.clear()
                logger.info("Telemetry flushed to disk")
            except Exception as exc:
                logger.error(f"Telemetry flush failed: {exc}")

    def is_enabled(self) -> bool:
        return self.enabled

    def get_snapshot(self) -> Dict[str, Any]:
        """Return the current anonymous telemetry snapshot."""
        with self._lock:
            return {
                "event_count": len(self._events),
                "last_event": self._events[-1] if self._events else None,
            }
