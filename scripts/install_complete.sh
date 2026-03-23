#!/bin/bash
# SwarmIA Complete Installer - With Dashboard

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
echo "║                 SwarmIA Complete Installer                   ║"
echo "║                 With Dashboard Included                      ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Verificar root
if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}[!] This installer must be run as root${NC}"
    exit 1
fi

echo -e "${BLUE}[*] Starting complete installation...${NC}"

# Configuración
SWARMIA_DIR="/opt/swarmia"
CONFIG_DIR="/etc/swarmia"
LOGS_DIR="/var/log/swarmia"
DATA_DIR="/var/lib/swarmia"
PORT="3000"

# Limpiar instalación anterior PERO mantener directorios
echo -e "${BLUE}[*] Cleaning previous installation...${NC}"
systemctl stop swarmia 2>/dev/null || true

# Crear directorios COMPLETOS (primero)
echo -e "${BLUE}[*] Creating directories...${NC}"
mkdir -p "$SWARMIA_DIR" "$CONFIG_DIR" "$LOGS_DIR" "$DATA_DIR"
mkdir -p "$SWARMIA_DIR/static/css" "$SWARMIA_DIR/static/js" "$SWARMIA_DIR/static/images" "$SWARMIA_DIR/templates"
mkdir -p "$SWARMIA_DIR/src/core"
echo -e "${GREEN}[✓] Directories created${NC}"

# Limpiar contenido pero mantener estructura
rm -rf "$SWARMIA_DIR"/* 2>/dev/null || true

# Instalar dependencias mínimas
echo -e "${BLUE}[*] Installing dependencies...${NC}"
apt-get update > /dev/null 2>&1
apt-get install -y python3 python3-flask python3-requests > /dev/null 2>&1
echo -e "${GREEN}[✓] Dependencies installed${NC}"

# Crear estructura básica de SwarmIA CON DASHBOARD
echo -e "${BLUE}[*] Creating SwarmIA with dashboard...${NC}"

# Crear main.py con dashboard
cat > "$SWARMIA_DIR/src/core/main.py" << 'PYTHON_EOF'
#!/usr/bin/env python3
"""
SwarmIA - AI System with Dashboard
"""

from flask import Flask, jsonify, request, render_template, send_from_directory
import os
import json
import time

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

@app.route('/')
def index():
    """Serve the dashboard"""
    return render_template('index.html', api_url=request.host_url)

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'version': '1.0.0'})

@app.route('/api/stats')
def stats():
    """Get system statistics"""
    uptime = time.time() - start_time
    hours = int(uptime // 3600)
    minutes = int((uptime % 3600) // 60)
    seconds = int(uptime % 60)
    
    return jsonify({
        'uptime': f'{hours:02d}:{minutes:02d}:{seconds:02d}',
        'message_count': message_count,
        'status': 'running',
        'version': '1.0.0'
    })

@app.route('/api/chat', methods=['POST'])
def chat():
    """Chat endpoint"""
    global message_count
    data = request.get_json()
    message = data.get('message', '')
    
    message_count += 1
    
    # Simular procesamiento de IA
    response_text = f"I received your message: '{message}'. This is a response from the {config['ai']['backend']} backend."
    
    return jsonify({
        'response': response_text,
        'ai_backend': config['ai']['backend'],
        'message_id': message_count,
        'timestamp': time.time()
    })

@app.route('/static/<path:path>')
def serve_static(path):
    """Serve static files"""
    return send_from_directory(app.static_folder, path)

if __name__ == '__main__':
    host = config['server']['host']
    port = config['server']['port']
    debug = config['server']['debug']
    
    print(f"SwarmIA starting on http://{host}:{port}")
    print(f"Dashboard available at: http://{host}:{port}/")
    app.run(host=host, port=port, debug=debug)
PYTHON_EOF

chmod +x "$SWARMIA_DIR/src/core/main.py"
echo -e "${GREEN}[✓] Main application created${NC}"

# Crear archivo CSS del dashboard
cat > "$SWARMIA_DIR/static/css/dashboard.css" << 'CSS_EOF'
/* SwarmIA Dashboard Styles */
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

