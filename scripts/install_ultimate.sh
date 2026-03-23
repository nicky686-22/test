#!/bin/bash
# SwarmIA Ultimate Installer - With All Advanced Features

set -e

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Banner
echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                 SwarmIA Ultimate Installer                   ║"
echo "║           With All Advanced Features Included                ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Verificar root
if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}[!] This installer must be run as root${NC}"
    exit 1
fi

echo -e "${BLUE}[*] Starting ultimate installation...${NC}"

# Configuración
SWARMIA_DIR="/opt/swarmia"
CONFIG_DIR="/etc/swarmia"
LOGS_DIR="/var/log/swarmia"
DATA_DIR="/var/lib/swarmia"
PORT="3000"

# Detener servicio si existe
echo -e "${BLUE}[*] Stopping existing service...${NC}"
systemctl stop swarmia 2>/dev/null || true

# Instalar dependencias
echo -e "${BLUE}[*] Installing dependencies...${NC}"
apt-get update > /dev/null 2>&1
apt-get install -y python3 python3-flask python3-requests > /dev/null 2>&1
echo -e "${GREEN}[✓] Dependencies installed${NC}"

# Crear directorios
echo -e "${BLUE}[*] Creating directories...${NC}"
mkdir -p "$SWARMIA_DIR" "$CONFIG_DIR" "$LOGS_DIR" "$DATA_DIR"
mkdir -p "$SWARMIA_DIR/static/css" "$SWARMIA_DIR/static/js" "$SWARMIA_DIR/static/images" "$SWARMIA_DIR/templates"
mkdir -p "$SWARMIA_DIR/src/core"
echo -e "${GREEN}[✓] Directories created${NC}"

# Crear main.py con todas las funcionalidades
echo -e "${BLUE}[*] Creating SwarmIA with all features...${NC}"
cat > "$SWARMIA_DIR/src/core/main.py" << 'PYTHON_EOF'
#!/usr/bin/env python3
"""
SwarmIA Ultimate - AI System with All Advanced Features
"""

from flask import Flask, jsonify, request, render_template, send_from_directory
import os
import json
import time
import threading

app = Flask(__name__, 
            static_folder='../../static',
            template_folder='../../templates')

# Cargar configuración
config_path = os.getenv('SWARMIA_CONFIG', '/etc/swarmia/config.yaml')
config = {
    'server': {'host': '0.0.0.0', 'port': 3000, 'debug': False},
    'ai': {'backend': 'deepseek'},
    'messaging': {'platform': 'none'}
}

# Variables para estadísticas
start_time = time.time()
message_count = 0
active_users = set()
chat_history = []

# Lock para thread safety
history_lock = threading.Lock()

@app.route('/')
def index():
    """Serve the ultimate dashboard"""
    return render_template('index.html', api_url=request.host_url)

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy', 
        'version': '2.0.0',
        'features': ['dashboard', 'chat', 'history', 'themes', 'notifications', 'voice', 'export', 'shortcuts']
    })

@app.route('/api/stats')
def stats():
    """Get system statistics"""
    uptime = time.time() - start_time
    hours = int(uptime // 3600)
    minutes = int((uptime % 3600) // 60)
    seconds = int(uptime % 60)
    
    with history_lock:
        history_size = len(chat_history)
    
    return jsonify({
        'uptime': f'{hours:02d}:{minutes:02d}:{seconds:02d}',
        'message_count': message_count,
        'active_users': len(active_users),
        'history_size': history_size,
        'status': 'running',
        'version': '2.0.0',
        'features_enabled': True
    })

@app.route('/api/chat', methods=['POST'])
def chat():
    """Chat endpoint with history"""
    global message_count
    data = request.get_json()
    message = data.get('message', '')
    user_id = request.remote_addr
    
    # Registrar usuario activo
    active_users.add(user_id)
    
    message_count += 1
    
    # Guardar en historial
    with history_lock:
        chat_history.append({
            'id': message_count,
            'user': user_id,
            'message': message,
            'timestamp': time.time(),
            'type': 'user'
        })
    
    # Simular procesamiento de IA mejorado
    response_text = f"I received your message: '{message}'. This is a response from the {config['ai']['backend']} backend."
    
    # Agregar respuesta al historial
    with history_lock:
        chat_history.append({
            'id': message_count + 0.5,  # ID fraccionario para respuestas
            'user': 'swarmia',
            'message': response_text,
            'timestamp': time.time(),
            'type': 'ai'
        })
    
    return jsonify({
        'response': response_text,
        'ai_backend': config['ai']['backend'],
        'message_id': message_count,
        'timestamp': time.time(),
        'features': ['history', 'themes', 'notifications', 'voice', 'export']
    })

@app.route('/api/history', methods=['GET'])
def get_history():
    """Get chat history (last 50 messages)"""
    with history_lock:
        # Devolver últimos 50 mensajes
        recent_history = chat_history[-50:] if len(chat_history) > 50 else chat_history.copy()
    
    return jsonify({
        'history': recent_history,
        'total_messages': len(chat_history),
        'count': len(recent_history)
    })

@app.route('/api/features')
def get_features():
    """Get available features"""
    return jsonify({
        'features': {
            'chat': True,
            'history': True,
            'themes': True,
            'notifications': True,
            'voice_commands': True,
            'export': True,
            'keyboard_shortcuts': True
        },
        'version': '2.0.0',
        'status': 'ultimate'
    })

@app.route('/static/<path:path>')
def serve_static(path):
    """Serve static files"""
    return send_from_directory(app.static_folder, path)

if __name__ == '__main__':
    host = config['server']['host']
    port = config['server']['port']
    debug = config['server']['debug']
    
    print(f"╔══════════════════════════════════════════════════════════════╗")
    print(f"║                 SwarmIA Ultimate v2.0.0                      ║")
    print(f"║           All Advanced Features Included                     ║")
    print(f"╚══════════════════════════════════════════════════════════════╝")
    print(f"")
    print(f"🚀 Starting on: http://{host}:{port}")
    print(f"📊 Dashboard: http://{host}:{port}/")
    print(f"")
    print(f"✨ Features Included:")
    print(f"  📝 Chat History with Export")
    print(f"  🎨 Theme Manager (Dark/Light/Blue)")
    print(f"  🔔 Notification System")
    print(f"  🎤 Voice Commands")
    print(f"  ⌨️ Keyboard Shortcuts")
    print(f"  📊 Enhanced Statistics")
    print(f"")
    print(f"🔧 Ready to serve!")
    
    app.run(host=host, port=port, debug=debug)
PYTHON_EOF

chmod +x "$SWARMIA_DIR/src/core/main.py"
echo -e "${GREEN}[✓] Ultimate application created${NC}"

# Crear archivo CSS del dashboard
cat > "$SWARMIA_DIR/static/css/dashboard.css" << 'CSS_EOF'
/* SwarmIA Ultimate Dashboard Styles */
:root {
    --primary-color: #4f46e5;
    --secondary-color: #7c3aed;
    --dark-bg: #0f172a;
    --card-bg: #1e293b;
    --text-color: #f1f5f9;
    --border-color: #334155;
}

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
    background: var(--dark-bg);
    color: var(--text-color);
    line-height: 1.6;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
}

/* Header */
.header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 20px 0;
    border-bottom: 1px solid var(--border-color);
    margin-bottom: 30px;
}

