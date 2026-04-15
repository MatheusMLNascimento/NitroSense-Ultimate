#!/bin/bash
# Script simples para criar pacote .deb do NitroSense

set -e
cd "$(dirname "$0")"

echo "📦 Criando pacote .deb do NitroSense Ultimate..."

# Criar estrutura temporária
DEB_DIR="$(mktemp -d)"
trap 'rm -rf "$DEB_DIR"' EXIT
mkdir -p "$DEB_DIR/DEBIAN"
mkdir -p "$DEB_DIR/usr/local/bin"
mkdir -p "$DEB_DIR/usr/share/applications"
mkdir -p "$DEB_DIR/usr/share/nitrosense"

# Copiar arquivos selecionados
echo "Copiando arquivos..."
rsync -a --exclude='.git' \
      --exclude='tests' \
      --exclude='DOCS' \
      --exclude='*.pyc' \
      --exclude='__pycache__' \
      --exclude='.pytest_cache' \
      --exclude='venv' \
      --exclude='*.log' \
      --exclude='*.deb' \
      --exclude='create_deb.sh' \
      --exclude='.gitignore' \
      ./ "$DEB_DIR/usr/share/nitrosense/"

# Criar arquivo de controle
cat > "$DEB_DIR/DEBIAN/control" << 'EOF'
Package: nitrosense
Version: 3.0.5
Section: utils
Priority: optional
Architecture: all
Depends: python3 (>=3.12), python3-pyqt6, python3-matplotlib, python3-psutil, python3-numpy
Maintainer: NitroSense Team <nitrosense@example.com>
Description: Professional Fan & Thermal Control for Acer Nitro 5
 Professional thermal management system with AI-powered fan control,
 hardware monitoring, and comprehensive diagnostics for Acer Nitro 5 laptops.
 .
 Features:
  * AI-powered predictive thermal management
  * Real-time hardware monitoring
  * Advanced fan control with NBFC integration
  * Comprehensive diagnostics and system integrity checks
  * Modern PyQt6 graphical interface
  * Resilience framework with watchdog protection
EOF

# Criar script de pós-instalação
cat > "$DEB_DIR/DEBIAN/postinst" << 'EOF'
#!/bin/bash
set -e
chmod +x /usr/local/bin/nitrosense
chmod +x /usr/share/nitrosense/main.py
update-desktop-database /usr/share/applications 2>/dev/null || true
echo "NitroSense Ultimate installed successfully!"
echo "Run with: nitrosense"
EOF

chmod +x "$DEB_DIR/DEBIAN/postinst"

# Criar arquivo desktop
cat > "$DEB_DIR/usr/share/applications/nitrosense.desktop" << 'EOF'
[Desktop Entry]
Version=3.0.5
Type=Application
Name=NitroSense Ultimate
Comment=Professional Fan & Thermal Control for Acer Nitro 5
Exec=nitrosense
Icon=nitrosense
Terminal=false
Categories=Utility;System;Monitor;
Keywords=fan;thermal;control;nitro;acer;nvidia;monitoring;
StartupNotify=true
EOF

# Criar launcher
cat > "$DEB_DIR/usr/local/bin/nitrosense" << 'EOF'
#!/bin/bash
# NitroSense Ultimate Launcher

# Check if running in graphical environment
if [ -z "$DISPLAY" ] && [ -z "$WAYLAND_DISPLAY" ]; then
    echo "Error: NitroSense requires a graphical environment (X11 or Wayland)"
    echo "Please run from a desktop environment or set DISPLAY variable"
    exit 1
fi

# Quick dependency check
python3 -c "import PyQt6, psutil, matplotlib, numpy" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Error: Missing required Python dependencies"
    echo "Please install: python3-pyqt6, python3-psutil, python3-matplotlib, python3-numpy"
    exit 1
fi

# Set working directory and Python path
cd /usr/share/nitrosense
export PYTHONPATH="/usr/share/nitrosense:$PYTHONPATH"

# Execute the application
exec python3 main.py "$@"
EOF

chmod +x "$DEB_DIR/usr/local/bin/nitrosense"

# Criar o pacote
echo "Criando pacote .deb..."
dpkg-deb --build "$DEB_DIR" "nitrosense_3.0.5_all.deb"

if [ -f "nitrosense_3.0.5_all.deb" ]; then
    echo "✅ Pacote criado com sucesso: nitrosense_3.0.5_all.deb"
    echo "📦 Para instalar: sudo dpkg -i nitrosense_3.0.5_all.deb"
    echo "🚀 Para executar: nitrosense"
else
    echo "❌ Falha ao criar pacote .deb"
    exit 1
fi

# Limpar
rm -rf "$DEB_DIR"