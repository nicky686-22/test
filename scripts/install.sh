#!/bin/bash
# SwarmIA Universal Installer - Ultra Simple version

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
echo "║                     Ultra Simple & Fast                      ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Verificar root
if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}[!] This installer must be run as root${NC}"
    exit 1
fi

# Descargar y ejecutar el instalador ultra simple
echo -e "${BLUE}[*] Downloading installer...${NC}"
TEMP_SCRIPT="/tmp/swarmia_install_$(date +%s).sh"

curl -sSL https://raw.githubusercontent.com/nicky686-22/test/main/scripts/ultra_simple_installer.sh -o "$TEMP_SCRIPT"
chmod +x "$TEMP_SCRIPT"

echo -e "${GREEN}[✓] Installer ready${NC}"
echo ""

# Ejecutar
exec "$TEMP_SCRIPT"