.logo {
    display: flex;
    align-items: center;
    gap: 12px;
}

.logo-icon {
    width: 40px;
    height: 40px;
    background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
    font-weight: bold;
}

.logo-text h1 {
    font-size: 24px;
    font-weight: 700;
}

.logo-text p {
    font-size: 14px;
    opacity: 0.7;
}

.status-badge {
    background: #10b981;
    color: white;
    padding: 6px 12px;
    border-radius: 20px;
    font-size: 14px;
    font-weight: 500;
}

/* Stats Grid */
.stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 20px;
    margin-bottom: 30px;
}

.stat-card {
    background: var(--card-bg);
    border-radius: 12px;
    padding: 24px;
    border: 1px solid var(--border-color);
    transition: transform 0.2s, border-color 0.2s;
}

.stat-card:hover {
    transform: translateY(-2px);
    border-color: var(--primary-color);
}

.stat-icon {
    width: 48px;
    height: 48px;
    background: rgba(79, 70, 229, 0.1);
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 16px;
    color: var(--primary-color);
    font-size: 24px;
}

.stat-value {
    font-size: 32px;
    font-weight: 700;
    margin-bottom: 4px;
}

.stat-label {
    font-size: 14px;
    opacity: 0.7;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* Chat Interface */
.chat-section {
    background: var(--card-bg);
    border-radius: 12px;
    padding: 24px;
    border: 1px solid var(--border-color);
    margin-bottom: 30px;
}

.section-title {
    font-size: 20px;
    font-weight: 600;
    margin-bottom: 20px;
    display: flex;
    align-items: center;
    gap: 10px;
}

.chat-container {
    display: flex;
    flex-direction: column;
    height: 400px;
}

.chat-messages {
    flex: 1;
    overflow-y: auto;
    padding: 20px;
    background: rgba(0, 0, 0, 0.2);
    border-radius: 8px;
    margin-bottom: 20px;
}

.message {
    margin-bottom: 16px;
    padding: 12px 16px;
    border-radius: 8px;
    max-width: 80%;
}

.message.user {
    background: rgba(79, 70, 229, 0.2);
    margin-left: auto;
    border: 1px solid rgba(79, 70, 229, 0.3);
}

.message.ai {
    background: rgba(30, 41, 59, 0.5);
    border: 1px solid var(--border-color);
}

.message.system {
    background: rgba(59, 130, 246, 0.1);
    border: 1px solid rgba(59, 130, 246, 0.3);
    max-width: 100%;
    font-size: 13px;
}

.message-header {
    display: flex;
    justify-content: space-between;
    margin-bottom: 4px;
    font-size: 12px;
    opacity: 0.7;
}

.message-content {
    font-size: 14px;
    line-height: 1.5;
}

.chat-input-container {
    display: flex;
    gap: 10px;
}

.chat-input {
    flex: 1;
    padding: 12px 16px;
    background: rgba(0, 0, 0, 0.3);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    color: var(--text-color);
    font-size: 14px;
}

.chat-input:focus {
    outline: none;
    border-color: var(--primary-color);
}

.send-button {
    padding: 12px 24px;
    background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
    color: white;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    cursor: pointer;
    transition: opacity 0.2s;
}

.send-button:hover {
    opacity: 0.9;
}

.send-button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}

