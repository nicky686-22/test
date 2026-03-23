#!/bin/bash
# SwarmIA Cleanup Script - Wrapper
# Ejecuta: curl -sSL https://raw.githubusercontent.com/nicky686-22/test/main/clean.sh | sudo bash

set -e

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Banner
echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                 🧹 SwarmIA Cleanup Script                    ║"
echo "║               Eliminación completa del sistema              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Verificar root
if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}[!] Este script debe ejecutarse como root${NC}"
    echo -e "${YELLOW}Usa: sudo bash -c \"\$(curl -sSL https://raw.githubusercontent.com/nicky686-22/test/main/clean.sh)\"${NC}"
    exit 1
fi

# Verificar python3
if ! command -v python3 >/dev/null 2>&1; then
    echo -e "${RED}[!] python3 no encontrado. Instalando...${NC}"
    apt update && apt install -y python3
fi

# Descargar script de limpieza Python
echo -e "${BLUE}[*] Descargando script de limpieza...${NC}"
TEMP_SCRIPT="/tmp/swarmia_clean_$(date +%s).py"

if ! curl -sSL --fail "https://raw.githubusercontent.com/nicky686-22/test/main/clean.py" -o "$TEMP_SCRIPT"; then
    echo -e "${RED}[!] Error: No se pudo descargar clean.py${NC}"
    echo -e "${RED}[!] Verifica que el archivo exista en el repositorio${NC}"
    exit 1
fi

if [[ ! -s "$TEMP_SCRIPT" ]]; then
    echo -e "${RED}[!] Error: Archivo descargado vacío${NC}"
    exit 1
fi

echo -e "${GREEN}[✓] Script de limpieza listo${NC}"
echo ""

# Confirmar antes de limpiar
echo -e "${YELLOW}⚠️  Esta acción eliminará COMPLETAMENTE SwarmIA del sistema.${NC}"
echo -e "${YELLOW}⚠️  Toda la configuración, datos y logs serán eliminados.${NC}"
echo ""
echo -e "${BLUE}¿Estás seguro? (escribe SI para confirmar): ${NC}"
read -r response

if [[ "$response" != "SI" ]]; then
    echo -e "${YELLOW}❌ Limpieza cancelada.${NC}"
    exit 0
fi

echo ""
echo -e "${GREEN}✅ Iniciando limpieza...${NC}"
echo ""

# Ejecutar el script Python con --no-interactive
python3 "$TEMP_SCRIPT" --no-interactive

# Limpiar archivo temporal
rm -f "$TEMP_SCRIPT"

echo ""
echo -e "${GREEN}✅ Limpieza completada.${NC}"
