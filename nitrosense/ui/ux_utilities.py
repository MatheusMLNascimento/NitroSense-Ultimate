"""
UX Resilience Utilities - Dir 12
Debouncing, Loading States, Pulsing Effects, Feedback

FEATURES:
1. DebouncedSlider: QSlider com debouncing automático (300ms)
2. LoadingButton: QPushButton com estados Loading/Enabled/Disabled
3. PulseAnimation: Efeito de pulsação com cores
4. FeedbackToast: Confirmação visual de comandos
"""

from PyQt6.QtWidgets import QPushButton, QSlider, QWidget
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QColor
from typing import Callable, Optional
import time


class DebouncedSlider(QSlider):
    """
    QSlider com debouncing automático.
    Evita múltiplas emissões de valueChanged durante interação do usuário.
    
    Emite signal `value_ready` apenas após 300ms de inatividade.
    """
    
    value_ready = pyqtSignal(int)  # Emitted after debounce delay
    
    def __init__(self, orientation=Qt.Orientation.Horizontal, debounce_ms: int = 300, parent=None):
        super().__init__(orientation, parent)
        self.debounce_ms = debounce_ms
        self.debounce_timer = QTimer()
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.timeout.connect(self._on_debounce_timeout)
        
        # Connect to value changes
        self.sliderMoved.connect(self._on_slider_moved)
        self.valueChanged.connect(self._on_value_changed)
    
    def _on_slider_moved(self):
        """Called when user drags the slider."""
        self.debounce_timer.stop()
        self.debounce_timer.start(self.debounce_ms)
    
    def _on_value_changed(self):
        """Called when value changes (from any source)."""
        self.debounce_timer.stop()
        self.debounce_timer.start(self.debounce_ms)
    
    def _on_debounce_timeout(self):
        """Emit value_ready signal after debounce delay."""
        self.value_ready.emit(self.value())


class LoadingButton(QPushButton):
    """
    QPushButton com estados Loading/Normal/Error.
    
    Estados:
    - Normal: texto original, ativo
    - Loading: "⏳ Loading..." ou "⟳ Aguardando...", desativado
    - Error: "❌ Erro" (temporário)
    - Success: "✓ Sucesso" (temporário)
    """
    
    command_requested = pyqtSignal(str)  # Emitted when button clicked (arg: command_type)
    
    def __init__(self, text: str = "Execute", command_type: str = "", parent=None):
        super().__init__(text, parent)
        self.original_text = text
        self.command_type = command_type
        self.is_loading = False
        self._loading_timer = None
        self._reset_timer = QTimer()
        self._reset_timer.setSingleShot(True)
        self._reset_timer.timeout.connect(self._reset_to_normal)
    
    def start_loading(self, message: str = "Aguardando..."):
        """Enter loading state."""
        if self.is_loading:
            return
        
        self.is_loading = True
        self.setEnabled(False)
        self.setText(f"⟳ {message}")
        self._add_pulse_effect()
    
    def set_success(self, message: str = "Sucesso!", duration_ms: int = 1500):
        """Show success state temporarily."""
        self.is_loading = False
        self.setEnabled(True)
        self.setText(f"✓ {message}")
        self.setStyleSheet(self.styleSheet() + "\n" + 
            "QPushButton { color: #00ff00; font-weight: bold; }")
        
        # Reset after duration
        self._reset_timer.start(duration_ms)
    
    def set_error(self, message: str = "Erro", duration_ms: int = 2000):
        """Show error state temporarily."""
        self.is_loading = False
        self.setEnabled(True)
        self.setText(f"❌ {message}")
        self.setStyleSheet(self.styleSheet() + "\n" + 
            "QPushButton { color: #ff3333; font-weight: bold; }")
        
        # Reset after duration
        self._reset_timer.start(duration_ms)
    
    def _add_pulse_effect(self):
        """Add subtle pulsing effect during loading."""
        # This would need QPropertyAnimation integration
        # For now, just visual feedback via color
        pass
    
    def _reset_to_normal(self):
        """Reset button to original state."""
        self.is_loading = False
        self.setEnabled(True)
        self.setText(self.original_text)
        # Reset stylesheet
        self.setStyleSheet("")


class PulseAnimation(QPropertyAnimation):
    """
    QPropertyAnimation for pulsing effect on colors.
    Animates between two colors infinitely.
    
    Usage:
        pulse = PulseAnimation(widget, b"color", widget)
        pulse.setStartValue(QColor("#1E1E1E"))
        pulse.setEndValue(QColor("#00ff00"))
        pulse.setDuration(600)
        pulse.start()
    """
    
    def __init__(self, widget: QWidget, property_name: str, target_widget: QWidget):
        super().__init__(widget, property_name)
        self.target_widget = target_widget
        self.setDuration(600)
        self.setEasingCurve(QEasingCurve.Type.InOutQuad)
        # Pulse effect: goes from start → end → start
        self.setLoopCount(-1)  # Infinite loop


class ConfirmationOverlay:
    """
    Visual confirmation that a low-level command was received.
    
    Shows brief color change/pulse on UI element to confirm:
    - Fan speed change received
    - Profile activation
    - Mode switch
    """
    
    def __init__(self, widget: QWidget, color: str = "#00ff00", duration_ms: int = 400):
        """
        Args:
            widget: Target QWidget to pulse
            color: Color to pulse to (hex string)
            duration_ms: Duration of pulse effect
        """
        self.widget = widget
        self.color = color
        self.duration_ms = duration_ms
        self.original_stylesheet = widget.styleSheet() if widget else ""
    
    def show_brief(self):
        """Show brief color flash (200ms pulse)."""
        if not self.widget:
            return
        
        # Save original
        original_style = self.widget.styleSheet()
        
        # Apply pulse color
        try:
            self.widget.setStyleSheet(
                original_style + f"\nQWidget {{ border: 2px solid {self.color}; }}"
            )
        except:
            pass
        
        # Reset after delay
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(lambda: self.widget.setStyleSheet(original_style))
        timer.start(self.duration_ms)
