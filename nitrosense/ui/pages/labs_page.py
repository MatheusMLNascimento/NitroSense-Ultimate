"""
Labs Page - Advanced testing and diagnostics.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTextEdit, QFrame, QGridLayout
)
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QFont
from pathlib import Path
from typing import Optional
from ...core.logger import logger
from ...core.constants import COLOR_SCHEME
from ...hardware.manager import HardwareManager
from ...security.diagnostics import SecurityAndDiagnostics
from ..icon_theme import load_icon_pixmap


class LabsPage(QWidget):
    """Labs page for testing and diagnostics."""

    def __init__(self, hardware_manager: HardwareManager, config_manager):
        super().__init__()
        self.hardware = hardware_manager
        self.config = config_manager

        if hardware_manager is not None:
            self._init_ui()
            logger.info("LabsPage initialized")
            self._run_tests()
        else:
            # For testing, skip UI initialization
            self.test_blocks = {}
            self.console = None

    def _init_ui(self) -> None:
        """Initialize labs page."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("Advanced Labs & Diagnostics")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLOR_SCHEME['primary']};")
        layout.addWidget(title)

        description = QLabel("Run diagnostics, hardware checks, and quick report generation.")
        description.setFont(QFont("Segoe UI", 10))
        description.setStyleSheet(f"color: {COLOR_SCHEME['text_secondary']}; margin-bottom: 16px;")
        layout.addWidget(description)

        # Temperature Display Section
        temp_title = QLabel("Current Temperatures")
        temp_title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        temp_title.setStyleSheet(f"color: {COLOR_SCHEME['primary']}; margin-top: 18px;")
        layout.addWidget(temp_title)

        temp_layout = QHBoxLayout()
        temp_layout.setSpacing(20)

        self.cpu_temp_label = QLabel("CPU: -- °C")
        self.cpu_temp_label.setFont(QFont("Courier New", 14))
        self.cpu_temp_label.setStyleSheet(f"color: {COLOR_SCHEME['text_primary']};")
        temp_layout.addWidget(self.cpu_temp_label)

        self.gpu_temp_label = QLabel("GPU: -- °C")
        self.gpu_temp_label.setFont(QFont("Courier New", 14))
        self.gpu_temp_label.setStyleSheet(f"color: {COLOR_SCHEME['text_primary']};")
        temp_layout.addWidget(self.gpu_temp_label)

        refresh_temp_btn = self._create_action_button("Refresh Temps", self._refresh_temps)
        temp_layout.addWidget(refresh_temp_btn)

        temp_layout.addStretch()
        layout.addLayout(temp_layout)

        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(14)

        button_layout.addWidget(self._create_action_button("Test NBFC", self._test_nbfc))
        button_layout.addWidget(self._create_action_button("Test NVIDIA", self._test_nvidia))
        button_layout.addWidget(self._create_action_button("Test Sensors", self._test_sensors))
        button_layout.addWidget(self._create_action_button("Generate Report", self._generate_report))

        layout.addLayout(button_layout)

        # Output console
        console_label = QLabel("Console Output")
        console_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        console_label.setStyleSheet(f"color: {COLOR_SCHEME['text_primary']}; margin-top: 18px;")
        layout.addWidget(console_label)

        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setStyleSheet(
            f"background-color: {COLOR_SCHEME['surface']}; color: {COLOR_SCHEME['text_primary']}; font-family: 'Courier New'; border: 1px solid #2b3340; border-radius: 14px;"
        )
        self.console.setFixedHeight(260)
        layout.addWidget(self.console)

        # Test Status Section
        test_title = QLabel("Test Status")
        test_title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        test_title.setStyleSheet(f"color: {COLOR_SCHEME['primary']}; margin-top: 24px;")
        layout.addWidget(test_title)

        test_grid = QGridLayout()
        test_grid.setSpacing(15)

        self.test_blocks = {}

        self.test_files = {
            "ai": "test_ai_engine.py",
            "config": "test_config_manager.py",
            "error": "test_error_codes.py",
            "fan": "test_fan_control.py",
            "home": "test_home_page.py",
            "monitoring": "test_monitoring.py",
            "watchdog": "test_watchdog.py",
        }

        blocks = [
            ("AI Engine Tests", "ai", "🧪"),
            ("Config Manager Tests", "config", "🧪"),
            ("Error Codes Tests", "error", "🧪"),
            ("Fan Control Tests", "fan", "🧪"),
            ("Home Page Tests", "home", "🧪"),
            ("Monitoring Tests", "monitoring", "🧪"),
            ("Watchdog Tests", "watchdog", "🧪"),
        ]

        for idx, (name, key, icon) in enumerate(blocks):
            block = self._create_status_block(name, key, icon)
            self.test_blocks[key] = block
            test_grid.addWidget(block, idx // 2, idx % 2)

        layout.addLayout(test_grid)

        layout.addStretch()

    def _create_action_button(self, text: str, handler) -> QPushButton:
        button = QPushButton(text)
        button.clicked.connect(handler)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setStyleSheet(
            "QPushButton {"
            "  color: #ffffff;"
            "  background-color: #2f80ed;"
            "  border: none;"
            "  border-radius: 12px;"
            "  padding: 12px 18px;"
            "  font-weight: bold;"
            "}"
            "QPushButton:hover {"
            "  background-color: #4a94ff;"
            "}"
            "QPushButton:pressed {"
            "  background-color: #1f5fc2;"
            "}"
        )
        return button

    def _refresh_temps(self) -> None:
        """Refresh and display current CPU and GPU temperatures."""
        try:
            cpu_temp = self._get_cpu_temp()
            gpu_temp = self._get_gpu_temp()

            self.cpu_temp_label.setText(f"CPU: {cpu_temp:.1f} °C" if cpu_temp else "CPU: N/A")
            self.gpu_temp_label.setText(f"GPU: {gpu_temp:.1f} °C" if gpu_temp else "GPU: N/A")
        except Exception as e:
            self.cpu_temp_label.setText("CPU: Error")
            self.gpu_temp_label.setText("GPU: Error")
            logger.error(f"Temp refresh error: {e}")

    def _get_cpu_temp(self) -> Optional[float]:
        """Get CPU temperature."""
        try:
            success, output = self.hardware.run_nbfc("status -a")
            if success:
                # Parse temperature from NBFC output
                for line in output.split('\n'):
                    if 'Temperature' in line:
                        temp_str = line.split(':')[-1].strip().replace('°C', '').strip()
                        return float(temp_str)
        except Exception as e:
            logger.debug(f"NBFC CPU temp failed: {e}")

        # Fallback to ACPI
        try:
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                temp_value = int(f.read().strip())
                return temp_value / 1000.0
        except Exception as e:
            logger.debug(f"ACPI CPU temp failed: {e}")

        return None

    def _get_gpu_temp(self) -> Optional[float]:
        """Get GPU temperature."""
        try:
            import subprocess
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                return float(result.stdout.strip().split('\n')[0])
        except Exception as e:
            logger.debug(f"GPU temp failed: {e}")

        return None

    def _test_nbfc(self) -> None:
        """Test NBFC service."""
        try:
            self.console.clear()
            self.console.append("Testing NBFC service...\n")

            success, output = self.hardware.run_nbfc("status -a")
            self.console.append(f"Success: {success}\n")
            self.console.append(f"Output:\n{output}")
            
        except Exception as e:
            self.console.append(f"NBFC test failed: {e}")
            logger.error(f"NBFC test error: {e}")

    def _test_nvidia(self) -> None:
        """Test NVIDIA GPU."""
        try:
            import subprocess

            self.console.clear()
            self.console.append("Testing NVIDIA GPU...\n")

            result = subprocess.run(
                ["nvidia-smi", "-L"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            self.console.append(f"GPUs Found:\n{result.stdout}")
            
        except subprocess.TimeoutExpired:
            self.console.append("NVIDIA test timed out")
        except FileNotFoundError:
            self.console.append("nvidia-smi not found")
        except Exception as e:
            self.console.append(f"NVIDIA test error: {e}")
            logger.error(f"NVIDIA test error: {e}")

    def _test_sensors(self) -> None:
        """Test lm-sensors."""
        try:
            import subprocess

            self.console.clear()
            self.console.append("Testing lm-sensors...\n")

            result = subprocess.run(
                ["sensors"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            self.console.append(result.stdout)
            
        except subprocess.TimeoutExpired:
            self.console.append("Sensors test timed out")
        except FileNotFoundError:
            self.console.append("sensors command not found")
        except Exception as e:
            self.console.append(f"Sensors test error: {e}")
            logger.error(f"Sensors test error: {e}")

    def _generate_report(self) -> None:
        """Generate final diagnostic report in TXT format."""
        if self.console is None:
            return  # UI not initialized
        self.console.clear()
        self.console.append("Generating diagnostics report...\n")
        diagnostics = SecurityAndDiagnostics(self.hardware, None)
        err, report_path = diagnostics.generate_diagnostic_report()

        if err == 0 and report_path:
            self.console.append(f"Report created at: {report_path}\n")
        else:
            self.console.append("Failed to create diagnostics report.\n")

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

    def _create_status_block(self, name: str, icon_key: str, fallback_text: str) -> QFrame:
        """Create a status indicator block with minimal iconography."""
        frame = QFrame()
        frame.setStyleSheet(
            f"background-color: {COLOR_SCHEME['surface']}; border: 3px solid {COLOR_SCHEME['primary']}; border-radius: 20px;"
        )
        frame.setFixedHeight(220)
        try:
            layout = QVBoxLayout(frame)
            layout.setContentsMargins(20, 20, 20, 20)
            layout.setSpacing(12)

            icon_label = QLabel()
            self._apply_icon_to_label(icon_label, icon_key, fallback_text, QSize(70, 70))
            layout.addWidget(icon_label, alignment=Qt.AlignmentFlag.AlignHCenter)

            name_container = QFrame()
            name_container.setStyleSheet(
                "background: rgba(255, 149, 0, 0.14); border-radius: 14px;"
            )
            name_layout = QHBoxLayout(name_container)
            name_layout.setContentsMargins(10, 6, 10, 6)
            name_layout.setSpacing(8)

            led = QLabel("●")
            led.setFont(QFont("Arial", 14))
            led.setFixedWidth(16)
            led.setAlignment(Qt.AlignmentFlag.AlignCenter)
            led.setStyleSheet("color: #ff9500;")
            name_layout.addWidget(led)

            name_label = QLabel(name)
            name_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            name_label.setStyleSheet(f"color: {COLOR_SCHEME['text_primary']};")
            name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            name_layout.addWidget(name_label)
            name_layout.addStretch()

            layout.addWidget(name_container)

            status_label = QLabel("Checking...")
            status_label.setFont(QFont("Segoe UI", 10))
            status_label.setStyleSheet(f"color: {COLOR_SCHEME['text_secondary']};")
            status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(status_label)

            detail_label = QLabel("…")
            detail_label.setFont(QFont("Segoe UI", 9))
            detail_label.setStyleSheet(f"color: {COLOR_SCHEME['text_secondary']};")
            layout.addWidget(detail_label)

            frame.led = led
            frame.name_container = name_container
            frame.status_label = status_label
            frame.detail_label = detail_label
        except Exception as exc:
            logger.error(f"Failed creating status block for {name}: {exc}", exc_info=True)
            frame = QFrame()
            frame.setStyleSheet(f"background-color: {COLOR_SCHEME['surface']}; border-radius: 16px;")
            fallback_layout = QVBoxLayout(frame)
            fallback_label = QLabel(f"{name} (status unavailable)")
            fallback_label.setWordWrap(True)
            fallback_layout.addWidget(fallback_label)
        return frame

    def _update_block(self, key: str, is_ok: bool, status_text: str, detail_text: str = "") -> None:
        """Update status block."""
        if key not in self.test_blocks:
            return

        block = self.test_blocks[key]
        color = "#34c759" if is_ok else "#ff3b30"  # Green or Red
        if hasattr(block, 'led'):
            block.led.setStyleSheet(f"color: {color};")
        if hasattr(block, 'name_container'):
            block.name_container.setStyleSheet(
                f"background: {color}26; border-radius: 14px;"
            )
        if hasattr(block, 'status_label'):
            block.status_label.setText(status_text)
        if hasattr(block, 'detail_label') and detail_text:
            block.detail_label.setText(detail_text)

    def _run_tests(self):
        """Run tests for each test file and update status."""
        import subprocess
        for key, file in self.test_files.items():
            try:
                result = subprocess.run(
                    ["python", "-m", "pytest", f"tests/{file}", "--tb=no", "-q"],
                    capture_output=True,
                    text=True,
                    cwd="/home/matheus/Documentos/NitroSense Ultimate",
                    timeout=30
                )
                is_ok = result.returncode == 0
                status_text = "Passed" if is_ok else "Failed"
                detail_text = f"Return code: {result.returncode}"
                self._update_block(key, is_ok, status_text, detail_text)
            except Exception as e:
                self._update_block(key, False, "Error", str(e))
