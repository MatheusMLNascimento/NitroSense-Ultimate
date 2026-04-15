"""
Automatic Dependency Installer

Manages automatic installation of missing system and Python dependencies.
Features:
- Passwordless sudo detection
- Package availability checking
- Retry logic with exponential backoff
- Detailed error reporting
- Logging for all operations

SECURITY NOTE:
Only installs with explicit user consent. Never auto-installs without confirmation.
Logs all installation attempts for audit purposes.
"""

import subprocess
import sys
import time
from typing import List, Dict, Tuple, Optional
from pathlib import Path

from ..core.logger import logger
from ..core.error_codes import ErrorCode


class DependencyInstaller:
    """
    Manages automatic installation of missing system and Python dependencies.
    
    Features:
        - Detects passwordless sudo availability
        - Checks for installed packages before attempting installation
        - Retry logic with exponential backoff
        - Detailed error logging
        - Timeout protection
    
    Attributes:
        has_sudo: Whether passwordless sudo is available
        has_pip: Whether pip is available
        
    Examples:
        >>> installer = DependencyInstaller()
        >>> if installer.can_install_automatically():
        ...     missing_apt, missing_pip = installer.check_missing_dependencies()
        ...     installer.install_apt_packages(missing_apt["tools"])
    """

    # System dependencies that can be auto-installed
    APT_PACKAGES = {
        "nbfc": "nbfc",
        "nvidia-smi": "nvidia-driver-535",
        "sensors": "lm-sensors",
        "pkexec": "policykit-1",  # Usually pre-installed
    }

    # Python packages that can be auto-installed
    PIP_PACKAGES = {
        "matplotlib": "matplotlib",
        "numpy": "numpy",
        "psutil": "psutil",
        "PyQt6": "PyQt6",
        "pynput": "pynput",  # For hotkeys
    }

    # Retry configuration
    MAX_RETRIES = 2
    RETRY_DELAY = 2.0  # seconds, increases exponentially

    def __init__(self) -> None:
        """Initialize installer and check system capabilities."""
        logger.info("Initializing DependencyInstaller...")
        self.has_sudo = self._check_sudo_access()
        self.has_pip = self._check_pip_available()
        
        if self.has_sudo:
            logger.info("✓ Passwordless sudo available")
        else:
            logger.warning("✗ Passwordless sudo NOT available")
            
        if self.has_pip:
            logger.info("✓ pip available")
        else:
            logger.warning("✗ pip NOT available")

    def _check_sudo_access(self) -> bool:
        """
        Check if we can run sudo commands without password prompt.
        
        Returns:
            True if passwordless sudo is available, False otherwise
            
        Implementation:
            Runs `sudo -n true` which succeeds only if passwordless sudo is configured.
        """
        try:
            result = subprocess.run(
                ["sudo", "-n", "true"],
                capture_output=True,
                timeout=5,
                text=True
            )
            success = result.returncode == 0
            logger.debug(f"sudo check: {'available' if success else 'unavailable'}")
            return success
        except subprocess.TimeoutExpired as e:
            logger.warning(f"sudo check timed out: {e}")
            return False
        except (OSError, subprocess.SubprocessError) as e:
            logger.warning(f"sudo check failed: {e}")
            return False

    def _check_pip_available(self) -> bool:
        """
        Check if pip is available and working.
        
        Returns:
            True if pip can be executed, False otherwise
        """
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "--version"],
                capture_output=True,
                timeout=5,
                text=True
            )
            success = result.returncode == 0
            if success:
                logger.debug(f"pip version: {result.stdout.strip()}")
            return success
        except subprocess.TimeoutExpired as e:
            logger.warning(f"pip check timed out: {e}")
            return False
        except (OSError, subprocess.SubprocessError) as e:
            logger.warning(f"pip check failed: {e}")
            return False

    def check_missing_dependencies(
        self,
    ) -> Tuple[Dict[str, List[str]], Dict[str, List[str]]]:
        """
        Check for missing system and Python dependencies.
        
        Returns:
            Tuple of (missing_apt, missing_pip) dictionaries where:
            - missing_apt: {tool_name: [apt_package_name]}
            - missing_pip: {module_name: [pip_package_name]}
            
        Examples:
            >>> missing_apt, missing_pip = installer.check_missing_dependencies()
            >>> if missing_apt:
            ...     print(f"Missing system tools: {list(missing_apt.keys())}")
        """
        logger.info("Checking for missing dependencies...")
        missing_apt = {}
        missing_pip = {}

        # Check system tools
        logger.debug(f"Checking {len(self.APT_PACKAGES)} system tools...")
        for tool, package in self.APT_PACKAGES.items():
            available = self._is_tool_available(tool)
            if not available:
                if tool not in missing_apt:
                    missing_apt[tool] = []
                missing_apt[tool].append(package)
                logger.debug(f"  ✗ {tool} missing (APT: {package})")
            else:
                logger.debug(f"  ✓ {tool} available")

        # Check Python packages
        logger.debug(f"Checking {len(self.PIP_PACKAGES)} Python packages...")
        for module_name, pip_name in self.PIP_PACKAGES.items():
            available = self._is_python_package_available(module_name)
            if not available:
                if module_name not in missing_pip:
                    missing_pip[module_name] = []
                missing_pip[module_name].append(pip_name)
                logger.debug(f"  ✗ {module_name} missing (pip: {pip_name})")
            else:
                logger.debug(f"  ✓ {module_name} available")

        if missing_apt or missing_pip:
            logger.warning(
                f"Missing dependencies found: "
                f"{len(missing_apt)} APT packages, "
                f"{len(missing_pip)} Python packages"
            )
        else:
            logger.info("✓ All dependencies available")

        return missing_apt, missing_pip

    def _is_tool_available(self, tool: str) -> bool:
        """
        Check if a system tool is available in PATH.
        
        Args:
            tool: Tool name (e.g., "nvidia-smi")
            
        Returns:
            True if tool is in PATH, False otherwise
        """
        try:
            result = subprocess.run(
                ["which", tool],
                capture_output=True,
                timeout=3,
                text=True
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, OSError, subprocess.SubprocessError) as e:
            logger.debug(f"Tool check '{tool}' failed: {e}")
            return False

    def _is_python_package_available(self, package: str) -> bool:
        """
        Check if a Python package is importable.
        
        Args:
            package: Package name (e.g., "numpy")
            
        Returns:
            True if package can be imported, False otherwise
        """
        try:
            __import__(package)
            return True
        except ImportError:
            return False
        except Exception as e:
            logger.debug(f"Package import check '{package}' failed: {e}")
            return False

    def install_apt_packages(
        self, packages: List[str], retry: int = 0
    ) -> Tuple[bool, str]:
        """
        Install APT packages with sudo (with retry logic).
        
        Args:
            packages: List of package names to install
            retry: Internal retry counter (0-MAX_RETRIES)
            
        Returns:
            Tuple of (success: bool, message: str)
            
        Features:
            - Exponential backoff retry on transient failures
            - APT cache update before install
            - Detailed error reporting
            - Timeout protection (5 min)
            
        Examples:
            >>> success, msg = installer.install_apt_packages(["nbfc", "lm-sensors"])
            >>> if success:
            ...     print("Installation successful")
        """
        if not self.has_sudo:
            msg = (
                "Sudo access not available (passwordless sudo required). "
                "Setup: sudo visudo and add 'ALL=(ALL) NOPASSWD: /usr/bin/apt-get'"
            )
            logger.error(msg)
            return False, msg

        if not packages:
            logger.info("No APT packages to install")
            return True, "No packages to install"

        try:
            # Update package list first
            logger.info("Updating APT package list...")
            update_result = subprocess.run(
                ["sudo", "apt-get", "update", "-qq"],
                capture_output=True,
                timeout=60,
                text=True
            )

            if update_result.returncode != 0:
                logger.warning(
                    f"APT update returned code {update_result.returncode}: "
                    f"{update_result.stderr[:200]}"
                )

            # Install packages
            logger.info(f"Installing APT packages: {', '.join(packages)}")
            install_result = subprocess.run(
                ["sudo", "apt-get", "install", "-y", "-qq"] + packages,
                capture_output=True,
                timeout=300,  # 5 minutes
                text=True
            )

            if install_result.returncode == 0:
                msg = f"Successfully installed APT packages: {', '.join(packages)}"
                logger.info(msg)
                return True, msg
            else:
                error_msg = install_result.stderr or "Unknown error"
                
                # Check if it's a transient error (e.g., lock, network)
                is_transient = any(
                    text in error_msg.lower()
                    for text in ["lock", "connection", "temporary", "unavailable"]
                )
                
                if is_transient and retry < self.MAX_RETRIES:
                    delay = self.RETRY_DELAY * (2 ** retry)  # Exponential backoff
                    logger.warning(
                        f"Transient error (attempt {retry + 1}/{self.MAX_RETRIES}), "
                        f"retrying in {delay:.1f}s: {error_msg[:100]}"
                    )
                    time.sleep(delay)
                    return self.install_apt_packages(packages, retry=retry + 1)
                
                msg = f"Failed to install APT packages: {error_msg[:200]}"
                logger.error(msg)
                return False, msg

        except subprocess.TimeoutExpired as e:
            msg = f"APT installation timed out after {e.timeout}s"
            logger.error(msg)
            return False, msg
        except Exception as e:
            msg = f"APT installation error: {e}"
            logger.error(msg)
            return False, msg

    def install_pip_packages(
        self, packages: List[str], retry: int = 0
    ) -> Tuple[bool, str]:
        """
        Install Python packages with pip (with retry logic).
        
        Args:
            packages: List of package names to install
            retry: Internal retry counter (0-MAX_RETRIES)
            
        Returns:
            Tuple of (success: bool, message: str)
            
        Features:
            - Exponential backoff retry on transient failures
            - Uses current Python interpreter
            - Quiet mode to reduce log spam
            - Timeout protection (5 min)
            
        Examples:
            >>> success, msg = installer.install_pip_packages(["numpy", "matplotlib"])
        """
        if not self.has_pip:
            msg = (
                "pip not available. "
                "Install Python pip: sudo apt-get install python3-pip"
            )
            logger.error(msg)
            return False, msg

        if not packages:
            logger.info("No pip packages to install")
            return True, "No packages to install"

        try:
            logger.info(f"Installing pip packages: {', '.join(packages)}")
            install_result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "--quiet", "--upgrade"] + packages,
                capture_output=True,
                timeout=300,  # 5 minutes
                text=True
            )

            if install_result.returncode == 0:
                msg = f"Successfully installed pip packages: {', '.join(packages)}"
                logger.info(msg)
                return True, msg
            else:
                error_msg = install_result.stderr or "Unknown error"
                
                # Check if it's a transient error (e.g., network, timeout)
                is_transient = any(
                    text in error_msg.lower()
                    for text in ["timeout", "connection", "temporary", "unavailable", "ssl"]
                )
                
                if is_transient and retry < self.MAX_RETRIES:
                    delay = self.RETRY_DELAY * (2 ** retry)
                    logger.warning(
                        f"Transient error (attempt {retry + 1}/{self.MAX_RETRIES}), "
                        f"retrying in {delay:.1f}s: {error_msg[:100]}"
                    )
                    time.sleep(delay)
                    return self.install_pip_packages(packages, retry=retry + 1)
                
                msg = f"Failed to install pip packages: {error_msg[:200]}"
                logger.error(msg)
                return False, msg

        except subprocess.TimeoutExpired as e:
            msg = f"pip installation timed out after {e.timeout}s"
            logger.error(msg)
            return False, msg
        except Exception as e:
            msg = f"pip installation error: {e}"
            logger.error(msg)
            return False, msg

    def can_install_automatically(self) -> bool:
        """
        Check if automatic installation is possible.
        
        Requirements:
            - Passwordless sudo available
            - pip available
            
        Returns:
            True if both requirements met, False otherwise
            
        Examples:
            >>> if installer.can_install_automatically():
            ...     installer.install_apt_packages(missing_packages)
        """
        can_install = self.has_sudo and self.has_pip
        logger.debug(
            f"Automatic installation possible: {can_install} "
            f"(sudo={self.has_sudo}, pip={self.has_pip})"
        )
        return can_install

    def get_installation_report(self) -> str:
        """
        Generate a human-readable installation capability report.
        
        Returns:
            Formatted string describing capabilities
            
        Examples:
            >>> print(installer.get_installation_report())
            Installation Capabilities:
              ✓ Passwordless sudo: available
              ✓ pip: available (21.0)
              Status: Ready for automatic installation
        """
        lines = ["Installation Capabilities:"]
        
        if self.has_sudo:
            lines.append("  ✓ Passwordless sudo: available")
        else:
            lines.append("  ✗ Passwordless sudo: NOT available")
        
        if self.has_pip:
            lines.append("  ✓ pip: available")
        else:
            lines.append("  ✗ pip: NOT available")
        
        if self.can_install_automatically():
            lines.append("  Status: Ready for automatic installation")
        else:
            lines.append("  Status: Manual installation required")
        
        return "\n".join(lines)