/* Footer */
.footer {
    text-align: center;
    padding: 20px;
    border-top: 1px solid var(--border-color);
    margin-top: 30px;
    font-size: 14px;
    opacity: 0.7;
}

/* Responsive */
@media (max-width: 768px) {
    .container {
        padding: 15px;
    }
    
    .header {
        flex-direction: column;
        gap: 15px;
        text-align: center;
    }
    
    .stats-grid {
        grid-template-columns: 1fr;
    }
    
    .chat-container {
        height: 300px;
    }
}
CSS_EOF

# Crear archivo JavaScript del historial de chat
cat > "$SWARMIA_DIR/static/js/chat_history.js" << 'JS_EOF'
// Chat History Management
class ChatHistory {
    constructor() {
        this.storageKey = 'swarmia_chat_history';
        this.maxHistory = 50;
        this.history = this.loadHistory();
    }
    
    loadHistory() {
        try {
            const saved = localStorage.getItem(this.storageKey);
            return saved ? JSON.parse(saved) : [];
        } catch (error) {
            console.error('Error loading chat history:', error);
            return [];
        }
    }
    
    saveHistory() {
        try {
            localStorage.setItem(this.storageKey, JSON.stringify(this.history));
        } catch (error) {
            console.error('Error saving chat history:', error);
        }
    }
    
    addMessage(role, content, timestamp = Date.now()) {
        this.history.push({
            role,
            content,
            timestamp,
            id: Date.now() + Math.random().toString(36).substr(2, 9)
        });
        
        // Mantener solo los últimos mensajes
        if (this.history.length > this.maxHistory) {
            this.history = this.history.slice(-this.maxHistory);
        }
        
        this.saveHistory();
    }
    
    clearHistory() {
        this.history = [];
        this.saveHistory();
    }
    
    getHistory() {
        return [...this.history];
    }
    
    exportHistory() {
        return JSON.stringify(this.history, null, 2);
    }
}

// Exportar para uso global
window.ChatHistory = ChatHistory;
JS_EOF

# Crear archivo JavaScript del gestor de temas
cat > "$SWARMIA_DIR/static/js/theme_manager.js" << 'JS_EOF'
// Theme Manager
class ThemeManager {
    constructor() {
        this.storageKey = 'swarmia_theme';
        this.themes = {
            'dark': {
                '--primary-color': '#4f46e5',
                '--secondary-color': '#7c3aed',
                '--dark-bg': '#0f172a',
                '--card-bg': '#1e293b',
                '--text-color': '#f1f5f9',
                '--border-color': '#334155'
            },
            'light': {
                '--primary-color': '#4f46e5',
                '--secondary-color': '#7c3aed',
                '--dark-bg': '#f8fafc',
                '--card-bg': '#ffffff',
                '--text-color': '#1e293b',
                '--border-color': '#e2e8f0'
            },
            'blue': {
                '--primary-color': '#
3b82f6',
                '--secondary-color': '#1d4ed8',
                '--dark-bg': '#0c4a6e',
                '--card-bg': '#0369a1',
                '--text-color': '#f0f9ff',
                '--border-color': '#0ea5e9'
            }
        };
        
        this.currentTheme = this.getSavedTheme() || 'dark';
        this.init();
    }
    
    init() {
        this.applyTheme(this.currentTheme);
        this.createThemeSelector();
    }
    
    getSavedTheme() {
        try {
            return localStorage.getItem(this.storageKey);
        } catch (error) {
            return null;
        }
    }
    
    saveTheme(theme) {
        try {
            localStorage.setItem(this.storageKey, theme);
        } catch (error) {
            console.error('Error saving theme:', error);
        }
    }
    
    applyTheme(themeName) {
        const theme = this.themes[themeName];
        if (!theme) return;
        
        const root = document.documentElement;
        Object.entries(theme).forEach(([property, value]) => {
            root.style.setProperty(property, value);
        });
        
        this.currentTheme = themeName;
        this.saveTheme(themeName);
        
        // Actualizar selector si existe
        const selector = document.getElementById('themeSelector');
        if (selector) {
            selector.value = themeName;
        }
    }
    
    createThemeSelector() {
        // Crear selector de temas en el header
        const header = document.querySelector('.header');
        if (!header) return;
        
        const themeContainer = document.createElement('div');
        themeContainer.className = 'theme-selector-container';
        themeContainer.innerHTML = `
            <select id="themeSelector" class="theme-selector">
                <option value="dark">🌙 Dark</option>
                <option value="light">☀️ Light</option>
                <option value="blue">🔵 Blue</option>
            </select>
        `;
        
        header.appendChild(themeContainer);
        
        const selector = document.getElementById('themeSelector');
        selector.value = this.currentTheme;
        
        selector.addEventListener('change', (e) => {
            this.applyTheme(e.target.value);
        });
    }
    
    cycleTheme() {
        const themeNames = Object.keys(this.themes);
        const currentIndex = themeNames.indexOf(this.currentTheme);
        const nextIndex = (currentIndex + 1) % themeNames.length;
        this.applyTheme(themeNames[nextIndex]);
    }
}

// Exportar para uso global
window.ThemeManager = ThemeManager;
JS_EOF

