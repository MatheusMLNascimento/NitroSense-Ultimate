"""
Global exception handler and error diagnostics for NitroSense Ultimate.
Captures all unhandled exceptions and displays them in a custom dialog.
"""

import sys
import traceback
from PyQt6.QtWidgets import QMessageBox, QTextEdit, QVBoxLayout, QDialog, QLabel
from PyQt6.QtCore import Qt
from .logger import logger


class ErrorDialog(QDialog):
    """Custom error dialog displaying full traceback."""

    def __init__(self, exc_type, exc_value, exc_traceback, parent=None):
        super().__init__(parent)
        self.setWindowTitle("NitroSense - Fatal Error")
        self.setGeometry(100, 100, 800, 600)
        self.setStyleSheet(
            "QDialog { background-color: #1e1e1e; color: white; border-radius: 16px; }"
            "QTextEdit { background-color: #2d2d2d; color: #ff6b6b; font-family: 'Courier New'; border-radius: 12px; }"
            "QPushButton { background-color: #007aff; color: white; padding: 10px; border-radius: 12px; }"
        )

        layout = QVBoxLayout()

        # Error message summary
        summary = f"<b>Error Type:</b> {exc_type.__name__}<br>"
        summary += f"<b>Message:</b> {str(exc_value)}"

        summary_label = self._create_label(summary, "#ff6b6b")
        layout.addWidget(summary_label)

        # Traceback text area
        traceback_text = QTextEdit()
        traceback_text.setReadOnly(True)
        traceback_text.setText(
            "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        )
        layout.addWidget(traceback_text)

        # Buttons
        button_layout = self._create_buttons()
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def _create_label(self, text, color):
        """Create a colored label."""
        from PyQt6.QtWidgets import QLabel
        label = QLabel(text)
        label.setStyleSheet(f"color: {color}; font-weight: bold;")
        return label

    def _create_buttons(self):
        """Create action buttons."""
        from PyQt6.QtWidgets import QPushButton, QHBoxLayout

        layout = QHBoxLayout()

        restart_btn = QPushButton("Restart Module")
        restart_btn.clicked.connect(self.restart_module)

        ignore_btn = QPushButton("Ignore & Continue")
        ignore_btn.clicked.connect(self.accept)

        exit_btn = QPushButton("Exit")
        exit_btn.clicked.connect(sys.exit)

        layout.addWidget(restart_btn)
        layout.addWidget(ignore_btn)
        layout.addWidget(exit_btn)

        return layout

    def restart_module(self):
        """Restart the main application module."""
        logger.warning("User initiated module restart")
        self.accept()
        # Triggering restart signal should be handled by main app


def setup_exception_handler(use_dialogs: bool = True):
    """
    Install global exception handler for NitroSense.
    If use_dialogs is False, errors are logged to stderr instead of shown.
    """

    def handle_exception(exc_type, exc_value, exc_traceback):
        """Global exception handler callback."""

        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        logger.critical(
            "Unhandled exception",
            exc_info=(exc_type, exc_value, exc_traceback),
        )

        if not use_dialogs:
            sys.stderr.write(
                "Unhandled exception: "
                + "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
            )
            return

        dialog = ErrorDialog(exc_type, exc_value, exc_traceback)
        dialog.exec()

    sys.excepthook = handle_exception
    logger.info(f"Global exception handler installed (use_dialogs={use_dialogs})")
