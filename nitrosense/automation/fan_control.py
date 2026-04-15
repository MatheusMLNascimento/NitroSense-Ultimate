"""
Fan Control Logic - Direct interface to NBFC and thermal management.
"""

from typing import Optional
from ..core.logger import logger
from ..core.retry_strategy import GENTLE_RETRY
from ..core.constants import THERMAL_CONFIG, PERFORMANCE_CONFIG


class FanController:
    """
    Direct fan control via NBFC.
    Handles speed changes with validation and logging.
    """

    def __init__(self, hardware_manager, config_manager):
        self.hardware = hardware_manager
        self.config = config_manager
        self.current_speed = None
        logger.info("FanController initialized")

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

    def enable_auto_curve(self, config_name: str = "Acer Nitro AN515-51") -> bool:
        """Enable automatic thermal curve."""
        try:
            success, output = self.hardware.run_nbfc(
                f"config --apply '{config_name}'"
            )

            if success:
                logger.info("Auto thermal curve enabled")
            else:
                logger.warning(f"Auto curve setup failed: {output}")

            return success
        except Exception as e:
            logger.error(f"Exception in enable_auto_curve: {e}")
            return False

    def get_current_speed(self) -> Optional[int]:
        """Get current fan speed."""
        return self.current_speed

    def frost_mode_engage(self, duration_seconds: int = 120) -> bool:
        """
        Engage Frost Mode (maximum cooling for fixed duration).
        
        Args:
            duration_seconds: How long to maintain max speed
            
        Returns:
            True if engaged
        """
        logger.info(f"🥶 FROST MODE: Engaging {duration_seconds}s of max cooling")
        return self.set_fan_speed(100)
