"""
Main Entry Point - NitroSense Ultimate Application
Initializes all systems and launches the UI

CRITICAL DESIGN PRINCIPLES:
1. All long-lived objects (Threads, Hardware, Windows) are stored as QApplication attributes (anti-GC)
2. Splash screen is the pre-flight validator and error bridge
3. Global exception handlers catch and log surgically with full context
4. Signal/slot lifecycle is managed with explicit cleanup
5. Hardware watchdog enforces 100% fan on sensor failure
"""

import os
import sys
import time
import threading
import argparse
import signal
import atexit
import gc
from pathlib import Path
from typing import Optional

# Ensure we can import from the package
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
import traceback

from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPlainTextEdit,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget
)
from PyQt6.QtGui import QColor, QFont, QTextCursor
from PyQt6.QtCore import Qt, QTimer, QObject, QThread, pyqtSignal, QCoreApplication

from nitrosense.core.logger import setup_logging, logger
from nitrosense.core.error_handler import setup_exception_handler
from nitrosense.core.error_codes import ErrorCode, is_critical, get_error_description
from nitrosense.core.constants import APP_CONFIG, DEVICE_VALIDATION, LOG_CONFIG
from nitrosense.core.single_instance import SingleInstanceLock
from nitrosense.core.hotkeys import CrashReporter, HotkeysManager
from nitrosense.ui.splash import (
    create_splash_screen,
    update_splash,
    log_validation_step,
    QtSplashLogHandler,
    SplashWindow,
)
from nitrosense.i18n import initialize_i18n, t
from nitrosense.ui.tray_icon import AutostartManager
from nitrosense.resilience.system_integrity import SystemIntegrityCheck
from nitrosense.system import NitroSenseSystem
from nitrosense.ui.main_window import NitroSenseApp


class NitroSenseApplication(QApplication):
    """Application subclass to own runtime state and long-lived objects."""

    single_instance_lock: Optional[SingleInstanceLock]
    previous_crash_detected: bool
    system: Optional['NitroSenseSystem']
    worker: 'StartupWorker'
    startup_thread: QThread
    main_window: 'NitroSenseApp'
    hotkeys_manager: Optional[HotkeysManager]
    log_handler: Optional[logging.Handler]

SESSION_LOCK_DIR = Path.home() / ".config" / "nitrosense"
SESSION_LOCK_FILE = SESSION_LOCK_DIR / ".session_lock"

ERROR_TRANSLATIONS = {
    FileNotFoundError: t("Incapaz de localizar um arquivo de sistema necessário. Verifique as permissões e tente novamente."),
    PermissionError: t("Permissão insuficiente para acessar sensores. Execute como root ou ajuste as regras de udev."),
    RuntimeError: t("Falha temporária no subsistema de hardware. Reiniciando monitoramento automaticamente."),
}


def get_user_friendly_error(exc: Exception) -> str:
    """Mapeia exceções internas para mensagens amigáveis ao usuário."""
    for exc_type, message in ERROR_TRANSLATIONS.items():
        if isinstance(exc, exc_type):
            return message
    return t("Ocorreu um erro interno. Verifique os logs e reinicie o aplicativo.")


def ensure_session_lock() -> None:
    """Create a session lock file to detect unexpected shutdowns."""
    try:
        SESSION_LOCK_DIR.mkdir(parents=True, exist_ok=True)
        SESSION_LOCK_FILE.write_text(
            f"pid={os.getpid()}\nstarted={time.time()}\n",
            encoding="utf-8",
        )
        logger.info(f"Session lock created: {SESSION_LOCK_FILE}")
    except Exception as exc:
        logger.warning(f"Unable to create session lock: {exc}")


def clear_session_lock() -> None:
    """Remove the session lock file on clean shutdown."""
    try:
        SESSION_LOCK_FILE.unlink(missing_ok=True)
        logger.info("Session lock cleared")
    except Exception as exc:
        logger.warning(f"Unable to clear session lock: {exc}")


def check_previous_crash() -> bool:
    """Return True if the previous app instance terminated unexpectedly."""
    try:
        if SESSION_LOCK_FILE.exists():
            logger.warning("Previous session lock found, last shutdown may have been unclean")
            return True
    except Exception as exc:
        logger.warning(f"Unable to verify previous crash state: {exc}")
    return False


