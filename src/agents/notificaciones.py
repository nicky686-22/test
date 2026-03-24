#!/usr/bin/env python3
"""
Agente Notificaciones - Envío de notificaciones multi-canal
Soporta: Telegram, WhatsApp, Email, Slack, Discord, Webhook
"""

import os
import sys
import json
import smtplib
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
from src.utils.env_manager import EnvManager

# Importaciones opcionales
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    from telegram import Bot
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False

try:
    import discord
    DISCORD_AVAILABLE = True
except ImportError:
    DISCORD_AVAILABLE = False

from src.core.agente import Agente, TipoAgente, ResultadoTarea
from src.core.supervisor import Supervisor
from src.core.config import Config


class AgenteNotificaciones(Agente):
    """
    Agente Notificaciones - Envía notificaciones a múltiples canales
    Soporta: Telegram, WhatsApp, Email, Slack, Discord, Webhooks
    """
    
    def __init__(self, supervisor: Supervisor, config: Config):
        super().__init__(
            id_agente="notificaciones",
            nombre="Agente Notificaciones",
            tipo=TipoAgente.NOTIFICACIONES,
            supervisor=supervisor,
            version="1.0.0"
        )
        self.config = config
        
        # Configuración de canales
        self.telegram_bot = None
        self.discord_client = None
        
        # Historial de notificaciones
        self.historial: List[Dict] = []
        self.historial_max = 1000
        
        # Cargar configuración de canales
        self._cargar_configuracion()
        
        self._registrar_capacidades()
        self.logger.info("Agente Notificaciones iniciado")
    
    def _cargar_configuracion(self):
        """Cargar configuración de canales desde variables de entorno"""
        import os
        from dotenv import load_dotenv
        
        # Recargar .env
        load_dotenv()
        
        # Telegram
        self.telegram_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.telegram_chat_ids = os.getenv("TELEGRAM_CHAT_IDS", "").split(",")
        if self.telegram_token and TELEGRAM_AVAILABLE:
            try:
                self.telegram_bot = Bot(token=self.telegram_token)
                self.logger.info("Telegram configurado")
            except Exception as e:
                self.logger.error(f"Error configurando Telegram: {e}")
        
        # Slack
        self.slack_webhook = os.getenv("SLACK_WEBHOOK", "")
        if self.slack_webhook:
            self.logger.info("Slack configurado")
        
        # Discord
        self.discord_webhook = os.getenv("DISCORD_WEBHOOK", "")
        if self.discord_webhook:
            self.logger.info("Discord configurado")
        
        # Email
        self.email_host = os.getenv("EMAIL_HOST", "")
        self.email_port = int(os.getenv("EMAIL_PORT", "587"))
        self.email_user = os.getenv("EMAIL_USER", "")
        self.email_password = os.getenv("EMAIL_PASSWORD", "")
        self.email_from = os.getenv("EMAIL_FROM", "")
        self.email_to = os.getenv("EMAIL_TO", "").split(",")
    
    def _registrar_capacidades(self):
        """Registrar capacidades del agente"""
        
        self.registrar_capacidad(
            nombre="notificar_telegram",
            descripcion="Enviar mensaje a Telegram",
            parametros=["mensaje", "chat_id"],
            ejemplos=["notificar por Telegram que backup completado", "enviar alerta a Telegram"],
            nivel_riesgo="bajo"
        )
        
        self.registrar_capacidad(
            nombre="notificar_whatsapp",
            descripcion="Enviar mensaje a WhatsApp",
            parametros=["mensaje", "numero"],
            ejemplos=["enviar WhatsApp al administrador", "notificar por WhatsApp"],
            nivel_riesgo="bajo"
        )
        
        self.registrar_capacidad(
            nombre="notificar_email",
            descripcion="Enviar correo electrónico",
            parametros=["asunto", "mensaje", "destinatario"],
            ejemplos=["enviar email con reporte", "notificar por correo"],
            nivel_riesgo="bajo"
        )
        
        self.registrar_capacidad(
            nombre="notificar_slack",
            descripcion="Enviar mensaje a Slack",
            parametros=["mensaje", "canal"],
            ejemplos=["enviar alerta a Slack", "notificar en #general"],
            nivel_riesgo="bajo"
        )
        
        self.registrar_capacidad(
            nombre="notificar_discord",
            descripcion="Enviar mensaje a Discord",
            parametros=["mensaje", "canal"],
            ejemplos=["enviar mensaje a Discord", "notificar en servidor"],
            nivel_riesgo="bajo"
        )
        
        self.registrar_capacidad(
            nombre="notificar_webhook",
            descripcion="Enviar notificación a webhook",
            parametros=["url", "payload"],
            ejemplos=["enviar webhook a servicio externo"],
            nivel_riesgo="bajo"
        )
        
        self.registrar_capacidad(
            nombre="notificar_todos",
            descripcion="Enviar a todos los canales configurados",
            parametros=["mensaje"],
            ejemplos=["notificar a todos", "enviar alerta general"],
            nivel_riesgo="bajo"
        )
        
        self.registrar_capacidad(
            nombre="historial",
            descripcion="Ver historial de notificaciones",
            ejemplos=["ver últimas notificaciones", "historial de alertas"],
            nivel_riesgo="bajo"
        )
    
    async def ejecutar(self, tarea: Dict[str, Any]) -> ResultadoTarea:
        """Ejecuta tarea según tipo"""
        tipo = tarea.get("tipo", "")
        desc = tarea.get("descripcion", "").lower()
        parametros = tarea.get("parametros", {})
        
        if "notificar_telegram" in tipo or "telegram" in desc:
            return await self._notificar_telegram(desc, parametros)

        if "configurar_telegram" in tipo or "configurar telegram" in desc:
            return await self._configurar_telegram(desc, parametros)
        
        elif "notificar_whatsapp" in tipo or "whatsapp" in desc:
            return await self._notificar_whatsapp(desc, parametros)
        
        elif "notificar_email" in tipo or "email" in desc or "correo" in desc:
            return await self._notificar_email(desc, parametros)
        
        elif "notificar_slack" in tipo or "slack" in desc:
            return await self._notificar_slack(desc, parametros)
        
        elif "notificar_discord" in tipo or "discord" in desc:
            return await self._notificar_discord(desc, parametros)
        
        elif "notificar_webhook" in tipo or "webhook" in desc:
            return await self._notificar_webhook(desc, parametros)
        
        elif "notificar_todos" in tipo or "todos" in desc:
            return await self._notificar_todos(desc, parametros)
        
        elif "historial" in tipo:
            return await self._historial()
        
        else:
            return ResultadoTarea(exito=False, error=f"No sé cómo manejar: {tipo}")
    
    # ============================================================
    # TELEGRAM
    # ============================================================
    
    async def _notificar_telegram(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Enviar mensaje a Telegram"""
        mensaje = parametros.get("mensaje") or self._extraer_mensaje(desc)
        chat_id = parametros.get("chat_id")
        
        if not mensaje:
            return ResultadoTarea(exito=False, error="Especifica el mensaje a enviar")
        
        if not self.telegram_bot:
            return ResultadoTarea(exito=False, error="Telegram no configurado. Configura TELEGRAM_BOT_TOKEN")
        
        if not chat_id and self.telegram_chat_ids:
            chat_id = self.telegram_chat_ids[0]
        
        if not chat_id:
            return ResultadoTarea(exito=False, error="Especifica chat_id o configura TELEGRAM_CHAT_IDS")
        
        try:
            await self.telegram_bot.send_message(chat_id=chat_id, text=mensaje)
            self._guardar_historial("telegram", chat_id, mensaje, True)
            return ResultadoTarea(
                exito=True,
                datos={"canal": "telegram", "chat_id": chat_id, "mensaje": mensaje[:100]}
            )
        except Exception as e:
            self._guardar_historial("telegram", chat_id, mensaje, False, str(e))
            return ResultadoTarea(exito=False, error=str(e))
    
    # ============================================================
    # WHATSAPP
    # ============================================================
    
    async def _notificar_whatsapp(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Enviar mensaje a WhatsApp (usa webhook o servicio externo)"""
        mensaje = parametros.get("mensaje") or self._extraer_mensaje(desc)
        numero = parametros.get("numero")
        
        if not mensaje:
            return ResultadoTarea(exito=False, error="Especifica el mensaje a enviar")
        
        # Usar webhook de WhatsApp Business API o servicio como Twilio
        whatsapp_webhook = os.getenv("WHATSAPP_WEBHOOK", "")
        
        if not whatsapp_webhook:
            return ResultadoTarea(exito=False, error="WhatsApp no configurado. Configura WHATSAPP_WEBHOOK")
        
        payload = {
            "numero": numero or os.getenv("WHATSAPP_ADMIN_NUMBER", ""),
            "mensaje": mensaje
        }
        
        try:
            response = requests.post(whatsapp_webhook, json=payload, timeout=10)
            self._guardar_historial("whatsapp", payload["numero"], mensaje, response.status_code < 400)
            return ResultadoTarea(
                exito=response.status_code < 400,
                datos={"canal": "whatsapp", "status": response.status_code}
            )
        except Exception as e:
            self._guardar_historial("whatsapp", payload["numero"], mensaje, False, str(e))
            return ResultadoTarea(exito=False, error=str(e))
    
    # ============================================================
    # EMAIL
    # ============================================================
    
    async def _notificar_email(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Enviar correo electrónico"""
        asunto = parametros.get("asunto") or self._extraer_asunto(desc)
        mensaje = parametros.get("mensaje") or self._extraer_mensaje(desc)
        destinatario = parametros.get("destinatario")
        
        if not asunto:
            asunto = "Notificación SwarmIA"
        
        if not mensaje:
            return ResultadoTarea(exito=False, error="Especifica el mensaje a enviar")
        
        if not self.email_host:
            return ResultadoTarea(exito=False, error="Email no configurado. Configura EMAIL_HOST, EMAIL_USER, EMAIL_PASSWORD")
        
        if not destinatario and self.email_to:
            destinatario = self.email_to[0]
        
        if not destinatario:
            return ResultadoTarea(exito=False, error="Especifica destinatario o configura EMAIL_TO")
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_from
            msg['To'] = destinatario
            msg['Subject'] = asunto
            msg.attach(MIMEText(mensaje, 'plain'))
            
            server = smtplib.SMTP(self.email_host, self.email_port)
            server.starttls()
            server.login(self_email_user, self.email_password)
            server.send_message(msg)
            server.quit()
            
            self._guardar_historial("email", destinatario, asunto, True)
            return ResultadoTarea(
                exito=True,
                datos={"canal": "email", "destinatario": destinatario, "asunto": asunto}
            )
        except Exception as e:
            self._guardar_historial("email", destinatario, asunto, False, str(e))
            return ResultadoTarea(exito=False, error=str(e))
    
    # ============================================================
    # SLACK
    # ============================================================
    
    async def _notificar_slack(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Enviar mensaje a Slack"""
        mensaje = parametros.get("mensaje") or self._extraer_mensaje(desc)
        canal = parametros.get("canal")
        
        if not mensaje:
            return ResultadoTarea(exito=False, error="Especifica el mensaje a enviar")
        
        webhook = self.slack_webhook
        if not webhook:
            return ResultadoTarea(exito=False, error="Slack no configurado. Configura SLACK_WEBHOOK")
        
        payload = {"text": mensaje}
        if canal:
            payload["channel"] = canal
        
        try:
            response = requests.post(webhook, json=payload, timeout=10)
            self._guardar_historial("slack", canal or "general", mensaje, response.status_code < 400)
            return ResultadoTarea(
                exito=response.status_code < 400,
                datos={"canal": "slack", "status": response.status_code}
            )
        except Exception as e:
            self._guardar_historial("slack", canal or "general", mensaje, False, str(e))
            return ResultadoTarea(exito=False, error=str(e))
    
    # ============================================================
    # DISCORD
    # ============================================================
    
    async def _notificar_discord(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Enviar mensaje a Discord"""
        mensaje = parametros.get("mensaje") or self._extraer_mensaje(desc)
        
        if not mensaje:
            return ResultadoTarea(exito=False, error="Especifica el mensaje a enviar")
        
        webhook = self.discord_webhook
        if not webhook:
            return ResultadoTarea(exito=False, error="Discord no configurado. Configura DISCORD_WEBHOOK")
        
        payload = {"content": mensaje}
        
        try:
            response = requests.post(webhook, json=payload, timeout=10)
            self._guardar_historial("discord", "webhook", mensaje, response.status_code < 400)
            return ResultadoTarea(
                exito=response.status_code < 400,
                datos={"canal": "discord", "status": response.status_code}
            )
        except Exception as e:
            self._guardar_historial("discord", "webhook", mensaje, False, str(e))
            return ResultadoTarea(exito=False, error=str(e))
    
    # ============================================================
    # WEBHOOK
    # ============================================================
    
    async def _notificar_webhook(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Enviar notificación a webhook personalizado"""
        url = parametros.get("url") or self._extraer_url(desc)
        payload = parametros.get("payload", {})
        
        if not url:
            return ResultadoTarea(exito=False, error="Especifica la URL del webhook")
        
        if not payload:
            payload = {"mensaje": self._extraer_mensaje(desc), "timestamp": datetime.now().isoformat()}
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            self._guardar_historial("webhook", url, str(payload)[:100], response.status_code < 400)
            return ResultadoTarea(
                exito=response.status_code < 400,
                datos={"url": url, "status": response.status_code}
            )
        except Exception as e:
            self._guardar_historial("webhook", url, str(payload)[:100], False, str(e))
            return ResultadoTarea(exito=False, error=str(e))
    
    # ============================================================
    # NOTIFICAR A TODOS
    # ============================================================
    
    async def _notificar_todos(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Enviar mensaje a todos los canales configurados"""
        mensaje = parametros.get("mensaje") or self._extraer_mensaje(desc)
        
        if not mensaje:
            return ResultadoTarea(exito=False, error="Especifica el mensaje a enviar")
        
        resultados = []
        
        # Telegram
        if self.telegram_bot and self.telegram_chat_ids:
            for chat_id in self.telegram_chat_ids:
                try:
                    await self.telegram_bot.send_message(chat_id=chat_id, text=mensaje)
                    resultados.append({"canal": "telegram", "exito": True})
                except Exception as e:
                    resultados.append({"canal": "telegram", "exito": False, "error": str(e)})
        
        # Slack
        if self.slack_webhook:
            try:
                response = requests.post(self.slack_webhook, json={"text": mensaje}, timeout=10)
                resultados.append({"canal": "slack", "exito": response.status_code < 400})
            except Exception as e:
                resultados.append({"canal": "slack", "exito": False, "error": str(e)})
        
        # Discord
        if self.discord_webhook:
            try:
                response = requests.post(self.discord_webhook, json={"content": mensaje}, timeout=10)
                resultados.append({"canal": "discord", "exito": response.status_code < 400})
            except Exception as e:
                resultados.append({"canal": "discord", "exito": False, "error": str(e)})
        
        # Email
        if self.email_host and self.email_to:
            try:
                msg = MIMEMultipart()
                msg['From'] = self.email_from
                msg['To'] = self.email_to[0]
                msg['Subject'] = "Notificación SwarmIA"
                msg.attach(MIMEText(mensaje, 'plain'))
                
                server = smtplib.SMTP(self.email_host, self.email_port)
                server.starttls()
                server.login(self_email_user, self.email_password)
                server.send_message(msg)
                server.quit()
                resultados.append({"canal": "email", "exito": True})
            except Exception as e:
                resultados.append({"canal": "email", "exito": False, "error": str(e)})
        
        self._guardar_historial("todos", "todos", mensaje, True)
        
        return ResultadoTarea(
            exito=True,
            datos={"resultados": resultados, "total": len(resultados)}
        )
    
    # ============================================================
    # HISTORIAL
    # ============================================================
    
    async def _historial(self) -> ResultadoTarea:
        """Ver historial de notificaciones"""
        return ResultadoTarea(
            exito=True,
            datos={"historial": self.historial[-50:], "total": len(self.historial)}
        )
    
    def _guardar_historial(self, canal: str, destino: str, mensaje: str, exito: bool, error: str = None):
        """Guardar notificación en historial"""
        self.historial.append({
            "canal": canal,
            "destino": destino,
            "mensaje": mensaje[:200],
            "exito": exito,
            "error": error,
            "timestamp": datetime.now().isoformat()
        })
        
        if len(self.historial) > self.historial_max:
            self.historial = self.historial[-self.historial_max:]
    
    # ============================================================
    # EXTRACTORES
    # ============================================================
    
    def _extraer_mensaje(self, desc: str) -> str:
        """Extraer mensaje de la descripción"""
        import re
        # Buscar después de "mensaje:" o "texto:"
        match = re.search(r'(?:mensaje|texto)[:\s]+(.+)', desc, re.IGNORECASE)
        if match:
            return match.group(1)
        # Si no, usar toda la descripción
        return desc
    
    def _extraer_asunto(self, desc: str) -> str:
        """Extraer asunto de la descripción"""
        import re
        match = re.search(r'asunto[:\s]+([^,]+)', desc, re.IGNORECASE)
        if match:
            return match.group(1)
        return "Notificación SwarmIA"
    
    def _extraer_url(self, desc: str) -> Optional[str]:
        """Extraer URL de la descripción"""
        import re
        match = re.search(r'https?://[^\s]+', desc)
        return match.group(0) if match else None

    # ============================================================
    # CONFIGURACIÓN DINÁMICA
    # ============================================================
    
    async def _configurar_telegram(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Configurar Telegram con token proporcionado por el usuario"""
        token = parametros.get("token") or self._extraer_token(desc)
        
        if not token:
            return ResultadoTarea(
                exito=False,
                error="Necesito el token de Telegram. Ejemplo: configurar telegram con token 123456:ABC-DEF"
            )
        
        try:
            import requests
            response = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
            if response.status_code != 200:
                return ResultadoTarea(exito=False, error="❌ Token inválido")
            
            bot_info = response.json()
            bot_username = bot_info.get("result", {}).get("username", "desconocido")
            
            # Guardar en .env usando EnvManager
            env = EnvManager()
            env.set("TELEGRAM_BOT_TOKEN", token)
            env.set("TELEGRAM_ENABLED", "true")
            
            # Recargar configuración
            self._cargar_configuracion()
            
            return ResultadoTarea(
                exito=True,
                datos={
                    "bot": bot_username,
                    "mensaje": f"✅ Telegram configurado correctamente. Bot: @{bot_username}"
                }
            )
        except Exception as e:
            return ResultadoTarea(exito=False, error=str(e))
    
    def _extraer_token(self, desc: str) -> Optional[str]:
        """Extraer token de Telegram de la descripción"""
        import re
        match = re.search(r'(\d+:[A-Za-z0-9_-]+)', desc)
        return match.group(1) if match else None


# ============================================================
# Factory Function
# ============================================================

def crear_agente_notificaciones(supervisor: Supervisor, config: Config) -> AgenteNotificaciones:
    """Crea instancia del agente de notificaciones"""
    return AgenteNotificaciones(supervisor, config)
