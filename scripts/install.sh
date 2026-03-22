#!/bin/bash
# SwarmIA Installation Script - Versión Mejorada
# Soluciona problemas de instalación existente

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

# Banner simplificado (sin clear)
print_banner() {
    echo -e "${GREEN}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                    SwarmIA Installation                      ║"
    echo "║                    Version 2.1 - Fixed                       ║"
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

# Verificar instalación existente
check_existing_installation() {
    if [ -d "$SWARMIA_DIR" ]; then
        echo -e "${YELLOW}[!] SwarmIA is already installed at $SWARMIA_DIR${NC}"
        echo ""
        echo "What would you like to do?"
        echo "  1) Update existing installation"
        echo "  2) Clean reinstall (keep configs)"
        echo "  3) Complete uninstall"
        echo "  4) Exit"
        echo ""
        
        read -p "Select option [1-4]: " choice
        
        case $choice in
            1)
                echo -e "${BLUE}[*] Updating existing installation...${NC}"
                update_installation
                ;;
            2)
                echo -e "${BLUE}[*] Performing clean reinstall...${NC}"
                clean_reinstall
                ;;
            3)
                echo -e "${BLUE}[*] Uninstalling SwarmIA...${NC}"
                uninstall_swarmia
                ;;
            4)
                echo -e "${YELLOW}[*] Exiting...${NC}"
                exit 0
                ;;
            *)
                echo -e "${RED}[!] Invalid option. Exiting...${NC}"
                exit 1
                ;;
        esac
    fi
}