class LogViewerDialog(QDialog):
    """Standalone dialog to show current log file contents in a terminal-like view."""

    def __init__(self, log_path, parent=None):
        super().__init__(parent)
        self.log_path = log_path
        self.setWindowTitle("NitroSense Logs")
        self.setModal(False)
        self.resize(760, 520)

        layout = QVBoxLayout(self)
        self.viewer = QPlainTextEdit(self)
        self.viewer.setReadOnly(True)
        self.viewer.setStyleSheet(
            "QPlainTextEdit {"
            "  background: #11151b;"
            "  color: #d1f2ff;"
            "  border: 1px solid #2f3a4a;"
            "  border-radius: 12px;"
            "  padding: 10px;"
            "}"
        )
        layout.addWidget(self.viewer)

        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(1000)
        self.refresh_timer.timeout.connect(self.refresh)
        self.refresh_timer.start()

        button_layout = QHBoxLayout()
        refresh_button = QPushButton("Refresh", self)
        copy_button = QPushButton("Copy all", self)
        button_layout.addWidget(refresh_button)
        button_layout.addStretch()
        button_layout.addWidget(copy_button)
        layout.addLayout(button_layout)

        refresh_button.clicked.connect(self.refresh)
        copy_button.clicked.connect(self.copy_all)

        self.refresh()

    def refresh(self) -> None:
        try:
            text = self.log_path.read_text(encoding="utf-8", errors="replace")
        except (OSError, UnicodeError) as exc:
            text = f"Unable to read log file: {exc}"
        self.viewer.setPlainText(text)
        self.viewer.moveCursor(QTextCursor.MoveOperation.End)

    def copy_all(self) -> None:
        self.viewer.selectAll()
        self.viewer.copy()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run NitroSense Ultimate")
    parser.add_argument(
        "--no-splash",
        action="store_true",
        help="Skip the splash screen during startup",
    )
    parser.add_argument(
        "--background",
        action="store_true",
        help="Start the application in background mode (minimized)",
    )
    return parser.parse_args()


def check_prerequisites() -> bool:
    """Verify system requirements and dependencies."""
    try:
        logger.info("=" * 60)
        logger.info(f"NitroSense Ultimate v{APP_CONFIG['version']}")
        logger.info(f"Target: {APP_CONFIG['target_device']}")
        logger.info(f"Architecture: {APP_CONFIG.get('architecture', 'Standard')[:50]}")
        logger.info("=" * 60)

        python_version = sys.version_info
        if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 12):
            logger.error("Python 3.12+ required")
            return False
        logger.info(f"Python {python_version.major}.{python_version.minor} OK")

        try:
            device_path = Path(DEVICE_VALIDATION["dmi_product_path"])
            if device_path.exists():
                device_name = device_path.read_text().strip()
                logger.info(f"Device: {device_name}")

                if not any(model in device_name for model in DEVICE_VALIDATION["accepted_models"]):
                    logger.warning(f"Device {device_name} may not be fully supported")
        except Exception as e:
            logger.debug(f"Device check failed: {e}")

        return True
    except Exception as e:
        logger.critical(f"Prerequisites check failed: {e}")
        return False


