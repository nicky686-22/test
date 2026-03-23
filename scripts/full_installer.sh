#!/bin/bash
# SwarmIA Full Interactive Installer
# Version 3.1 - Supports both interactive and non-interactive modes

set -e

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuración
SWARMIA_DIR="/opt/swarmia"
CONFIG_DIR="/etc/swarmia"
LOGS_DIR="/var/log/swarmia"
DATA_DIR="/var/lib/swarmia"
PORT="3000"
REPO_URL="https://github.com/nicky686-22/test.git"

# Variables de configuración
AI_BACKEND="deepseek"
MESSAGING_PLATFORM="none"
DEEPSEEK_API_KEY=""
LLAMA_MODEL_PATH=""
WHATSAPP_NUMBER=""
TELEGRAM_BOT_TOKEN=""

# Modo
INTERACTIVE=true
ACTION="menu"

# Parsear argumentos
while [[ $# -gt 0 ]]; do
    case $1 in
        --install)
            ACTION="install"
            INTERACTIVE=false
            shift
            ;;
        --update)
            ACTION="update"
            INTERACTIVE=false
            shift
            ;;
        --reinstall)
            ACTION="reinstall"
            INTERACTIVE=false
            shift
            ;;
        --uninstall)
            ACTION="uninstall"
            INTERACTIVE=false
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Si no hay terminal, forzar no interactivo
if [ ! -t 0 ]; then
    INTERACTIVE=false
    if [ "$ACTION" = "menu" ]; then
        ACTION="update"  # Default para curl | bash
    fi
fi

# Limpiar pantalla
clear_screen() {
    if [ "$INTERACTIVE" = true ]; then
        printf "\033c"
    fi
}

# Banner principal
print_main_banner() {
    clear_screen
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                    SWARMIA INSTALLER 3.1                     ║"
    echo "║           Interactive & Automatic Installation               ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo ""
}

# Banner de sección
print_section_banner() {
    local title="$1"
    echo -e "${PURPLE}"
    echo "══════════════════════════════════════════════════════════════"
    echo "  $title"
    echo "══════════════════════════════════════════════════════════════"
    echo -e "${NC}"
    echo ""
}

# Verificar root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        echo -e "${RED}[!] This installer must be run as root${NC}"
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
    
    echo -e "${GREEN}[✓] System: $OS $VER${NC}"
    echo ""
}

# Menú principal
main_menu() {
    while true; do
        print_main_banner
        detect_system
        
        echo -e "${YELLOW}SwarmIA will be installed to: $SWARMIA_DIR${NC}"
        echo -e "${YELLOW}Repository: $REPO_URL${NC}"
        echo ""
        
        if [ -d "$SWARMIA_DIR" ]; then
            echo -e "${YELLOW}[!] SwarmIA is already installed at $SWARMIA_DIR${NC}"
            echo ""
        fi
        
        echo "Please select an option:"
        echo ""
        echo -e "  ${GREEN}1)${NC} Install SwarmIA (Fresh installation)"
        echo -e "  ${GREEN}2)${NC} Update existing installation"
        echo -e "  ${GREEN}3)${NC} Clean reinstall (keep configurations)"
        echo -e "  ${GREEN}4)${NC} Complete uninstall"
        echo -e "  ${GREEN}5)${NC} Exit"
        echo ""
        
        read -p "Enter your choice [1-5]: " choice
        
        case $choice in
            1)
                ACTION="install"
                break
                ;;
            2)
                ACTION="update"
                break
                ;;
            3)
                ACTION="reinstall"
                break
                ;;
            4)
                ACTION="uninstall"
                break
                ;;
            5)
                echo -e "${YELLOW}[*] Exiting...${NC}"
                exit 0
                ;;
            *)
                echo -e "${RED}[!] Invalid option. Please try again.${NC}"
                sleep 2
                ;;
        esac
    done
}

