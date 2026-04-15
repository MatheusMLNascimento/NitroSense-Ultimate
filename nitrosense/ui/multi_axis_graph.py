"""
Advanced Multi-Axis Graph Widget for NitroSense Ultimate.

FEATURE #6: Gráfico Multi-Eixo
MOTIVO: Visualizar relacionamento entre temperatura e velocidade do fan.
- 2 eixos Y: temperatura (lado esquerdo), RPM (lado direito)
- Permite ver padrão "fan increases when temp spikes"
- Histórico de 30 pontos (últimos 60 segundos) em tempo real
- Cores diferenciam CPU/GPU vs. fan speed para clareza visual
- Vs. gráfico único mostra apenas um tipo de dado por vez
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QCheckBox, QLabel
from PyQt6.QtCore import Qt
from matplotlib.backends.backend_qtgg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator
from typing import List, Optional
from ...core.logger import logger
from ...core.constants import COLOR_SCHEME, TEMP_COLORS


class MultiAxisGraph(QWidget):
    """Advanced multi-axis graph widget showing temperature and fan speed."""
    
    def __init__(self, parent=None):
        """
        Initialize multi-axis graph.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.cpu_temps: List[float] = []
        self.gpu_temps: List[float] = []
        self.fan_rpms: List[float] = []
        self.timestamps: List[int] = []
        
        # Display options
        self.show_cpu = True
        self.show_gpu = True
        self.show_rpm = True
        self._cpu_line = None
        self._gpu_line = None
        self._rpm_line = None
        self._last_draw_time = 0.0
        
        self._init_ui()
        
        logger.info("MultiAxisGraph initialized")
    
    def _init_ui(self) -> None:
        """Initialize UI with graph and controls."""
        layout = QVBoxLayout(self)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        self.checkbox_cpu = QCheckBox("CPU Temp")
        self.checkbox_cpu.setChecked(True)
        self.checkbox_cpu.stateChanged.connect(self._on_cpu_toggled)
        controls_layout.addWidget(self.checkbox_cpu)
        
        self.checkbox_gpu = QCheckBox("GPU Temp")
        self.checkbox_gpu.setChecked(True)
        self.checkbox_gpu.stateChanged.connect(self._on_gpu_toggled)
        controls_layout.addWidget(self.checkbox_gpu)
        
        self.checkbox_rpm = QCheckBox("Fan RPM")
        self.checkbox_rpm.setChecked(True)
        self.checkbox_rpm.stateChanged.connect(self._on_rpm_toggled)
        controls_layout.addWidget(self.checkbox_rpm)
        
        # Legend
        legend_label = QLabel("← Temperature (°C) | Fan Speed (RPM) →")
        legend_label.setStyleSheet(f"color: {COLOR_SCHEME['text_secondary']}; font-size: 9px;")
        controls_layout.addWidget(legend_label)
        
        controls_layout.addStretch()
        layout.addLayout(controls_layout)
        
        # Create matplotlib figure with dual axes
        self.figure = Figure(figsize=(10, 3.5), dpi=100, facecolor=COLOR_SCHEME['surface'])
        self.figure.tight_layout(pad=2)
        
        # Primary axis (temperature)
        self.ax_temp = self.figure.add_subplot(111)
        self.ax_temp.set_facecolor(COLOR_SCHEME['background'])
        self.ax_temp.set_xlabel("Time (s)", color=COLOR_SCHEME['text_secondary'], fontsize=8)
        self.ax_temp.set_ylabel("Temperature (°C)", color="#0099ff", fontsize=9, fontweight='bold')
        self.ax_temp.tick_params(axis='y', labelcolor="#0099ff")
        self.ax_temp.tick_params(axis='x', labelcolor=COLOR_SCHEME['text_secondary'])
        self.ax_temp.grid(True, alpha=0.2, linestyle='--')
        
        # Secondary axis (fan RPM)
        self.ax_rpm = self.ax_temp.twinx()
        self.ax_rpm.set_facecolor(COLOR_SCHEME['background'])
        self.ax_rpm.set_ylabel("Fan RPM", color="#ff9500", fontsize=9, fontweight='bold')
        self.ax_rpm.tick_params(axis='y', labelcolor="#ff9500")

        self._cpu_line, = self.ax_temp.plot([], [], color="#0099ff", linewidth=2, marker='o', markersize=3, label="CPU Temp")
        self._gpu_line, = self.ax_temp.plot([], [], color="#00ff99", linewidth=2, marker='s', markersize=3, label="GPU Temp", alpha=0.8)
        self._rpm_line, = self.ax_rpm.plot([], [], color="#ff9500", linewidth=2, marker='^', markersize=3, label="Fan RPM", alpha=0.8)

        # Create canvas
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)
    
    def update_data(
        self, 
        cpu_temp: Optional[float] = None,
        gpu_temp: Optional[float] = None,
        fan_rpm: Optional[float] = None
    ) -> None:
        """
        Update graph with new data point.
        
        Args:
            cpu_temp: CPU temperature in °C
            gpu_temp: GPU temperature in °C
            fan_rpm: Fan speed in RPM
        """
        should_draw = False
        if cpu_temp is not None:
            if not self.cpu_temps or abs(cpu_temp - self.cpu_temps[-1]) >= 0.15:
                should_draw = True
            self.cpu_temps.append(cpu_temp)
            if len(self.cpu_temps) > 30:
                self.cpu_temps.pop(0)

        if gpu_temp is not None:
            if not self.gpu_temps or abs(gpu_temp - self.gpu_temps[-1]) >= 0.15:
                should_draw = True
            self.gpu_temps.append(gpu_temp)
            if len(self.gpu_temps) > 30:
                self.gpu_temps.pop(0)

        if fan_rpm is not None:
            if not self.fan_rpms or abs(fan_rpm - self.fan_rpms[-1]) >= 25:
                should_draw = True
            self.fan_rpms.append(fan_rpm)
            if len(self.fan_rpms) > 30:
                self.fan_rpms.pop(0)

        self.timestamps = list(range(max(len(self.cpu_temps), len(self.gpu_temps), len(self.fan_rpms))))

        if should_draw:
            self._draw_graph()
    
    def _draw_graph(self) -> None:
        """Redraw the multi-axis graph."""
        try:
            self.ax_temp.set_facecolor(COLOR_SCHEME['background'])
            self.ax_rpm.set_facecolor(COLOR_SCHEME['background'])
            self.ax_temp.set_xlabel("Time (s)", color=COLOR_SCHEME['text_secondary'], fontsize=8)
            self.ax_temp.set_ylabel("Temperature (°C)", color="#0099ff", fontsize=9, fontweight='bold')
            self.ax_temp.tick_params(axis='y', labelcolor="#0099ff")
            self.ax_temp.tick_params(axis='x', labelcolor=COLOR_SCHEME['text_secondary'])
            self.ax_rpm.set_ylabel("Fan RPM", color="#ff9500", fontsize=9, fontweight='bold')
            self.ax_rpm.tick_params(axis='y', labelcolor="#ff9500")

            self._cpu_line.set_data(self.timestamps if self.show_cpu else [], self.cpu_temps if self.show_cpu else [])
            self._gpu_line.set_data(self.timestamps if self.show_gpu else [], self.gpu_temps if self.show_gpu else [])
            self._rpm_line.set_data(self.timestamps if self.show_rpm else [], self.fan_rpms if self.show_rpm else [])

            self.ax_temp.relim()
            self.ax_temp.autoscale_view(scalex=True, scaley=True)
            self.ax_rpm.relim()
            self.ax_rpm.autoscale_view(scalex=True, scaley=True)

            self.ax_temp.grid(True, alpha=0.2, linestyle='--')

            lines1, labels1 = self.ax_temp.get_legend_handles_labels()
            lines2, labels2 = self.ax_rpm.get_legend_handles_labels()
            self.ax_temp.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=8)

            self.canvas.draw_idle()
        except Exception as exc:
            logger.error(f"Graph draw error: {exc}")
    
    def _on_cpu_toggled(self, state: int) -> None:
        """Handle CPU checkbox toggle."""
        self.show_cpu = state == Qt.CheckState.Checked.value
        self._draw_graph()
    
    def _on_gpu_toggled(self, state: int) -> None:
        """Handle GPU checkbox toggle."""
        self.show_gpu = state == Qt.CheckState.Checked.value
        self._draw_graph()
    
    def _on_rpm_toggled(self, state: int) -> None:
        """Handle RPM checkbox toggle."""
        self.show_rpm = state == Qt.CheckState.Checked.value
        self._draw_graph()
    
    def clear_data(self) -> None:
        """Clear all displayed data."""
        self.cpu_temps.clear()
        self.gpu_temps.clear()
        self.fan_rpms.clear()
        self.timestamps.clear()
        self._draw_graph()