# Crear archivo JavaScript del dashboard
cat > "$SWARMIA_DIR/static/js/dashboard.js" << 'JS_EOF'
// SwarmIA Dashboard JavaScript

class SwarmIADashboard {
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
        
        this.init();
    }
    
    init() {
        this.updateStats();
        this.setupEventListeners();
        this.loadInitialData();
        
        // Actualizar estadísticas cada 30 segundos
        setInterval(() => this.updateStats(), 30000);
        
        // Actualizar tiempo de actividad
        setInterval(() => this.updateUptime(), 1000);
    }
    
    setupEventListeners() {
        this.sendButton.addEventListener('click', () => this.sendMessage());
        this.chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
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
            }
        } catch (error) {
            this.systemStatus.textContent = 'Offline';
            this.systemStatus.style.background = '#ef4444';
            this.addSystemMessage('Unable to connect to SwarmIA API.');
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
            
        } catch (error) {
            this.addSystemMessage('Error: Unable to send message to SwarmIA.');
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
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Inicializar dashboard cuando el DOM
 esté listo
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new SwarmIADashboard();
});
JS_EOF

# Crear archivo HTML del dashboard
cat > "$SWARMIA_DIR/templates/index.html" << 'HTML_EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SwarmIA Dashboard</title>
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
                    <h1>SwarmIA</h1>
                    <p>AI Assistant Dashboard</p>
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
                <div class="stat-value">v1.0.0</div>
                <div class="stat-label">Version</div>
            </div>
        </div>

        <!-- Chat Interface -->
        <section class="chat-section">
            <h2 class="section-title">
                <i class="fas fa-comment-dots"></i>
                Chat with SwarmIA
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
            <p>SwarmIA Dashboard &copy; 2026 | AI Assistant System</p>
            <p>Connected to: <span id="apiEndpoint">{{ api_url }}</span></p>
        </footer>
    </div>

    <script src="/static/js/dashboard.js"></script>
</body>
</html>
HTML_EOF

echo -e "${GREEN}[✓] Dashboard files created${NC}"

# Crear archivo de configuración
echo -e "${BLUE}[*] Creating configuration...${NC}"
cat > "$CONFIG_DIR/config.yaml" << CONFIG_EOF
# SwarmIA Configuration
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
CONFIG_EOF
echo -e "${GREEN}[✓] Configuration created${NC}"

# Crear servicio systemd
echo -e "${BLUE}[*] Creating service...${NC}"
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
echo -e "${GREEN}[✓] Service created${NC}"

# Iniciar servicio
echo -e "${BLUE}[*] Starting SwarmIA...${NC}"
systemctl enable swarmia > /dev/null 2>&1
systemctl start swarmia > /dev/null 2>&1

sleep 2

# Verificar
if systemctl is-active --quiet swarmia; then
    echo -e "${GREEN}[✓] SwarmIA is running${NC}"
else
    # Intentar iniciar manualmente
    echo -e "${YELLOW}[*] Trying manual start...${NC}"
    cd "$SWARMIA_DIR"
    nohup python3 src/core/main.py > "$LOGS_DIR/swarmia.log" 2>&1 &
    sleep 2
    if ps aux | grep -v grep | grep -q "python3.*main.py"; then
        echo -e "${GREEN}[✓] SwarmIA started manually${NC}"
    else
        echo -e "${RED}[!] Failed to start${NC}"
        echo -e "${YELLOW}[*] Check logs: tail -f $LOGS_DIR/swarmia.log${NC}"
    fi
fi

# Mostrar información
IP=$(hostname -I | awk '{print $1}')
echo ""
echo -e "${GREEN}✅ SwarmIA with Dashboard installed successfully!${NC}"
echo ""
echo -e "${CYAN}Dashboard URL:${NC} http://$IP:$PORT/"
echo -e "${CYAN}API Health:${NC} http://$IP:$PORT/health"
echo -e "${CYAN}API Chat:${NC} POST http://$IP:$PORT/api/chat"
echo ""
echo -e "${GREEN}══════════════════════════════════════════════════════════════${NC}"
