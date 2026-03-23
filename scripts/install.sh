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
    echo -e "${RED}[!] Este instalador debe ejecutarse como root${NC}"
    echo -e "${YELLOW}Usa: sudo bash -c \"\$(curl -sSL https://raw.githubusercontent.com/nicky686-22/test/main/scripts/install.sh)\"${NC}"
    exit 1
fi

# Verificar curl
if ! command -v curl >/dev/null 2>&1; then
    echo -e "${RED}[!] curl no encontrado. Instalando...${NC}"
    apt update && apt install -y curl || yum install -y curl
fi

# Descargar lógica real de instalación
echo -e "${BLUE}[*] Descargando instalador principal...${NC}"
TEMP_SCRIPT="/tmp/swarmia_core_$(date +%s).sh"

if ! curl -sSL --fail "https://raw.githubusercontent.com/nicky686-22/test/main/scripts/swarmia_core.sh" -o "$TEMP_SCRIPT"; then
    echo -e "${RED}[!] Error: No se pudo descargar swarmia_core.sh${NC}"
    echo -e "${RED}[!] Verifica que el archivo exista en el repositorio${NC}"
    exit 1
fi

if [[ ! -s "$TEMP_SCRIPT" ]]; then
    echo -e "${RED}[!] Error: Archivo descargado vacío${NC}"
    exit 1
fi

chmod +x "$TEMP_SCRIPT"

echo -e "${GREEN}[✓] Instalador principal listo${NC}"
echo ""

# Ejecutar de forma segura
bash "$TEMP_SCRIPT"
