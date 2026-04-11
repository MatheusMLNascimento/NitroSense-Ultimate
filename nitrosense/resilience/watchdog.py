"""
Hardware Watchdog - Independent Timer
If hardware monitor doesn't ping for 10s, force bus reset
"""

from PyQt6.QtCore import QTimer, QThread, pyqtSignal
from PyQt6.QtWidgets import QMessageBox
import time
from ..core.logger import logger
from ..core.error_codes import ErrorCode


class HardwareWatchdog(QThread):
    """
    Independent watchdog timer.
    Monitors if hardware thread sends heartbeat every 10s.
    If no heartbeat: triggers emergency bus reset.
    """
    
    timeout_detected = pyqtSignal()  # Signal when watchdog times out
    
    def __init__(self, timeout_sec: int = 10):
        super().__init__()
        self.timeout_sec = timeout_sec
        self.last_heartbeat = time.time()
        self.running = False
        self.last_reset_time = 0
        self.reset_cooldown = 60  # Don't reset more than once per minute
        logger.info(f"✅ HardwareWatchdog initialized ({timeout_sec}s timeout)")
    
    def heartbeat(self):
        """Hardware thread calls this to signal 'still alive'."""
        self.last_heartbeat = time.time()
    
    def run(self):
        """Main watchdog loop."""
        logger.info(f"🐕 Watchdog started (monitoring every second)")
        
        while self.running:
            time.sleep(1)
            
            elapsed = time.time() - self.last_heartbeat
            
            if elapsed > self.timeout_sec:
                logger.critical(f"🚨 WATCHDOG TIMEOUT: No heartbeat for {elapsed:.1f}s")
                self.timeout_detected.emit()
                
                # Only attempt emergency bus reset if enough time has passed since last reset
                if time.time() - self.last_reset_time > self.reset_cooldown:
                    self._emergency_bus_reset()
                    self.last_reset_time = time.time()
                else:
                    logger.warning("⏰ Reset cooldown active, skipping emergency reset")
                
                # Reset timer
                self.last_heartbeat = time.time()
    
    def _emergency_bus_reset(self):
        """
        Emergency bus reset procedure.
        1. Kill NBFC
        2. Reload EC module
        3. Restart NBFC
        """
        logger.critical("🔧 Attempting emergency bus reset...")
        
        try:
            import subprocess
            
            # Kill NBFC
            subprocess.run(["sudo", "pkill", "-9", "nbfc"], capture_output=True)
            time.sleep(0.5)
            
            # Reload EC
            subprocess.run(["sudo", "modprobe", "-r", "ec_sys"], capture_output=True)
            time.sleep(0.5)
            subprocess.run(
                ["sudo", "modprobe", "ec_sys", "write_support=1"],
                capture_output=True
            )
            time.sleep(1)
            
            # Restart NBFC
            subprocess.run(["sudo", "systemctl", "restart", "nbfc_service"], capture_output=True)
            
            logger.info("✅ Emergency bus reset completed")
            
        except Exception as e:
            logger.error(f"❌ Bus reset failed: {e}")
    
    def stop(self):
        """Stop the watchdog."""
        self.running = False
        try:
            self.wait(1000)
        except Exception:
            pass

    def is_alive(self) -> bool:
        """Return whether the watchdog is alive and the heartbeat is current."""
        if not self.running:
            return False
        return time.time() - self.last_heartbeat <= self.timeout_sec

    def start(self) -> None:
        """Start the watchdog thread."""
        self.running = True
        super().start()
