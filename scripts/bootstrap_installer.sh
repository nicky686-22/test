#!/bin/bash
# Bootstrap installer for SwarmIA
# Downloads the full interactive installer and runs it

set -e

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🚀 SwarmIA Bootstrap Installer${NC}"
echo "==============================="
echo ""

# Verificar curl
if ! command -v curl >/dev/null 2>&1; then
    echo -e "${RED}[!] curl not found. Please install curl.${NC}"
    exit 1
fi

# Descargar el instalador completo
echo "📥 Downloading SwarmIA installer..."
TEMP_SCRIPT="/tmp/swarmia_full_installer.sh"

curl -sSL https://raw.githubusercontent.com/nicky686-22/test/main/scripts/full_installer.sh -o "$TEMP_SCRIPT"

# Validar descarga
if [[ ! -s "$TEMP_SCRIPT" ]]; then
    echo -e "${RED}[!] Download failed. File is empty.${NC}"
    exit 1
fi

chmod +x "$TEMP_SCRIPT"

echo -e "${GREEN}✅ Installer downloaded${NC}"
echo ""
echo "🔧 Running interactive installer..."
echo ""

# Ejecutar de forma segura
bash "$TEMP_SCRIPT"
