#!/bin/bash
# SwarmIA Universal Installer - Phase 1
# Works with: curl -sSL https://raw.githubusercontent.com/nicky686-22/test/main/scripts/install.sh | sudo bash

set -e

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# URLs
REPO_URL="https://github.com/nicky686-22/test.git"
INSTALLER_URL="https://raw.githubusercontent.com/nicky686-22/test/main/scripts/full_installer.sh"
TEMP_DIR="/tmp/swarmia_install"

# Banner
echo -e "${GREEN}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                 SwarmIA Universal Installer                  ║"
echo "║                     Phase 1 - Bootstrap                      ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Verificar root
if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}[!] This installer must be run as root${NC}"
    echo -e "${YELLOW}Please run: sudo bash <(curl -sSL $INSTALLER_URL)${NC}"
    exit 1
fi

# Detectar si hay terminal interactivo
if [ -t 0 ]; then
    INTERACTIVE=true
    echo -e "${BLUE}[*] Interactive terminal detected${NC}"
else
    INTERACTIVE=false
    echo -e "${YELLOW}[*] Non-interactive mode (curl | bash)${NC}"
fi

# Crear directorio temporal
echo -e "${BLUE}[*] Preparing installation...${NC}"
rm -rf "$TEMP_DIR"
mkdir -p "$TEMP_DIR"
cd "$TEMP_DIR"

# Descargar instalador completo
echo -e "${BLUE}[*] Downloading SwarmIA installer...${NC}"
curl -sSL "$INSTALLER_URL" -o swarmia_installer.sh
chmod +x swarmia_installer.sh

echo -e "${GREEN}[✓] Installer downloaded${NC}"

# Si no hay terminal interactivo, usar modo automático
if [ "$INTERACTIVE" = false ]; then
    echo -e "${YELLOW}[*] Running in automatic mode...${NC}"
    
    # Verificar si ya está instalado
    if [ -d "/opt/swarmia" ]; then
        echo -e "${BLUE}[*] SwarmIA is already installed, updating...${NC}"
        ./swarmia_installer.sh --update
    else
        echo -e "${BLUE}[*] Installing SwarmIA fresh...${NC}"
        ./swarmia_installer.sh --install
    fi
else
    # Modo interactivo: ejecutar el instalador
    echo -e "${GREEN}[✓] Starting interactive installer...${NC}"
    echo ""
    exec ./swarmia_installer.sh
fi