# Configurar AI Backend (solo en modo interactivo)
configure_ai_backend() {
    if [ "$INTERACTIVE" = false ]; then
        # Modo automático: usar defaults
        AI_BACKEND="deepseek"
        return
    fi
    
    print_section_banner "AI BACKEND CONFIGURATION"
    
    echo "Select your AI backend:"
    echo ""
    echo -e "  ${GREEN}1)${NC} DeepSeek API (Online - requires API key)"
    echo -e "  ${GREEN}2)${NC} Llama.cpp (Local - requires model file)"
    echo -e "  ${GREEN}3)${NC} Both (use DeepSeek as primary, Llama as fallback)"
    echo ""
    
    while true; do
        read -p "Select backend [1-3]: " ai_choice
        
        case $ai_choice in
            1)
                AI_BACKEND="deepseek"
                configure_deepseek
                break
                ;;
            2)
                AI_BACKEND="llama"
                configure_llama
                break
                ;;
            3)
                AI_BACKEND="both"
                configure_deepseek
                configure_llama
                break
                ;;
            *)
                echo -e "${RED}[!] Invalid option. Please try again.${NC}"
                ;;
        esac
    done
}

# Configurar DeepSeek
configure_deepseek() {
    if [ "$INTERACTIVE" = false ]; then
        return
    fi
    
    echo ""
    echo -e "${YELLOW}DeepSeek API Configuration${NC}"
    echo ""
    echo "You need a DeepSeek API key from: https://platform.deepseek.com/api-keys"
    echo ""
    
    read -p "Enter your DeepSeek API key (or press Enter to skip): " DEEPSEEK_API_KEY
    
    if [ -z "$DEEPSEEK_API_KEY" ]; then
        echo -e "${YELLOW}[!] DeepSeek API key not provided. You can add it later in config.${NC}"
    else
        echo -e "${GREEN}[✓] DeepSeek API key saved${NC}"
    fi
}

# Configurar Llama
configure_llama() {
    if [ "$INTERACTIVE" = false ]; then
        return
    fi
    
    echo ""
    echo -e "${YELLOW}Llama.cpp Configuration${NC}"
    echo ""
    echo "Llama.cpp runs locally. You need to download a model file."
    echo ""
    
    echo "Available model options:"
    echo -e "  ${GREEN}1)${NC} Download 7B model (recommended for most systems)"
    echo -e "  ${GREEN}2)${NC} Use existing model file"
    echo -e "  ${GREEN}3)${NC} Skip for now (configure later)"
    echo ""
    
    read -p "Select option [1-3]: " llama_choice
    
    case $llama_choice in
        1)
            LLAMA_MODEL_PATH="/opt/swarmia/models/llama-7b.gguf"
            echo -e "${GREEN}[✓] Will download 7B model during installation${NC}"
            ;;
        2)
            read -p "Enter path to existing model file: " LLAMA_MODEL_PATH
            if [ -f "$LLAMA_MODEL_PATH" ]; then
                echo -e "${GREEN}[✓] Model file found: $LLAMA_MODEL_PATH${NC}"
            else
                echo -e "${RED}[!] File not found. Will skip for now.${NC}"
                LLAMA_MODEL_PATH=""
            fi
            ;;
        3)
            LLAMA_MODEL_PATH=""
            echo -e "${YELLOW}[!] Llama configuration skipped${NC}"
            ;;
    esac
}

# Configurar mensajería (solo en modo interactivo)
configure_messaging() {
    if [ "$INTERACTIVE" = false ]; then
        # Modo automático: no configurar mensajería
        MESSAGING_PLATFORM="none"
        return
    fi
    
    print_section_banner "MESSAGING PLATFORM CONFIGURATION"
    
    echo "Select your messaging platform:"
    echo ""
    echo -e "  ${GREEN}1)${NC} WhatsApp (requires phone number)"
    echo -e "  ${GREEN}2)${NC} Telegram (requires bot token)"
    echo -e "  ${GREEN}3)${NC} Both platforms"
    echo -e "  ${GREEN}4)${NC} Skip for now (configure later)"
    echo ""
    
    while true; do
        read -p "Select platform [1-4]: " msg_choice
        
        case $msg_choice in
            1)
                MESSAGING_PLATFORM="whatsapp"
                configure_whatsapp
                break
                ;;
            2)
                MESSAGING_PLATFORM="telegram"
                configure_telegram
                break
                ;;
            3)
                MESSAGING_PLATFORM="both"
                configure_whatsapp
                configure_telegram
                break
                ;;
            4)
                MESSAGING_PLATFORM="none"
                echo -e "${YELLOW}[!] Messaging configuration skipped${NC}"
                break
                ;;
            *)
                echo -e "${RED}[!] Invalid option. Please try again.${NC}"
                ;;
        esac
    done
}

