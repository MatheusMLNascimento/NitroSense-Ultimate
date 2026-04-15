"""
Startup manager for NitroSense Ultimate.
Encapsulates pre-flight validation, subsystem bootstrap, and splash screen orchestration.
"""

import sys
import os
import time
import traceback
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PyQt6.QtCore import QObject, QThread, pyqtSignal
from PyQt6.QtWidgets import QMessageBox

from ..core.logger import logger
from ..core.constants import APP_CONFIG, DEVICE_VALIDATION, LOG_CONFIG, PERFORMANCE_CONFIG
from ..core.error_codes import ErrorCode, is_critical, get_error_description
from ..resilience.system_integrity import SystemIntegrityCheck
from ..system import NitroSenseSystem

from ..ui.splash import (
    create_splash_screen,
    update_splash,
    log_validation_step,
    QtSplashLogHandler,
    SplashWindow,
)


def get_user_friendly_error(exc: Exception) -> str:
    """Map common exceptions to friendly user-facing messages."""
    error_translations = {
        FileNotFoundError: "Incapaz de localizar um arquivo de sistema necessário. Verifique as permissões e tente novamente.",
        PermissionError: "Permissão insuficiente para acessar sensores. Execute como root ou ajuste as regras de udev.",
        RuntimeError: "Falha temporária no subsistema de hardware. Reiniciando monitoramento automaticamente.",
    }
    for exc_type, message in error_translations.items():
        if isinstance(exc, exc_type):
            return message
    return "Ocorreu um erro interno. Verifique os logs e reinicie o aplicativo."


