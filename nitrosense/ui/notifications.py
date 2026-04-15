"""
Toast Notification System for NitroSense Ultimate.

FEATURE #3: Notificações Toast
MOTIVO: Alertas críticos precisam ser visíveis e não-intrusivos simultaneamente.
- Floats acima de tudo sem bloquear interação
- Auto-dismissível (5s) reduz fadiga do usuário
- Stack vertical economiza espaço vs. múltiplas modais
- Cores por severidade (vermelho=crítico, amarelo=warning) para reconhecimento rápido
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, QTimer, QPoint, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from typing import Optional, List
from ..core.constants import COLOR_SCHEME, THERMAL_CONFIG
from ..core.logger import logger


class ToastNotification(QWidget):
    """Individual toast notification widget."""
    
    closed = pyqtSignal()
    
    def __init__(
        self, 
        message: str, 
        severity: str = "info",  # info, warning, critical
        duration: int = 2000,  # milliseconds
        parent: Optional[QWidget] = None
    ):
        """
        Initialize toast notification.
        
        Args:
            message: Notification text
            severity: One of info/warning/critical
            duration: Display duration in ms
            parent: Parent widget
        """
        super().__init__(parent)
        self.message = message
        self.severity = severity
        self.duration = duration
        
        # Styling
        self._init_ui()
        self._setup_timer()
        
        logger.debug(f"Toast notification created: {severity} - {message}")
    
    def _init_ui(self) -> None:
        """Initialize UI."""
        # Colors based on severity
        severity_colors = {
            "info": COLOR_SCHEME["primary"],
            "warning": COLOR_SCHEME["warning"],
            "critical": COLOR_SCHEME["danger"],
        }
        
        bg_colors = {
            "info": "#1a3a52",     # Dark blue tint
            "warning": "#523a1a",  # Dark orange tint
            "critical": "#521a1a", # Dark red tint
        }
        
        bg_color = bg_colors.get(self.severity, bg_colors["info"])
        text_color = severity_colors.get(self.severity, COLOR_SCHEME["primary"])
        
        # Window properties
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        
        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 12)
        
        # Message label
        label = QLabel(self.message)
        label.setFont(QFont("Segoe UI", 10, QFont.Weight.Normal))
        label.setStyleSheet(f"""
            color: {text_color};
            background-color: {bg_color};
            border-left: 4px solid {text_color};
            padding: 10px;
            border-radius: 12px;
        """)
        label.setWordWrap(True)
        label.setMaximumWidth(350)
        layout.addWidget(label)
        
        self.setStyleSheet(f"background-color: transparent;")
        self.adjustSize()
    
    def _setup_timer(self) -> None:
        """Setup auto-close timer."""
        self.close_timer = QTimer()
        self.close_timer.timeout.connect(self.fadeout_and_close)
        self.close_timer.start(self.duration)
    
    def fadeout_and_close(self) -> None:
        """Fade out and close the notification."""
        self.close()
        self.closed.emit()


class ToastManager:
    """
    Manages toast notification lifecycle and positioning.
    
    FEATURE #1: Dashboard Customizável (partial)
    Also helps organize notifications in customizable stack positions.
    """
    
    def __init__(self, parent_window: QWidget):
        """
        Initialize toast manager.
        
        Args:
            parent_window: Main application window
        """
        self.parent = parent_window
        self.active_toasts: List[ToastNotification] = []
        self.max_toasts = 5  # Max simultaneous notifications
        self.toast_offset = 60  # pixels between toasts
        self.start_position = QPoint(
            parent_window.width() - 370,  # Right side, 20px margin
            20  # Top, 20px margin
        )
        
        logger.info("ToastManager initialized")
    
    def show_toast(
        self, 
        message: str, 
        severity: str = "info",
        duration: int = 5000
    ) -> None:
        """
        Show a toast notification.
        
        Args:
            message: Notification text
            severity: Severity level (info/warning/critical)
            duration: Display duration in milliseconds
        """
        # Limit concurrent toasts
        if len(self.active_toasts) >= self.max_toasts:
            self.active_toasts.pop(0).close()
        
        toast = ToastNotification(message, severity, duration, self.parent)
        toast.closed.connect(lambda: self._on_toast_closed(toast))
        
        # Position toast
        y_pos = self.start_position.y() + (len(self.active_toasts) * self.toast_offset)
        toast.move(self.start_position.x(), y_pos)
        
        self.active_toasts.append(toast)
        toast.show()
        
        logger.debug(f"Toast shown: {len(self.active_toasts)} active")
    
    def _on_toast_closed(self, toast: ToastNotification) -> None:
        """
        Handle toast closure and reposition remaining toasts.
        
        Args:
            toast: The toast that was closed
        """
        if toast in self.active_toasts:
            self.active_toasts.remove(toast)
            self._reposition_toasts()
    
    def _reposition_toasts(self) -> None:
        """Reposition remaining toasts after one closes."""
        for i, toast in enumerate(self.active_toasts):
            y_pos = self.start_position.y() + (i * self.toast_offset)
            toast.move(self.start_position.x(), y_pos)
    
    def clear_all(self) -> None:
        """Clear all active toasts."""
        for toast in self.active_toasts:
            toast.close()
        self.active_toasts.clear()
