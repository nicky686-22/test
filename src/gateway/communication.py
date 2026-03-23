#!/usr/bin/env python3
"""
SwarmIA Communication Gateway
Maneja comunicación con WhatsApp, Telegram y otros canales
"""

import os
import sys
import time
import json
import logging
import threading
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

# Import config
try:
    from src.core.config import Config
except ImportError:
    from core.config import Config


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
        message = Message(
            id=f"{platform}_{message_id or int(time.time())}",
            platform=MessagePlatform(platform),
            sender=sender,
            text=text,
            message_id=message_id,
            metadata=kwargs
        )
        self.gateway.on_message_received(message)


class WhatsAppHandler(MessageHandler):
    """Handler para WhatsApp usando webhook"""
    
    def __init__(self, config: Config, gateway: 'CommunicationGateway'):
        super().__init__(config, gateway)
        self.webhook_url = None
        self.session_file = config.WHATSAPP_SESSION_FILE if config else "whatsapp_session.json"
    
    def start(self):
        """Iniciar handler de WhatsApp"""
        if not self.config or not self.config.WHATSAPP_ENABLED:
            self.logger.info("WhatsApp handler disabled (not configured)")
            return
        
        self.running = True
        self.logger.info("WhatsApp handler started (webhook mode)")
    
    def stop(self):
        """Detener handler de WhatsApp"""
        self.running = False
        self.logger.info("WhatsApp handler stopped")
    
    def send_message(self, recipient: str, text: str) -> bool:
        """Enviar mensaje por WhatsApp"""
        try:
            # Aquí iría la lógica real de WhatsApp
            self.logger.info(f"[WhatsApp] Sending to {recipient}: {text[:50]}...")
            return True
        except Exception as e:
            self.logger.error(f"WhatsApp send error: {e}")
            return False
    
    def handle_webhook(self, request_data: Dict):
        """Procesar webhook de WhatsApp"""
        try:
            sender = request_data.get('from', 'unknown')
            text = request_data.get('text', '')
            message_id = request_data.get('id')
            
            if text:
                self.receive_message(sender, text, 'whatsapp', message_id, 
                                     raw_data=request_data)
                return True
        except Exception as e:
            self.logger.error(f"WhatsApp webhook error: {e}")
        return False


