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
        
        if [[ $confirm != "y" && $confirm != "Y" ]]; then
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
                echo -e "${YELL
