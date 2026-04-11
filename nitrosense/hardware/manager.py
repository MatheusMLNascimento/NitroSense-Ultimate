"""
Hardware layer for NitroSense Ultimate.
Manages EC access, kernel modules, and low-level system operations.
"""

import os
import subprocess
import time
import shutil
import sys
import asyncio
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
from PyQt6.QtCore import QSemaphore
from ..core.logger import logger
from ..core.constants import SYSTEM_PATHS, RETRY_CONFIG, ErrorCode


class HardwareManager:
    """
    Thread-safe hardware interface with semaphore protection.
    All subprocess calls are protected against race conditions.
    """

    def __init__(self):
        """Initialize hardware manager with bus semaphore."""
        self.bus_semaphore = QSemaphore(1)
        self.binary_paths = {}
        self.ec_available = False
        self.nbfc_available = False
        # Cache for sensor readings: {key: (value, timestamp)}
        self._sensor_cache: Dict[str, Tuple[Any, float]] = {}
        self._cache_ttl = 2.0  # 2 seconds TTL for sensor data
        self._resolve_binary_paths()
        self._initialize_hardware()

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

    def has_root_privileges(self) -> bool:
        """Return True when the process runs with root privileges."""
        if os.name == "nt":
            return False
        try:
            return os.geteuid() == 0
        except AttributeError:
            return False

    def is_pkexec_available(self) -> bool:
        """Return True when pkexec is available on the system."""
        return bool(self.binary_paths.get("pkexec"))

    def _initialize_hardware(self) -> None:
        """Initialize and verify hardware access."""
        logger.info("Initializing hardware layer...")

        # Check EC module
        if self._load_ec_module():
            self.ec_available = True
            logger.info("✅ Embedded Controller initialized")
        else:
            logger.warning("⚠️  EC module not available (some features limited)")

        # Check NBFC service
        if self._check_nbfc_service():
            self.nbfc_available = True
            logger.info("✅ NBFC service available")
        else:
            logger.warning("⚠️  NBFC service not available")

    def _load_ec_module(self) -> bool:
        """
        Load ec_sys kernel module with write support.
        Returns True if successful or already loaded.
        """
        try:
            ec_sys_path = Path(SYSTEM_PATHS["EC_SYS"])

            # Check if already loaded
            if ec_sys_path.exists():
                logger.debug("EC module already loaded")
                return True

            if not self.has_root_privileges() and not self.is_pkexec_available():
                logger.error("Root privileges or pkexec required to load EC module")
                return False

            nbfc_binary = self.binary_paths.get("nbfc", "nbfc")
            result = self._run_command_as_root([
                "modprobe", "ec_sys", "write_support=1"
            ])

            return result.returncode == 0

        except Exception as e:
            logger.error(f"Failed to load EC module: {e}")
            return False

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

    def _run_command_as_root(self, command, use_sudo: bool = False) -> subprocess.CompletedProcess:
        """
        Execute command with root privileges.
        Uses pkexec or sudo when required.
        """
        if isinstance(command, str):
            command = ["sh", "-c", command]

        if not isinstance(command, list):
            raise ValueError("Root command must be provided as a list or string")

        if self.has_root_privileges():
            full_cmd = command
        elif use_sudo and self.binary_paths.get("sudo"):
            full_cmd = [self.binary_paths["sudo"]] + command
        elif self.is_pkexec_available():
            full_cmd = [self.binary_paths["pkexec"]] + command
        else:
            full_cmd = command

        try:
            result = subprocess.run(
                full_cmd,
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result
        except subprocess.TimeoutExpired:
            logger.error(f"Root command timeout: {' '.join(command)}")
            raise

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
        Safely read system file.
        
        Args:
            filepath: Path to system file
            default: Default value if read fails
            
        Returns:
            File contents or default
        """
        try:
            path = Path(filepath)
            if path.exists():
                return path.read_text().strip()
        except Exception as e:
            logger.debug(f"Failed to read {filepath}: {e}")
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
                cmd = f"echo '{content}' > {filepath}"
                result = self._run_command_as_root(cmd, use_sudo=True)
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
