"""
Threading infrastructure for NitroSense Ultimate.
Worker threads, thread pool, and async operations.
"""

import time
from typing import Dict, Any, Optional, Callable
from PyQt6.QtCore import QThread, QThreadPool, QRunnable, pyqtSignal, QObject
from PyQt6.QtCore import QSemaphore
import psutil
import subprocess
from collections import deque
from ..core.logger import logger
from ..core.constants import PERFORMANCE_CONFIG


class HardwareSignals(QObject):
    """Signals emitted by hardware worker."""
    update_signal = pyqtSignal(dict)  # Hardware data
    error_signal = pyqtSignal(str)    # Error message
    finished_signal = pyqtSignal()    # Worker finished


class HardwareWorker(QThread):
    """
    Background worker thread for hardware monitoring.
    Reads temperatures, RPM, and system metrics without blocking UI.
    """

    update_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)

    def __init__(self, hardware_manager, update_interval: int = 1500):
        super().__init__()
        self.hardware_manager = hardware_manager
        self.update_interval = update_interval / 1000.0  # Convert to seconds
        self.is_running = False

        # Data caching for averaging
        self.temp_cache = deque(maxlen=PERFORMANCE_CONFIG["cache_size"])
        self.gpu_cache = deque(maxlen=PERFORMANCE_CONFIG["cache_size"])
        self.cpu_cache = deque(maxlen=PERFORMANCE_CONFIG["cache_size"])

        logger.info("HardwareWorker initialized")

    def run(self):
        """Main worker loop."""
        self.is_running = True
        logger.info("HardwareWorker started")

        while self.is_running:
            try:
                data = self._gather_hardware_data()
                self.update_signal.emit(data)
                time.sleep(self.update_interval)

            except Exception as e:
                self.error_signal.emit(f"Hardware monitoring error: {e}")
                logger.error(f"Worker error: {e}")
                time.sleep(1)

    def stop(self):
        """Stop worker thread gracefully."""
        self.is_running = False
        self.wait()
        logger.info("HardwareWorker stopped")

    def _gather_hardware_data(self) -> Dict[str, Any]:
        """Collect all hardware metrics."""
        data = {}

        # CPU Temperature via nbfc
        success, nbfc_output = self.hardware_manager.run_nbfc("status -a")
        if success:
            temp = self._parse_nbfc_output(nbfc_output)
            if temp is not None:
                self.temp_cache.append(temp)
                data["cpu_temp"] = float(sum(self.temp_cache)) / len(
                    self.temp_cache
                )  # Average

        # GPU Temperature
        gpu_temp = self._get_nvidia_temp()
        if gpu_temp is not None:
            self.gpu_cache.append(gpu_temp)
            data["gpu_temp"] = float(sum(self.gpu_cache)) / len(self.gpu_cache)

        # Fan RPM
        rpm = self._parse_nbfc_rpm(nbfc_output) if success else None
        data["rpm"] = rpm

        # System metrics
        data["cpu_usage"] = psutil.cpu_percent(interval=0.1)
        data["ram_usage"] = psutil.virtual_memory().percent
        data["disk_io"] = self._get_disk_io()

        # Timestamp
        data["timestamp"] = time.time()

        return data

    def _parse_nbfc_output(self, output: str) -> Optional[float]:
        """Extract CPU temperature from nbfc status output."""
        try:
            for line in output.split("\n"):
                if "Temperature" in line and "°C" in line:
                    # Extract number before °C
                    temp_str = line.split(":")[-1].replace("°C", "").strip()
                    return float(temp_str)
        except Exception as e:
            logger.debug(f"Failed to parse NBFC temperature: {e}")
        return None

    def _parse_nbfc_rpm(self, output: str) -> Optional[int]:
        """Extract fan RPM from nbfc status output."""
        try:
            for line in output.split("\n"):
                if "Speed" in line or "RPM" in line:
                    parts = line.split(":")
                    if len(parts) > 1:
                        rpm_str = parts[-1].replace("RPM", "").strip()
                        return int(float(rpm_str))
        except Exception as e:
            logger.debug(f"Failed to parse NBFC RPM: {e}")
        return None

    def _get_nvidia_temp(self) -> Optional[float]:
        """Get GPU temperature via nvidia-smi."""
        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=temperature.gpu",
                    "--format=csv,noheader",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0:
                temp_str = result.stdout.strip().split("\n")[0]
                return float(temp_str)

        except Exception as e:
            logger.debug(f"Failed to get NVIDIA temperature: {e}")

        return None

    def _get_disk_io(self) -> Dict[str, float]:
        """Get disk I/O statistics."""
        try:
            io = psutil.disk_io_counters()
            return {
                "read_mb_s": io.read_bytes / (1024 * 1024),
                "write_mb_s": io.write_bytes / (1024 * 1024),
            }
        except Exception:
            return {"read_mb_s": 0.0, "write_mb_s": 0.0}


class AsyncTaskRunner(QRunnable):
    """
    Async task runner for thread pool.
    Executes functions without blocking UI.
    """

    def __init__(self, func: Callable, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        """Execute the task."""
        try:
            self.func(*self.args, **self.kwargs)
        except Exception as e:
            logger.error(f"Async task failed: {e}")


class ThreadPoolManager:
    """Manages QThreadPool for async operations."""

    def __init__(self, max_threads: int = PERFORMANCE_CONFIG["thread_pool_size"]):
        self.pool = QThreadPool.globalInstance()
        self.pool.setMaxThreadCount(max_threads)
        logger.info(f"ThreadPoolManager initialized with {max_threads} threads")

    def run_async(self, func: Callable, *args, **kwargs) -> None:
        """
        Execute function asynchronously in thread pool.
        
        Args:
            func: Callable to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
        """
        task = AsyncTaskRunner(func, *args, **kwargs)
        self.pool.start(task)

    def wait_all(self) -> None:
        """Wait for all tasks to complete."""
        self.pool.waitForDone()

    def clear(self) -> None:
        """Clear pending tasks."""
        self.pool.clear()
