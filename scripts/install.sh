
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

# Verificar curl
if ! command -v curl >/dev/null 2>&1; then
    echo -e "${RED}[!] curl not found. Please install curl.${NC}"
    exit 1
fi

# Descargar lógica real de instalación
echo -e "${BLUE}[*] Downloading installation script...${NC}"
TEMP_SCRIPT="/tmp/swarmia_core_$(date +%s).sh"

curl -sSL https://raw.githubusercontent.com/nicky686-22/test/main/scripts/swarmia_core.sh -o "$TEMP_SCRIPT"

if [[ ! -s "$TEMP_SCRIPT" ]]; then
    echo -e "${RED}[!] Download failed. File is empty.${NC}"
    exit 1
fi

chmod +x "$TEMP_SCRIPT"

echo -e "${GREEN}[✓] Core installer ready${NC}"
echo ""

# Ejecutar de forma segura
bash "$TEMP_SCRIPT"
