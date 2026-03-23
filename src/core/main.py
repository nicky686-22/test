#!/usr/bin/env python3
"""
SwarmIA Main Entry Point - Orquestador Principal
Inicia todos los componentes y el dashboard
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

# Add project root to path (2 niveles arriba porque estamos en src/core/)
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import uvicorn

# Importar componentes REALES (usando rutas desde la raíz)
from src.core.config import Config
from src.core.supervisor import create_supervisor
from src.agents.chat import create_chat_agent
from src.agents.aggressive import create_aggressive_agent
from src.gateway.communication import setup_communication_gateway
from src.ui.server import app



# ============================================================
# Logger
# ============================================================

def setup_logger(name: str = "swarmia") -> logging.Logger:
    """Configurar logger"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Crear directorio de logs
    log_dir = project_root / "logs"
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
# Clase Principal SwarmIA
# ============================================================

class SwarmIA:
    """Orquestador principal de SwarmIA"""
    
    def __init__(self):
        self.config = Config()
        self.logger = setup_logger()
        
        # Componentes reales
        self.supervisor = None
        self.chat_agent = None
        self.aggressive_agent = None
        self.gateway = None
        
        # Estado
        self.running = False
        self.start_time = None
        
        # Estadísticas
        self.stats = {
            "start_time": None,
            "uptime": None,
            "errors": 0
        }
        
        self.logger.info("SwarmIA orquestador inicializado")
    
    def initialize_components(self):
        """Inicializar todos los componentes de SwarmIA"""
        self.logger.info("Inicializando componentes de SwarmIA...")
        
        try:
            # 1. Inicializar Supervisor (gestor de tareas)
            self.supervisor = create_supervisor(self.config)
            self.logger.info("✓ Supervisor inicializado")
            
            # 2. Inicializar Chat Agent (IA conversacional)
            self.chat_agent = create_chat_agent(self.supervisor, self.config)
            self.logger.info("✓ Chat Agent inicializado")
            
            # 3. Inicializar Aggressive Agent (pentesting)
            self.aggressive_agent = create_aggressive_agent(self.supervisor, self.config)
            self.logger.info("✓ Aggressive Agent inicializado")
            
            # 4. Inicializar Communication Gateway (Telegram/WhatsApp)
            self.gateway = setup_communication_gateway(self.config)
            self.logger.info("✓ Communication Gateway inicializado")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error inicializando componentes: {e}")
            return False
    
    def start(self):
        """Iniciar el sistema SwarmIA"""
        if self.running:
            self.logger.warning("SwarmIA ya está en ejecución")
            return False
        
        self.logger.info("🚀 Iniciando SwarmIA...")
        self.start_time = datetime.now()
        self.stats["start_time"] = self.start_time
        
        try:
            # Inicializar componentes
            if not self.initialize_components():
                raise RuntimeError("Falló la inicialización de componentes")
            
            self.logger.info("Iniciando componentes...")
            
            # Iniciar cada componente
            self.supervisor.start()
            self.logger.info("✓ Supervisor iniciado")
            
            self.chat_agent.start()
            self.logger.info("✓ Chat Agent iniciado")
            
            self.aggressive_agent.start()
            self.logger.info("✓ Aggressive Agent iniciado")
            
            self.gateway.start()
            self.logger.info("✓ Communication Gateway iniciado")
            
            self.running = True
            
            # Mostrar banner
            self._display_startup_banner()
            
            # Iniciar servidor web (dashboard)
            self._start_web_server()
            
            self.logger.info("🎉 SwarmIA iniciado correctamente!")
            return True
            
        except Exception as e:
            self.logger.error(f"Error iniciando SwarmIA: {e}")
            self.stats["errors"] += 1
            return False
    
    def _display_startup_banner(self):
        """Mostrar banner de inicio"""
        local_ip = self.config.get_local_ip()
        port = self.config.SERVER_PORT
        
        banner = f"""
╔══════════════════════════════════════════════════════════════╗
║                   🚀 SwarmIA is Running!                    ║
║          Sistema de Asistentes IA Distribuidos              ║
╚══════════════════════════════════════════════════════════════╝

📡 ACCESO:
  Dashboard:    http://{local_ip}:{port}
  Login:        http://{local_ip}:{port}/login
  API Docs:     http://{local_ip}:{port}/api/docs

🔑 CREDENCIALES POR DEFECTO:
  Usuario:      admin
  Contraseña:   admin
  ⚠️  CAMBIAR EN EL PRIMER ACCESO!

⚙️  COMPONENTES ACTIVOS:
  Supervisor:   ✓ Activo
  Chat Agent:   ✓ Activo
  Aggressive:   ✓ Activo
  Gateway:      ✓ Activo
  Dashboard:    ✓ Activo en puerto {port}

📊 CARACTERÍSTICAS:
  • Chat con IA (DeepSeek/Llama)
  • WhatsApp y Telegram integrados
  • Sistema Anti-Hacking
  • Dashboard completo con menú lateral
  • Gestión de tareas y agentes

💡 ATAJOS DE TECLADO:
  Ctrl+Shift+T - Cambiar tema
  Ctrl+Shift+E - Exportar historial
  Ctrl+Shift+V - Comandos de voz
══════════════════════════════════════════════════════════════
"""
        print(banner)
    
    def _start_web_server(self):
        """Iniciar el servidor web (dashboard)"""
        import threading
        
        def run_server():
            # Usar la app importada desde server.py
            uvicorn.run(
                app,  # <--- App completa de server.py
                host=self.config.SERVER_HOST,
                port=self.config.SERVER_PORT,
                log_level="info",
                access_log=True
            )
        
        server_thread = threading.Thread(target=run_server, daemon=True, name="web-server")
        server_thread.start()
        self.logger.info(f"Servidor web iniciado en {self.config.SERVER_HOST}:{self.config.SERVER_PORT}")
    
    def stop(self):
        """Detener el sistema SwarmIA"""
        if not self.running:
            return
        
        self.logger.info("🛑 Deteniendo SwarmIA...")
        
        try:
            if self.gateway:
                self.gateway.stop()
                self.logger.info("✓ Gateway detenido")
            
            if self.aggressive_agent:
                self.aggressive_agent.stop()
                self.logger.info("✓ Aggressive Agent detenido")
            
            if self.chat_agent:
                self.chat_agent.stop()
                self.logger.info("✓ Chat Agent detenido")
            
            if self.supervisor:
                self.supervisor.stop()
                self.logger.info("✓ Supervisor detenido")
            
            if self.start_time:
                uptime = datetime.now() - self.start_time
                self.stats["uptime"] = str(uptime)
            
            self.running = False
            self.logger.info("✅ SwarmIA detenido correctamente")
            
        except Exception as e:
            self.logger.error(f"Error durante el apagado: {e}")
    
    def get_status(self) -> Dict:
        """Obtener estado del sistema"""
        if not self.running:
            return {"status": "stopped", "message": "SwarmIA no está corriendo"}
        
        uptime = datetime.now() - self.start_time
        
        # Obtener estadísticas de los componentes
        supervisor_stats = self.supervisor.get_stats() if self.supervisor else {}
        chat_stats = self.chat_agent.get_stats() if self.chat_agent else {}
        gateway_stats = self.gateway.get_stats() if self.gateway else {}
        
        return {
            "status": "running",
            "start_time": self.start_time.isoformat(),
            "uptime": str(uptime),
            "version": "2.0.0",
            "components": {
                "supervisor": supervisor_stats,
                "chat_agent": chat_stats,
                "gateway": gateway_stats
            },
            "stats": self.stats
        }
    
    def run_forever(self) -> int:
        """Ejecutar SwarmIA indefinidamente"""
        if not self.start():
            self.logger.error("Error al iniciar SwarmIA")
            return 1
        
        try:
            # Mantener el hilo principal vivo
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("Interrupción de teclado recibida")
        finally:
            self.stop()
        
        return 0


# ============================================================
# Main Entry Point
# ============================================================

def main():
    """Punto de entrada principal"""
    parser = argparse.ArgumentParser(description="SwarmIA - Sistema de Asistentes IA Distribuidos")
    parser.add_argument("--version", action="store_true", help="Mostrar versión")
    parser.add_argument("--status", action="store_true", help="Mostrar estado del sistema")
    parser.add_argument("--stop", action="store_true", help="Detener instancia en ejecución")
    parser.add_argument("--debug", action="store_true", help="Modo debug")
    
    args = parser.parse_args()
    
    if args.version:
        print("SwarmIA v2.0.0 - Sistema de Asistentes IA Distribuidos")
        print("Características: Chat IA, WhatsApp, Telegram, Anti-Hacking, Dashboard")
        return 0
    
    # Configurar modo debug
    if args.debug:
        os.environ["SWARMIA_DEBUG"] = "true"
    
    swarmia = SwarmIA()
    
    if args.status:
        status = swarmia.get_status()
        print(json.dumps(status, indent=2, default=str))
        return 0
    
    # Ejecutar normalmente
    return swarmia.run_forever()


if __name__ == "__main__":
    sys.exit(main())
