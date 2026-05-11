"""
Widget Builders and UX Utilities for NitroSense Ultimate UI.
Consolidates button building, debounced sliders, loading states, and feedback components.
"""

from typing import Optional, Callable, Any
from PyQt6.QtWidgets import QPushButton, QWidget, QSlider
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QColor
import time


class ButtonBuilder:
    """Factory for creating styled buttons with actions."""

    @staticmethod
    def create(
        text: str,
        preset: str = "primary",
        action: Optional[Callable] = None,
        action_args: Optional[tuple] = None,
        parent: Optional[QWidget] = None,
        icon: Optional[str] = None
    ) -> QPushButton:
        """
        Create a styled button.

        Args:
            text: Button text
            preset: Style preset ("primary", "secondary", "danger")
            action: Function to call when clicked
            action_args: Arguments to pass to action
            parent: Parent widget
            icon: Icon path or Base64 data

        Returns:
            Configured QPushButton
        """
        button = QPushButton(text, parent)

        # Apply style based on preset
        ButtonBuilder._apply_style(button, preset)

        # Set icon if provided
        if icon:
            # Implementation for icon setting
            pass

        # Connect action if provided
        if action:
            if action_args:
                button.clicked.connect(lambda: action(*action_args))
            else:
                button.clicked.connect(action)

        return button

    @staticmethod
    def _apply_style(button: QPushButton, preset: str):
        """Apply style preset to button."""
        base_style = """
            QPushButton {
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: 500;
                font-size: 14px;
            }
        """

        if preset == "primary":
            button.setStyleSheet(base_style + """
                QPushButton {
                    background-color: #0078d4;
                    color: white;
                    border: none;
                }
                QPushButton:hover {
                    background-color: #106ebe;
                }
                QPushButton:pressed {
                    background-color: #005a9e;
                }
            """)
        elif preset == "secondary":
            button.setStyleSheet(base_style + """
                QPushButton {
                    background-color: #f3f2f1;
                    color: #323130;
                    border: 1px solid #d2d0ce;
                }
                QPushButton:hover {
                    background-color: #edebe9;
                }
                QPushButton:pressed {
                    background-color: #e1dfdd;
                }
            """)
        elif preset == "danger":
            button.setStyleSheet(base_style + """
                QPushButton {
                    background-color: #d13438;
                    color: white;
                    border: none;
                }
                QPushButton:hover {
                    background-color: #c42b2f;
                }
                QPushButton:pressed {
                    background-color: #a72024;
                }
            """)


class DebouncedSlider(QSlider):
    """
    QSlider with automatic debouncing.
    Prevents multiple valueChanged emissions during user interaction.

    Emits `value_ready` signal only after 300ms of inactivity.
    """

    value_ready = pyqtSignal(int)  # Emitted after debounce delay

    def __init__(self, orientation=Qt.Orientation.Horizontal, debounce_ms: int = 300, parent=None):
        super().__init__(orientation, parent)
        self.debounce_ms = debounce_ms
        self.debounce_timer = QTimer()
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.timeout.connect(self._on_debounce_timeout)

        # Connect to value changes
        self.sliderMoved.connect(self._on_slider_moved)
        self.valueChanged.connect(self._on_value_changed)

    def _on_slider_moved(self):
        """Called when user drags the slider."""
        self.debounce_timer.stop()
        self.debounce_timer.start(self.debounce_ms)

    def _on_value_changed(self):
        """Called when value changes (from any source)."""
        self.debounce_timer.stop()
        self.debounce_timer.start(self.debounce_ms)

    def _on_debounce_timeout(self):
        """Emit the debounced value."""
        self.value_ready.emit(self.value())


class LoadingButton(QPushButton):
    """
    QPushButton with loading states.
    Shows loading animation and disables interaction during async operations.
    """

    def __init__(self, text: str = "", parent: Optional[QWidget] = None):
        super().__init__(text, parent)
        self.original_text = text
        self.is_loading = False
        self.loading_dots = 0
        self.loading_timer = QTimer()
        self.loading_timer.timeout.connect(self._update_loading_text)

    def set_loading(self, loading: bool, loading_text: str = "Loading"):
        """
        Set loading state.

        Args:
            loading: Whether to show loading state
            loading_text: Text to show during loading
        """
        self.is_loading = loading
        self.setEnabled(not loading)

        if loading:
            self.loading_dots = 0
            self.loading_timer.start(500)  # Update every 500ms
            self._update_loading_text()
        else:
            self.loading_timer.stop()
            self.setText(self.original_text)

    def _update_loading_text(self):
        """Update loading text with animated dots."""
        self.loading_dots = (self.loading_dots + 1) % 4
        dots = "." * self.loading_dots
        self.setText(f"Loading{dots}")


class PulseAnimation:
    """
    Pulsing effect animation for widgets.
    Creates a breathing effect by animating opacity or color.
    """

    def __init__(self, widget: QWidget, color: QColor = QColor(0, 120, 212)):
        self.widget = widget
        self.color = color
        self.animation = QPropertyAnimation(widget, b"styleSheet")
        self.animation.setDuration(1000)  # 1 second cycle
        self.animation.setLoopCount(-1)  # Infinite loop
        self.animation.setEasingCurve(QEasingCurve.Type.InOutSine)

        # Create pulsing effect by changing background color opacity
        self._setup_animation()

    def _setup_animation(self):
        """Setup the pulsing animation."""
        base_style = self.widget.styleSheet()
        pulse_style = f"""
            {base_style}
            background-color: rgba({self.color.red()}, {self.color.green()}, {self.color.blue()}, 0.3);
        """
        self.animation.setKeyValueAt(0, base_style)
        self.animation.setKeyValueAt(0.5, pulse_style)
        self.animation.setKeyValueAt(1, base_style)

    def start(self):
        """Start the pulsing animation."""
        self.animation.start()

    def stop(self):
        """Stop the pulsing animation."""
        self.animation.stop()
        # Reset to original style
        self.widget.setStyleSheet(self.widget.styleSheet())


class FeedbackToast(QWidget):
    """
    Visual feedback toast for command confirmations.
    Shows temporary success/error messages with animations.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.hide_timer = QTimer()
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.hide)

        # Animation for fade in/out
        self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(300)

    def show_feedback(self, message: str, success: bool = True, duration: int = 2000):
        """
        Show feedback toast.

        Args:
            message: Message to display
            success: Whether it's a success message
            duration: How long to show (ms)
        """
        # Set style based on success
        if success:
            self.setStyleSheet("""
                background-color: rgba(0, 120, 212, 0.9);
                color: white;
                border-radius: 8px;
                padding: 12px 16px;
                font-size: 14px;
            """)
        else:
            self.setStyleSheet("""
                background-color: rgba(209, 52, 56, 0.9);
                color: white;
                border-radius: 8px;
                padding: 12px 16px;
                font-size: 14px;
            """)

        # Position near parent or center of screen
        if self.parent():
            parent_rect = self.parent().geometry()
            self.move(
                parent_rect.center().x() - self.width() // 2,
                parent_rect.center().y() - self.height() // 2
            )

        # Set text and show
        self.setText(message)
        self.adjustSize()

        # Fade in
        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.start()
        self.show()

        # Auto-hide after duration
        self.hide_timer.start(duration)

    def hideEvent(self, event):
        """Override to fade out when hiding."""
        if self.fade_animation.state() == QPropertyAnimation.State.Running:
            self.fade_animation.stop()
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.0)
        self.fade_animation.start()
        super().hideEvent(event)