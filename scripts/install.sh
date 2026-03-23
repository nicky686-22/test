#!/bin/bash
# SwarmIA Universal Installer - Complete with Dashboard

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
echo "║                 Complete with Dashboard                      ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Verificar root
if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}[!] This installer must be run as root${NC}"
    exit 1
fi

# Descargar y ejecutar el instalador completo
echo -e "${BLUE}[*] Downloading complete installer...${NC}"
TEMP_SCRIPT="/tmp/swarmia_complete_$(date +%s).sh"

curl -sSL https://raw.githubusercontent.com/nicky686-22/test/main/scripts/install_complete.sh -o "$TEMP_SCRIPT"
chmod +x "$TEMP_SCRIPT"

echo -e "${GREEN}[✓] Installer ready${NC}"
echo ""

# Ejecutar
exec "$TEMP_SCRIPT"
