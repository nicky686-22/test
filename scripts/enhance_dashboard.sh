
#!/bin/bash
# SwarmIA - Enhance Dashboard with Advanced Features
# Añade: historial de chat, temas, notificaciones, comandos de voz

set -e

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Banner
echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║           SwarmIA Dashboard Enhancer                         ║"
echo "║           Advanced Features Installation                     ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Verificar root
if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}[!] Este script debe ejecutarse como root${NC}"
    echo -e "${YELLOW}Usa: sudo bash scripts/enhance_dashboard.sh${NC}"
    exit 1
fi

# Configuración
SWARMIA_DIR="/opt/swarmia"
STATIC_DIR="$SWARMIA_DIR/static/js"
TEMPLATES_DIR="$SWARMIA_DIR/templates"

# Verificar instalación
if [ ! -d "$SWARMIA_DIR" ]; then
    echo -e "${RED}[!] SwarmIA no encontrado en $SWARMIA_DIR${NC}"
    echo -e "${YELLOW}[!] Ejecuta primero el instalador principal${NC}"
    exit 1
fi

# Crear directorios si no existen
mkdir -p "$STATIC_DIR"
mkdir -p "$TEMPLATES_DIR"

echo -e "${BLUE}[*] Deteniendo servicio SwarmIA...${NC}"
systemctl stop swarmia 2>/dev/null || true

echo -e "${BLUE}[*] Instalando funcionalidades avanzadas...${NC}"

# ============================================================
# 1. Chat History Manager
# ============================================================
cat > "$STATIC_DIR/chat_history.js" << 'JS_EOF'
/**
 * SwarmIA - Chat History Manager
 * Guarda, carga y exporta el historial de conversaciones
 */
class ChatHistory {
    constructor() {
        this.storageKey = 'swarmia_chat_history';
        this.maxHistory = 100;
        this.history = this.loadHistory();
    }
    
    loadHistory() {
        try {
            const saved = localStorage.getItem(this.storageKey);
            return saved ? JSON.parse(saved) : [];
        } catch (e) {
            console.error('Error loading history:', e);
            return [];
        }
    }
    
    saveHistory() {
        try {
            localStorage.setItem(this.storageKey, JSON.stringify(this.history));
        } catch (e) {
            console.error('Error saving history:', e);
        }
    }
    
    addMessage(role, content, timestamp = Date.now()) {
        this.history.push({
            id: `${timestamp}-${Math.random().toString(36).substr(2, 6)}`,
            role: role,
            content: content,
            timestamp: timestamp,
            date: new Date(timestamp).toLocaleString()
        });
        
        if (this.history.length > this.maxHistory) {
            this.history = this.history.slice(-this.maxHistory);
        }
        this.saveHistory();
    }
    
    getHistory() {
        return [...this.history];
    }
    
    clearHistory() {
        this.history = [];
        this.saveHistory();
    }
    
    exportHistory() {
        const data = {
            exportDate: new Date().toISOString(),
            version: '1.0',
            totalMessages: this.history.length,
            history: this.history
        };
        return JSON.stringify(data, null, 2);
    }
    
    importHistory(jsonData) {
        try {
            const data = JSON.parse(jsonData);
            if (data.history && Array.isArray(data.history)) {
                this.history = data.history;
                this.saveHistory();
                return true;
            }
            return false;
        } catch (e) {
            console.error('Import error:', e);
            return false;
        }
    }
}

window.ChatHistory = ChatHistory;
JS_EOF

# ============================================================
# 2. Theme Manager (Dark/Light/Blue)
# ============================================================
cat > "$STATIC_DIR/theme_manager.js" << 'JS_EOF'
/**
 * SwarmIA - Theme Manager
 * Gestión de temas: dark, light, blue
 */