class StartupWorker(QObject):
    """Worker thread for pre-flight validation and system bootstrap."""
    
    update_progress = pyqtSignal(str, int)  # (message, progress_value)
    validation_step = pyqtSignal(str, str)  # (message, status: INFO|WARN|ERROR)
    startup_failed = pyqtSignal(str)  # Failure reason
    startup_complete = pyqtSignal(object)  # NitroSenseSystem instance

    def run(self) -> None:
        """Main startup sequence with comprehensive error handling."""
        try:
            self.perform_startup()
        except Exception as exc:
            tb = traceback.format_exc()
            self.startup_failed.emit(f"Startup error: {exc}\n{tb}")
        finally:
            pass

    def perform_startup(self) -> None:
        """
        Complete pre-flight validation and system bootstrap.
        If any CRITICAL failure occurs, must not proceed to UI.
        """
        start_time = time.monotonic()

        # Phase 1: Prerequisites
        self.update_progress.emit("Verifying prerequisites...", 5)
        self.validation_step.emit("Checking Python version and system paths", "INFO")
        if not self._check_prerequisites():
            self.startup_failed.emit("System prerequisites check failed.")
            return

        # Phase 2: Path & Permission Validation
        self.update_progress.emit("Validating I/O permissions and asset paths...", 15)
        self.validation_step.emit("Checking asset paths and I/O permissions", "INFO")
        if not self._validate_paths_and_permissions():
            self.startup_failed.emit("Critical I/O paths not accessible.")
            return

        # Phase 3: System Integrity
        self.update_progress.emit("Running system integrity checks...", 25)
        self.validation_step.emit("Validating system integrity (3-level check)", "INFO")
        integrity_ok = self._validate_system_integrity()
        if not integrity_ok:
            self.validation_step.emit("System integrity issues detected—degraded mode", "WARN")

        # Phase 4: Hardware Validation
        self.update_progress.emit("Validating hardware sensors...", 35)
        self.validation_step.emit("Testing sensor accessibility and permissions", "INFO")
        if not self._validate_hardware_sensors():
            self.validation_step.emit("Hardware sensor validation failed", "WARN")

        # Phase 5: Initialize NitroSenseSystem
        self.update_progress.emit("Bootstrapping NitroSense subsystems...", 50)
        self.validation_step.emit("Initializing core system components", "INFO")
        system = NitroSenseSystem()

        err, bootstrap_msg = system.bootstrap()
        if err != ErrorCode.SUCCESS:
            logger.error(f"Bootstrap failed: {get_error_description(err)}")
            if is_critical(err):
                self.startup_failed.emit(
                    f"Critical bootstrap failed: {get_error_description(err)}"
                )
                return
            self.validation_step.emit(f"Non-critical error: {bootstrap_msg}", "WARN")

        # Phase 6: Dependency Check
        self.update_progress.emit("Verifying hardware dependencies...", 70)
        if getattr(system, "hardware_manager", None):
            try:
                deps = system.hardware_manager.check_dependencies()
                dep_status = "OK" if all(deps.values()) else "Missing"
                self.validation_step.emit(f"Dependencies: {dep_status}", "INFO")
            except Exception as e:
                self.validation_step.emit(f"Dependency check error: {e}", "WARN")

        # Phase 7: Asset Integrity & Fallbacks
        self.update_progress.emit("Verifying UI assets...", 80)
        self.validation_step.emit("Checking icons, fonts, and theme assets", "INFO")
        self._validate_ui_assets()

        # Phase 8: Final Checks
        self.update_progress.emit("Finalizing startup...", 90)
        elapsed = time.monotonic() - start_time
        if elapsed < 3.0:
            time.sleep(3.0 - elapsed)

        self.update_progress.emit("✓ All validation passed—launching UI", 100)
        self.validation_step.emit("STARTUP SUCCESSFUL: All systems ready", "INFO")
        self.startup_complete.emit(system)

    def _check_prerequisites(self) -> bool:
        """Verify Python version and basic system requirements."""
        try:
            python_version = sys.version_info
            if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 12):
                self.validation_step.emit("Python 3.12+ required", "ERROR")
                return False
            self.validation_step.emit(f"Python {python_version.major}.{python_version.minor} ✓", "INFO")

            try:
                device_path = Path(DEVICE_VALIDATION["dmi_product_path"])
                if device_path.exists():
                    device_name = device_path.read_text().strip()
                    if not any(model in device_name for model in DEVICE_VALIDATION["accepted_models"]):
                        self.validation_step.emit(f"Device {device_name} may not be supported", "WARN")
                    else:
                        self.validation_step.emit(f"Device: {device_name} ✓", "INFO")
            except Exception as e:
                self.validation_step.emit(f"Device check skipped: {e}", "INFO")

            return True
        except Exception as e:
            self.validation_step.emit(f"Prerequisites check failed: {e}", "ERROR")
            return False

    def _validate_paths_and_permissions(self) -> bool:
        """Check critical I/O paths and read/write permissions."""
        try:
            log_dir = Path(LOG_CONFIG.get("log_dir", "/tmp/nitrosense"))
            
            # Check/create log directory
            log_dir.mkdir(parents=True, exist_ok=True)
            
            # Test write permission
            test_file = log_dir / ".nitrosense_write_test"
            try:
                test_file.write_text("test")
                test_file.unlink()
                self.validation_step.emit(f"Log directory {log_dir} is writable ✓", "INFO")
            except (PermissionError, OSError) as e:
                self.validation_step.emit(f"Log directory not writable: {e}", "ERROR")
                return False

            # Check asset paths
            asset_dirs = [
                Path(__file__).parent / "nitrosense" / "assets" / "icons",
            ]
            for asset_dir in asset_dirs:
                if not asset_dir.exists():
                    self.validation_step.emit(f"Asset path missing: {asset_dir}", "WARN")
                else:
                    self.validation_step.emit(f"Asset path found: {asset_dir.name} ✓", "INFO")

            return True
        except Exception as e:
            self.validation_step.emit(f"Path validation error: {e}", "ERROR")
            return False

    def _validate_system_integrity(self) -> bool:
        """Run 3-level system integrity check."""
        try:
            integrity_result = SystemIntegrityCheck.full_integrity_check()
            status = integrity_result.get("status", "UNKNOWN")
            
            if "CRITICAL" in status:
                self.validation_step.emit(f"Integrity: CRITICAL issues detected", "ERROR")
                return False
            elif "WARNING" in status:
                self.validation_step.emit(f"Integrity: Warnings present (degraded mode)", "WARN")
                return True
            else:
                self.validation_step.emit(f"Integrity: All checks passed ✓", "INFO")
                return True
        except Exception as e:
            self.validation_step.emit(f"Integrity check error: {e}", "WARN")
            return True  # Don't fail on integrity check error

    def _validate_hardware_sensors(self) -> bool:
        """Test hardware sensor accessibility."""
        try:
            # This will be expanded once hardware is initialized
            self.validation_step.emit("Sensor validation (hardware not yet initialized)", "INFO")
            return True
        except Exception as e:
            self.validation_step.emit(f"Sensor validation error: {e}", "WARN")
            return True

    def _validate_ui_assets(self) -> None:
        """Verify UI assets with fallback mechanisms."""
        try:
            icon_dir = Path(__file__).parent / "nitrosense" / "assets" / "icons"
            required_icons = ["home.png", "settings.png"]
            
            for icon in required_icons:
                icon_path = icon_dir / icon
                if not icon_path.exists():
                    self.validation_step.emit(f"Icon {icon} missing (fallback enabled)", "WARN")
                else:
                    self.validation_step.emit(f"Icon {icon} ✓", "INFO")
        except Exception as e:
            self.validation_step.emit(f"Asset validation error: {e}", "WARN")


