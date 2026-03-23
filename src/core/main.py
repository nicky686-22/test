#!/usr/bin/env python3
"""
SwarmIA Main Entry Point
Enhanced AI Assistant System
"""

import os
import sys
import json
import logging
import signal
import time
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import FastAPI for web server
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
import uvicorn


# ============================================================
# Configuración
# ============================================================

class Config:
    """Configuración de SwarmIA"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.BASE_DIR = Path(__file__).parent.parent
        self.STATIC_DIR = self.BASE_DIR / "static"
        self.TEMPLATES_DIR = self.BASE_DIR / "templates"
        self.LOGS_DIR = self.BASE_DIR / "logs"
        self.CONFIG_DIR = self.BASE_DIR / "config"
        
        # Crear directorios
        for d in [self.LOGS_DIR, self.CONFIG_DIR, self.STATIC_DIR, self.TEMPLATES_DIR]:
            d.mkdir(parents=True, exist_ok=True)
        
        # Configuración del servidor
        self.SERVER_HOST = os.getenv("SWARMIA_HOST", "0.0.0.0")
        self.SERVER_PORT = int(os.getenv("SWARMIA_PORT", "8080"))
        self.SERVER_DEBUG = os.getenv("SWARMIA_DEBUG", "false").lower() == "true"
        
        # Configuración de la IA
        self.AI_PROVIDER = os.getenv("AI_PROVIDER", "deepseek")
        self.DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
        self.LLAMA_MODEL_PATH = os.getenv("LLAMA_MODEL_PATH", "")
        
        # Configuración de gateways
        self.WHATSAPP_ENABLED = os.getenv("WHATSAPP_ENABLED", "false").lower() == "true"
        self.TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
        
        # Credenciales
        self.ADMIN_USER = os.getenv("ADMIN_USER", "admin")
        self.ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH", "")
    
    def get_local_ip(self) -> str:
        """Obtener IP local"""
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"


# ============================================================
# Logger
# ============================================================

def setup_logger(name: str = "swarmia") -> logging.Logger:
    """Configurar logger"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Crear directorio de logs
    log_dir = Path(__file__).parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    
    # File handler
    file_handler = logging.FileHandler(log_dir / "swarmia.log")
    file_handler.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


# ============================================================
# Agentes Simulados (para pruebas)
# ============================================================

class Supervisor:
    """Supervisor de agentes"""
    
    def __init__(self):
        self.running = False
        self.stats = {"tasks": 0, "completed": 0}
    
    def start(self):
        self.running = True
    
    def stop(self):
        self.running = False
    
    def get_stats(self):
        return self.stats


class ChatAgent:
    """Agente de chat"""
    
    def __init__(self, supervisor, config):
        self.supervisor = supervisor
        self.config = config
        self.running = False
    
    def start(self):
        self.running = True
    
    def stop(self):
        self.running = False
    
    def get_stats(self):
        return {"running": self.running, "messages": 0}


class AggressiveAgent:
    """Agente agresivo"""
    
    def __init__(self, supervisor, config):
        self.supervisor = supervisor
        self.config = config
        self.running = False
    
    def start(self):
        self.running = True
    
    def stop(self):
        self.running = False
    
    def get_stats(self):
        return {"running": self.running, "actions": 0}


class CommunicationGateway:
    """Gateway de comunicación"""
    
    def __init__(self, config):
        self.config = config
        self.running = False
    
    def start(self):
        self.running = True
    
    def stop(self):
        self.running = False
    
    def get_stats(self):
        return {"running": self.running, "whatsapp": False, "telegram": False}


class UpdateChecker:
    """Verificador de actualizaciones"""
    
    def __init__(self, config):
        self.config = config
        self.settings = {"notify_on_update": True}
    
    def check_for_updates(self, force=False):
        return False, {}
    
    def should_check(self):
        return False
    
    def mark_notified(self):
        pass


def create_chat_agent(supervisor, config):
    return ChatAgent(supervisor, config)


def create_aggressive_agent(supervisor, config):
    return AggressiveAgent(supervisor, config)


def setup_communication_gateway(config):
    return CommunicationGateway(config)


def create_update_checker(config):
    return UpdateChecker(config)


# ============================================================
# Aplicación Web
# ============================================================

