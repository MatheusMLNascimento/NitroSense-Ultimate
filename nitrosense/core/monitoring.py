"""
Advanced monitoring and sensor reading system for NitroSense Ultimate.
Handles temperature, GPU, and system metrics with intelligent caching.
"""

import subprocess
import time
import concurrent.futures
from typing import Dict, Optional, Tuple, List, Any
from collections import deque
from datetime import datetime
import psutil
from ..core.logger import logger
from ..core.constants import PERFORMANCE_CONFIG
from ..core.error_codes import ErrorCode
from ..resilience.state_machine import get_state_machine
from ..resilience.dirty_bit import get_dirty_bit_cache


class MonitoringEngine:
    """
    Central monitoring system for all hardware metrics.
    Provides cached, averaged data for stable UI updates.
    """

    def __init__(self, hardware_manager, watchdog=None):
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
        metrics = {
            "cpu_temp": self._get_cpu_temperature(),
            "gpu_temp": self._get_gpu_temperature(),
            "gpu_hotspot": self._get_gpu_hotspot_temperature(),
            "fan_rpm": self._get_fan_rpm(),
            "cpu_usage": psutil.cpu_percent(interval=0),
            "ram_usage": psutil.virtual_memory().percent,
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
        """Get CPU temperature from NBFC or ACPI fallback."""
        try:
            success, output = self.hardware.run_nbfc("status -a")
            if success:
                temp = self._parse_temperature(output)
                if temp:
                    self.last_temp = temp
                    return temp
        except Exception as e:
            logger.error(f"Failed to get CPU temperature from NBFC: {e}")

        # Fallback using raw ACPI bytes
        read_acpi = getattr(self.hardware, "read_acpi_raw_data", None)
        if callable(read_acpi):
            raw_bytes = read_acpi("/sys/class/thermal/thermal_zone0/temp")
            if raw_bytes:
                try:
                    temp_value = int(raw_bytes.decode().strip())
                    temp = temp_value / 1000.0
                    self.last_temp = temp
                    return temp
                except Exception as e:
                    logger.debug(f"ACPI fallback parse failed: {e}")

        return None

    def _get_gpu_temperature(self) -> Optional[float]:
        """Get GPU temperature from nvidia-smi."""
        try:
            binary_paths = getattr(self.hardware, "binary_paths", {}) or {}
            nvidia_binary = binary_paths.get("nvidia-smi", "nvidia-smi")
            result = subprocess.run(
                [
                    nvidia_binary,
                    "--query-gpu=temperature.gpu",
                    "--format=csv,noheader",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0:
                return float(result.stdout.strip().split("\n")[0])
        except Exception as e:
            logger.debug(f"GPU temperature read failed: {e}")

        return None

    def _get_gpu_hotspot_temperature(self) -> Optional[float]:
        """Get GPU hotspot temperature from nvidia-smi."""
        try:
            binary_paths = getattr(self.hardware, "binary_paths", {}) or {}
            nvidia_binary = binary_paths.get("nvidia-smi", "nvidia-smi")
            result = subprocess.run(
                [
                    nvidia_binary,
                    "--query-gpu=temperature.gpu,temperature.memory",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                values = [float(v) for v in result.stdout.strip().split(",") if v.strip()]
                return max(values) if values else None
        except Exception as e:
            logger.debug(f"GPU hotspot read failed: {e}")

        return None

    def _get_fan_rpm(self) -> Optional[int]:
        """Get current fan RPM."""
        try:
            success, output = self.hardware.run_nbfc("status -a")
            if success:
                return self._parse_rpm(output)
        except Exception as e:
            logger.error(f"Failed to get fan RPM: {e}")
        return None

    def _get_uptime(self) -> str:
        """Get system uptime as formatted string."""
        try:
            with open("/proc/uptime") as f:
                uptime_seconds = int(float(f.read().split()[0]))

            days = uptime_seconds // 86400
            hours = (uptime_seconds % 86400) // 3600
            minutes = (uptime_seconds % 3600) // 60

            return f"{days}d {hours}h {minutes}m"
        except Exception as e:
            logger.warning(f"Failed to read uptime: {e}")
            return "N/A"

    def _parse_temperature(self, nbfc_output: str) -> Optional[float]:
        """Parse temperature from NBFC output."""
        try:
            for line in nbfc_output.split("\n"):
                if "Temperature" in line and "°C" in line:
                    temp_str = line.split(":")[-1].replace("°C", "").strip()
                    return float(temp_str)
        except Exception as e:
            logger.debug(f"Temperature parsing failed: {e}")
        return None

    def _parse_rpm(self, nbfc_output: str) -> Optional[int]:
        """Parse RPM from NBFC output."""
        try:
            for line in nbfc_output.split("\n"):
                if "RPM" in line or "Speed" in line:
                    parts = line.split(":")
                    if len(parts) > 1:
                        rpm_str = parts[-1].replace("RPM", "").strip()
                        return int(float(rpm_str))
        except Exception as e:
            logger.debug(f"RPM parsing failed: {e}")
        return None

    def get_temperature_delta(self, time_window: float = 1.5) -> Optional[float]:
        """
        Calculate temperature change rate (dT/dt).
        Used for predictive fan control.
        
        Args:
            time_window: Time window in seconds
            
        Returns:
            Temperature change in °C per second, or None
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
            
            logger.info("✅ Monitoring started (background thread)")
            return ErrorCode.SUCCESS, "Monitoring active"
            
        except Exception as e:
            logger.error(f"Monitoring start failed: {e}")
            self.monitoring_active = False
            return ErrorCode.THREAD_CREATION_FAILED, str(e)
    
    def _monitoring_loop(self):
        """Main monitoring loop with watchdog integration."""
        try:
            logger.info("🔄 Monitoring loop started")
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
        """Stop monitoring thread gracefully."""
        try:
            self.monitoring_active = False
            
            if self.monitoring_thread and self.monitoring_thread.is_alive():
                # Wait for thread to finish
                self.monitoring_thread.join(timeout=2.0)
                logger.info("✅ Monitoring stopped")
            
            return ErrorCode.SUCCESS, "Monitoring stopped"
            
        except Exception as e:
            logger.error(f"Monitoring stop failed: {e}")
            return ErrorCode.UNKNOWN_ERROR, str(e)
