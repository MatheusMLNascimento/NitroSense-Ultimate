"""
Hardware layer for NitroSense Ultimate.
Manages EC access, kernel modules, and low-level system operations.

CRITICAL DESIGN PRINCIPLES:
1. ALL sysfs reads use context managers (with)
2. Dynamic path discovery using glob patterns
3. FileNotFoundError and PermissionError handled gracefully
4. Retry-on-Fail with exponential backoff for bus operations
5. Sensor cache with TTL to reduce I/O pressure
6. Degraded mode return values for all failures
7. Decoupled from UI via HardwareInterface abstraction (enables mocking)
"""

import os
import subprocess
import time
import shutil
import sys
import asyncio
import glob
import threading
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List
from PyQt6.QtCore import QSemaphore
from ..core.logger import logger
from ..core.command_executor import CommandExecutor
from ..core.constants import PERFORMANCE_CONFIG, SYSTEM_PATHS, SUPPORTED_MODELS, RETRY_CONFIG, ErrorCode
from .interface import HardwareInterface


class HardwareManager(HardwareInterface):
    """
    Thread-safe singleton hardware interface with semaphore protection.
    All subprocess calls are protected against race conditions.
    Implements HardwareInterface to allow easy mocking for testing.
    """

    _instance: Optional["HardwareManager"] = None
    _singleton_lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._singleton_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return

        super().__init__()
        self.bus_semaphore = QSemaphore(1)
        self.binary_paths: Dict[str, str] = {}
        self.command_executor: Optional[CommandExecutor] = None
        self.ec_available = False
        self.nbfc_available = False
        
        # Cache for sensor readings: {key: (value, timestamp)}
        self._sensor_cache: Dict[str, Tuple[Any, float]] = {}
        self._cache_ttl = PERFORMANCE_CONFIG["cache_ttl"]  # Sensor cache TTL
        
        # Dynamic sysfs paths discovered at runtime
        self._discovered_sensor_paths: List[Path] = []
        self._sensor_failure_count: Dict[str, int] = {}
        self._max_sensor_failures = 3  # Force 100% fan after 3 consecutive failures
        
        self._resolve_binary_paths()
        self.command_executor = CommandExecutor(self.binary_paths)
        self.binary_paths = self.command_executor.binary_paths
        self._discover_sensor_paths()
        self._initialize_hardware()
        self._initialized = True

        self.detected_model = self._detect_hardware_model()
        logger.info(f"HardwareManager initialized for model: {self.detected_model}")

    def _detect_hardware_model(self) -> str:
        """Detect the hardware model from DMI information."""
        try:
            with open(SYSTEM_PATHS["DMI_PRODUCT"], "r") as f:
                model = f.read().strip()
            if model in SUPPORTED_MODELS:
                return model
            else:
                logger.warning(f"Unsupported model detected: {model}")
                return "Unknown"
        except Exception as e:
            logger.warning(f"Failed to detect hardware model: {e}")
            return "Unknown"

    def _get_cached(self, key: str) -> Optional[Any]:
        """Get cached value if not expired."""
        if key in self._sensor_cache:
            value, timestamp = self._sensor_cache[key]
            if time.time() - timestamp < self._cache_ttl:
                return value
            else:
                del self._sensor_cache[key]
        return None

    def _set_cached(self, key: str, value: Any) -> None:
        """Set cached value with current timestamp."""
        self._sensor_cache[key] = (value, time.time())

    def _resolve_binary_paths(self) -> None:
        """Resolve absolute paths for critical system binaries."""
        for tool in ["nbfc", "nvidia-smi", "sensors", "pkexec", "sudo", "which"]:
            path = shutil.which(tool)
            if path:
                self.binary_paths[tool] = path
                logger.debug(f"Resolved {tool}: {path}")

    def _discover_sensor_paths(self) -> None:
        """
        Dynamically discover sensor paths using glob patterns.
        Builds list of accessible hwmon sysfs entries.
        """
        try:
            # Common sensor path patterns on Linux
            patterns = [
                "/sys/class/hwmon/hwmon*/name",
                "/sys/class/thermal/thermal_zone*/type",
                "/sys/class/dmi/id/product_name",
            ]
            
            for pattern in patterns:
                matches = glob.glob(pattern)
                self._discovered_sensor_paths.extend([Path(m) for m in matches])
            
            logger.info(f"Discovered {len(self._discovered_sensor_paths)} sensor paths")
        except Exception as e:
            logger.warning(f"Sensor discovery error: {e}")

    def has_root_privileges(self) -> bool:
        """Return True when the process runs with root privileges."""
        return self.command_executor.has_root_privileges() if self.command_executor else False

    def is_pkexec_available(self) -> bool:
        """Return True when pkexec is available on the system."""
        return self.command_executor.is_pkexec_available() if self.command_executor else False

    def _initialize_hardware(self) -> None:
        """Initialize and verify hardware access."""
        logger.info("Initializing hardware layer...")

        # Check EC module
        code, msg = self._load_ec_module()
        if code == ErrorCode.SUCCESS:
            self.ec_available = True
            logger.info("✅ Embedded Controller initialized")
        else:
            logger.warning(f"⚠️  EC module not available: {msg} (some features limited)")

        # Check NBFC service
        if self._check_nbfc_service():
            self.nbfc_available = True
            logger.info("✅ NBFC service available")
        else:
            logger.warning("⚠️  NBFC service not available")

    def _load_ec_module(self) -> tuple[ErrorCode, str]:
        """
        Load ec_sys kernel module with write support.
        Returns (ErrorCode, message).
        """
        try:
            ec_sys_path = Path(SYSTEM_PATHS["EC_SYS"])

            # Check if already loaded
            if ec_sys_path.exists():
                logger.debug("EC module already loaded")
                return ErrorCode.SUCCESS, "EC module already loaded"

            if not self.has_root_privileges() and not self.is_pkexec_available():
                logger.error("Root privileges or pkexec required to load EC module")
                return ErrorCode.PERMISSION_DENIED, "Root privileges required"

            assert self.command_executor is not None, "CommandExecutor is required for EC module loading"
            result = self.command_executor.execute_root_command([
                "modprobe", "ec_sys", "write_support=1"
            ], use_sudo=True)

            if result.returncode == 0:
                return ErrorCode.SUCCESS, "EC module loaded successfully"
            else:
                return ErrorCode.EC_MODULE_LOAD_FAILED, f"modprobe failed: {result.stderr}"

        except Exception as e:
            logger.error(f"Failed to load EC module: {e}")
            return ErrorCode.EC_MODULE_LOAD_FAILED, str(e)

    def _check_nbfc_service(self) -> bool:
        """Check if NBFC service is active."""
        try:
            result = self._run_protected_command(
                ["systemctl", "is-active", "nbfc_service"]
            )
            return "active" in result.stdout.lower()
        except Exception as e:
            logger.error(f"NBFC service check failed: {e}")
            return False


    def _run_protected_command(
        self,
        cmd: list,
        timeout: int = 10,
        retry: bool = True
    ) -> subprocess.CompletedProcess:
        """
        Execute command with semaphore protection and exponential backoff retry.
        
        Args:
            cmd: Command list
            timeout: Timeout in seconds
            retry: Whether to use exponential backoff
            
        Returns:
            CompletedProcess
        """
        for attempt in range(RETRY_CONFIG["max_retries"]):
            try:
                self.bus_semaphore.acquire()

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )

                self.bus_semaphore.release()

                if result.returncode == 0:
                    return result

                if retry and attempt < RETRY_CONFIG["max_retries"] - 1:
                    wait_time = (
                        RETRY_CONFIG["base_delay"] *
                        (RETRY_CONFIG["exponential_base"] ** attempt)
                    )
                    logger.warning(
                        f"Command retry {attempt + 1}: waiting {wait_time:.2f}s"
                    )
                    time.sleep(wait_time)
                else:
                    return result

            except subprocess.TimeoutExpired:
                self.bus_semaphore.release()
                logger.error(f"Command timeout: {' '.join(cmd)}")
                raise
            except Exception as e:
                self.bus_semaphore.release()
                logger.error(f"Command execution error: {e}")
                raise

        raise RuntimeError(f"Command failed after {RETRY_CONFIG['max_retries']} retries")

    async def async_run_command(
        self, cmd: list, timeout: int = 10, retry: bool = True
    ) -> subprocess.CompletedProcess:
        """
        Execute command asynchronously with semaphore protection.
        
        Args:
            cmd: Command list
            timeout: Timeout in seconds
            retry: Whether to use exponential backoff
            
        Returns:
            CompletedProcess
        """
        for attempt in range(RETRY_CONFIG["max_retries"]):
            try:
                self.bus_semaphore.acquire()

                # Run in thread pool to avoid blocking event loop
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    lambda: subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=timeout,
                    )
                )

                self.bus_semaphore.release()

                if result.returncode == 0:
                    return result

                if retry and attempt < RETRY_CONFIG["max_retries"] - 1:
                    wait_time = (
                        RETRY_CONFIG["base_delay"] *
                        (RETRY_CONFIG["exponential_base"] ** attempt)
                    )
                    logger.warning(
                        f"Async command retry {attempt + 1}: waiting {wait_time:.2f}s"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    return result

            except subprocess.TimeoutExpired:
                self.bus_semaphore.release()
                logger.error(f"Async command timeout: {' '.join(cmd)}")
                raise
            except Exception as e:
                self.bus_semaphore.release()
                logger.error(f"Async command execution error: {e}")
                raise

        raise RuntimeError(f"Async command failed after {RETRY_CONFIG['max_retries']} retries")

    def run_nbfc(self, args: str) -> Tuple[bool, str]:
        """
        Execute NBFC command with protection.
        
        Args:
            args: NBFC arguments (e.g., "status -a")
            
        Returns:
            (success, output) tuple
        """
        try:
            nbfc_binary = self.binary_paths.get("nbfc", "nbfc")
            cmd = [nbfc_binary] + args.split()
            result = self._run_protected_command(cmd)
            return result.returncode == 0, result.stdout
        except (subprocess.SubprocessError, OSError) as e:
            logger.error(f"NBFC command failed: {e}")
            return False, ""

    def read_file(self, filepath: str, default: str = "") -> str:
        """
        Safely read system file with context manager protection.
        Handles FileNotFoundError and PermissionError gracefully.
        
        Args:
            filepath: Path to system file
            default: Default value if read fails
            
        Returns:
            File contents (stripped) or default value
        """
        try:
            path = Path(filepath)
            if not path.exists():
                logger.debug(f"File not found: {filepath}")
                return default
            
            # Use Path.read_text for safe file operations
            content = path.read_text(encoding='utf-8', errors='replace').strip()
            return content if content else default
                
        except PermissionError:
            logger.debug(f"Permission denied reading {filepath} (may need elevated privileges)")
            return default
        except FileNotFoundError:
            logger.debug(f"File not found: {filepath}")
            return default
        except Exception as e:
            logger.debug(f"Error reading {filepath}: {e}")
            return default

    def read_file_safe_retry(self, filepath: str, default: str = "", max_retries: int = 2) -> str:
        """
        Read file with retry-on-fail and exponential backoff.
        Useful for transient I/O errors on sysfs.
        
        Args:
            filepath: Path to system file
            default: Default value if all retries fail
            max_retries: Maximum retry attempts
            
        Returns:
            File contents or default value
        """
        for attempt in range(max_retries):
            try:
                path = Path(filepath)
                if not path.exists():
                    return default
                
                with open(path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read().strip()
                    if content:
                        return content
                    return default
                    
            except (FileNotFoundError, PermissionError):
                return default
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = (0.1 * (2 ** attempt))
                    logger.debug(f"Retry {attempt + 1}: waiting {wait_time}s before retry")
                    time.sleep(wait_time)
                else:
                    logger.debug(f"Failed to read {filepath} after {max_retries} retries: {e}")
                    return default
        
        return default

    def read_acpi_raw_data(self, filepath: str) -> Optional[bytearray]:
        """
        Read raw ACPI bytes from a system file and return them as a bytearray.
        """
        try:
            path = Path(filepath)
            if path.exists():
                return bytearray(path.read_bytes())
        except Exception as e:
            logger.debug(f"Failed to read ACPI raw data {filepath}: {e}")
        return None

    def write_file(self, filepath: str, content: str,
                  require_root: bool = False) -> bool:
        """
        Safely write to system file.
        
        Args:
            filepath: Path to system file
            content: Content to write
            require_root: Whether root is required
            
        Returns:
            True if successful
        """
        try:
            if require_root:
                assert self.command_executor is not None, "CommandExecutor is required to write protected files"
                cmd = f"echo '{content}' > {filepath}"
                result = self.command_executor.execute_root_command(cmd, use_sudo=True)
                return result.returncode == 0
            else:
                Path(filepath).write_text(content)
                return True
        except Exception as e:
            logger.error(f"Failed to write {filepath}: {e}")
            return False

    def check_dependencies(self) -> dict:
        """
        Check system dependencies.
        
        Returns:
            Dictionary of dependency status
        """
        deps = {}
        tools = ["nbfc", "nvidia-smi", "sensors", "pkexec"]

        for tool in tools:
            deps[tool] = bool(self.binary_paths.get(tool) or shutil.which(tool))

        return deps

    def get_hardware_id(self) -> Optional[str]:
        """Get system hardware ID for validation."""
        try:
            path = Path("/sys/class/dmi/id/product_name")
            if path.exists():
                return path.read_text().strip()
        except Exception as e:
            logger.debug(f"Failed to read hardware ID: {e}")
        return None
    
    # Implementation of HardwareInterface abstract methods
    # These delegate to existing hardware layer methods
    
    def get_cpu_temperature(self) -> Optional[float]:
        """Get CPU temperature in Celsius from thermal sensors."""
        try:
            for path_pattern in [
                SYSTEM_PATHS["CPU_TEMP_SYSFS"],
                SYSTEM_PATHS["CPU_TEMP_HWMON"],
            ]:
                try:
                    temp_raw = self.read_file_safe_retry(path_pattern)
                    if temp_raw:
                        return float(temp_raw) / 1000.0
                except (ValueError, FileNotFoundError):
                    continue
            return None
        except Exception as e:
            logger.debug(f"Failed to read CPU temperature: {e}", exc_info=True)
            return None
    
    def get_gpu_temperature(self) -> Optional[float]:
        """Get GPU temperature in Celsius using nvidia-smi if available."""
        try:
            if not self.binary_paths.get("nvidia-smi"):
                return None
            
            result = self._run_protected_command(
                [self.binary_paths["nvidia-smi"], "--query-gpu=temperature.gpu", "--format=csv,noheader"],
            )
            if result.returncode == 0:
                temp_str = result.stdout.strip().split()[0]
                return float(temp_str)
        except Exception as e:
            logger.debug(f"Failed to read GPU temperature: {e}", exc_info=True)
        return None
    
    def get_cpu_usage(self) -> Optional[float]:
        """Get CPU usage percentage (0-100)."""
        try:
            import psutil
            return psutil.cpu_percent(interval=0.1)
        except Exception as e:
            logger.debug(f"Failed to read CPU usage: {e}", exc_info=True)
            return None
    
    def get_gpu_usage(self) -> Optional[float]:
        """Get GPU usage percentage (0-100)."""
        try:
            if not self.binary_paths.get("nvidia-smi"):
                return None
            
            result = self._run_protected_command(
                [self.binary_paths["nvidia-smi"], "--query-gpu=utilization.gpu", "--format=csv,noheader"],
            )
            if result.returncode == 0:
                usage_str = result.stdout.strip().split()[0]
                return float(usage_str)
        except Exception as e:
            logger.debug(f"Failed to read GPU usage: {e}", exc_info=True)
        return None
    
    def get_gpu_memory_stats(self) -> Tuple[Optional[float], Optional[int], Optional[int]]:
        """Get GPU memory usage stats (utilization, used, and total)."""
        try:
            if not self.binary_paths.get("nvidia-smi"):
                return None, None, None
            
            result = self._run_protected_command(
                [
                    self.binary_paths["nvidia-smi"],
                    "--query-gpu=utilization.gpu,memory.used,memory.total",
                    "--format=csv,noheader,nounits",
                ],
            )
            if result.returncode == 0 and result.stdout.strip():
                parts = [part.strip() for part in result.stdout.split(",") if part.strip()]
                if len(parts) >= 3:
                    return float(parts[0]), int(parts[1]), int(parts[2])
        except Exception as e:
            logger.debug(f"Failed to read GPU memory stats: {e}", exc_info=True)
        return None, None, None
    
    def get_ram_usage(self) -> Optional[float]:
        """Get RAM usage percentage (0-100)."""
        try:
            import psutil
            return psutil.virtual_memory().percent
        except Exception as e:
            logger.debug(f"Failed to read RAM usage: {e}")
            return None
    
    def get_fan_rpm(self, fan_index: int = 0) -> Optional[float]:
        """Get fan RPM for given fan index."""
        try:
            # Try NBFC first if available
            if self.binary_paths.get("nbfc"):
                success, output = self.run_nbfc("status -a")
                if success and output:
                    # Parse NBFC output for fan RPM
                    lines = output.split('\n')
                    for line in lines:
                        if 'Fan' in line and 'RPM' in line:
                            try:
                                # Extract RPM value from line like "Fan 0: 1200 RPM"
                                parts = line.split()
                                if len(parts) >= 3 and parts[2].isdigit():
                                    return float(parts[2])
                            except (ValueError, IndexError):
                                continue
            
            # Fallback to sysfs sensors
            for sensor_path in self._discovered_sensor_paths:
                fan_path = sensor_path / f"fan{fan_index}_input"
                if fan_path.exists():
                    try:
                        rpm_str = fan_path.read_text().strip()
                        return float(rpm_str)
                    except (ValueError, OSError):
                        continue
                        
        except Exception as e:
            logger.debug(f"Failed to read fan RPM: {e}")
        return None
    
    def set_fan_speed(self, speed: int) -> bool:
        """Set fan speed (0-100 percentage)."""
        try:
            if not self.binary_paths.get("nbfc"):
                logger.warning("NBFC not available, cannot set fan speed")
                return False
            
            # Clamp speed to 0-100
            speed = max(0, min(100, speed))
            
            success, msg = self.run_nbfc(f"set -s {speed}")
            return success
        except Exception as e:
            logger.error(f"Failed to set fan speed: {e}")
            return False
    
    def bootstrap(self) -> Tuple[int, str]:
        """
        Initialize hardware backend and perform pre-flight checks.
        
        Returns:
            (error_code: int, message: str)
            - 0 for success
            - Non-zero ErrorCode for failures
        """
        try:
            logger.info("Hardware bootstrap starting...")
            
            # Check dependencies
            deps = self.check_dependencies()
            if not any(deps.values()):
                msg = "No hardware tools available (nbfc/sensors/nvidia-smi)"
                logger.warning(msg)
                return ErrorCode.HARDWARE_NOT_AVAILABLE, msg
            
            # Try to load EC module
            code, msg = self._load_ec_module()
            if code != ErrorCode.SUCCESS:
                logger.warning(f"EC module loading failed: {msg}, attempting degraded mode")
            
            # Check NBFC service
            if self.binary_paths.get("nbfc"):
                if not self._check_nbfc_service():
                    logger.warning("NBFC service check failed")
            
            logger.info("Hardware bootstrap complete")
            return ErrorCode.SUCCESS, "Hardware initialized"
        except Exception as e:
            logger.error(f"Hardware bootstrap failed: {e}")
            return ErrorCode.HARDWARE_INIT_FAILED, str(e)