class ThemeManager {
    constructor() {
        this.storageKey = 'swarmia_theme';
        this.themes = {
            'dark': {
                name: 'Dark',
                icon: '🌙',
                colors: {
                    '--primary': '#4f46e5',
                    '--primary-dark': '#4338ca',
                    '--bg-primary': '#0f172a',
                    '--bg-secondary': '#1e293b',
                    '--text-primary': '#f1f5f9',
                    '--text-secondary': '#94a3b8',
                    '--border': '#334155',
                    '--success': '#10b981',
                    '--error': '#ef4444',
                    '--warning': '#f59e0b'
                }
            },
            'light': {
                name: 'Light',
                icon: '☀️',
                colors: {
                    '--primary': '#4f46e5',
                    '--primary-dark': '#4338ca',
                    '--bg-primary': '#f8fafc',
                    '--bg-secondary': '#ffffff',
                    '--text-primary': '#1e293b',
                    '--text-secondary': '#64748b',
                    '--border': '#e2e8f0',
                    '--success': '#10b981',
                    '--error': '#ef4444',
                    '--warning': '#f59e0b'
                }
            },
            'blue': {
                name: 'Blue',
                icon: '🔵',
                colors: {
                    '--primary': '#3b82f6',
                    '--primary-dark': '#2563eb',
                    '--bg-primary': '#0c4a6e',
                    '--bg-secondary': '#075985',
                    '--text-primary': '#f0f9ff',
                    '--text-secondary': '#bae6fd',
                    '--border': '#0ea5e9',
                    '--success': '#10b981',
                    '--error': '#ef4444',
                    '--warning': '#f59e0b'
                }
            }
        };
        
        this.currentTheme = this.getSavedTheme() || 'dark';
        this.applyTheme(this.currentTheme);
    }
    
    getSavedTheme() {
        try {
            return localStorage.getItem(this.storageKey);
        } catch (e) {
            return null;
        }
    }
    
    saveTheme(theme) {
        try {
            localStorage.setItem(this.storageKey, theme);
        } catch (e) {}
    }
    
    applyTheme(themeName) {
        const theme = this.themes[themeName];
        if (!theme) return;
        
        const root = document.documentElement;
        Object.entries(theme.colors).forEach(([prop, value]) => {
            root.style.setProperty(prop, value);
        });
        
        this.currentTheme = themeName;
        this.saveTheme(themeName);
        
        // Actualizar meta theme-color para móviles
        const meta = document.querySelector('meta[name="theme-color"]');
        if (meta) {
            meta.setAttribute('content', theme.colors['--bg-primary']);
        }
        
        this.dispatchThemeChange();
    }
    
    dispatchThemeChange() {
        const event = new CustomEvent('themeChanged', { detail: { theme: this.currentTheme } });
        document.dispatchEvent(event);
    }
    
    getCurrentTheme() {
        return this.currentTheme;
    }
    
    getAvailableThemes() {
        return Object.keys(this.themes).map(key => ({
            id: key,
            name: this.themes[key].name,
            icon: this.themes[key].icon
        }));
    }
    
    cycleTheme() {
        const themes = Object.keys(this.themes);
        const currentIndex = themes.indexOf(this.currentTheme);
        const nextIndex = (currentIndex + 1) % themes.length;
        this.applyTheme(themes[nextIndex]);
    }
}

window.ThemeManager = ThemeManager;
JS_EOF

# ============================================================
# 3. Notification System
# ============================================================
cat > "$STATIC_DIR/notifications.js" << 'JS_EOF'
/**
 * SwarmIA - Notification System
 * Notificaciones en tiempo real con diferentes tipos
 */
class NotificationSystem {
    constructor() {
        this.container = null;
        this.defaultDuration = 5000;
        this.init();
    }
    
    init() {
        this.createContainer();
        this.injectStyles();
    }
    
    createContainer() {
        this.container = document.createElement('div');
        this.container.id = 'swarmia-notifications';
        this.container.className = 'notification-container';
        document.body.appendChild(this.container);
    }
    
    injectStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .notification-container {
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 10000;
                display: flex;
                flex-direction: column;
                gap: 12px;
                max-width: 380px;
            }
            
            .notification {
                background: var(--bg-secondary);
                border: 1px solid var(--border);
                border-radius: 12px;
                padding: 14px 16px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                animation: slideInRight 0.3s ease;
                display: flex;
                align-items: flex-start;
                gap: 12px;
            }
            
            .notification-icon {
                font-size: 20px;
                flex-shrink: 0;
            }
            
            .notification-content {
                flex: 1;
            }
            
            .notification-title {
                font-weight: 600;
                margin-bottom: 4px;
                color: var(--text-primary);
            }
            
            .notification-message {
                font-size: 13px;
                color: var(--text-secondary);
                line-height: 1.4;
            }
            
