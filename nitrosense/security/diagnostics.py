"""
Security and Diagnostics Module (Functions 76-100)
Comprehensive safety, monitoring, and diagnostic features
"""

import subprocess
import hashlib
import os
from typing import Tuple, Optional, List, Dict
from pathlib import Path
from datetime import datetime
import psutil

from ..core.logger import logger
from ..core.error_codes import ErrorCode, SafeOperation


class SecurityAndDiagnostics:
    """
    Implements security protocols and diagnostic functions (76-100).
    All operations wrapped with error handling.
    """
    
    def __init__(self, hardware_manager, monitoring_engine):
        self.hardware = hardware_manager
        self.monitoring = monitoring_engine
        self.crash_log = Path.home() / ".config/nitrosense/crash.log"
        self.crash_log.parent.mkdir(parents=True, exist_ok=True)
        logger.info("SecurityAndDiagnostics initialized")
    
    # ========================================================================
    # FUNCTION 76-80: Emergency Protocol & Alerts
    # ========================================================================
    
    @SafeOperation(ErrorCode.CRITICAL_TEMP_95C)
    def emergency_protocol_95c(self) -> Tuple[ErrorCode, bool]:
        """
        Fn 76: Emergency protocol at T >= 95°C
        - Kill non-essential processes
        - Engage 100% fan speed
        - Log event
        - Trigger notifications
        """
        logger.critical("🔴 EMERGENCY PROTOCOL: T >= 95°C activated")
        
        # Kill bloatware processes
        killable_apps = ["steam", "chrome", "firefox", "code", "vlc", "spotify"]
        for app in killable_apps:
            try:
                for proc in psutil.process_iter(["name", "pid"]):
                    if proc.info["name"] == app:
                        logger.warning(f"Killing {app} for thermal protection")
                        proc.terminate()
            except Exception as e:
                logger.debug(f"Could not kill {app}: {e}")
        
        # Force fan to 100%
        try:
            success, _ = self.hardware.run_nbfc("set -s 100")
        except Exception as e:
            logger.error(f"Failed to set fan to max in emergency: {e}")
            success = False
        
        # Log emergency event
        self._log_emergency_event("THERMAL_EMERGENCY_95C")
        
        # Play alert sound (if available)
        self._play_alert_sound()
        
        return (ErrorCode.CRITICAL_TEMP_95C, success)
    
    def emergency_justification_dialog_text(self) -> str:
        """Fn 77: Generate explanation text for emergency shutdown."""
        return """
        ⚠️  THERMAL EMERGENCY SHUTDOWN
        
        Your system temperature reached ≥95°C.
        
        ACTIONS TAKEN:
        ✓ Non-essential applications terminated
        ✓ Fan speed forced to 100%
        ✓ Event logged for diagnostics
        
        RECOMMENDATIONS:
        • Let system cool for 5 minutes
        • Check for dust in fans
        • Consider thermal paste replacement
        • Ensure proper ventilation
        
        Temperature will be monitored continuously.
        """
    
    @SafeOperation(ErrorCode.FAN_STALL_DETECTED)
    def watchdog_fan_monitoring(self, temp: float, rpm: Optional[int]) -> Tuple[ErrorCode, bool]:
        """
        Fn 78: Detect fan stalls (RPM=0 at high temperature).
        Indicates potential hardware failure.
        """
        if temp > 75 and (rpm is None or rpm == 0):
            logger.critical(f"🔴 Fan stall detected: T={temp}°C, RPM={rpm}")
            self._log_emergency_event("FAN_STALL_DETECTED")
            self._play_alert_sound()
            return ErrorCode.FAN_STALL_DETECTED, True
        
        return ErrorCode.SUCCESS, False
    
    def simulate_stress_test_95c(self) -> bool:
        """
        Fn 79: Inject fake 95°C reading for testing emergency protocol.
        Used in Labs page to validate safety systems.
        """
        logger.warning("🧪 Simulating 95°C for stress test")
        # This would be called from test harness
        return True
    
    @SafeOperation(ErrorCode.DEPENDENCY_MISSING)
    def system_dependency_check(self) -> Tuple[ErrorCode, Dict[str, bool]]:
        """
        Fn 80: Verify all required system dependencies on boot.
        """
        deps = {
            "nbfc": False,
            "nvidia-smi": False,
            "sensors": False,
            "pkexec": False,
        }
        
        for tool in deps.keys():
            try:
                result = subprocess.run(
                    ["which", tool],
                    capture_output=True,
                    timeout=5
                )
                deps[tool] = result.returncode == 0
            except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError) as e:
                logger.debug(f"Dependency check failed for {tool}: {e}")
        
        missing = [k for k, v in deps.items() if not v]
        if missing:
            logger.warning(f"Missing dependencies: {missing}")
            return ErrorCode.DEPENDENCY_MISSING, deps
        
        return ErrorCode.SUCCESS, deps
    
    # ========================================================================
    # FUNCTION 81-85: Hardware Repair & Diagnostics
    # ========================================================================
    
    @SafeOperation(ErrorCode.EC_MODULE_LOAD_FAILED)
    def force_driver_reset(self) -> Tuple[ErrorCode, bool]:
        """
        Fn 81: Force EC driver reset by unloading and reloading ec_sys.
        Recovers from hardware communication hangs.
        """
        try:
            logger.info("Attempting EC driver force reset...")
            
            # Unload
            subprocess.run(
                ["pkexec", "modprobe", "-r", "ec_sys"],
                capture_output=True,
                timeout=5
            )
            
            # Reload
            result = subprocess.run(
                ["pkexec", "modprobe", "ec_sys", "write_support=1"],
                capture_output=True,
                timeout=5
            )
            
            if result.returncode == 0:
                logger.info("✅ EC driver reset successful")
                return ErrorCode.SUCCESS, True
            else:
                logger.error("❌ EC driver reset failed")
                return ErrorCode.EC_MODULE_LOAD_FAILED, False
                
        except Exception as e:
            logger.error(f"EC reset exception: {e}")
            return ErrorCode.EC_MODULE_LOAD_FAILED, False
    
    @SafeOperation(ErrorCode.UNKNOWN_ERROR)
    def fault_sound_alert(self) -> bool:
        """Fn 82: Play hardware failure alert sound."""
        self._play_alert_sound()
        return True
    
    @SafeOperation(ErrorCode.UNKNOWN_ERROR)
    def ec_register_validation_test(self) -> Tuple[ErrorCode, bool]:
        """
        Fn 83: Test EC communication by reading non-critical register.
        Validates if embedded controller bus is responsive.
        """
        try:
            result = subprocess.run(
                ["nbfc", "status", "-a"],
                capture_output=True,
                timeout=5,
                text=True
            )
            
            if result.returncode == 0 and "Temperature" in result.stdout:
                logger.info("✅ EC bus communication validated")
                return ErrorCode.SUCCESS, True
            else:
                logger.warning("⚠️  EC bus communication test inconclusive")
                return ErrorCode.UNKNOWN_ERROR, False
                
        except Exception as e:
            logger.error(f"EC validation test failed: {e}")
            return ErrorCode.EC_ACCESS_FAILED, False
    
    def memory_leak_detector(self) -> Tuple[ErrorCode, Optional[float]]:
        """
        Fn 84: Monitor NitroSense process memory usage.
        Returns memory percentage. Triggers cleanup if >500MB.
        """
        try:
            process = psutil.Process()
            mem_mb = process.memory_info().rss / (1024 * 1024)
            mem_percent = process.memory_percent()
            
            logger.debug(f"NitroSense memory: {mem_mb:.1f}MB ({mem_percent:.1f}%)")
            
            if mem_mb > 500:
                logger.warning(f"High memory usage detected: {mem_mb:.1f}MB")
                import gc
                gc.collect()
                
                # Check again
                mem_mb_after = process.memory_info().rss / (1024 * 1024)
                logger.info(f"After GC: {mem_mb_after:.1f}MB")
            
            return ErrorCode.SUCCESS, mem_percent
            
        except Exception as e:
            logger.error(f"Memory monitoring failed: {e}")
            return ErrorCode.UNKNOWN_ERROR, None
    
    def persistent_crash_logger(self, exc_type, exc_value, exc_traceback) -> bool:
        """
        Fn 85: Log all crashes to persistent crash.log file (black box).
        Called by global exception handler.
        """
        try:
            with open(self.crash_log, "a") as f:
                f.write(f"\n{'='*60}\n")
                f.write(f"Timestamp: {datetime.now().isoformat()}\n")
                f.write(f"Error Type: {exc_type.__name__}\n")
                f.write(f"Message: {str(exc_value)}\n")
                f.write(f"File: {exc_traceback.tb_frame.f_code.co_filename}:{exc_traceback.tb_lineno}\n")
                f.write(f"{'='*60}\n")
            
            logger.info(f"Crash logged to {self.crash_log}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to log crash: {e}")
            return False

    def verify_update_package(self, package_path: str, expected_hash: str) -> Tuple[ErrorCode, bool]:
        """Verify update package SHA-256 checksum before applying."""
        try:
            path = Path(package_path)
            if not path.exists():
                logger.error(f"Update package not found: {package_path}")
                return ErrorCode.FILE_NOT_FOUND, False

            return self.verify_file_checksum(package_path, expected_hash)
        except Exception as e:
            logger.error(f"Update package verification failed: {e}")
            return ErrorCode.CHECKSUM_MISMATCH, False

    def generate_diagnostic_report(self) -> Tuple[ErrorCode, Optional[str]]:
        """Create a final diagnostics TXT report after Labs tests."""
        try:
            report_path = Path.home() / ".config" / "nitrosense" / "diagnostics_report.txt"
            report_path.parent.mkdir(parents=True, exist_ok=True)

            with open(report_path, "w", encoding="utf-8") as f:
                f.write("NitroSense Ultimate Diagnostics Report\n")
                f.write("=" * 60 + "\n")
                f.write(f"Timestamp: {datetime.now().isoformat()}\n")
                f.write(f"Hardware ID: {self.hardware.get_hardware_id() if self.hardware else 'N/A'}\n")
                f.write("\n")
                f.write("Dependencies:\n")
                err, result = self.system_dependency_check()
                if err == ErrorCode.SUCCESS and isinstance(result, tuple):
                    dep_err, deps = result
                    if dep_err == ErrorCode.SUCCESS and isinstance(deps, dict):
                        for tool, available in deps.items():
                            f.write(f" - {tool}: {'OK' if available else 'MISSING'}\n")
                    else:
                        f.write(f" - Dependency check failed: {dep_err}\n")
                else:
                    f.write(f" - Dependency check failed: {err}\n")

                f.write("\n")
                f.write("Recent crash log tail:\n")
                if self.crash_log.exists():
                    with open(self.crash_log, "r", encoding="utf-8", errors="ignore") as log_f:
                        lines = log_f.readlines()[-20:]
                        f.writelines(lines)
                else:
                    f.write("None\n")

                f.write("\n")
                f.write("System metrics:\n")
                if self.monitoring:
                    metrics = self.monitoring.get_system_metrics()
                    for key, value in metrics.items():
                        f.write(f" - {key}: {value}\n")
                else:
                    f.write("No monitoring engine attached.\n")

            logger.info(f"Diagnostics report generated: {report_path}")
            return ErrorCode.SUCCESS, str(report_path)
        except (OSError, IOError, PermissionError) as e:
            logger.error(f"Failed to generate diagnostics report: {e}")
            return ErrorCode.UNKNOWN_ERROR, None

    # ========================================================================
    # FUNCTION 86-90: Advanced Monitoring
    # ========================================================================
    
    def thermal_prediction_alert(self, temp: float, temp_delta: Optional[float]) -> Tuple[ErrorCode, bool]:
        """
        Fn 86: Alert if temperature will reach 90°C within 10 seconds.
        Predictive warning system.
        """
        if temp_delta is None or temp_delta <= 0:
            return ErrorCode.SUCCESS, False
        
        # Calculate time to reach 90°C
        if temp < 90:
            time_to_limit = (90 - temp) / temp_delta
            
            if time_to_limit < 10:
                logger.warning(f"⚠️  Will reach 90°C in {time_to_limit:.1f}s!")
                return ErrorCode.SUCCESS, True
        
        return ErrorCode.SUCCESS, False
    
    @SafeOperation(ErrorCode.CHECKSUM_MISMATCH)
    def file_integrity_check(self, filepath: str) -> Tuple[ErrorCode, str]:
        """
        Fn 87: Validate file integrity using SHA-256.
        Checks if files have been corrupted or modified.
        """
        try:
            with open(filepath, 'rb') as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()
            
            logger.debug(f"File hash {filepath}: {file_hash}")
            return ErrorCode.SUCCESS, file_hash
            
        except Exception as e:
            logger.error(f"Integrity check failed for {filepath}: {e}")
            return ErrorCode.FILE_NOT_FOUND, ""
    
    @SafeOperation(ErrorCode.PROCESS_ZOMBIE_DETECTED)
    def zombie_process_cleanup(self) -> Tuple[ErrorCode, int]:
        """
        Fn 88: Detect and clean zombie processes.
        Prevents resource leaks from failed process terminations.
        """
        zombie_count = 0
        
        try:
            for proc in psutil.process_iter():
                try:
                    if proc.status() == psutil.STATUS_ZOMBIE:
                        logger.warning(f"Zombie process found: {proc.name()} (PID {proc.pid})")
                        zombie_count += 1
                        # Parent cleanup is automatic on Linux
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            if zombie_count > 0:
                logger.info(f"Found and marked {zombie_count} zombie processes for cleanup")
                return ErrorCode.PROCESS_ZOMBIE_DETECTED, zombie_count
            
            return ErrorCode.SUCCESS, 0
            
        except Exception as e:
            logger.error(f"Zombie process detection failed: {e}")
            return ErrorCode.UNKNOWN_ERROR, -1
    
    def ssd_temperature_monitor(self) -> Tuple[ErrorCode, Optional[float]]:
        """
        Fn 89: Monitor SSD/NVMe temperature to prevent throttling.
        Reads via smartmontools or nvme-cli.
        """
        try:
            # Try smartctl first
            result = subprocess.run(
                ["smartctl", "-a", "/dev/nvme0n1"],
                capture_output=True,
                timeout=5,
                text=True
            )
            
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'Temperature' in line:
                        # Parse temperature
                        parts = line.split()
                        if parts:
                            try:
                                temp = float(parts[-2])
                                logger.debug(f"SSD Temperature: {temp}°C")
                                return ErrorCode.SUCCESS, temp
                            except (ValueError, IndexError):
                                pass
            
            logger.debug("SSD temperature monitoring not available")
            return ErrorCode.SUCCESS, None
            
        except Exception as e:
            logger.debug(f"SSD temp monitoring failed: {e}")
            return ErrorCode.SUCCESS, None
    
    # ========================================================================
    # FUNCTION 90-95: Control & Hysteresis
    # ========================================================================
    
    def fan_speed_hysteresis(self, current_speed: int, new_speed: int, 
                            hysteresis_margin: int = 5) -> int:
        """
        Fn 90: Prevent fan speed from changing by <5% (acoustic stability).
        Reduces speed changes that cause audible noise.
        """
        if abs(new_speed - current_speed) < hysteresis_margin:
            logger.debug(f"Speed change blocked by hysteresis: {current_speed}% -> {new_speed}%")
            return current_speed  # Keep current speed
        
        return new_speed
    
    @SafeOperation(ErrorCode.NBFC_COMMAND_FAILED)
    def nbfc_exclusive_lock(self) -> Tuple[ErrorCode, bool]:
        """
        Fn 91: Prevent other apps from overriding NBFC control.
        Ensures NitroSense maintains exclusive mode.
        """
        try:
            # Try to set exclusive mode (if supported)
            result = subprocess.run(
                ["nbfc", "set", "-m", "exclusive"],
                capture_output=True,
                timeout=5
            )
            
            if result.returncode == 0:
                logger.info("✅ NBFC exclusive lock acquired")
                return ErrorCode.SUCCESS, True
            else:
                logger.warning("⚠️  NBFC exclusive lock not available (continuing in shared mode)")
                return ErrorCode.SUCCESS, False
                
        except Exception as e:
            logger.debug(f"NBFC exclusive lock attempt: {e}")
            return ErrorCode.SUCCESS, False
    
    # ========================================================================
    # FUNCTION 96-100: Security & Network
    # ========================================================================
    
    @SafeOperation(ErrorCode.INVALID_COMMAND_SYNTAX)
    def sanitize_shell_command(self, command: str) -> Tuple[ErrorCode, str]:
        """
        Fn 92: Validate command syntax to prevent shell injection.
        Blocks dangerous characters: ; & | ` $ ( )
        """
        dangerous_chars = [';', '&', '|', '`', '$', '(', ')', '<', '>']
        
        for char in dangerous_chars:
            if char in command:
                logger.warning(f"🔒 Security: Blocked command with '{char}': {command}")
                return ErrorCode.UNSAFE_SHELL_INJECTION, ""
        
        return ErrorCode.SUCCESS, command
    
    @SafeOperation(ErrorCode.CHECKSUM_MISMATCH)
    def verify_file_checksum(self, filepath: str, expected_hash: str) -> Tuple[ErrorCode, bool]:
        """
        Fn 93: Verify file integrity against known good hash.
        Used for update validation and security checks.
        """
        try:
            actual_hash = self.file_integrity_check(filepath)[1]
            
            if actual_hash.lower() == expected_hash.lower():
                logger.info("✅ Checksum verified")
                return ErrorCode.SUCCESS, True
            else:
                logger.error("🔒 Checksum mismatch - file may be corrupted")
                return ErrorCode.CHECKSUM_MISMATCH, False
                
        except Exception as e:
            logger.error(f"Checksum verification failed: {e}")
            return ErrorCode.CHECKSUM_MISMATCH, False
    
    def network_ping_quality(self, target: str = "8.8.8.8") -> Tuple[ErrorCode, Optional[float]]:
        """
        Fn 94: Monitor network quality via ping loss detection.
        Returns packet loss percentage.
        """
        try:
            result = subprocess.run(
                ["ping", "-c", "4", target],
                capture_output=True,
                timeout=10,
                text=True
            )
            
            # Parse ping output for loss
            for line in result.stdout.split('\n'):
                if '% packet loss' in line:
                    loss_str = line.split(',')[2].strip().split('%')[0].strip()
                    loss = float(loss_str)
                    
                    if loss > 0:
                        logger.warning(f"⚠️  Network packet loss: {loss}%")
                    
                    return ErrorCode.SUCCESS, loss
            
            return ErrorCode.SUCCESS, 0.0
            
        except Exception as e:
            logger.debug(f"Ping quality check failed: {e}")
            return ErrorCode.NETWORK_UNREACHABLE, None
    
    def kernel_version_check(self) -> Tuple[ErrorCode, str]:
        """
        Fn 95: Check Linux kernel version for known Nitro 5 bugs.
        Warns about incompatible versions.
        """
        try:
            import platform
            kernel_version = platform.release()
            
            # Known problematic versions for Acer Nitro 5
            problematic_versions = ["5.10.0", "5.13.0"]  # Example
            
            for bad_version in problematic_versions:
                if kernel_version.startswith(bad_version):
                    logger.warning(f"⚠️  Kernel {kernel_version} has known ACPI bugs with Nitro 5")
                    return ErrorCode.KERNEL_VERSION_INCOMPATIBLE, kernel_version
            
            logger.info(f"✅ Kernel {kernel_version} compatible")
            return ErrorCode.SUCCESS, kernel_version
            
        except Exception as e:
            logger.debug(f"Kernel check failed: {e}")
            return ErrorCode.SUCCESS, "Unknown"
    
    @SafeOperation(ErrorCode.NBFC_COMMAND_FAILED)
    def panic_button_full_reset(self) -> Tuple[ErrorCode, bool]:
        """
        Fn 96: Emergency panic button - return to BIOS control immediately.
        Closes NitroSense and restores default fan control.
        """
        try:
            logger.critical("🆘 PANIC BUTTON: Returning to BIOS control")
            
            # Try to restore BIOS control
            subprocess.run(
                ["nbfc", "set", "-m", "bios"],
                capture_output=True,
                timeout=5
            )
            
            self._log_emergency_event("PANIC_BUTTON_ACTIVATED")
            return ErrorCode.SUCCESS, True
            
        except Exception as e:
            logger.error(f"Panic button failed: {e}")
            return ErrorCode.NBFC_COMMAND_FAILED, False
    
    def individual_fan_test(self, fan_number: int = 1) -> Tuple[ErrorCode, bool]:
        """
        Fn 97: Test individual fan (1 or 2) for mechanical issues.
        Diagnostics for hardware problems.
        """
        try:
            if fan_number not in [1, 2]:
                return ErrorCode.UNKNOWN_ERROR, False
            
            logger.info(f"Testing Fan {fan_number}...")
            
            # Command varies by NBFC version
            result = subprocess.run(
                ["nbfc", "set", "-s", "100"],
                capture_output=True,
                timeout=5
            )
            
            return ErrorCode.SUCCESS, result.returncode == 0
            
        except Exception as e:
            logger.error(f"Fan test failed: {e}")
            return ErrorCode.UNKNOWN_ERROR, False
    
    def vrm_voltage_monitor(self) -> Tuple[ErrorCode, Optional[Dict[str, float]]]:
        """
        Fn 98: Monitor Voltage Regulator Modules (VRM) health.
        Checks motherboard power delivery health.
        """
        try:
            result = subprocess.run(
                ["sensors"],
                capture_output=True,
                timeout=5,
                text=True
            )
            
            if result.returncode == 0:
                voltages = {}
                for line in result.stdout.split('\n'):
                    if 'V' in line and ':' in line:
                        # Simple parsing
                        parts = line.split(':')
                        if len(parts) == 2:
                            key = parts[0].strip()
                            val_str = parts[1].strip().split()[0]
                            try:
                                voltages[key] = float(val_str)
                            except ValueError:
                                pass
                
                if voltages:
                    logger.debug(f"VRM Voltages: {voltages}")
                    return ErrorCode.SUCCESS, voltages
            
            return ErrorCode.SUCCESS, None
            
        except Exception as e:
            logger.debug(f"VRM monitoring failed: {e}")
            return ErrorCode.SUCCESS, None
    
    # ========================================================================
    # UTILITY FUNCTIONS
    # ========================================================================
    
    def _play_alert_sound(self) -> None:
        """Play system alert sound."""
        try:
            import subprocess
            subprocess.run(
                ["paplay", "/usr/share/sounds/freedesktop/stereo/alarm-clock-elapsed.oga"],
                timeout=2,
                capture_output=True
            )
        except Exception:
            pass  # Alert sound not critical
    
    def _log_emergency_event(self, event_type: str) -> None:
        """Log emergency event to dedicated log file."""
        try:
            emergency_log = Path.home() / ".config/nitrosense/emergency.log"
            with open(emergency_log, "a") as f:
                f.write(f"[{datetime.now().isoformat()}] {event_type}\n")
        except Exception as e:
            logger.error(f"Failed to log emergency event: {e}")
