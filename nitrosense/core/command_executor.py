"""
Command executor service for NitroSense Ultimate.
Provides a single place for elevated command resolution, root escalation, and binary discovery.
"""

import os
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Iterable, Optional, Sequence

from .logger import logger
from .retry_strategy import RetryStrategy


class CommandExecutor:
    """Helper for executing shell commands safely and consistently."""

    def __init__(self, binary_paths: Optional[Dict[str, str]] = None) -> None:
        self.binary_paths: Dict[str, str] = binary_paths.copy() if binary_paths else {}
        self._resolve_binaries()

    def _resolve_binaries(self) -> None:
        """Resolve helper command paths for the current environment."""
        for tool in ["sudo", "pkexec", "nbfc", "which"]:
            if tool not in self.binary_paths:
                path = shutil.which(tool)
                if path:
                    self.binary_paths[tool] = path
                    logger.debug(f"Resolved {tool}: {path}")

    def has_root_privileges(self) -> bool:
        """Return True when the current process already has root permissions."""
        if os.name == "nt":
            return False
        try:
            return os.geteuid() == 0
        except AttributeError:
            return False

    def is_pkexec_available(self) -> bool:
        """Return True when pkexec is available on the host."""
        return bool(self.binary_paths.get("pkexec"))

    def _normalize_command(self, command: Sequence[str] | str) -> list[str]:
        if isinstance(command, str):
            return shlex.split(command)
        return list(command)

    def execute_root_command(
        self,
        command: Sequence[str] | str,
        use_sudo: bool = False,
        timeout: int = 10,
    ) -> subprocess.CompletedProcess:
        """Execute a command with root escalation if needed."""
        command_list = self._normalize_command(command)

        if self.has_root_privileges():
            full_command = command_list
        elif use_sudo and self.binary_paths.get("sudo"):
            full_command = [self.binary_paths["sudo"]] + command_list
        elif self.is_pkexec_available():
            full_command = [self.binary_paths["pkexec"]] + command_list
        else:
            full_command = command_list

        try:
            result = subprocess.run(
                full_command,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return result
        except subprocess.TimeoutExpired:
            logger.error(f"Root command timeout: {' '.join(command_list)}")
            raise
        except Exception as exc:
            logger.error(f"Root command failed: {exc}")
            raise

    def execute_protected_command(
        self,
        command: Sequence[str] | str,
        timeout: int = 10,
        retry: bool = True,
    ) -> subprocess.CompletedProcess:
        """
        Execute a command with optional retry/backoff semantics.
        
        Uses RetryStrategy for unified retry handling across the application.
        """
        cmd = self._normalize_command(command)
        retry_strategy = RetryStrategy() if retry else RetryStrategy(max_retries=1)
        
        def _execute_command() -> subprocess.CompletedProcess:
            """Execute subprocess with given timeout."""
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )
                
                # Treat non-zero return code as failure for retry purposes
                if result.returncode != 0:
                    raise RuntimeError(
                        f"Command failed with code {result.returncode}: {result.stderr}"
                    )
                
                return result
            except subprocess.TimeoutExpired:
                logger.error(f"Command timeout: {' '.join(cmd)}")
                raise
        
        try:
            return retry_strategy.execute_with_retry(_execute_command)
        except Exception as e:
            logger.error(f"Protected command failed after retries: {e}")
            raise