            .notification-close {
                background: none;
                border: none;
                color: var(--text-secondary);
                cursor: pointer;
                font-size: 16px;
                padding: 4px;
                border-radius: 4px;
                line-height: 1;
                flex-shrink: 0;
            }
            
            .notification-close:hover {
                background: rgba(255,255,255,0.1);
                color: var(--text-primary);
            }
            
            .notification.success { border-left: 3px solid #10b981; }
            .notification.error { border-left: 3px solid #ef4444; }
            .notification.warning { border-left: 3px solid #f59e0b; }
            .notification.info { border-left: 3px solid #3b82f6; }
            
            @keyframes slideInRight {
                from {
                    transform: translateX(100%);
                    opacity: 0;
                }
                to {
                    transform: translateX(0);
                    opacity: 1;
                }
            }
            
            @keyframes slideOutRight {
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
    
    show(title, message, type = 'info', duration = null) {
        const id = `notif-${Date.now()}-${Math.random().toString(36).substr(2, 6)}`;
        const durationMs = duration !== null ? duration : this.defaultDuration;
        
        const icons = {
            success: '✓',
            error: '✗',
            warning: '⚠',
            info: 'ℹ'
        };
        
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.id = id;
        notification.innerHTML = `
            <div class="notification-icon">${icons[type] || icons.info}</div>
            <div class="notification-content">
                <div class="notification-title">${this.escapeHtml(title)}</div>
                <div class="notification-message">${this.escapeHtml(message)}</div>
            </div>
            <button class="notification-close" onclick="window.notificationSystem?.remove('${id}')">×</button>
        `;
        
        this.container.appendChild(notification);
        
        if (durationMs > 0) {
            setTimeout(() => this.remove(id), durationMs);
        }
        
        return id;
    }
    
    success(title, message, duration = null) {
        return this.show(title, message, 'success', duration);
    }
    
    error(title, message, duration = null) {
        return this.show(title, message, 'error', duration);
    }
    
    warning(title, message, duration = null) {
        return this.show(title, message, 'warning', duration);
    }
    
    info(title, message, duration = null) {
        return this.show(title, message, 'info', duration);
    }
    
    remove(id) {
        const element = document.getElementById(id);
        if (!element) return;
        
        element.style.animation = 'slideOutRight 0.3s ease forwards';
        setTimeout(() => {
            if (element.parentNode) element.remove();
        }, 300);
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

window.NotificationSystem = NotificationSystem;
JS_EOF

# ============================================================
# 4. Voice Commands
# ============================================================
cat > "$STATIC_DIR/voice_commands.js" << 'JS_EOF'
/**
 * SwarmIA - Voice Command System
 * Reconocimiento de voz para comandos
 */
class VoiceCommandSystem {
    constructor() {
        this.recognition = null;
        this.isListening = false;
        this.commands = new Map();
        this.supported = 'webkitSpeechRecognition' in window || 'SpeechRecognition' in window;
        this.init();
    }
    
    init() {
        if (!this.supported) {
            console.warn('Voice recognition not supported');
            return;
        }
        
        this.setupDefaultCommands();
        this.createVoiceButton();
    }
    
    setupDefaultCommands() {
        this.registerCommand('hola', () => {
            window.dashboard?.addSystemMessage('¡Hola! ¿En qué puedo ayudarte?');
        });
        
        this.registerCommand('hora', () => {
            const now = new Date();
            const time = now.toLocaleTimeString();
            window.dashboard?.addSystemMessage(`La hora actual es: ${time}`);
        });
        
        this.registerCommand('fecha', () => {
            const now = new Date();
            const date = now.toLocaleDateString();
            window.dashboard?.addSystemMessage(`Hoy es: ${date}`);
        });
        
        this.registerCommand('estado', () => {
            window.dashboard?.addSystemMessage('El sistema está funcionando correctamente.');
        });
        
        this.registerCommand('ayuda', () => {
            const commands = Array.from(this.commands.keys()).join(', ');
            window.dashboard?.addSystemMessage(`Comandos disponibles: ${commands}`);
        });
        
        this.registerCommand('limpiar', () => {
            window.dashboard?.clearChat();
        });
    }
    
    registerCommand(phrase, callback) {
        this.commands.set(phrase.toLowerCase(), callback);
    }
    
    createVoiceButton() {
        const style = document.createElement('style');
        style.textContent = `
            .voice-button {
                padding: 8px 12px;
                background: var(--primary);
                border: none;
                border-radius: 8px;
                color: white;
                cursor: pointer;
                font-size: 18px;
                transition: all 0.2s;
                margin-right: 8px;
            }
            .voice-button:hover { opacity: 0.9; transform: scale(1.02); }
            .voice-button.listening {
                background: #ef4444;
                animation: pulse 1s infinite;
            }
            @keyframes pulse {
                0% { opacity: 1; }
                50% { opacity: 0.6; }
                100% { opacity: 1; }
            }
        `;
        document.head.appendChild(style);
        
        const voiceBtn = document.createElement('button');
        voiceBtn.id = 'voiceCommandBtn';
        voiceBtn.className = 'voice-button';
        voiceBtn.innerHTML = '🎤';
        voiceBtn.title = 'Comandos de voz (Ctrl+Shift+V)';
        
        voiceBtn.addEventListener('click', () => this.toggleListening());
        
        const inputContainer = document.querySelector('.chat-input-container');
        if (inputContainer) {
            inputContainer.insertBefore(voiceBtn, inputContainer.firstChild);
        }
    }
    
    toggleListening() {
        if (this.isListening) {
            this.stopListening();
        } else {
            this.startListening();
        }
    }
    
    startListening() {
        if (!this.supported) {
            window.notificationSystem?.error('No soportado', 'Tu navegador no soporta reconocimiento de voz.');
            return;
        }
        
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        this.recognition = new SpeechRecognition();
        this.recognition.lang = 'es-ES';
        this.recognition.interimResults = false;
        
        this.recognition.onstart = () => {
            this.isListening = true;
            const btn = document.getElementById('voiceCommandBtn');
            if (btn) btn.classList.add('listening');
            window.notificationSystem?.info('🎤 Escuchando', 'Di un comando...');
        };
        
        this.recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript.toLowerCase();
            this.processCommand(transcript);
        };
        
        this.recognition.onerror = (event) => {
            console.error('Voice error:', event.error);
            window.notificationSystem?.error('Error', 'No se pudo reconocer el comando.');
        };
        
        this.recognition.onend = () => {
            this.isListening = false;
            const btn = document.getElementById('voiceCommandBtn');
            if (btn) btn.classList.remove('listening');
        };
        
        this.recognition.start();
    }
    
    stopListening() {
        if (this.recognition) {
            this.recognition.stop();
        }
    }
    
    processCommand(transcript) {
        for (const [command, callback] of this.commands) {
            if (transcript.includes(command)) {
                callback();
                return;
            }
        }
        
        // Si no es comando, enviar como mensaje
        const input = document.getElementById('chatInput');
        if (input) {
            input.value = transcript;
            window.dashboard?.sendMessage();
        }
    }
}

window.VoiceCommandSystem = VoiceCommandSystem;
JS_EOF

# ============================================================
# 5. Dashboard Principal Mejorado
# ============================================================
cat > "$STATIC_DIR/dashboard_enhanced.js" << 'JS_EOF'
/**
 * SwarmIA - Enhanced Dashboard
 * Dashboard principal con todas las funcionalidades avanzadas
 */
class SwarmIAEnhancedDashboard {
    constructor() {
        // Elementos DOM
        this.chatMessages = document.getElementById('chatMessages');
        this.chatInput = document.getElementById('chatInput');
        this.sendBtn = document.getElementById('sendButton');
        
        // Estadísticas
        this.startTime = Date.now();
        this.messageCount = 0;
        
        // Sistemas
        this.chatHistory = null;
        this.themeManager = null;
        this.notificationSystem = null;
        this.voiceCommands = null;
        
        this.init();
    }
    
    async init() {
        this.setupEventListeners();
        await this.loadInitialData();
        this.initAdvancedSystems();
        this.startStatsUpdater();
        this.addExportButton();
        this.addThemeSelector();
        
        window.notificationSystem?.success('Dashboard Mejorado', 'Todas las funcionalidades están activas');
    }
    
    initAdvancedSystems() {
        if (window.ChatHistory) {
            this.chatHistory = new window.ChatHistory();
        }
        if (window.ThemeManager) {
            this.themeManager = new window.ThemeManager();
        }
        if (window.NotificationSystem) {
            this.notificationSystem = new window.NotificationSystem();
            window.notificationSystem = this.notificationSystem;
        }
        if (window.VoiceCommandSystem) {
            this.voiceCommands = new window.VoiceCommandSystem();
        }
    }
    
    setupEventListeners() {
        this.sendBtn?.addEventListener('click', () => this.sendMessage());
        this.chatInput?.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        // Atajos de teclado
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.shiftKey) {
                switch(e.key) {
                    case 'T': e.preventDefault(); this.themeManager?.cycleTheme(); break;
                    case 'E': e.preventDefault(); this.exportHistory(); break;
                    case 'V': e.preventDefault(); this.voiceCommands?.toggleListening(); break;
                }
            }
        });
    }
    
    async loadInitialData() {
        try {
            const response = await fetch('/health');
            if (response.ok) {
                this.addSystemMessage('✅ Sistema conectado correctamente');
            } else {
                this.addSystemMessage('⚠️ Error al conectar con el servidor');
            }
        } catch (error) {
            this.addSystemMessage('❌ No se pudo conectar con SwarmIA');
        }
    }
    
    async sendMessage() {
        const message = this.chatInput?.value.trim();
        if (!message) return;
        
        this.setSendingState(true);
        this.chatHistory?.addMessage('user', message);
        this.addMessage('user', 'Tú', message);
        this.chatInput.value = '';
        
        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message })
            });
            
