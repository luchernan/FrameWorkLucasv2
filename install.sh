#!/usr/bin/env bash
# ============================================================
#  Fr4meLuc — Instalador
#  Requisitos: Kali Linux / Distribuciones basadas en Debian
# ============================================================
set -e

YELLOW='\033[1;33m'
GREEN='\033[0;32m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}"
echo "  ╔═════════════════════════════════════════════════╗"
echo "  ║              Fr4meLuc — Instalador              ║"
echo "  ╚═════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check root
if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}[!] Este script debe ejecutarse como root (sudo ./install.sh)${NC}"
    exit 1
fi

echo -e "${YELLOW}[*] Actualizando repositorios...${NC}"
apt update -qq

echo -e "${YELLOW}[*] Instalando herramientas del sistema...${NC}"
apt install -y \
    nmap \
    gobuster \
    nikto \
    ffuf \
    wpscan \
    hydra \
    sqlmap \
    enum4linux \
    exploitdb \
    netcat-traditional \
    arp-scan \
    john \
    python3-pip 2>/dev/null || true

echo -e "${YELLOW}[*] Instalando Nuclei...${NC}"
if ! command -v nuclei &>/dev/null; then
    apt install -y nuclei 2>/dev/null || \
    go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest 2>/dev/null || \
    echo -e "${YELLOW}[!] Instala Nuclei manualmente: https://github.com/projectdiscovery/nuclei${NC}"
fi

echo -e "${YELLOW}[*] Instalando dependencias Python...${NC}"
pip3 install -r requirements.txt -q

echo -e "${YELLOW}[*] Actualizando plantillas de Nuclei...${NC}"
nuclei -ut -silent 2>/dev/null || true

chmod +x motor.py

echo -e "${GREEN}"
echo "  [+] Instalación completada."
echo "  [+] Ejecuta: sudo python3 motor.py"
echo -e "${NC}"
