#!/bin/bash
# Script de instalación SIMPLE para SwarmIA
# Soluciona el problema de raw.githubusercontent.com 404

set -e

echo "🚀 Instalador SwarmIA - Método Simple"
echo "====================================="

# Verificar sudo
if [[ $EUID -ne 0 ]]; then
    echo "⚠️  Necesitas permisos de superusuario"
    exec sudo bash "$0" "$@"
    exit $?
fi

# Directorios
INSTALL_DIR="/opt/swarmia"

echo "📦 Creando estructura de directorios..."
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

echo "⬇️  Descargando SwarmIA desde GitHub (método directo)..."

# Método 1: Usar git clone (si git está disponible)
if command -v git &> /dev/null; then
    echo "  🔄 Usando git clone..."
    git clone https://github.com/nicky686-22/SwarmIA.git . || true
fi

# Si git falló, usar curl directo para archivos clave
if [ ! -f "README.md" ]; then
    echo "  🔄 Descargando archivos individuales..."
    
    # Lista de archivos esenciales
    FILES=(
        "README.md"
        "requirements.txt"
        "src/core/main.py"
        "src/core/config.py"
        "src/core/supervisor.py"
    )
    
    for file in "${FILES[@]}"; do
        echo "    📥 $file"
        curl -s -L "https://raw.githubusercontent.com/nicky686-22/SwarmIA/main/$file" \
             -o "$file" 2>/dev/null || true
    done
fi

# Verificar que tenemos algo instalado
if [ -f "requirements.txt" ]; then
    echo "✅ Archivos descargados correctamente"
else
    echo "❌ No se pudieron descargar los archivos"
    echo "💡 Solución alternativa: Instalar manualmente"
    echo "   git clone https://github.com/nicky686-22/SwarmIA.git /opt/swarmia"
    exit 1
fi

echo "🐍 Instalando dependencias de Python..."
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt

echo "⚙️  Configurando servicio..."
# Crear servicio systemd simple
cat > /etc/systemd/system/swarmia.service << 'EOF'
[Unit]
Description=SwarmIA AI System
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/swarmia
ExecStart=/usr/bin/python3 /opt/swarmia/src/core/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable swarmia
systemctl start swarmia

echo "⏳ Esperando inicio del servicio..."
sleep 5

if systemctl is-active --quiet swarmia; then
    echo "✅ Servicio iniciado correctamente"
    echo ""
    echo "🎉 ¡INSTALACIÓN COMPLETADA!"
    echo "=========================="
    echo ""
    echo "🌐 Dashboard: http://$(hostname -I | awk '{print $1}'):3000"
    echo "🔧 Ver estado: sudo systemctl status swarmia"
    echo "📋 Ver logs: sudo journalctl -u swarmia -f"
else
    echo "⚠️  El servicio no se inició automáticamente"
    echo "💡 Intenta manualmente: sudo systemctl start swarmia"
fi

# Crear archivo de ayuda
cat > "$INSTALL_DIR/INSTALACION_COMPLETADA.txt" << EOF
SwarmIA instalado: $(date)

Para acceder:
1. Dashboard: http://$(hostname -I | awk '{print $1}'):3000
2. Health check: http://$(hostname -I | awk '{print $1}'):3000/health

Comandos útiles:
- sudo systemctl status swarmia
- sudo journalctl -u swarmia -f
- sudo systemctl restart swarmia

Credenciales por defecto:
- Usuario: admin
- Contraseña: admin
EOF

echo ""
echo "📄 Más información en: $INSTALL_DIR/INSTALACION_COMPLETADA.txt"