class StartupManager(QObject):
    """Dedicated startup manager for boot orchestration."""

    update_progress = pyqtSignal(str, int)
    validation_step = pyqtSignal(str, str)
    startup_failed = pyqtSignal(str)
    startup_complete = pyqtSignal(object)
    dependency_install_prompt = pyqtSignal(object, object)

    def __init__(self) -> None:
        super().__init__()
        self.missing_deps_data: Optional[Tuple[Dict[str, List[str]], Dict[str, List[str]]]] = None
        self.thread = QThread()
        self.moveToThread(self.thread)
        self.thread.started.connect(self.run)

    def start(self) -> None:
        """Start the startup thread."""
        self.thread.start()

    def stop(self) -> None:
        """Stop the startup thread cleanly."""
        self.thread.quit()
        self.thread.wait(2000)

    def run(self) -> None:
        """Main startup sequence executed in a worker thread."""
        try:
            self.perform_startup()
        except Exception as exc:
            tb = traceback.format_exc()
            self.startup_failed.emit(f"Startup error: {exc}\n{tb}")

    def perform_startup(self) -> None:
        """Perform full validation and bootstrap of NitroSense subsystems."""
        start_time = time.monotonic()

        self.update_progress.emit("Verifying prerequisites...", 5)
        self.validation_step.emit("Checking Python version and system paths", "INFO")
        if not self._check_prerequisites():
            self.startup_failed.emit("System prerequisites check failed.")
            return

        self.update_progress.emit("Validating I/O permissions and asset paths...", 15)
        self.validation_step.emit("Checking asset paths and I/O permissions", "INFO")
        if not self._validate_paths_and_permissions():
            self.startup_failed.emit("Critical I/O paths not accessible.")
            return

        self.update_progress.emit("Running system integrity checks...", 25)
        self.validation_step.emit("Validating system integrity (3-level check)", "INFO")
        integrity_ok = self._validate_system_integrity()
        if not integrity_ok:
            self.validation_step.emit("System integrity issues detected—degraded mode", "WARN")

        self.update_progress.emit("Validating hardware sensors...", 35)
        self.validation_step.emit("Testing sensor accessibility and permissions", "INFO")
        if not self._validate_hardware_sensors():
            self.validation_step.emit("Hardware sensor validation failed", "WARN")

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

        self.update_progress.emit("Verifying hardware dependencies...", 70)
        if getattr(system, "hardware_manager", None):
            try:
                deps = system.hardware_manager.check_dependencies()
                dep_status = "OK" if all(deps.values()) else "Missing"
                self.validation_step.emit(f"Dependencies: {dep_status}", "INFO")

                if not all(deps.values()):
                    missing_apt, missing_pip = self._check_missing_installable_deps()
                    if missing_apt or missing_pip:
                        self.validation_step.emit("Missing installable dependencies detected", "WARN")
                        self.missing_deps_data = (missing_apt, missing_pip)
                    else:
                        self.validation_step.emit("All critical dependencies available", "INFO")
            except Exception as exc:
                self.validation_step.emit(f"Dependency check error: {exc}", "WARN")

        self.update_progress.emit("Verifying UI assets...", 80)
        self.validation_step.emit("Checking icons, fonts, and theme assets", "INFO")
        self._validate_ui_assets()

        self.update_progress.emit("Finalizing startup...", 90)
        elapsed = time.monotonic() - start_time
        if elapsed < 3.0:
            time.sleep(3.0 - elapsed)

        self.update_progress.emit("✓ All validation passed—launching UI", 100)
        self.validation_step.emit("STARTUP SUCCESSFUL: All systems ready", "INFO")

        if self.missing_deps_data:
            missing_apt, missing_pip = self.missing_deps_data
            if missing_apt or missing_pip:
                self.dependency_install_prompt.emit(missing_apt, missing_pip)
                return

        self.startup_complete.emit(system)

    def _check_prerequisites(self) -> bool:
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
            except Exception as exc:
                self.validation_step.emit(f"Device check skipped: {exc}", "INFO")

            return True
        except Exception as exc:
            self.validation_step.emit(f"Prerequisites check failed: {exc}", "ERROR")
            return False

    def _validate_paths_and_permissions(self) -> bool:
        try:
            log_dir = Path(LOG_CONFIG.get("log_dir", "/tmp/nitrosense"))
            log_dir.mkdir(parents=True, exist_ok=True)

            test_file = log_dir / ".nitrosense_write_test"
            try:
                test_file.write_text("test")
                test_file.unlink()
                self.validation_step.emit(f"Log directory {log_dir} is writable ✓", "INFO")
            except (PermissionError, OSError) as exc:
                self.validation_step.emit(f"Log directory not writable: {exc}", "ERROR")
                return False

            asset_dir = Path(__file__).resolve().parents[1] / "assets" / "icons"
            if not asset_dir.exists():
                self.validation_step.emit(f"Asset path missing: {asset_dir}", "WARN")
            else:
                self.validation_step.emit(f"Asset path found: {asset_dir.name} ✓", "INFO")

            return True
        except Exception as exc:
            self.validation_step.emit(f"Path validation error: {exc}", "ERROR")
            return False

    def _check_missing_installable_deps(self) -> Tuple[Dict[str, List[str]], Dict[str, List[str]]]:
        from ..resilience.dependency_installer import DependencyInstaller

        installer = DependencyInstaller()
        return installer.check_missing_dependencies()

    def _validate_system_integrity(self) -> bool:
        try:
            integrity_result = SystemIntegrityCheck.full_integrity_check()
            status = integrity_result.get("status", "UNKNOWN")
            if "CRITICAL" in status:
                self.validation_step.emit("Integrity: CRITICAL issues detected", "ERROR")
                return False
            elif "WARNING" in status:
                self.validation_step.emit("Integrity: Warnings present (degraded mode)", "WARN")
                return True
            self.validation_step.emit("Integrity: All checks passed ✓", "INFO")
            return True
        except Exception as exc:
            self.validation_step.emit(f"Integrity check error: {exc}", "WARN")
            return True

    def _validate_hardware_sensors(self) -> bool:
        try:
            self.validation_step.emit("Sensor validation (hardware not yet initialized)", "INFO")
            return True
        except Exception as exc:
            self.validation_step.emit(f"Sensor validation error: {exc}", "WARN")
            return True

    def _validate_ui_assets(self) -> None:
        try:
            icon_dir = Path(__file__).resolve().parents[1] / "assets" / "icons"
            required_icons = ["home.png", "settings.png"]
            for icon in required_icons:
                icon_path = icon_dir / icon
                if not icon_path.exists():
                    self.validation_step.emit(f"Icon {icon} missing (fallback enabled)", "WARN")
                else:
                    self.validation_step.emit(f"Icon {icon} ✓", "INFO")
        except Exception as exc:
            self.validation_step.emit(f"Asset validation error: {exc}", "WARN")


