"""
Advanced monitoring and sensor reading system for NitroSense Ultimate.
Handles temperature, GPU, and system metrics with intelligent caching.
"""

import time
import concurrent.futures
from typing import Dict, Optional, Tuple, List, Any
from collections import deque
from datetime import datetime
import psutil
from ..core.logger import logger
from ..core.constants import PERFORMANCE_CONFIG, SYSTEM_PATHS
from ..hardware.interface import HardwareInterface
from ..core.error_codes import ErrorCode
from ..resilience.state_machine import get_state_machine
from ..resilience.dirty_bit import get_dirty_bit_cache


class MonitoringEngine:
    """
    Central monitoring system for all hardware metrics.
    Provides cached, averaged data for stable UI updates.
    """
    __slots__ = ('hardware', 'watchdog', 'last_temp', 'last_cpu_temp', 'last_gpu_temp', 'last_nbfc_rpm', 'last_timestamp', 'monitoring_active', 'monitoring_thread', 'last_monitor_time', 'suspend_detected', 'state_machine', 'dirty_cache', 'temp_history', 'rpm_history', 'timestamp_history', 'update_counter')

    def __init__(self, hardware_manager: HardwareInterface, watchdog=None):
        self.hardware = hardware_manager
        self.watchdog = watchdog
        self.last_temp = 0.0
        self.last_cpu_temp = 0.0
        self.last_gpu_temp = 0.0
        self.last_nbfc_rpm = 0
        self.last_timestamp = 0.0
        self.monitoring_active = False
        self.monitoring_thread = None
        self.last_monitor_time = time.time()
        self.suspend_detected = False

        # Resilience components
        self.state_machine = get_state_machine()
        self.dirty_cache = get_dirty_bit_cache()

        # Data history for graphs
        self.temp_history = deque(
            maxlen=PERFORMANCE_CONFIG["graph_points"]
        )
        self.rpm_history = deque(
            maxlen=PERFORMANCE_CONFIG["graph_points"]
        )
        self.timestamp_history = deque(
            maxlen=PERFORMANCE_CONFIG["graph_points"]
        )

        self.update_counter = 0
        logger.info("MonitoringEngine initialized")

    def get_system_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive system metrics.
        
        Returns:
            Dictionary with all monitored values
        """
        # Parallel sensor reads
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            cpu_future = executor.submit(self._get_cpu_temperature)
            gpu_future = executor.submit(self._get_gpu_temperature)
            hotspot_future = executor.submit(self._get_gpu_hotspot_temperature)
            rpm_future = executor.submit(self._get_fan_rpm)

        metrics = {
            "cpu_temp": cpu_future.result(),
            "gpu_temp": gpu_future.result(),
            "gpu_hotspot": hotspot_future.result(),
            "fan_rpm": rpm_future.result(),
            "cpu_usage": self.hardware.get_cpu_usage(),
            "ram_usage": self.hardware.get_ram_usage(),
            "disk_usage": psutil.disk_usage("/").percent,
            "uptime": self._get_uptime(),
            "timestamp": datetime.now().timestamp(),
        }

        # Add to history
        if metrics["cpu_temp"]:
            self.temp_history.append(metrics["cpu_temp"])
            self.timestamp_history.append(metrics["timestamp"])

        if metrics["fan_rpm"]:
            self.rpm_history.append(metrics["fan_rpm"])

        self.update_counter += 1

        # Force garbage collection every N updates
        if self.update_counter % PERFORMANCE_CONFIG["gc_interval"] == 0:
            import gc
            gc.collect()

        return metrics

    def _get_cpu_temperature(self) -> Optional[float]:
        """Get CPU temperature from the hardware provider."""
        try:
            raw_temp = self.hardware.get_cpu_temperature()
            if raw_temp is not None and 0.0 <= raw_temp <= 110.0:
                self.last_cpu_temp = raw_temp
                return raw_temp

            if raw_temp is not None:
                logger.warning(f"Discarded CPU temperature outside valid range: {raw_temp}")
        except Exception as e:
            logger.debug(f"Failed to get CPU temperature: {e}", exc_info=True)

        return self.last_cpu_temp if 0.0 <= self.last_cpu_temp <= 110.0 else None

    def _get_gpu_temperature(self) -> Optional[float]:
        """Get GPU temperature from the hardware provider."""
        try:
            raw_temp = self.hardware.get_gpu_temperature()
            if raw_temp is not None and 0.0 <= raw_temp <= 110.0:
                self.last_gpu_temp = raw_temp
                return raw_temp

            if raw_temp is not None:
                logger.warning(f"Discarded GPU temperature outside valid range: {raw_temp}")
        except Exception as e:
            logger.debug(f"GPU temperature read failed: {e}", exc_info=True)

        return self.last_gpu_temp if 0.0 <= self.last_gpu_temp <= 110.0 else None

    def _get_gpu_hotspot_temperature(self) -> Optional[float]:
        """Get GPU hotspot temperature from the hardware provider."""
        try:
            return self._get_gpu_temperature()
        except Exception as e:
            logger.debug(f"GPU hotspot read failed: {e}", exc_info=True)
        return None

    def _get_fan_rpm(self) -> Optional[int]:
        """Get current fan RPM."""
        try:
            raw_rpm = self.hardware.get_fan_rpm()
            if raw_rpm is not None and 0 <= raw_rpm <= 25000:
                self.last_nbfc_rpm = int(raw_rpm)
                return int(raw_rpm)

            if raw_rpm is not None:
                logger.warning(f"Discarded fan RPM outside valid range: {raw_rpm}")
        except Exception as e:
            logger.error(f"Failed to get fan RPM: {e}", exc_info=True)
        return self.last_nbfc_rpm if 0 <= self.last_nbfc_rpm <= 25000 else None

    def _get_uptime(self) -> str:
        """Get system uptime as formatted string."""
        try:
            uptime_payload = self.hardware.read_file_safe_retry(SYSTEM_PATHS["UPTIME"])
            if uptime_payload:
                uptime_seconds = int(float(uptime_payload.split()[0]))
                days = uptime_seconds // 86400
                hours = (uptime_seconds % 86400) // 3600
                minutes = (uptime_seconds % 3600) // 60
                return f"{days}d {hours}h {minutes}m"
        except Exception as e:
            logger.warning(f"Failed to read uptime: {e}", exc_info=True)
            return "Unknown"
    
    def calculate_temp_change_rate(self, time_window: float) -> Optional[float]:
        """
        Calculate temperature change rate over the given time window.
        
        Args:
            time_window: Time window in seconds
            
        Returns:
            Temperature change in degrees C per second, or None
        """
        if len(self.temp_history) < 2:
            return None

        try:
            current_temp = self.temp_history[-1]
            past_temp = self.temp_history[0] if len(
                self.temp_history) > 1 else current_temp

            current_time = self.timestamp_history[-1]
            past_time = self.timestamp_history[0] if len(
                self.timestamp_history) > 1 else current_time

            time_diff = current_time - past_time
            if time_diff > 0:
                return (current_temp - past_temp) / time_diff

        except (ValueError, IndexError):
            pass

        return None

    def get_average_temperature(self) -> float:
        """Get average of recent temperatures."""
        if self.temp_history:
            return sum(self.temp_history) / len(self.temp_history)
        return 0.0

    def get_peak_temperature(self) -> float:
        """Get peak temperature from history."""
        if self.temp_history:
            return max(self.temp_history)
        return 0.0

    def reset_history(self) -> None:
        """Reset stored temperature and RPM history."""
        self.temp_history.clear()
        self.rpm_history.clear()
        self.timestamp_history.clear()

    def get_temperature_trend(self) -> List[float]:
        """Get temperature history for graphing."""
        return list(self.temp_history)

    def get_temperature_delta(self) -> float:
        """Get the temperature delta (change) from the last two readings."""
        if len(self.temp_history) >= 2:
            return self.temp_history[-1] - self.temp_history[-2]
        return 0.0

    def get_rpm_trend(self) -> List[int]:
        """Get RPM history for graphing."""
        return list(self.rpm_history)

    def check_throttling(self) -> bool:
        """Detect if CPU is being thermally throttled."""
        try:
            # Check if any CPU is at max frequency (indicates throttling)
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if "cpu MHz" in line:
                        freq_str = line.split(":")[-1].strip()
                        freq = float(freq_str)
                        if freq < 1000:  # Below 1GHz likely throttled
                            return True
        except Exception as e:
            logger.warning(f"Failed to check CPU throttling: {e}")
        return False

    def get_battery_health(self) -> Dict[str, Any]:
        """Get battery wear level and health."""
        try:
            battery = psutil.sensors_battery()
            return {
                "percent": battery.percent,
                "is_plugged": battery.power_plugged,
                "time_left": battery.secsleft if battery.secsleft != -1 else None,
            }
        except Exception as e:
            logger.warning(f"Failed to read battery health: {e}")
            return {"percent": None, "is_plugged": None}

    def start_monitoring(self) -> Tuple[ErrorCode, str]:
        """Start monitoring thread with IdlePriority for <0.5% CPU budget."""
        try:
            if self.monitoring_active:
                return ErrorCode.SUCCESS, "Monitoring already active"
            
            self.monitoring_active = True
            self.last_monitor_time = time.time()
            
            # Create and start background thread
            import threading
            self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self.monitoring_thread.start()
            
            logger.info("OK Monitoring started (background thread)")
            return ErrorCode.SUCCESS, "Monitoring active"
            
        except Exception as e:
            logger.error(f"Monitoring start failed: {e}")
            self.monitoring_active = False
            return ErrorCode.THREAD_CREATION_FAILED, str(e)
    
    def _monitoring_loop(self):
        # """Main monitoring loop with watchdog integration."""
        try:
            logger.info("Monitoring Monitoring loop started")
            while self.monitoring_active:
                now = time.time()
                elapsed = now - self.last_monitor_time
                self.last_monitor_time = now

                if elapsed > 10:
                    logger.info("System suspend/resume detected; pausing monitoring temporarily")
                    self.suspend_detected = True

                if self.suspend_detected:
                    self.suspend_detected = False
                    time.sleep(5.0)
                    continue

                # Get metrics
                metrics = self.get_system_metrics()
                
                # Update state machine atomically
                self.state_machine.update_batch({
                    "cpu_temp": metrics.get("cpu_temp", 0),
                    "gpu_temp": metrics.get("gpu_temp", 0),
                    "fan_rpm": metrics.get("fan_rpm", 0),
                })
                
                # Update dirty bit cache
                self.dirty_cache.update_cache("cpu_temp", metrics.get("cpu_temp", 0))
                self.dirty_cache.update_cache("gpu_temp", metrics.get("gpu_temp", 0))
                
                # Signal watchdog: "I'm alive"
                if self.watchdog:
                    self.watchdog.heartbeat()
                    logger.debug("💓 Heartbeat sent to watchdog")
                else:
                    logger.warning("⚠️  No watchdog attached to monitoring engine")
                
                # Sleep to budge CPU <0.5% (1s interval for IdlePriority)
                time.sleep(1.0)
                
        except Exception as e:
            logger.error(f"Monitoring loop error: {e}")
        finally:
            self.monitoring_active = False
    
    def stop_monitoring(self) -> Tuple[ErrorCode, str]:
        try:
            self.monitoring_active = False
            
            if self.monitoring_thread and self.monitoring_thread.is_alive():
                # Wait for thread to finish
                self.monitoring_thread.join(timeout=2.0)
                logger.info("OK Monitoring stopped")
            
            return ErrorCode.SUCCESS, "Monitoring stopped"
            
        except Exception as e:
            logger.error(f"Monitoring stop failed: {e}")
            return ErrorCode.UNKNOWN_ERROR, str(e)
