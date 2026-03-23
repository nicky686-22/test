#!/bin/bash
# SwarmIA Core Installer
# Lógica real de instalación con entorno virtual

set -e

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}[*] Iniciando instalación de SwarmIA Core...${NC}"
echo ""

# Verificar dependencias
echo -e "${BLUE}[*] Verificando dependencias...${NC}"

MISSING=""
for cmd in python3 git; do
    if ! command -v $cmd >/dev/null 2>&1; then
        MISSING="$MISSING $cmd"
    fi
done

# Verificar python3-venv
if ! python3 -c "import venv" 2>/dev/null; then
    MISSING="$MISSING python3-venv"
fi

if [[ -n "$MISSING" ]]; then
    echo -e "${YELLOW}[!] Instalando dependencias faltantes:${NC}$MISSING"
    
    if command -v apt >/dev/null 2>&1; then
        apt update
        apt install -y python3 python3-venv git
    elif command -v yum >/dev/null 2>&1; then
        yum install -y python3 python3-virtualenv git
    else
        echo -e "${RED}[!] No se pudo instalar dependencias automáticamente${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}[✓] Dependencias OK${NC}"

# Directorio de instalación
INSTALL_DIR="/opt/swarmia"
echo -e "${BLUE}[*] Instalando en: ${YELLOW}$INSTALL_DIR${NC}"

# Clonar o actualizar repositorio
if [[ -d "$INSTALL_DIR/.git" ]]; then
    echo -e "${BLUE}[*] Actualizando instalación existente...${NC}"
    cd "$INSTALL_DIR"
    git pull origin main
else
    echo -e "${BLUE}[*] Clonando repositorio...${NC}"
    rm -rf "$INSTALL_DIR"
    git clone https://github.com/nicky686-22/test.git "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"

# Crear entorno virtual
echo -e "${BLUE}[*] Creando entorno virtual...${NC}"
python3 -m venv venv

# Instalar dependencias Python en el entorno virtual
echo -e "${BLUE}[*] Instalando dependencias Python...${NC}"
"$INSTALL_DIR/venv/bin/pip" install --upgrade pip

if [[ -f "$INSTALL_DIR/requirements.txt" ]]; then
    "$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt"
else
    echo -e "${YELLOW}[!] requirements.txt no encontrado, instalando mínimos...${NC}"
    "$INSTALL_DIR/venv/bin/pip" install flask flask-socketio python-dotenv requests
fi

# Crear directorios adicionales
mkdir -p "$INSTALL_DIR"/{logs,data,config}

# Configuración por defecto
if [[ ! -f "$INSTALL_DIR/config/config.yaml" ]]; then
    echo -e "${BLUE}[*] Creando configuración por defecto...${NC}"
    cat > "$INSTALL_DIR/config/config.yaml" << 'EOF'
app:
  name: "SwarmIA"
  host: "0.0.0.0"
  port: 8080
  debug: false

models:
  deepseek:
    enabled: false
    api_key: ""
  llama:
    enabled: false
    model_path: ""

gateways:
  whatsapp:
    enabled: false
  telegram:
    enabled: false
    bot_token: ""

security:
  session_timeout: 3600
  max_login_attempts: 5
EOF
fi

# Archivo .env por defecto
if [[ ! -f "$INSTALL_DIR/.env" ]]; then
    echo -e "${BLUE}[*] Creando archivo .env...${NC}"
    cat > "$INSTALL_DIR/.env" << 'EOF'
FLASK_SECRET_KEY=changeme
ADMIN_USER=admin
ADMIN_PASSWORD_HASH=8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918
SWARMIA_HOST=0.0.0.0
SWARMIA_PORT=8080
EOF
fi

# Permisos
chown -R $(logname 2>/dev/null || echo $SUDO_USER || echo "root"): "$INSTALL_DIR" 2>/dev/null || true
chmod +x "$INSTALL_DIR/src/main.py" 2>/dev/null || true

# Crear servicio systemd
if command -v systemctl >/dev/null 2>&1; then
    echo -e "${BLUE}[*] Creando servicio systemd...${NC}"
    
    cat > /etc/systemd/system/swarmia.service << EOF
[Unit]
Description=SwarmIA Distributed Agents System
After=network.target

[Service]
Type=simple
User=$(logname 2>/dev/null || echo $SUDO_USER || echo "root")
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/src/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable swarmia.service
    systemctl start swarmia.service
    echo -e "${GREEN}[✓] Servicio creado e iniciado${NC}"
fi

# Script de arranque
cat > /usr/local/bin/swarmia << 'EOF'
#!/bin/bash
cd /opt/swarmia && /opt/swarmia/venv/bin/python src/main.py "$@"
EOF
chmod +x /usr/local/bin/swarmia

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    INSTALACIÓN COMPLETADA                    ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}📁 Instalado en: ${YELLOW}$INSTALL_DIR${NC}"
echo -e "${CYAN}🌐 Dashboard: ${YELLOW}http://localhost:8080${NC}"
echo -e "${CYAN}🔑 Credenciales: ${YELLOW}admin / admin${NC}"
echo ""
echo -e "${BLUE}Comandos útiles:${NC}"
echo -e "  ${GREEN}swarmia${NC}                   - Iniciar manualmente"
echo -e "  ${GREEN}systemctl start swarmia${NC}   - Iniciar servicio"
echo -e "  ${GREEN}systemctl status swarmia${NC}  - Ver estado"
echo -e "  ${GREEN}journalctl -u swarmia -f${NC}  - Ver logs en tiempo real"
echo ""
echo -e "${YELLOW}[!] IMPORTANTE: Cambia las credenciales en el primer acceso${NC}"
