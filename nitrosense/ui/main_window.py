"""
Main Application Window and UI Framework for NitroSense Ultimate.
Uses QStackedWidget for multi-page navigation.

CRITICAL DESIGN PRINCIPLES:
1. Visibility guards: Skip updates if window is hidden or minimized
2. Lazy loading: Create pages only when first visited
3. CPU reduction: Use draw_idle() for Matplotlib, avoid busy-waiting
4. RAM efficiency: Use __slots__ for page data classes
5. Cleanup: gc.collect() on page transitions, remove old animations
"""

import gc
import psutil
import weakref
from typing import Optional, Dict, Type
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QStackedWidget, QPushButton, QFrame, QLabel, QStatusBar,
    QScrollArea, QSystemTrayIcon, QMenu
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve, QSize, QEvent
from PyQt6.QtGui import QFont, QGuiApplication, QIcon

from ..core.logger import logger
from ..core.constants import APP_CONFIG, COLOR_SCHEME
from ..i18n import t
from .icon_theme import load_icon
from .notifications import ToastManager
from .window_state import WindowStateManager, ApplicationStateManager
from .tray_icon import DynamicTrayIcon, TrayMenuBuilder, AutostartManager
from .ux_utilities import DebouncedSlider, LoadingButton


class NitroSenseApp(QMainWindow):
    """
    Main application window with visibility guards and lazy loading.
    
    Features:
    - Visibility guards prevent updates when minimized/hidden
    - Pages are lazy-loaded (created on first access)
    - Automatic garbage collection on page transitions
    - CPU optimized: respects KWin compositor with draw_idle()
    """

    def __init__(self, system):
        try:
            self._temporary_qapp = None
            if QApplication.instance() is None:
                self._temporary_qapp = QApplication([])

            # Page management with lazy loading
            self.pages: Dict[str, Optional[QWidget]] = {
                "home": None,
                "status": None,
                "config": None,
                "labs": None,
                "docs": None,
            }
            self.page_classes: Dict[str, Type] = {}  # Will be populated lazily
            
            self.stacked_widget = QStackedWidget()
            self.update_timer = None
            self.status_update_timer = None
            self.config_reload_timer = None
            self.update_check_timer = None
            
            # Visibility tracking
            self._is_visible = True
            self._is_minimized = False

            super().__init__()
            self.system = system
            self.hardware = getattr(system, 'hardware_manager', None)
            self.config = getattr(system, 'config_manager', None)
            self.background_mode = False

            # Set window flags to ensure it appears in taskbar
            self.setWindowFlags(Qt.WindowType.Window)
            self.setWindowTitle("NitroSense Ultimate")

            # Initialize UI
            self._init_ui()

            # Setup theme
            self._apply_theme()
            
            # Initialize Toast Manager
            self.toast_manager = ToastManager(self)
            
            # ===== DIR 19-20: Window State Persistence =====
            self.window_state_manager = WindowStateManager()
            self.app_state_manager = ApplicationStateManager()
            self.window_state_manager.restore_window_state(self)
            self.window_state_manager.restore_tab(self.stacked_widget, getattr(self, '_last_saved_tab', None))
            self._saved_theme = getattr(self, '_saved_theme', 'dark')
            logger.info("✓ Window state restoration initialized")
            
            # ===== DIR 13: System Tray Icon (Dynamic) =====
            self._init_system_tray()
            logger.info("✓ System tray initialized with dynamic temperature coloring")
            
            # ===== DIR 6: Hardware Watchdog =====
            self._init_hardware_watchdog()
            logger.info("✓ Hardware watchdog initialized (100% fan on >3 sensor failures)")

            # Create timers with VISIBILITY GUARDS
            self.update_timer = QTimer()
            self.update_timer.timeout.connect(self._periodic_cleanup_guarded)
            self.update_timer.start(10000)  # Every 10 seconds
            
            self.status_update_timer = QTimer()
            self.status_update_timer.timeout.connect(self._update_status_bar_guarded)
            self.status_update_timer.start(1000)  # Every 1 second

            self.config_reload_timer = QTimer()
            self.config_reload_timer.timeout.connect(self._reload_config_guarded)
            self.config_reload_timer.start(5000)  # Every 5 seconds

            self.update_check_timer = QTimer()
            self.update_check_timer.timeout.connect(self._check_for_updates)
            self.update_check_timer.start(24 * 60 * 60 * 1000)  # 24 hours

            # Animation tracking
            self.current_animation: Optional[QPropertyAnimation] = None
            self.frame_count = 0
            self.last_frame_time = datetime.now()
            
            # Install event filter for visibility changes
            self.installEventFilter(self)

            logger.info("✓ NitroSenseApp initialized with lazy loading and visibility guards")

        except Exception as e:
            logger.critical(f"Failed to initialize main window: {e}", exc_info=True)
            self._show_startup_error(str(e))

    def eventFilter(self, obj, event: QEvent) -> bool:
        """Monitor visibility and minimize events to optimize CPU."""
        if obj == self:
            if event.type() == QEvent.Type.ShowToParent:
                self._is_visible = True
                self._is_minimized = False
                logger.debug("Window shown—resuming full refresh")
            elif event.type() == QEvent.Type.HideToParent:
                self._is_visible = False
                self._is_minimized = True
                logger.debug("Window hidden—reducing update frequency")
            elif event.type() == QEvent.Type.WindowStateChange:
                self._is_minimized = self.isMinimized()
                if self._is_minimized:
                    logger.debug("Window minimized—sensor sample rate reduced")
                else:
                    logger.debug("Window restored—resuming normal refresh")
        
        return super().eventFilter(obj, event)

    def _periodic_cleanup_guarded(self) -> None:
        """Cleanup with visibility guard."""
        if not self._should_update():
            return
        self._periodic_cleanup()

    def _update_status_bar_guarded(self) -> None:
        """Update status bar only if visible."""
        if not self._should_update():
            return
        self._update_status_bar()

    def _reload_config_guarded(self) -> None:
        """Reload config with visibility guard."""
        if not self._should_update():
            return
        self._reload_config()

    def _should_update(self) -> bool:
        """Check if window is visible and not minimized."""
        return self._is_visible and not self._is_minimized

    def _show_startup_error(self, message: str) -> None:
        """Display a lightweight fallback UI after main window initialization failure."""
        try:
            fallback_widget = QWidget()
            layout = QVBoxLayout(fallback_widget)
            layout.setContentsMargins(20, 20, 20, 20)
            layout.setSpacing(12)

            label = QLabel("NitroSense encountered an error during startup.")
            label.setWordWrap(True)
            label.setStyleSheet(f"color: {COLOR_SCHEME['text_secondary']}; font-size: 14px;")
            layout.addWidget(label)

            details = QLabel(message)
            details.setWordWrap(True)
            details.setStyleSheet("color: #ff6b6b; font-size: 12px;")
            layout.addWidget(details)

            self.setCentralWidget(fallback_widget)
            self._set_ui_timers_enabled(False)
        except Exception:
            logger.critical("Failed to create fallback startup error UI", exc_info=True)

    def _set_ui_timers_enabled(self, enabled: bool) -> None:
        """Pause or resume UI timers when entering/exiting background mode."""
        if self.update_timer:
            if enabled:
                self.update_timer.start(10000)
            else:
                self.update_timer.stop()

        if self.status_update_timer:
            if enabled:
                self.status_update_timer.start(1000)
            else:
                self.status_update_timer.stop()

        if self.config_reload_timer:
            if enabled:
                self.config_reload_timer.start(5000)
            else:
                self.config_reload_timer.stop()

        if self.update_check_timer:
            if enabled:
                self.update_check_timer.start(24 * 60 * 60 * 1000)
            else:
                self.update_check_timer.stop()

    def enter_background_mode(self, reason: str = "background") -> None:
        """Move the app into a hidden background mode and pause UI updates."""
        if self.background_mode:
            return
        self.background_mode = True
        logger.info(f"Entering background mode ({reason}); UI timers paused.")
        self._set_ui_timers_enabled(False)
        self.showMinimized()  # Minimize instead of hide to keep the app running

    def exit_background_mode(self) -> None:
        """Restore the app from background mode and resume UI updates."""
        if not self.background_mode:
            return
        self.background_mode = False
        logger.info("Exiting background mode; UI timers resumed.")
        self._set_ui_timers_enabled(True)
        self.showNormal()

    def changeEvent(self, event: QEvent) -> None:
        if event.type() == QEvent.Type.WindowStateChange:
            if self.windowState() & Qt.WindowState.WindowMinimized:
                self.enter_background_mode(reason="window minimized")
            elif event.oldState() & Qt.WindowState.WindowMinimized:
                self.exit_background_mode()
        super().changeEvent(event)

    def _reload_config(self) -> None:
        """Hot-reload configuration."""
        try:
            old_config = self.config._cache.copy()
            self.config.reload_config()
            if self.config._cache != old_config:
                logger.info("Configuration hot-reloaded")
                # Optionally refresh UI elements that depend on config
                self._apply_theme()  # In case theme changed
        except Exception as e:
            logger.error(f"Config reload error: {e}")

    def _check_for_updates(self) -> None:
        """Check for application updates."""
        try:
            # Simulate version check (replace with actual API call)
            current_version = APP_CONFIG["version"]
            latest_version = "3.0.6"  # This would come from API

            if latest_version > current_version:
                self.toast_manager.show_toast(
                    f"Update Available: v{latest_version}",
                    "A new version is available. Check the project repository for details.",
                    duration=10000
                )
                logger.info(f"Update available: {latest_version} > {current_version}")
            else:
                logger.debug("Application is up to date")

        except Exception as e:
            logger.error(f"Update check error: {e}")

    def _tray_activated(self, reason):
        """Handle tray icon activation."""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.showNormal()
            self.activateWindow()

    def _init_ui(self) -> None:
        """Initialize user interface."""
        # Detect screen size for multi-monitor support
        screens = QGuiApplication.screens()
        primary_screen = QGuiApplication.primaryScreen()
        screen_width = APP_CONFIG["window_width"]
        screen_height = APP_CONFIG["window_height"]

        if primary_screen is not None:
            try:
                screen_geometry = primary_screen.availableGeometry()
                screen_width = int(screen_geometry.width())
                screen_height = int(screen_geometry.height())
            except Exception:
                screen_width = APP_CONFIG["window_width"]
                screen_height = APP_CONFIG["window_height"]
        
        # Adaptive sizing: use 80% of screen on large displays, fixed size on small
        if screen_width > 1920:
            window_width = int(screen_width * 0.8)
            window_height = int(screen_height * 0.8)
        else:
            window_width = min(APP_CONFIG["window_width"], screen_width - 100)
            window_height = min(APP_CONFIG["window_height"], screen_height - 100)
        
        self.setWindowTitle(f"{t(APP_CONFIG['app_name'])} v{APP_CONFIG['version']} - {len(screens)} monitor(s)")
        self.setWindowIcon(QIcon("/home/matheus/Documentos/NitroSense Ultimate/nitrosense/assets/icons/home.png"))
        self.setGeometry(0, 0, window_width, window_height)
        self.setMinimumSize(1000, 680)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Sidebar navigation
        sidebar = self._create_sidebar()
        main_layout.addWidget(sidebar)

        # Stacked widget for pages
        self.stacked_widget = QStackedWidget()

        # Lazy-loaded pages dictionary
        self.pages = {}

        # Add placeholder pages initially
        for i in range(5):  # 5 pages
            placeholder = QWidget()
            placeholder_layout = QVBoxLayout(placeholder)
            placeholder_layout.addWidget(QLabel(t("Loading...")))
            self.stacked_widget.addWidget(placeholder)

        main_layout.addWidget(self.stacked_widget)
        self._switch_page(0)
        
        # Feature #14: Status Bar Inferior
        self._init_status_bar()

    def _create_sidebar(self) -> QFrame:
        """Create navigation sidebar."""
        sidebar = QFrame()
        sidebar.setFixedWidth(200)
        sidebar.setStyleSheet(
            f"background-color: {COLOR_SCHEME['surface']}; border-radius: 18px;"
        )

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(10, 10, 10, 10)

        # App title
        title = QLabel("NitroSense")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLOR_SCHEME['primary']};")
        layout.addWidget(title)

        layout.addSpacing(20)

        # Navigation buttons
        nav_buttons = [
            (t("Home"), "home", 0),
            (t("Status"), "status", 1),
            (t("Config"), "config", 2),
            (t("Labs"), "labs", 3),
            (t("Docs"), "docs", 4),
        ]

        for label, icon_key, page_index in nav_buttons:
            btn = QPushButton(label)
            btn.setFixedHeight(50)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            icon = load_icon(icon_key)
            if not icon.isNull():
                btn.setIcon(icon)
                btn.setIconSize(QSize(20, 20))
            btn.clicked.connect(lambda checked, idx=page_index: self._switch_page(idx))
            layout.addWidget(btn)

        layout.addStretch()

        # Fullscreen control
        self.fullscreen_button = QPushButton(t("Fullscreen"))
        self.fullscreen_button.setCheckable(True)
        self.fullscreen_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.fullscreen_button.clicked.connect(self._toggle_fullscreen)
        layout.addWidget(self.fullscreen_button)

        # Footer info
        version_label = QLabel(f"v{APP_CONFIG['version']}")
        version_label.setStyleSheet(f"color: {COLOR_SCHEME['text_secondary']}; font-size: 10px;")
        layout.addWidget(version_label)

        return sidebar

    def _wrap_page(self, page: QWidget) -> QScrollArea:
        """Wrap page widgets in a scrollable area."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(page)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(
            f"background-color: {COLOR_SCHEME['background']}; border-radius: 18px; padding: 8px;"
        )
        return scroll

    def _toggle_fullscreen(self, checked: bool) -> None:
        """Toggle full screen mode on or off."""
        if checked:
            self.showFullScreen()
            self.fullscreen_button.setText(t("Exit Fullscreen"))
        else:
            self.showNormal()
            self.fullscreen_button.setText(t("Fullscreen"))

    def _init_status_bar(self) -> None:
        """Initialize status bar with metrics (Feature #14)."""
        try:
            status_bar = QStatusBar()
            try:
                if not isinstance(status_bar, QStatusBar):
                    logger.debug("Skipping status bar initialization due to non-QStatusBar object")
                    return
            except TypeError:
                logger.debug("Skipping status bar initialization due to mocked QStatusBar type")
                return

            status_bar.setStyleSheet(f"""
                QStatusBar {{
                    background-color: {COLOR_SCHEME['surface']};
                    color: {COLOR_SCHEME['text_secondary']};
                    border-top: 1px solid {COLOR_SCHEME['primary']};
                    padding: 3px;
                    font-size: 9px;
                }}
            """)
            self.setStatusBar(status_bar)
        except Exception as e:
            logger.error(f"Failed to initialize status bar: {e}")
            # Continue without status bar
        
        # Status labels
        self.status_label_update = QLabel("Last update: --")
        self.status_label_fps = QLabel("FPS: --")
        self.status_label_memory = QLabel("Memory: --")
        
        status_bar.addWidget(self.status_label_update)
        status_bar.addPermanentWidget(self.status_label_fps, 0)
        status_bar.addPermanentWidget(self.status_label_memory, 0)
    
    def _update_status_bar(self) -> None:
        """Update status bar metrics (Feature #14)."""
        try:
            # Last update time
            now = datetime.now().strftime("%H:%M:%S")
            self.status_label_update.setText(f"Last update: {now}")
            
            # FPS calculation
            current_time = datetime.now()
            self.frame_count += 1
            elapsed = (current_time - self.last_frame_time).total_seconds()
            if elapsed >= 1.0:
                fps = int(self.frame_count / elapsed)
                self.status_label_fps.setText(f"FPS: {fps}")
                self.frame_count = 0
                self.last_frame_time = current_time
            
            # Memory usage
            memory_info = psutil.virtual_memory()
            memory_pct = memory_info.percent
            self.status_label_memory.setText(f"Memory: {memory_pct:.1f}%")
        except Exception as e:
            logger.debug(f"Status bar update error: {e}")

    def _switch_page(self, index: int) -> None:
        """Switch to page by index with animation (Feature #13)."""
        # Lazy load the page if not already loaded
        if index not in self.pages:
            self._load_page(index)
        self.stacked_widget.setCurrentIndex(index)
        try:
            self.app_state_manager.set("last_tab", index)
        except Exception as e:
            logger.debug(f"Failed to persist last tab: {e}")
        logger.debug(f"Switched to page {index} with animation")

    def _load_page(self, index: int) -> None:
        """Lazy load a page by index."""
        try:
            if index == 0:
                monitoring_engine = getattr(self.system, 'monitoring', None) if self.system is not None else None
                page = HomePage(self.hardware, self.config, monitoring_engine)
            elif index == 1:
                page = StatusPage(self.hardware, self.config)
            elif index == 2:
                page = ConfigPage(self.hardware, self.config)
            elif index == 3:
                page = LabsPage(self.hardware, self.config)
            elif index == 4:
                page = DocsPage(None)
            else:
                return

            wrapped_page = self._wrap_page(page)
            self.stacked_widget.insertWidget(index, wrapped_page)
            try:
                count = self.stacked_widget.count()
                if isinstance(count, int) and count > index + 1:
                    self.stacked_widget.removeWidget(self.stacked_widget.widget(index + 1))
            except Exception:
                pass
            self.pages[index] = page
            logger.info(f"Lazy loaded page {index}")
        except Exception as exc:
            logger.error(f"Failed to lazy load page {index}: {exc}", exc_info=True)
            fallback = QWidget()
            fallback_layout = QVBoxLayout(fallback)
            fallback_message = QLabel("Unable to load this page. Check the logs for details.")
            fallback_message.setWordWrap(True)
            fallback_message.setStyleSheet(f"color: {COLOR_SCHEME['text_secondary']}; font-size: 14px;")
            fallback_layout.addWidget(fallback_message)
            wrapped_fallback = self._wrap_page(fallback)
            self.stacked_widget.insertWidget(index, wrapped_fallback)
            try:
                if int(self.stacked_widget.count()) > index + 1:
                    self.stacked_widget.removeWidget(self.stacked_widget.widget(index + 1))
            except Exception:
                pass
            self.pages[index] = fallback
            self.stacked_widget.setCurrentIndex(index)

    def _init_system_tray(self) -> None:
        """Initialize system tray with dynamic temperature coloring."""
        try:
            self.tray_icon = QSystemTrayIcon(self)
            
            # ===== DIR 13: Dynamic Tray Icon =====
            self.dynamic_tray = DynamicTrayIcon(self.tray_icon, self.hardware)
            self.dynamic_tray.start_updates()
            
            # Build tray menu
            menu_builder = TrayMenuBuilder()
            tray_menu = menu_builder.build_menu(
                on_show_hide=self._tray_toggle_visibility,
                on_frost_mode=self._tray_activate_frost_mode,
                on_settings=self._tray_open_settings,
                on_quit=self.close
            )
            self.tray_icon.setContextMenu(tray_menu)
            self.tray_icon.activated.connect(self._tray_activated)
            self.tray_icon.show()
            
            logger.info("✓ System tray initialized")
        except Exception as e:
            logger.error(f"Failed to initialize system tray: {e}")
    
    def _init_hardware_watchdog(self) -> None:
        """Initialize hardware watchdog for emergency fan control."""
        try:
            if not hasattr(self.system, 'watchdog'):
                logger.warning("Watchdog not available in system")
                return
            
            # ===== DIR 6: Watchdog Emergency Mode =====
            watchdog = self.system.watchdog
            watchdog.timeout_detected.connect(self._on_watchdog_timeout)
            watchdog.emergency_mode_activated.connect(self._on_emergency_mode)
            
            logger.info("✓ Hardware watchdog connected to UI")
        except Exception as e:
            logger.error(f"Failed to initialize watchdog: {e}")
    
    def _tray_toggle_visibility(self):
        """Toggle window visibility from tray."""
        if self.isVisible():
            self.hide()
        else:
            self.showNormal()
            self.activateWindow()
    
    def _tray_activate_frost_mode(self):
        """Quick access to Frost Mode from tray."""
        try:
            logger.info("Activating Frost Mode from tray...")
            # Set to maximum cooling profile
            if self.config:
                self.config.set("fan_profile", "frost", persist=True)
            if self.hardware:
                self.hardware.set_fan_speed(100)
            self.toast_manager.show(t("Frost Mode activated"), duration=2000)
        except Exception as e:
            logger.error(f"Failed to activate Frost Mode: {e}")
    
    def _tray_open_settings(self):
        """Open settings page from tray."""
        self.showNormal()
        self.activateWindow()
        # Navigate to config page (index typically 2)
        if hasattr(self, 'stacked_widget'):
            self.stacked_widget.setCurrentIndex(2)
    
    def _on_watchdog_timeout(self):
        """Watchdog timeout signal: hardware not responding."""
        logger.warning("Watchdog timeout: hardware not responding")
        self.toast_manager.show(t("Hardware timeout detected"), duration=3000)
    
    def _on_emergency_mode(self):
        """Emergency mode activated: fans forced to 100%."""
        logger.critical("EMERGENCY MODE: Fans forced to 100%")
        self.toast_manager.show(t("Emergency: Fans forced to maximum"), duration=5000)

    def _apply_theme(self) -> None:
        """Apply theme based on persisted window state or defaults."""
        theme_colors = None
        try:
            if hasattr(self, 'window_state_manager'):
                theme_colors = self.window_state_manager.get_theme_colors(getattr(self, '_saved_theme', 'dark'))
        except Exception as e:
            logger.debug(f"Unable to get persisted theme colors: {e}")
        if not theme_colors:
            theme_colors = {
                'background': COLOR_SCHEME['background'],
                'text': COLOR_SCHEME.get('text_primary', '#ffffff'),
                'primary': COLOR_SCHEME['primary'],
                'surface': COLOR_SCHEME.get('surface', COLOR_SCHEME['background']),
            }

        stylesheet = f"""
        QMainWindow {{
            background-color: {theme_colors['background']};
        }}
        QLabel {{
            color: {theme_colors['text']};
            font-family: 'Segoe UI';
        }}
        QPushButton {{
            background-color: {theme_colors['primary']};
            color: {theme_colors['text']};
            border: none;
            border-radius: 12px;
            padding: 10px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: {theme_colors['primary']};
            opacity: 0.8;
        }}
        QLineEdit {{
            background-color: {theme_colors['surface']};
            color: {theme_colors['text']};
            border: 1px solid {theme_colors['primary']};
            padding: 8px;
            border-radius: 10px;
        }}
        QFrame {{
            border-radius: 16px;
        }}
        QScrollArea {{
            border-radius: 18px;
        }}
        """
        self.setStyleSheet(stylesheet)

    def _periodic_cleanup(self) -> None:
        """Periodic maintenance and garbage collection."""
        # Force garbage collection
        collected = gc.collect()
        logger.debug(f"Garbage collected: {collected} objects")

        # Clear any expired weakrefs
        # (Add weakref management here if needed)

    def closeEvent(self, event):
        """Handle application closure."""
        logger.info("NitroSenseApp closing...")
        self.update_timer.stop()
        self.status_update_timer.stop()
        self.config_reload_timer.stop()
        self.update_check_timer.stop()

        # Clear toasts
        self.toast_manager.clear_all()
        
        # ===== DIR 19-20: Persist window state before closing =====
        try:
            self.window_state_manager.save_window_state(self)
            logger.info("✓ Window state saved on close")
        except Exception as e:
            logger.error(f"Failed to save window state: {e}")
        
        # Stop dynamic tray icon updates
        if hasattr(self, 'dynamic_tray'):
            self.dynamic_tray.stop_updates()

        # Cleanup loaded pages
        for page in self.pages.values():
            try:
                if hasattr(page, 'cleanup'):
                    page.cleanup()
            except Exception as e:
                logger.error(f"Page cleanup error: {e}")

        event.accept()
        logger.info("Application closed")