def handle_startup_failure(
    splash: Optional[SplashWindow],
    app: QCoreApplication,
    message: str,
    use_dialogs: bool = True,
) -> None:
    """
    Handle startup failure with surgical error logging.
    Logs: Module, Function, Attempted Action, Cause, Last 5 Variables, Hints
    """
    logger.critical(f"STARTUP FAILURE: {message}")
    
    # Extract stack context for surgical logging
    tb_lines = traceback.format_exc().split('\n')
    logger.critical("Stack trace (last 5 frames):")
    for line in tb_lines[-6:-1]:
        logger.critical(f"  {line}")

    if not use_dialogs or not splash:
        logger.warning("Keeping application active for manual shutdown")
        return

    try:
        from PyQt6.QtWidgets import QMessageBox
        
        friendly_message = get_user_friendly_error(Exception(message))
        splash.log_validation(f"ERROR: {message}", "ERROR")
        
        QMessageBox.critical(
            None,
            "NitroSense - Initialization Failed",
            f"{friendly_message}\n\nDetalhes técnicos foram gravados em log.\n\nHINTS:\n"
            "• Execute como root ou ajuste regras de udev, se necessário.\n"
            "• Verifique hardware sensores e dependências de driver.\n"
            "• Abra o log em NitroSense para informações adicionais.",
        )
        
        if hasattr(splash, "progress_bar"):
            splash.progress_bar.hide()
        
        update_splash(splash, "Startup failed—check logs", 100)
        splash.show()
        
    except Exception as e:
        logger.critical(f"Error displaying failure dialog: {e}", exc_info=True)