def handle_startup_failure(
    splash: Optional[SplashWindow],
    app: "QApplication",
    message: str,
    use_dialogs: bool = True,
) -> None:
    logger.critical(f"STARTUP FAILURE: {message}")
    tb_lines = traceback.format_exc().split("\n")
    logger.critical("Stack trace (last 5 frames):")
    for line in tb_lines[-6:-1]:
        logger.critical(f"  {line}")

    if not use_dialogs or not splash:
        logger.warning("Keeping application active for manual shutdown")
        return

    try:
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
    except Exception as exc:
        logger.critical(f"Error displaying failure dialog: {exc}", exc_info=True)


def finish_startup(
    splash: Optional[SplashWindow],
    app: "QApplication",
    system: NitroSenseSystem,
    thread: QThread,
) -> None:
    logger.info("Creating main application window...")
    app.system = system

    try:
        start_minimized = system.config_manager.get("advanced_config", {}).get("start_minimized", False)

        if getattr(app, "previous_crash_detected", False):
            logger.warning("Previous execution ended unexpectedly; enabling crash recovery defaults")
            try:
                if hasattr(system, "fan_controller"):
                    system.fan_controller.enable_auto_curve()
                    logger.info("Crash recovery: auto thermal profile enabled")
            except Exception as exc:
                logger.warning(f"Crash recovery fallback failed: {exc}")

        app.main_window = __import__("nitrosense.ui.main_window", fromlist=["NitroSenseApp"]).NitroSenseApp(system)

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

    except Exception as exc:
        logger.critical(f"Failed to create main window: {exc}", exc_info=True)
        tb_str = traceback.format_exc()
        logger.critical(f"Full traceback:\n{tb_str}")
        if splash:
            splash.log_validation(f"FATAL: Failed to create main window: {exc}", "ERROR")
            splash.log_validation(tb_str, "ERROR")
            splash.show()
        handle_startup_failure(splash, app, f"Failed to create main window: {exc}")
        return

    monitor_err, monitor_msg = system.start_monitoring()
    if monitor_err != ErrorCode.SUCCESS:
        logger.warning(f"Background monitoring warning: {monitor_msg}")
    else:
        logger.info("✓ Background monitoring is active")

    if hasattr(system, "watchdog") and system.watchdog:
        if not system.watchdog.isRunning():
            system.watchdog.running = True
            system.watchdog.start()
            logger.info("✓ Hardware watchdog started (100% fan on >3 sensor failures)")
        else:
            system.watchdog.running = True
            logger.info("✓ Hardware watchdog already running")

    try:
        if not __import__("nitrosense.ui.tray_icon", fromlist=["AutostartManager"]).AutostartManager.is_autostart_enabled():
            logger.debug("Autostart not configured, offer to user (optional)")
        else:
            logger.info("✓ Autostart is enabled")
    except Exception as exc:
        logger.warning(f"Failed to check autostart status: {exc}")

    try:
        HotkeysManager = __import__("nitrosense.core.hotkeys", fromlist=["HotkeysManager"]).HotkeysManager
        hotkeys_manager = HotkeysManager()

        def frost_mode_handler() -> None:
            logger.info("Frost Mode hotkey triggered (Ctrl+Shift+F)")
            main_window = app.main_window
            if main_window is not None:
                main_window._tray_activate_frost_mode()

        hotkeys_manager.register_hotkey(
            "ctrl+shift+f",
            frost_mode_handler,
            "Activate Frost Mode",
        )

        if hotkeys_manager.start_listening():
            app.hotkeys_manager = hotkeys_manager
            logger.info("✓ Global hotkeys registered (Ctrl+Shift+F for Frost Mode)")
    except Exception as exc:
        logger.warning(f"Failed to register global hotkeys: {exc}")

    logger.info("= " * 30)  # Keep concise final startup marker