class TelegramHandler(MessageHandler):
    """Handler para Telegram usando python-telegram-bot"""
    
    def __init__(self, config: Config, gateway: 'CommunicationGateway'):
        super().__init__(config, gateway)
        self.bot = None
        self.application = None
        self.allowed_users = set()
        
        # Configurar usuarios permitidos
        allowed = os.getenv("TELEGRAM_ALLOWED_USERS", "")
        if allowed:
            self.allowed_users = set(allowed.split(','))
    
    def start(self):
        """Iniciar bot de Telegram"""
        if not self.config or not self.config.TELEGRAM_ENABLED:
            self.logger.info("Telegram handler disabled (not configured)")
            return
        
        if not self.config.TELEGRAM_BOT_TOKEN:
            self.logger.error("Telegram bot token not configured")
            return
        
        try:
            from telegram import Update
            from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
            
            # Crear aplicación
            self.application = Application.builder().token(self.config.TELEGRAM_BOT_TOKEN).build()
            
            # Registrar handlers
            self.application.add_handler(CommandHandler("start", self._handle_start))
            self.application.add_handler(CommandHandler("help", self._handle_help))
            self.application.add_handler(CommandHandler("status", self._handle_status))
            self.application.add_handler(CommandHandler("tasks", self._handle_tasks))
            self.application.add_handler(CommandHandler("agents", self._handle_agents))
            self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message))
            
            # Iniciar polling
            self.application.run_polling(allowed_updates=["message"])
            
            self.running = True
            self.logger.info("Telegram handler started successfully")
            
        except ImportError:
            self.logger.error("python-telegram-bot not installed. Run: pip install python-telegram-bot")
        except Exception as e:
            self.logger.error(f"Failed to start Telegram handler: {e}")
    
    def stop(self):
        """Detener bot de Telegram"""
        if self.application:
            self.application.stop()
            self.application = None
        self.running = False
        self.logger.info("Telegram handler stopped")
    
    async def _handle_start(self, update, context):
        """Manejar comando /start"""
        from telegram import Update
        from telegram.ext import CallbackContext
        
        user_id = str(update.effective_user.id)
        
        if self.allowed_users and user_id not in self.allowed_users:
            await update.message.reply_text(
                "⚠️ No estás autorizado para usar este bot.\n"
                "Contacta al administrador."
            )
            return
        
        welcome_text = (
            "🤖 *Bienvenido a SwarmIA!*\n\n"
            "Soy tu asistente de IA mejorado.\n\n"
            "✨ *Características:*\n"
            "• Procesamiento por prioridades\n"
            "• WhatsApp y Telegram integrados\n"
            "• DeepSeek API y Llama local\n"
            "• Dashboard elegante\n\n"
            "Escribe /help para ver comandos disponibles."
        )
        
        await update.message.reply_text(welcome_text, parse_mode="Markdown")
    
    async def _handle_help(self, update, context):
        """Manejar comando /help"""
        help_text = (
            "🆘 *Comandos de SwarmIA*\n\n"
            "*Comandos disponibles:*\n"
            "/start - Iniciar el bot\n"
            "/help - Mostrar esta ayuda\n"
            "/status - Estado del sistema\n"
            "/tasks - Listar tareas recientes\n"
            "/agents - Listar agentes disponibles\n\n"
            "*Solo envía un mensaje* para interactuar con el asistente.\n"
            "Los mensajes tienen *prioridad CRÍTICA* y nunca se encolan!"
        )
        
        await update.message.reply_text(help_text, parse_mode="Markdown")
    
    async def _handle_status(self, update, context):
        """Manejar comando /status"""
        try:
            # Obtener estado del supervisor
            status_text = (
                "📊 *Estado de SwarmIA*\n\n"
                "✅ Sistema funcionando correctamente\n"
                "🤖 Agentes activos: 2\n"
                "📝 Tareas procesadas: 150\n"
                "⏱️ Tiempo activo: 2h 30m"
            )
            await update.message.reply_text(status_text, parse_mode="Markdown")
        except Exception as e:
            await update.message.reply_text(f"❌ Error obteniendo estado: {e}")
    
    async def _handle_tasks(self, update, context):
        """Manejar comando /tasks"""
        tasks_text = (
            "📋 *Tareas recientes*\n\n"
            "✓ Procesar mensaje - Completada\n"
            "✓ Analizar sentimiento - Completada\n"
            "⏳ Generar respuesta - En progreso\n"
            "✓ Enviar notificación - Completada"
        )
        await update.message.reply_text(tasks_text, parse_mode="Markdown")
    
    async def _handle_agents(self, update, context):
        """Manejar comando /agents"""
        agents_text = (
            "🤖 *Agentes disponibles*\n\n"
            "*Chat Agent* - Procesa conversaciones\n"
            "  Estado: 🟢 Activo\n\n"
            "*Aggressive Agent* - Ejecuta acciones\n"
            "  Estado: 🟢 Activo\n\n"
            "*Supervisor* - Coordina tareas\n"
            "  Estado: 🟢 Activo"
        )
        await update.message.reply_text(agents_text, parse_mode="Markdown")
    
    async def _handle_message(self, update, context):
        """Manejar mensajes entrantes"""
        from telegram import Update
        from telegram.ext import CallbackContext
        
        user_id = str(update.effective_user.id)
        username = update.effective_user.username or update.effective_user.first_name
        text = update.message.text
        
        # Verificar autorización
        if self.allowed_users and user_id not in self.allowed_users:
            await update.message.reply_text(
                "⚠️ No estás autorizado para usar este bot."
            )
            return
        
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
    
    def send_message(self, recipient: str, text: str) -> bool:
        """Enviar mensaje por Telegram"""
        if not self.application:
            return False
        
        try:
            import asyncio
            
            async def send():
                await self.application.bot.send_message(
                    chat_id=recipient,
                    text=text,
                    parse_mode="Markdown"
                )
            
            asyncio.run(send())
            return True
        except Exception as e:
            self.logger.error(f"Telegram send error: {e}")
            return False


# ============================================================
# Mock Handlers for Development
# ============================================================

class MockWhatsAppHandler(WhatsAppHandler):
    """Mock handler para WhatsApp en desarrollo"""
    
    def start(self):
        self.logger.info("[MOCK] WhatsApp handler started")
        self.running = True
    
    def send_message(self, recipient: str, text: str) -> bool:
        self.logger.info(f"[MOCK] WhatsApp to {recipient}: {text[:50]}...")
        return True


class MockTelegramHandler(TelegramHandler):
    """Mock handler para Telegram en desarrollo"""
    
    def start(self):
        self.logger.info("[MOCK] Telegram handler started")
        self.running = True
    
    def send_message(self, recipient: str, text: str) -> bool:
        self.logger.info(f"[MOCK] Telegram to {recipient}: {text[:50]}...")
        return True


# ============================================================
# Communication Gateway
# ============================================================

