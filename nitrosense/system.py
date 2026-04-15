"""
NitroSense System Integration Module
Coordinates all subsystems with error code pattern for anti-crash execution.
"""

from typing import Dict, Tuple, Optional

from .core.logger import logger
from .core.error_codes import ErrorCode, is_critical, get_error_description
from .core.config import ConfigManager
from .hardware.manager import HardwareManager
from .core.monitoring import MonitoringEngine
from .automation.ai_engine import PredictiveAIEngine
from .automation.fan_control import FanController
from .security.diagnostics import SecurityAndDiagnostics
from .security.validation import BackendValidation
from .resilience.signal_hub import get_signal_hub
from .resilience.state_machine import get_state_machine
from .resilience.dirty_bit import get_dirty_bit_cache
from .resilience.watchdog import HardwareWatchdog
from .resilience.system_integrity import SystemIntegrityCheck
from .resilience.lazy_loader import get_lazy_loader
from .core.constants import PERFORMANCE_CONFIG


class NitroSenseSystem:
    """
    Master system controller coordinating all modules.
    All operations return (ErrorCode, Optional[value]) tuples.
    """
    
    def __init__(self):
        """Initialize all subsystems with error handling."""
        self.config_manager: ConfigManager = None
        self.hardware_manager: HardwareManager = None
        self.monitoring: MonitoringEngine = None
        self.ai_engine: PredictiveAIEngine = None
        self.fan_controller: FanController = None
        self.security: SecurityAndDiagnostics = None
        self.validation: BackendValidation = None
        self.initialized = False
        
        # Resilience v3.0 components
        self.signal_hub = get_signal_hub()
        self.state_machine = get_state_machine()
        self.dirty_cache = get_dirty_bit_cache()
        self.watchdog: Optional[HardwareWatchdog] = None
        self.lazy_loader = get_lazy_loader()
        
        logger.info("=" * 60)
        logger.info("NitroSense System v3.0.5 Initialization")
        logger.info("Architecture: Resilience Framework + Performance Optimization")
        logger.info("=" * 60)
    
    def bootstrap(self) -> Tuple[ErrorCode, str]:
        """
        Bootstrap all system components in correct order.
        Returns: (ErrorCode, status_message)
        """
        try:
            # 1. Configuration (must be first - singleton)
            logger.info("🔧 Loading configuration...")
            self.config_manager = ConfigManager()
            logger.info("✅ ConfigManager ready")
            
            # 2. Validation & Backend (dependencies check)
            logger.info("🔧 Validating system...")
            self.validation = BackendValidation()
            
            # Check hardware compatibility
            err, is_acer = self.validation.validate_hardware_dmi_binding()
            if err != ErrorCode.SUCCESS and is_critical(err):
                return err, f"Hardware validation failed: {get_error_description(err)}"
            
            # 3. Hardware Manager (semaphore protected)
            logger.info("🔧 Initializing hardware layer...")
            self.hardware_manager = HardwareManager()
            logger.info("✅ HardwareManager ready")
            
            # 3.5 RESILIENCE: Multi-Stage System Integrity Check
            logger.info("🔍 Running 3-level system integrity check...")
            integrity = SystemIntegrityCheck.full_integrity_check()
            
            if "CRITICAL" in integrity.get("status", ""):
                logger.error(f"⚠️  System integrity issues: {integrity}")
                # Continue anyway - may degrade gracefully
            else:
                logger.info("✅ System integrity check passed")
            
            # 4. Monitoring Engine (with watchdog integration)
            logger.info("🔧 Starting monitoring engine...")
            self.monitoring = MonitoringEngine(self.hardware_manager, self.watchdog)
            logger.info("✅ MonitoringEngine ready (with watchdog integration)")
            
            # 5. AI Engine (depends on monitoring)
            logger.info("🔧 Initializing AI engine...")
            self.ai_engine = PredictiveAIEngine(self.monitoring, self.hardware_manager, self.config_manager)
            logger.info("✅ PredictiveAIEngine ready")
            
            # 6. Fan Controller (depends on hw + ai)
            logger.info("🔧 Starting fan controller...")
            self.fan_controller = FanController(
                self.hardware_manager,
                self.config_manager
            )
            logger.info("✅ FanController ready")
            
            # 7. Security & Diagnostics
            logger.info("🔧 Enabling security module...")
            self.security = SecurityAndDiagnostics(
                self.hardware_manager,
                self.monitoring
            )
            logger.info("✅ SecurityAndDiagnostics ready")
            
            # 8. Final system checks
            logger.info("🔧 Running system diagnostics...")
            err, diag_report = self.security.generate_diagnostic_report()
            
            if err != ErrorCode.SUCCESS:
                logger.warning(f"Diagnostics warning: {get_error_description(err)}")
            
            # 9. RESILIENCE: Start Hardware Watchdog AFTER monitoring is ready
            watchdog_timeout = PERFORMANCE_CONFIG.get("watchdog_timeout", 10.0)
            logger.info(f"🐕 Starting hardware watchdog ({watchdog_timeout:.0f}s timeout)...")
            self.watchdog = HardwareWatchdog(timeout_sec=watchdog_timeout)
            self.watchdog.timeout_detected.connect(self._on_watchdog_timeout)
            self.watchdog.start()
            logger.info("✅ Hardware watchdog active")
            
            # Update monitoring reference to watchdog
            self.monitoring.watchdog = self.watchdog
            
            self.initialized = True
            logger.info("=" * 60)
            logger.info("✅ NitroSense System v3.0.5 READY (Resilience Framework)")
            logger.info("=" * 60)
            
            return ErrorCode.SUCCESS, "System initialized"
            
        except Exception as e:
            logger.critical(f"Bootstrap failed: {e}")
            return ErrorCode.CRITICAL_SYSTEM_FAILURE, str(e)
    
    def start_monitoring(self) -> Tuple[ErrorCode, str]:
        """Start background monitoring and fan control with watchdog integration."""
        try:
            if not self.initialized:
                return ErrorCode.UNKNOWN_ERROR, "System not initialized"
            
            # Ensure watchdog is ready before starting monitoring
            if not self.watchdog:
                logger.warning("⚠️  Watchdog not initialized, starting without it")
            
            logger.info("🔧 Calling monitoring.start_monitoring()...")
            # Start monitoring thread (IdlePriority with watchdog heartbeat integration)
            err, msg = self.monitoring.start_monitoring()
            logger.info(f"🔧 monitoring.start_monitoring() returned: {err}, {msg}")
            if err != ErrorCode.SUCCESS:
                return err, f"Monitoring failed: {get_error_description(err)}"
            
            logger.info("✅ Monitoring started (IdlePriority + Watchdog)")
            return ErrorCode.SUCCESS, "Monitoring active"
            
        except Exception as e:
            logger.error(f"Monitor start failed: {e}")
            return ErrorCode.THREAD_CREATION_FAILED, str(e)
    
    def stop_monitoring(self) -> Tuple[ErrorCode, str]:
        """Stop background monitoring gracefully."""
        try:
            if self.monitoring:
                self.monitoring.stop_monitoring()
                logger.info("✅ Monitoring stopped")
            
            return ErrorCode.SUCCESS, "Monitoring stopped"
            
        except Exception as e:
            logger.error(f"Monitor stop failed: {e}")
            return ErrorCode.UNKNOWN_ERROR, str(e)
    
    def _on_watchdog_timeout(self):
        """Called when hardware watchdog detects timeout."""
        logger.critical("🚨 WATCHDOG TIMEOUT - Hardware bus may be hung")
        self.signal_hub.emergencyProtocolTriggered.emit(ErrorCode.THREAD_TIMEOUT)
        # Watchdog auto-triggers bus reset
    
    def shutdown(self) -> Tuple[ErrorCode, str]:
        """Graceful system shutdown."""
        try:
            logger.info("Shutting down NitroSense v3.0.5...")
            
            # Stop watchdog first
            if self.watchdog:
                self.watchdog.stop()
                logger.info("🐕 Watchdog stopped")
            
            # Stop monitoring
            self.stop_monitoring()
            
            # Save any pending configuration
            if self.config_manager:
                self.config_manager.flush()
            
            # Reset fan to balanced
            if self.fan_controller:
                self.fan_controller.set_profile("balanced")
            
            logger.info("✅ Shutdown complete")
            return ErrorCode.SUCCESS, "Shutdown complete"
            
        except Exception as e:
            logger.error(f"Shutdown error: {e}")
            return ErrorCode.UNKNOWN_ERROR, str(e)
    
    def get_system_status(self) -> Dict:
        """Get comprehensive system status (all error codes)."""
        status = {
            "initialized": self.initialized,
            "monitoring": {
                "cpu_temp": self.monitoring.last_cpu_temp if self.monitoring else 0,
                "gpu_temp": self.monitoring.last_gpu_temp if self.monitoring else 0,
                "rpm": self.monitoring.last_nbfc_rpm if self.monitoring else 0,
            },
            "config": {
                "loaded": self.config_manager is not None,
            },
            "hardware": {
                "ec_available": self.hardware_manager.ec_available if self.hardware_manager else False,
                "nbfc_available": self.hardware_manager.nbfc_available if self.hardware_manager else False,
            },
            "errors": [],
        }
        
        return status
    
    def handle_error(self, error_code: ErrorCode, context: str = "") -> None:
        """
        Central error handling (all errors flow through here).
        Logs, alerts UI, triggers emergency protocol if needed.
        """
        description = get_error_description(error_code)
        
        logger.error(f"Error {error_code}: {description} [{context}]")
        
        if is_critical(error_code):
            logger.critical(f"⛔ CRITICAL ERROR: {description}")
            
            # Trigger emergency protocol for thermal cases
            if error_code in [ErrorCode.CRITICAL_TEMP_95C, ErrorCode.CRITICAL_TEMP_100C]:
                if self.security:
                    self.security.emergency_protocol_95c()