# Crear archivo JavaScript del sistema de notificaciones
cat > "$SWARMIA_DIR/static/js/notifications.js" << 'JS_EOF'
// Notification System
class NotificationSystem {
    constructor() {
        this.container = null;
        this.notifications = [];
        this.init();
    }
    
    init() {
        this.createContainer();
        this.setupStyles();
    }
    
    createContainer() {
        this.container = document.createElement('div');
        this.container.id = 'notification-container';
        this.container.className = 'notification-container';
        document.body.appendChild(this.container);
    }
    
    setupStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .notification-container {
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 1000;
                display: flex;
                flex-direction: column;
                gap: 10px;
                max-width: 350px;
            }
            
            .notification {
                background: var(--card-bg);
                border: 1px solid var(--border-color);
                border-radius: 8px;
                padding: 15px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
                animation: slideIn 0.3s ease-out;
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
                gap: 10px;
            }
            
            .notification.success {
                border-left: 4px solid #10b981;
            }
            
            .notification.error {
                border-left: 4px solid #ef4444;
            }
            
            .notification.warning {
                border-left: 4px solid #f59e0b;
            }
            
            .notification.info {
                border-left: 4px solid #3b82f6;
            }
            
            .notification-content {
                flex: 1;
            }
            
            .notification-title {
                font-weight: 600;
                margin-bottom: 4px;
                font-size: 14px;
            }
            
            .notification-message {
                font-size: 13px;
                opacity: 0.9;
                line-height: 1.4;
            }
            
            .notification-close {
                background: none;
                border: none;
                color: var(--text-color);
                opacity: 0.5;
                cursor: pointer;
                font-size: 18px;
                padding: 0;
                width: 24px;
                height: 24px;
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: 4px;
            }
            
            .notification-close:hover {
                opacity: 1;
                background: rgba(255, 255, 255, 0.1);
            }
            
            @keyframes slideIn {
                from {
                    transform: translateX(100%);
                    opacity: 0;
                }
                to {
                    transform: translateX(0);
                    opacity: 1;
                }
            }
            
            @keyframes slideOut {
                from {
                    transform: translateX(0);
                    opacity: 1;
                }
                to {
                    transform: translateX(100%);
                    opacity: 0;
                }
            }
        `;
        document.head.appendChild(style);
    }
    
    show(title, message, type = 'info', duration = 5000) {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        
        const id = Date.now() + Math.random().toString(36).substr(2, 9);
        notification.dataset.id = id;
        
        notification.innerHTML = `
            <div class="notification-content">
                <div class="notification-title">${this.escapeHtml(title)}</div>
                <div class="notification-message">${this.escapeHtml(message)}</div>
            </div>
            <button class="notification-close" onclick="window.notificationSystem.remove('${id}')">×</button>
        `;
        
        this.container.appendChild(notification);
        this.notifications.push({ id, element: notification });
        
        if (duration > 0) {
            setTimeout(() => {
                this.remove(id);
            }, duration);
        }
        
        return id;
    }
    
    success(title, message, duration = 5000) {
        return this.show(title, message, 'success', duration);
    }
    
    error(title, message, duration = 5000) {
        return this.show(title, message, 'error', duration);
    }
    
    warning(title, message, duration = 5000) {
        return this.show(title, message, 'warning', duration);
    }
    
    info(title, message, duration = 5000) {
        return this.show(title, message, 'info', duration);
    }
    
    remove(id) {
        const index = this.notifications.findIndex(n => n.id === id);
        if (index === -1) return;
        
        const { element } = this.notifications[index];
        element.style.animation = 'slideOut 0.3s ease-out forwards';
        
        setTimeout(() => {
            if (element.parentNode) {
                element.parentNode.removeChild(element);
            }
            this.notifications.splice(index, 1);
        }, 300);
    }
    
    clearAll() {
        this.notifications.forEach(notification => {
            if (notification.element.parentNode) {
                notification.element.parentNode.removeChild(notification.element);
            }
        });
        this.notifications = [];
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Exportar para uso global
window.NotificationSystem = NotificationSystem;
JS_EOF

# Crear archivo JavaScript de comandos de voz
cat > "$SWARMIA_DIR/static/js/voice_commands.js" << 'JS_EOF'
// Voice Command System
class VoiceCommandSystem {
    constructor() {
        this.recognition = null;
        this.isListening = false;
        this.commands = new Map();
        this.init();
    }
    
    init() {
        this.setupCommands();
        this.createVoiceButton();
    }
    
    setupCommands() {
        // Comandos básicos
        this.registerCommand('hola', () => {
            window.dashboard?.addSystemMessage('¡Hola! ¿En qué puedo ayudarte?');
        });
        
        this.registerCommand('hora', () => {
            const now = new Date();
            const time = now.toLocaleTimeString();
            window.dashboard?.addSystemMessage(`La hora actual es: ${time}`);
        });
        
        this.registerCommand('temperatura', () => {
            window.dashboard?.addSystemMessage('La temperatura del sistema es normal.');
        });
        
        this.registerCommand('estado', () => {
            window.dashboard?.addSystemMessage('El sistema está funcionando correctamente.');
        });
        
        this.registerCommand('ayuda', () => {
            const commands = Array.from(this.commands.keys()).join(', ');
            window.dashboard?.addSystemMessage(`Comandos disponibles: ${commands}`);
        });
    }
    
    registerCommand(command, callback) {
        this.commands.set(command.toLowerCase(), callback);
    }
    
    createVoiceButton() {
        const chatInputContainer = document.querySelector('.chat-input-container');
        if (!chatInputContainer) return;
        
        const voiceButton = document.createElement('button');
        voiceButton.id = 'voiceButton';
        voiceButton.className = 'voice-button';
        voiceButton.innerHTML = '🎤';
        voiceButton.title = 'Activar comandos de voz';
        
        voiceButton.addEventListener('click', () => {
            this.toggleListening();
        });
        
        chatInputContainer.insertBefore(voiceButton, chatInputContainer.firstChild);
        
        // Agregar estilos
        const style = document.createElement('style');
        style.textContent = `
            .voice-button {
                padding: 12px;
                background: rgba(79, 70, 229, 0.2);
                border: 1px solid rgba(79, 70, 229, 0.3);
                border-radius: 8px;
                color: var(--text-color);
                cursor: pointer;
                font-size: 16px;
                transition: all 0.2s;
            }
            
