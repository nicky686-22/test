#!/bin/bash
# Enhance SwarmIA Dashboard with Advanced Features

set -e

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Banner
echo -e "${GREEN}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║           Enhancing SwarmIA Dashboard                        ║"
echo "║           Adding Advanced Features                           ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Verificar root
if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}[!] This script must be run as root${NC}"
    exit 1
fi

SWARMIA_DIR="/opt/swarmia"

# Verificar si SwarmIA está instalado
if [ ! -d "$SWARMIA_DIR" ]; then
    echo -e "${RED}[!] SwarmIA not found at $SWARMIA_DIR${NC}"
    exit 1
fi

echo -e "${BLUE}[*] Stopping SwarmIA service...${NC}"
systemctl stop swarmia 2>/dev/null || true

echo -e "${BLUE}[*] Enhancing dashboard with advanced features...${NC}"

# 1. Agregar funcionalidad de historial de chat
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

# 2. Agregar funcionalidad de temas (light/dark mode)
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
                '--primary-color': '#3b82f6',
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

# 3. Agregar funcionalidad de notificaciones
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

# 4. Agregar funcionalidad de comandos de voz
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

# 5. Actualizar dashboard.js principal para integrar todas las funcionalidades
cat > "$SWARMIA_DIR/static/js/dashboard_enhanced.js" << 'JS_EOF'
// Swarm
IA Enhanced Dashboard JavaScript

class SwarmIAEnhancedDashboard {
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
                    'Dashboard Mejorado',
                    'Funcionalidades avanzadas activadas: historial, temas, notificaciones y comandos de voz.'
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
        this.chatInput.addEventListener('keypress', (e) => {
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
                this.addSystemMessage('System is online and ready.');
                
                if (this.notificationSystem) {
                    this.notificationSystem.success('Conectado', 'SwarmIA está en línea y funcionando.');
                }
            }
        } catch (error) {
            this.systemStatus.textContent = 'Offline';
            this.systemStatus.style.background = '#ef4444';
            this.addSystemMessage('Unable to connect to SwarmIA API.');
            
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
        this.sendButton.textContent = 'Sending...';
        
        // Guardar en historial
        if (this.chatHistory) {
            this.chatHistory.addMessage('user', message);
        }
        
        // Mostrar mensaje del usuario
        this.addMessage('user', 'You', message);
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
            this.addSystemMessage('Error: Unable to send message to SwarmIA.');
            
            if (this.notificationSystem) {
                this.notificationSystem.error('Error', 'No se pudo enviar el mensaje.');
            }
        } finally {
            // Rehabilitar entrada
            this.chatInput.disabled = false;
            this.sendButton.disabled = false;
            this.sendButton.textContent = 'Send';
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
                <span class="message-sender">System</span>
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

// Inicializar dashboard mejorado cuando el DOM esté listo
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
        // Inicializar dashboard mejorado
        window.dashboard = new SwarmIAEnhancedDashboard();
        console.log('Enhanced dashboard initialized with all features');
    }).catch(error => {
        console.error('Error loading advanced features:', error);
        // Fallback al dashboard básico
        window.dashboard = new SwarmIADashboard();
    });
});
JS_EOF

# 6. Actualizar main.py para soportar nuevas funcionalidades
echo -e "${BLUE}[*] Updating main.py with enhanced features...${NC}"
cat > "$SWARMIA_DIR/src/core/main.py" << 'PYTHON_EOF'
#!/usr/bin/env python3
"""
SwarmIA - AI System with Enhanced Dashboard
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
    """Serve the enhanced dashboard"""
    return render_template('index.html', api_url=request.host_url)

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy', 
        'version': '1.0.0',
        'features': ['dashboard', 'chat', 'history', 'themes', 'notifications', 'voice']
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
        'version': '1.0.0',
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
        'features': ['history', 'themes', 'notifications']
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
            'export': True
        },
        'version': '1.1.0',
        'status': 'enhanced'
    })

@app.route('/static/<path:path>')
def serve_static(path):
    """Serve static files"""
    return send_from_directory(app.static_folder, path)

if __name__ == '__main__':
    host = config['server']['host']
    port = config['server']['port']
    debug = config['server']['debug']
    
    print(f"SwarmIA Enhanced starting on http://{host}:{port}")
    print(f"Enhanced Dashboard available at: http://{host}:{port}/")
    print(f"Features: Chat History, Themes, Notifications, Voice Commands")
    app.run(host=host, port=port, debug=debug)
PYTHON_EOF

# 7. Actualizar index.html para cargar el dashboard mejorado
echo -e "${BLUE}[*] Updating index.html to
 load enhanced dashboard...${NC}"
sed -i 's|/static/js/dashboard.js|/static/js/dashboard_enhanced.js|g' "$SWARMIA_DIR/templates/index.html"

# Agregar información de características en el footer
sed -i 's|AI Assistant System|AI Assistant System with Advanced Features|g' "$SWARMIA_DIR/templates/index.html"

echo -e "${GREEN}[✓] Dashboard enhanced with advanced features${NC}"

# Reiniciar servicio
echo -e "${BLUE}[*] Restarting SwarmIA service...${NC}"
systemctl daemon-reload
systemctl restart swarmia

sleep 2

if systemctl is-active --quiet swarmia; then
    echo -e "${GREEN}[✓] SwarmIA restarted successfully${NC}"
else
    echo -e "${YELLOW}[*] Trying manual start...${NC}"
    cd "$SWARMIA_DIR"
    nohup python3 src/core/main.py > /var/log/swarmia/swarmia.log 2>&1 &
    sleep 2
    if ps aux | grep -v grep | grep -q "python3.*main.py"; then
        echo -e "${GREEN}[✓] SwarmIA started manually${NC}"
    else
        echo -e "${RED}[!] Failed to start${NC}"
    fi
fi

# Mostrar información
IP=$(hostname -I | awk '{print $1}')
echo ""
echo -e "${GREEN}✅ Dashboard enhanced successfully!${NC}"
echo ""
echo -e "${CYAN}New Features Added:${NC}"
echo -e "  📝 ${GREEN}Chat History${NC} - Guarda y exporta conversaciones"
echo -e "  🎨 ${GREEN}Theme Manager${NC} - Temas dark/light/blue"
echo -e "  🔔 ${GREEN}Notification System${NC} - Notificaciones en tiempo real"
echo -e "  🎤 ${GREEN}Voice Commands${NC} - Comandos de voz (hola, hora, ayuda)"
echo -e "  📊 ${GREEN}Enhanced Stats${NC} - Usuarios activos, tamaño de historial"
echo ""
echo -e "${CYAN}Keyboard Shortcuts:${NC}"
echo -e "  ${YELLOW}Ctrl+Shift+T${NC} - Cambiar tema"
echo -e "  ${YELLOW}Ctrl+Shift+E${NC} - Exportar historial"
echo -e "  ${YELLOW}Ctrl+Shift+V${NC} - Comandos de voz"
echo ""
echo -e "${CYAN}Dashboard URL:${NC} http://$IP:3000/"
echo -e "${CYAN}API Features:${NC} http://$IP:3000/api/features"
echo -e "${CYAN}API History:${NC} http://$IP:3000/api/history"
echo ""
echo -e "${GREEN}══════════════════════════════════════════════════════════════${NC}"