# Configurar WhatsApp
configure_whatsapp() {
    if [ "$INTERACTIVE" = false ]; then
        return
    fi
    
    echo ""
    echo -e "${YELLOW}WhatsApp Configuration${NC}"
    echo ""
    echo "You need a phone number for WhatsApp Web integration."
    echo "Format: +5491122334455 (with country code)"
    echo ""
    
    read -p "Enter your WhatsApp phone number (or press Enter to skip): " WHATSAPP_NUMBER
    
    if [ -z "$WHATSAPP_NUMBER" ]; then
        echo -e "${YELLOW}[!] WhatsApp number not provided. You can add it later.${NC}"
    else
        echo -e "${GREEN}[✓] WhatsApp number saved${NC}"
    fi
}

# Configurar Telegram
configure_telegram() {
    if [ "$INTERACTIVE" = false ]; then
        return
    fi
    
    echo ""
    echo -e "${YELLOW}Telegram Configuration${NC}"
    echo ""
    echo "You need a bot token from @BotFather"
    echo ""
    
    read -p "Enter your Telegram bot token (or press Enter to skip): " TELEGRAM_BOT_TOKEN
    
    if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
        echo -e "${YELLOW}[!] Telegram bot token not provided. You can add it later.${NC}"
    else
        echo -e "${GREEN}[✓] Telegram bot token saved${NC}"
    fi
}

