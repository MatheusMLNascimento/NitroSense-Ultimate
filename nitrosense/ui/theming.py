"""
Theming Module for NitroSense Ultimate UI.
Consolidates icon loading, emoji themes, and visual styling.
"""

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QSize
from PyQt6.QtGui import QIcon, QPixmap

# Fallback icon search paths. Add your custom PNGs to one of these folders.
BASE_DIR = Path(__file__).resolve().parent.parent
ICON_DIRS = [
    # Look in nitrosense/assets first, then nitrosense/assets/icons.
    BASE_DIR / "assets",
    BASE_DIR / "assets" / "icons",
    BASE_DIR.parent / "assets" / "icons",
    BASE_DIR.parent / "assets",
]

# Centralized icon-to-file mapping used by the entire UI.
# Add new image files to one of the ICON_DIRS directories.
ICON_FILES = {
    # Navigation icons
    "home": "home.png",
    "status": "status.png",
    "config": "config.png",
    "labs": "labs.png",
    "docs": "docs.png",

    # Section / card icons
    "thermal": "thermal.png",
    "history": "history.png",
    "control": "control.png",

    # Status page icons
    "cpu": "cpu.png",
    "gpu": "gpu.png",
    "nbfc": "nbfc.png",
    "sensors": "sensors.png",
    "fan": "fan.png",
    "memory": "memory.png",
    "disk": "disk.png",

    # Button / action icons
    "frost": "frost.png",
    "pause": "pause.png",
    "save": "save.png",
    "reset": "reset.png",
    "export": "export.png",
    "help": "help.png",
    "auto": "auto.png",
}

# Navigation emojis
NAV_EMOJIS = {
    "home": "🏠",
    "status": "📊",
    "config": "⚙️",
    "labs": "🧪",
    "docs": "📖",
}

# Status indicator emojis
STATUS_EMOJIS = {
    "ok": "🟢",
    "success": "✅",
    "warning": "🟡",
    "critical": "🔴",
    "error": "❌",
}

# Hardware emojis
HARDWARE_EMOJIS = {
    "cpu": "🖥️",
    "gpu": "📐",
    "fan": "🌀",
    "temp": "🌡️",
    "memory": "💾",
    "disk": "💿",
    "power": "⚡",
}

# Feature emojis
FEATURE_EMOJIS = {
    "frost_mode": "❄️",
    "performance": "🚀",
    "quiet": "🔇",
    "gaming": "🎮",
    "thermal": "🔥",
    "cooling": "❄️",
    "ai": "🤖",
    "watchdog": "👁️",
    "protection": "🛡️",
}

# Action emojis
ACTION_EMOJIS = {
    "check": "✅",
    "cross": "❌",
    "play": "▶️",
    "pause": "⏸️",
    "stop": "⏹️",
    "save": "💾",
    "load": "📂",
    "settings": "⚙️",
    "help": "❓",
    "info": "ℹ️",
}


def load_icon_pixmap(icon_name: str, size: Optional[QSize] = None) -> QPixmap:
    """
    Load an icon as a QPixmap from the icon files.

    Args:
        icon_name: Name of the icon (key in ICON_FILES)
        size: Optional size to scale the pixmap to

    Returns:
        QPixmap of the icon, or empty pixmap if not found
    """
    if icon_name not in ICON_FILES:
        return QPixmap()

    filename = ICON_FILES[icon_name]

    for icon_dir in ICON_DIRS:
        icon_path = icon_dir / filename
        if icon_path.exists():
            pixmap = QPixmap(str(icon_path))
            if size and not pixmap.isNull():
                pixmap = pixmap.scaled(size, aspectRatioMode=1)  # KeepAspectRatio
            return pixmap

    # Return empty pixmap if not found
    return QPixmap()


def load_icon(icon_name: str, size: Optional[QSize] = None) -> QIcon:
    """
    Load an icon as a QIcon from the icon files.

    Args:
        icon_name: Name of the icon (key in ICON_FILES)
        size: Optional size for the icon

    Returns:
        QIcon of the icon, or null icon if not found
    """
    pixmap = load_icon_pixmap(icon_name, size)
    if pixmap.isNull():
        return QIcon()
    return QIcon(pixmap)


def get_emoji(category: str, key: str) -> str:
    """
    Get an emoji from the theme dictionaries.

    Args:
        category: Category of emoji ('nav', 'status', 'hardware', 'feature', 'action')
        key: Key within the category

    Returns:
        Emoji string, or empty string if not found
    """
    emoji_dicts = {
        'nav': NAV_EMOJIS,
        'status': STATUS_EMOJIS,
        'hardware': HARDWARE_EMOJIS,
        'feature': FEATURE_EMOJIS,
        'action': ACTION_EMOJIS,
    }

    if category in emoji_dicts and key in emoji_dicts[category]:
        return emoji_dicts[category][key]
    return ""