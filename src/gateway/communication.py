#!/usr/bin/env python3
"""
SwarmIA Communication Gateway
Maneja comunicación con WhatsApp, Telegram y otros canales
Integrado con sistema anti-hacking y comandos remotos
"""

import os
import sys
import time
import json
import logging
import threading
import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

# Import config and supervisor
try:
    from src.core.config import Config
    from src.core.supervisor import create_supervisor, AttackType, ThreatLevel
except ImportError:
    from core.config import Config
    from core.supervisor import create_supervisor, AttackType, ThreatLevel


# ============================================================
# Enums and Data Classes
# ============================================================

class MessagePlatform(Enum):
    """Plataformas de mensajería soportadas"""
    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"
    DASHBOARD = "dashboard"
    CLI = "cli"
    WEBHOOK = "webhook"


@dataclass
class Message:
    """Mensaje en el sistema"""
    id: str
    platform: MessagePlatform
    sender: str
    text: str
    timestamp: datetime = field(default_factory=datetime.now)
    recipient: Optional[str] = None
    message_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_command: bool = False
    command_response: Optional[str] = None


# ============================================================
# Abstract Handlers
# ============================================================

class MessageHandler(ABC):
    """Clase base para handlers de mensajería"""
    
    def __init__(self, config: Config, gateway: 'CommunicationGateway'):
        self.config = config
        self.gateway = gateway
        self.logger = logging.getLogger(f"swarmia.{self.__class__.__name__}")
        self.running = False
        self._thread = None
        self.allowed_users = set()
    
    @abstractmethod
    def start(self):
        """Iniciar handler"""
        pass
    
    @abstractmethod
    def stop(self):
        """Detener handler"""
        pass
    
    @abstractmethod
    def send_message(self, recipient: str, text: str) -> bool:
        """Enviar mensaje"""
        pass
    
    def receive_message(self, sender: str, text: str, platform: str, 
                        message_id: Optional[str] = None, **kwargs):
        """Recibir mensaje (llamado por el handler)"""
        # Verificar si es un comando
        is_command = text.strip().startswith('/') or text.strip().startswith('!')
        
        message = Message(
            id=f"{platform}_{message_id or int(time.time())}",
            platform=MessagePlatform(platform),
            sender=sender,
            text=text,
            message_id=message_id,
            metadata=kwargs,
            is_command=is_command
        )
        self.gateway.on_message_received(message)
    
    def is_user_allowed(self, user_id: str) -> bool:
        """Verificar si el usuario está permitido"""
        if not self.allowed_users:
            return True
        return user_id in self.allowed_users


class WhatsAppHandler(MessageHandler):
    """Handler para WhatsApp usando webhook"""
    
    def __init__(self, config: Config, gateway: 'CommunicationGateway'):
        super().__init__(config, gateway)
        self.webhook_url = None
        self.session_file = config.WHATSAPP_SESSION_FILE if config else "whatsapp_session.json"
        
        # Cargar usuarios permitidos
        allowed = os.getenv("WHATSAPP_ALLOWED_NUMBERS", "")
        if allowed:
            self.allowed_users = set(allowed.split(','))
    
    def start(self):
        """Iniciar handler de WhatsApp"""
        if not self.config or not self.config.WHATSAPP_ENABLED:
            self.logger.info("Handler de WhatsApp desactivado (no configurado)")
            return
        
        self.running = True
        self.logger.info("Handler de WhatsApp iniciado (modo webhook)")
        self.logger.info(f"Usuarios permitidos: {len(self.allowed_users)} números")
    
    def stop(self):
        """Detener handler de WhatsApp"""
        self.running = False
        self.logger.info("Handler de WhatsApp detenido")
    
    def send_message(self, recipient: str, text: str) -> bool:
        """Enviar mensaje por WhatsApp"""
        try:
            self.logger.info(f"[WhatsApp] Enviando a {recipient}: {text[:50]}...")
            # Aquí iría la lógica real de WhatsApp
            return True
        except Exception as e:
            self.logger.error(f"Error enviando WhatsApp: {e}")
            return False
    
    def handle_webhook(self, request_data: Dict):
        """Procesar webhook de WhatsApp"""
        try:
            sender = request_data.get('from', 'unknown')
            text = request_data.get('text', '')
            message_id = request_data.get('id')
            
            if text:
                # Verificar si el usuario está permitido
                if not self.is_user_allowed(sender):
                    self.logger.warning(f"Usuario WhatsApp no autorizado: {sender}")
                    return False
                
                self.receive_message(sender, text, 'whatsapp', message_id, 
                                     raw_data=request_data)
                return True
        except Exception as e:
            self.logger.error(f"Error en webhook de WhatsApp: {e}")
        return False


