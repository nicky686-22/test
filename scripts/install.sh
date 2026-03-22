#!/bin/bash
# SwarmIA Installation Script - Versión Mejorada
# Soluciona problemas de GitHub raw 404 y asegura instalación completa

set -e

# Colores para output
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
print_banner() {
    clear
    echo -e "${GREEN}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                    SwarmIA Installation                      ║"
    echo "║                    Version 2.0 - Enhanced                    ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Verificar root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        echo -e "${RED}[!] This script must be run as root${NC}"
        echo -e "${YELLOW}Please run: sudo bash $0${NC}"
        exit 1
    fi
}

# Detectar sistema
detect_system() {
    echo -e "${BLUE}[*] Detecting system...${NC}"
    
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$NAME
        VER=$VERSION_ID
    else
        OS=$(uname -s)
        VER=$(uname -r)
    fi
    
    echo -e "${GREEN}[✓] Detected: $OS $VER${NC}"
}

# Instalar dependencias
install_dependencies() {
    echo -e "${BLUE}[*] Installing dependencies...${NC}"
    
    # Python y pip
    if ! command -v python3 &> /dev/null; then
        echo -e "${YELLOW}[*] Installing Python3...${NC}"
        apt-get update && apt-get install -y python3 python3-pip python3-venv
    fi
    
    # Git
    if ! command -v git &> /dev/null; then
        echo -e "${YELLOW}[*] Installing Git...${NC}"
        apt-get install -y git
    fi
    
    # Otras dependencias
    apt-get install -y curl wget net-tools
    
    echo -e "${GREEN}[✓] Dependencies installed${NC}"
}

# Crear directorios
create_directories() {
    echo -e "${BLUE}[*] Creating directories...${NC}"
    
    mkdir -p "$SWARMIA_DIR"
    mkdir -p "$CONFIG_DIR"
    mkdir -p "$LOGS_DIR"
    mkdir -p "$DATA_DIR"
    mkdir -p "$DATA_DIR/uploads"
    mkdir -p "$DATA_DIR/models"
    
    echo -e "${GREEN}[✓] Directories created${NC}"
}

# Descargar SwarmIA desde GitHub
download_swarmia() {
    echo -e "${BLUE}[*] Downloading SwarmIA from GitHub...${NC}"
    
    cd "$SWARMIA_DIR"
    
    # Método 1: Git clone (preferido)
    echo -e "${YELLOW}[*] Attempting git clone...${NC}"
    if git clone "$REPO_URL" . 2>/dev/null; then
        echo -e "${GREEN}[✓] Git clone successful${NC}"
        return 0
    fi
    
    # Método 2: Descargar archivos individuales via API
    echo -e "${YELLOW}[*] Git failed, downloading files individually...${NC}"
    
    # Lista de archivos esenciales
    ESSENTIAL_FILES=(
        "README.md"
        "requirements.txt"
        "src/core/main.py"
        "src/core/config.py"
        "src/core/supervisor.py"
        "src/core/updater.py"
        "scripts/install.sh"
        "scripts/verify_installation.py"
    )
    
    for file in "${ESSENTIAL_FILES[@]}"; do
        echo -e "  📥 Downloading: $file"
        
        # Crear directorios si no existen
        dir=$(dirname "$file")
        mkdir -p "$dir"
        
        # Intentar descargar
        curl -s -L "https://raw.githubusercontent.com/nicky686-22/SwarmIA/main/$file" \
             -o "$file" 2>/dev/null || true
        
        # Verificar que el archivo no esté vacío
        if [ -s "$file" ]; then
            echo -e "    ${GREEN}✓ Downloaded${NC}"
        else
            echo -e "    ${RED}✗ Failed to download${NC}"
        fi
    done
    
    # Verificar que tenemos los archivos mínimos
    if [ -f "requirements.txt" ] && [ -f "src/core/main.py" ]; then
        echo -e "${GREEN}[✓] Essential files downloaded${NC}"
        return 0
    else
        echo -e "${RED}[!] Failed to download essential files${NC}"
        return 1
    fi
}

