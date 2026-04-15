"""
Home Page - Main monitoring dashboard with LCD display and graph.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSlider, QFrame
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QColor
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from ...core.logger import logger
from ...core.constants import COLOR_SCHEME, THERMAL_CONFIG
from ...core.monitoring import MonitoringEngine
from ...automation.ai_engine import PredictiveAIEngine
from ...automation.fan_control import FanController
from ...hardware.manager import HardwareManager
from ...ui.icon_theme import load_icon_pixmap, load_icon


class MetricCard(QFrame):
    """Custom frame for metric display with value label."""

    def __init__(self, title: str, value: str, subtitle: str, color: str, font_size: int = 42):
        super().__init__()
        self.setStyleSheet(
            f"background-color: {COLOR_SCHEME['surface']}; border-radius: 24px; padding: 24px;"
        )
        self.setMinimumHeight(200)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
        title_label.setStyleSheet(f"color: {COLOR_SCHEME['text_secondary']}; letter-spacing: 0.4px;")
        layout.addWidget(title_label)

        self.value_label = QLabel(value)
        self.value_label.setFont(QFont("Segoe UI", font_size, QFont.Weight.Bold))
        self.value_label.setStyleSheet(f"color: {color};")
        layout.addWidget(self.value_label)

        subtitle_label = QLabel(subtitle)
        subtitle_label.setFont(QFont("Segoe UI", 10))
        subtitle_label.setStyleSheet(f"color: {COLOR_SCHEME['text_secondary']};")
        subtitle_label.setWordWrap(True)
        layout.addWidget(subtitle_label)


class HomePage(QWidget):
    """Home page with temperature display and control."""

    def __init__(self, hardware_manager: HardwareManager, config_manager, monitoring_engine=None):
        try:
            super().__init__()
            self.hardware = hardware_manager
            self.config = config_manager

            # Services
            self.monitoring = monitoring_engine or MonitoringEngine(hardware_manager)
            self.ai_engine = PredictiveAIEngine(
                self.monitoring, hardware_manager, config_manager
            )
            self.fan_controller = FanController(hardware_manager, config_manager)
            self.graph_paused = False
            self.dark_mode = False
            self.auto_mode = False  # Start in manual mode

            # UI
            self._init_ui()

            # Update timer
            self.update_timer = QTimer()
            self.update_timer.timeout.connect(self._update_display)
            self.update_timer.start(THERMAL_CONFIG.get("ui_update_interval", 2000))

            logger.info("HomePage initialized")
            
        except Exception as e:
            logger.critical(f"Failed to initialize home page: {e}", exc_info=True)
            self._setup_error_state(str(e))

    def _init_ui(self) -> None:
        """Initialize UI layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(18)

        header = QLabel("NitroSense Ultimate")
        header.setFont(QFont("Segoe UI", 22, QFont.Weight.DemiBold))
        header.setStyleSheet(f"color: {COLOR_SCHEME['primary']};")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        subtitle = QLabel("Real-time thermal diagnostics and fan control")
        subtitle.setFont(QFont("Segoe UI", 10))
        subtitle.setStyleSheet(f"color: {COLOR_SCHEME['text_secondary']};")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        layout.addLayout(self.init_temperature_display())
        layout.addWidget(self.init_graph())
        layout.addLayout(self.init_controls())
        layout.addLayout(self.init_status_area())
        layout.addStretch()

    def init_temperature_display(self) -> QVBoxLayout:
        """Create the main temperature and summary panel with human-centered hierarchy."""
        layout = QHBoxLayout()
        layout.setSpacing(18)

        self.cpu_card = self._create_metric_card(
            title="CPU Temperature",
            value="-- °C",
            subtitle="Core thermal load",
            color=COLOR_SCHEME['primary'],
            font_size=56,
        )
        self.gpu_card = self._create_metric_card(
            title="GPU Temperature",
            value="-- °C",
            subtitle="Graphics processor",
            color=COLOR_SCHEME['success'],
            font_size=44,
        )
        self.rpm_card = self._create_metric_card(
            title="Fan RPM",
            value="--",
            subtitle="Mechanical response",
            color=COLOR_SCHEME['warning'],
            font_size=44,
        )

        layout.addWidget(self.cpu_card, 3)
        layout.addWidget(self.gpu_card, 2)
        layout.addWidget(self.rpm_card, 2)

        # Additional info labels
        info_layout = QHBoxLayout()
        info_layout.setSpacing(16)
        
        self.cooldown_label = QLabel("Cooldown: --")
        self.cooldown_label.setFont(QFont("Segoe UI", 10))
        self.cooldown_label.setStyleSheet(f"color: {COLOR_SCHEME['text_secondary']};")
        info_layout.addWidget(self.cooldown_label)
        
        self.trend_label = QLabel("Trend: --")
        self.trend_label.setFont(QFont("Segoe UI", 10))
        self.trend_label.setStyleSheet(f"color: {COLOR_SCHEME['text_secondary']};")
        info_layout.addWidget(self.trend_label)
        
        info_layout.addStretch()
        
        temp_layout = QVBoxLayout()
        temp_layout.addLayout(layout)
        temp_layout.addLayout(info_layout)

        return temp_layout

    def _create_metric_card(
        self,
        title: str,
        value: str,
        subtitle: str,
        color: str,
        font_size: int = 42,
    ) -> MetricCard:
        return MetricCard(title, value, subtitle, color, font_size)

    def init_graph(self) -> QWidget:
        """Create temperature history graph."""
        graph_widget = QFrame()
        graph_widget.setStyleSheet(
            f"background-color: {COLOR_SCHEME['surface']}; border-radius: 18px; padding: 12px;"
        )
        layout = QVBoxLayout(graph_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("Temperature History")
        title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLOR_SCHEME['primary']};")
        layout.addWidget(title)

        self.figure = Figure(figsize=(10, 3), dpi=100, facecolor='#2d2d2d')
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)
        self.ax.set_facecolor('#2d2d2d')
        self.ax.tick_params(colors=COLOR_SCHEME['text_secondary'])

        layout.addWidget(self.canvas)
        return graph_widget

    def init_controls(self) -> QHBoxLayout:
        """Create control buttons and quick user actions."""
        layout = QHBoxLayout()
        layout.setSpacing(16)

        frost_btn = QPushButton("Frost Mode")
        frost_btn.clicked.connect(self._frost_mode)
        self._style_button(frost_btn)
        layout.addWidget(frost_btn)

        auto_btn = QPushButton("Modo Automatico")
        auto_btn.clicked.connect(self._enable_auto_mode)
        self._style_button(auto_btn)
        layout.addWidget(auto_btn)

        slider_card = QFrame()
        slider_card.setStyleSheet(
            f"background-color: {COLOR_SCHEME['surface']}; border-radius: 16px; padding: 12px;"
        )
        slider_layout = QVBoxLayout(slider_card)
        slider_layout.setContentsMargins(10, 10, 10, 10)
        slider_layout.setSpacing(8)

        self.fan_speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.fan_speed_slider.setMaximum(100)
        self.fan_speed_slider.setValue(50)
        self.fan_speed_slider.setSingleStep(5)
        self.fan_speed_slider.setPageStep(10)
        self.fan_speed_slider.setEnabled(True)  # Start enabled in manual mode
        self.fan_speed_slider.valueChanged.connect(self._sync_slider_label)
        self.fan_speed_slider.sliderReleased.connect(self._apply_fan_speed)
        self.fan_speed_slider.setStyleSheet(
            "QSlider::groove:horizontal { height: 8px; background: #2b3340; border-radius: 4px; }"
            "QSlider::handle:horizontal { background: #2f80ed; width: 16px; margin: -4px 0; border-radius: 8px; }"
        )
        slider_layout.addWidget(self.fan_speed_slider)

        self.fan_label = QLabel("Fan: 50%")
        self.fan_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
        self.fan_label.setStyleSheet(f"color: {COLOR_SCHEME['primary']};")
        slider_layout.addWidget(self.fan_label, alignment=Qt.AlignmentFlag.AlignRight)

        layout.addWidget(slider_card, 2)

        self.pause_button = QPushButton("Pause Graph")
        self.pause_button.clicked.connect(self._toggle_pause)
        self._style_button(self.pause_button)
        layout.addWidget(self.pause_button)

        self.theme_toggle_button = QPushButton("Dark Mode")
        self.theme_toggle_button.clicked.connect(self._toggle_theme)
        self._style_button(self.theme_toggle_button)
        layout.addWidget(self.theme_toggle_button)

        layout.addStretch()
        return layout

    def init_status_area(self) -> QHBoxLayout:
        """Create status display area."""
        layout = QHBoxLayout()
        layout.setSpacing(16)

        # Mode indicator
        self.mode_label = QLabel("Mode: Manual")
        self.mode_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
        self.mode_label.setStyleSheet(f"color: {COLOR_SCHEME['text_secondary']};")
        layout.addWidget(self.mode_label)

        # Status message
        self.status_label = QLabel("System ready")
        self.status_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
        self.status_label.setStyleSheet(f"color: {COLOR_SCHEME['text_primary']};")
        layout.addWidget(self.status_label)

        layout.addStretch()
        return layout

    def _style_button(self, button: QPushButton) -> None:
        """Apply consistent styling to buttons."""
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setStyleSheet(
            "QPushButton {"
            "  color: #ffffff;"
            "  background-color: #2f80ed;"
            "  border: none;"
            "  border-radius: 12px;"
            "  padding: 10px 18px;"
            "  font-weight: bold;"
            "}"
            "QPushButton:hover {"
            "  background-color: #4798ff;"
            "}"
            "QPushButton:pressed {"
            "  background-color: #1f5fc2;"
            "}"
        )

    def _sync_slider_label(self, value: int) -> None:
        try:
            self.fan_label.setText(f"Fan: {value}%")
        except (AttributeError, ValueError) as e:
            logger.error(f"Failed syncing slider label: {e}")

    def _apply_fan_speed(self) -> None:
        try:
            value = self.fan_speed_slider.value()
            self.fan_controller.set_fan_speed(value)
            self.status_label.setText(f"Fan speed set to {value}%")
            self.auto_mode = False  # Disable auto mode when slider is used
            self.mode_label.setText("Mode: Manual")
            self.fan_speed_slider.setEnabled(True)  # Ensure slider is enabled in manual mode
        except (AttributeError, RuntimeError, ValueError) as e:
            logger.error(f"Failed applying fan speed: {e}")

    def _enable_auto_mode(self) -> None:
        try:
            self.auto_mode = True
            self.mode_label.setText("Mode: Auto")
            self.status_label.setText("Auto mode enabled")
            self.fan_speed_slider.setEnabled(False)  # Disable slider in auto mode
            logger.info("Auto mode manually enabled")
        except (AttributeError, RuntimeError) as e:
            logger.error(f"Failed to enable auto mode: {e}")

    def _setup_error_state(self, message: str) -> None:
        """Fallback home page state when initialization fails."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        error_label = QLabel("Home page unavailable due to an initialization error.")
        error_label.setWordWrap(True)
        error_label.setStyleSheet(f"color: {COLOR_SCHEME['text_secondary']}; font-size: 14px;")
        layout.addWidget(error_label)

        details = QLabel(message)
        details.setWordWrap(True)
        details.setStyleSheet("color: #ff6b6b; font-size: 12px;")
        layout.addWidget(details)

    def _update_display(self) -> None:
        """Update display with latest metrics."""
        if not self.isVisible() or self.isMinimized():
            return

        try:
            metrics = self.monitoring.get_system_metrics()

            cpu_temp = metrics.get("cpu_temp")
            gpu_temp = metrics.get("gpu_temp")
            fan_rpm = metrics.get("fan_rpm")

            # Temperature display
            if cpu_temp is not None:
                self.cpu_card.value_label.setText(f"{cpu_temp:.1f}°C")
                self._update_color(cpu_temp)
                if hasattr(self, 'cooldown_label'):
                    self.cooldown_label.setText(f"Cooldown: {self.ai_engine.get_cooldown_estimate(cpu_temp)}")

            if gpu_temp is not None:
                self.gpu_card.value_label.setText(f"{gpu_temp:.1f}°C")

            # RPM display
            if fan_rpm is not None:
                self.rpm_card.value_label.setText(str(fan_rpm))

            # Thermal gradient
            temp_delta = self.monitoring.get_temperature_delta()
            trend = self.ai_engine.calculate_thermal_gradient(
                temp_delta
            )
            if hasattr(self, 'trend_label'):
                self.trend_label.setText(f"Trend: {trend}")

            profile_event = self.ai_engine.refresh_profile_state()
            if profile_event == "closed":
                if hasattr(self, 'status_label'):
                    self.status_label.setText("Game closed, silent mode restored")

            # Calculate and apply speed
            if cpu_temp and not hasattr(self, '_frost_mode_active') and self.auto_mode:
                required_speed = self.ai_engine.calculate_required_speed(
                    cpu_temp, temp_delta
                )
                self.fan_controller.set_fan_speed(required_speed)
                self.fan_label.setText(f"Fan: {required_speed}%")
                self.fan_speed_slider.setValue(required_speed)  # Sync slider

            # Re-enable auto mode if temperature exceeds 75°C
            if cpu_temp and cpu_temp >= 75 and not self.auto_mode:
                self.auto_mode = True
                if hasattr(self, 'mode_label'):
                    self.mode_label.setText("Mode: Auto (Temp > 75°C)")
                self.fan_speed_slider.setEnabled(False)  # Disable slider when auto mode is re-enabled
                logger.info("Auto mode re-enabled due to high temperature")

            # Update graph
            if not self.graph_paused:
                self._update_graph()
            else:
                if hasattr(self, 'status_label'):
                    self.status_label.setText("Graph updates paused")

            # Check watchdog
            if cpu_temp and fan_rpm is not None:
                if self.ai_engine.check_fan_watchdog(cpu_temp, fan_rpm):
                    if hasattr(self, 'status_label'):
                        self.status_label.setText("Fan Stall Detected!")

        except Exception as e:
            logger.error(f"Display update error: {e}")

    def _update_color(self, temp: float) -> None:
        """Update color based on temperature."""
        if temp < 45:
            color = "#0099ff"  # Cold
        elif temp < 60:
            color = "#34c759"  # Normal
        elif temp < 75:
            color = "#ff9500"  # Warm
        elif temp < 90:
            color = "#ff3b30"  # Hot
        else:
            color = "#ff0033"  # Critical

        # Update temp label if it exists
        self.cpu_card.value_label.setStyleSheet(f"color: {color};")

    def _update_graph(self) -> None:
        """Update temperature history graph."""
        try:
            temps = self.monitoring.get_temperature_trend()
            if temps:
                self.ax.clear()
                self.ax.plot(temps, color=COLOR_SCHEME['primary'], linewidth=2)
                self.ax.fill_between(range(len(temps)), temps, alpha=0.3, color=COLOR_SCHEME['primary'])
                self.ax.set_ylim(30, 100)
                self.ax.set_title("Temperature History", color=COLOR_SCHEME['text_primary'])
                self.ax.grid(True, alpha=0.3)
                self.canvas.draw_idle() 

        except Exception as e:
            logger.debug(f"Graph update error: {e}")

    def _frost_mode(self) -> None:
        """Activate Frost Mode."""
        try:
            logger.info("Frost mode activated")
            self.fan_controller.frost_mode_engage(120)
            self.status_label.setText("FROST MODE ACTIVE (120s)")
        except Exception as e:
            logger.error(f"Frost mode error: {e}")

    def _toggle_pause(self) -> None:
        """Toggle graph update pause mode."""
        try:
            self.graph_paused = not self.graph_paused
            label = "Resume Graph" if self.graph_paused else "Pause Graph"
            self.pause_button.setText(label)
        except Exception as e:
            logger.error(f"Toggle pause error: {e}")

    def _toggle_theme(self) -> None:
        """Toggle theme state and refresh the action label."""
        try:
            self.dark_mode = not self.dark_mode
            theme_text = "Light Mode" if self.dark_mode else "Dark Mode"
            self.theme_toggle_button.setText(theme_text)
            self.status_label.setText(
                "Dark theme enabled" if self.dark_mode else "Light theme enabled"
            )
        except Exception as e:
            logger.error(f"Toggle theme error: {e}")

    def _apply_icon_to_label(self, label, icon_name, fallback_text, size):
        """Apply icon to label."""
        try:
            pixmap = load_icon_pixmap(icon_name, size)
            if pixmap:
                label.setPixmap(pixmap)
            else:
                label.setText(fallback_text)
        except Exception as e:
            logger.error(f"Apply icon error: {e}")
            label.setText(fallback_text)

    def cleanup(self) -> None:
        """Cleanup on page close."""
        try:
            self.update_timer.stop()
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
