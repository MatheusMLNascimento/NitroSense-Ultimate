"""
Config Page - Thermal curve configuration and settings.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QGroupBox, QComboBox, QCheckBox, QSpinBox,
    QDoubleSpinBox, QToolButton
)
from PyQt6.QtCore import Qt, QPoint, QTimer, QSize
from PyQt6.QtGui import QFont, QIntValidator, QDoubleValidator
from ...core.logger import logger
from ...core.constants import COLOR_SCHEME, THERMAL_CONFIG
from ...hardware.manager import HardwareManager
from ..icon_theme import load_icon


class ConfigPage(QWidget):
    """Configuration page for thermal settings."""

    def __init__(self, hardware_manager: HardwareManager, config_manager):
        super().__init__()
        self.hardware = hardware_manager
        self.config = config_manager
        self.advanced_config = self._get_advanced_config()

        self._init_ui()
        self._apply_checkbox_styles()
        logger.info("ConfigPage initialized")

    def _create_help_button(self, title: str, description: str):
        """Create a help icon button with tooltip and popup card."""
        button = QToolButton()
        help_icon = load_icon("help")
        if not help_icon.isNull():
            button.setIcon(help_icon)
            button.setIconSize(QSize(16, 16))
        else:
            button.setText("?")
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setToolTip(f"{title}\n{description}")
        button.setAutoRaise(True)
        button.setStyleSheet(
            "QToolButton {"
            "  border: 1px solid #666;"
            "  border-radius: 10px;"
            "  min-width: 18px;"
            "  min-height: 18px;"
            "  font-weight: bold;"
            "  color: #ffffff;"
            "  background: rgba(255,255,255,0.08);"
            "}"
            "QToolButton:hover {"
            "  background: rgba(255,255,255,0.14);"
            "}"
        )
        button.clicked.connect(lambda _, t=title, d=description, b=button: self._show_help_card(b, t, d))
        return button

    def _show_help_card(self, anchor, title: str, description: str) -> None:
        """Show a small help card anchored to the help icon."""
        if hasattr(self, "_active_help_card") and self._active_help_card is not None:
            self._active_help_card.close()

        card = QLabel()
        card.setTextFormat(Qt.TextFormat.RichText)
        card.setText(f"<b>{title}</b><br><small>{description}</small>")
        card.setWindowFlag(Qt.WindowType.ToolTip)
        card.setStyleSheet(
            "QLabel {"
            "  background: #1f1f1f;"
            "  color: #f5f5f5;"
            "  border: 1px solid #4a4a4a;"
            "  border-radius: 10px;"
            "  padding: 10px;"
            "  min-width: 240px;"
            "}"
        )
        card.setWordWrap(True)
        position = anchor.mapToGlobal(anchor.rect().bottomLeft())
        card.move(position + QPoint(0, 8))
        card.show()

        self._active_help_card = card
        QTimer.singleShot(5000, card.close)

    def _get_advanced_config(self) -> dict:
        """Return advanced configuration with defaults filled in."""
        defaults = {
            "theme": "macOS_Dark",
            "ui_layout_type": "column",
            "ping_target": "8.8.8.8",
            "frost_duration": 120,
            "notifications": {
                "critical_temp": True,
                "fan_stall": True,
                "throttling": True,
                "update_available": False,
            },
            "log_directory": str(self.config.config_dir / "logs"),
            "start_minimized": False,
            "hide_graph": False,
            "auto_curve_enabled": False,
            "ai_sensitivity": 1.0,
            "battery_charge_limit": 100,
            "maintenance_scheduler_enabled": False,
            "maintenance_hour": 4,
            "debug_mode": False,
            "export_csv_enabled": False,
            "ui_scale": 1.0,
        }

        saved = self.config.get("advanced_config", {}) or {}
        result = defaults.copy()
        result.update({k: saved.get(k, v) for k, v in defaults.items()})

        # Merge notifications separately to preserve keys.
        result["notifications"] = defaults["notifications"].copy()
        result["notifications"].update(saved.get("notifications", {}))
        return result

    def _init_ui(self) -> None:
        """Initialize config page."""
        if self.layout() is not None:
            QWidget().setLayout(self.layout())

        self.advanced_config = self._get_advanced_config()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(18)

        title = QLabel("Thermal & Advanced Configuration")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLOR_SCHEME['primary']};")
        layout.addWidget(title)

        curve_group = QGroupBox("Fan Speed Curve")
        curve_group.setStyleSheet(
            f"QGroupBox {{ background: {COLOR_SCHEME['surface']}; border: 1px solid {COLOR_SCHEME['primary']}; border-radius: 16px; margin-top: 12px; padding: 14px; }} QGroupBox::title {{ subcontrol-origin: margin; left: 14px; padding: 0 6px; }}"
        )
        curve_layout = QVBoxLayout(curve_group)
        curve_layout.setSpacing(12)

        self.threshold_inputs = {}
        for level in ["Low", "Mid", "High"]:
            row_layout = QHBoxLayout()

            temp_label = QLabel(f"{level} Temperature (°C):")
            temp_input = QLineEdit()
            temp_input.setValidator(QIntValidator(20, 100))
            temp_input.setText(str(self.config.get("thermal.temp_thresholds." + level, THERMAL_CONFIG["temp_thresholds"][level])))
            temp_input.setMaximumWidth(100)
            self.threshold_inputs[f"temp_{level}"] = temp_input

            speed_label = QLabel("Fan Speed (%):")
            speed_input = QLineEdit()
            speed_input.setValidator(QIntValidator(0, 100))
            speed_input.setText(str(self.config.get("thermal.speed_thresholds." + level, THERMAL_CONFIG["speed_thresholds"][level])))
            speed_input.setMaximumWidth(100)
            self.threshold_inputs[f"speed_{level}"] = speed_input

            row_layout.addWidget(temp_label)
            row_layout.addWidget(temp_input)
            row_layout.addSpacing(20)
            row_layout.addWidget(speed_label)
            row_layout.addWidget(speed_input)
            row_layout.addStretch()
            curve_layout.addLayout(row_layout)

        layout.addWidget(curve_group)

        layout.addWidget(self._create_display_group())
        layout.addWidget(self._create_notifications_group())
        layout.addWidget(self._create_advanced_group())

        button_layout = QHBoxLayout()
        save_btn = QPushButton("Save Configuration")
        save_icon = load_icon("save")
        if not save_icon.isNull():
            save_btn.setIcon(save_icon)
            save_btn.setIconSize(QSize(18, 18))
        save_btn.clicked.connect(self._save_config)

        reset_btn = QPushButton("Reset to Defaults")
        reset_icon = load_icon("reset")
        if not reset_icon.isNull():
            reset_btn.setIcon(reset_icon)
            reset_btn.setIconSize(QSize(18, 18))
        reset_btn.clicked.connect(self._reset_config)

        export_btn = QPushButton("Export Backup")
        export_icon = load_icon("export")
        if not export_icon.isNull():
            export_btn.setIcon(export_icon)
            export_btn.setIconSize(QSize(18, 18))
        export_btn.clicked.connect(self._export_backup)

        button_style = f"""
            QPushButton {{
                background-color: {COLOR_SCHEME['surface']};
                color: {COLOR_SCHEME['text_primary']};
                border: 1px solid {COLOR_SCHEME['primary']};
                border-radius: 14px;
                padding: 12px 18px;
                min-width: 160px;
            }}
            QPushButton:hover {{
                background-color: {COLOR_SCHEME['primary']};
                color: {COLOR_SCHEME['background']};
            }}
            QPushButton:pressed {{
                background-color: {COLOR_SCHEME['success']};
                color: {COLOR_SCHEME['background']};
            }}
        """
        for button in (save_btn, reset_btn, export_btn):
            button.setStyleSheet(button_style)

        button_layout.addWidget(save_btn)
        button_layout.addWidget(reset_btn)
        button_layout.addWidget(export_btn)

        layout.addLayout(button_layout)

        self.feedback_label = QLabel("")
        self.feedback_label.setStyleSheet(f"color: {COLOR_SCHEME['success']}; font-size: 10pt;")
        layout.addWidget(self.feedback_label)
        layout.addStretch()

    def _create_display_group(self) -> QGroupBox:
        """Create display and behavior settings."""
        group = QGroupBox("Display & Behavior")
        group.setStyleSheet(
            f"QGroupBox {{ background: {COLOR_SCHEME['surface']}; border: 1px solid {COLOR_SCHEME['primary']}; border-radius: 16px; margin-top: 12px; padding: 14px; }} QGroupBox::title {{ subcontrol-origin: margin; left: 14px; padding: 0 6px; }}"
        )
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(12)

        theme_layout = QHBoxLayout()
        theme_layout.addWidget(QLabel("Theme:"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["macOS_Dark", "Ultra_Black", "Light"])
        self.theme_combo.setCurrentText(self.advanced_config["theme"])
        theme_layout.addWidget(self.theme_combo)
        theme_layout.addWidget(self._create_help_button(
            "Theme",
            "Escolha o tema do aplicativo. macOS_Dark oferece visual escuro elegante, Ultra_Black maximiza contraste e Light traz uma aparência clara."
        ))
        theme_layout.addStretch()
        group_layout.addLayout(theme_layout)

        layout_layout = QHBoxLayout()
        layout_layout.addWidget(QLabel("UI Layout:"))
        self.ui_layout_combo = QComboBox()
        self.ui_layout_combo.addItems(["column", "row", "compact"])
        self.ui_layout_combo.setCurrentText(self.advanced_config["ui_layout_type"])
        layout_layout.addWidget(self.ui_layout_combo)
        layout_layout.addWidget(self._create_help_button(
            "UI Layout",
            "Defina a organização dos painéis da interface: coluna, linha ou modo compacto para economizar espaço."
        ))
        layout_layout.addStretch()
        group_layout.addLayout(layout_layout)

        scale_layout = QHBoxLayout()
        scale_layout.addWidget(QLabel("UI Scale:"))
        self.ui_scale_spin = QDoubleSpinBox()
        self.ui_scale_spin.setRange(0.75, 1.5)
        self.ui_scale_spin.setSingleStep(0.05)
        self.ui_scale_spin.setValue(self.advanced_config.get("ui_scale", 1.0))
        scale_layout.addWidget(self.ui_scale_spin)
        scale_layout.addWidget(self._create_help_button(
            "UI Scale",
            "Ajusta o tamanho geral da interface para melhor leitura em telas maiores ou menores."
        ))
        scale_layout.addStretch()
        group_layout.addLayout(scale_layout)

        auto_curve_layout = QHBoxLayout()
        self.auto_curve_checkbox = QCheckBox("Enable Auto Fan Curve")
        self.auto_curve_checkbox.setChecked(self.advanced_config.get("auto_curve_enabled", False))
        auto_curve_layout.addWidget(self.auto_curve_checkbox)
        auto_curve_layout.addWidget(self._create_help_button(
            "Auto Fan Curve",
            "Ativa uma curva de velocidade automática que ajusta a refrigeração de acordo com o uso do sistema."
        ))
        auto_curve_layout.addStretch()
        group_layout.addLayout(auto_curve_layout)

        hide_graph_layout = QHBoxLayout()
        self.hide_graph_checkbox = QCheckBox("Hide Graph in Home Page")
        self.hide_graph_checkbox.setChecked(self.advanced_config.get("hide_graph", False))
        hide_graph_layout.addWidget(self.hide_graph_checkbox)
        hide_graph_layout.addWidget(self._create_help_button(
            "Hide Graph",
            "Oculta o gráfico na home page para uma experiência mais limpa."
        ))
        hide_graph_layout.addStretch()
        group_layout.addLayout(hide_graph_layout)

        start_minimized_layout = QHBoxLayout()
        self.start_minimized_checkbox = QCheckBox("Start Minimized")
        self.start_minimized_checkbox.setChecked(self.advanced_config.get("start_minimized", False))
        start_minimized_layout.addWidget(self.start_minimized_checkbox)
        start_minimized_layout.addWidget(self._create_help_button(
            "Start Minimized",
            "Inicia o aplicativo minimizado na bandeja, ideal para inicialização silenciosa."
        ))
        start_minimized_layout.addStretch()
        group_layout.addLayout(start_minimized_layout)

        log_dir_layout = QHBoxLayout()
        log_dir_layout.addWidget(QLabel("Log Directory:"))
        self.log_dir_input = QLineEdit(self.advanced_config.get("log_directory", str(self.config.config_dir / "logs")))
        log_dir_layout.addWidget(self.log_dir_input)
        log_dir_layout.addWidget(self._create_help_button(
            "Log Directory",
            "Escolha onde os arquivos de log serão gravados para diagnóstico e auditoria."
        ))
        log_dir_layout.addStretch()
        group_layout.addLayout(log_dir_layout)

        return group

    def _apply_checkbox_styles(self) -> None:
        """Apply dark theme checkbox styles for better contrast."""
        self.setStyleSheet(
            "QCheckBox {"
            "  color: #f5f5f5;"
            "  spacing: 8px;"
            "}"
            "QCheckBox::indicator {"
            "  width: 18px;"
            "  height: 18px;"
            "  border: 1px solid #7a7a7a;"
            "  border-radius: 4px;"
            "  background: #252525;"
            "}"
            "QCheckBox::indicator:checked {"
            "  background: #00d1ff;"
            "  border: 1px solid #0099dd;"
            "}"
            "QCheckBox::indicator:hover {"
            "  border-color: #00d1ff;"
            "}"
        )

    def _create_notifications_group(self) -> QGroupBox:
        """Create notification toggles."""
        group = QGroupBox("Notifications")
        group.setStyleSheet(
            f"QGroupBox {{ background: {COLOR_SCHEME['surface']}; border: 1px solid {COLOR_SCHEME['primary']}; border-radius: 16px; margin-top: 12px; padding: 14px; }} QGroupBox::title {{ subcontrol-origin: margin; left: 14px; padding: 0 6px; }}"
        )
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(8)

        notif = self.advanced_config["notifications"]
        self.notification_checkboxes = {}

        for name, label, hint in [
            ("critical_temp", "Critical Temperature Alerts", "Notifica quando a temperatura atinge níveis críticos."),
            ("fan_stall", "Fan Stall Alerts", "Detecta e alerta se a ventoinha ficar presa ou parar de girar."),
            ("throttling", "CPU Throttling Alerts", "Avise se o sistema reduzir desempenho por calor excessivo."),
            ("update_available", "Update Notifications", "Mostra aviso quando há nova versão disponível."),
        ]:
            row = QHBoxLayout()
            checkbox = QCheckBox(label)
            checkbox.setChecked(notif.get(name, False))
            self.notification_checkboxes[name] = checkbox
            row.addWidget(checkbox)
            row.addWidget(self._create_help_button(label, hint))
            row.addStretch()
            group_layout.addLayout(row)

        return group

    def _create_advanced_group(self) -> QGroupBox:
        """Create advanced feature settings."""
        group = QGroupBox("Advanced Controls")
        group.setStyleSheet(
            f"QGroupBox {{ background: {COLOR_SCHEME['surface']}; border: 1px solid {COLOR_SCHEME['primary']}; border-radius: 16px; margin-top: 12px; padding: 14px; }} QGroupBox::title {{ subcontrol-origin: margin; left: 14px; padding: 0 6px; }}"
        )
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(12)

        frost_layout = QHBoxLayout()
        frost_layout.addWidget(QLabel("Frost Duration (s):"))
        self.frost_duration_spin = QSpinBox()
        self.frost_duration_spin.setRange(10, 600)
        self.frost_duration_spin.setSingleStep(10)
        self.frost_duration_spin.setValue(self.advanced_config.get("frost_duration", 120))
        frost_layout.addWidget(self.frost_duration_spin)
        frost_layout.addWidget(self._create_help_button(
            "Frost Duration",
            "Controla por quanto tempo o modo de resfriamento adicional permanece ativo após picos de temperatura."
        ))
        frost_layout.addStretch()
        group_layout.addLayout(frost_layout)

        ai_layout = QHBoxLayout()
        ai_layout.addWidget(QLabel("AI Sensitivity:"))
        self.ai_sensitivity_spin = QDoubleSpinBox()
        self.ai_sensitivity_spin.setRange(0.1, 2.0)
        self.ai_sensitivity_spin.setSingleStep(0.1)
        self.ai_sensitivity_spin.setValue(self.advanced_config.get("ai_sensitivity", 1.0))
        ai_layout.addWidget(self.ai_sensitivity_spin)
        ai_layout.addWidget(self._create_help_button(
            "AI Sensitivity",
            "Ajusta a sensibilidade do motor preditivo ao definir as curvas de refrigeração."
        ))
        ai_layout.addStretch()
        group_layout.addLayout(ai_layout)

        battery_layout = QHBoxLayout()
        battery_layout.addWidget(QLabel("Battery Charge Limit (%):"))
        self.battery_limit_spin = QSpinBox()
        self.battery_limit_spin.setRange(20, 100)
        self.battery_limit_spin.setValue(self.advanced_config.get("battery_charge_limit", 100))
        battery_layout.addWidget(self.battery_limit_spin)
        battery_layout.addWidget(self._create_help_button(
            "Battery Charge Limit",
            "Define o limite máximo de carga para preservar a bateria a longo prazo."
        ))
        battery_layout.addStretch()
        group_layout.addLayout(battery_layout)

        scheduler_layout = QHBoxLayout()
        self.maintenance_scheduler_checkbox = QCheckBox("Enable Maintenance Scheduler")
        self.maintenance_scheduler_checkbox.setChecked(self.advanced_config.get("maintenance_scheduler_enabled", False))
        scheduler_layout.addWidget(self.maintenance_scheduler_checkbox)
        scheduler_layout.addWidget(self._create_help_button(
            "Maintenance Scheduler",
            "Ativa manutenção automática em horários definidos."
        ))
        scheduler_layout.addStretch()
        group_layout.addLayout(scheduler_layout)

        hour_layout = QHBoxLayout()
        hour_layout.addWidget(QLabel("Maintenance Hour:"))
        self.maintenance_hour_spin = QSpinBox()
        self.maintenance_hour_spin.setRange(0, 23)
        self.maintenance_hour_spin.setValue(self.advanced_config.get("maintenance_hour", 4))
        hour_layout.addWidget(self.maintenance_hour_spin)
        hour_layout.addWidget(self._create_help_button(
            "Maintenance Hour",
            "Escolha a hora em que a manutenção programada deve ocorrer."
        ))
        hour_layout.addStretch()
        group_layout.addLayout(hour_layout)

        debug_layout = QHBoxLayout()
        self.debug_checkbox = QCheckBox("Debug Mode")
        self.debug_checkbox.setChecked(self.advanced_config.get("debug_mode", False))
        debug_layout.addWidget(self.debug_checkbox)
        debug_layout.addWidget(self._create_help_button(
            "Debug Mode",
            "Ativa logs detalhados para depuração e diagnóstico."
        ))
        debug_layout.addStretch()
        group_layout.addLayout(debug_layout)

        csv_layout = QHBoxLayout()
        self.csv_checkbox = QCheckBox("Enable CSV Export")
        self.csv_checkbox.setChecked(self.advanced_config.get("export_csv_enabled", False))
        csv_layout.addWidget(self.csv_checkbox)
        csv_layout.addWidget(self._create_help_button(
            "CSV Export",
            "Permite exportar dados de monitoramento em CSV para análise externa."
        ))
        csv_layout.addStretch()
        group_layout.addLayout(csv_layout)

        ping_layout = QHBoxLayout()
        ping_layout.addWidget(QLabel("Ping Target:"))
        self.ping_target_input = QLineEdit(self.advanced_config.get("ping_target", "8.8.8.8"))
        ping_layout.addWidget(self.ping_target_input)
        ping_layout.addWidget(self._create_help_button(
            "Ping Target",
            "Endereço usado para verificar conectividade e latência de rede."
        ))
        ping_layout.addStretch()
        group_layout.addLayout(ping_layout)

        return group

    def _save_config(self) -> None:
        """Save configuration."""
        try:
            thermal_cfg = self.config.get_thermal_config()

            for level in ["Low", "Mid", "High"]:
                temp = int(self.threshold_inputs[f"temp_{level}"].text())
                speed = int(self.threshold_inputs[f"speed_{level}"].text())
                thermal_cfg["temp_thresholds"][level] = temp
                thermal_cfg["speed_thresholds"][level] = speed

            self.config.set_thermal_config(thermal_cfg)

            advanced_config = {
                "theme": self.theme_combo.currentText(),
                "ui_layout_type": self.ui_layout_combo.currentText(),
                "ui_scale": self.ui_scale_spin.value(),
                "ping_target": self.ping_target_input.text(),
                "frost_duration": self.frost_duration_spin.value(),
                "notifications": {
                    key: checkbox.isChecked()
                    for key, checkbox in self.notification_checkboxes.items()
                },
                "log_directory": self.log_dir_input.text(),
                "start_minimized": self.start_minimized_checkbox.isChecked(),
                "hide_graph": self.hide_graph_checkbox.isChecked(),
                "auto_curve_enabled": self.auto_curve_checkbox.isChecked(),
                "ai_sensitivity": self.ai_sensitivity_spin.value(),
                "battery_charge_limit": self.battery_limit_spin.value(),
                "maintenance_scheduler_enabled": self.maintenance_scheduler_checkbox.isChecked(),
                "maintenance_hour": self.maintenance_hour_spin.value(),
                "debug_mode": self.debug_checkbox.isChecked(),
                "export_csv_enabled": self.csv_checkbox.isChecked(),
            }

            self.config.set("advanced_config", advanced_config, persist=True)
            self.feedback_label.setText("Configuration saved successfully.")
            self.feedback_label.setStyleSheet(f"color: {COLOR_SCHEME['success']}; font-size: 10pt;")
            logger.info("Configuration saved")

        except Exception as e:
            self.feedback_label.setText("Save failed. Check values and try again.")
            self.feedback_label.setStyleSheet(f"color: {COLOR_SCHEME['danger']}; font-size: 10pt;")
            logger.error(f"Save failed: {e}")

    def _reset_config(self) -> None:
        """Reset to defaults."""
        self.config.reset_to_defaults()
        self.config.set("advanced_config", self._get_advanced_config(), persist=True)
        self._init_ui()
        self.feedback_label.setText("Configuration reset to defaults.")
        self.feedback_label.setStyleSheet(f"color: {COLOR_SCHEME['warning']}; font-size: 10pt;")
        logger.info("Config reset to defaults")

    def _export_backup(self) -> None:
        """Export backup snapshot."""
        if self.config.export_snapshot():
            backup_path = self.config.config_dir / "system_snapshot.nsbackup"
            logger.info(f"Backup exported to {backup_path}")
            self.feedback_label.setText(f"Backup exported to {backup_path}")
            self.feedback_label.setStyleSheet(f"color: {COLOR_SCHEME['success']}; font-size: 10pt;")
        else:
            self.feedback_label.setText("Failed to export backup")
            self.feedback_label.setStyleSheet(f"color: {COLOR_SCHEME['danger']}; font-size: 10pt;")