# Resumen de configuración
show_config_summary() {
    print_section_banner "CONFIGURATION SUMMARY"
    
    echo -e "${CYAN}Installation Details:${NC}"
    echo -e "  Directory:    $SWARMIA_DIR"
    echo -e "  Repository:   $REPO_URL"
    echo -e "  Port:         $PORT"
    echo ""
    
    echo -e "${CYAN}AI Backend:${NC}"
    case $AI_BACKEND in
        "deepseek")
            echo -e "  ✅ DeepSeek API"
            if [ -n "$DEEPSEEK_API_KEY" ]; then
                echo -e "  🔑 API Key:    ${GREEN}Configured${NC}"
            else
                echo -e "  🔑 API Key:    ${YELLOW}Not configured${NC}"
            fi
            ;;
        "llama")
            echo -e "  ✅ Llama.cpp (Local)"
            if [ -n "$LLAMA_MODEL_PATH" ]; then
                echo -e "  📁 Model:      $LLAMA_MODEL_PATH"
            else
                echo -e "  📁 Model:      ${YELLOW}Not configured${NC}"
            fi
            ;;
        "both")
            echo -e "  ✅ Both (DeepSeek + Llama)"
            if [ -n "$DEEPSEEK_API_KEY" ]; then
                echo -e "  🔑 DeepSeek:   ${GREEN}Configured${NC}"
            else
                echo -e "  🔑 DeepSeek:   ${YELLOW}Not configured${NC}"
            fi
            if [ -n "$LLAMA_MODEL_PATH" ]; then
                echo -e "  📁 Llama:      Model configured"
            else
                echo -e "  📁 Llama:      ${YELLOW}Not configured${NC}"
            fi
            ;;
        *)
            echo -e "  ❌ ${RED}Not configured${NC}"
            ;;
    esac
    echo ""
    
    echo -e "${CYAN}Messaging Platform:${NC}"
    case $MESSAGING_PLATFORM in
        "whatsapp")
            echo -e "  ✅ WhatsApp"
            if [ -n "$WHATSAPP_NUMBER" ]; then
                echo -e "  📱 Number:     $WHATSAPP_NUMBER"
            else
                echo -e "  📱 Number:     ${YELLOW}Not configured${NC}"
            fi
            ;;
        "telegram")
            echo -e "  ✅ Telegram"
            if [ -n "$TELEGRAM_BOT_TOKEN" ]; then
                echo -e "  🤖 Bot Token:  ${GREEN}Configured${NC}"
            else
                echo -e "  🤖 Bot Token:  ${YELLOW}Not configured${NC}"
            fi
            ;;
        "both")
            echo -e "  ✅ Both (WhatsApp + Telegram)"
            if [ -n "$WHATSAPP_NUMBER" ]; then
                echo -e "  📱 WhatsApp:   ${GREEN}Configured${NC}"
            else
                echo -e "  📱 WhatsApp:   ${YELLOW}Not configured${NC}"
            fi
            if [ -n "$TELEGRAM_BOT_TOKEN" ]; then
                echo -e "  🤖 Telegram:   ${GREEN}Configured${NC}"
            else
                echo -e "  🤖 Telegram:   ${YELLOW}Not configured${NC}"
            fi
            ;;
        "none")
            echo -e "  ❌ ${YELLOW}Not configured${NC}"
            ;;
        *)
            echo -e "  ❌ ${RED}Not configured${NC}"
            ;;
    esac
    echo ""
    
    echo -e "${CYAN}Actions to be performed:${NC}"
    echo -e "  1. Install dependencies"
    echo -e "  2. Create directories"
    echo -e "  3. Download SwarmIA from GitHub"
    echo -e "  4. Setup Python environment"
    echo -e "  5. Create configuration file"
    echo -e "  6. Create systemd service"
    echo -e "  7. Start SwarmIA service"
    echo ""
    
    if [ "$INTERACTIVE" = true ]; then
        read -p "Proceed with installation? (y/N): " confirm
        
        if [[ $confirm != "y" if [[ $confirm != "y" && $confirm != "Y" ]; thenif [[ $confirm != "y" && $confirm != "Y" ]; then $confirm != "Y" ]]; then
            echo -e "${YELLOW}[*] Installation cancelled${NC}"
            exit 0
        fi
    else
        echo -e "${BLUE}[*] Proceeding with automatic installation...${NC}"
        sleep 2
    fi
}

# Ejecutar acción basada en ACTION
execute_action() {
    case $ACTION in
        "install")
            echo -e "${GREEN}[*] Starting SwarmIA installation...${NC}"
            echo ""
            
            if [ "$INTERACTIVE" = true ]; then
                configure_ai_backend
                configure_messaging
                show_config_summary
            fi
            
            install_dependencies
            create_directories
            download_swarmia
            setup_python_environment
            create_config_file
            create_systemd_service
            start_service
            show_completion_message
            ;;
            
        "update")
            echo -e "${GREEN}[*] Updating SwarmIA...${NC}"
            echo ""
            
            if [ ! -d "$SWARMIA_DIR" ]; then
                echo -e "${RED}[!] SwarmIA is not installed${NC}"
                echo -e "${YELLOW}Please run the installer instead.${NC}"
                exit 1
            fi
            
            cd "$SWARMIA_DIR"
            
            if [ -d ".git" ]; then
                echo -e "${BLUE}[*] Updating from Git repository...${NC}"
                git pull origin main
                echo -e "${GREEN}[✓] Updated from Git${NC}"
            else
                echo -e "${YELLOW}[*] No Git repository found, downloading fresh...${NC}"
                rm -rf "$SWARMIA_DIR"/*
                git clone "$REPO_URL" "$SWARMIA_DIR"
                echo -e "${GREEN}[✓] Downloaded fresh copy${NC}"
            fi
            
            restart_service
            show_completion_message
            ;;
            
        "reinstall")
            echo -e "${GREEN}[*] Reinstalling SwarmIA...${NC}"
            echo ""
            
            if [ ! -d "$SWARMIA_DIR" ]; then
                echo -e "${RED}[!] SwarmIA is not installed${NC}"
                echo -e "${YELLOW}Please run the installer instead.${NC}"
                exit 1
            fi
            
            echo -e "${YELLOW}[!] Backing up configuration...${NC}"
            
            # Backup configs
            if [ -f "$CONFIG_DIR/config.yaml" ]; then
                cp "$CONFIG_DIR/config.yaml" "/tmp/swarmia_config_backup.yaml"
                echo -e "${GREEN}[✓] Configuration backed up${NC}"
            fi
            
            echo -e "${BLUE}[*] Removing existing installation...${NC}"
            systemctl stop swarmia 2>/dev/null || true
            rm -rf "$SWARMIA_DIR"
            
            # Install fresh
            install_dependencies
            create_directories
            download_swarmia
            setup_python_environment
            
            # Restore config
            if [ -f "/tmp/swarmia_config_backup.yaml" ]; then
                cp "/tmp/swarmia_config_backup.yaml" "$CONFIG_DIR/config.yaml"
                echo -e "${GREEN}[✓] Configuration restored${NC}"
            fi
            
            create_systemd_service
            start_service
            show_completion_message
            ;;
            
        "uninstall")
            echo -e "${RED}[!] WARNING: This will completely remove SwarmIA${NC}"
            echo ""
            
            if [ ! -d "$SWARMIA_DIR" ]; then
                echo -e "${YELLOW}[!] SwarmIA is not installed${NC}"
                exit 0
            fi
            
            if [ "$INTERACTIVE" = true ]; then
                read -p "Are you sure you want to uninstall SwarmIA? (y/N): " confirm
                
                if [[ $confirm != "y" && $confirm != "Y" ]]; then
                    echo -e "${YELLOW}[*] Uninstall cancelled${NC}"
                    exit 0
                fi
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
            ;;
            
        "menu")
            main_menu
            execute_action
            ;;
    esac
}

# Instalar dependencias
install_dependencies() {
    print_section_banner "INSTALLING DEPENDENCIES"
    
    echo -e "${BLUE}[*] Updating package list...${NC}"
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
    echo -e "${BLUE}[*] Installing other dependencies...${NC}"
    apt-get install -y curl wget net-tools
    
    echo -e "${GREEN}[✓] Dependencies installed${NC}"
}

# Crear directorios
create_directories() {
    print_section_banner "CREATING DIRECTORIES"
    
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
    print_section_banner "DOWNLOADING SWARMIA"
    
    echo -e "${BLUE}[*] Downloading SwarmIA from GitHub...${NC}"
    
    cd "$SWARMIA_DIR"
    
    if git clone "$REPO_URL" . 2>/dev/null; then
        echo -e "${GREEN}[✓] Repository cloned successfully${NC}"
    else
        echo -e "${RED}[!] Git clone failed${NC}"
        exit 1
    fi
}

# Configurar entorno Python
setup_python_environment() {
    print_section_banner "SETTING UP PYTHON ENVIRONMENT"
    
    echo -e "${BLUE}[*] Installing Python dependencies...${NC}"
    
    cd "$SWARMIA_DIR"
    
    if [ -f "requirements.txt" ]; then
        pip3 install -r requirements.txt
        echo -e "${GREEN}[✓] Python dependencies installed${NC}"
    else
        echo -e "${YELLOW}[!] No requirements.txt found${NC}"
    fi
}

# Crear archivo de configuración
create_config_file() {
    print_section_banner "CREATING CONFIGURATION FILE"
    
    echo -e "${BLUE}[*] Creating configuration file...${NC}"
    
    cat > "$CONFIG_DIR/config.yaml" << CONFIG_EOF
# SwarmIA Configuration
# Generated by installer on $(date)

# Server settings
server:
  host: "0.0.0.0"
  port: $PORT
  debug: false

# AI Backend configuration
ai:
  backend: "$AI_BACKEND"
  
  deepseek:
    api_key: "$DEEPSEEK_API_KEY"
    model: "deepseek-chat"
    base_url: "https://api.deepseek.com"
  
  llama:
    model_path: "$LLAMA_MODEL_PATH"
    n_ctx: 2048
    n_gpu_layers: -1

# Messaging platforms
messaging:
  platform: "$MESSAGING_PLATFORM"
  
  whatsapp:
    phone_number: "$WHATSAPP_NUMBER"
    session_path: "$DATA_DIR/whatsapp_session"
  
  telegram:
    bot_token: "$TELEGRAM_BOT_TOKEN"
    admin_ids: []

# Database
database:
  path: "$DATA_DIR/swarmia.db"
  type: "sqlite"

# Logging
logging:
  level: "INFO"
  file: "$LOGS_DIR/swarmia.log"
  max_size_mb: 10
  backup_count: 5

# Security
security:
  api_key_enabled: false
  cors_origins: ["*"]
CONFIG_EOF
    
    echo -e "${GREEN}[✓] Configuration file created at $CONFIG_DIR/config.yaml${NC}"
}

# Crear servicio systemd
create_systemd_service() {
    print_section_banner "CREATING SYSTEMD SERVICE"
    
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
    echo -e "${GREEN}[✓] Systemd service created${NC}"
}

# Iniciar servicio
start_service() {
    print_section_banner "STARTING SWARMIA SERVICE"
    
    echo -e "${BLUE}[*] Enabling and starting SwarmIA service...${NC}"
    
    systemctl enable swarmia
    systemctl start swarmia
    
    sleep 3
    
    if systemctl is-active --quiet swarmia; then
        echo -e "${GREEN}[✓] SwarmIA service is running${NC}"
    else
        echo -e "${RED}[!] Failed to start service${NC}"
        echo -e "${YELLOW}Checking logs...${NC}"
        journalctl -u swarmia --no-pager -n 10
    fi
}

# Reiniciar servicio
restart_service() {
    echo -e "${BLUE}[*] Restarting SwarmIA service...${NC}"
    systemctl restart swarmia
    sleep 2
    
    if systemctl is-active --quiet swarmia; then
        echo -e "${GREEN}[✓] Service restarted successfully${NC}"
    else
        echo -e "${RED}[!] Failed to restart service${NC}"
    fi
}

# Mensaje de finalización
show_completion_message() {
    print_section_banner "INSTALLATION COMPLETE"
    
    local ip_address=$(hostname -I | awk '{print $1}')
    
    echo -e "${GREEN}✅ SwarmIA has been successfully installed!${NC}"
    echo ""
    echo -e "${CYAN}Access Information:${NC}"
    echo -e "  Dashboard:    http://$ip_address:$PORT"
    echo -e "  Health check: http://$ip_address:$PORT/health"
    echo ""
    echo -e "${CYAN}Service Management:${NC}"
    echo -e "  Check status: systemctl status swarmia"
    echo -e "  View logs:    journalctl -u swarmia -f"
    echo -e "  Stop service: systemctl stop swarmia"
    echo -e "  Start service: systemctl start swarmia"
    echo ""
    echo -e "${CYAN}Configuration Files:${NC}"
    echo -e "  Main config:  $CONFIG_DIR/config.yaml"
    echo -e "  Logs:         $LOGS_DIR/"
    echo -e "  Data:         $DATA_DIR/"
    echo ""
    echo -e "${CYAN}Next Steps:${NC}"
    echo -e "  1. Open the dashboard in your browser"
    echo -e "  2. Configure additional settings if needed"
    echo -e "  3. Check the logs for any issues"
    echo ""
    echo -e "${GREEN}══════════════════════════════════════════════════════════════${NC}"
    echo ""
}

# Función principal
main() {
    check_root
    
    if [ "$ACTION" = "menu" ] && [ "$INTERACTIVE" = true ]; then
        main_menu
    fi
    
    execute_action
}

# Ejecutar
main