# Configurar entorno Python
setup_python_env() {
    echo -e "${BLUE}[*] Setting up Python environment...${NC}"
    
    cd "$SWARMIA_DIR"
    
    # Actualizar pip
    python3 -m pip install --upgrade pip
    
    # Instalar dependencias
    if [ -f "requirements.txt" ]; then
        echo -e "${YELLOW}[*] Installing Python dependencies...${NC}"
        python3 -m pip install -r requirements.txt
        echo -e "${GREEN}[✓] Python dependencies installed${NC}"
    else
        echo -e "${YELLOW}[*] requirements.txt not found, installing common packages...${NC}"
        python3 -m pip install fastapi uvicorn python-multipart requests
        echo -e "${GREEN}[✓] Common packages installed${NC}"
    fi
}

# Crear configuración
create_config() {
    echo -e "${BLUE}[*] Creating configuration...${NC}"
    
    cat > "$CONFIG_DIR/config.yaml" << EOF
# SwarmIA Configuration
web:
  host: "0.0.0.0"
  port: 3000
  debug: false

database:
  path: "$DATA_DIR/swarmia.db"

ai:
  default_provider: "deepseek"
  deepseek_api_key: ""
  llama_endpoint: "http://localhost:11434"

security:
  admin_password: "admin"
  require_password_change: true

updates:
  check_interval_hours: 6
  github_repo: "nicky686-22/SwarmIA"
EOF
    
    echo -e "${GREEN}[✓] Configuration created at $CONFIG_DIR/config.yaml${NC}"
}

# Crear servicio systemd
setup_systemd_service() {
    echo -e "${BLUE}[*] Creating systemd service...${NC}"
    
    cat > /etc/systemd/system/swarmia.service << EOF
[Unit]
Description=SwarmIA AI System
After=network.target
Requires=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$SWARMIA_DIR
Environment="PYTHONPATH=$SWARMIA_DIR"
ExecStart=/usr/bin/python3 $SWARMIA_DIR/src/core/main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=$LOGS_DIR $DATA_DIR $CONFIG_DIR

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    systemctl enable swarmia
    
    echo -e "${GREEN}[✓] Systemd service created and enabled${NC}"
}

# Configurar firewall
setup_firewall() {
    echo -e "${BLUE}[*] Configuring firewall...${NC}"
    
    # Verificar si ufw está instalado
    if command -v ufw &> /dev/null; then
        if ufw status | grep -q "active"; then
            echo -e "${YELLOW}[*] Opening port $PORT in firewall...${NC}"
            ufw allow $PORT/tcp
            echo -e "${GREEN}[✓] Firewall configured${NC}"
        fi
    fi
    
    # Verificar si firewalld está instalado
    if command -v firewall-cmd &> /dev/null; then
        if systemctl is-active --quiet firewalld; then
            echo -e "${YELLOW}[*] Opening port $PORT in firewalld...${NC}"
            firewall-cmd --permanent --add-port=$PORT/tcp
            firewall-cmd --reload
            echo -e "${GREEN}[✓] Firewalld configured${NC}"
        fi
    fi
}

# Obtener información de red
get_network_info() {
    echo -e "${BLUE}[*] Gathering network information...${NC}"
    
    LOCAL_IP=$(hostname -I | awk '{print $1}')
    PUBLIC_IP=$(curl -s ifconfig.me || echo "Unknown")
    
    echo -e "${GREEN}[✓] Network info gathered${NC}"
}

