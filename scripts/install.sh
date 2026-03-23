#!/bin/bash
# SwarmIA Universal Installer - Direct and Fast

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
echo "║                     Direct & Fast                            ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Verificar root
if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}[!] This installer must be run as root${NC}"
    exit 1
fi

echo -e "${BLUE}[*] Starting installation...${NC}"

# Configuración
SWARMIA_DIR="/opt/swarmia"
CONFIG_DIR="/etc/swarmia"
LOGS_DIR="/var/log/swarmia"
DATA_DIR="/var/lib/swarmia"
PORT="3000"

# Crear directorios
mkdir -p "$SWARMIA_DIR" "$CONFIG_DIR" "$LOGS_DIR" "$DATA_DIR"

# Limpiar instalación anterior
echo -e "${BLUE}[*] Cleaning previous installation...${NC}"
systemctl stop swarmia 2>/dev/null || true
rm -rf "$SWARMIA_DIR"/*

# Instalar dependencias mínimas
echo -e "${BLUE}[*] Installing dependencies...${NC}"
apt-get update > /dev/null 2>&1
apt-get install -y python3 python3-flask python3-requests > /dev/null 2>&1
echo -e "${GREEN}[✓] Dependencies installed${NC}"

# Crear estructura básica de SwarmIA
echo -e "${BLUE}[*] Creating SwarmIA structure...${NC}"

# Crear main.py básico
mkdir -p "$SWARMIA_DIR/src/core"
cat > "$SWARMIA_DIR/src/core/main.py" << 'PYTHON_EOF'
#!/usr/bin/env python3
"""
SwarmIA - Minimal AI System
"""

from flask import Flask, jsonify, request
import os
import json

app = Flask(__name__)

# Cargar configuración
config_path = os.getenv('SWARMIA_CONFIG', '/etc/swarmia/config.yaml')
config = {
    'server': {'host': '0.0.0.0', 'port': 3000, 'debug': False},
    'ai': {'backend': 'deepseek'},
    'messaging': {'platform': 'none'}
}

@app.route('/')
def index():
    return jsonify({
        'name': 'SwarmIA',
        'version': '1.0.0',
        'status': 'running'
    })

@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'version': '1.0.0'})

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.get_json()
    message = data.get('message', '')
    
    return jsonify({
        'response': f'SwarmIA received: {message}',
        'ai_backend': config['ai']['backend']
    })

if __name__ == '__main__':
    host = config['server']['host']
    port = config['server']['port']
    debug = config['server']['debug']
    
    print(f"SwarmIA starting on http://{host}:{port}")
    app.run(host=host, port=port, debug=debug)
PYTHON_EOF

chmod +x "$SWARMIA_DIR/src/core/main.py"
echo -e "${GREEN}[✓] SwarmIA created${NC}"

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
        echo -e "${YELLOW}[*] Check logs: tail -f $LOGS_DIR/swarmia.log${NC}"
    fi
fi

# Mostrar información
IP=$(hostname -I | awk '{print $1}')
echo ""
echo -e "${GREEN}✅ Installation complete!${NC}"
echo ""
echo -e "${CYAN}Access:${NC} http://$IP:$PORT"
echo -e "${CYAN}Health:${NC} http://$IP:$PORT/health"
echo -e "${CYAN}API Chat:${NC} POST http://$IP:$PORT/api/chat"
echo ""
echo -e "${GREEN}══════════════════════════════════════════════════════════════${NC}"
