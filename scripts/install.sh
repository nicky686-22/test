#!/bin/bash
# SwarmIA Universal Installer - Ultimate Version

set -e

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Banner
echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                 SwarmIA Universal Installer                  ║"
echo "║                 Ultimate Version v2.0.0                      ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Verificar root
if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}[!] This installer must be run as root${NC}"
    exit 1
fi

# Descargar y ejecutar el instalador ultimate
echo -e "${BLUE}[*] Downloading ultimate installer...${NC}"
TEMP_SCRIPT="/tmp/swarmia_ultimate_$(date +%s).sh"

curl -sSL https://raw.githubusercontent.com/nicky686-22/test/main/scripts/install_ultimate.sh -o "$TEMP_SCRIPT"
chmod +x "$TEMP_SCRIPT"

echo -e "${GREEN}[✓] Ultimate installer ready${NC}"
echo ""

# Ejecutar
exec "$TEMP_SCRIPT"
