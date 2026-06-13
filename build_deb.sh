#!/usr/bin/env bash
# Construye fr4meluc_3.0.0_all.deb usando dpkg-deb (sin fpm ni stdeb).
# Uso: ./build_deb.sh
# Requiere: python3, pip, dpkg-deb (todos presentes en Kali por defecto).
set -euo pipefail

PKG="fr4meluc"
VERSION="3.0.0"
ARCH="all"
DEB_NAME="${PKG}_${VERSION}_${ARCH}.deb"
STAGING="$(mktemp -d)"
trap 'rm -rf "$STAGING"' EXIT

echo "[*] Staging dir: $STAGING"

# 1. Estructura de directorios
mkdir -p "$STAGING/DEBIAN"
mkdir -p "$STAGING/usr/bin"
mkdir -p "$STAGING/usr/lib/python3/dist-packages"
mkdir -p "$STAGING/lib/systemd/system"

# 2. Instalar el paquete Python en el staging dir
echo "[*] Instalando fr4meluc con pip --target..."
pip install . \
    --target "$STAGING/usr/lib/python3/dist-packages" \
    --no-deps \
    --quiet

# (instalar dependencias base también)
pip install colorama requests apscheduler \
    --target "$STAGING/usr/lib/python3/dist-packages" \
    --quiet

# 3. Wrappers en /usr/bin
cat > "$STAGING/usr/bin/fr4meluc" << 'WRAPPER'
#!/usr/bin/env python3
import sys
sys.path.insert(0, '/usr/lib/python3/dist-packages')
from fr4meluc.cli.main import main
main()
WRAPPER

cat > "$STAGING/usr/bin/fr4meluc-gui" << 'WRAPPER'
#!/usr/bin/env python3
import sys
sys.path.insert(0, '/usr/lib/python3/dist-packages')
from fr4meluc.gui.app import run_gui
run_gui()
WRAPPER

chmod +x "$STAGING/usr/bin/fr4meluc"
chmod +x "$STAGING/usr/bin/fr4meluc-gui"

# 4. Unidad systemd
if [ -f "fr4meluc-daemon.service" ]; then
    cp "fr4meluc-daemon.service" "$STAGING/lib/systemd/system/"
fi

# 5. Control file
cat > "$STAGING/DEBIAN/control" << CONTROL
Package: ${PKG}
Version: ${VERSION}
Architecture: ${ARCH}
Maintainer: Fr4meLuc <fr4meluc@localhost>
Depends: python3 (>= 3.9), python3-pip
Recommends: python3-pyqt6, nmap, gobuster, nikto, ffuf, wpscan, hydra, sqlmap, enum4linux, john, nuclei
Description: Fr4meLuc Enterprise Pentesting Framework
 CLI and GUI pentesting framework with automated pipeline,
 multi-target parallel scanning, professional PDF/DOCX reports,
 Slack/Teams/Jira/webhook integrations, and APScheduler daemon.
CONTROL

# 6. Construir .deb
echo "[*] Construyendo $DEB_NAME..."
dpkg-deb --build "$STAGING" "$DEB_NAME"

echo "[+] Listo: $DEB_NAME"
echo "    Instalar: sudo dpkg -i $DEB_NAME"
echo "    Desinstalar: sudo dpkg -r ${PKG}"