def create_app(config: Config, supervisor, chat_agent, aggressive_agent, gateway, updater):
    """Crear aplicación FastAPI"""
    
    app = FastAPI(title="SwarmIA API", version="2.0.0")
    
    # Montar archivos estáticos
    if config.STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(config.STATIC_DIR)), name="static")
    
    # Templates
    templates = Jinja2Templates(directory=str(config.TEMPLATES_DIR))
    
    # Estado del sistema
    start_time = datetime.now()
    message_count = 0
    
    # ============================================================
    # Endpoints
    # ============================================================
    
    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        """Dashboard principal"""
        try:
            return templates.TemplateResponse("index.html", {"request": request})
        except:
            # Fallback si no hay template
            return HTMLResponse("""
            <!DOCTYPE html>
            <html>
            <head>
                <title>SwarmIA</title>
                <style>
                    body { font-family: sans-serif; text-align: center; padding: 50px; background: #0f172a; color: white; }
                    h1 { color: #4f46e5; }
                </style>
            </head>
            <body>
                <h1>🚀 SwarmIA</h1>
                <p>Sistema de Agentes Distribuidos</p>
                <p>API funcionando correctamente</p>
            </body>
            </html>
            """)
    
    @app.get("/health")
    async def health():
        """Health check"""
        return {
            "status": "healthy",
            "version": "2.0.0",
            "features": ["chat", "history", "themes", "notifications", "voice"],
            "timestamp": time.time()
        }
    
    @app.get("/api/stats")
    async def stats():
        """Estadísticas del sistema"""
        uptime = datetime.now() - start_time
        hours = uptime.seconds // 3600
        minutes = (uptime.seconds % 3600) // 60
        seconds = uptime.seconds % 60
        
        return {
            "uptime": f"{hours:02d}:{minutes:02d}:{seconds:02d}",
            "message_count": message_count,
            "active_sessions": 0,
            "history_size": 0,
            "status": "running",
            "version": "2.0.0"
        }
    
    @app.post("/api/chat")
    async def chat(request: Request):
        """Endpoint de chat"""
        nonlocal message_count
        
        data = await request.json()
        message = data.get("message", "")
        message_count += 1
        
        # Respuesta simulada
        response_text = f"Recibí: '{message}'. Soy SwarmIA v2.0 con dashboard mejorado."
        
        return {
            "response": response_text,
            "message_id": message_count,
            "timestamp": time.time()
        }
    
    @app.get("/api/features")
    async def features():
        """Lista de características"""
        return {
            "features": {
                "chat": True,
                "history": True,
                "themes": True,
                "notifications": True,
                "voice_commands": True,
                "export_history": True,
                "stats": True
            },
            "version": "2.0.0",
            "status": "enhanced"
        }
    
    return app


# ============================================================
# Clase Principal SwarmIA
# ============================================================

