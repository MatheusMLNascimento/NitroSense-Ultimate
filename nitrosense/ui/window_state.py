"""
Window State Persistence - Dir 19-20
Salva e restaura posição, tamanho, aba ativa, tema

FEATURES:
1. Persistência de geometry (posição + tamanho da janela)
2. Lembrar última aba ativa no stacked widget
3. Detecção automática de Dark/Light do KDE Plasma via env vars
4. Serialização segura em ~/.config/nitrosense/window_state.json
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from PyQt6.QtWidgets import QMainWindow, QWidget
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
import os

from ..core.logger import logger
from ..core.constants import APP_CONFIG


class WindowStateManager:
    """
    Gerencia persistência visual da janela.
    
    Salva em ~/.config/nitrosense/window_state.json:
    - posição x, y
    - tamanho width, height
    - última aba ativa (index no stacked widget)
    - tema dark/light
    - estado de maximização
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
        Save window geometry and state.
        
        Args:
            window: QMainWindow to save state from
            
        Returns:
            True if saved successfully
        """
        try:
            geometry = window.geometry()
            state = {
                "geometry": {
                    "x": geometry.x(),
                    "y": geometry.y(),
                    "width": geometry.width(),
                    "height": geometry.height(),
                },
                "maximized": window.isMaximized(),
                "last_tab": self._get_active_tab_index(window),
                "theme": self._detect_kde_theme(),
            }
            
            self._atomic_write(self.state_file, json.dumps(state, indent=2))
            logger.debug(f"Window state saved to {self.state_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to save window state: {e}")
            return False
    
    def restore_window_state(self, window: QMainWindow) -> bool:
        """
        Restore window geometry and state.
        
        Args:
            window: QMainWindow to restore state to
            
        Returns:
            True if restored successfully
        """
        try:
            if not self.state_file.exists():
                logger.debug("No saved window state found")
                return False
            
            state = json.loads(self.state_file.read_text())
            
            # Restore geometry
            geom = state.get("geometry", {})
            if geom:
                window.setGeometry(
                    geom.get("x", 100),
                    geom.get("y", 100),
                    geom.get("width", APP_CONFIG.get("window_width", 1400)),
                    geom.get("height", APP_CONFIG.get("window_height", 900))
                )
            
            # Restore maximized state
            if state.get("maximized", False):
                window.showMaximized()
            
            # Store last_tab for later use (after UI is fully initialized)
            setattr(window, '_last_saved_tab', state.get("last_tab", 0))
            
            # Store theme for later use
            setattr(window, '_saved_theme', state.get("theme", "dark"))
            
            logger.debug(f"Window state restored from {self.state_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to restore window state: {e}")
            return False
    
    def restore_tab(self, stacked_widget, tab_index: Optional[int] = None) -> None:
        """
        Restore last active tab.
        
        Args:
            stacked_widget: QStackedWidget to restore tab in
            tab_index: Override index (if None, uses saved value)
        """
        try:
            if tab_index is None:
                if not self.state_file.exists():
                    return
                
                state = json.loads(self.state_file.read_text())
                tab_index = state.get("last_tab", 0)
            
            if tab_index is not None:
                count = stacked_widget.count() if stacked_widget is not None else 0
                if count > 0 and 0 <= tab_index < count:
                    stacked_widget.setCurrentIndex(tab_index)
                    logger.debug(f"Restored tab index: {tab_index}")
        except Exception as e:
            logger.error(f"Failed to restore tab: {e}")
    
    def _get_active_tab_index(self, window: QMainWindow) -> int:
        """Get index of active tab from stacked widget."""
        try:
            # Access stacked_widget if it exists
            stacked_widget = getattr(window, 'stacked_widget', None)
            if stacked_widget is not None:
                return stacked_widget.currentIndex()
        except Exception:
            pass
        return 0
    
    @staticmethod
    def _detect_kde_theme() -> str:
        """
        Detect KDE Plasma color scheme preference.
        
        Checks:
        - KDE_FULL_SESSION env var
        - QT_STYLE_OVERRIDE
        - /etc/kde/ config
        
        Returns:
            "dark" or "light"
        """
        try:
            # Check KDE Plasma Breeze Dark/Light
            kde_colorscheme = os.environ.get("KDE_COLOR_SCHEME", "")
            if "dark" in kde_colorscheme.lower():
                return "dark"
            if "light" in kde_colorscheme.lower():
                return "light"
            
            # Check Qt style
            qt_style = os.environ.get("QT_STYLE_OVERRIDE", "").lower()
            if "dark" in qt_style:
                return "dark"
            if "light" in qt_style:
                return "light"
            
            # Check KDE Plasma config
            kde_config = Path.home() / ".config" / "kdeglobals"
            if kde_config.exists():
                config_text = kde_config.read_text()
                if "[Colors:Window]" in config_text:
                    # Parse background color
                    for line in config_text.split('\n'):
                        if line.startswith("BackgroundNormal="):
                            # RGB format: 239,239,239
                            try:
                                rgb = line.split("=")[1]
                                r, g, b = map(int, rgb.split(","))
                                # If average is > 128, it's light
                                avg = (r + g + b) / 3
                                return "light" if avg > 128 else "dark"
                            except:
                                pass
            
            # Default to dark (most common for NitroSense users)
            return "dark"
        except Exception as e:
            logger.debug(f"Failed to detect KDE theme: {e}")
            return "dark"
    
    def get_theme_colors(self, theme: str = "") -> Dict[str, str]:
        """
        Get color palette for detected/specified theme.
        
        Args:
            theme: "dark", "light", or "" for auto-detect
            
        Returns:
            Dictionary of theme colors
        """
        if not theme:
            theme = self._detect_kde_theme()
        
        if theme == "light":
            return {
                "background": "#FFFFFF",
                "text": "#000000",
                "border": "#CCCCCC",
                "primary": "#007AFF",  # macOS blue
            }
        else:  # dark
            return {
                "background": "#1E1E1E",
                "text": "#FFFFFF",
                "border": "#333333",
                "primary": "#00D1FF",  # Cyan
            }


class ApplicationStateManager:
    """
    Persists general application state (não apenas window).
    
    Salva:
    - Última aba ativa
    - Zoom level
    - Modo visual (OLED vs normal)
    - Preferências do usuário
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
