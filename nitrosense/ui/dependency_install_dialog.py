"""
Dependency Installation Dialog
Asks user for consent to automatically install missing dependencies
"""

from typing import List, Dict, Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QCheckBox, QProgressBar, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap

from ..core.logger import logger
from ..resilience.dependency_installer import DependencyInstaller


class DependencyInstallDialog(QDialog):
    """
    Dialog that asks user for consent to install missing dependencies automatically.
    Shows what will be installed and handles the installation process.
    """

    installation_complete = pyqtSignal(bool, str)  # (success, message)

    def __init__(self, missing_apt: Dict[str, List[str]], missing_pip: Dict[str, List[str]], parent=None):
        super().__init__(parent)
        self.missing_apt = missing_apt
        self.missing_pip = missing_pip
        self.installer = DependencyInstaller()

        self.setWindowTitle("Instalar Dependências Faltantes")
        self.setModal(True)
        self.setFixedSize(600, 500)
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
                color: #ffffff;
                border-radius: 16px;
                border: 2px solid #2f3745;
            }
            QLabel {
                color: #ffffff;
            }
            QPushButton {
                background-color: #2f3745;
                color: #ffffff;
                border: 1px solid #404040;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #404040;
            }
            QPushButton:pressed {
                background-color: #1a1a1a;
            }
            QCheckBox {
                color: #ffffff;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #404040;
                border-radius: 3px;
                background-color: #2f3745;
            }
            QCheckBox::indicator:checked {
                background-color: #34c759;
                border: 1px solid #34c759;
            }
            QTextEdit {
                background-color: #2a2a2a;
                color: #ffffff;
                border: 1px solid #404040;
                border-radius: 8px;
                padding: 8px;
            }
            QProgressBar {
                border: 1px solid #404040;
                border-radius: 4px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #34c759;
                border-radius: 3px;
            }
        """)

        self._setup_ui()
        self._populate_missing_deps()

    def _setup_ui(self):
        """Setup the dialog UI components."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header
        header_label = QLabel("🔧 Dependências Faltantes Detectadas")
        header_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header_label)

        # Description
        desc_label = QLabel(
            "O NitroSense Ultimate detectou dependências faltantes. "
            "Você gostaria de instalá-las automaticamente?\n\n"
            "Isso requer acesso de administrador (sudo) e pode demorar alguns minutos."
        )
        desc_label.setWordWrap(True)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc_label)

        # Missing dependencies display
        deps_label = QLabel("Dependências que serão instaladas:")
        deps_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(deps_label)

        self.deps_text = QTextEdit()
        self.deps_text.setReadOnly(True)
        self.deps_text.setMaximumHeight(150)
        layout.addWidget(self.deps_text)

        # Progress bar (hidden initially)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)

        # Status label (hidden initially)
        self.status_label = QLabel("")
        self.status_label.setVisible(False)
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        # Checkbox for remembering choice
        self.remember_checkbox = QCheckBox("Lembrar minha escolha para futuras inicializações")
        layout.addWidget(self.remember_checkbox)

        # Buttons
        button_layout = QHBoxLayout()

        self.install_button = QPushButton("🚀 Instalar Automaticamente")
        self.install_button.setStyleSheet("""
            QPushButton {
                background-color: #34c759;
                color: white;
                border: 1px solid #34c759;
            }
            QPushButton:hover {
                background-color: #28a745;
            }
        """)
        self.install_button.clicked.connect(self._start_installation)
        button_layout.addWidget(self.install_button)

        self.manual_button = QPushButton("📖 Instruções Manuais")
        self.manual_button.clicked.connect(self._show_manual_instructions)
        button_layout.addWidget(self.manual_button)

        self.skip_button = QPushButton("⏭️ Pular (Funcionalidades Limitadas)")
        self.skip_button.clicked.connect(self._skip_installation)
        button_layout.addWidget(self.skip_button)

        layout.addLayout(button_layout)

        # Check if automatic installation is possible
        if not self.installer.can_install_automatically():
            self.install_button.setEnabled(False)
            self.install_button.setText("🚫 Instalação Automática Indisponível")
            self.install_button.setToolTip(
                "Requer sudo sem senha. Execute: sudo visudo\n"
                "Adicione: seu_usuario ALL=(ALL) NOPASSWD: ALL"
            )

    def _populate_missing_deps(self):
        """Populate the text area with missing dependencies."""
        text = ""

        if self.missing_apt:
            text += "📦 Pacotes do Sistema (APT):\n"
            for tool, packages in self.missing_apt.items():
                text += f"  • {tool} → {' '.join(packages)}\n"
            text += "\n"

        if self.missing_pip:
            text += "🐍 Pacotes Python (pip):\n"
            for package, pip_names in self.missing_pip.items():
                text += f"  • {package} → {' '.join(pip_names)}\n"
            text += "\n"

        if not text.strip():
            text = "✅ Todas as dependências estão instaladas!"

        self.deps_text.setPlainText(text.strip())

    def _start_installation(self):
        """Start the automatic installation process."""
        self.install_button.setEnabled(False)
        self.manual_button.setEnabled(False)
        self.skip_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.status_label.setVisible(True)

        # Collect all packages to install
        apt_packages = []
        for packages in self.missing_apt.values():
            apt_packages.extend(packages)

        pip_packages = []
        for packages in self.missing_pip.values():
            pip_packages.extend(packages)

        # Start installation in a separate thread to avoid blocking UI
        self._install_async(apt_packages, pip_packages)

    def _install_async(self, apt_packages: List[str], pip_packages: List[str]):
        """Perform installation asynchronously."""
        try:
            self.progress_bar.setValue(10)
            self.status_label.setText("Instalando pacotes do sistema...")

            # Install APT packages
            if apt_packages:
                success, message = self.installer.install_apt_packages(apt_packages)
                if not success:
                    self._installation_failed(message)
                    return

            self.progress_bar.setValue(60)
            self.status_label.setText("Instalando pacotes Python...")

            # Install pip packages
            if pip_packages:
                success, message = self.installer.install_pip_packages(pip_packages)
                if not success:
                    self._installation_failed(message)
                    return

            self.progress_bar.setValue(100)
            self.status_label.setText("✅ Instalação concluída com sucesso!")
            self.status_label.setStyleSheet("color: #34c759;")

            # Save user preference if requested
            if self.remember_checkbox.isChecked():
                self._save_install_preference(True)

            QTimer.singleShot(2000, lambda: self._finish_installation(True, "Instalação concluída"))

        except Exception as e:
            self._installation_failed(f"Erro durante instalação: {e}")

    def _installation_failed(self, message: str):
        """Handle installation failure."""
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"❌ Falha na instalação: {message}")
        self.status_label.setStyleSheet("color: #ff3b30;")

        self.install_button.setEnabled(True)
        self.manual_button.setEnabled(True)
        self.skip_button.setEnabled(True)

    def _finish_installation(self, success: bool, message: str):
        """Finish the installation process."""
        self.installation_complete.emit(success, message)
        self.accept()

    def _show_manual_instructions(self):
        """Show manual installation instructions."""
        instructions = """
Para instalar manualmente as dependências faltantes:

1. 📦 Pacotes do Sistema:
   sudo apt update
   sudo apt install -y nbfc nvidia-driver-535 lm-sensors

2. 🐍 Pacotes Python:
   pip install -r requirements.txt

3. 🔄 Reinicie o NitroSense Ultimate

Para habilitar instalação automática no futuro:
   sudo visudo
   Adicione: seu_usuario ALL=(ALL) NOPASSWD: ALL
        """

        msg = QMessageBox(self)
        msg.setWindowTitle("Instruções de Instalação Manual")
        msg.setText(instructions)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()

    def _skip_installation(self):
        """Skip installation and continue with limited functionality."""
        if self.remember_checkbox.isChecked():
            self._save_install_preference(False)

        self.installation_complete.emit(False, "Instalação pulada - funcionalidades limitadas")
        self.reject()

    def _save_install_preference(self, auto_install: bool):
        """Save user's preference for automatic installation."""
        try:
            config_dir = Path.home() / ".config" / "nitrosense"
            config_dir.mkdir(parents=True, exist_ok=True)
            config_file = config_dir / "install_preferences.json"

            import json
            prefs = {"auto_install_dependencies": auto_install}
            config_file.write_text(json.dumps(prefs, indent=2))
            logger.info(f"Saved install preference: auto_install={auto_install}")
        except Exception as e:
            logger.warning(f"Failed to save install preference: {e}")

    @staticmethod
    def load_install_preference() -> Optional[bool]:
        """Load user's saved preference for automatic installation."""
        try:
            config_file = Path.home() / ".config" / "nitrosense" / "install_preferences.json"
            if config_file.exists():
                import json
                prefs = json.loads(config_file.read_text())
                return prefs.get("auto_install_dependencies")
        except Exception as e:
            logger.debug(f"Failed to load install preference: {e}")
        return None