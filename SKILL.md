# SwarmIA - Sistema de Asistentes IA Distribuidos

Sistema de asistentes IA con procesamiento por prioridades, múltiples proveedores de IA Nicky68622

### Descripción

SwarmIA es un sistema de asistentes IA distribuidos que incluye:

- Procesamiento de tareas por prioridad con prioridad CRÍTICA para mensajes de usuario
- Integración con WhatsApp y Telegram con APIs independientes
- Soporte dual de IA: API de DeepSeek y modelos locales Llama
- Agentes que completan tareas completamente sin dejar cosas a medias
- Dashboard elegante con cambio de contraseña obligatorio
- Sistema de auto-actualización desde GitHub
- Sistema Anti-Hacking con bloqueo automático de IPs y detección de ataques
- Ejecución de comandos desde Telegram/WhatsApp

### Instalación

Instalación Rápida (Linux)

curl -sSL https://raw.githubusercontent.com/nicky686-22/test/main/scripts/install.sh | sudo bash

Instalación Manual

git clone https://github.com/nicky686-22/test.git SwarmIA
cd SwarmIA
pip install -r requirements.txt
python src/main.py

Windows: Descargar install.bat y ejecutar como Administrador

### Acceso al Dashboard

URL: http://[TU_IP]:8080
Usuario: admin
Contraseña: admin (cambiar en el primer inicio)
Documentación API: http://[TU_IP]:8080/api/docs

### Comandos Remotos (Telegram/WhatsApp)

Una vez configurado el bot, puedes enviar estos comandos:

/status     - Estado del sistema y estadísticas
/install    - Instalar paquetes de Python
/update     - Actualizar SwarmIA desde GitHub
/restart    - Reiniciar servicios SwarmIA
/block_ip   - Bloquear IP maliciosa
/unblock_ip - Desbloquear una IP
/scan       - Escanear puertos de una IP
/info       - Geolocalización de una IP
/whois      - Información WHOIS
/uptime     - Tiempo de actividad del sistema
/logs       - Mostrar logs recientes
/help       - Mostrar comandos disponibles

### Características Principales

Rendimiento Mejorado:
- Prioridad CRÍTICA para mensajes de usuario (nunca se encolan)
- Agentes que completan tareas completamente
- Monitoreo en tiempo real con estadísticas detalladas
- Auto-escalado basado en carga

Sistema Anti-Hacking:
- Detección automática de ataques: escaneo de puertos, fuerza bruta SSH, SQL injection, XSS
- Bloqueo automático de IPs maliciosas con iptables
- Geolocalización de atacantes (país, ciudad, ISP)
- Alertas en tiempo real vía Telegram/WhatsApp
- Registro completo de ataques en base de datos SQLite

Acceso Agresivo al Sistema:
- Integración SSH para gestión remota
- Ejecución de comandos del sistema con privilegios elevados
- Escaneo de red y descubrimiento de dispositivos
- Gestión de servicios (iniciar/detener/reiniciar)

Soporte Dual de IA:
- API de DeepSeek (requiere token)
- Modelos locales Llama (formato GGUF)
- Cambio de modelo en tiempo real
- Historial de conversación por sesión

Comunicación:
- WhatsApp Business API
- Telegram Bot API
- Soporte multi-usuario con permisos
- Colas de mensajes con prioridad
- Soporte multimedia (imágenes, documentos, audio)

Seguridad:
- Autenticación JWT con tokens de refresco
- Cambio de contraseña obligatorio en primer inicio
- Lista blanca de IPs para acceso al dashboard
- Limitación de tasa y protección DDoS
- Registro de actividad con trazabilidad

Auto-actualizaciones:
- Verificación de actualizaciones en GitHub cada 24 horas
- Actualizaciones con un clic desde el dashboard
- Capacidad de reversión si falla la actualización

### Configuración Rápida

Crea un archivo .env en la raíz:

SWARMIA_PORT=8080
DEEPSEEK_API_KEY=tu-clave-api
TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=tu-token
AGGRESSIVE_ENABLED=false
AGGRESSIVE_MODE=normal
AGGRESSIVE_ALLOWED_NETWORKS=192.168.0.0/16,10.0.0.0/8

### Activación del Modo Ultra

El modo Ultra escanea todos los puertos (1-65535) con máxima velocidad:

1. Editar .env:
AGGRESSIVE_ENABLED=true
AGGRESSIVE_MODE=ultra
AGGRESSIVE_ALLOWED_NETWORKS=192.168.0.0/16,10.0.0.0/8
AGGRESSIVE_MAX_THREADS=200

2. Instalar dependencias adicionales:
pip install paramiko cryptography requests

3. Verificar activación en logs:
[AGGRESSIVE] 🔥 ULTRA MODE ACTIVATED - MAXIMUM AGGRESSION 🔥

### Estructura del Proyecto

SwarmIA/
├── SKILL.md
├── README.md
├── LICENSE
├── requirements.txt
├── .env.example
├── config/
│   └── config.example.yaml
├── scripts/
│   ├── install.sh
│   └── install.bat
├── src/
│   ├── core/
│   │   ├── main.py
│   │   ├── config.py
│   │   └── supervisor.py
│   ├── ai/
│   │   ├── deepseek.py
│   │   └── llama.py
│   ├── agents/
│   │   ├── chat.py
│   │   └── aggressive.py
│   ├── gateway/
│   │   └── communication.py
│   └── ui/
│       ├── server.py
│       ├── templates/
│       └── static/
└── docs/

### Desarrollo

Prerrequisitos: Python 3.8+, Git

Configurar entorno de desarrollo:

git clone https://github.com/nicky686-22/test.git SwarmIA
cd SwarmIA
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python src/main.py --debug

### Solución de Problemas

Puerto 8080 en uso: editar .env SWARMIA_PORT=8081
Dashboard no accesible: sudo ufw allow 8080/tcp
IA no responde: verificar API key en dashboard > Configuración > Probar Conexión
Actualización fallida: cd /opt/swarmia && git pull origin main

Ubicación de Logs:
/opt/swarmia/logs/swarmia.log - Logs principales
/opt/swarmia/logs/supervisor.log - Logs del supervisor
/opt/swarmia/logs/security.log - Logs de seguridad (ataques)

### Contribuciones

1. Haz fork del repositorio
2. Crea una rama para tu feature
3. Realiza tus cambios
4. Envía un pull request

### Licencia

MIT License - Ver archivo LICENSE para detalles

### Soporte

GitHub Issues: https://github.com/nicky686-22/test/issues
Documentación: https://github.com/nicky686-22/test#readme

### Historial de Cambios

v2.0.0 (2026-03-23)
- Sistema Anti-Hacking con detección de ataques
- Modo Ultra para escaneo agresivo de puertos
- Comandos remotos desde Telegram/WhatsApp
- Bloqueo automático de IPs maliciosas
- Geolocalización de atacantes
- Mejoras de rendimiento en el supervisor

v1.0.0 (2026-03-22)
- Lanzamiento inicial
- Sistema completo de asistentes IA
- Soporte DeepSeek y Llama
- Integración WhatsApp/Telegram
- Dashboard elegante
- Sistema de auto-actualización