class SwarmIA:
    """Clase principal de SwarmIA"""
    
    def __init__(self):
        self.config = Config()
        self.logger = setup_logger()
        
        # Core components
        self.supervisor = None
        self.chat_agent = None
        self.aggressive_agent = None
        self.gateway = None
        self.web_app = None
        self.updater = None
        
        # State
        self.running = False
        self.start_time = None
        
        # Statistics
        self.stats = {
            "start_time": None,
            "uptime": None,
            "requests_processed": 0,
            "messages_handled": 0,
            "errors": 0
        }
        
        self.logger.info("SwarmIA initialized")
    
    def initialize_components(self):
        """Initialize all SwarmIA components"""
        self.logger.info("Initializing SwarmIA components...")
        
        try:
            # 1. Initialize Supervisor
            self.supervisor = Supervisor()
            self.logger.info("✓ Supervisor initialized")
            
            # 2. Initialize Chat Agent
            self.chat_agent = create_chat_agent(self.supervisor, self.config)
            self.logger.info("✓ Chat Agent initialized")
            
            # 3. Initialize Aggressive Agent
            self.aggressive_agent = create_aggressive_agent(self.supervisor, self.config)
            self.logger.info("✓ Aggressive Agent initialized")
            
            # 4. Initialize Update Checker
            self.updater = create_update_checker(self.config)
            self.logger.info("✓ Update Checker initialized")
            
            # 5. Initialize Communication Gateway
            self.gateway = setup_communication_gateway(self.config)
            self.logger.info("✓ Communication Gateway initialized")
            
            # 6. Initialize Web Application
            self.web_app = create_app(self.config, self.supervisor, self.chat_agent, 
                                       self.aggressive_agent, self.gateway, self.updater)
            self.logger.info("✓ Web Application initialized")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize components: {e}")
            return False
    
    def start(self):
        """Start the SwarmIA system"""
        if self.running:
            self.logger.warning("SwarmIA is already running")
            return False
        
        self.logger.info("🚀 Starting SwarmIA Enhanced AI Assistant...")
        self.start_time = datetime.now()
        self.stats["start_time"] = self.start_time
        
        try:
            if not self.initialize_components():
                raise RuntimeError("Component initialization failed")
            
            self.logger.info("Starting components...")
            
            self.supervisor.start()
            self.chat_agent.start()
            self.aggressive_agent.start()
            self.gateway.start()
            
            self.running = True
            self._display_startup_banner()
            self._start_web_server()
            
            self.logger.info("🎉 SwarmIA started successfully!")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start SwarmIA: {e}")
            self.stats["errors"] += 1
            return False
    
    def _display_startup_banner(self):
        """Display startup banner"""
        local_ip = self.config.get_local_ip()
        port = self.config.SERVER_PORT
        
        banner = f"""
╔══════════════════════════════════════════════════════════════╗
║                   🚀 SwarmIA is Running!                    ║
║          Enhanced AI Assistant System                       ║
╚══════════════════════════════════════════════════════════════╝

📡 ACCESS INFORMATION:
  Local URL:    http://{local_ip}:{port}
  Dashboard:    http://{local_ip}:{port}/
  API Docs:     http://{local_ip}:{port}/docs

🔐 DEFAULT CREDENTIALS:
  Username:     admin
  Password:     admin
  ⚠️  CHANGE PASSWORD ON FIRST LOGIN!

⚙️  SYSTEM STATUS:
  Supervisor:   ✓ Running
  Chat Agent:   ✓ Running  
  Gateway:      ✓ Running
  Web Server:   ✓ Running on port {port}

📊 FEATURES:
  • Chat con historial
  • Temas (Dark/Light/Blue)
  • Notificaciones en tiempo real
  • Comandos de voz
  • Exportación de historial

💡 Keyboard Shortcuts:
  Ctrl+Shift+T - Cambiar tema
  Ctrl+Shift+E - Exportar historial
  Ctrl+Shift+V - Comandos de voz
══════════════════════════════════════════════════════════════
"""
        print(banner)
    
    def _start_web_server(self):
        """Start the web server"""
        import threading
        
        def run_server():
            uvicorn.run(
                self.web_app,
                host=self.config.SERVER_HOST,
                port=self.config.SERVER_PORT,
                log_level="info",
                access_log=True
            )
        
        server_thread = threading.Thread(target=run_server, daemon=True, name="web-server")
        server_thread.start()
        self.logger.info(f"Web server started on {self.config.SERVER_HOST}:{self.config.SERVER_PORT}")
    
    def stop(self):
        """Stop the SwarmIA system"""
        if not self.running:
            return
        
        self.logger.info("🛑 Stopping SwarmIA...")
        
        try:
            if self.gateway:
                self.gateway.stop()
            if self.aggressive_agent:
                self.aggressive_agent.stop()
            if self.chat_agent:
                self.chat_agent.stop()
            if self.supervisor:
                self.supervisor.stop()
            
            if self.start_time:
                uptime = datetime.now() - self.start_time
                self.stats["uptime"] = str(uptime)
            
            self.running = False
            self.logger.info("✅ SwarmIA stopped gracefully")
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
    
    def get_status(self):
        """Get system status"""
        if not self.running:
            return {"status": "stopped", "message": "SwarmIA is not running"}
        
        uptime = datetime.now() - self.start_time
        
        return {
            "status": "running",
            "start_time": self.start_time.isoformat(),
            "uptime": str(uptime),
            "version": "2.0.0"
        }
    
    def run_forever(self):
        """Run SwarmIA forever"""
        if not self.start():
            self.logger.error("Failed to start SwarmIA")
            return 1
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("Keyboard interrupt received")
        finally:
            self.stop()
        
        return 0


# ============================================================
# Main Entry Point
# ============================================================

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="SwarmIA Enhanced AI Assistant")
    parser.add_argument("--version", action="store_true", help="Show version")
    parser.add_argument("--status", action="store_true", help="Show status")
    parser.add_argument("--stop", action="store_true", help="Stop running instance")
    
    args = parser.parse_args()
    
    if args.version:
        print("SwarmIA v2.0.0 - Enhanced AI Assistant")
        print("Features: Chat History, Themes, Notifications, Voice Commands")
        return 0
    
    swarmia = SwarmIA()
    
    if args.status:
        status = swarmia.get_status()
        print(json.dumps(status, indent=2, default=str))
        return 0
    
    return swarmia.run_forever()


if __name__ == "__main__":
    sys.exit(main())