class TelegramHandler(MessageHandler):
    """Handler para Telegram usando python-telegram-bot"""
    
    def __init__(self, config: Config, gateway: 'CommunicationGateway'):
        super().__init__(config, gateway)
        self.bot = None
        self.application = None
        self._loop = None
        
        # Cargar usuarios permitidos
        allowed = os.getenv("TELEGRAM_ALLOWED_USERS", "")
        if allowed:
            self.allowed_users = set(allowed.split(','))
        
        # Cargar administradores (reciben notificaciones de seguridad)
        self.admin_ids = set(os.getenv("TELEGRAM_ADMIN_IDS", "").split(',')) if os.getenv("TELEGRAM_ADMIN_IDS") else set()
    
    def start(self):
        """Iniciar bot de Telegram en hilo separado"""
        if not self.config or not self.config.TELEGRAM_ENABLED:
            self.logger.info("Handler de Telegram desactivado (no configurado)")
            return
        
        if not self.config.TELEGRAM_BOT_TOKEN:
            self.logger.error("Token de bot de Telegram no configurado")
            return
        
        try:
            from telegram.ext import Application, CommandHandler, MessageHandler, filters
            
            # Crear aplicación
            self.application = Application.builder().token(self.config.TELEGRAM_BOT_TOKEN).build()
            
            # Registrar handlers
            self.application.add_handler(CommandHandler("start", self._handle_start))
            self.application.add_handler(CommandHandler("help", self._handle_help))
            self.application.add_handler(CommandHandler("status", self._handle_command_wrapper))
            self.application.add_handler(CommandHandler("install", self._handle_command_wrapper))
            self.application.add_handler(CommandHandler("update", self._handle_command_wrapper))
            self.application.add_handler(CommandHandler("restart", self._handle_command_wrapper))
            self.application.add_handler(CommandHandler("block_ip", self._handle_command_wrapper))
            self.application.add_handler(CommandHandler("unblock_ip", self._handle_command_wrapper))
            self.application.add_handler(CommandHandler("scan", self._handle_command_wrapper))
            self.application.add_handler(CommandHandler("info", self._handle_command_wrapper))
            self.application.add_handler(CommandHandler("whois", self._handle_command_wrapper))
            self.application.add_handler(CommandHandler("uptime", self._handle_command_wrapper))
            self.application.add_handler(CommandHandler("logs", self._handle_command_wrapper))
            self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message))
            
            # Iniciar en hilo separado
            self._thread = threading.Thread(target=self._run_bot, daemon=True)
            self._thread.start()
            
            self.running = True
            self.logger.info("Handler de Telegram iniciado correctamente")
            self.logger.info(f"Usuarios permitidos: {len(self.allowed_users)}")
            self.logger.info(f"Administradores: {len(self.admin_ids)}")
            
        except ImportError:
            self.logger.error("python-telegram-bot no instalado. Ejecuta: pip install python-telegram-bot")
        except Exception as e:
            self.logger.error(f"Error al iniciar handler de Telegram: {e}")
    
    def _run_bot(self):
        """Ejecutar el bot en un hilo separado"""
        try:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self.application.run_polling(allowed_updates=["message"])
        except Exception as e:
            self.logger.error(f"Error en el bucle del bot: {e}")
    
    async def _handle_command_wrapper(self, update, context):
        """Wrapper para manejar comandos a través del supervisor"""
        user_id = str(update.effective_user.id)
        
        if not self.is_user_allowed(user_id):
            await update.message.reply_text("⚠️ No estás autorizado para usar este bot.")
            return
        
        # Obtener el comando y argumentos
        command = update.message.text
        # Eliminar el slash y obtener comando y args
        parts = command[1:].split()
        cmd = parts[0] if parts else ""
        args = parts[1:] if len(parts) > 1 else []
        
        # Construir el comando completo
        full_command = f"{cmd} {' '.join(args)}".strip()
        
        # Procesar a través del supervisor
        response = self.gateway.supervisor.process_remote_command(full_command, user_id, "telegram")
        
        # Enviar respuesta
        await update.message.reply_text(response, parse_mode="Markdown")
    
    async def _handle_start(self, update, context):
        """Manejar comando /start"""
        user_id = str(update.effective_user.id)
        
        if not self.is_user_allowed(user_id):
            await update.message.reply_text("⚠️ No estás autorizado para usar este bot.")
            return
        
        welcome_text = """
🤖 *Bienvenido a SwarmIA!*

Soy tu asistente de IA mejorado con sistema anti-hacking.

✨ *Características:*
• Procesamiento por prioridades
• WhatsApp y Telegram integrados
• DeepSeek API y Llama local
• 🛡️ *Sistema Anti-Hacking activo*
• Comandos remotos para administración

📖 *Comandos disponibles:*
`/status` - Estado del sistema
`/install <paquete>` - Instalar paquete Python
`/update` - Actualizar SwarmIA
`/restart` - Reiniciar SwarmIA
`/block_ip <ip>` - Bloquear IP
`/unblock_ip <ip>` - Desbloquear IP
`/scan [ip]` - Escanear puertos
`/info [ip]` - Información de IP
`/whois <ip>` - WHOIS de IP
`/uptime` - Tiempo de actividad
`/logs [n]` - Últimos n logs
`/help` - Esta ayuda

Escribe `/help` para más información.
"""
        await update.message.reply_text(welcome_text, parse_mode="Markdown")
    
    async def _handle_help(self, update, context):
        """Manejar comando /help"""
        user_id = str(update.effective_user.id)
        
        if not self.is_user_allowed(user_id):
            await update.message.reply_text("⚠️ No estás autorizado para usar este bot.")
            return
        
        help_text = """
🆘 *Comandos de SwarmIA*

*Comandos de sistema:*
`/status` - Estado del sistema y estadísticas
`/uptime` - Tiempo de actividad
`/logs [n]` - Últimos n logs (default 20)

*Comandos de administración:*
`/install <paquete>` - Instalar paquete Python
`/update` - Actualizar SwarmIA desde Git
`/restart` - Reiniciar SwarmIA

*Comandos de seguridad:*
`/block_ip <ip>` - Bloquear una IP
`/unblock_ip <ip>` - Desbloquear una IP
`/scan [ip]` - Escanear puertos abiertos
`/info [ip]` - Geolocalización de IP
`/whois <ip>` - Información WHOIS

*Ejemplos:*
`/install requests`
`/block_ip 192.168.1.100`
`/scan 8.8.8.8`
`/info 1.1.1.1`

*Nota:* Todos los comandos requieren autorización previa.
"""
        await update.message.reply_text(help_text, parse_mode="Markdown")
    
    async def _handle_message(self, update, context):
        """Manejar mensajes entrantes (no comandos)"""
        user_id = str(update.effective_user.id)
        username = update.effective_user.username or update.effective_user.first_name
        text = update.message.text
        
        # Verificar autorización
        if not self.is_user_allowed(user_id):
            await update.message.reply_text("⚠️ No estás autorizado para usar este bot.")
            return
        
        # Verificar si es un ataque (detección básica)
        self._check_for_attack_in_message(text, user_id)
        
        # Enviar al gateway
        self.receive_message(
            sender=user_id,
            text=text,
            platform='telegram',
            message_id=str(update.message.message_id),
            username=username,
            chat_id=update.effective_chat.id
        )
        
        # Confirmar recepción
        await update.message.reply_text(
            "✅ Mensaje recibido con *prioridad CRÍTICA*.\n"
            "Un agente responderá en breve...",
            parse_mode="Markdown"
        )
    
    def _check_for_attack_in_message(self, text: str, user_id: str):
        """Verificar si el mensaje contiene indicadores de ataque"""
        # Palabras clave sospechosas
        suspicious_patterns = [
            " UNION SELECT ", "'; DROP TABLE", "xp_cmdshell", "../", "..\\",
            "<?php", "eval(", "base64_decode", "system(", "exec(",
            "<script", "onerror=", "onload=", "javascript:"
        ]
        
        for pattern in suspicious_patterns:
            if pattern.lower() in text.lower():
                self.gateway.supervisor._detect_attack(
                    source_ip=user_id,
                    attack_type=AttackType.SQL_INJECTION,
                    details={"message": text[:200], "pattern": pattern},
                    threat_level=ThreatLevel.MEDIUM
                )
                break
    
    def send_message(self, recipient: str, text: str) -> bool:
        """Enviar mensaje por Telegram"""
        if not self.application or not self.running:
            self.logger.warning("Bot de Telegram no disponible")
            return False
        
        try:
            if self._loop and self._loop.is_running():
                future = asyncio.run_coroutine_threadsafe(
                    self._async_send_message(recipient, text),
                    self._loop
                )
                future.result(timeout=10)
                return True
            else:
                asyncio.run(self._async_send_message(recipient, text))
                return True
        except Exception as e:
            self.logger.error(f"Error enviando mensaje Telegram: {e}")
            return False
    
    async def _async_send_message(self, chat_id: str, text: str):
        """Método asíncrono para enviar mensaje"""
        try:
            await self.application.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode="Markdown"
            )
        except Exception as e:
            self.logger.error(f"Error en envío asíncrono: {e}")
            raise
    
    def send_notification_to_admins(self, message: str):
        """Enviar notificación a todos los administradores"""
        for admin_id in self.admin_ids:
            if admin_id.strip():
                self.send_message(admin_id.strip(), message)
    
    def stop(self):
        """Detener bot de Telegram"""
        self.running = False
        if self.application:
            try:
                if self._loop:
                    self._loop.call_soon_threadsafe(self.application.stop)
                else:
                    self.application.stop()
            except Exception as e:
                self.logger.error(f"Error al detener bot: {e}")
            self.application = None
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
        
        self.logger.info("Handler de Telegram detenido")


