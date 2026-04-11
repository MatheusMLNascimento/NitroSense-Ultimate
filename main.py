"""
Main Entry Point - NitroSense Ultimate Application
Initializes all systems and launches the UI
"""

import sys
import time
import threading
import argparse
from pathlib import Path

# Ensure we can import from the package
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging

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
    QWidget,
    QSplashScreen,
)
from PyQt6.QtGui import QColor, QFont, QTextCursor, QPixmap
from PyQt6.QtCore import Qt, QTimer, QObject, QThread, pyqtSignal, QCoreApplication

from nitrosense.core.logger import setup_logging, logger
from nitrosense.core.error_handler import setup_exception_handler
from nitrosense.core.error_codes import ErrorCode, is_critical, get_error_description
from nitrosense.core.constants import APP_CONFIG, DEVICE_VALIDATION, LOG_CONFIG
from nitrosense.resilience.system_integrity import SystemIntegrityCheck
from nitrosense.system import NitroSenseSystem
from nitrosense.ui.main_window import NitroSenseApp


class LogSignalEmitter(QObject):
    """Emitter used to safely append log messages on the Qt main thread."""

    message_ready = pyqtSignal(str)


class QtSplashLogHandler(logging.Handler):
    """Logger handler that writes startup logs into the splash terminal view."""

    def __init__(self, widget):
        super().__init__()
        self.widget = widget
        self.signal_emitter = LogSignalEmitter()
        self.signal_emitter.message_ready.connect(self._append)
        self.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ))

    def emit(self, record):
        try:
            message = self.format(record)
            if self.widget:
                self.signal_emitter.message_ready.emit(message)
        except Exception:
            self.handleError(record)

    def _append(self, message: str) -> None:
        self.widget.appendPlainText(message)
        cursor = self.widget.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.widget.setTextCursor(cursor)


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


class SplashWindow(QWidget):
    """Resizable splash window with an embedded terminal view."""

    def __init__(self, log_path: Path):
        super().__init__()
        self.setWindowTitle("NitroSense Ultimate - Starting")
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.resize(1000, 700)  # Increased size
        self.setMinimumSize(800, 600)  # Minimum size for resizability
        self.setStyleSheet("background-color: #141414;")  # MacOS dark theme

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        self.title_label = QLabel("NitroSense Ultimate")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setFont(QFont("Segoe UI", 18, QFont.Weight.DemiBold))
        self.title_label.setStyleSheet("color: #00d1ff;")
        layout.addWidget(self.title_label)

        self.message_label = QLabel("Preparing your system...")
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message_label.setFont(QFont("Segoe UI", 11))
        self.message_label.setStyleSheet("color: #d1f2ff;")
        layout.addWidget(self.message_label)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet(
            "QProgressBar {"
            "  border: 1px solid #444;"
            "  border-radius: 9px;"
            "  background: #20232a;"
            "  color: #00d1ff;"
            "}"
            "QProgressBar::chunk {"
            "  background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00d1ff, stop:1 #70e0ff);"
            "  border-radius: 9px;"
            "}"
        )
        layout.addWidget(self.progress_bar)

        self.terminal = QPlainTextEdit(self)
        self.terminal.setReadOnly(True)
        self.terminal.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.terminal.setStyleSheet(
            "QPlainTextEdit {"
            "  font-family: 'Courier New';"
            "  font-size: 11px;"  # Font size 11
            "  background: #11151b;"
            "  color: #d1f2ff;"
            "  border: 1px solid #2f3a4a;"
            "  border-radius: 12px;"
            "  padding: 10px;"
            "}"
        )
        self.terminal.setMinimumHeight(300)  # Increased height
        layout.addWidget(self.terminal, 1)

        button_layout = QHBoxLayout()
        self.copy_button = QPushButton("Copy Terminal", self)
        self.copy_button.setStyleSheet(
            "QPushButton {"
            "  color: #ffffff;"
            "  background: #2d2d34;"
            "  border-radius: 10px;"
            "  padding: 8px 14px;"
            "}"
            "QPushButton:hover {"
            "  background: #3f4b5b;"
            "}"
        )
        self.copy_button.clicked.connect(self.copy_terminal)
        button_layout.addWidget(self.copy_button)
        button_layout.addStretch()
        self.quit_button = QPushButton("Quit", self)
        self.quit_button.setStyleSheet(
            "QPushButton {"
            "  color: #ffffff;"
            "  background: #2d2d34;"
            "  border-radius: 10px;"
            "  padding: 8px 14px;"
            "}"
            "QPushButton:hover {"
            "  background: #3f4b5b;"
            "}"
        )
        self.quit_button.clicked.connect(QApplication.instance().quit)
        button_layout.addWidget(self.quit_button)
        layout.addLayout(button_layout)

        self.log_dialog = LogViewerDialog(log_path, self)

    def copy_terminal(self) -> None:
        self.terminal.selectAll()
        self.terminal.copy()

    def show_error_logs(self) -> None:
        try:
            self.log_dialog.refresh()
            self.log_dialog.show()
            self.log_dialog.raise_()
            self.raise_()
        except Exception as exc:
            logger.error(f"Failed opening log dialog: {exc}", exc_info=True)


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