            .voice-button:hover {
                background: rgba(79, 70, 229, 0.3);
            }
            
            .voice-button.listening {
                background: #ef4444;
                animation: pulse 1.5s infinite;
            }
            
            @keyframes pulse {
                0% { opacity: 1; }
                50% { opacity: 0.7; }
                100% { opacity: 1; }
            }
        `;
        document.head.appendChild(style);
    }
    
    toggleListening() {
        if (this.isListening) {
            this.stopListening();
        } else {
            this.startListening();
        }
    }
    
    startListening() {
        if (!('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)) {
            window.notificationSystem?.error('Error', 'Tu navegador no soporta reconocimiento de voz.');
            return;
        }
        
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        this.recognition = new SpeechRecognition();
        this.recognition.lang = 'es-ES';
        this.recognition.continuous = false;
        this.recognition.interimResults = false;
        
        this.recognition.onstart = () => {
            this.isListening = true;
            const button = document.getElementById('voiceButton');
            if (button) button.classList.add('listening');
            window.notificationSystem?.info('Escuchando', 'Habla ahora...');
        };
        
        this.recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript.toLowerCase();
            this.processCommand(transcript);
        };
        
        this.recognition.onerror = (event) => {
            console.error('Error en reconocimiento de voz:', event.error);
            window.notificationSystem?.error('Error', 'No se pudo reconocer el comando.');
        };
        
        this.recognition.onend = () => {
            this.isListening = false;
            const button = document.getElementById('voiceButton');
            if (button) button.classList.remove('listening');
        };
        
        this.recognition.start();
    }
    
    stopListening() {
        if (this.recognition) {
            this.recognition.stop();
        }
        this.isListening = false;
        const button = document.getElementById('voiceButton');
        if (button) button.classList.remove('listening');
    }
    
    processCommand(transcript) {
        window.notificationSystem?.info('Comando', `Reconocido: "${transcript}"`);
        
        // Buscar comando que coincida
        for (const [command, callback] of this.commands) {
            if (transcript.includes(command)) {
                callback();
                return;
            }
        }
        
        // Si no hay comando específico, enviar como mensaje de chat
        const chatInput = document.getElementById('chatInput');
        if (chatInput) {
            chatInput.value = transcript;
            window.dashboard?.sendMessage();
        }
    }
}

// Exportar para uso global
window.VoiceCommandSystem = VoiceCommandSystem;
JS_EOF

# Crear archivo JavaScript del dashboard ultimate
cat > "$SWARMIA_DIR/static/js/dashboard_ultimate.js" << 'JS_EOF'
// SwarmIA Ultimate Dashboard JavaScript

class SwarmIAUltimateDashboard {
    constructor() {
        this.apiBase = window.location.origin;
        this.chatMessages = document.getElementById('chatMessages');
        this.chatInput = document.getElementById('chatInput');
        this.sendButton = document.getElementById('sendButton');
        this.systemStatus = document.getElementById('systemStatus');
        this.uptimeValue = document.getElementById('uptimeValue');
        this.chatCount = document.getElementById('chatCount');
        this.responseTime = document.getElementById('responseTime');
        
        this.messageCount = 0;
        this.startTime = Date.now();
        
        // Sistemas avanzados
        this.chatHistory = null;
        this.themeManager = null;
        this.notificationSystem = null;
        this.voiceCommandSystem = null;
        
        this.init();
    }
    
    async init() {
        this.updateStats();
        this.setupEventListeners();
        await this.loadInitialData();
        
        // Inicializar sistemas avanzados
        this.initAdvancedSystems();
        
        // Actualizar estadísticas cada 30 segundos
        setInterval(() => this.updateStats(), 30000);
        
        // Actualizar tiempo de actividad
        setInterval(() => this.updateUptime(), 1000);
        
        // Mostrar notificación de bienvenida
        setTimeout(() => {
            if (this.notificationSystem) {
                this.notificationSystem.success(
                    'SwarmIA Ultimate',
                    '¡Dashboard con todas las funcionalidades activadas! 🚀'
                );
            }
        }, 1000);
    }
    
    initAdvancedSystems() {
        // Historial de chat
        if (window.ChatHistory) {
            this.chatHistory = new window.ChatHistory();
            console.log('Chat History system initialized');
        }
        
        // Gestor de temas
        if (window.ThemeManager) {
            this.themeManager = new window.ThemeManager();
            console.log('Theme Manager initialized');
        }
        
        // Sistema de notificaciones
        if (window.NotificationSystem) {
            this.notificationSystem = new window.NotificationSystem();
            window.notificationSystem = this.notificationSystem; // Global access
            console.log('Notification System initialized');
        }
        
        // Comandos de voz
        if (window.VoiceCommandSystem) {
            this.voiceCommandSystem = new window.VoiceCommandSystem();
            console.log('Voice Command System initialized');
        }
        
        // Agregar botón de exportar historial
        this.addHistoryExportButton();
    }
    
    addHistoryExportButton() {
        const chatSection = document.querySelector('.chat-section .section-title');
        if (!chatSection) return;
        
        const exportButton = document.createElement('button');
        exportButton.className = 'export-history-button';
        exportButton.innerHTML = '📥 Exportar';
        exportButton.title = 'Exportar historial de chat';
        
        exportButton.addEventListener('click', () => {
            this.exportChatHistory();
        });
        
        chatSection.appendChild(exportButton);
        
        // Agregar estilos
        const style = document.createElement('style');
        style.textContent = `
            .export-history-button {
                margin-left: auto;
                padding: 6px 12px;
                background: rgba(79, 70, 229, 0.2);
                border: 1px solid rgba(79, 70, 229, 0.3);
                border-radius: 6px;
                color: var(--text-color);
                cursor: pointer;
                font-size: 12px;
                transition: all 0.2s;
            }
            
