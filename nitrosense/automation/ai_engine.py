"""
AI and Predictive Automation Engine for NitroSense Ultimate.
Implements thermal prediction, emergency protocols, and process-based profiles.
"""

import subprocess
import psutil
import time
import functools
from typing import Dict, Optional, Tuple
from ..core.logger import logger
from ..core.constants import PERFORMANCE_CONFIG, THERMAL_CONFIG, PROCESS_PROFILES
from ..core.error_codes import ErrorCode, SafeOperation


class PredictiveAIEngine:
    """
    Advanced AI engine for thermal prediction and proactive fan control.
    Uses mathematical algorithms for anticipatory cooling.
    """

    def __init__(self, monitoring_engine, hardware_manager, config_manager):
        self.monitoring = monitoring_engine
        self.hardware = hardware_manager
        self.config = config_manager
        self.predictive_mode_active = False
        self.active_profile = None
        self.game_heat_state = False
        self._profile_cache: Tuple[Optional[str], float] = (None, 0.0)
        self._profile_cache_ttl: float = PERFORMANCE_CONFIG.get("profile_detection_cache_ttl", 5.0)
        logger.info("PredictiveAIEngine initialized")

    @functools.lru_cache(maxsize=128)
    def calculate_required_speed(
        self, current_temp: float, temp_delta: Optional[float] = None
    ) -> int:
        """
        Calculate required fan speed using predictive algorithm.
        
        Algorithm:
        1. Base speed from thermal curve
        2. If dT/dt > 3°C/1.5s, enter anticipation mode (+20% speed)
        3. Emergency threshold at >95°C -> 100%
        
        Args:
            current_temp: Current CPU temperature
            temp_delta: Temperature change rate (°C/sec)
            
        Returns:
            Recommended fan speed (0-100%)
        """
        thermal_cfg = self.config.get_thermal_config()
        thresholds = thermal_cfg["temp_thresholds"]
        speeds = thermal_cfg["speed_thresholds"]

        try:
            current_temp = float(current_temp)
        except (TypeError, ValueError):
            logger.debug(f"Invalid temperature input: {current_temp}")
            self.predictive_mode_active = False
            return thermal_cfg["idle_speed"]

        # Emergency protocol
        if current_temp >= thermal_cfg["emergency_temp"]:
            logger.warning(f"🔴 EMERGENCY: Temp {current_temp}°C - Engaging 100%")
            self.predictive_mode_active = False
            return thermal_cfg["emergency_speed"]

        # Normal thermal curve
        if current_temp >= thresholds["High"]:
            base_speed = speeds["High"]
        elif current_temp >= thresholds["Mid"]:
            base_speed = speeds["Mid"]
        elif current_temp >= thresholds["Low"]:
            base_speed = speeds["Low"]
        else:
            base_speed = thermal_cfg["idle_speed"]

        # Predictive anticipation (derivative-based)
        if temp_delta is not None and temp_delta > thermal_cfg["predictive_temp_delta"]:
            logger.info(f"⚡ Anticipation Mode: dT/dt = {temp_delta:.2f}°C/s")
            self.predictive_mode_active = True

            # Boost speed by 20%
            speed = min(
                int(base_speed * 1.2),
                100
            )
            return speed
        else:
            self.predictive_mode_active = False

        return base_speed

    def detect_active_profile(self) -> Optional[str]:
        """
        Detect active application profile based on running processes.

        Returns:
            Profile name (gaming, video_editing, office, cinema) or None
        """
        now = time.time()
        cached_profile, cached_until = self._profile_cache
        if now < cached_until:
            return cached_profile

        detected_profile: Optional[str] = None
        try:
            running_processes = [p.name() for p in psutil.process_iter(["name"])]
            for profile_name, profile_cfg in PROCESS_PROFILES.items():
                for process in profile_cfg["processes"]:
                    if process in running_processes:
                        detected_profile = profile_name
                        logger.info(f"Profile detected: {profile_name}")
                        break
                if detected_profile:
                    break
        except Exception as exc:
            logger.debug(f"Profile detection failed: {exc}")

        self._profile_cache = (detected_profile, now + self._profile_cache_ttl)
        return detected_profile

    def get_profile_fan_speed(self, profile: str) -> Optional[int]:
        """Get recommended fan speed for profile."""
        if profile in PROCESS_PROFILES:
            return PROCESS_PROFILES[profile]["fan_speed"]
        return None

    def execute_emergency_shutdown(self):
        """
        Thermal emergency protocol.
        When T >= 95°C:
        1. Kill non-essential processes
        2. Force fan to 100%
        3. Display critical alert
        """
        logger.critical("🚨 EXECUTING EMERGENCY THERMAL SHUTDOWN")

        # Kill processes
        killable_processes = ["steam", "chrome", "firefox", "code"]

        for proc_name in killable_processes:
            try:
                for proc in psutil.process_iter(["name"]):
                    if proc.name() == proc_name:
                        logger.warning(f"Killing {proc_name} for thermal protection")
                        proc.terminate()
            except Exception as e:
                logger.debug(f"Failed to kill {proc_name}: {e}")

        # Force fan to maximum
        try:
            self.hardware.run_nbfc("set -s 100")
        except Exception as e:
            logger.error(f"Failed to set fan to max in emergency: {e}")

        # Play alert sound (if available)
        self._play_alert_sound()

    def _play_alert_sound(self):
        """Play system alert sound."""
        try:
            import subprocess
            subprocess.run(
                ["paplay", "/usr/share/sounds/freedesktop/stereo/alarm-clock-elapsed.oga"],
                timeout=2,
            )
        except Exception:
            pass  # Sound not critical

    def check_fan_watchdog(
        self, current_temp: float, current_rpm: Optional[int]
    ) -> bool:
        """
        Watchdog monitoring: Alert if fan not spinning under thermal load.
        
        Returns:
            True if fan is stalled (potential failure)
        """
        thermal_cfg = self.config.get_thermal_config()

        rpm_threshold = thermal_cfg.get("watchdog_rpm_threshold", 1000)
        if (
            current_temp > thermal_cfg["watchdog_fan_threshold"]
            and (
                current_rpm is None
                or current_rpm == 0
                or current_rpm < rpm_threshold
            )
        ):
            logger.warning(f"⚠️  Fan stall detected at {current_temp}°C!")
            return True

        return False

    def calculate_thermal_gradient(self, temp_delta: Optional[float]) -> str:
        """
        Get human-readable thermal gradient description.
        
        Returns:
            "Stable", "Rising", or "Rapid Rise"
        """
        if temp_delta is None:
            return "Unknown"

        if temp_delta < 0.5:
            return "Stable ✓"
        elif temp_delta < 2.5:
            return "Rising ↗"
        else:
            return "Rapid Rise ↑↑"

    def get_cooldown_estimate(self, current_temp: float) -> str:
        """Estimate the cooldown time after high thermal load."""
        if current_temp is None:
            return "N/A"
        if current_temp < 50:
            return "Ready"
        seconds = int((current_temp - 40) * 12)
        minutes = max(1, seconds // 60)
        return f"~{minutes} min"

    def cleanup_swap_before_game(self) -> bool:
        """Clean swap and drop caches before a high-performance game session."""
        try:
            if psutil.virtual_memory().percent < 70:
                return False

            if self.hardware.is_pkexec_available():
                subprocess.run([self.hardware.binary_paths.get("pkexec", "pkexec"), "swapoff", "-a"], timeout=15)
                subprocess.run([self.hardware.binary_paths.get("pkexec", "pkexec"), "swapon", "-a"], timeout=15)
                subprocess.run([self.hardware.binary_paths.get("pkexec", "pkexec"), "bash", "-lc", "echo 3 > /proc/sys/vm/drop_caches"], timeout=10)
            else:
                subprocess.run(["sudo", "swapoff", "-a"], timeout=15)
                subprocess.run(["sudo", "swapon", "-a"], timeout=15)
                subprocess.run(["sudo", "bash", "-lc", "echo 3 > /proc/sys/vm/drop_caches"], timeout=10)

            logger.info("✅ Swap cleanup completed before gaming")
            return True
        except Exception as e:
            logger.debug(f"Swap cleanup failed: {e}")
            return False

    def refresh_profile_state(self) -> Optional[str]:
        """Refresh the active process profile and revert fans to silent after game closes."""
        new_profile = self.detect_active_profile()
        if self.active_profile and new_profile is None:
            logger.info("Game profile closed, reverting fans to silent mode")
            self.active_profile = None
            return "closed"

        if new_profile and new_profile != self.active_profile:
            self.active_profile = new_profile
            if new_profile == "gaming":
                self.cleanup_swap_before_game()
            return new_profile

        return new_profile
