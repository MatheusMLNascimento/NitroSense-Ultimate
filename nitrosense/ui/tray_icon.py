"""
System Tray Integration and Autostart - Dir 13
Ícone dinâmico refletindo temperatura, acesso rápido ao Modo Frost
Inicialização automática via ~/.config/autostart/nitrosense.desktop

FEATURES:
1. Tray icon dinâmico que muda cor/ícone baseado em temperatura
2. Menu rápido no tray: Show/Hide, Frost Mode, Quit
3. Criar .desktop file em ~/.config/autostart para inicialização automática
4. Double-click no tray para show/hide
"""

import os
import subprocess
from pathlib import Path
from typing import Optional, Callable
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QColor, QPixmap, QPainter, QFont
from PyQt6.QtCore import Qt, QTimer, QSize

from ..core.logger import logger
from ..core.constants import APP_CONFIG, COLOR_SCHEME
from ..i18n import t


class DynamicTrayIcon:
    """
    Tray icon que muda cor/ícone baseado em temperatura do sistema.
    
    Cores:
    - Verde (#00FF00): < 40°C
    - Amarelo (#FFFF00): 40-55°C
    - Laranja (#FFA500): 55-70°C
    - Vermelho (#FF0000): > 70°C (alerta)
    """
    
    def __init__(self, tray_icon: QSystemTrayIcon, hardware_manager=None):
        """
        Args:
            tray_icon: QSystemTrayIcon object
            hardware_manager: Hardware manager para ler temperatura
        """
        self.tray_icon = tray_icon
        self.hardware = hardware_manager
        self.icon_size = QSize(32, 32)
        self.current_color = QColor("#00FF00")
        self._update_timer = QTimer()
        self._update_timer.setInterval(2000)  # Update every 2 seconds
        self._update_timer.timeout.connect(self._on_timer)
    
    def start_updates(self) -> None:
        """Start updating tray icon based on temperature."""
        self._update_timer.start()
        self._on_timer()  # Update immediately
    
    def stop_updates(self) -> None:
        """Stop updating tray icon."""
        self._update_timer.stop()
    
    def _on_timer(self) -> None:
        """Timer callback: update tray icon based on current temperature."""
        if not self.hardware:
            return
        
        try:
            # Get current CPU temperature
            temp = self.hardware.get_cpu_temperature()
            if temp is None:
                return
            
            # Determine color based on temperature
            if temp < 40:
                color = QColor("#00FF00")  # Green - cool
            elif temp < 55:
                color = QColor("#FFFF00")  # Yellow - normal
            elif temp < 70:
                color = QColor("#FFA500")  # Orange - warm
            else:
                color = QColor("#FF0000")  # Red - hot/alert
            
            self.current_color = color
            self._update_icon(color, temp)
        except Exception as e:
            logger.debug(f"Failed to update tray icon: {e}")
    
    def _update_icon(self, color: QColor, temp: float) -> None:
        """
        Create and set tray icon based on color and temperature.
        
        Args:
            color: QColor for the icon
            temp: Temperature value for tooltip
        """
        try:
            # Create pixmap with color
            pixmap = QPixmap(self.icon_size)
            pixmap.fill(Qt.GlobalColor.transparent)
            
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Draw circle with color
            brush_color = color
            painter.setBrush(brush_color)
            painter.drawEllipse(
                4, 4,
                self.icon_size.width() - 8,
                self.icon_size.height() - 8
            )
            
            # Draw border
            painter.setPen(Qt.GlobalColor.gray)
            painter.drawEllipse(
                4, 4,
                self.icon_size.width() - 8,
                self.icon_size.height() - 8
            )
            
            # Draw temperature text (simple)
            if temp is not None:
                font = QFont("Arial", 6, QFont.Weight.Bold)
                painter.setFont(font)
                painter.setPen(Qt.GlobalColor.white)
                painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, f"{int(temp)}°")
            
            painter.end()
            
            # Set icon and tooltip
            icon = QIcon(pixmap)
            self.tray_icon.setIcon(icon)
            self.tray_icon.setToolTip(
                f"{t('NitroSense Ultimate')}\n"
                f"CPU Temp: {temp:.1f}°C" if temp else t('NitroSense Ultimate')
            )
        except Exception as e:
            logger.error(f"Failed to create tray icon: {e}")