# Crear archivo de información de acceso
create_access_info() {
    echo -e "${BLUE}[*] Creating access information file...${NC}"
    
    LOCAL_IP=$(hostname -I | awk '{print $1}')
    
    cat > "$SWARMIA_DIR/ACCESS_INFO.txt" << EOF
===========================================
         SwarmIA Access Information
===========================================

INSTALLATION COMPLETE!

Access URLs:
- Local:      http://$LOCAL_IP:$PORT
- Dashboard:  http://$LOCAL_IP:$PORT/dashboard
- Health:     http://$LOCAL_IP:$PORT/health

Default Credentials:
- Username: admin
- Password: admin
⚠️  CHANGE PASSWORD ON FIRST LOGIN!

Installation Directories:
- Main:      $SWARMIA_DIR
- Config:    $CONFIG_DIR
- Logs:      $LOGS_DIR
- Data:      $DATA_DIR

Management Commands:
- Start:     sudo systemctl start swarmia
- Stop:      sudo systemctl stop swarmia
- Status:    sudo systemctl status swarmia
- Restart:   sudo systemctl restart swarmia
- Logs:      sudo journalctl -u swarmia -f

Troubleshooting:
1. Check service status: sudo systemctl status swarmia
2. View logs: sudo journalctl -u swarmia -f
3. Verify port: ss -tlnp | grep :$PORT
4. Test health: curl http://$LOCAL_IP:$PORT/health

Next Steps:
1. Open dashboard in browser
2. Login with admin/admin
3. Change password immediately
4. Configure AI provider (DeepSeek or Llama)
5. Setup WhatsApp/Telegram if desired

Generated: $(date)
EOF
    
    echo -e "${GREEN}[✓] Access information saved to: $SWARMIA_DIR/ACCESS_INFO.txt${NC}"
}

# Iniciar servicio SwarmIA
start_swarmia() {
    echo -e "${BLUE}[*] Starting SwarmIA service...${NC}"
    
    systemctl start swarmia
    
    # Esperar y verificar
    echo -e "${YELLOW}[*] Waiting for service to start...${NC}"
    sleep 5
    
    if systemctl is-active --quiet swarmia; then
        echo -e "${GREEN}[✓] SwarmIA service started successfully${NC}"
        
        # Verificar salud
        echo -e "${YELLOW}[*] Verifying health check...${NC}"
        sleep 2
        
        if curl -s http://localhost:$PORT/health > /dev/null 2>&1; then
            echo -e "${GREEN}[✓] Health check passed${NC}"
        else
            echo -e "${YELLOW}[!] Health check failed (service may still be starting)${NC}"
        fi
    else
        echo -e "${RED}[!] Failed to start SwarmIA service${NC}"
        echo -e "${YELLOW}Check logs: journalctl -u swarmia -f${NC}"
    fi
}

# Función principal
main() {
    print_banner
    check_root
    detect_system
    
    echo -e "${YELLOW}This will install SwarmIA to $SWARMIA_DIR${NC}"
    echo -e "${YELLOW}Repository: $REPO_URL${NC}"
    echo ""
    read -p "Continue? (Y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]] && [[ ! -z "$REPLY" ]]; then
        echo -e "${YELLOW}Installation cancelled.${NC}"
        exit 0
    fi
    
    # Pasos de instalación
    install_dependencies
    create_directories
    download_swarmia
    setup_python_env
    create_config
    setup_systemd_service
    setup_firewall
    get_network_info
    create_access_info
    start_swarmia
    
    # Mostrar resumen
    LOCAL_IP=$(hostname -I | awk '{print $1}')
    
    echo -e "\n${GREEN}══════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}            🎊 SwarmIA Installation Complete!                  ${NC}"
    echo -e "${GREEN}══════════════════════════════════════════════════════════════${NC}"
    echo -e ""
    echo -e "${BLUE}📋 Quick Start:${NC}"
    echo -e "  1. Open your browser to: http://$LOCAL_IP:$PORT"
    echo -e "  2. Login with admin/admin"
    echo -e "  3. Change password immediately"
    echo -e "  4. Configure your AI provider"
    echo -e ""
    echo -e "${BLUE}📊 Service Status:${NC}"
    echo -e "  Status:  sudo systemctl status swarmia"
    echo -e "  Logs:    sudo journalctl -u swarmia -f"
    echo -e "  Restart: sudo systemctl restart swarmia"
    echo -e ""
    echo -e "${BLUE}🔗 Access Information:${NC}"
    echo -e "  Full details: $SWARMIA_DIR/ACCESS_INFO.txt"
    echo -e ""
    echo -e "${GREEN}══════════════════════════════════════════════════════════════${NC}"
}

# Ejecutar función principal
main "$@"