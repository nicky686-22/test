#!/bin/bash
# Script de instalación alternativo para SwarmIA
# Usa la API de GitHub directamente para evitar problemas de raw.githubusercontent.com

set -e

echo "🚀 Instalando SwarmIA (método alternativo)..."
echo "=============================================="

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Verificar que estamos en Linux
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    echo -e "${RED}❌ Este script solo funciona en Linux${NC}"
    exit 1
fi

# Verificar sudo
if [[ $EUID -ne 0 ]]; then
    echo -e "${YELLOW}⚠️  Necesitas permisos de superusuario${NC}"
    exec sudo bash "$0" "$@"
    exit $?
fi

# Directorio de instalación
INSTALL_DIR="/opt/swarmia"
CONFIG_DIR="/etc/swarmia"
LOG_DIR="/var/log/swarmia"

echo -e "${GREEN}📦 Preparando instalación...${NC}"

# Crear directorios
mkdir -p "$INSTALL_DIR"
mkdir -p "$CONFIG_DIR"
mkdir -p "$LOG_DIR"

# Descargar archivos usando la API de GitHub
echo -e "${GREEN}⬇️  Descargando SwarmIA desde GitHub...${NC}"

# Función para descargar archivos
download_file() {
    local file_path="$1"
    local local_path="$2"
    
    echo "  📥 Descargando: $file_path"
    
    # Usar API de GitHub
    curl -s -H "Accept: application/vnd.github.v3.raw" \
         "https://api.github.com/repos/nicky686-22/SwarmIA/contents/$file_path" \
         -o "$local_path"
    
    if [[ $? -eq 0 ]] && [[ -s "$local_path" ]]; then
        echo -e "    ${GREEN}✅ Descargado${NC}"
    else
        echo -e "    ${RED}❌ Error descargando $file_path${NC}"
        # Intentar método alternativo
        echo "    🔄 Intentando método alternativo..."
        curl -s "https://raw.githubusercontent.com/nicky686-22/SarmIA/main/$file_path" -o "$local_path" || true
    fi
}

# Descargar archivos principales
download_file "README.md" "$INSTALL_DIR/README.md"
download_file "requirements.txt" "$INSTALL_DIR/requirements.txt"
download_file "src/core/main.py" "$INSTALL_DIR/main.py"
download_file "src/core/config.py" "$INSTALL_DIR/config.py"
download_file "src/core/supervisor.py" "$INSTALL_DIR/supervisor.py"

# Crear estructura de directorios en /opt/swarmia
mkdir -p "$INSTALL_DIR/src"
mkdir -p "$INSTALL_DIR/scripts"
mkdir -p "$INSTALL_DIR/config"

# Descargar scripts
download_file "scripts/install.sh" "$INSTALL_DIR/scripts/install.sh"
download_file "scripts/verify_installation.py" "$INSTALL_DIR/scripts/verify_installation.py"

# Hacer ejecutable
chmod +x "$INSTALL_DIR/scripts/install.sh"
chmod +x "$INSTALL_DIR/scripts/verify_installation.py"

# Instalar dependencias de Python
echo -e "${GREEN}🐍 Instalando dependencias de Python...${NC}"
if command -v python3 &> /dev/null; then
    python3 -m pip install --upgrade pip
    python3 -m pip install -r "$INSTALL_DIR/requirements.txt"
else
    echo -e "${RED}❌ Python3 no encontrado${NC}"
    apt-get update && apt-get install -y python3 python3-pip
    python3 -m pip install -r "$INSTALL_DIR/requirements.txt"
fi

# Crear servicio systemd
echo -e "${GREEN}⚙️  Configurando servicio systemd...${NC}"
cat > /etc/systemd/system/swarmia.service << EOF
[Unit]
Description=SwarmIA - Sistema de IA Distribuida
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$INSTALL_DIR
ExecStart=/usr/bin/python3 $INSTALL_DIR/main.py
Restart=always
RestartSec=10
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=swarmia

[Install]
WantedBy=multi-user.target
EOF

# Recargar systemd
systemctl daemon-reload
systemctl enable swarmia.service

# Crear archivo de configuración por defecto
cat > "$CONFIG_DIR/config.yaml" << EOF
# Configuración de SwarmIA
version: "1.0.0"

# Servidor web
web:
  host: "0.0.0.0"
  port: 3000
  debug: false

# Agentes
agents:
  chat:
    enabled: true
    model: "deepseek-chat"
  aggressive:
    enabled: true
    ssh_enabled: true

# Logs
logging:
  level: "INFO"
  file: "$LOG_DIR/swarmia.log"
  max_size_mb: 100

# Actualizaciones
updates:
  enabled: true
  check_interval_hours: 6
  github_repo: "nicky686-22/SwarmIA"
EOF

# Configurar permisos
chmod 644 "$CONFIG_DIR/config.yaml"
chown -R root:root "$INSTALL_DIR"
chown -R root:root "$CONFIG_DIR"
chown -R root:root "$LOG_DIR"

# Iniciar servicio
echo -e "${GREEN}🚀 Iniciando servicio SwarmIA...${NC}"
systemctl start swarmia.service

# Esperar a que el servicio se inicie
sleep 3

# Verificar estado
if systemctl is-active --quiet swarmia.service; then
    echo -e "${GREEN}✅ Servicio SwarmIA iniciado correctamente${NC}"
else
    echo -e "${RED}❌ Error iniciando el servicio${NC}"
    journalctl -u swarmia.service --no-pager -n 20
    exit 1
fi

# Crear archivo de información de acceso
cat > "$INSTALL_DIR/ACCESS_INFO.txt" << EOF
🎉 ¡SwarmIA instalado correctamente!

📊 INFORMACIÓN DE ACCESO:
========================

🌐 DASHBOARD WEB:
   URL: http://$(hostname -I | awk '{print $1}'):3000
   Alternativa: http://localhost:3000
   Health check: http://$(hostname -I | awk '{print $1}'):3000/health

🔧 COMANDOS DE GESTIÓN:
   Ver estado: sudo systemctl status swarmia
   Ver logs: sudo journalctl -u swarmia -f
   Reiniciar: sudo systemctl restart swarmia
   Detener: sudo systemctl stop swarmia

📁 DIRECTORIOS:
   Instalación: $INSTALL_DIR
   Configuración: $CONFIG_DIR
   Logs: $LOG_DIR

🔐 CREDENCIALES POR DEFECTO:
   Usuario: admin
   Contraseña: admin
   (Cambiar en el dashboard después del primer login)

🔄 ACTUALIZACIONES:
   El sistema verifica actualizaciones automáticamente cada 6 horas
   Repositorio: https://github.com/nicky686-22/SwarmIA

📞 SOPORTE:
   Revisar logs: $LOG_DIR/swarmia.log
   Verificar salud: curl http://localhost:3000/health

⏰ Instalación completada: $(date)
EOF

echo -e "${GREEN}==============================================${NC}"
echo -e "${GREEN}🎉 ¡INSTALACIÓN COMPLETADA!${NC}"
echo -e "${GREEN}==============================================${NC}"
echo ""
echo -e "${YELLOW}📋 INFORMACIÓN DE ACCESO:${NC}"
cat "$INSTALL_DIR/ACCESS_INFO.txt"
echo ""
echo -e "${GREEN}🚀 SwarmIA está listo para usar!${NC}"
echo -e "${GREEN}🌐 Accede al dashboard: http://$(hostname -I | awk '{print $1}'):3000${NC}"