class AutostartManager:
    """
    Gerencia inicialização automática via .desktop file.
    
    Cria ~/.config/autostart/nitrosense.desktop com:
    - Exec=python /path/to/main.py
    - StartupNotify=true
    - Terminal=false
    - Categories=Utility;System;
    """
    
    AUTOSTART_DIR = Path.home() / ".config" / "autostart"
    DESKTOP_FILE = AUTOSTART_DIR / "nitrosense.desktop"
    
    @staticmethod
    def get_main_py_path() -> str:
        """Get absolute path to main.py."""
        try:
            # Try to get from APP_CONFIG
            if "app_path" in APP_CONFIG:
                return APP_CONFIG["app_path"]
            
            # Fallback: construct from package location
            import nitrosense
            app_dir = Path(nitrosense.__file__).parent.parent
            return str(app_dir / "main.py")
        except:
            return "/opt/nitrosense/main.py"  # Fallback for installed version
    
    @staticmethod
    def enable_autostart() -> bool:
        """
        Enable autostart by creating .desktop file.
        
        Returns:
            True if successful
        """
        try:
            AutostartManager.AUTOSTART_DIR.mkdir(parents=True, exist_ok=True)
            
            main_py = AutostartManager.get_main_py_path()
            python_exe = "python3"  # Use python3 explicitly
            
            # Get icon path (fallback to generic)
            icon_path = "/usr/share/icons/hicolor/scalable/apps/nitrosense.svg"
            if not Path(icon_path).exists():
                icon_path = "nitrosense"
            
            desktop_content = f"""[Desktop Entry]
Type=Application
Name=NitroSense Ultimate
Comment=Acer laptop thermal management and system monitoring
Exec={python_exe} {main_py} --background
Icon={icon_path}
Terminal=false
Categories=System;Utility;
StartupNotify=true
X-GNOME-Autostart-enabled=true
X-GNOME-Autostart-Phase=Application
X-KDE-autoStartDelay=2
"""
            
            AutostartManager.DESKTOP_FILE.write_text(desktop_content)
            AutostartManager.DESKTOP_FILE.chmod(0o755)
            
            logger.info(f"Autostart enabled: {AutostartManager.DESKTOP_FILE}")
            return True
        except Exception as e:
            logger.error(f"Failed to enable autostart: {e}")
            return False
    
    @staticmethod
    def disable_autostart() -> bool:
        """
        Disable autostart by removing .desktop file.
        
        Returns:
            True if successful
        """
        try:
            if AutostartManager.DESKTOP_FILE.exists():
                AutostartManager.DESKTOP_FILE.unlink()
                logger.info(f"Autostart disabled: {AutostartManager.DESKTOP_FILE}")
            return True
        except Exception as e:
            logger.error(f"Failed to disable autostart: {e}")
            return False
    
    @staticmethod
    def is_autostart_enabled() -> bool:
        """Check if autostart is currently enabled."""
        return AutostartManager.DESKTOP_FILE.exists()


class TrayMenuBuilder:
    """
    Constrói o menu de contexto do tray com ações rápidas.
    
    Menu:
    - Show/Hide (toggle)
    - Modo Frost (ativa modo máximo resfriamento)
    - Configurações
    - ───────────
    - Sair
    """
    
    def __init__(self):
        self.menu: Optional[QMenu] = None
    
    def build_menu(self,
                   on_show_hide: Callable,
                   on_frost_mode: Callable,
                   on_settings: Callable,
                   on_quit: Callable) -> QMenu:
        """
        Build tray context menu.
        
        Args:
            on_show_hide: Callback for show/hide action
            on_frost_mode: Callback for Frost Mode activation
            on_settings: Callback for settings
            on_quit: Callback for quit action
            
        Returns:
            QMenu object ready to be set on tray icon
        """
        self.menu = QMenu()
        
        # Show/Hide
        show_action = self.menu.addAction(t("Show/Hide"))
        show_action.triggered.connect(on_show_hide)
        
        # Modo Frost (quick access)
        frost_action = self.menu.addAction(t("Activate Frost Mode"))
        frost_action.triggered.connect(on_frost_mode)
        frost_action.setToolTip(t("Maximum cooling - fans at full speed"))
        
        # Settings
        settings_action = self.menu.addAction(t("Settings"))
        settings_action.triggered.connect(on_settings)
        
        # Separator
        self.menu.addSeparator()
        
        # Quit
        quit_action = self.menu.addAction(t("Quit Application"))
        quit_action.triggered.connect(on_quit)
        
        return self.menu
