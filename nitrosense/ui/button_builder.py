"""
Button Builder for NitroSense Ultimate UI.

Provides a factory for creating consistent buttons with predefined styles
and actions from the ActionController.
"""

from typing import Optional, Callable, Any
from PyQt6.QtWidgets import QPushButton, QWidget
from PyQt6.QtCore import pyqtSignal
from ..core.style_tokens import StyleTokens
from ..core.actions import action_controller

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
    def create_action_button(
        text: str,
        action_name: str,
        preset: str = "primary",
        action_args: Optional[tuple] = None,
        parent: Optional[QWidget] = None
    ) -> QPushButton:
        """
        Create a button that calls an ActionController method.

        Args:
            text: Button text
            action_name: Name of method in ActionController
            preset: Style preset
            action_args: Arguments for the action
            parent: Parent widget

        Returns:
            Configured QPushButton
        """
        action = getattr(action_controller, action_name, None)
        if not action:
            raise ValueError(f"Action '{action_name}' not found in ActionController")

        return ButtonBuilder.create(text, preset, action, action_args, parent)

    @staticmethod
    def _apply_style(button: QPushButton, preset: str):
        """Apply style to button based on preset."""
        style = StyleTokens.COMPONENTS["button"].get(preset, StyleTokens.COMPONENTS["button"]["primary"])

        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {style['background']};
                color: {style['color']};
                border: {style.get('border', 'none')};
                border-radius: {style['border_radius']}px;
                padding: {style['padding']};
                font-size: {style['font_size']}px;
                font-weight: {style['font_weight']};
            }}
            QPushButton:hover {{
                background-color: {ButtonBuilder._lighten_color(style['background'])};
            }}
            QPushButton:pressed {{
                background-color: {ButtonBuilder._darken_color(style['background'])};
            }}
        """)

    @staticmethod
    def _lighten_color(color: str) -> str:
        """Lighten a hex color for hover effect."""
        # Simple implementation - could be enhanced
        if color.startswith("#"):
            # For now, return same color
            return color
        return color

    @staticmethod
    def _darken_color(color: str) -> str:
        """Darken a hex color for pressed effect."""
        # Simple implementation - could be enhanced
        if color.startswith("#"):
            # For now, return same color
            return color
        return color