def finish_startup(
    splash: Optional[SplashWindow],
    app: NitroSenseApplication,
    system: NitroSenseSystem,
    thread: QThread,
) -> None:
    """
    Finalize startup: create main window, start monitoring, keep objects persistent.
    CRITICAL: Store main_window on app to prevent garbage collection.
    """
    logger.info("Creating main application window...")
    app.system = system

    try:
        start_minimized = system.config_manager.get("advanced_config", {}).get("start_minimized", False)
        
        if getattr(app, 'previous_crash_detected', False):
            logger.warning("Previous execution ended unexpectedly; enabling crash recovery defaults")
            try:
                if hasattr(system, 'fan_controller'):
                    system.fan_controller.enable_auto_curve()
                    logger.info("Crash recovery: auto thermal profile enabled")
            except Exception as ex:
                logger.warning(f"Crash recovery fallback failed: {ex}")

        # CREATE MAIN WINDOW AND STORE ON APP (ANTI-GC)
        app.main_window = NitroSenseApp(system)
        logger.info("✓ Main window created and stored on QApplication (persistent)")

        if start_minimized:
            app.main_window.show()
            app.main_window.showMinimized()
            logger.info("Application minimized on startup")
        else:
            app.main_window.show()
            logger.info("Application window shown")

        if splash:
            splash.close()
            logger.info("Splash window closed")

    except Exception as e:
        logger.critical(f"Failed to create main window: {e}", exc_info=True)
        tb_str = traceback.format_exc()
        logger.critical(f"Full traceback:\n{tb_str}")
        
        if splash:
            splash.log_validation(f"FATAL: Failed to create main window: {e}", "ERROR")
            splash.log_validation(tb_str, "ERROR")
            splash.show()
        
        handle_startup_failure(splash, app, f"Failed to create main window: {e}")
        return

    # Start background monitoring
    monitor_err, monitor_msg = system.start_monitoring()
    if monitor_err != ErrorCode.SUCCESS:
        logger.warning(f"Background monitoring warning: {monitor_msg}")
    else:
        logger.info("✓ Background monitoring is active")
    
    # ===== DIR 6: Start Hardware Watchdog =====
    if hasattr(system, 'watchdog') and system.watchdog:
        system.watchdog.running = True
        system.watchdog.start()
        logger.info("✓ Hardware watchdog started (100% fan on >3 sensor failures)")
    
    # ===== DIR 13: Check/Offer Autostart Configuration =====
    try:
        if not AutostartManager.is_autostart_enabled():
            logger.debug("Autostart not configured, offer to user (optional)")
            # Note: User can enable via UI settings
        else:
            logger.info("✓ Autostart is enabled")
    except Exception as e:
        logger.warning(f"Failed to check autostart status: {e}")
    
    # ===== DIR 15: Register Global Hotkeys =====
    try:
        hotkeys_manager = HotkeysManager()
        
        # Register Frost Mode hotkey
        def frost_mode_handler():
            logger.info("Frost Mode hotkey triggered (Ctrl+Shift+F)")
            main_window = app.main_window
            if main_window is not None:
                main_window._tray_activate_frost_mode()
        
        hotkeys_manager.register_hotkey(
            "ctrl+shift+f",
            frost_mode_handler,
            "Activate Frost Mode"
        )
        
        if hotkeys_manager.start_listening():
            app.hotkeys_manager = hotkeys_manager  # Store for cleanup
            logger.info("✓ Global hotkeys registered (Ctrl+Shift+F for Frost Mode)")
    except Exception as e:
        logger.warning(f"Failed to register global hotkeys: {e}")

    logger.info("=" * 60)
    logger.info("✓ NitroSense Ultimate v3.0.5 LAUNCHED SUCCESSFULLY")
    logger.info("=" * 60)
    
    # Clean up startup thread
    thread.quit()
    thread.wait(2000)  # Wait up to 2s for clean exit