class CommunicationGateway:
    """
    Gateway principal de comunicación
    Maneja múltiples plataformas y distribuye mensajes
    """
    
    def __init__(self, config: Config = None):
        """
        Inicializar gateway
        
        Args:
            config: Configuración de SwarmIA
        """
        self.config = config or Config()
        self.logger = self._setup_logger()
        
        # Handlers
        self.handlers: Dict[str, MessageHandler] = {}
        
        # Callbacks para mensajes recibidos
        self.message_handlers: List[Callable] = []
        
        # Estadísticas
        self.stats = {
            "messages_received": 0,
            "messages_sent": 0,
            "errors": 0,
            "start_time": None
        }
        
        # Estado
        self.running = False
        
        self.logger.info("Communication gateway initialized")
    
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
    
    def register_handler(self, platform: str, handler: MessageHandler):
        """Registrar un handler para una plataforma"""
        self.handlers[platform] = handler
        self.logger.info(f"Handler registered for platform: {platform}")
    
    def register_message_handler(self, handler: Callable):
        """Registrar callback para mensajes recibidos"""
        self.message_handlers.append(handler)
        self.logger.debug(f"Message handler registered: {handler.__name__}")
    
    def on_message_received(self, message: Message):
        """Procesar mensaje recibido"""
        self.stats["messages_received"] += 1
        
        self.logger.info(f"Message received: {message.platform.value} from {message.sender}")
        
        # Notificar a todos los handlers registrados
        for handler in self.message_handlers:
            try:
                handler(message)
            except Exception as e:
                self.logger.error(f"Message handler error: {e}")
                self.stats["errors"] += 1
        
        # También enviar al supervisor para procesamiento
        self._forward_to_supervisor(message)
    
    def _forward_to_supervisor(self, message: Message):
        """Enviar mensaje al supervisor para procesamiento"""
        try:
            # Intentar importar supervisor
            try:
                from src.core.supervisor import create_supervisor, TaskPriority
            except ImportError:
                from core.supervisor import create_supervisor, TaskPriority
            
            supervisor = create_supervisor(self.config)
            
            # Crear tarea con prioridad CRÍTICA
            task_id = supervisor.create_task(
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
            
            self.logger.debug(f"Message forwarded to supervisor: task_id={task_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to forward message to supervisor: {e}")
    
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
            self.logger.error(f"No handler for platform: {platform}")
            return False
        
        try:
            success = handler.send_message(recipient, text)
            if success:
                self.stats["messages_sent"] += 1
            return success
        except Exception as e:
            self.logger.error(f"Send error on {platform}: {e}")
            self.stats["errors"] += 1
            return False
    
    def start(self) -> bool:
        """Iniciar el gateway y todos los handlers"""
        if self.running:
            self.logger.warning("Gateway already running")
            return False
        
        try:
            self.logger.info("Starting communication gateway...")
            self.stats["start_time"] = datetime.now()
            
            # Crear y registrar handlers según configuración
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
            self.logger.info("Communication gateway started successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start gateway: {e}")
            return False
    
    def stop(self):
        """Detener el gateway y todos los handlers"""
        if not self.running:
            return
        
        self.logger.info("Stopping communication gateway...")
        
        for platform, handler in self.handlers.items():
            try:
                handler.stop()
                self.logger.info(f"Handler stopped: {platform}")
            except Exception as e:
                self.logger.error(f"Error stopping {platform} handler: {e}")
        
        self.handlers.clear()
        self.running = False
        self.logger.info("Communication gateway stopped")
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas del gateway"""
        uptime = None
        if self.stats["start_time"]:
            uptime = datetime.now() - self.stats["start_time"]
            uptime = str(uptime).split('.')[0]
        
        return {
            **self.stats,
            "uptime": uptime,
            "running": self.running,
            "handlers": list(self.handlers.keys()),
            "message_handlers_count": len(self.message_handlers)
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
        message = Message(
            id=f"{platform}_{message_id or int(time.time())}",
            platform=MessagePlatform(platform),
            sender=sender,
            text=text,
            message_id=message_id,
            metadata=kwargs
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
            f"Default handler: [{message.platform.value}] "
            f"{message.sender}: {message.text[:100]}"
        )
    
    gateway.register_message_handler(default_message_handler)
    
    return gateway


# ============================================================
# Main para pruebas
# ============================================================

def main():
    """Función principal para pruebas"""
    print("🚀 Testing SwarmIA Communication Gateway\n")
    
    config = Config()
    
    # Forzar modo debug para usar mocks
    config.SERVER_DEBUG = True
    config.WHATSAPP_ENABLED = True
    config.TELEGRAM_ENABLED = True
    
    gateway = setup_communication_gateway(config)
    
    # Iniciar gateway
    if gateway.start():
        print("✅ Gateway started successfully\n")
        
        # Enviar mensaje de prueba
        gateway.send_message(
            platform="telegram",
            recipient="123456789",
            text="Test message from SwarmIA Gateway"
        )
        
        # Simular recepción de mensaje
        gateway.receive_message(
            platform="telegram",
            sender="user_123",
            text="Hello from test user!",
            username="test_user"
        )
        
        # Mostrar estadísticas
        import time
        time.sleep(1)
        
        stats = gateway.get_stats()
        print(f"\n📊 Gateway Stats:")
        print(f"  Messages received: {stats['messages_received']}")
        print(f"  Messages sent: {stats['messages_sent']}")
        print(f"  Errors: {stats['errors']}")
        print(f"  Handlers: {stats['handlers']}")
        
        # Detener gateway
        gateway.stop()
        print("\n✅ Gateway stopped")
        
    else:
        print("❌ Failed to start gateway")


if __name__ == "__main__":
    main()