            const data = await response.json();
            this.addMessage('ai', 'SwarmIA', data.response);
            this.chatHistory?.addMessage('ai', data.response);
            this.messageCount++;
            
            this.updateStatsDisplay();
            
        } catch (error) {
            this.addSystemMessage('Error al enviar mensaje');
            this.notificationSystem?.error('Error', 'No se pudo enviar el mensaje');
        } finally {
            this.setSendingState(false);
            this.chatInput?.focus();
        }
    }
    
    addMessage(type, sender, content) {
        if (!this.chatMessages) return;
        
        const div = document.createElement('div');
        div.className = `message ${type}`;
        div.innerHTML = `
            <div class="message-header">
                <strong>${this.escapeHtml(sender)}</strong>
                <span class="message-time">${new Date().toLocaleTimeString()}</span>
            </div>
            <div class="message-content">${this.escapeHtml(content)}</div>
        `;
        
        this.chatMessages.appendChild(div);
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }
    
    addSystemMessage(content) {
        this.addMessage('system', 'Sistema', content);
    }
    
    clearChat() {
        if (this.chatMessages) {
            this.chatMessages.innerHTML = '';
        }
        this.addSystemMessage('Chat limpiado');
    }
    
    exportHistory() {
        if (!this.chatHistory) {
            this.notificationSystem?.warning('No disponible', 'Historial no inicializado');
            return;
        }
        
        const data = this.chatHistory.exportHistory();
        const blob = new Blob([data], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `swarmia_chat_${new Date().toISOString().split('T')[0]}.json`;
        a.click();
        URL.revokeObjectURL(url);
        
        this.notificationSystem?.success('Exportado', 'Historial descargado correctamente');
    }
    
    addExportButton() {
        const header = document.querySelector('.chat-header');
        if (!header) return;
        
        const btn = document.createElement('button');
        btn.className = 'export-btn';
        btn.innerHTML = '📥 Exportar';
        btn.title = 'Exportar historial (Ctrl+Shift+E)';
        btn.addEventListener('click', () => this.exportHistory());
        header.appendChild(btn);
    }
    
    addThemeSelector() {
        const header = document.querySelector('.main-header');
        if (!header || !this.themeManager) return;
        
        const select = document.createElement('select');
        select.className = 'theme-selector';
        select.title = 'Cambiar tema (Ctrl+Shift+T)';
        
        this.themeManager.getAvailableThemes().forEach(theme => {
            const option = document.createElement('option');
            option.value = theme.id;
            option.textContent = `${theme.icon} ${theme.name}`;
            if (theme.id === this.themeManager.getCurrentTheme()) {
                option.selected = true;
            }
            select.appendChild(option);
        });
        
        select.addEventListener('change', (e) => {
            this.themeManager.applyTheme(e.target.value);
        });
        
        header.appendChild(select);
    }
    
    setSendingState(sending) {
        if (this.sendBtn) {
            this.sendBtn.disabled = sending;
            this.sendBtn.textContent = sending ? 'Enviando...' : 'Enviar';
        }
        if (this.chatInput) {
            this.chatInput.disabled = sending;
        }
    }
    
    startStatsUpdater() {
        setInterval(() => this.updateStatsDisplay(), 30000);
        setInterval(() => this.updateUptime(), 1000);
    }
    
    async updateStatsDisplay() {
        try {
            const response = await fetch('/api/stats');
            const stats = await response.json();
            
            const uptimeEl = document.getElementById('uptimeValue');
            const msgsEl = document.getElementById('messageCount');
            
            if (uptimeEl) uptimeEl.textContent = stats.uptime || '00:00:00';
            if (msgsEl) msgsEl.textContent = this.messageCount;
            
        } catch (e) {}
    }
    
    updateUptime() {
        const uptimeMs = Date.now() - this.startTime;
        const hours = Math.floor(uptimeMs / 3600000);
        const minutes = Math.floor((uptimeMs % 3600000) / 60000);
        const seconds = Math.floor((uptimeMs % 60000) / 1000);
        
        const uptimeEl = document.getElementById('uptimeValue');
        if (uptimeEl && !uptimeEl.textContent?.includes(':')) {
            uptimeEl.textContent = `${hours.toString().padStart(2,'0')}:${minutes.toString().padStart(2,'0')}:${seconds.toString().padStart(2,'0')}`;
        }
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Inicialización
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new SwarmIAEnhancedDashboard();
});
JS_EOF

