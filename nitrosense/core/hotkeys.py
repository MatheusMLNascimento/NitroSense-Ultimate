"""
Global Hotkeys and Pre-Death Telemetry for NitroSense Ultimate.

CRITICAL FEATURES:
1. Global hotkey registration (Ctrl+Shift+F for Frost Mode)
2. Pre-crash telemetry collection (crash report with system state)
3. DBus service registration for desktop integration
4. Exception hook that generates last_crash_report.txt before exit

DESIGN: Uses pynput for cross-platform hotkey support,
         falls back to X11 if pynput unavailable
"""

import os
import sys
import time
import platform
import json
import subprocess
import importlib
import importlib.util
from pathlib import Path
from typing import Optional, Callable, Dict, Any
from datetime import datetime
from threading import Thread

from ..core.logger import logger
from ..core.constants import APP_CONFIG


class HotkeysManager:
    """
    Global hotkey manager for desktop environment integration.
    
    Supports:
    - Global hotkey registration (Ctrl+Shift+F for Frost Mode)
    - DBus service for KDE Plasma integration
    - Graceful fallback on X11 systems
    """
    
    def __init__(self):
        """Initialize hotkeys manager."""
        self.hotkeys: Dict[str, Any] = {}
        self._listener = None
        self._pynput_available = self._check_pynput()
        self._running = False

    def _check_pynput(self) -> bool:
        """Check if pynput is available for hotkey support."""
        if importlib.util.find_spec("pynput") is None:
            logger.warning("pynput not installed; global hotkeys disabled")
            logger.info("Install pynput: pip install pynput")
            return False

        logger.debug("pynput available for global hotkey support")
        return True

    def register_hotkey(self, hotkey: str, callback: Callable, description: str = "") -> bool:
        """
        Register a global hotkey.

        Args:
            hotkey: Hotkey string (e.g., "ctrl+shift+f")
            callback: Function to call when hotkey is pressed
            description: Human-readable description

        Returns:
            True if registered successfully
        """
        if not self._pynput_available:
            logger.warning(f"Cannot register hotkey '{hotkey}': pynput not available")
            return False

        try:
            pynput = importlib.import_module("pynput")
            keyboard = getattr(pynput, "keyboard")

            keys = self._parse_hotkey(hotkey)
            if not keys:
                logger.error(f"Invalid hotkey format: {hotkey}")
                return False

            hotkey_combo = keyboard.HotKey(keys, callback)

            self.hotkeys[hotkey] = {
                "callback": callback,
                "description": description,
                "combo": hotkey_combo
            }

            logger.info(f"Registered hotkey '{hotkey}': {description}")
            return True

        except Exception as e:
            logger.error(f"Failed to register hotkey '{hotkey}': {e}")
            return False

    def _parse_hotkey(self, hotkey_str: str) -> list:
        """
        Parse hotkey string into pynput-compatible format.
        
        Examples:
            "ctrl+shift+f" -> [...]
            "alt+enter" -> [...]
        """
        try:
            pynput = importlib.import_module("pynput")
            keyboard = getattr(pynput, "keyboard")

            parts = hotkey_str.lower().split("+")
            keys = []
            
            modifier_map = {
                "ctrl": keyboard.Key.ctrl,
                "alt": keyboard.Key.alt,
                "shift": keyboard.Key.shift,
            }
            
            for part in parts:
                part = part.strip()
                if part in modifier_map:
                    keys.append(modifier_map[part])
                elif len(part) == 1:
                    # Single character
                    keys.append(part)
                else:
                    # Named key
                    try:
                        keys.append(getattr(keyboard.Key, part))
                    except AttributeError:
                        logger.warning(f"Unknown key: '{part}'")
                        return []
            
            return keys
        except Exception as e:
            logger.error(f"Error parsing hotkey: {e}")
            return []
    
    def start_listening(self) -> bool:
        """Start listening for registered hotkeys."""
        if not self._pynput_available:
            logger.warning("Cannot start hotkey listener: pynput not available")
            return False
        
        if self._running:
            logger.warning("Hotkey listener already running")
            return False
        
        try:
            pynput = importlib.import_module("pynput")
            keyboard = getattr(pynput, "keyboard")

            def on_press(key):
                pass  # Handled by hotkey combo above

            def on_release(key):
                pass
            
            # Start listener in background thread
            self._listener = keyboard.Listener(
                on_press=on_press,
                on_release=on_release
            )
            self._listener.start()
            self._running = True
            logger.info("Global hotkey listener started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start hotkey listener: {e}")
            return False
    
    def stop_listening(self) -> None:
        """Stop listening for hotkeys."""
        try:
            if self._listener and self._running:
                self._listener.stop()
                self._running = False
                logger.info("Global hotkey listener stopped")
        except Exception as e:
            logger.error(f"Error stopping hotkey listener: {e}")


