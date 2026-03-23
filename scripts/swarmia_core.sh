
#!/bin/bash
# SwarmIA Core Installer - Versión Estable con manejo de errores

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}[*] Iniciando instalación de SwarmIA Core...${NC}"
echo ""

INSTALL_DIR="/opt/swarmia"
PYTHON_VERSION=""

# ============================================
# FUNCIÓN: Verificar versión de Python
# ============================================
check_python_version() {
    if ! command -v python3 >/dev/null 2>&1; then
        echo -e "${RED}[!] Python3 no encontrado. Instalando...${NC}"
        apt update && apt install -y python3 python3-venv python3-pip
        return 1
    fi
    
    PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
    
    echo -e "${BLUE}[*] Versión de Python detectada: ${YELLOW}$PYTHON_VERSION${NC}"
    
    if [[ $PYTHON_MAJOR -eq 3 ]] && [[ $PYTHON_MINOR -gt 12 ]]; then
        echo -e "${YELLOW}[!] ADVERTENCIA: Python $PYTHON_VERSION detectado${NC}"
        echo -e "${YELLOW}[!] SwarmIA fue probado con Python 3.12. Puede haber incompatibilidades.${NC}"
        echo -e "${YELLOW}[!] Continuando con la instalación...${NC}"
        echo ""
        return 0
    fi
    
    if [[ $PYTHON_MAJOR -eq 3 ]] && [[ $PYTHON_MINOR -lt 8 ]]; then
        echo -e "${RED}[!] ERROR: Python $PYTHON_VERSION no es compatible${NC}"
        echo -e "${RED}[!] Se requiere Python 3.8 o superior${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}[✓] Versión de Python compatible${NC}"
    return 0
}

# ============================================
# FUNCIÓN: Verificar si ya está instalado
# ============================================
check_installed() {
    if [[ -d "$INSTALL_DIR/venv" ]] && [[ -f "$INSTALL_DIR/venv/bin/python" ]]; then
        if "$INSTALL_DIR/venv/bin/pip" list 2>/dev/null | grep -q "fastapi"; then
            return 0
        fi
    fi
    return 1
}

# ============================================
# FUNCIÓN: Instalar dependencias
# ============================================
install_dependencies() {
    echo -e "${BLUE}[*] Creando entorno virtual...${NC}"
    python3 -m venv venv
    
    echo -e "${BLUE}[*] Actualizando pip, setuptools y wheel...${NC}"
    "$INSTALL_DIR/venv/bin/pip" install --upgrade pip setuptools wheel
    
    echo -e "${BLUE}[*] Instalando pyyaml primero (evita errores)...${NC}"
    "$INSTALL_DIR/venv/bin/pip" install pyyaml==6.0.1
    
    echo -e "${BLUE}[*] Instalando dependencias restantes...${NC}"
    if [[ -f "$INSTALL_DIR/requirements.txt" ]]; then
        "$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt"
    else
        "$INSTALL_DIR/venv/bin/pip" install fastapi uvicorn pydantic python-dotenv click
    fi
    
    echo -e "${GREEN}[✓] Dependencias instaladas correctamente${NC}"
}

# ============================================
# FUNCIÓN: Configurar archivos
# ============================================
setup_config() {
    mkdir -p "$INSTALL_DIR"/{logs,data,config}
    
    if [[ ! -f "$INSTALL_DIR/.env" ]]; then
        echo -e "${BLUE}[*] Creando archivo .env...${NC}"
        cat > "$INSTALL_DIR/.env" << 'EOF'
FLASK_SECRET_KEY=changeme
ADMIN_USER=admin
ADMIN_PASSWORD_HASH=8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918
SWARMIA_HOST=0.0.0.0
SWARMIA_PORT=8080
EOF
    else
        echo -e "${GREEN}[✓] .env ya existe, conservando${NC}"
    fi
    
    if [[ ! -f "$INSTALL_DIR/config/config.yaml" ]]; then
        echo -e "${BLUE}[*] Creando config/config.yaml...${NC}"
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
    else
        echo -e "${GREEN}[✓] config/config.yaml ya existe, conservando${NC}"
    fi
}

# ============================================
# INICIO DE LA INSTALACIÓN
# ============================================

# 1. Verificar dependencias básicas
echo -e "${BLUE}[*] Verificando dependencias del sistema...${NC}"

for cmd in git curl wget; do
    if ! command -v $cmd >/dev/null 2>&1; then
        echo -e "${YELLOW}[!] Instalando $cmd...${NC}"
        apt update && apt install -y $cmd
    fi
done

# 2. Verificar versión de Python
check_python_version

# 3. Preparar directorio de instalación
echo -e "${BLUE}[*] Preparando directorio de instalación...${NC}"

if [[ -d "$INSTALL_DIR/.git" ]]; then
    echo -e "${GREEN}[✓] Instalación existente detectada en $INSTALL_DIR${NC}"
    cd "$INSTALL_DIR"
    echo -e "${BLUE}[*] Actualizando repositorio...${NC}"
    git pull origin main
else
    echo -e "${BLUE}[*] Clonando repositorio...${NC}"
    rm -rf "$INSTALL_DIR"
    git clone https://github.com/nicky686-22/test.git "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# 4. Instalar dependencias (saltar si ya están)
if check_installed; then
    echo -e "${GREEN}[✓] Dependencias Python ya instaladas. Saltando...${NC}"
else
    install_dependencies
fi

# 5. Configurar archivos
setup_config

# 6. Permisos
chown -R $(logname 2>/dev/null || echo $SUDO_USER || echo "root"): "$INSTALL_DIR" 2>/dev/null || true
chmod +x "$INSTALL_DIR/src/main.py" 2>/dev/null || true

# 7. Crear servicio systemd
if command -v systemctl >/dev/null 2>&1; then
    echo -e "${BLUE}[*] Creando servicio systemd...${NC}"
    
    cat > /etc/systemd/system/swarmia.service << EOF
[Unit]
Description=SwarmIA Distributed Agents System
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/src/core/main.py
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

# 8. Crear comando global
cat > /usr/local/bin/swarmia << 'EOF'
#!/bin/bash
cd /opt/swarmia && /opt/swarmia/venv/bin/python src/ui/server.py "$@"
EOF
chmod +x /usr/local/bin/swarmia

# 9. Mostrar resultado
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    INSTALACIÓN COMPLETADA                    ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}📁 Instalado en: ${YELLOW}$INSTALL_DIR${NC}"
echo -e "${CYAN}🌐 Dashboard: ${YELLOW}http://localhost:8080${NC}"
echo -e "${CYAN}🔑 Credenciales: ${YELLOW}admin / admin${NC}"
echo ""
echo -e "${CYAN}🐍 Versión Python detectada: ${YELLOW}$PYTHON_VERSION${NC}"
echo ""
echo -e "${BLUE}Comandos útiles:${NC}"
echo -e "  ${GREEN}systemctl status swarmia${NC}  - Ver estado del servicio"
echo -e "  ${GREEN}systemctl restart swarmia${NC} - Reiniciar servicio"
echo -e "  ${GREEN}journalctl -u swarmia -f${NC}   - Ver logs en tiempo real"
echo -e "  ${GREEN}swarmia${NC}                   - Iniciar manualmente"
echo ""
echo -e "${YELLOW}[!] IMPORTANTE: Cambia las credenciales en el primer acceso${NC}"
