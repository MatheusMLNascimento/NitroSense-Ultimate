"""
Log Viewer Dialog

Provides a standalone dialog to display and monitor the current log file.
Useful for debugging and user support.
"""

from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QPushButton,
    QPlainTextEdit,
    QVBoxLayout,
)
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QTextCursor


class LogViewerDialog(QDialog):
    """
    Standalone dialog to show current log file contents in a terminal-like view.
    
    Features:
        - Auto-refreshes every 1 second
        - Shows last 50KB of log file (prevents memory issues)
        - Copy all logs to clipboard
        - Styled with dark terminal aesthetic
        
    Examples:
        >>> from pathlib import Path
        >>> log_path = Path.home() / ".local/share/nitrosense/nitrosense.log"
        >>> dialog = LogViewerDialog(log_path)
        >>> dialog.exec()
    """

    def __init__(self, log_path: Path, parent=None) -> None:
        """
        Initialize the log viewer dialog.
        
        Args:
            log_path: Path to the log file to display
            parent: Parent widget
        """
        super().__init__(parent)
        self.log_path = log_path
        self.setWindowTitle("NitroSense Logs")
        self.setModal(False)
        self.resize(760, 520)

        # Main layout
        layout = QVBoxLayout(self)
        
        # Text viewer
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

        # Auto-refresh timer
        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(1000)  # 1 second
        self.refresh_timer.timeout.connect(self.refresh)
        self.refresh_timer.start()

        # Button layout
        button_layout = QHBoxLayout()
        refresh_button = QPushButton("Refresh", self)
        copy_button = QPushButton("Copy all", self)
        button_layout.addWidget(refresh_button)
        button_layout.addStretch()
        button_layout.addWidget(copy_button)
        layout.addLayout(button_layout)

        # Connect buttons
        refresh_button.clicked.connect(self.refresh)
        copy_button.clicked.connect(self.copy_all)

        # Initial load
        self.refresh()

    def refresh(self) -> None:
        """
        Refresh the log viewer by reading the log file.
        
        Handles missing files and encoding errors gracefully.
        Only shows last 50KB to prevent memory issues.
        """
        try:
            # Read log file
            content = self.log_path.read_text(encoding="utf-8", errors="replace")
            
            # Limit to last 50KB to prevent memory issues
            if len(content) > 50000:
                content = "...(truncated - showing last 50KB)...\n" + content[-50000:]
            
            self.viewer.setPlainText(content)
            # Scroll to end
            self.viewer.moveCursor(QTextCursor.MoveOperation.End)
        except (OSError, UnicodeError) as exc:
            self.viewer.setPlainText(f"Unable to read log file: {exc}")

    def copy_all(self) -> None:
        """
        Copy all log content to clipboard.
        
        Examples:
            >>> dialog = LogViewerDialog(log_path)
            >>> dialog.copy_all()  # Copies all text to clipboard
        """
        self.viewer.selectAll()
        self.viewer.copy()