def create_splash_screen(app: QApplication) -> SplashWindow:
    log_path = Path(LOG_CONFIG["log_dir"]) / LOG_CONFIG["log_file"]
    splash = SplashWindow(log_path)

    splash.log_handler = QtSplashLogHandler(splash.terminal)
    logger.addHandler(splash.log_handler)
    logger.info("Splash screen terminal log handler attached.")

    splash.show()
    app.processEvents()

    return splash


def update_splash(splash: SplashWindow | None, app: QApplication, message: str, value: int) -> None:
    """Update splash text and progress bar."""
    if not splash:
        return
    try:
        if hasattr(splash, "message_label"):
            splash.message_label.setText(message)
        if hasattr(splash, "progress_bar"):
            splash.progress_bar.setValue(value)
    except Exception as exc:
        logger.error(f"Failed updating splash screen: {exc}", exc_info=True)


class StartupWorker(QObject):
    update_progress = pyqtSignal(str, int)
    startup_failed = pyqtSignal(str)
    startup_complete = pyqtSignal(object)

    def run(self) -> None:
        try:
            self.perform_startup()
        except Exception as exc:
            self.startup_failed.emit(f"Startup error: {exc}")
        finally:
            pass

    def perform_startup(self) -> None:
        start_time = time.monotonic()

        self.update_progress.emit("Verifying prerequisites...", 10)
        if not check_prerequisites():
            self.startup_failed.emit("System prerequisites check failed.")
            return

        self.update_progress.emit("Initializing NitroSense subsystems...", 25)
        logger.info("Running system integrity checks...")
        try:
            integrity_result = SystemIntegrityCheck.full_integrity_check()
            logger.info(f"Integrity report: {integrity_result.get('status', 'UNKNOWN')}")

            if "CRITICAL" in integrity_result.get("status", ""):
                self.update_progress.emit("System Integrity Issues — degraded mode...", 35)
            else:
                self.update_progress.emit("System integrity OK", 35)
        except Exception as e:
            logger.warning(f"Integrity check error: {e}")
            self.update_progress.emit("Integrity check warning...", 35)

        logger.info("Initializing integrated system...")
        system = NitroSenseSystem()

        self.update_progress.emit("Bootstrapping system modules...", 50)
        err, bootstrap_msg = system.bootstrap()

        if err != ErrorCode.SUCCESS:
            logger.error(f"Bootstrap failed: {get_error_description(err)}")
            if is_critical(err):
                self.startup_failed.emit(
                    f"Critical bootstrap failed: {get_error_description(err)}"
                )
                return
            logger.warning(f"Non-critical bootstrap error, continuing: {bootstrap_msg}")

        self.update_progress.emit("Verifying hardware dependencies...", 70)
        if getattr(system, "hardware_manager", None):
            deps = system.hardware_manager.check_dependencies()
            dep_status = "OK" if all(deps.values()) else "Missing"
            logger.info(f"Dependency status: {deps}")
            self.update_progress.emit(f"Dependencies: {dep_status}", 75)

        self.update_progress.emit("Finalizing startup...", 90)
        elapsed = time.monotonic() - start_time
        if elapsed < 5.0:
            time.sleep(5.0 - elapsed)

        self.update_progress.emit("Ready — opening interface", 100)
        self.startup_complete.emit(system)


