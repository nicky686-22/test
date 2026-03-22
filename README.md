# SwarmIA - Sistema de Agentes Distribuidos

## 🚀 Visión
SwarmIA es un sistema de agentes distribuidos inspirado en OpenClaw, pero mejorado en todos los aspectos. Sistema de comunicación robusto, agentes extremadamente cumplidores y dashboard elegante.

## ✨ Características Principales
- ✅ **Multi-modelo**: DeepSeek API y Llama local
- ✅ **Comunicación**: WhatsApp y Telegram integrados
- ✅ **Instalación simple**: CMD para Windows, consola para Linux
- ✅ **Dashboard elegante**: Interfaz moderna y responsive
- ✅ **Agentes cumplidores**: Terminan todas las tareas asignadas
- ✅ **Chat siempre activo**: Sin colas de mensajes trabados
- ✅ **Auto-arranque**: Configuración automática para Linux/Windows
- ✅ **Rutas relativas**: Sin rutas absolutas como `/home/xxx`

## 📦 Instalación

### Windows (CMD/PowerShell)
```cmd
git clone https://github.com/nicky686-22/SwarmIA.git
cd SwarmIA
install.bat
```

### Linux (Bash)
```bash
git clone https://github.com/nicky686-22/SwarmIA.git
cd SwarmIA
chmod +x install.sh
./install.sh
```

## 🔧 Configuración Inicial

### 1. Elegir Modelo
- **DeepSeek**: Ingresa tu API token
- **Llama**: Especifica ruta al modelo GGUF

### 2. Configurar Comunicación
- WhatsApp (requiere QR code)
- Telegram (requiere bot token)

### 3. Personalizar IA
- Nombre de tu asistente
- Comportamiento por defecto
- Nivel de supervisión

## 🖥️ Dashboard
Accede después de instalación:
```
http://[TU_IP]:8080
```
- **Usuario inicial**: admin
- **Contraseña inicial**: admin
- **Cambiar credenciales**: Obligatorio en primer acceso

## 🤖 Agentes
- **Supervisor**: Dirige todos los agentes, evita colas
- **Agentes especializados**: Cumplen tareas específicas
- **Chat prioritario**: Mensajes del usuario tienen prioridad máxima

## 🔒 Seguridad
- Credenciales encriptadas
- Acceso por IP local y remoto
- Confirmación explícita para acciones críticas
- Logs detallados de todas las operaciones

## 📁 Estructura del Proyecto
```
SwarmIA/
├── src/                    # Código fuente
│   ├── core/              # Núcleo del sistema
│   ├── agents/            # Agentes especializados
│   ├── gateway/           # Comunicación externa
│   ├── ui/                # Dashboard frontend
│   └── config/            # Configuraciones
├── scripts/               # Scripts de instalación
├── docs/                  # Documentación
└── tests/                 # Pruebas
```

## 🚨 Requisitos
- Python 3.8+ o Node.js 18+
- 2GB RAM mínimo
- Conexión a internet (para DeepSeek/WhatsApp/Telegram)

## 📞 Soporte
- Issues: https://github.com/nicky686-22/SwarmIA/issues
- Wiki: https://github.com/nicky686-22/SwarmIA/wiki

## 📄 Licencia
MIT License - Ver LICENSE para detalles

---

**¡SwarmIA está listo para dominar el mundo de los agentes!** 🚀