# ============================================================
# 6. Actualizar main.py
# ============================================================
echo -e "${BLUE}[*] Actualizando main.py...${NC}"

cat > "$SWARMIA_DIR/src/core/main.py" << 'PYTHON_EOF'
#!/usr/bin/env python3
"""
SwarmIA - Sistema de Agentes Distribuidos
Dashboard mejorado con historial, temas, notificaciones y comandos de voz
"""

import os
import json
import time
import threading
from datetime import datetime
from flask import Flask, jsonify, request, render_template, send_from_directory

app = Flask(__name__, 
            static_folder='../../static',
            template_folder='../../templates')

# Configuración básica
HOST = os.getenv('SWARMIA_HOST', '0.0.0.0')
PORT = int(os.getenv('SWARMIA_PORT', '8080'))
DEBUG = os.getenv('SWARMIA_DEBUG', 'false').lower() == 'true'

# Estado del sistema
start_time = time.time()
message_count = 0
active_sessions = set()
chat_history = []
history_lock = threading.Lock()

# ============================================================
# Rutas principales
# ============================================================

@app.route('/')
def index():
    """Dashboard principal"""
    return render_template('index.html')

@app.route('/health')
def health():
    """Health check"""
    return jsonify({
        'status': 'healthy',
        'version': '2.0.0',
        'features': ['chat', 'history', 'themes', 'notifications', 'voice'],
        'timestamp': time.time()
    })