def handle_startup_failure(
    splash: SplashWindow | None,
    app: QCoreApplication | QApplication,
    message: str,
    use_dialogs: bool = True,
) -> None:
    logger.critical(message)

    if not use_dialogs:
        logger.warning("Startup failed in background mode; keeping application active for manual shutdown.")
        return

    if not splash:
        return

    from PyQt6.QtWidgets import QMessageBox
    QMessageBox.critical(
        None,
        "NitroSense - Initialization Failed",
        f"{message}\n\nCheck the logs below for details.",
    )
    if hasattr(splash, "progress_bar"):
        splash.progress_bar.hide()
    splash.show_error_logs()
    update_splash(splash, app, "Startup failed — log viewer opened.", 100)


def finish_startup(
    splash: SplashWindow | None,
    app: QApplication,
    system: NitroSenseSystem,
    thread: QThread,
) -> None:
    logger.info("Creating main window...")

    try:
        start_minimized = system.config_manager.get("advanced_config", {}).get("start_minimized", False)
        app.main_window = NitroSenseApp(system) # <--- Referência persistente

        if start_minimized:
            app.main_window.show()
            app.main_window.showMinimized()
        else:
            app.main_window.show()

        if splash:
            splash.close()

    except Exception as e:
        logger.critical(f"Failed to create main window: {e}", exc_info=True)
        if splash:
            # Keep splash active on error
            splash.message_label.setText("Startup failed - check logs")
            splash.show_error_logs()
            # Don't close splash
        else:
            # Fallback if no splash
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(None, "NitroSense - Startup Failed", f"Failed to create main window: {e}")

    monitor_err, monitor_msg = system.start_monitoring()
    if monitor_err != ErrorCode.SUCCESS:
        logger.warning(f"Background monitoring start warning: {monitor_msg}")
    else:
        logger.info("Background monitoring is active")

    logger.info("Application started successfully")
    logger.info("=" * 60)
    thread.quit()


def main():
    """Main application entry point."""

    args = parse_args()
    app = QApplication(sys.argv)
    setup_exception_handler(use_dialogs=True)

    def thread_exception_handler(args: threading.ExceptHookArgs) -> None:
        logger.critical(
            f"Unhandled thread exception: {args.exc_type.__name__}: {args.exc_value}",
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )

    threading.excepthook = thread_exception_handler

    def unraisable_exception_hook(unraisable):
        logger.error(
            f"Unraisable exception: {unraisable.exc_value}",
            exc_info=(getattr(unraisable, 'exc_type', None), getattr(unraisable, 'exc_value', None), getattr(unraisable, 'exc_traceback', None)),
        )

    sys.unraisablehook = unraisable_exception_hook

    splash = None
    use_splash = not args.no_splash

    if use_splash:
        try:
            splash = create_splash_screen(app)
        except Exception as exc:
            logger.critical(f"Failed to create splash screen: {exc}", exc_info=True)

    
    app.worker = StartupWorker()           # <--- Adicionado 'app.'
    app.startup_thread = QThread()         # <--- Adicionado 'app.'
    
    app.worker.moveToThread(app.startup_thread)
    
    app.worker.update_progress.connect(
        lambda msg, value: update_splash(splash, app, msg, value)
    )
    app.worker.startup_failed.connect(
        lambda reason: handle_startup_failure(splash, app, reason, use_dialogs=True)
    )
    app.worker.startup_complete.connect(
        lambda system: finish_startup(splash, app, system, app.startup_thread)
    )
    
    app.startup_thread.started.connect(app.worker.run)
    app.startup_thread.start()
    

    try:
        return app.exec()
    except Exception as exc:
        logger.critical("Unexpected Qt event loop failure.", exc_info=True)
        return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Fatal application error: {e}", exc_info=True)
        sys.exit(1)
