"""
Automatic Dependency Installer
Handles automatic installation of missing system dependencies with user consent
"""

import subprocess
import sys
from typing import List, Dict, Tuple, Optional
from pathlib import Path

from ..core.logger import logger
from ..core.error_codes import ErrorCode


class DependencyInstaller:
    """
    Manages automatic installation of missing system dependencies.
    Only installs with explicit user consent for security.
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

    def __init__(self):
        self.has_sudo = self._check_sudo_access()
        self.has_pip = self._check_pip_available()

    def _check_sudo_access(self) -> bool:
        """Check if we can run sudo commands without password prompt."""
        try:
            result = subprocess.run(
                ["sudo", "-n", "true"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, subprocess.SubprocessError):
            return False

    def _check_pip_available(self) -> bool:
        """Check if pip is available."""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "--version"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, subprocess.SubprocessError):
            return False

    def check_missing_dependencies(self) -> Tuple[Dict[str, List[str]], Dict[str, List[str]]]:
        """
        Check for missing system and Python dependencies.

        Returns:
            Tuple of (missing_apt, missing_pip) dictionaries
        """
        missing_apt = {}
        missing_pip = {}

        # Check system tools
        for tool, package in self.APT_PACKAGES.items():
            if not self._is_tool_available(tool):
                if tool not in missing_apt:
                    missing_apt[tool] = []
                missing_apt[tool].append(package)

        # Check Python packages
        for package, pip_name in self.PIP_PACKAGES.items():
            if not self._is_python_package_available(package):
                if package not in missing_pip:
                    missing_pip[package] = []
                missing_pip[package].append(pip_name)

        return missing_apt, missing_pip

    def _is_tool_available(self, tool: str) -> bool:
        """Check if a system tool is available."""
        try:
            result = subprocess.run(
                ["which", tool],
                capture_output=True,
                timeout=3
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, subprocess.SubprocessError):
            return False

    def _is_python_package_available(self, package: str) -> bool:
        """Check if a Python package is available."""
        try:
            __import__(package)
            return True
        except ImportError:
            return False

    def install_apt_packages(self, packages: List[str]) -> Tuple[bool, str]:
        """
        Install APT packages with sudo.

        Args:
            packages: List of package names to install

        Returns:
            Tuple of (success, message)
        """
        if not self.has_sudo:
            return False, "Sudo access not available (passwordless sudo required)"

        if not packages:
            return True, "No packages to install"

        try:
            # Update package list first
            logger.info("Updating package list...")
            update_result = subprocess.run(
                ["sudo", "apt-get", "update", "-qq"],
                capture_output=True,
                timeout=60
            )

            if update_result.returncode != 0:
                logger.warning(f"apt-get update failed: {update_result.stderr.decode()}")

            # Install packages
            logger.info(f"Installing packages: {', '.join(packages)}")
            install_result = subprocess.run(
                ["sudo", "apt-get", "install", "-y", "-qq"] + packages,
                capture_output=True,
                timeout=300  # 5 minutes timeout
            )

            if install_result.returncode == 0:
                return True, f"Successfully installed: {', '.join(packages)}"
            else:
                error_msg = install_result.stderr.decode() or "Unknown error"
                return False, f"Failed to install packages: {error_msg}"

        except subprocess.TimeoutExpired:
            return False, "Installation timed out"
        except subprocess.SubprocessError as e:
            return False, f"Installation error: {e}"

    def install_pip_packages(self, packages: List[str]) -> Tuple[bool, str]:
        """
        Install Python packages with pip.

        Args:
            packages: List of package names to install

        Returns:
            Tuple of (success, message)
        """
        if not self.has_pip:
            return False, "pip not available"

        if not packages:
            return True, "No packages to install"

        try:
            logger.info(f"Installing Python packages: {', '.join(packages)}")
            install_result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "--quiet"] + packages,
                capture_output=True,
                timeout=300  # 5 minutes timeout
            )

            if install_result.returncode == 0:
                return True, f"Successfully installed Python packages: {', '.join(packages)}"
            else:
                error_msg = install_result.stderr.decode() or "Unknown error"
                return False, f"Failed to install Python packages: {error_msg}"

        except subprocess.TimeoutExpired:
            return False, "Python package installation timed out"
        except subprocess.SubprocessError as e:
            return False, f"Python package installation error: {e}"

    def can_install_automatically(self) -> bool:
        """
        Check if automatic installation is possible.
        Requires passwordless sudo and pip availability.
        """
        return self.has_sudo and self.has_pip