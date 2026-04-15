"""
Abstract Hardware Interface for NitroSense Ultimate.

Provides abstraction layer between UI and hardware backend,
enabling testing with mock data on non-Acer hardware and CI/CD environments.

PATTERN: Strategy pattern with pluggable backends (Real vs Mock)
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class SensorReading:
    """Immutable sensor reading with timestamp and quality info."""
    value: float
    timestamp: float
    unit: str = ""
    quality: str = "good"  # "good", "degraded", "error"
    

class HardwareInterface(ABC):
    """
    Abstract base class for hardware backends.
    
    All UI components should depend on this interface, not concrete implementations.
    This enables easy testing with mock data.
    """
    
    @abstractmethod
    def get_cpu_temperature(self) -> Optional[float]:
        """Get CPU temperature in Celsius."""
        pass
    
    @abstractmethod
    def get_gpu_temperature(self) -> Optional[float]:
        """Get GPU temperature in Celsius."""
        pass
    
    @abstractmethod
    def get_cpu_usage(self) -> Optional[float]:
        """Get CPU usage percentage (0-100)."""
        pass
    
    @abstractmethod
    def get_gpu_usage(self) -> Optional[float]:
        """Get GPU usage percentage (0-100)."""
        pass

    @abstractmethod
    def get_ram_usage(self) -> Optional[float]:
        """Get RAM usage percentage (0-100)."""
        pass

    @abstractmethod
    def get_fan_rpm(self, fan_index: int = 0) -> Optional[float]:
        """Get fan RPM for given fan index."""
        pass
    
    @abstractmethod
    def get_gpu_memory_stats(self) -> Tuple[Optional[float], Optional[int], Optional[int]]:
        """Get GPU memory stats: utilization, used MB, total MB."""
        pass
    
    @abstractmethod
    def read_file_safe_retry(self, filepath: str, default: str = "", max_retries: int = 2) -> str:
        """Read file safely with retries for transient I/O issues."""
        pass

    @abstractmethod
    def set_fan_speed(self, speed: int) -> bool:
        """Set fan speed (0-100 percentage or RPM)."""
        pass
    
    @abstractmethod
    def has_root_privileges(self) -> bool:
        """Check if running with root/admin privileges."""
        pass
    
    @abstractmethod
    def check_dependencies(self) -> Dict[str, bool]:
        """Check for required dependencies."""
        pass
    
    @abstractmethod
    def bootstrap(self) -> Tuple[int, str]:
        """
        Initialize hardware backend.
        Returns: (error_code: int, message: str)
        """
        pass


class HardwareMock(HardwareInterface):
    """
    High-fidelity mock hardware backend for testing.
    
    Simulates realistic sensor values:
    - Temperature: Sine wave oscillation (30-65°C typical)
    - CPU/GPU Usage: Smooth random walk
    - Fan RPM: Proportional to temperature
    """
    
    def __init__(self, seed: float = 0.0):
        """
        Initialize mock with deterministic values for reproducible tests.
        
        Args:
            seed: Starting time offset for sine waves (enables different scenarios)
        """
        super().__init__()
        self.seed = seed
        self._time_offset = seed
        self._cpu_usage_base = 45.0
        self._gpu_usage_base = 25.0
        self._has_root = False
        
    def get_cpu_temperature(self) -> Optional[float]:
        """Simulate CPU temperature with sine wave (30-55°C)."""
        import time
        t = time.time() + self._time_offset
        # Sine wave: base 42°C ± 12°C, period 60 seconds
        return 42.0 + 12.0 * math.sin(t / 10.0)
    
    def get_gpu_temperature(self) -> Optional[float]:
        """Simulate GPU temperature (slightly lower, 25-45°C)."""
        import time
        t = time.time() + self._time_offset
        # Sine wave: base 35°C ± 10°C, slightly offset from CPU
        return 35.0 + 10.0 * math.sin(t / 12.0 + math.pi/4)
    
    def get_cpu_usage(self) -> Optional[float]:
        """Simulate CPU usage with smooth random walk."""
        import time
        import random
        random.seed(int(time.time()) // 5)  # New value every 5 seconds
        delta = random.uniform(-5, 5)
        self._cpu_usage_base = max(5, min(95, self._cpu_usage_base + delta))
        return self._cpu_usage_base
    
    def get_gpu_usage(self) -> Optional[float]:
        """Simulate GPU usage with smooth random walk."""
        import time
        import random
        random.seed(int(time.time()) // 7 + 1)  # Different seed, different phase
        delta = random.uniform(-3, 3)
        self._gpu_usage_base = max(0, min(80, self._gpu_usage_base + delta))
        return self._gpu_usage_base
    
    def get_ram_usage(self) -> Optional[float]:
        """Simulate RAM usage (relatively stable)."""
        import time
        import random
        random.seed(int(time.time()) // 10 + 2)
        return 45.0 + random.uniform(-2, 2)
    
    def get_fan_rpm(self, fan_index: int = 0) -> Optional[float]:
        """Simulate fan RPM proportional to temperature."""
        cpu_temp = self.get_cpu_temperature()
        if cpu_temp is None:
            return None
        # Fan curve: 0 RPM at 30°C, 5000 RPM at 65°C
        if cpu_temp < 30:
            return 1000.0
        elif cpu_temp > 65:
            return 5000.0
        else:
            return 1000.0 + (cpu_temp - 30) / (65 - 30) * 4000.0

    def get_gpu_memory_stats(self) -> Tuple[Optional[float], Optional[int], Optional[int]]:
        """Simulate GPU memory stats."""
        return 32.0, 4096, 8192

    def read_file_safe_retry(self, filepath: str, default: str = "", max_retries: int = 2) -> str:
        """Simulated safe file read for mock backend."""
        return default
    
    def set_fan_speed(self, speed: int) -> bool:
        """Mock fan speed set (always succeeds)."""
        return True
    
    def has_root_privileges(self) -> bool:
        """Mock privilege check (can be overridden for testing)."""
        return self._has_root
    
    def check_dependencies(self) -> Dict[str, bool]:
        """Mock dependency check (all present)."""
        return {
            "nbfc": True,
            "nvidia-smi": True,
            "sensors": True,
            "acer_wmi": True,
        }
    
    def bootstrap(self) -> Tuple[int, str]:
        """Mock bootstrap (always succeeds)."""
        return 0, "Hardware mock initialized"


class HardwareFactory:
    """Factory for creating hardware interface instances."""
    
    _instance: Optional[HardwareInterface] = None
    _use_mock = False
    
    @classmethod
    def create(cls, use_mock: bool = False) -> HardwareInterface:
        """
        Create hardware interface instance.
        
        Args:
            use_mock: If True, use mock backend for testing
            
        Returns:
            HardwareInterface instance (real or mock)
        """
        if cls._instance is not None:
            return cls._instance

        if use_mock:
            cls._instance = HardwareMock()
        else:
            # Import here to avoid circular dependency
            from .manager import HardwareManager
            cls._instance = HardwareManager()

        return cls._instance
    
    @classmethod
    def set_instance(cls, instance: HardwareInterface) -> None:
        """Set singleton instance (useful for testing)."""
        cls._instance = instance
    
    @classmethod
    def get_instance(cls) -> Optional[HardwareInterface]:
        """Get singleton instance."""
        return cls._instance
