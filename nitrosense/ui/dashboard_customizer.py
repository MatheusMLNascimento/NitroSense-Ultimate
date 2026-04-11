"""
Customizable Dashboard System for NitroSense Ultimate.

FEATURE #1: Dashboard Customizável
MOTIVO: Diferentes usuários têm diferentes prioridades de monitoramento.
- Usuário gaming: quer ver FPS + temp, não precisa de status LEDs
- Usuário server: quer memory/disk, não RPM detalhado
- Arrasta/reordena widgets sem código = UX profissional
- Layout persiste em config.json entre sessões
- Vs. layout fixo = força UX que não funciona para todos

FEATURE #14: Status Bar (já implementado no main_window.py)
MOTIVO: Usuários precisam de info sempre visível sem abrir menus.
- "Last update: HH:MM:SS" = diagnosticar se app congelou
- "FPS: --" = detectar if rendering está sendo throttled
- "Memory: --.-%\" = ver footprint e memory leaks
- Status bar é "free real estate" (always visible) vs. modal dialogs
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFrame, QLabel
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QDrag
from PyQt6.QtCore import QMimeData, QPoint
import json
from pathlib import Path
from typing import Dict, List, Optional
from ...core.logger import logger
from ...core.constants import COLOR_SCHEME


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
        
        # Styling
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {COLOR_SCHEME['surface']};
                border: 1px solid {COLOR_SCHEME['primary']};
                border-radius: 16px;
                padding: 8px;
            }}
        """)
        
        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Title bar
        title_bar = self._create_title_bar()
        layout.addWidget(title_bar)
        
        # Content
        layout.addWidget(content)
        layout.addStretch()
    
    def _create_title_bar(self) -> QWidget:
        """Create title bar with drag handle."""
        bar = QWidget()
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Title label
        title_label = QLabel(f"::  {self.title}")
        title_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        title_label.setStyleSheet(f"color: {COLOR_SCHEME['primary']};")
        layout.addWidget(title_label)
        
        # Spacer
        layout.addStretch()
        
        # Close button (optional)
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {COLOR_SCHEME['danger']};
                border: none;
                font-weight: bold;
            }}
        """)
        layout.addWidget(close_btn)
        
        return bar
    
    def mousePressEvent(self, event):
        """Start drag operation."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = True
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event):
        """Handle drag movement."""
        if self.is_dragging and self.drag_position:
            self.move(event.globalPos() - self.drag_position)
            event.accept()
    
    def mouseReleaseEvent(self, event):
        """End drag operation."""
        self.is_dragging = False
        event.accept()


class DashboardController:
    """
    Manages dashboard customization state and persistence.
    
    Handles:
    - Widget layout configuration
    - Drag-and-drop position tracking
    - Save/load from config file
    - Widget enable/disable toggles
    """
    
    def __init__(self, config_manager):
        """
        Initialize dashboard controller.
        
        Args:
            config_manager: Application configuration manager
        """
        self.config = config_manager
        self.widgets_order: List[str] = []
        self.widgets_visible: Dict[str, bool] = {}
        self.widgets_positions: Dict[str, tuple] = {}
        
        # Default order
        self.default_order = [
            "temperature_display",
            "multi_axis_graph",
            "controls",
        ]
        
        self._load_dashboard_config()
        logger.info("DashboardController initialized")
    
    def _load_dashboard_config(self) -> None:
        """Load dashboard configuration from file."""
        try:
            config_path = Path.home() / ".config" / "nitrosense" / "dashboard.json"
            
            if config_path.exists():
                with open(config_path, 'r') as f:
                    dashboard_config = json.load(f)
                    self.widgets_order = dashboard_config.get("widget_order", self.default_order)
                    self.widgets_visible = dashboard_config.get("widgets_visible", {})
                    self.widgets_positions = dashboard_config.get("widgets_positions", {})
            else:
                self.widgets_order = self.default_order
                self.widgets_visible = {w: True for w in self.default_order}
                self._save_dashboard_config()
        
        except Exception as e:
            logger.error(f"Failed to load dashboard config: {e}")
            self.widgets_order = self.default_order
    
    def _save_dashboard_config(self) -> None:
        """Save dashboard configuration to file."""
        try:
            config_path = Path.home() / ".config" / "nitrosense" / "dashboard.json"
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            dashboard_config = {
                "widget_order":  self.widgets_order,
                "widgets_visible": self.widgets_visible,
                "widgets_positions": self.widgets_positions,
            }
            
            with open(config_path, 'w') as f:
                json.dump(dashboard_config, f, indent=2)
            
            logger.info("Dashboard config saved")
        
        except Exception as e:
            logger.error(f"Failed to save dashboard config: {e}")
    
    def get_widget_order(self) -> List[str]:
        """Get current widget display order."""
        return self.widgets_order
    
    def set_widget_order(self, new_order: List[str]) -> None:
        """Update widget order and persist."""
        self.widgets_order = new_order
        self._save_dashboard_config()
        logger.info(f"Widget order updated: {new_order}")
    
    def set_widget_visibility(self, widget_id: str, visible: bool) -> None:
        """Toggle widget visibility."""
        self.widgets_visible[widget_id] = visible
        self._save_dashboard_config()
        logger.info(f"Widget {widget_id} visibility: {visible}")
    
    def save_widget_position(self, widget_id: str, pos_tuple: tuple) -> None:
        """Save widget position for persistence."""
        self.widgets_positions[widget_id] = pos_tuple
        self._save_dashboard_config()
    
    def get_widget_position(self, widget_id: str) -> Optional[tuple]:
        """Retrieve saved widget position."""
        return self.widgets_positions.get(widget_id)
    
    def reset_to_default(self) -> None:
        """Reset dashboard to default layout."""
        self.widgets_order = self.default_order
        self.widgets_visible = {w: True for w in self.default_order}
        self.widgets_positions = {}
        self._save_dashboard_config()
        logger.info("Dashboard reset to default")