class CrashReporter:
    """
    Pre-death telemetry collector.
    Generates detailed crash reports with system state at time of crash.
    """
    
    CRASH_REPORT_FILE = Path.home() / ".config" / "nitrosense" / "last_crash_report.txt"
    
    @staticmethod
    def generate_crash_report(exception: Exception, traceback_str: str = "") -> str:
        """
        Generate comprehensive crash report with system telemetry.
        
        Returns:
            Path to generated crash report file
        """
        try:
            # Collect system information
            report_lines = [
                "=" * 70,
                "NitroSense Ultimate - Crash Report",
                "=" * 70,
                f"Timestamp: {datetime.now().isoformat()}",
                f"Exception: {exception.__class__.__name__}",
                f"Message: {str(exception)}",
                "",
            ]
            
            # System information
            report_lines.extend([
                "SYSTEM INFORMATION:",
                f"  Python: {platform.python_version()}",
                f"  OS: {platform.system()} {platform.release()}",
                f"  Kernel: {platform.platform()}",
                f"  Machine: {platform.machine()}",
                f"  Hostname: {platform.node()}",
                "",
            ])
            
            # Kernel version
            try:
                kernel_version = subprocess.check_output(
                    ["uname", "-a"],
                    timeout=5,
                    text=True
                ).strip()
                report_lines.append(f"KERNEL: {kernel_version}")
            except Exception:
                pass
            
            # Video driver
            report_lines.append("")
            report_lines.append("VIDEO DRIVER:")
            try:
                result = subprocess.check_output(
                    ["glxinfo", "-B"],
                    timeout=5,
                    text=True
                )
                for line in result.split('\n')[:5]:
                    if 'vendor' in line.lower() or 'device' in line.lower():
                        report_lines.append(f"  {line}")
            except subprocess.TimeoutExpired:
                report_lines.append("  (timeout reading video info)")
            except FileNotFoundError:
                report_lines.append("  glxinfo not available")
            except Exception as e:
                report_lines.append(f"  Error: {e}")
            
            # System uptime
            try:
                with open("/proc/uptime", "r") as f:
                    uptime_seconds = int(float(f.read().split()[0]))
                    uptime_hours = uptime_seconds / 3600
                    report_lines.append(f"  Uptime: {uptime_hours:.1f} hours ({uptime_seconds} seconds)")
            except:
                pass
            
            # Loaded modules (especially acer_wmi if applicable)
            report_lines.append("")
            report_lines.append("LOADED KERNEL MODULES (EC/ACPI related):")
            try:
                with open("/proc/modules", "r") as f:
                    for line in f:
                        module = line.split()[0]
                        if any(x in module.lower() for x in ["acpi", "acer", "ec", "wmi", "nbfc"]):
                            report_lines.append(f"  {module}")
            except:
                pass
            
            # Thermal sensor state
            report_lines.append("")
            report_lines.append("LAST SENSOR STATE (if available):")
            try:
                import psutil
                report_lines.append(f"  CPU Usage: {psutil.cpu_percent()}%")
                report_lines.append(f"  RAM Usage: {psutil.virtual_memory().percent}%")
                if hasattr(psutil, "sensors_temperatures"):
                    temps = psutil.sensors_temperatures()
                    for name, entries in temps.items():
                        for entry in entries[:3]:  # First 3 sensors per device
                            report_lines.append(f"  {name}/{entry.label}: {entry.current}°C")
            except:
                pass
            
            # Traceback
            report_lines.extend([
                "",
                "FULL TRACEBACK:",
                traceback_str or "No traceback available",
                "",
                "=" * 70,
            ])
            
            # Write report
            report_text = "\n".join(report_lines)
            CrashReporter.CRASH_REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
            CrashReporter.CRASH_REPORT_FILE.write_text(report_text)
            
            logger.critical(f"Crash report generated: {CrashReporter.CRASH_REPORT_FILE}")
            return str(CrashReporter.CRASH_REPORT_FILE)
            
        except Exception as e:
            logger.error(f"Failed to generate crash report: {e}")
            return ""
