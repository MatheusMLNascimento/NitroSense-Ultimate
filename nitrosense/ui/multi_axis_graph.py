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
        # Add data (keep last 30 points)
        if cpu_temp is not None:
            self.cpu_temps.append(cpu_temp)
            if len(self.cpu_temps) > 30:
                self.cpu_temps.pop(0)
        
        if gpu_temp is not None:
            self.gpu_temps.append(gpu_temp)
            if len(self.gpu_temps) > 30:
                self.gpu_temps.pop(0)
        
        if fan_rpm is not None:
            self.fan_rpms.append(fan_rpm)
            if len(self.fan_rpms) > 30:
                self.fan_rpms.pop(0)
        
        # Update timestamps
        self.timestamps = list(range(len(self.cpu_temps)))
        
        # Redraw graph
        self._draw_graph()
    
    def _draw_graph(self) -> None:
        """Redraw the multi-axis graph."""
        try:
            # Clear old lines
            self.ax_temp.clear()
            self.ax_rpm.clear()
            
            # Setup axes
            self.ax_temp.set_facecolor(COLOR_SCHEME['background'])
            self.ax_rpm.set_facecolor(COLOR_SCHEME['background'])
            
            self.ax_temp.set_xlabel("Time (s)", color=COLOR_SCHEME['text_secondary'], fontsize=8)
            self.ax_temp.set_ylabel("Temperature (°C)", color="#0099ff", fontsize=9, fontweight='bold')
            self.ax_temp.tick_params(axis='y', labelcolor="#0099ff")
            self.ax_temp.tick_params(axis='x', labelcolor=COLOR_SCHEME['text_secondary'])
            
            self.ax_rpm.set_ylabel("Fan RPM", color="#ff9500", fontsize=9, fontweight='bold')
            self.ax_rpm.tick_params(axis='y', labelcolor="#ff9500")
            
            # Plot temperature data on primary axis
            if self.show_cpu and len(self.cpu_temps) > 1:
                self.ax_temp.plot(
                    self.timestamps, 
                    self.cpu_temps,
                    color="#0099ff",
                    linewidth=2,
                    marker='o',
                    markersize=3,
                    label="CPU Temp"
                )
            
            if self.show_gpu and len(self.gpu_temps) > 1:
                self.ax_temp.plot(
                    self.timestamps,
                    self.gpu_temps,
                    color="#00ff99",
                    linewidth=2,
                    marker='s',
                    markersize=3,
                    label="GPU Temp",
                    alpha=0.8
                )
            
            # Plot RPM data on secondary axis
            if self.show_rpm and len(self.fan_rpms) > 1:
                self.ax_rpm.plot(
                    self.timestamps,
                    self.fan_rpms,
                    color="#ff9500",
                    linewidth=2,
                    marker='^',
                    markersize=3,
                    label="Fan RPM",
                    alpha=0.8
                )
            
            # Grid
            self.ax_temp.grid(True, alpha=0.2, linestyle='--')
            
            # Set y-axis limits with padding
            temps = [t for temps in [self.cpu_temps, self.gpu_temps] for t in temps if temps]
            if temps:
                temp_min = min(temps)
                temp_max = max(temps)
                temp_padding = (temp_max - temp_min) * 0.1 + 5
                self.ax_temp.set_ylim(max(0, temp_min - temp_padding), temp_max + temp_padding)
            
            if self.fan_rpms:
                rpm_max = max(self.fan_rpms) * 1.1 + 100
                self.ax_rpm.set_ylim(0, rpm_max)
            
            # Combine legends
            lines1, labels1 = self.ax_temp.get_legend_handles_labels()
            lines2, labels2 = self.ax_rpm.get_legend_handles_labels()
            self.ax_temp.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=8)
            
            self.canvas.draw_idle()
        
        except Exception as e:
            logger.error(f"Graph draw error: {e}")
    
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
