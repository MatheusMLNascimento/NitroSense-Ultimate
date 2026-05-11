"""
Automation Engine for NitroSense Ultimate.

Consolidated fan control and AI predictive automation.
Combines NBFC fan control with predictive thermal management.
"""

import subprocess
import psutil
import time
import functools
from typing import Dict, Optional, Tuple

from ..core.logger import logger
from ..core.retry_strategy import GENTLE_RETRY
from ..core.constants import THERMAL_CONFIG, PERFORMANCE_CONFIG, PROCESS_PROFILES
from ..core.error_codes import ErrorCode, SafeOperation


class AutomationEngine:
    """
    Unified automation engine combining fan control and AI prediction.
    Handles NBFC commands and predictive thermal management.
    """

    def __init__(self, monitoring_engine, hardware_manager, config_manager):
        self.monitoring = monitoring_engine
        self.hardware = hardware_manager
        self.config = config_manager

        # Fan control state
        self.current_speed = None

        # AI prediction state
        self.predictive_mode_active = False
        self.active_profile = None
        self.game_heat_state = False
        self._profile_cache: Tuple[Optional[str], float] = (None, 0.0)
        self._profile_cache_ttl: float = PERFORMANCE_CONFIG.get("profile_detection_cache_ttl", 5.0)

        logger.info("AutomationEngine initialized")

    # Fan Control Methods
    def set_fan_speed(self, speed: int) -> bool:
        """
        Set fan speed via NBFC with retry/backoff for transient bus errors.

        Args:
            speed: Fan speed 0-100%

        Returns:
            True if command succeeds within allowed retries.
        """
        speed = max(0, min(100, speed))

        def _execute_set_speed() -> bool:
            """Execute the fan speed command."""
            success, output = self.hardware.run_nbfc(f"set -s {speed}")
            if success:
                self.current_speed = speed
                logger.info(f"Fan speed set to {speed}%")
                return True

            error_msg = output or "Unknown NBFC failure"
            logger.warning(f"Fan speed command failed: {error_msg}")
            raise RuntimeError(f"NBFC error: {error_msg}")

        try:
            return GENTLE_RETRY.execute_with_retry(_execute_set_speed)
        except Exception as e:
            logger.error(f"Fan speed command failed after all retries: {e}")
            return False

    def get_current_speed(self) -> Optional[int]:
        """Get current fan speed."""
        return self.current_speed

    # AI Prediction Methods
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
        # Emergency override
        if current_temp >= THERMAL_CONFIG["emergency_temp"]:
            return THERMAL_CONFIG["emergency_speed"]

        # Predictive boost for rising temperatures
        base_speed = self._calculate_base_speed(current_temp)
        if temp_delta and temp_delta > THERMAL_CONFIG["predictive_temp_delta"]:
            predictive_boost = THERMAL_CONFIG["predictive_activation_speed"]
            boosted_speed = min(100, base_speed + predictive_boost)
            logger.debug(f"Predictive boost: {base_speed}% -> {boosted_speed}% (ΔT={temp_delta:.1f}°C/s)")
            return boosted_speed

        return base_speed

    def _calculate_base_speed(self, temp: float) -> int:
        """Calculate base fan speed from thermal curve."""
        thresholds = THERMAL_CONFIG["temp_thresholds"]
        speeds = THERMAL_CONFIG["speed_thresholds"]

        if temp <= thresholds["Low"]:
            return speeds["Low"]
        elif temp <= thresholds["Mid"]:
            return speeds["Mid"]
        elif temp <= thresholds["High"]:
            return speeds["High"]
        else:
            return speeds["High"]  # Max speed for high temps

    def detect_active_profile(self) -> Optional[str]:
        """
        Detect which process profile is currently active.

        Returns:
            Profile name if gaming/video editing detected, None otherwise
        """
        cache_profile, cache_time = self._profile_cache
        if cache_profile and (time.time() - cache_time) < self._profile_cache_ttl:
            return cache_profile

        try:
            # Check running processes against known profiles
            running_procs = {p.name().lower() for p in psutil.process_iter(['name'])}

            for profile_name, profile_data in PROCESS_PROFILES.items():
                processes = profile_data.get("processes", [])
                if any(proc in running_procs for proc in processes):
                    self._profile_cache = (profile_name, time.time())
                    logger.info(f"Profile '{profile_name}' detected")
                    return profile_name

        except Exception as e:
            logger.debug(f"Profile detection error: {e}")

        self._profile_cache = (None, time.time())
        return None

    def apply_profile_settings(self, profile: str) -> bool:
        """
        Apply fan settings for detected profile.

        Args:
            profile: Profile name from PROCESS_PROFILES

        Returns:
            True if settings applied successfully
        """
        if profile not in PROCESS_PROFILES:
            logger.warning(f"Unknown profile: {profile}")
            return False

        profile_data = PROCESS_PROFILES[profile]
        fan_speed = profile_data.get("fan_speed", 50)

        if self.set_fan_speed(fan_speed):
            self.active_profile = profile
            logger.info(f"Applied {profile} profile: fan={fan_speed}%")
            return True

        return False

    def emergency_shutdown(self) -> None:
        """Emergency protocol: max fan speed and system warnings."""
        logger.critical("🚨 EMERGENCY: Critical temperature detected!")
        self.set_fan_speed(100)

        # Could add system notifications here
        try:
            subprocess.run(["notify-send", "NitroSense", "CRITICAL TEMPERATURE - MAX FAN SPEED"],
                         capture_output=True, timeout=5)
        except Exception:
            pass  # Notification failure shouldn't crash

    def reset_to_automatic(self) -> bool:
        """Reset fan control to automatic/BIOS mode."""
        try:
            # NBFC command to return to auto mode
            success, output = self.hardware.run_nbfc("set -a")
            if success:
                self.current_speed = None
                self.active_profile = None
                logger.info("Fan control reset to automatic")
                return True
            else:
                logger.error(f"Failed to reset fan control: {output}")
                return False
        except Exception as e:
            logger.error(f"Error resetting fan control: {e}")
            return False