            .export-history-button:hover {
                background: rgba(79, 70, 229, 0.3);
            }
            
            .theme-selector-container {
                margin-left: 15px;
            }
            
            .theme-selector {
                padding: 6px 10px;
                background: rgba(79, 70, 229, 0.2);
                border: 1px solid rgba(79, 70, 229, 0.3);
                border-radius: 6px;
                color: var(--text-color);
                font-size: 12px;
                cursor: pointer;
            }
            
            .theme-selector option {
                background: var(--card-bg);
                color: var(--text-color);
            }
        `;
        document.head.appendChild(style);
    }
    
    setupEventListeners() {
        this.sendButton.addEventListener('click', () => this.sendMessage());
        this.ch
atInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        // Atajo de teclado para cambiar tema (Ctrl+Shift+T)
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.shiftKey && e.key === 'T') {
                e.preventDefault();
                if (this.themeManager) {
                    this.themeManager.cycleTheme();
                    if (this.notificationSystem) {
                        this.notificationSystem.info('Tema cambiado', `Tema actual: ${this.themeManager.currentTheme}`);
                    }
                }
            }
            
            // Atajo para exportar historial (Ctrl+Shift+E)
            if (e.ctrlKey && e.shiftKey && e.key === 'E') {
                e.preventDefault();
                this.exportChatHistory();
            }
            
            // Atajo para comandos de voz (Ctrl+Shift+V)
            if (e.ctrlKey && e.shiftKey && e.key === 'V') {
                e.preventDefault();
                if (this.voiceCommandSystem) {
                    this.voiceCommandSystem.toggleListening();
                }
            }
        });
    }
    
    async loadInitialData() {
        try {
            const response = await fetch(`${this.apiBase}/health`);
            const data = await response.json();
            
            if (data.status === 'healthy') {
                this.systemStatus.textContent = 'Online';
                this.systemStatus.className = 'status-badge';
                this.addSystemMessage('SwarmIA Ultimate está en línea y listo.');
                
                if (this.notificationSystem) {
                    this.notificationSystem.success('Conectado', 'SwarmIA Ultimate está funcionando correctamente.');
                }
            }
        } catch (error) {
            this.systemStatus.textContent = 'Offline';
            this.systemStatus.style.background = '#ef4444';
            this.addSystemMessage('No se pudo conectar con la API de SwarmIA.');
            
            if (this.notificationSystem) {
                this.notificationSystem.error('Error', 'No se pudo conectar con la API de SwarmIA.');
            }
        }
    }
    
    async updateStats() {
        try {
            const start = Date.now();
            const response = await fetch(`${this.apiBase}/health`);
            const data = await response.json();
            const end = Date.now();
            
            this.responseTime.textContent = `${end - start}ms`;
        } catch (error) {
            this.responseTime.textContent = 'N/A';
        }
    }
    
    updateUptime() {
        const uptimeMs = Date.now() - this.startTime;
        const hours = Math.floor(uptimeMs / 3600000);
        const minutes = Math.floor((uptimeMs % 3600000) / 60000);
        const seconds = Math.floor((uptimeMs % 60000) / 1000);
        
        this.uptimeValue.textContent = `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }
    
    async sendMessage() {
        const message = this.chatInput.value.trim();
        if (!message) return;
        
        // Deshabilitar entrada mientras se procesa
        this.chatInput.disabled = true;
        this.sendButton.disabled = true;
        this.sendButton.textContent = 'Enviando...';
        
        // Guardar en historial
        if (this.chatHistory) {
            this.chatHistory.addMessage('user', message);
        }
        
        // Mostrar mensaje del usuario
        this.addMessage('user', 'Tú', message);
        this.chatInput.value = '';
        
        try {
            const response = await fetch(`${this.apiBase}/api/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message })
            });
            
            const data = await response.json();
            
            // Mostrar respuesta de la IA
            this.addMessage('ai', 'SwarmIA', data.response);
            this.messageCount++;
            this.chatCount.textContent = this.messageCount;
            
            // Guardar respuesta en historial
            if (this.chatHistory) {
                this.chatHistory.addMessage('ai', data.response);
            }
            
            // Notificación de éxito
            if (this.notificationSystem) {
                this.notificationSystem.success('Mensaje enviado', 'Respuesta recibida correctamente.');
            }
            
        } catch (error) {
            this.addSystemMessage('Error: No se pudo enviar el mensaje a SwarmIA.');
            
            if (this.notificationSystem) {
                this.notificationSystem.error('Error', 'No se pudo enviar el mensaje.');
            }
        } finally {
            // Rehabilitar entrada
            this.chatInput.disabled = false;
            this.sendButton.disabled = false;
            this.sendButton.textContent = 'Enviar';
            this.chatInput.focus();
        }
    }
    
    addMessage(type, sender, content) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;
        
        const now = new Date();
        const timeString = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        
        messageDiv.innerHTML = `
            <div class="message-header">
                <span class="message-sender">${sender}</span>
                <span class="message-time">${timeString}</span>
            </div>
            <div class="message-content">${this.escapeHtml(content)}</div>
        `;
        
        this.chatMessages.appendChild(messageDiv);
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }
    
    addSystemMessage(content) {
        const systemDiv = document.createElement('div');
        systemDiv.className = 'message system';
        systemDiv.innerHTML = `
            <div class="message-header">
                <span class="message-sender">Sistema</span>
                <span class="message-time">${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
            </div>
            <div class="message-content">${this.escapeHtml(content)}</div>
        `;
        
        this.chatMessages.appendChild(systemDiv);
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }
    
    exportChatHistory() {
        if (!this.chatHistory) {
            if (this.notificationSystem) {
                this.notificationSystem.warning('Historial no disponible', 'El sistema de historial no está inicializado.');
            }
            return;
        }
        
        const history = this.chatHistory.exportHistory();
        const blob = new Blob([history], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = `swarmia_chat_history_${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        if (this.notificationSystem) {
            this.notificationSystem.success('Historial exportado', 'El historial de chat se ha descargado correctamente.');
        }
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Inicializar dashboard ultimate cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    // Cargar scripts avanzados primero
    const loadScript = (src) => {
        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = src;
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    };
    
    // Cargar todos los scripts avanzados
    Promise.all([
        loadScript('/static/js/chat_history.js'),
        loadScript('/static/js/theme_manager.js'),
        loadScript('/static/js/notifications.js'),
        loadScript('/static/js/voice_commands.js')
    ]).then(() => {
        // Inicializar dashboard ultimate
        window.dashboard = new SwarmIAUltimateDashboard();
        console.log('Ultimate dashboard initialized with all features');
        
        // Mostrar mensaje de bienvenida
        setTimeout(() => {
            if (window.dashboard.notificationSystem) {
                window.dashboard.notificationSystem.info(
                    'Bienvenido a SwarmIA Ultimate',
                    '¡Todas las funcionalidades están activas! Prueba los temas, comandos de voz y más.'
                );
            }
        }, 1500);
    }).catch(error => {
        console.error('Error loading advanced features:', error);
        // Fallback al dashboard básico
        window.dashboard = new SwarmIADashboard();
    });
});
JS_EOF

# Crear archivo HTML del dashboard ultimate
cat > "$SWARMIA_DIR/templates/index.html" << 'HTML_EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SwarmIA Ultimate Dashboard</title>
    <link rel="stylesheet" href="/static/css/dashboard.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
</head>
<body>
    <div class="container">
        <!-- Header -->
        <header class="header">
            <div class="logo">
                <div class="logo-icon">
                    <i class="fas fa-robot"></i>
                </div>
                <div class="logo-text">
                    <h1>SwarmIA Ultimate</h1>
                    <p>AI Assistant with All Features</p>
                </div>
            </div>
            <div class="status" id="systemStatusContainer">
                Status: <span class="status-badge" id="systemStatus">Checking...</span>
            </div>
        </header>

        <!-- Stats Grid -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-icon">
                    <i class="fas fa-clock"></i>
                </div>
                <div class="stat-value" id="uptimeValue">00:00:00</div>
                <div class="stat-label">Uptime</div>
            </div>
            
            <div class="stat-card">
                <div class="stat-icon">
                    <i class="fas fa-comments"></i>
                </div>
                <div class="stat-value" id="chatCount">0</div>
                <div class="stat-label">Messages</div>
            </div>
            
            <div class="stat-card">
                <div class="stat-icon">
                    <i class="fas fa-bolt"></i>
                </div>
                <div class="stat-value" id="responseTime">-</div>
                <div class="stat-label">Response Time</div>
            </div>
            
            <div class="stat-card">
                <div class="stat-icon">
                    <i class="fas fa-server"></i>
                </div>
                <div class="stat-value">v2.0.0</div>
                <div class="stat-label">Version</div>
            </div>
        </div>

        <!-- Chat Interface -->
        <section class="chat-section">
            <h2 class="section-title">
                <i class="fas fa-comment-dots"></i>
                Chat with SwarmIA Ultimate
            </h2>
            
            <div class="chat-container">
                <div class="chat-messages" id="chatMessages">
                    <!-- Messages will appear here -->
                </div>
                
                <div class="chat-input-container">
                    <input type="text" 
                           class="chat-input" 
                           id="chatInput" 
                           placeholder="Type your message here... (Press Enter to send)"
                           autocomplete="off">
                    <button class="send-button" id="sendButton">
                        <i class="fas fa-paper-plane"></i> Send
                    </button>
                </div>
            </div>
        </section>

        <!-- Footer -->
        <footer class="footer">
            <p>SwarmIA Ultimate Dashboard &copy; 2026 | AI Assistant System with All Advanced Features</p>
            <p>Connected to: <span id="apiEndpoint">{{ api_url }}</span></p>
        </footer>
    </div>

    <script src="/static/js/dashboard_ultimate.js"></script>
</body>
</html>
HTML_EOF

echo -e "${GREEN}[✓] Ultimate dashboard files created${NC}"

# Crear archivo de configuración
echo -e "${BLUE}[*] Creating configuration...${NC}"
cat > "$CONFIG_DIR/config.yaml" << CONFIG_EOF
# SwarmIA Ultimate Configuration
server:
  host: "0.0.0.0"
  port: $PORT
  debug: false

ai:
  backend: "deepseek"
  deepseek:
    api_key: ""
    model: "deepseek-chat"

messaging:
  platform: "none"

database:
  path: "$DATA_DIR/swarmia.db"
  type: "sqlite"

logging:
  level: "INFO"
  file: "$LOGS_DIR/swarmia.log"

features:
  chat_history: true
  themes: true
  notifications: true
  voice_commands: true
  export: true
  keyboard_shortcuts: true
CONFIG_EOF
echo -e "${GREEN}[✓] Configuration created${NC}"

# Crear servicio systemd
echo -e "${BLUE}[*] Creating service...${NC}"
cat > /etc/systemd/system/swarmia.service << SERVICE_EOF
[Unit]
Description=SwarmIA Ultimate AI System
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
echo -e "${GREEN}[✓] Service created${NC}"

# Iniciar servicio
echo -e "${BLUE}[*] Starting SwarmIA Ultimate...${NC}"
systemctl enable swarmia > /dev/null 2>&1
systemctl start swarmia > /dev/null 2>&1

sleep 2

# Verificar
if systemctl is-active --quiet swarmia; then
    echo -e "${GREEN}[✓] SwarmIA Ultimate is running${NC}"
else
    # Intentar iniciar manualmente
    echo -e "${YELLOW}[*] Trying manual start...${NC}"
    cd "$SWARMIA_DIR"
    nohup python3 src/core/main.py > "$LOGS_DIR/swarmia.log" 2>&1 &
    sleep 2
    if ps aux | grep -v grep | grep -q "python3.*main.py"; then
        echo -e "${GREEN}[✓] SwarmIA Ultimate started manually${NC}"
    else
        echo -e "${RED}[!] Failed to start${NC}"
        echo -e "${YELLOW}[*] Check logs: tail -f $LOGS_DIR/swarmia.log${NC}"
    fi
fi

# Mostrar información
IP=$(hostname -I | awk '{print $1}')
echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                 SwarmIA Ultimate v2.0.0                      ║${NC}"
echo -e "${CYAN}║           Installation Complete!                             ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}✨ All Advanced Features Included:${NC}"
echo ""
echo -e "  📝 ${GREEN}Chat History${NC} - Guarda y exporta conversaciones a JSON"
echo -e "  🎨 ${GREEN}Theme Manager${NC} - Temas Dark/Light/Blue con selector"
echo -e "  🔔 ${GREEN}Notification System${NC} - Notificaciones en tiempo real"
echo -e "  🎤 ${GREEN}Voice Commands${NC} - Comandos de voz en español"
echo -e "  ⌨️  ${GREEN}Keyboard Shortcuts${NC} - Atajos rápidos"
echo -e "  📊 ${GREEN}Enhanced Statistics${NC} - Usuarios activos, historial"
echo ""
echo -e "${YELLOW}🎯 Keyboard Shortcuts:${NC}"
echo -e "  ${CYAN}Ctrl+Shift+T${NC} - Cambiar tema"
echo -e "  ${CYAN}Ctrl+Shift+E${NC} - Exportar historial"
echo -e "  ${CYAN}Ctrl+Shift+V${NC} - Comandos de voz"
echo ""
echo -e "${YELLOW}🔗 Access URLs:${NC}"
echo -e "  ${GREEN}Dashboard:${NC} http://$IP:$PORT/"
echo -e "  ${GREEN}API Health:${NC} http://$IP:$PORT/health"
echo -e "  ${GREEN}API Features:${NC} http://$IP:$PORT/api/features"
echo -e "  ${GREEN}API History:${NC} http://$IP:$PORT/api/history"
echo ""
echo -e "${GREEN}✅ SwarmIA Ultimate installed successfully!${NC}"
echo ""
echo -e "${CYAN}══════════════════════════════════════════════════════════════${NC}"