# ============================================================
# Mock Handlers for Development
# ============================================================

class MockWhatsAppHandler(WhatsAppHandler):
    """Mock handler para WhatsApp en desarrollo"""
    
    def start(self):
        self.logger.info("[MOCK] Handler de WhatsApp iniciado")
        self.running = True
    
    def send_message(self, recipient: str, text: str) -> bool:
        self.logger.info(f"[MOCK] WhatsApp a {recipient}: {text[:50]}...")
        return True


class MockTelegramHandler(TelegramHandler):
    """Mock handler para Telegram en desarrollo"""
    
    def start(self):
        self.logger.info("[MOCK] Handler de Telegram iniciado")
        self.running = True
    
    def send_message(self, recipient: str, text: str) -> bool:
        self.logger.info(f"[MOCK] Telegram a {recipient}: {text[:50]}...")
        return True


# ============================================================
# Communication Gateway
# ============================================================

class CommunicationGateway:
    """
    Gateway principal de comunicación
    Maneja múltiples plataformas, distribuye mensajes y comandos remotos
    """
    
    def __init__(self, config: Config = None):
        """
        Inicializar gateway
        
        Args:
            config: Configuración de SwarmIA
        """
        self.config = config or Config()
        self.logger = self._setup_logger()
        
        # Supervisor para comandos remotos
        self.supervisor = create_supervisor(self.config)
        
        # Handlers
        self.handlers: Dict[str, MessageHandler] = {}
        
        # Callbacks para mensajes recibidos
        self.message_handlers: List[Callable] = []
        
        # Estadísticas
        self.stats = {
            "messages_received": 0,
            "messages_sent": 0,
            "commands_processed": 0,
            "errors": 0,
            "start_time": None
        }
        
        # Estado
        self.running = False
        
        # Registrar notificaciones del supervisor
        self.supervisor.register_notification_callback(self._on_security_notification, "all")
        
        self.logger.info("Gateway de comunicación inicializado")
    
    def _setup_logger(self) -> logging.Logger:
        """Configurar logger"""
        logger = logging.getLogger("swarmia.gateway")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _on_security_notification(self, message: str, channel: str):
        """
        Callback para notificaciones de seguridad del supervisor
        
        Args:
            message: Mensaje de notificación
            channel: Canal de destino ("telegram", "whatsapp", "all")
        """
        if channel == "telegram" or channel == "all":
            handler = self.handlers.get("telegram")
            if handler:
                handler.send_notification_to_admins(message)
        
        if channel == "whatsapp" or channel == "all":
            handler = self.handlers.get("whatsapp")
            if handler:
                # Enviar a administradores de WhatsApp
                admins = os.getenv("WHATSAPP_ADMIN_NUMBERS", "").split(",")
                for admin in admins:
                    if admin.strip():
                        handler.send_message(admin.strip(), message)
    
    def register_handler(self, platform: str, handler: MessageHandler):
        """Registrar un handler para una plataforma"""
        self.handlers[platform] = handler
        self.logger.info(f"Handler registrado para plataforma: {platform}")
    
    def register_message_handler(self, handler: Callable):
        """Registrar callback para mensajes recibidos"""
        self.message_handlers.append(handler)
        self.logger.debug(f"Handler de mensajes registrado: {handler.__name__}")
    
    def on_message_received(self, message: Message):
        """Procesar mensaje recibido"""
        self.stats["messages_received"] += 1
        
        self.logger.info(f"Mensaje recibido: {message.platform.value} de {message.sender}")
        
        # Si es un comando, procesar inmediatamente
        if message.is_command:
            self.stats["commands_processed"] += 1
            self._process_command(message)
        
        # Notificar a todos los handlers registrados
        for handler in self.message_handlers:
            try:
                handler(message)
            except Exception as e:
                self.logger.error(f"Error en handler de mensaje: {e}")
                self.stats["errors"] += 1
        
        # También enviar al supervisor para procesamiento como tarea
        self._forward_to_supervisor(message)
    
    def _process_command(self, message: Message):
        """
        Procesar un comando remoto
        
        Args:
            message: Mensaje con comando
        """
        command = message.text.strip()
        
        # Remover prefijo si es necesario
        if command.startswith('/'):
            command = command[1:]
        elif command.startswith('!'):
            command = command[1:]
        
        self.logger.info(f"Comando remoto detectado: {command} de {message.sender}")
        
        # Procesar a través del supervisor
        response = self.supervisor.process_remote_command(
            command, 
            message.sender, 
            message.platform.value
        )
        
        # Guardar respuesta en el mensaje
        message.command_response = response
        
        # Enviar respuesta de vuelta al usuario
        handler = self.handlers.get(message.platform.value)
        if handler:
            handler.send_message(message.sender, response)
    
    def _forward_to_supervisor(self, message: Message):
        """
        Enviar mensaje al supervisor para procesamiento como tarea
        
        Args:
            message: Mensaje recibido
        """
        try:
            # Crear tarea con prioridad CRÍTICA
            task_id = self.supervisor.create_task(
                task_type="process_message",
                data={
                    "platform": message.platform.value,
                    "sender": message.sender,
                    "text": message.text,
                    "message_id": message.message_id,
                    "metadata": message.metadata
                },
                priority=TaskPriority.CRITICAL,
                source="gateway"
            )
            
            self.logger.debug(f"Mensaje enviado al supervisor: task_id={task_id}")
            
        except Exception as e:
            self.logger.error(f"Error enviando mensaje al supervisor: {e}")
    
    def send_message(self, platform: str, recipient: str, text: str) -> bool:
        """
        Enviar mensaje a través de una plataforma
        
        Args:
            platform: Plataforma (telegram, whatsapp)
            recipient: ID del destinatario
            text: Texto del mensaje
        
        Returns:
            True si se envió correctamente
        """
        handler = self.handlers.get(platform.lower())
        if not handler:
            self.logger.error(f"No hay handler para plataforma: {platform}")
            return False
        
        try:
            success = handler.send_message(recipient, text)
            if success:
                self.stats["messages_sent"] += 1
            return success
        except Exception as e:
            self.logger.error(f"Error en envío a {platform}: {e}")
            self.stats["errors"] += 1
            return False
    
    def start(self) -> bool:
        """Iniciar el gateway, supervisor y todos los handlers"""
        if self.running:
            self.logger.warning("Gateway ya está en ejecución")
            return False
        
        try:
            self.logger.info("Iniciando gateway de comunicación...")
            self.stats["start_time"] = datetime.now()
            
            # Iniciar supervisor primero
            if not self.supervisor.start():
                self.logger.error("Error iniciando supervisor")
                return False
            
            # Configurar handlers con referencia al supervisor
            if self.config.WHATSAPP_ENABLED:
                if self.config.SERVER_DEBUG:
                    handler = MockWhatsAppHandler(self.config, self)
                else:
                    handler = WhatsAppHandler(self.config, self)
                self.register_handler("whatsapp", handler)
                handler.start()
            
            if self.config.TELEGRAM_ENABLED:
                if self.config.SERVER_DEBUG:
                    handler = MockTelegramHandler(self.config, self)
                else:
                    handler = TelegramHandler(self.config, self)
                self.register_handler("telegram", handler)
                handler.start()
            
            self.running = True
            self.logger.info("Gateway de comunicación iniciado correctamente")
            self.logger.info("🛡️ Sistema anti-hacking ACTIVO")
            return True
            
        except Exception as e:
            self.logger.error(f"Error iniciando gateway: {e}")
            return False
    
    def stop(self):
        """Detener el gateway, supervisor y todos los handlers"""
        if not self.running:
            return
        
        self.logger.info("Deteniendo gateway de comunicación...")
        
        for platform, handler in self.handlers.items():
            try:
                handler.stop()
                self.logger.info(f"Handler detenido: {platform}")
            except Exception as e:
                self.logger.error(f"Error deteniendo handler {platform}: {e}")
        
        self.handlers.clear()
        
        # Detener supervisor
        self.supervisor.stop()
        
        self.running = False
        self.logger.info("Gateway de comunicación detenido")
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas del gateway y supervisor"""
        uptime = None
        if self.stats["start_time"]:
            uptime = datetime.now() - self.stats["start_time"]
            uptime = str(uptime).split('.')[0]
        
        supervisor_stats = self.supervisor.get_stats() if self.supervisor else {}
        
        return {
            **self.stats,
            "uptime": uptime,
            "running": self.running,
            "handlers": list(self.handlers.keys()),
            "message_handlers_count": len(self.message_handlers),
            "supervisor": supervisor_stats
        }
    
    def receive_message(self, platform: str, sender: str, text: str,
                        message_id: Optional[str] = None, **kwargs):
        """
        Método público para recibir mensajes desde handlers
        
        Args:
            platform: Plataforma del mensaje
            sender: ID del remitente
            text: Texto del mensaje
            message_id: ID opcional del mensaje
            **kwargs: Metadata adicional
        """
        is_command = text.strip().startswith('/') or text.strip().startswith('!')
        
        message = Message(
            id=f"{platform}_{message_id or int(time.time())}",
            platform=MessagePlatform(platform),
            sender=sender,
            text=text,
            message_id=message_id,
            metadata=kwargs,
            is_command=is_command
        )
        self.on_message_received(message)


# ============================================================
# Factory Function
# ============================================================

def setup_communication_gateway(config: Config = None) -> CommunicationGateway:
    """
    Factory function para crear y configurar el gateway
    
    Args:
        config: Configuración de SwarmIA
    
    Returns:
        CommunicationGateway configurado
    """
    gateway = CommunicationGateway(config)
    
    # Registrar handler por defecto
    def default_message_handler(message: Message):
        """Handler por defecto que loguea mensajes"""
        gateway.logger.info(
            f"Handler por defecto: [{message.platform.value}] "
            f"{message.sender}: {message.text[:100]}"
        )
    
    gateway.register_message_handler(default_message_handler)
    
    return gateway


# ============================================================
# Main para pruebas
# ============================================================

def main():
    """Función principal para pruebas"""
    print("🚀 Probando Gateway de Comunicación de SwarmIA\n")
    
    config = Config()
    
    # Configurar para pruebas
    config.SERVER_DEBUG = True
    config.WHATSAPP_ENABLED = True
    config.TELEGRAM_ENABLED = True
    
    gateway = setup_communication_gateway(config)
    
    # Iniciar gateway
    if gateway.start():
        print("✅ Gateway iniciado correctamente\n")
        
        # Probar comando remoto simulado
        print("📡 Probando comando remoto...")
        gateway.receive_message(
            platform="telegram",
            sender="admin_user",
            text="/status",
            username="admin"
        )
        
        time.sleep(1)
        
        # Probar mensaje normal
        print("\n💬 Probando mensaje normal...")
        gateway.receive_message(
            platform="telegram",
            sender="user_123",
            text="Hola, ¿cómo estás?",
            username="test_user"
        )
        
        # Mostrar estadísticas
        time.sleep(1)
        stats = gateway.get_stats()
        
        print(f"\n📊 Estadísticas del Gateway:")
        print(f"  Mensajes recibidos: {stats['messages_received']}")
        print(f"  Mensajes enviados: {stats['messages_sent']}")
        print(f"  Comandos procesados: {stats['commands_processed']}")
        print(f"  Errores: {stats['errors']}")
        print(f"  Handlers: {stats['handlers']}")
        
        print(f"\n🛡️ Estadísticas del Supervisor:")
        sup_stats = stats.get('supervisor', {})
        print(f"  Ataques detectados: {sup_stats.get('attacks_detected', 0)}")
        print(f"  IPs bloqueadas: {sup_stats.get('blocked_ips_count', 0)}")
        print(f"  Tareas completadas: {sup_stats.get('tasks_completed', 0)}")
        
        # Detener gateway
        gateway.stop()
        print("\n✅ Gateway detenido")
        
    else:
        print("❌ Error al iniciar gateway")


if __name__ == "__main__":
    main()