# Actualizar instalación existente
update_installation() {
    cd "$SWARMIA_DIR"
    
    if [ -d ".git" ]; then
        echo -e "${BLUE}[*] Updating from Git repository...${NC}"
        git pull origin main
    else
        echo -e "${YELLOW}[*] No Git repository found, downloading fresh...${NC}"
        rm -rf "$SWARMIA_DIR"/*
        git clone "$REPO_URL" "$SWARMIA_DIR"
    fi
    
    echo -e "${GREEN}[✓] Installation updated${NC}"
    show_access_info
}

# Reinstalación limpia
clean_reinstall() {
    echo -e "${YELLOW}[*] Backing up configuration...${NC}"
    
    # Backup configs if they exist
    if [ -f "$CONFIG_DIR/config.yaml" ]; then
        cp "$CONFIG_DIR/config.yaml" "/tmp/swarmia_config_backup.yaml"
        echo -e "${GREEN}[✓] Configuration backed up${NC}"
    fi
    
    echo -e "${BLUE}[*] Removing existing installation...${NC}"
    systemctl stop swarmia 2>/dev/null || true
    rm -rf "$SWARMIA_DIR"
    
    # Install fresh
    install_fresh
    
    # Restore config if it exists
    if [ -f "/tmp/swarmia_config_backup.yaml" ]; then
        cp "/tmp/swarmia_config_backup.yaml" "$CONFIG_DIR/config.yaml"
        echo -e "${GREEN}[✓] Configuration restored${NC}"
    fi
}

# Desinstalar completamente
uninstall_swarmia() {
    echo -e "${RED}[!] WARNING: This will completely remove SwarmIA${NC}"
    read -p "Are you sure? (y/N): " confirm
    
    if [[ $confirm != "y" && $confirm != "Y" ]]; then
        echo -e "${YELLOW}[*] Uninstall cancelled${NC}"
        exit 0
    fi
    
    echo -e "${BLUE}[*] Stopping service...${NC}"
    systemctl stop swarmia 2>/dev/null || true
    systemctl disable swarmia 2>/dev/null || true
    
    echo -e "${BLUE}[*] Removing files...${NC}"
    rm -rf "$SWARMIA_DIR"
    rm -rf "$CONFIG_DIR"
    rm -rf "$LOGS_DIR"
    rm -rf "$DATA_DIR"
    
    echo -e "${BLUE}[*] Removing systemd service...${NC}"
    rm -f /etc/systemd/system/swarmia.service
    
    echo -e "${GREEN}[✓] SwarmIA completely uninstalled${NC}"
}

# Instalación fresca
install_fresh() {
    install_dependencies
    create_directories
    download_swarmia
    setup_python_environment
    create_systemd_service
    start_service
    show_access_info
}

# Instalar dependencias
install_dependencies() {
    echo -e "${BLUE}[*] Installing dependencies...${NC}"
    
    apt-get update
    
    # Python y pip
    if ! command -v python3 &> /dev/null; then
        echo -e "${YELLOW}[*] Installing Python3...${NC}"
        apt-get install -y python3 python3-pip python3-venv
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

# Descargar SwarmIA
download_swarmia() {
    echo -e "${BLUE}[*] Downloading SwarmIA...${NC}"
    
    cd "$SWARMIA_DIR"
    
    if git clone "$REPO_URL" . 2>/dev/null; then
        echo -e "${GREEN}[✓] Repository cloned successfully${NC}"
    else
        echo -e "${RED}[!] Git clone failed, trying wget...${NC}"
        rm -rf "$SWARMIA_DIR"/*
        wget -qO- "$REPO_URL/archive/main.tar.gz" | tar -xz --strip-components=1
        echo -e "${GREEN}[✓] Downloaded via wget${NC}"
    fi
}

# Configurar entorno Python
setup_python_environment() {
    echo -e "${BLUE}[*] Setting up Python environment...${NC}"
    
    cd "$SWARMIA_DIR"
    
    # Instalar requirements
    if [ -f "requirements.txt" ]; then
        pip3 install -r requirements.txt
        echo -e "${GREEN}[✓] Python dependencies installed${NC}"
    else
        echo -e "${YELLOW}[!] No requirements.txt found${NC}"
    fi
}

# Crear servicio systemd
create_systemd_service() {
    echo -e "${BLUE}[*] Creating systemd service...${NC}"
    
    cat > /etc/systemd/system/swarmia.service << SERVICE_EOF
[Unit]
Description=SwarmIA AI System
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$SWARMIA_DIR
Environment="PYTHONPATH=$SWARMIA_DIR"
ExecStart=/usr/bin/python3 $SWARMIA_DIR/src/core/main.py
Restart=on-failure
RestartSec=5
StandardOutput=append:$LOGS_DIR/swarmia.log
StandardError=append:$LOGS_DIR/swarmia-error.log

[Install]
WantedBy=multi-user.target
SERVICE_EOF
    
    systemctl daemon-reload
    echo -e "${GREEN}[✓] Systemd service created${NC}"
}

# Iniciar servicio
start_service() {
    echo -e "${BLUE}[*] Starting SwarmIA service...${NC}"
    
    systemctl enable swarmia
    systemctl start swarmia
    
    sleep 2
    
    if systemctl is-active --quiet swarmia; then
        echo -e "${GREEN}[✓] SwarmIA service is running${NC}"
    else
        echo -e "${RED}[!] Failed to start service${NC}"
        journalctl -u swarmia --no-pager -n 10
    fi
}

# Mostrar información de acceso
show_access_info() {
    echo ""
    echo -e "${GREEN}══════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}                    INSTALLATION COMPLETE                     ${NC}"
    echo -e "${GREEN}══════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "  Dashboard:    http://$(hostname -I | awk '{print $1}'):$PORT"
    echo -e "  Health check: http://$(hostname -I | awk '{print $1}'):$PORT/health"
    echo -e "  Service:      systemctl status swarmia"
    echo -e "  Logs:         journalctl -u swarmia -f"
    echo ""
    echo -e "${GREEN}══════════════════════════════════════════════════════════════${NC}"
}

# Función principal
main() {
    print_banner
    check_root
    detect_system
    
    echo -e "${YELLOW}This will install SwarmIA to $SWARMIA_DIR${NC}"
    echo -e "${YELLOW}Repository: $REPO_URL${NC}"
    echo ""
    
    check_existing_installation
    
    # Si no hay instalación existente, instalar fresco
    install_fresh
}

# Ejecutar
main
