"""
Single Instance Lock Manager for NitroSense Ultimate.

Prevents multiple instances from accessing hardware simultaneously,
which would corrupt the EC/ACPI bus communication.

Uses both QSharedMemory (preferred) and filesystem lock as fallback.
"""

import os
import sys
import time
from pathlib import Path
from typing import Optional
from PyQt6.QtCore import QSharedMemory, QSystemSemaphore, QUuid
from ..core.logger import logger


class SingleInstanceLock:
    """
    Thread-safe single instance enforcer.
    
    Uses QSharedMemory for efficient inter-process communication.
    Falls back to filesystem lock for robustness on missing IPC support.
    """
    
    LOCK_KEY = "NitroSenseUltimate_SingleInstance_v3"
    LOCK_TIMEOUT = 30  # seconds
    
    def __init__(self):
        """Initialize the single instance lock."""
        self._shared_memory: Optional[QSharedMemory] = None
        self._lock_file: Optional[Path] = None
        self._lock_acquired = False
        self._use_filesystem_lock = False
        
    def acquire(self) -> tuple[bool, str]:
        """
        Attempt to acquire the single instance lock.
        
        Returns:
            (success: bool, message: str)
                - True, "Acquired": Lock acquired successfully
                - False, "Already running": Another instance is running
                - False, "Timeout": Failed to acquire within timeout
        """
        try:
            # Try QSharedMemory first (preferred)
            if self._try_shared_memory_lock():
                logger.info("✓ Single instance lock acquired (QSharedMemory)")
                self._lock_acquired = True
                return True, "Acquired"
            
            # Fall back to filesystem lock
            logger.debug("QSharedMemory unavailable, falling back to filesystem lock")
            self._use_filesystem_lock = True
            
            if self._try_filesystem_lock():
                logger.info("✓ Single instance lock acquired (filesystem)")
                self._lock_acquired = True
                return True, "Acquired"
            
            # Another instance is running
            logger.warning("Another instance of NitroSense is already running")
            return False, "Already running"
            
        except Exception as e:
            logger.error(f"Single instance lock error: {e}")
            return False, f"Lock error: {e}"
    
    def _try_shared_memory_lock(self) -> bool:
        """
        Try to acquire lock using QSharedMemory.
        
        Returns:
            True if acquired, False if another instance owns it
        """
        try:
            self._shared_memory = QSharedMemory(self.LOCK_KEY)
            
            # Try to attach to existing memory (another instance)
            if self._shared_memory.attach():
                return False  # Another instance owns this
            
            # Try to create new shared memory block
            if not self._shared_memory.create(1):
                # Failed to create, might be owned by another instance
                return False
            
            # Successfully acquired
            return True
            
        except Exception as e:
            logger.debug(f"QSharedMemory unavailable: {e}")
            self._shared_memory = None
            return False
    
    def _try_filesystem_lock(self) -> bool:
        """
        Try to acquire lock using filesystem lock file.
        
        Returns:
            True if acquired, False if another instance owns it
        """
        try:
            # Use ~/.config/nitrosense for lock file
            lock_dir = Path.home() / ".config" / "nitrosense"
            lock_dir.mkdir(parents=True, exist_ok=True)
            self._lock_file = lock_dir / "nitrosense.lock"
            
            # Check if lock file exists and is still valid
            if self._lock_file.exists():
                try:
                    pid = int(self._lock_file.read_text().strip())
                    
                    # Check if process with that PID is still running
                    if self._process_exists(pid):
                        # Another instance is running
                        return False
                    else:
                        # Stale lock file, remove it
                        logger.debug(f"Removing stale lock file (PID {pid} no longer running)")
                        self._lock_file.unlink(missing_ok=True)
                except Exception as e:
                    logger.debug(f"Error reading lock file: {e}")
                    # Try to remove corrupted lock file
                    self._lock_file.unlink(missing_ok=True)
            
            # Create new lock file with current PID
            self._lock_file.write_text(str(os.getpid()))
            logger.debug(f"Created lock file: {self._lock_file}")
            return True
            
        except Exception as e:
            logger.error(f"Filesystem lock error: {e}")
            return False
    
    def _process_exists(self, pid: int) -> bool:
        """Check if a process with given PID exists."""
        try:
            # Send signal 0 to check if process exists (doesn't kill)
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False
    
    def release(self) -> None:
        """Release the single instance lock."""
        try:
            if self._use_filesystem_lock and self._lock_file:
                self._lock_file.unlink(missing_ok=True)
                logger.debug(f"Filesystem lock released: {self._lock_file}")
            
            if self._shared_memory:
                self._shared_memory.detach()
                logger.debug("QSharedMemory lock released")
            
            self._lock_acquired = False
        except Exception as e:
            logger.error(f"Error releasing lock: {e}")
    
    def is_acquired(self) -> bool:
        """Check if the lock is currently held."""
        return self._lock_acquired
    
    def __enter__(self):
        """Context manager entry."""
        self.acquire()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.release()
