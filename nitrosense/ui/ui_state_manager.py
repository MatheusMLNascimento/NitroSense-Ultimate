"""
UI State Manager for NitroSense Ultimate.
Consolidates window state persistence, dashboard customization, and UI configuration.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFrame, QLabel
from PyQt6.QtCore import Qt, pyqtSignal, QMimeData, QPoint
from PyQt6.QtGui import QFont, QDrag, QColor
import os

from ..core.logger import logger
from ..core.constants import APP_CONFIG, COLOR_SCHEME, CONFIG_DIRS


class WindowStateManager:
    """
    Manages window state persistence.

    Saves to ~/.config/nitrosense/window_state.json:
    - position x, y
    - size width, height
    - last active tab (index in stacked widget)
    - dark/light theme
    - maximization state
    """

    STATE_FILE = Path.home() / ".config" / "nitrosense" / "window_state.json"

    def __init__(self):
        """Initialize state manager."""
        self.state_file = self.STATE_FILE
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _atomic_write(path: Path, content: str) -> None:
        """Write content to disk atomically."""
        temp_path = path.parent / f"{path.name}.tmp"
        temp_path.write_text(content, encoding="utf-8")
        os.replace(temp_path, path)

    def save_window_state(self, window: QMainWindow) -> bool:
        """
        Save current window state to disk.

        Args:
            window: The main window to save state for

        Returns:
            True if saved successfully
        """
        try:
            geometry = window.geometry()
            state = {
                "x": geometry.x(),
                "y": geometry.y(),
                "width": geometry.width(),
                "height": geometry.height(),
                "maximized": window.isMaximized(),
                "theme": self._detect_theme(),
            }

            # Save current tab if available
            if hasattr(window, 'stacked_widget'):
                current_index = window.stacked_widget.currentIndex()
                state["current_tab"] = current_index

            self._atomic_write(self.state_file, json.dumps(state, indent=2))
            logger.debug(f"Window state saved: {state}")
            return True

        except Exception as e:
            logger.error(f"Failed to save window state: {e}")
            return False

    def restore_window_state(self, window: QMainWindow) -> bool:
        """
        Restore window state from disk.

        Args:
            window: The main window to restore state for

        Returns:
            True if restored successfully
        """
        try:
            if not self.state_file.exists():
                logger.debug("No window state file found, using defaults")
                return False

            with open(self.state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)

            # Restore geometry
            if not state.get("maximized", False):
                window.setGeometry(
                    state.get("x", 100),
                    state.get("y", 100),
                    state.get("width", 1200),
                    state.get("height", 800)
                )

            # Restore maximization
            if state.get("maximized", False):
                window.showMaximized()

            # Restore current tab
            if hasattr(window, 'stacked_widget') and "current_tab" in state:
                window.stacked_widget.setCurrentIndex(state["current_tab"])

            logger.debug(f"Window state restored: {state}")
            return True

        except Exception as e:
            logger.error(f"Failed to restore window state: {e}")
            return False

    def _detect_theme(self) -> str:
        """Detect system theme preference."""
        # Check KDE Plasma theme
        kde_theme = os.environ.get('QT_QPA_PLATFORMTHEME', '').lower()
        if 'breeze' in kde_theme or 'oxygen' in kde_theme:
            return "dark"  # KDE default is dark

        # Check GTK theme
        gtk_theme = os.environ.get('GTK_THEME', '').lower()
        if 'dark' in gtk_theme:
            return "dark"

        # Default to light
        return "light"


class DraggableWidget(QFrame):
    """
    A draggable widget component for dashboard customization.
    Supports drag-and-drop reordering on the home page.
    """

    def __init__(self, widget_id: str, title: str, content: QWidget):
        """
        Initialize draggable widget.

        Args:
            widget_id: Unique identifier for this widget
            title: Display title
            content: The actual content widget
        """
        super().__init__()
        self.widget_id = widget_id
        self.title = title
        self.content = content
        self.is_dragging = False
        self.drag_position: Optional[QPoint] = None

        self._setup_ui()

    def _setup_ui(self):
        """Setup the widget UI."""
        self.setFrameStyle(QFrame.Shape.Box)
        self.setStyleSheet(f"""
            DraggableWidget {{
                border: 1px solid {COLOR_SCHEME['border']};
                border-radius: 8px;
                background-color: {COLOR_SCHEME['surface']};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Title bar
        title_label = QLabel(self.title)
        title_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        title_label.setStyleSheet(f"color: {COLOR_SCHEME['text_primary']};")
        layout.addWidget(title_label)

        # Content
        layout.addWidget(self.content)

    def mousePressEvent(self, event):
        """Handle mouse press for drag start."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = True
            self.drag_position = event.position().toPoint()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Handle mouse move for dragging."""
        if self.is_dragging and self.drag_position:
            distance = (event.position().toPoint() - self.drag_position).manhattanLength()
            if distance > 10:  # Start drag after threshold
                self._start_drag()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Handle mouse release."""
        self.is_dragging = False
        self.drag_position = None
        self.setCursor(Qt.CursorShape.ArrowCursor)
        super().mouseReleaseEvent(event)

    def _start_drag(self):
        """Start the drag operation."""
        mime_data = QMimeData()
        mime_data.setText(self.widget_id)

        drag = QDrag(self)
        drag.setMimeData(mime_data)
        drag.setPixmap(self.grab())

        drag.exec(Qt.DropAction.MoveAction)


class DashboardCustomizer:
    """
    Customizable dashboard system for NitroSense Ultimate.

    Features:
    - Drag-and-drop widget reordering
    - Persistent layout configuration
    - Different priorities for different user types
    """

    def __init__(self, config_dir: Path = CONFIG_DIRS["user"]):
        self.config_dir = config_dir
        self.layout_file = config_dir / "dashboard_layout.json"
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def save_layout(self, widget_order: List[str]) -> bool:
        """
        Save dashboard layout to disk.

        Args:
            widget_order: List of widget IDs in current order

        Returns:
            True if saved successfully
        """
        try:
            layout_data = {
                "version": "1.0",
                "widget_order": widget_order,
                "timestamp": str(Path.home())
            }

            with open(self.layout_file, 'w', encoding='utf-8') as f:
                json.dump(layout_data, f, indent=2)

            logger.debug(f"Dashboard layout saved: {widget_order}")
            return True

        except Exception as e:
            logger.error(f"Failed to save dashboard layout: {e}")
            return False

    def load_layout(self) -> List[str]:
        """
        Load dashboard layout from disk.

        Returns:
            List of widget IDs in saved order, or default order if not found
        """
        try:
            if not self.layout_file.exists():
                return self._get_default_layout()

            with open(self.layout_file, 'r', encoding='utf-8') as f:
                layout_data = json.load(f)

            widget_order = layout_data.get("widget_order", [])
            if not widget_order:
                return self._get_default_layout()

            logger.debug(f"Dashboard layout loaded: {widget_order}")
            return widget_order

        except Exception as e:
            logger.error(f"Failed to load dashboard layout: {e}")
            return self._get_default_layout()

    def _get_default_layout(self) -> List[str]:
        """Get default widget layout."""
        return ["cpu_temp", "gpu_temp", "fan_speed", "thermal_gradient"]


class ApplicationStateManager:
    """
    Persists general application state (not just window).

    Saves:
    - Last active tab
    - Zoom level
    - Visual mode (OLED vs normal)
    - User preferences
    """

    APP_STATE_FILE = Path.home() / ".config" / "nitrosense" / "app_state.json"

    def __init__(self):
        self.state_file = self.APP_STATE_FILE
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self._state: Dict[str, Any] = self._load_state()

    def _load_state(self) -> Dict[str, Any]:
        """Load application state from disk."""
        try:
            if self.state_file.exists():
                return json.loads(self.state_file.read_text())
        except Exception as e:
            logger.error(f"Failed to load app state: {e}")

        return self._get_default_state()

    def _get_default_state(self) -> Dict[str, Any]:
        """Return default application state."""
        return {
            "last_tab": 0,
            "zoom_level": 100,
            "oled_mode": False,
            "sidebar_width": 200,
        }

    def _atomic_write(self, path: Path, content: str) -> None:
        """Write content to disk atomically."""
        temp_path = path.parent / f"{path.name}.tmp"
        temp_path.write_text(content, encoding="utf-8")
        os.replace(temp_path, path)

    def get(self, key: str, default: Any = None) -> Any:
        """Get state value."""
        return self._state.get(key, default)

    def set(self, key: str, value: Any, persist: bool = True) -> None:
        """Set state value."""
        self._state[key] = value
        if persist:
            self.save()

    def save(self) -> bool:
        """Persist state to disk."""
        try:
            self._atomic_write(self.state_file, json.dumps(self._state, indent=2))
            logger.debug(f"App state saved to {self.state_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to save app state: {e}")
            return False