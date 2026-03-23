#!/bin/bash
# SwarmIA Ultra Simple Installer - Minimal dependencies

set -e

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuración
SWARMIA_DIR="/opt/swarmia"
CONFIG_DIR="/etc/swarmia"
LOGS_DIR="/var/log/swarmia"
DATA_DIR="/var/lib/swarmia"
PORT="3000"
REPO_URL="https://github.com/nicky686-22/test.git"

# Banner
echo -e "${GREEN}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║              SwarmIA Ultra Simple Installer                  ║"
echo "║                     Fast & Minimal                           ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Verificar root
if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}[!] This installer must be run as root${NC}"
    exit 1
fi

echo -e "${BLUE}[*] Starting installation...${NC}"

# Crear directorios
mkdir -p "$SWARMIA_DIR" "$CONFIG_DIR" "$LOGS_DIR" "$DATA_DIR"

# Descargar directamente con wget (más rápido)
echo -e "${BLUE}[*] Downloading SwarmIA...${NC}"
cd /tmp
wget -q "$REPO_URL/archive/main.zip" -O swarmia.zip
unzip -q swarmia.zip -d "$SWARMIA_DIR"
mv "$SWARMIA_DIR/test-main"/* "$SWARMIA_DIR/"
rm -rf "$SWARMIA_DIR/test-main" swarmia.zip
echo -e "${GREEN}[✓] Downloaded successfully${NC}"

# Instalar solo Flask (lo mínimo)
echo -e "${BLUE}[*] Installing minimal dependencies...${NC}"
apt-get update > /dev/null 2>&1
apt-get install -y python3-flask python3-requests > /dev/null 2>&1
echo -e "${GREEN}[✓] Dependencies installed${NC}"

# Crear archivo de configuración
echo -e "${BLUE}[*] Creating configuration...${NC}"
cat > "$CONFIG_DIR/config.yaml" << CONFIG_EOF
# SwarmIA Configuration
server:
  host: "0.0.0.0"
  port: $PORT
  debug: false

ai:
  backend: "deepseek"
  deepseek:
    api_key: ""
    model: "deepseek-chat"

messaging:
  platform: "none"

database:
  path: "$DATA_DIR/swarmia.db"
  type: "sqlite"

logging:
  level: "INFO"
  file: "$LOGS_DIR/swarmia.log"
CONFIG_EOF
echo -e "${GREEN}[✓] Configuration created${NC}"

# Crear servicio systemd
echo -e "${BLUE}[*] Creating service...${NC}"
cat > /etc/systemd/system/swarmia.service << SERVICE_EOF
[Unit]
Description=SwarmIA AI System
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$SWARMIA_DIR
Environment="PYTHONPATH=$SWARMIA_DIR"
Environment="SWARMIA_CONFIG=$CONFIG_DIR/config.yaml"
ExecStart=/usr/bin/python3 $SWARMIA_DIR/src/core/main.py
Restart=on-failure
RestartSec=5
StandardOutput=append:$LOGS_DIR/swarmia.log
StandardError=append:$LOGS_DIR/swarmia-error.log

[Install]
WantedBy=multi-user.target
SERVICE_EOF

systemctl daemon-reload
echo -e "${GREEN}[✓] Service created${NC}"

# Iniciar servicio
echo -e "${BLUE}[*] Starting SwarmIA...${NC}"
systemctl enable swarmia > /dev/null 2>&1
systemctl start swarmia > /dev/null 2>&1

sleep 2

# Verificar
if systemctl is-active --quiet swarmia; then
    echo -e "${GREEN}[✓] SwarmIA is running${NC}"
else
    # Intentar iniciar manualmente
    echo -e "${YELLOW}[*] Trying manual start...${NC}"
    cd "$SWARMIA_DIR"
    nohup python3 src/core/main.py > "$LOGS_DIR/swarmia.log" 2>&1 &
    sleep 2
    if ps aux | grep -v grep | grep -q "python3.*main.py"; then
        echo -e "${GREEN}[✓] SwarmIA started manually${NC}"
    else
        echo -e "${RED}[!] Failed to start${NC}"
    fi
fi

# Mostrar información
IP=$(hostname -I | awk '{print $1}')
echo ""
echo -e "${GREEN}✅ Installation complete!${NC}"
echo ""
echo -e "${CYAN}Access:${NC} http://$IP:$PORT"
echo -e "${CYAN}Health:${NC} http://$IP:$PORT/health"
echo ""
echo -e "${GREEN}══════════════════════════════════════════════════════════════${NC}"