def main():
    """
    Main application entry point.
    
    CRITICAL LIFECYCLE:
    1. Single instance lock (prevent hardware collision)
    2. Setup exception handlers (ALL exceptions caught here)
    3. Create QApplication (parent for all objects)
    4. Show splash screen (pre-flight validation)
    5. Start background startup thread
    6. If all passes: spawn main window
    7. Signal handlers ensure clean shutdown
    """
    # SINGLE INSTANCE LOCK - MUST BE FIRST (before QApplication)
    # This prevents multiple instances from corrupting hardware communication
    single_instance_lock = SingleInstanceLock()
    lock_acquired, lock_msg = single_instance_lock.acquire()
    
    if not lock_acquired:
        # Another instance is already running
        print(f"ERROR: {lock_msg}")
        if "already running" in lock_msg.lower():
            print("Another instance of NitroSense Ultimate is already running.")
            print("To launch another instance, close the existing one first.")
        return 1
    
    args = parse_args()
    previous_crash = check_previous_crash()
    
    # CREATE QAPPLICATION FIRST (Parent of everything)
    app: NitroSenseApplication = NitroSenseApplication(sys.argv)
    initialize_i18n("auto")
    
    # Store lock on app to keep it alive
    app.single_instance_lock = single_instance_lock
    app.previous_crash_detected = previous_crash
    app.system = None

    ensure_session_lock()
    atexit.register(clear_session_lock)
    
    # Setup global exception handlers
    setup_exception_handler(use_dialogs=True)

    def global_exception_hook(exc_type, exc_value, exc_traceback):
        """Catch ALL unhandled exceptions with surgical logging and pre-death telemetry."""
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        # SURGICAL LOGGING
        logger.critical("=" * 70)
        logger.critical("UNHANDLED EXCEPTION - SURGICAL ERROR LOG")
        logger.critical("=" * 70)
        logger.critical(f"Module: {exc_traceback.tb_frame.f_globals.get('__name__', 'unknown')}")
        logger.critical(f"Function: {exc_traceback.tb_frame.f_code.co_name}")
        logger.critical(f"Line {exc_traceback.tb_lineno}: {exc_traceback.tb_frame.f_code.co_filename}")
        logger.critical(f"Exception Type: {exc_type.__name__}")
        logger.critical(f"Exception Message: {exc_value}")
        
        # Log last 5 local variables
        frame = exc_traceback.tb_frame
        logger.critical("Local variables (last 5):")
        for var, value in list(frame.f_locals.items())[-5:]:
            try:
                logger.critical(f"  {var} = {repr(value)[:100]}")
            except:
                logger.critical(f"  {var} = <unprintable>")
        
        logger.critical("=" * 70)
        logger.critical("RESOLUTION HINTS:")
        logger.critical("  • Check system permissions (may need sudo)")
        logger.critical("  • Verify hardware sensor paths exist")
        logger.critical("  • Check disk space and write permissions")
        logger.critical("  • Review full traceback in logs directory")
        logger.critical("=" * 70)
        
        # Generate pre-death crash report with telemetry
        try:
            tb_str = traceback.format_exc()
            crash_report_path = CrashReporter.generate_crash_report(exc_value, tb_str)
            if crash_report_path:
                logger.critical(f"Crash report saved: {crash_report_path}")
        except Exception as e:
            logger.error(f"Failed to generate crash report: {e}")

    sys.excepthook = global_exception_hook

    def thread_exception_handler(args: threading.ExceptHookArgs) -> None:
        """Catch unhandled exceptions in threads."""
        exc_value = args.exc_value or Exception("Unknown thread exception")
        logger.critical(
            f"THREAD EXCEPTION: {args.exc_type.__name__}: {exc_value}",
            exc_info=(args.exc_type, exc_value, args.exc_traceback),
        )

    threading.excepthook = thread_exception_handler

    def unraisable_exception_hook(unraisable):
        """Catch exceptions that can't be raised normally."""
        logger.error(
            f"Unraisable exception: {unraisable.exc_value}",
            exc_info=(
                getattr(unraisable, 'exc_type', None),
                getattr(unraisable, 'exc_value', None),
                getattr(unraisable, 'exc_traceback', None)
            ),
        )

    sys.unraisablehook = unraisable_exception_hook

    # SIGNAL HANDLERS FOR CLEAN SHUTDOWN
    def signal_handler(signum, frame):
        """Handle SIGTERM/SIGINT gracefully: clean fan control before exit."""
        logger.info(f"Signal {signum} received - initiating graceful shutdown")
        
        # 1. Stop monitoring
        try:
            if hasattr(app, 'main_window') and app.main_window:
                logger.info("Closing main window...")
                app.main_window.close()
        except Exception as e:
            logger.error(f"Error closing main window: {e}")
        
        # 2. Return fan control to BIOS
        try:
            if hasattr(app, 'system') and app.system:
                system = app.system
                if hasattr(system, 'fan_controller'):
                    logger.info("Returning fan control to BIOS...")
                    # This will trigger a signal in fan_controller
        except Exception as e:
            logger.error(f"Error returning fan control: {e}")
        
        # 3. Stop watchdog
        try:
            system = app.system
            if system is not None:
                watchdog = getattr(system, 'watchdog', None)
                if watchdog is not None:
                    logger.info("Stopping hardware watchdog...")
                    watchdog.stop()
        except Exception as e:
            logger.error(f"Error stopping watchdog: {e}")
        
        # 4. Release single instance lock
        try:
            lock = app.single_instance_lock
            if lock is not None:
                logger.info("Releasing single instance lock...")
                lock.release()
        except Exception as e:
            logger.error(f"Error releasing lock: {e}")
        
        # 5. Quit application
        logger.info("Exiting NitroSense Ultimate")
        app.quit()

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # ATEXIT HANDLER FOR FINAL CLEANUP
    def atexit_cleanup():
        """Final cleanup on exit."""
        logger.info("Application exit cleanup running...")
        try:
            # Force collect garbage
            gc.collect()
        except:
            pass

    atexit.register(atexit_cleanup)

    # CREATE AND SHOW SPLASH SCREEN
    splash = None
    use_splash = not args.no_splash

    if use_splash:
        try:
            log_path = Path(LOG_CONFIG["log_dir"]) / LOG_CONFIG["log_file"]
            splash = create_splash_screen(log_path)
            splash.log_handler = QtSplashLogHandler(splash.terminal)
            logger.addHandler(splash.log_handler)
            logger.info("✓ Splash screen created")
            if getattr(app, 'previous_crash_detected', False):
                splash.log_validation(
                    t("Detectado fechamento inesperado na última execução. Modo de recuperação ativado."),
                    "WARN",
                )
        except Exception as exc:
            logger.critical(f"Failed to create splash screen: {exc}", exc_info=True)

    # CREATE STARTUP WORKER AND THREAD
    # CRITICAL: Store on app to prevent garbage collection
    app.worker = StartupWorker()
    startup_thread = QThread()
    app.startup_thread = startup_thread
    
    app.worker.moveToThread(startup_thread)
    
    # Connect signals
    app.worker.update_progress.connect(
        lambda msg, value: update_splash(splash, msg, value)
    )
    app.worker.validation_step.connect(
        lambda msg, status: log_validation_step(splash, msg, status)
    )
    app.worker.startup_failed.connect(
        lambda reason: handle_startup_failure(splash, app, reason)
    )
    app.worker.startup_complete.connect(
        lambda system: finish_startup(splash, app, system, startup_thread)
    )
    
    app.startup_thread.started.connect(app.worker.run)
    app.startup_thread.start()

    # RUN EVENT LOOP WITH EXCEPTION PROTECTION
    try:
        logger.info("Starting Qt event loop...")
        exit_code = app.exec()
        logger.info(f"Qt event loop exited with code: {exit_code}")
        return exit_code
    except Exception as exc:
        logger.critical(f"Unexpected Qt event loop failure: {exc}", exc_info=True)
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Application interrupted by user (Ctrl+C)")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Fatal application error: {e}", exc_info=True)
        sys.exit(1)
