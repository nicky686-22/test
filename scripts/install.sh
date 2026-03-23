#!/bin/bash
# SwarmIA Universal Installer - Simple version
# Works with: curl -sSL https://raw.githubusercontent.com/nicky686-22/test/main/scripts/install.sh | sudo bash

set -e

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Banner
echo -e "${GREEN}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                 SwarmIA Universal Installer                  ║"
echo "║                     Simple & Reliable                        ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Verificar root
if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}[!] This installer must be run as root${NC}"
    echo -e "${YELLOW}Please run: sudo bash <(curl -sSL https://raw.githubusercontent.com/nicky686-22/test/main/scripts/install.sh)${NC}"
    exit 1
fi

# Descargar y ejecutar el instalador simple
echo -e "${BLUE}[*] Downloading SwarmIA installer...${NC}"
TEMP_DIR="/tmp/swarmia_install_$(date +%s)"
mkdir -p "$TEMP_DIR"
cd "$TEMP_DIR"

curl -sSL https://raw.githubusercontent.com/nicky686-22/test/main/scripts/simple_installer.sh -o swarmia_installer.sh
chmod +x swarmia_installer.sh

echo -e "${GREEN}[✓] Installer ready${NC}"
echo ""

# Ejecutar el instalador
exec ./swarmia_installer.sh
