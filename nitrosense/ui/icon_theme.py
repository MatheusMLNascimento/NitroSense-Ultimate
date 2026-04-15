from pathlib import Path

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


def _find_icon_path(filename: str):
    """Search fallback directories for a requested icon file."""
    for directory in ICON_DIRS:
        if not directory.exists():
            continue
        icon_path = directory / filename
        if icon_path.exists():
            return icon_path
    return None


def load_icon(name: str, size: QSize | None = None) -> QIcon:
    """Attempt to load an icon by name from the preferred asset folders."""
    filename = ICON_FILES.get(name)
    if not filename:
        return QIcon()

    path = _find_icon_path(filename)
    if path is None:
        return QIcon()

    icon = QIcon(str(path))
    if size is not None:
        icon = QIcon(icon.pixmap(size))
    return icon


def load_icon_pixmap(name: str, size: QSize) -> QPixmap | None:
    """Load a pixmap for a named icon, or return None if the asset is missing."""
    icon = load_icon(name, size)
    if icon.isNull():
        return None
    return icon.pixmap(size)
