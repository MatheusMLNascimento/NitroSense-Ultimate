"""
Status Page - System health monitoring with LED indicators.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame
)
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QColor, QPalette, QFont
import psutil
from ...core.logger import logger
from ...core.constants import COLOR_SCHEME
from ...core.monitoring import MonitoringEngine
from ...hardware.interface import HardwareInterface
from ..icon_theme import load_icon_pixmap


class StatusPage(QWidget):
    """System status monitoring page."""
    __slots__ = ('hardware', 'config', 'monitoring', 'update_timer', 'status_blocks', 'vital_labels', 'perf_labels')

    def _apply_icon_to_label(self, label: QLabel, icon_name: str, fallback_text: str, size: QSize) -> None:
        """Load an icon into a QLabel or fallback to text if missing."""
        try:
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setFixedSize(size)
            label.setContentsMargins(0, 0, 0, 0)

            pixmap = load_icon_pixmap(icon_name, size)
            if pixmap is not None:
                label.setPixmap(pixmap)
                label.setScaledContents(True)
            else:
                label.setFont(QFont("Segoe UI Emoji", 20, QFont.Weight.Bold))
                label.setText(fallback_text)
        except Exception as exc:
            logger.error(f"Failed loading icon {icon_name}: {exc}", exc_info=True)
            label.setText(fallback_text)

    def __init__(self, hardware_manager: HardwareInterface, config_manager):
        super().__init__()
        self.hardware = hardware_manager
        self.config = config_manager
        self.monitoring = MonitoringEngine(hardware_manager)

        try:
            self._init_ui()
        except Exception as exc:
            logger.error(f"Failed initializing StatusPage UI: {exc}", exc_info=True)
            self._init_error_ui(str(exc))

        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_status)
        self.update_timer.start(2000)

        logger.info("StatusPage initialized")

    def _init_ui(self) -> None:
        """Initialize status page layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(18)
        self.status_blocks = {}

        title = QLabel("System Status")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLOR_SCHEME['primary']};")
        layout.addWidget(title)

        subtitle = QLabel("Veja os três indicadores vitais primeiro e os detalhes secundários em blocos discretos.")
        subtitle.setFont(QFont("Segoe UI", 10))
        subtitle.setStyleSheet(f"color: {COLOR_SCHEME['text_secondary']};")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        vital_grid = QGridLayout()
        vital_grid.setSpacing(14)
        vital_grid.setColumnStretch(0, 1)
        vital_grid.setColumnStretch(1, 1)
        vital_grid.setColumnStretch(2, 1)

        self.vital_labels = {}
        vital_metrics = [
            ("CPU", "cpu", "°C"),
            ("GPU", "gpu", "°C"),
            ("Fan RPM", "fan_rpm", "RPM"),
        ]

        for col, (label_text, key, unit) in enumerate(vital_metrics):
            card = QFrame()
            card.setStyleSheet(
                "background-color: #242730; border-radius: 20px; padding: 18px;"
            )
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(14, 14, 14, 14)
            card_layout.setSpacing(10)

            label = QLabel(label_text)
            label.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
            label.setStyleSheet(f"color: {COLOR_SCHEME['text_secondary']};")
            card_layout.addWidget(label)

            value_label = QLabel("--" + unit)
            value_label.setFont(QFont("Segoe UI", 44, QFont.Weight.Bold))
            value_label.setStyleSheet(f"color: {COLOR_SCHEME['primary']};")
            card_layout.addWidget(value_label)

            status_label = QLabel("Verificando...")
            status_label.setFont(QFont("Segoe UI", 10))
            status_label.setStyleSheet(f"color: {COLOR_SCHEME['text_secondary']};")
            card_layout.addWidget(status_label)

            self.vital_labels[key] = value_label
            vital_grid.addWidget(card, 0, col)

        layout.addLayout(vital_grid)

        grid = QGridLayout()
        grid.setSpacing(18)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        blocks = [
            ("NBFC Service", "nbfc", "NBFC"),
            ("Temperature Sensors", "sensors", "TEMP"),
            ("Fan Hardware", "fan", "FAN"),
            ("System Memory", "memory", "MEM"),
            ("Disk I/O", "disk", "DSK"),
        ]

        for idx, (name, key, icon) in enumerate(blocks):
            block = self._create_status_block(name, key, icon)
            self.status_blocks[key] = block
            grid.addWidget(block, idx // 2, idx % 2)

        layout.addLayout(grid)

        perf_title = QLabel("Detalhes de desempenho")
        perf_title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        perf_title.setStyleSheet(f"color: {COLOR_SCHEME['primary']}; margin-top: 20px;")
        layout.addWidget(perf_title)

        perf_layout = QHBoxLayout()
        perf_layout.setSpacing(14)
        self.perf_labels = {}

        perf_metrics = [
            ("Avg Temp Control", "avg_temp", "°C"),
            ("Fan Efficiency", "fan_eff", "%"),
            ("Update Rate", "update_rate", "Hz"),
            ("Memory Usage", "mem_usage", "%"),
        ]

        for name, key, unit in perf_metrics:
            card = QFrame()
            card.setStyleSheet(
                "background-color: #242730; border-radius: 16px; padding: 14px;"
            )
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(10, 10, 10, 10)
            card_layout.setSpacing(8)

            label = QLabel(name)
            label.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
            label.setStyleSheet(f"color: {COLOR_SCHEME['text_secondary']};")
            card_layout.addWidget(label)

            value_label = QLabel("--" + unit)
            value_label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
            value_label.setStyleSheet(f"color: {COLOR_SCHEME['text_primary']};")
            card_layout.addWidget(value_label)

            self.perf_labels[key] = value_label
            perf_layout.addWidget(card)

        layout.addLayout(perf_layout)
        layout.addStretch()

    def _create_status_block(self, name: str, icon_key: str, fallback_text: str) -> QFrame:
        """Create a status indicator block with minimal iconography."""
        frame = QFrame()
        frame.setStyleSheet(
            "background-color: #ffffff; border: 2px solid #ffffff; border-radius: 20px;"
        )
        frame.setFixedHeight(250)
        try:
            layout = QVBoxLayout(frame)
            layout.setContentsMargins(20, 20, 20, 20)
            layout.setSpacing(15)

            icon_label = QLabel()
            self._apply_icon_to_label(icon_label, icon_key, fallback_text, QSize(100, 100))
            layout.addWidget(icon_label, alignment=Qt.AlignmentFlag.AlignHCenter)

            name_container = QFrame()
            name_container.setStyleSheet(
                "background: #f8f9ff; border-radius: 14px;"
            )
            name_layout = QHBoxLayout(name_container)
            name_layout.setContentsMargins(10, 8, 10, 8)
            name_layout.setSpacing(10)

            led = QLabel("●")
            led.setFont(QFont("Arial", 14))
            led.setFixedWidth(16)
            led.setAlignment(Qt.AlignmentFlag.AlignCenter)
            led.setStyleSheet("color: #007aff;")
            name_layout.addWidget(led)

            name_label = QLabel(name)
            name_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            name_label.setStyleSheet("color: #111111;")
            name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            name_layout.addWidget(name_label)
            name_layout.addStretch()

            layout.addWidget(name_container)

            status_label = QLabel("Checking...")
            status_label.setFont(QFont("Segoe UI", 10))
            status_label.setStyleSheet(f"color: {COLOR_SCHEME['text_primary']};")
            status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(status_label)

            detail_label = QLabel("…")
            detail_label.setWordWrap(True)
            detail_label.setFont(QFont("Segoe UI", 9))
            detail_label.setStyleSheet(f"color: {COLOR_SCHEME['text_secondary']};")
            layout.addWidget(detail_label)

            setattr(frame, 'led', led)
            setattr(frame, 'name_container', name_container)
            setattr(frame, 'status_label', status_label)
            setattr(frame, 'detail_label', detail_label)
        except Exception as exc:
            logger.error(f"Failed creating status block for {name}: {exc}", exc_info=True)
            frame = QFrame()
            frame.setStyleSheet(f"background-color: {COLOR_SCHEME['surface']}; border-radius: 16px;")
            fallback_layout = QVBoxLayout(frame)
            fallback_label = QLabel(f"{name} (status unavailable)")
            fallback_label.setWordWrap(True)
            fallback_label.setStyleSheet(f"color: {COLOR_SCHEME['text_secondary']};")
            fallback_layout.addWidget(fallback_label)
        return frame

    def _update_status(self) -> None:
        """Update health status."""
        try:
            metrics = self.monitoring.get_system_metrics()

            if getattr(self, 'vital_labels', None):
                if metrics.get("cpu_temp") is not None:
                    self.vital_labels["cpu"].setText(f"{metrics['cpu_temp']:.1f}°C")
                if metrics.get("gpu_temp") is not None:
                    self.vital_labels["gpu"].setText(f"{metrics['gpu_temp']:.1f}°C")
                if metrics.get("fan_rpm") is not None:
                    self.vital_labels["fan_rpm"].setText(str(metrics['fan_rpm']))

            cpu_temp = metrics.get("cpu_temp")
            cpu_usage = psutil.cpu_percent(interval=0)
            gpu_temp = metrics.get("gpu_temp")
            gpu_usage, gpu_mem_used, gpu_mem_total = self._get_gpu_stats()

            self._update_block(
                "nbfc",
                getattr(self.hardware, "nbfc_available", False),
                "NBFC Active",
                "Service responsive",
            )

            deps = self.hardware.check_dependencies()
            self._update_block(
                "sensors",
                deps.get("sensors", False),
                "Sensors OK",
                "Temperature sensors online",
            )

            fan_ok = metrics.get("fan_rpm", 0) >= 0
            self._update_block(
                "fan",
                fan_ok,
                f"RPM: {metrics.get('fan_rpm', '--')}",
                "Fan hardware responding",
            )

            ram_usage = metrics.get("ram_usage", 0)
            ram = psutil.virtual_memory()
            self._update_block(
                "memory",
                ram_usage < 90,
                f"RAM: {ram_usage:.0f}% Used",
                f"{ram.available / 1024**3:.1f}GB free of {ram.total / 1024**3:.1f}GB",
            )

            disk_usage = metrics.get("disk_usage", 0)
            self._update_block(
                "disk",
                disk_usage < 90,
                f"Disk: {disk_usage:.0f}% Used",
                "Storage healthy",
            )

            # Update performance metrics
            self._update_performance_metrics(metrics)

        except Exception as e:
            logger.error(f"Status update error: {e}")

    def _update_performance_metrics(self, metrics: dict) -> None:
        """Update performance metrics labels."""
        try:
            # Average temperature control (simplified)
            temps = [t for t in [metrics.get("cpu_temp"), metrics.get("gpu_temp")] if t is not None]
            avg_temp = sum(temps) / len(temps) if temps else 0
            self.perf_labels["avg_temp"].setText(f"{avg_temp:.1f}°C")

            # Fan efficiency (RPM vs expected)
            fan_rpm = metrics.get("fan_rpm", 0)
            expected_rpm = 2000  # Simplified
            efficiency = min(100, (fan_rpm / expected_rpm) * 100) if expected_rpm > 0 else 0
            self.perf_labels["fan_eff"].setText(f"{efficiency:.0f}%")

            # Update rate (simplified as 0.5 Hz since timer is 2s)
            self.perf_labels["update_rate"].setText("0.5 Hz")

            # Memory usage
            mem_usage = metrics.get("ram_usage", 0)
            self.perf_labels["mem_usage"].setText(f"{mem_usage:.1f}%")

        except Exception as e:
            logger.error(f"Performance metrics update error: {e}")

    def _update_block(self, key: str, is_ok: bool, status_text: str, detail_text: str = "") -> None:
        """Update status block."""
        if key not in self.status_blocks:
            return

        block = self.status_blocks[key]
        color = "#34c759" if is_ok else "#ff9500"
        if hasattr(block, 'led'):
            block.led.setStyleSheet(f"color: {color};")
        if hasattr(block, 'name_container'):
            block.name_container.setStyleSheet(
                f"background: {color}20; border-radius: 14px;"
            )
        if hasattr(block, 'status_label'):
            block.status_label.setText(status_text)
        if hasattr(block, 'detail_label') and detail_text:
            block.detail_label.setText(detail_text)

    def _get_gpu_stats(self):
        """Query NVIDIA GPU usage and memory if available."""
        try:
            gpu_usage = self.hardware.get_gpu_usage()
            gpu_stats = self.hardware.get_gpu_memory_stats()
            if gpu_stats and len(gpu_stats) == 3:
                mem_usage, mem_used, mem_total = gpu_stats
                return gpu_usage, mem_used, mem_total
        except Exception as exc:
            logger.debug(f"GPU stats query failed: {exc}", exc_info=True)

        return None, None, None

    def _init_error_ui(self, message: str) -> None:
        """Fallback status page state when initialization fails."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        error_label = QLabel("Status page unavailable due to an initialization error.")
        error_label.setWordWrap(True)
        error_label.setStyleSheet(f"color: {COLOR_SCHEME['text_secondary']}; font-size: 14px;")
        layout.addWidget(error_label)

        details = QLabel(message)
        details.setWordWrap(True)
        details.setStyleSheet("color: #f5a623; font-size: 12px;")
        layout.addWidget(details)

    def cleanup(self) -> None:
        """Cleanup on close."""
        self.update_timer.stop()
