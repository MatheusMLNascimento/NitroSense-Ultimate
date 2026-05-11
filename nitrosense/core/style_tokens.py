"""
Style Tokens and Design System for NitroSense Ultimate.

Centralized design tokens for consistent UI styling across QML and Python.
All colors, fonts, spacing, and visual elements are defined here.
"""

from typing import Dict, Any

# ============================================================================
# DESIGN TOKENS
# ============================================================================

class StyleTokens:
    """Centralized design tokens for consistent styling."""

    # Color Palette
    COLORS = {
        "primary": "#007aff",
        "secondary": "#6c757d",
        "success": "#28a745",
        "warning": "#ffc107",
        "danger": "#dc3545",
        "info": "#17a2b8",
        "background": "#1e1e1e",
        "surface": "#2d2d2d",
        "text_primary": "#ffffff",
        "text_secondary": "#a0a0a0",
        "border": "#404040",
    }

    # Temperature Colors
    TEMP_COLORS = {
        "cold": "#0099ff",
        "normal": "#34c759",
        "warm": "#ff9500",
        "hot": "#ff3b30",
        "critical": "#ff0033",
    }

    # Spacing Scale
    SPACING = {
        "xs": 4,
        "sm": 8,
        "md": 16,
        "lg": 24,
        "xl": 32,
        "xxl": 48,
    }

    # Border Radius
    RADIUS = {
        "none": 0,
        "sm": 4,
        "md": 8,
        "lg": 12,
        "xl": 16,
        "full": 9999,
    }

    # Font Sizes
    FONT_SIZE = {
        "xs": 10,
        "sm": 12,
        "md": 14,
        "lg": 16,
        "xl": 18,
        "xxl": 24,
        "heading": 28,
    }

    # Font Weights
    FONT_WEIGHT = {
        "normal": 400,
        "medium": 500,
        "bold": 700,
    }

    # Shadows
    SHADOWS = {
        "sm": "0 1px 2px rgba(0,0,0,0.1)",
        "md": "0 4px 6px rgba(0,0,0,0.1)",
        "lg": "0 10px 15px rgba(0,0,0,0.1)",
    }

    # Transitions
    TRANSITIONS = {
        "fast": "150ms ease-in-out",
        "normal": "300ms ease-in-out",
        "slow": "500ms ease-in-out",
    }

    # Component Styles
    COMPONENTS = {
        "button": {
            "primary": {
                "background": COLORS["primary"],
                "color": COLORS["text_primary"],
                "border_radius": RADIUS["md"],
                "padding": f"{SPACING['sm']}px {SPACING['md']}px",
                "font_size": FONT_SIZE["md"],
                "font_weight": FONT_WEIGHT["medium"],
            },
            "secondary": {
                "background": COLORS["surface"],
                "color": COLORS["text_primary"],
                "border": f"1px solid {COLORS['border']}",
                "border_radius": RADIUS["md"],
                "padding": f"{SPACING['sm']}px {SPACING['md']}px",
                "font_size": FONT_SIZE["md"],
            },
            "danger": {
                "background": COLORS["danger"],
                "color": COLORS["text_primary"],
                "border_radius": RADIUS["md"],
                "padding": f"{SPACING['sm']}px {SPACING['md']}px",
                "font_size": FONT_SIZE["md"],
                "font_weight": FONT_WEIGHT["medium"],
            },
        },
        "card": {
            "background": COLORS["surface"],
            "border": f"1px solid {COLORS['border']}",
            "border_radius": RADIUS["lg"],
            "padding": SPACING["md"],
            "shadow": SHADOWS["sm"],
        },
        "input": {
            "background": COLORS["background"],
            "color": COLORS["text_primary"],
            "border": f"1px solid {COLORS['border']}",
            "border_radius": RADIUS["md"],
            "padding": f"{SPACING['sm']}px {SPACING['md']}px",
            "font_size": FONT_SIZE["md"],
        },
    }

    @classmethod
    def get_color(cls, key: str) -> str:
        """Get color by key."""
        return cls.COLORS.get(key, cls.COLORS["text_primary"])

    @classmethod
    def get_temp_color(cls, temp: float) -> str:
        """Get temperature-based color."""
        if temp < 45:
            return cls.TEMP_COLORS["cold"]
        elif temp < 60:
            return cls.TEMP_COLORS["normal"]
        elif temp < 75:
            return cls.TEMP_COLORS["warm"]
        elif temp < 90:
            return cls.TEMP_COLORS["hot"]
        else:
            return cls.TEMP_COLORS["critical"]

    @classmethod
    def get_spacing(cls, key: str) -> int:
        """Get spacing value."""
        return cls.SPACING.get(key, cls.SPACING["md"])

    @classmethod
    def get_radius(cls, key: str) -> int:
        """Get border radius value."""
        return cls.RADIUS.get(key, cls.RADIUS["md"])