@app.route('/api/stats')
def stats():
    """Estadísticas del sistema"""
    uptime = time.time() - start_time
    hours = int(uptime // 3600)
    minutes = int((uptime % 3600) // 60)
    seconds = int(uptime % 60)
    
    with history_lock:
        history_count = len(chat_history)
    
    return jsonify({
        'uptime': f'{hours:02d}:{minutes:02d}:{seconds:02d}',
        'message_count': message_count,
        'active_sessions': len(active_sessions),
        'history_size': history_count,
        'status': 'running',
        'version': '2.0.0'
    })

@app.route('/api/chat', methods=['POST'])
def chat():
    """Endpoint de chat con historial"""
    global message_count
    
    data = request.get_json()
    message = data.get('message', '')
    session_id = request.remote_addr
    
    active_sessions.add(session_id)
    message_count += 1
    
    # Guardar mensaje del usuario
    with history_lock:
        chat_history.append({
            'id': message_count,
            'role': 'user',
            'content': message,
            'timestamp': time.time(),
            'datetime': datetime.now().isoformat(),
            'session': session_id
        })
    
    # Procesar respuesta (simulación - reemplazar con IA real)
    response_text = f"Recibí: '{message}'. Soy SwarmIA v2.0 con dashboard mejorado."
    
    # Guardar respuesta
    with history_lock:
        chat_history.append({
            'id': message_count + 0.5,
            'role': 'ai',
            'content': response_text,
            'timestamp': time.time(),
            'datetime': datetime.now().isoformat(),
            'session': 'swarmia'
        })
    
    return jsonify({
        'response': response_text,
        'message_id': message_count,
        'timestamp': time.time()
    })

@app.route('/api/history', methods=['GET'])
def get_history():
    """Obtener historial de chat"""
    limit = request.args.get('limit', default=50, type=int)
    
    with history_lock:
        history = chat_history[-limit:] if len(chat_history) > limit else chat_history.copy()
    
    return jsonify({
        'history': history,
        'total': len(chat_history),
        'limit': limit
    })

@app.route('/api/features')
def features():
    """Lista de características disponibles"""
    return jsonify({
        'features': {
            'chat': True,
            'history': True,
            'themes': True,
            'notifications': True,
            'voice_commands': True,
            'export_history': True,
            'stats': True
        },
        'version': '2.0.0',
        'status': 'enhanced'
    })

@app.route('/static/<path:path>')
def serve_static(path):
    """Servir archivos estáticos"""
    return send_from_directory(app.static_folder, path)

# ============================================================
# Inicialización
# ============================================================

if __name__ == '__main__':
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                    SwarmIA v2.0 Enhanced                     ║
║                   Sistema de Agentes Distribuidos             ║
╚══════════════════════════════════════════════════════════════╝

🚀 Servidor iniciado en: http://{HOST}:{PORT}
📊 Dashboard: http://{HOST}:{PORT}/
🔧 API Features: http://{HOST}:{PORT}/api/features

✨ Características activas:
   • Chat con historial
   • Temas (Dark/Light/Blue)
   • Notificaciones en tiempo real
   • Comandos de voz
   • Exportación de historial

💡 Atajos de teclado:
   Ctrl+Shift+T - Cambiar tema
   Ctrl+Shift+E - Exportar historial
   Ctrl+Shift+V - Comandos de voz
""")
    app.run(host=HOST, port=PORT, debug=DEBUG)
PYTHON_EOF

# ============================================================
# 7. Actualizar index.html
# ============================================================
echo -e "${BLUE}[*] Actualizando index.html...${NC}"

if [ -f "$TEMPLATES_DIR/index.html" ]; then
    # Crear respaldo
    cp "$TEMPLATES_DIR/index.html" "$TEMPLATES_DIR/index.html.bak"
    
    # Actualizar para cargar scripts mejorados
    sed -i 's|dashboard.js|dashboard_enhanced.js|g' "$TEMPLATES_DIR/index.html" 2>/dev/null || true
    sed -i 's|AI Assistant|SwarmIA Enhanced|g' "$TEMPLATES_DIR/index.html" 2>/dev/null || true
fi

# ============================================================
# 8. Crear archivo de versión
# ============================================================
echo "2.0.0" > "$SWARMIA_DIR/VERSION"
echo "enhanced" > "$SWARMIA_DIR/FEATURES"

# ============================================================
# 9. Reiniciar servicio
# ============================================================
echo -e "${BLUE}[*] Reiniciando SwarmIA...${NC}"

systemctl daemon-reload 2>/dev/null || true
systemctl restart swarmia 2>/dev/null || true

sleep 2

if systemctl is-active --quiet swarmia 2>/dev/null; then
    echo -e "${GREEN}[✓] Servicio reiniciado correctamente${NC}"
else
    echo -e "${YELLOW}[!] Iniciando manualmente...${NC}"
    cd "$SWARMIA_DIR"
    nohup python3 src/core/main.py > /var/log/swarmia.log 2>&1 &
    sleep 2
    if pgrep -f "python3.*main.py" > /dev/null; then
        echo -e "${GREEN}[✓] SwarmIA iniciado manualmente${NC}"
    else
        echo -e "${RED}[!] Error al iniciar SwarmIA${NC}"
    fi
fi

# ============================================================
# 10. Mostrar información final
# ============================================================
IP=$(hostname -I | awk '{print $1}' 2>/dev/null || echo "localhost")

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              DASHBOARD MEJORADO INSTALADO                     ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}✨ Nuevas características:${NC}"
echo
