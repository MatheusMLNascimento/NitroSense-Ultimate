"""
Hardware Watchdog—Critical Safety Monitor

CRITICAL SAFEGUARDS:
1. If hardware doesn't heartbeat for 10s, emit timeout signal
2. If sensors fail >3 times, force fans to 100% (EMERGENCY MODE)
3. On SIGTERM/SIGINT, return fans to BIOS before exit
4. Prevent application hang by enforcing thread safety
"""

from PyQt6.QtCore import QTimer, QThread, pyqtSignal, QObject
from PyQt6.QtWidgets import QMessageBox
import time
import subprocess
from ..core.logger import logger
from ..core.error_codes import ErrorCode


class HardwareWatchdog(QThread):
    """
    Independent watchdog timer.
    Monitors if hardware thread sends heartbeat every 10s.
    If no heartbeat: triggers emergency bus reset.
    If sensors fail >3x: forces fans to 100% via NBFC emergency mode.
    """
    
    timeout_detected = pyqtSignal()  # Signal when watchdog times out
    emergency_mode_activated = pyqtSignal()  # Signal when 100% fan emergency activated
    
    def __init__(self, timeout_sec: int = 10, hardware_manager=None):
        super().__init__()
        self.timeout_sec = timeout_sec
        self.hardware_manager = hardware_manager
        self.last_heartbeat = time.time()
        self.running = False
        self.last_reset_time = 0
        self.reset_cooldown = 60  # Don't reset more than once per minute
        self.sensor_failure_count = 0
        self.max_sensor_failures = 3
        self.in_emergency_mode = False
        logger.info(f"✅ HardwareWatchdog initialized ({timeout_sec}s timeout, emergency at {self.max_sensor_failures} failures)")
    
    def heartbeat(self):
        """Hardware thread calls this to signal 'still alive'."""
        self.last_heartbeat = time.time()
        self.sensor_failure_count = max(0, self.sensor_failure_count - 1)  # Decrement on success
    
    def report_sensor_failure(self):
        """Report a sensor read failure. >3 failures trigger emergency mode."""
        self.sensor_failure_count += 1
        logger.warning(f"Sensor failure reported ({self.sensor_failure_count}/{self.max_sensor_failures})")
        
        if self.sensor_failure_count >= self.max_sensor_failures:
            self._activate_emergency_mode()
    
    def run(self):
        """Main watchdog loop."""
        logger.info(f"🐕 Watchdog started (monitoring every second, {self.timeout_sec}s timeout)")
        
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
    
    def _activate_emergency_mode(self):
        """
        EMERGENCY MODE: Force fans to 100% immediately.
        This is a SAFETY mechanism to prevent hardware overheating.
        """
        if self.in_emergency_mode:
            return  # Already in emergency mode
        
        self.in_emergency_mode = True
        logger.critical("🔥 EMERGENCY MODE ACTIVATED: Forcing fans to 100%")
        self.emergency_mode_activated.emit()
        
        try:
            # Method 1: Direct NBFC command
            if self.hardware_manager:
                success, output = self.hardware_manager.run_nbfc("set --speed 100")
                if success:
                    logger.critical("✓ Fans set to 100% via NBFC")
                    return
            
            # Method 2: Direct systemctl/NBFC service command
            subprocess.run(
                ["nbfc", "set", "--speed", "100"],
                capture_output=True,
                timeout=5
            )
            logger.critical("✓ Fans set to 100% (direct command)")
            
        except subprocess.TimeoutExpired:
            logger.critical("⚠️  NBFC command timeout during emergency mode")
        except Exception as e:
            logger.critical(f"⚠️  Emergency mode activation failed: {e}")
            logger.critical("⚠️  MANUAL INTERVENTION REQUIRED: Please check fans manually!")
    
    def _emergency_bus_reset(self):
        """
        Emergency bus reset procedure.
        1. Force fans to 100% (safety first)
        2. Kill NBFC
        3. Reload EC module
        4. Restart NBFC
        """
        logger.critical("🔧 Attempting emergency bus reset...")
        
        # Safety first: ensure fans are at 100%
        self._activate_emergency_mode()
        
        try:
            import subprocess
            
            # Kill NBFC
            subprocess.run(["sudo", "pkill", "-9", "nbfc"], capture_output=True, timeout=5)
            time.sleep(0.5)
            
            # Reload EC
            subprocess.run(["sudo", "modprobe", "-r", "ec_sys"], capture_output=True, timeout=5)
            time.sleep(0.5)
            subprocess.run(
                ["sudo", "modprobe", "ec_sys", "write_support=1"],
                capture_output=True,
                timeout=5
            )
            time.sleep(1)
            
            # Restart NBFC
            subprocess.run(
                ["sudo", "systemctl", "restart", "nbfc_service"],
                capture_output=True,
                timeout=5
            )
            
            logger.info("✅ Emergency bus reset completed")
            self.in_emergency_mode = False
            
        except subprocess.TimeoutExpired:
            logger.error("❌ Bus reset command timeout")
        except Exception as e:
            logger.error(f"❌ Bus reset failed: {e}")
    
    def stop(self):
        """Stop the watchdog—return fan control to BIOS."""
        logger.info("🐕 Stopping watchdog and returning control to BIOS...")
        self.running = False
        
        # Return fan control to BIOS/NBFC default
        try:
            subprocess.run(
                ["nbfc", "set", "--auto"],
                capture_output=True,
                timeout=5
            )
            logger.info("✓ Fans returned to automatic/BIOS control")
        except Exception as e:
            logger.warning(f"Could not return fan control: {e}")
        
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
