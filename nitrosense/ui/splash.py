"""
Splash Screen Module - NitroSense Ultimate
Handles pre-flight validation and startup splash screen.
"""

import sys
import traceback
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPlainTextEdit,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtGui import QColor, QFont, QTextCursor
from PyQt6.QtCore import Qt, QTimer, QObject, QThread, pyqtSignal

from nitrosense.core.logger import logger
from nitrosense.i18n import t


class QtSplashLogHandler:
    """Custom log handler that writes to splash screen terminal."""

    def __init__(self, terminal: QPlainTextEdit):
        self.terminal = terminal

    def emit(self, record):
        """Write log record to terminal."""
        try:
            msg = self.format(record)
            cursor = self.terminal.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.terminal.setTextCursor(cursor)
            self.terminal.insertPlainText(msg + '\n')
            self.terminal.ensureCursorVisible()
        except Exception:
            pass  # Silent fail during logging

    def format(self, record):
        """Format log record."""
        return f"[{record.levelname}] {record.getMessage()}"


class SplashWindow(QWidget):
    """
    Resizable splash window with pre-flight validation.
    Acts as the "Tester Supremo" - validates paths, permissions, assets, and sensors.
    UI only launches if splash emits validation_success signal.
    """

    validation_success = pyqtSignal()  # Emitted when all pre-flight checks pass
    validation_failed = pyqtSignal(str)  # Emitted with error message on failure

    def __init__(self, log_path: Path):
        super().__init__()
        self.log_path = log_path
        self.validation_errors = []
        self.log_handler: Optional[QtSplashLogHandler] = None

        self.setWindowTitle("NitroSense Ultimate—Tester Supremo")
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.resize(1000, 700)
        self.setMinimumSize(800, 600)
        self.setStyleSheet("background-color: #141414;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Title
        self.title_label = QLabel(t("NitroSense Ultimate"))
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setFont(QFont("Segoe UI", 18, QFont.Weight.DemiBold))
        self.title_label.setStyleSheet("color: #00d1ff;")
        layout.addWidget(self.title_label)

        # Subtitle
        self.subtitle = QLabel(t("Tester Supremo—System Validation"))
        self.subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.subtitle.setFont(QFont("Segoe UI", 10))
        self.subtitle.setStyleSheet("color: #888;")
        layout.addWidget(self.subtitle)

        # Status message
        self.message_label = QLabel(t("Validating system..."))
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message_label.setFont(QFont("Segoe UI", 11))
        self.message_label.setStyleSheet("color: #d1f2ff;")
        layout.addWidget(self.message_label)

        # Progress bar
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet(
            "QProgressBar {"
            "  border: 1px solid #444;"
            "  border-radius: 9px;"
            "  background: #20232a;"
            "}"
            "QProgressBar::chunk {"
            "  background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00d1ff, stop:1 #70e0ff);"
            "  border-radius: 9px;"
            "}"
        )
        layout.addWidget(self.progress_bar)

        # Terminal for logs
        self.terminal = QPlainTextEdit(self)
        self.terminal.setReadOnly(True)
        self.terminal.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.terminal.setStyleSheet(
            "QPlainTextEdit {"
            "  font-family: 'Courier New';"
            "  font-size: 11px;"
            "  background: #11151b;"
            "  color: #d1f2ff;"
            "  border: 1px solid #2f3a4a;"
            "  border-radius: 4px;"
            "  padding: 4px;"
            "}"
        )
        layout.addWidget(self.terminal)

        # Validation steps
        self.validation_steps = QLabel("")
        self.validation_steps.setFont(QFont("Segoe UI", 9))
        self.validation_steps.setStyleSheet("color: #888;")
        self.validation_steps.setWordWrap(True)
        layout.addWidget(self.validation_steps)

        # Show window
        self.show()

    def log_validation(self, message: str, status: str = "INFO") -> None:
        """Log a validation message to the terminal."""
        try:
            cursor = self.terminal.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.terminal.setTextCursor(cursor)
            self.terminal.insertPlainText(f"[{status}] {message}\n")
            self.terminal.ensureCursorVisible()
        except Exception:
            pass

    def update_progress(self, message: str, value: int) -> None:
        """Update progress bar and message."""
        try:
            self.message_label.setText(message)
            self.progress_bar.setValue(value)
        except Exception:
            pass

    def update_validation_steps(self, steps: str) -> None:
        """Update validation steps display."""
        try:
            self.validation_steps.setText(steps)
        except Exception:
            pass


def create_splash_screen(log_path: Path) -> SplashWindow:
    """Create and return a splash screen instance."""
    return SplashWindow(log_path)


def update_splash(splash: Optional[SplashWindow], message: str, value: int) -> None:
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


def log_validation_step(splash: Optional[SplashWindow], message: str, status: str = "INFO") -> None:
    """Log validation step to splash terminal."""
    if not splash or not hasattr(splash, 'log_validation'):
        logger.info(f"[{status}] {message}")
        return
    splash.log_validation(message, status)