
#!/usr/bin/env python3
"""
SwarmIA Supervisor Module - Enhanced with Anti-Hacking System
Gestiona agentes, tareas, prioridades y detecta ataques con notificaciones multi-canal
"""

import os
import sys
import time
import queue
import logging
import threading
import subprocess
import socket
import ipaddress
import json
import sqlite3
from enum import Enum
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from uuid import uuid4
from collections import defaultdict
from pathlib import Path

# Intentar importar dependencias opcionales
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    import geoip2.database
    GEOIP_AVAILABLE = False
except ImportError:
    GEOIP_AVAILABLE = False


# ============================================================
# Enums
# ============================================================

class TaskPriority(Enum):
    """Prioridad de tareas"""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


class TaskStatus(Enum):
    """Estado de una tarea"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentStatus(Enum):
    """Estado de un agente"""
    IDLE = "idle"
    BUSY = "busy"
    OFFLINE = "offline"


class AttackType(Enum):
    """Tipo de ataque detectado"""
    PORT_SCAN = "port_scan"
    SSH_BRUTE = "ssh_brute"
    HTTP_SCAN = "http_scan"
    SQL_INJECTION = "sql_injection"
    DOS_ATTEMPT = "dos_attempt"
    SUSPICIOUS = "suspicious"


class ThreatLevel(Enum):
    """Nivel de amenaza"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ============================================================
# Data Classes
# ============================================================

@dataclass
class Task:
    """Representa una tarea en el sistema"""
    id: str
    type: str
    data: Dict[str, Any]
    priority: TaskPriority
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    assigned_agent: Optional[str] = None
    source: str = "system"
    retry_count: int = 0
    max_retries: int = 3
    timeout: int = 60
    error: Optional[str] = None
    result: Optional[Any] = None


@dataclass
class Agent:
    """Representa un agente en el sistema"""
    id: str
    name: str
    type: str
    status: AgentStatus = AgentStatus.IDLE
    capabilities: List[str] = field(default_factory=list)
    current_tasks: List[str] = field(default_factory=list)
    registered_at: datetime = field(default_factory=datetime.now)
    last_heartbeat: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AttackEvent:
    """Evento de ataque detectado"""
    id: str
    attack_type: AttackType
    source_ip: str
    threat_level: ThreatLevel
    details: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    blocked: bool = False
    geo_info: Optional[Dict] = None


# ============================================================
# Attack Detector
# ============================================================

class AttackDetector:
    """Detector de ataques y comportamientos sospechosos"""
    
    def __init__(self, supervisor):
        self.supervisor = supervisor
        self.logger = supervisor.logger
        self.connection_history: Dict[str, List[datetime]] = defaultdict(list)
        self.port_scan_tracker: Dict[str, List[int]] = defaultdict(list)
    
    def check_connection(self, ip: str, port: int = None) -> Tuple[bool, Optional[AttackType], str]:
        """
        Verificar si una conexión es sospechosa
        
        Returns:
            (is_malicious, attack_type, message)
        """
        # Verificar si IP está bloqueada
        if ip in self.supervisor.blocked_ips:
            block_time = self.supervisor.blocked_ips[ip]
            if datetime.now() - block_time < timedelta(minutes=self.supervisor.block_duration_minutes):
                return True, None, f"IP bloqueada hasta {block_time + timedelta(minutes=self.supervisor.block_duration_minutes)}"
            else:
                # Desbloquear si pasó el tiempo
                del self.supervisor.blocked_ips[ip]
        
        # Limpiar historial antiguo (más de 1 minuto)
        now = datetime.now()
        self.connection_history[ip] = [t for t in self.connection_history[ip] if now - t < timedelta(minutes=1)]
        
        # Agregar intento actual
        self.connection_history[ip].append(now)
        
        # Verificar tasa de intentos
        if len(self.connection_history[ip]) > self.supervisor.max_attempts_per_minute:
            return True, AttackType.SUSPICIOUS, f"Demasiados intentos ({len(self.connection_history[ip])}/minuto)"
        
        # Verificar port scanning
        if port:
            self.port_scan_tracker[ip].append(port)
            unique_ports = len(set(self.port_scan_tracker[ip]))
            if unique_ports > self.supervisor.port_scan_threshold:
                return True, AttackType.PORT_SCAN, f"Posible port scan detectado ({unique_ports} puertos)"
        
        return False, None, "OK"
    
    def record_ssh_attempt(self, ip: str, username: str, success: bool):
        """Registrar intento SSH"""
        if success:
            return
        
        now = datetime.now()
        self.connection_history[ip].append(now)
        
        if len(self.connection_history[ip]) > self.supervisor.max_attempts_per_minute:
            self.supervisor._detect_attack(
                source_ip=ip,
                attack_type=AttackType.SSH_BRUTE,
                details={"username": username, "attempts": len(self.connection_history[ip])}
            )


# ============================================================
# Supervisor Class
# ============================================================

class Supervisor:
    """
    Supervisor central de SwarmIA con sistema anti-hacking
    Gestiona agentes, tareas y detecta ataques con notificaciones multi-canal
    """
    
    def __init__(self, config=None):
        """
        Inicializar supervisor
        
        Args:
            config: Configuración (opcional)
        """
        self.config = config
        self.logger = self._setup_logger()
        
        # Estado
        self.running = False
        self.lock = threading.RLock()
        
        # Tareas
        self.tasks: Dict[str, Task] = {}
        self.task_queue: queue.PriorityQueue = queue.PriorityQueue()
        self.task_counter = 0
        self.task_handlers: Dict[str, Callable] = {}
        self.progress_callbacks: List[Callable] = []
        
        # Límites concurrentes
        self.max_concurrent_tasks = int(os.getenv("MAX_CONCURRENT_TASKS", "10"))
        self.active_tasks_count = 0
        self.task_timeout_default = int(os.getenv("TASK_TIMEOUT", "60"))
        
        # Agentes
        self.agents: Dict[str, Agent] = {}
        self.agent_capabilities: Dict[str, List[str]] = {}
        
        # ============================================================
        # SISTEMA ANTI-HACKING
        # ============================================================
        
        # Detección de ataques
        self.attack_detector = AttackDetector(self)
        self.attack_events: List[AttackEvent] = []
        self.blocked_ips: Dict[str, datetime] = {}
        self.connection_attempts: Dict[str, List[datetime]] = defaultdict(list)
        
        # Límites de seguridad
        self.max_attempts_per_minute = int(os.getenv("MAX_ATTEMPTS_PER_MINUTE", "10"))
        self.block_duration_minutes = int(os.getenv("BLOCK_DURATION_MINUTES", "30"))
        self.port_scan_threshold = int(os.getenv("PORT_SCAN_THRESHOLD", "20"))
        
        # ============================================================
        # NOTIFICACIONES MULTI-CANAL
        # ============================================================
        self.notification_callbacks: List[Callable] = []
        self.telegram_bot = None
        self.whatsapp_handler = None
        
        # ============================================================
        # COMANDOS REMOTOS
        # ============================================================
        self.allowed_remote_commands = {
            "status": self._cmd_status,
            "install": self._cmd_install,
            "update": self._cmd_update,
            "restart": self._cmd_restart,
            "block_ip": self._cmd_block_ip,
            "unblock_ip": self._cmd_unblock_ip,
            "scan": self._cmd_scan,
            "info": self._cmd_info,
            "help": self._cmd_help,
            "whois": self._cmd_whois,
            "uptime": self._cmd_uptime,
            "logs": self._cmd_logs
        }
        
        # Persistencia
        self.db_path = Path("data/supervisor.db")
        self._init_db()
        
        # Estadísticas
        self.stats = {
            "tasks_created": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "tasks_cancelled": 0,
            "agents_registered": 0,
            "agents_active": 0,
            "attacks_detected": 0,
            "ips_blocked": 0,
            "start_time": None
        }
        
        # Threads
        self.worker_thread = None
        self.cleanup_thread = None
        self.heartbeat_thread = None
        self.security_thread = None
        
        self.logger.info("Supervisor inicializado con sistema anti-hacking y notificaciones multi-canal")
        self._show_security_banner()
    
    def _setup_logger(self) -> logging.Logger:
        """Configurar logger"""
        logger = logging.getLogger("swarmia.supervisor")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _show_security_banner(self):
        """Mostrar banner de seguridad"""
        banner = f"""
╔══════════════════════════════════════════════════════════════╗
║  🛡️  SwarmIA Anti-Hacking System ACTIVE                      ║
║                                                              ║
║  Protecciones activas:                                       ║
║  • Detección de port scanning                                ║
║  • SSH brute force detection                                 ║
║  • HTTP attack detection                                     ║
║  • Auto-blocking de IPs maliciosas                           ║
║  • Notificaciones en tiempo real (Telegram/WhatsApp)         ║
║                                                              ║
║  Límites:                                                    ║
║  • Max intentos/minuto: {self.max_attempts_per_minute}/ip    ║
║  • Duración bloqueo: {self.block_duration_minutes} minutos   ║
║  • Umbral port scan: {self.port_scan_threshold} puertos      ║
╚══════════════════════════════════════════════════════════════╝
"""
        self.logger.info(banner)
    
    def _init_db(self):
        """Inicializar base de datos de seguridad"""
        self.db_path.parent.mkdir(exist_ok=True)
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS blocked_ips (
                    ip TEXT PRIMARY KEY,
                    blocked_at TIMESTAMP,
                    reason TEXT,
                    attack_type TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS attack_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    attack_type TEXT,
                    source_ip TEXT,
                    threat_level TEXT,
                    details TEXT,
                    timestamp TIMESTAMP,
                    blocked INTEGER
                )
            """)
            conn.commit()
            conn.close()
        except Exception as e:
            self.logger.error(f"Error inicializando BD: {e}")
    
    def register_notification_callback(self, callback: Callable, channel: str = "all"):
        """
        Registrar callback para notificaciones
        
        Args:
            callback: Función a llamar con (message, channel)
            channel: "telegram", "whatsapp", "all"
        """
        self.notification_callbacks.append((callback, channel))
        self.logger.info(f"Callback registrado para canal: {channel}")
    
    def set_telegram_bot(self, bot):
        """Configurar bot de Telegram para notificaciones"""
        self.telegram_bot = bot
        self.logger.info("Bot de Telegram configurado para notificaciones")
    
    def set_whatsapp_handler(self, handler):
        """Configurar handler de WhatsApp para notificaciones"""
        self.whatsapp_handler = handler
        self.logger.info("Handler de WhatsApp configurado para notificaciones")
    
    def _send_notification(self, message: str, channel: str = "all"):
        """
        Enviar notificación a través de los canales configurados
        
        Args:
            message: Mensaje a enviar
            channel: "telegram", "whatsapp", "all"
        """
        for callback, cb_channel in self.notification_callbacks:
            if cb_channel == "all" or cb_channel == channel:
                try:
                    callback(message, channel)
                except Exception as e:
                    self.logger.error(f"Error en callback de notificación: {e}")
        
        # Enviar directamente a Telegram si está configurado
        if channel in ["telegram", "all"] and self.telegram_bot:
            try:
                # Enviar a administradores configurados
                admins = os.getenv("TELEGRAM_ADMIN_IDS", "").split(",")
                for admin in admins:
                    if admin.strip():
                        self.telegram_bot.send_message(admin.strip(), message)
            except Exception as e:
                self.logger.error(f"Error enviando notificación Telegram: {e}")
        
        # Enviar directamente a WhatsApp si está configurado
        if channel in ["whatsapp", "all"] and self.whatsapp_handler:
            try:
                admins = os.getenv("WHATSAPP_ADMIN_NUMBERS", "").split(",")
                for admin in admins:
                    if admin.strip():
                        self.whatsapp_handler.send_message(admin.strip(), message)
            except Exception as e:
                self.logger.error(f"Error enviando notificación WhatsApp: {e}")
    
    def _detect_attack(self, source_ip: str, attack_type: AttackType, 
                       details: Dict, threat_level: ThreatLevel = ThreatLevel.MEDIUM):
        """
        Detectar y registrar un ataque
        
        Args:
            source_ip: IP del atacante
            attack_type: Tipo de ataque
            details: Detalles del ataque
            threat_level: Nivel de amenaza
        """
        # Obtener geolocalización
        geo_info = self._get_ip_geolocation(source_ip)
        
        # Crear evento
        event = AttackEvent(
            id=f"attack_{int(time.time())}_{uuid4().hex[:6]}",
            attack_type=attack_type,
            source_ip=source_ip,
            threat_level=threat_level,
            details=details,
            geo_info=geo_info
        )
        
        with self.lock:
            self.attack_events.append(event)
            self.stats["attacks_detected"] += 1
            
            # Bloquear IP si la amenaza es alta o crítica
            if threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
                self._block_ip(source_ip, str(attack_type.value))
        
        # Preparar mensaje de notificación
        threat_icons = {
            ThreatLevel.LOW: "⚠️",
            ThreatLevel.MEDIUM: "⚠️⚠️",
            ThreatLevel.HIGH: "🚨",
            ThreatLevel.CRITICAL: "💀"
        }
        
        location = f"📍 {geo_info.get('city', 'Desconocida')}, {geo_info.get('country', 'Desconocido')}" if geo_info else "📍 Ubicación desconocida"
        
        message = f"""
{threat_icons.get(threat_level, '⚠️')} *ALERTA DE SEGURIDAD* {threat_icons.get(threat_level, '⚠️')}

*Tipo:* {attack_type.value.replace('_', ' ').upper()}
*IP:* `{source_ip}`
{location}
*Nivel:* {threat_level.value.upper()}
*Detalles:* {json.dumps(details, indent=2)}
*Hora:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{self._get_recommendation(attack_type)}
        """
        
        # Enviar notificación a todos los canales
        self._send_notification(message.strip(), "all")
        
        # Guardar en BD
        self._save_attack_to_db(event)
        
        self.logger.warning(f"🚨 ATAQUE DETECTADO: {attack_type.value} desde {source_ip} - {threat_level.value}")
    
    def _get_ip_geolocation(self, ip: str) -> Optional[Dict]:
        """Obtener geolocalización de una IP"""
        if ip.startswith("127.") or ip.startswith("192.168.") or ip.startswith("10."):
            return {"country": "Local", "city": "Red Local"}
        
        if REQUESTS_AVAILABLE:
            try:
                response = requests.get(f"http://ip-api.com/json/{ip}", timeout=5)
                if response.ok:
                    data = response.json()
                    if data.get("status") == "success":
                        return {
                            "country": data.get("country", "Desconocido"),
                            "city": data.get("city", "Desconocida"),
                            "region": data.get("regionName", ""),
                            "isp": data.get("isp", ""),
                            "lat": data.get("lat"),
                            "lon": data.get("lon")
                        }
            except Exception:
                pass
        return None
    
    def _get_recommendation(self, attack_type: AttackType) -> str:
        """Obtener recomendación según tipo de ataque"""
        recommendations = {
            AttackType.PORT_SCAN: "*Recomendación:* Bloquear IP y revisar firewall",
            AttackType.SSH_BRUTE: "*Recomendación:* Cambiar contraseñas, deshabilitar root login, usar fail2ban",
            AttackType.HTTP_SCAN: "*Recomendación:* Revisar logs de web, actualizar aplicaciones",
            AttackType.SQL_INJECTION: "*Recomendación:* Revisar consultas SQL, usar prepared statements",
            AttackType.DOS_ATTEMPT: "*Recomendación:* Activar rate limiting, contactar ISP",
            AttackType.SUSPICIOUS: "*Recomendación:* Monitorear tráfico, revisar logs"
        }
        return recommendations.get(attack_type, "*Recomendación:* Monitorear la situación")
    
    def _block_ip(self, ip: str, reason: str):
        """Bloquear una IP"""
        if ip in self.blocked_ips:
            return
        
        self.blocked_ips[ip] = datetime.now()
        self.stats["ips_blocked"] += 1
        
        # Intentar bloquear con iptables (Linux)
        try:
            if sys.platform.startswith('linux'):
                subprocess.run(["iptables", "-A", "INPUT", "-s", ip, "-j", "DROP"], 
                              timeout=5, capture_output=True)
                self.logger.info(f"IP {ip} bloqueada con iptables")
        except Exception as e:
            self.logger.error(f"Error bloqueando IP con iptables: {e}")
        
        # Guardar en BD
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute(
                "INSERT OR REPLACE INTO blocked_ips (ip, blocked_at, reason) VALUES (?, ?, ?)",
                (ip, datetime.now().isoformat(), reason)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            self.logger.error(f"Error guardando IP bloqueada: {e}")
        
        self._send_notification(
            f"🔒 *IP BLOQUEADA*\n\nIP: `{ip}`\nRazón: {reason}\nHora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "all"
        )
    
    def _unblock_ip(self, ip: str) -> bool:
        """Desbloquear una IP"""
        if ip not in self.blocked_ips:
            return False
        
        del self.blocked_ips[ip]
        
        # Intentar desbloquear con iptables
        try:
            if sys.platform.startswith('linux'):
                subprocess.run(["iptables", "-D", "INPUT", "-s", ip, "-j", "DROP"], 
                              timeout=5, capture_output=True)
        except Exception:
            pass
        
        # Eliminar de BD
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("DELETE FROM blocked_ips WHERE ip = ?", (ip,))
            conn.commit()
            conn.close()
        except Exception:
            pass
        
        return True
    
    def _save_attack_to_db(self, event: AttackEvent):
        """Guardar evento de ataque en BD"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute(
                """INSERT INTO attack_log 
                   (attack_type, source_ip, threat_level, details, timestamp, blocked) 
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (event.attack_type.value, event.source_ip, event.threat_level.value,
                 json.dumps(event.details), event.timestamp.isoformat(), 
                 1 if event.blocked else 0)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            self.logger.error(f"Error guardando ataque: {e}")
    
    # ============================================================
    # COMANDOS REMOTOS (Telegram/WhatsApp)
    # ============================================================
    
    def _cmd_status(self, args: List[str], sender: str) -> str:
        """Comando: status - Muestra estado del sistema"""
        stats = self.get_stats()
        uptime = stats.get("uptime", "N/A")
        
        blocked_count = len(self.blocked_ips)
        
        return f"""
📊 *ESTADO DE SWARMIA*

🟢 Sistema: *ACTIVO*
⏱️ Tiempo activo: {uptime}
📝 Tareas creadas: {stats['tasks_created']}
✅ Tareas completadas: {stats['tasks_completed']}
❌ Tareas fallidas: {stats['tasks_failed']}
🚨 Ataques detectados: {stats['attacks_detected']}
🔒 IPs bloqueadas: {blocked_count}
🤖 Agentes activos: {stats['agents_active']}

🛡️ Anti-Hacking: *ACTIVO*
        """
    
    def _cmd_install(self, args: List[str], sender: str) -> str:
        """Comando: install <paquete> - Instala un paquete"""
        if not args:
            return "❌ Uso: install <nombre_paquete>"
        
        package = args[0]
        
        try:
            self._send_notification(f"📦 Instalando {package} solicitado por {sender}", "all")
            
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", package],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                return f"✅ Paquete {package} instalado correctamente\n\n{result.stdout[:500]}"
            else:
                return f"❌ Error instalando {package}\n\n{result.stderr[:500]}"
        except subprocess.TimeoutExpired:
            return f"⏰ Timeout instalando {package}"
        except Exception as e:
            return f"❌ Error: {e}"
    
    def _cmd_update(self, args: List[str], sender: str) -> str:
        """Comando: update - Actualiza SwarmIA"""
        self._send_notification(f"🔄 Actualizando SwarmIA solicitado por {sender}", "all")
        
        try:
            result = subprocess.run(
                ["git", "pull"],
                cwd=Path(__file__).parent.parent.parent,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                return f"✅ Actualización completada\n\n{result.stdout[:500]}"
            else:
                return f"❌ Error en actualización\n\n{result.stderr[:500]}"
        except Exception as e:
            return f"❌ Error: {e}"
    
    def _cmd_restart(self, args: List[str], sender: str) -> str:
        """Comando: restart - Reinicia SwarmIA"""
        self._send_notification(f"🔄 Reiniciando SwarmIA solicitado por {sender}", "all")
        
        # Programar reinicio en un hilo separado
        def restart():
            time.sleep(2)
            os._exit(0)  # El supervisor reiniciará el proceso
        
        threading.Thread(target=restart, daemon=True).start()
        return "🔄 Reiniciando SwarmIA..."
    
    def _cmd_block_ip(self, args: List[str], sender: str) -> str:
        """Comando: block_ip <ip> - Bloquea una IP"""
        if not args:
            return "❌ Uso: block_ip <dirección_ip>"
        
        ip = args[0]
        self._block_ip(ip, f"Comando manual por {sender}")
        return f"🔒 IP {ip} bloqueada"
    
    def _cmd_unblock_ip(self, args: List[str], sender: str) -> str:
        """Comando: unblock_ip <ip> - Desbloquea una IP"""
        if not args:
            return "❌ Uso: unblock_ip <dirección_ip>"
        
        ip = args[0]
        if self._unblock_ip(ip):
            return f"🔓 IP {ip} desbloqueada"
        else:
            return f"⚠️ IP {ip} no estaba bloqueada"
    
    def _cmd_scan(self, args: List[str], sender: str) -> str:
        """Comando: scan [ip] - Escanea puertos de una IP"""
        target = args[0] if args else "localhost"
        
        self._send_notification(f"🔍 Escaneando {target} solicitado por {sender}", "all")
        
        # Escaneo rápido de puertos comunes
        common_ports = [22, 80, 443, 8080, 3306, 5432, 6379]
        open_ports = []
        
        for port in common_ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex((target, port))
                sock.close()
                if result == 0:
                    open_ports.append(port)
            except:
                pass
        
        result = f"🔍 *Escaneo de {target}*\n\n"
        result += f"Puertos abiertos: {', '.join(map(str, open_ports)) if open_ports else 'Ninguno'}\n"
        
        return result
    
    def _cmd_info(self, args: List[str], sender: str) -> str:
        """Comando: info [ip] - Información de una IP"""
        target = args[0] if args else socket.gethostbyname(socket.gethostname())
        
        geo = self._get_ip_geolocation(target)
        
        if geo:
            return f"""
📍 *Información de IP: {target}*

🌍 País: {geo.get('country', 'N/A')}
🏙️ Ciudad: {geo.get('city', 'N/A')}
🗺️ Región: {geo.get('region', 'N/A')}
📡 ISP: {geo.get('isp', 'N/A')}
📌 Coordenadas: {geo.get('lat', 'N/A')}, {geo.get('lon', 'N/A')}
            """
        else:
            return f"❌ No se pudo obtener información de {target}"
    
    def _cmd_whois(self, args: List[str], sender: str) -> str:
        """Comando: whois <ip> - Información WHOIS"""
        if not args:
            return "❌ Uso: whois <ip>"
        
        ip = args[0]
        
        try:
            result = subprocess.run(["whois", ip], capture_output=True, text=True, timeout=10)
            output = result.stdout[:1000]
            return f"📋 *WHOIS para {ip}*\n\n```\n{output}\n```"
        except Exception as e:
            return f"❌ Error: {e}"
    
    def _cmd_uptime(self, args: List[str], sender: str) -> str:
        """Comando: uptime - Tiempo de actividad"""
        stats = self.get_stats()
        uptime = stats.get("uptime", "N/A")
        
        # Uptime del sistema
        try:
            import subprocess
            sys_uptime = subprocess.run(["uptime"], capture_output=True, text=True).stdout.strip()
        except:
            sys_uptime = "N/A"
        
        return f"""
⏱️ *Tiempo de actividad*

SwarmIA: {uptime}
Sistema: {sys_uptime}
        """
    
    def _cmd_logs(self, args: List[str], sender: str) -> str:
        """Comando: logs [n] - Últimos logs"""
        n = int(args[0]) if args and args[0].isdigit() else 20
        
        log_path = Path("logs/swarmia.log")
        if not log_path.exists():
            return "📄 No hay logs disponibles"
        
        try:
            with open(log_path, 'r') as f:
                lines = f.readlines()[-n:]
            return f"📋 *Últimos {n} logs*\n\n```\n{''.join(lines)}\n```"
        except Exception as e:
            return f"❌ Error leyendo logs: {e}"
    
    def _cmd_help(self, args: List[str], sender: str) -> str:
        """Comando: help - Muestra ayuda"""
        return """
📖 *Comandos disponibles*

| Comando | Descripción |
|---------|-------------|
| `status` | Estado del sistema |
| `install <paquete>` | Instalar paquete Python |
| `update` | Actualizar SwarmIA |
| `restart` | Reiniciar SwarmIA |
| `block_ip <ip>` | Bloquear IP |
| `unblock_ip <ip>` | Desbloquear IP |
| `scan [ip]` | Escanear puertos |
| `info [ip]` | Información de IP |
| `whois <ip>` | WHOIS de IP |
| `uptime` | Tiempo de actividad |
| `logs [n]` | Últimos n logs |
| `help` | Esta ayuda |

*Ejemplos:*
`install requests`
`block_ip 192.168.1.100`
`scan 8.8.8.8`
        """
    
    def process_remote_command(self, command: str, sender: str, channel: str = "telegram") -> str:
        """
        Procesar comando remoto desde Telegram/WhatsApp
        
        Args:
            command: Comando completo (ej: "install requests")
            sender: ID del remitente
            channel: Canal de origen ("telegram" o "whatsapp")
        
        Returns:
            Respuesta del comando
        """
        parts = command.strip().split()
        if not parts:
            return "❌ Comando vacío"
        
        cmd = parts[0].lower()
        args = parts[1:]
        
        if cmd in self.allowed_remote_commands:
            self.logger.info(f"Comando remoto '{cmd}' desde {sender} ({channel})")
            self._send_notification(f"📡 Comando remoto ejecutado: {command} por {sender}", channel)
            return self.allowed_remote_commands[cmd](args, sender)
        else:
            return f"❌ Comando desconocido: {cmd}\nEscribe 'help' para ver comandos disponibles"
    
    # ============================================================
    # Lifecycle Methods
    # ============================================================
    
    def start(self) -> bool:
        """Iniciar supervisor"""
        if self.running:
            self.logger.warning("Supervisor ya está en ejecución")
            return False
        
        try:
            self.logger.info("Iniciando supervisor...")
            self.running = True
            self.stats["start_time"] = datetime.now()
            
            # Iniciar threads
            self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
            self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
            self.security_thread = threading.Thread(target=self._security_monitor_loop, daemon=True)
            
            self.worker_thread.start()
            self.cleanup_thread.start()
            self.heartbeat_thread.start()
            self.security_thread.start()
            
            self.logger.info("Supervisor iniciado correctamente")
            
            # Notificar inicio
            self._send_notification("🚀 SwarmIA iniciado. Sistema anti-hacking ACTIVO.", "all")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error iniciando supervisor: {e}")
            self.running = False
            return False
    
    def _security_monitor_loop(self):
        """Loop de monitoreo de seguridad"""
        while self.running:
            try:
                time.sleep(5)
                self._check_for_threats()
            except Exception as e:
                self.logger.error(f"Error en monitor de seguridad: {e}")
    
    def _check_for_threats(self):
        """Verificar amenazas en tiempo real"""
        # Verificar logs del sistema para detectar ataques
        try:
            log_path = Path("/var/log/auth.log")
            if log_path.exists():
                with open(log_path, 'r') as f:
                    lines = f.readlines()[-100:]
                
                for line in lines:
                    if "Failed password" in line:
                        # Extraer IP
                        import re
                        match = re.search(r'from (\d+\.\d+\.\d+\.\d+)', line)
                        if match:
                            ip = match.group(1)
                            if ip not in self.blocked_ips:
                                self._detect_attack(
                                    source_ip=ip,
                                    attack_type=AttackType.SSH_BRUTE,
                                    details={"log_line": line.strip()},
                                    threat_level=ThreatLevel.MEDIUM
                                )
        except Exception as e:
            pass
    
    # ============================================================
    # Worker Loops
    # ============================================================
    
    def _worker_loop(self):
        """Loop principal de procesamiento de tareas"""
        self.logger.info("🟢 WORKER LOOP INICIADO - ESPERANDO TAREAS...")
        while self.running:
            try:
                priority, timestamp, task_id = self.task_queue.get(timeout=1)
                self.logger.info(f"📦 WORKER OBTUVO TAREA: {task_id}")
                
                with self.lock:
                    task = self.tasks.get(task_id)
                    if not task or task.status != TaskStatus.PENDING:
                        self.logger.warning(f"⚠️ Tarea {task_id} no válida: status={task.status if task else 'None'}")
                        continue
                
                self._process_task(task)
                
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"❌ Error en worker: {e}", exc_info=True)
    
    def _process_task(self, task: Task):
        """Procesar una tarea - asigna al agente adecuado"""
        # Verificar límite concurrente
        with self.lock:
            if self.active_tasks_count >= self.max_concurrent_tasks:
                self._requeue_task(task)
                return
            self.active_tasks_count += 1
        
        try:
            # 1. PRIMERO BUSCAR UN AGENTE QUE PUEDA MANEJAR ESTA TAREA
            agente = None
            for agent in self.agents.values():
                # Verificar por tipo de tarea en capacidades
                if task.type in agent.capabilities:
                    agente = agent
                    break
                # Verificar si el agente tiene método can_handle
                if hasattr(agent, 'can_handle') and agent.can_handle(task.type):
                    agente = agent
                    break
            
            # 2. SI HAY AGENTE, ASIGNAR LA TAREA
            if agente:
                self.logger.info(f"✅ Tarea {task.id} asignada a agente {agente.name}")
                
                with self.lock:
                    task.status = TaskStatus.RUNNING
                    task.started_at = datetime.now()
                    task.assigned_agent = agente.id
                    if hasattr(agente, 'current_tasks'):
                        agente.current_tasks.append(task.id)
                    if hasattr(agente, 'status'):
                        agente.status = AgentStatus.BUSY
                
                try:
                    # Ejecutar el agente
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    tarea_agente = {
                        "tipo": task.type,
                        "descripcion": task.data.get("descripcion", str(task.data)),
                        "parametros": task.data,
                        "id": task.id
                    }
                    
                    resultado = loop.run_until_complete(agente.ejecutar(tarea_agente))
                    loop.close()
                    
                    with self.lock:
                        if resultado.exito:
                            task.status = TaskStatus.COMPLETED
                            task.result = resultado.datos
                            self.logger.info(f"✅ Tarea {task.id} completada por {agente.name}")
                        else:
                            task.status = TaskStatus.FAILED
                            task.error = resultado.error
                            self.logger.error(f"❌ Tarea {task.id} falló: {resultado.error}")
                        
                        task.completed_at = datetime.now()
                        if hasattr(agente, 'current_tasks') and task.id in agente.current_tasks:
                            agente.current_tasks.remove(task.id)
                        if hasattr(agente, 'status') and not agente.current_tasks:
                            agente.status = AgentStatus.IDLE
                    
                    self.stats["tasks_completed" if resultado.exito else "tasks_failed"] += 1
                    
                except Exception as e:
                    self._handle_task_failure(task, e)
            
            # 3. SI NO HAY AGENTE, BUSCAR HANDLER
            else:
                handler = self.task_handlers.get(task.type)
                if handler:
                    self.logger.info(f"📦 Tarea {task.id} usando handler directo")
                    
                    # Buscar agente disponible (para el handler)
                    agent = self._assign_agent(task)
                    if not agent:
                        self._requeue_task(task)
                        return
                    
                    with self.lock:
                        task.status = TaskStatus.RUNNING
                        task.started_at = datetime.now()
                        task.assigned_agent = agent.id
                        agent.current_tasks.append(task.id)
                        agent.status = AgentStatus.BUSY
                    
                    self.logger.info(f"Tarea {task.id} asignada a agente {agent.name} para handler")
                    
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(handler, task.data, agent, self._notify_progress)
                        result = future.result(timeout=task.timeout)
                    
                    with self.lock:
                        if result.get("success"):
                            task.status = TaskStatus.COMPLETED
                            task.result = result
                        else:
                            task.status = TaskStatus.FAILED
                            task.error = result.get("error", "Error desconocido")
                        task.completed_at = datetime.now()
                        agent.current_tasks.remove(task.id)
                        if not agent.current_tasks:
                            agent.status = AgentStatus.IDLE
                    
                    self.stats["tasks_completed" if result.get("success") else "tasks_failed"] += 1
                else:
                    self.logger.error(f"❌ No hay handler ni agente para tarea tipo: {task.type}")
                    with self.lock:
                        task.status = TaskStatus.FAILED
                        task.error = f"No hay agente disponible para: {task.type}"
                        task.completed_at = datetime.now()
                    self.stats["tasks_failed"] += 1
        
        except concurrent.futures.TimeoutError:
            self.logger.error(f"Tarea {task.id} timeout")
            self._handle_task_failure(task, Exception("Timeout"))
        except Exception as e:
            self._handle_task_failure(task, e)
        finally:
            with self.lock:
                self.active_tasks_count -= 1
    
    def _assign_agent(self, task: Task) -> Optional[Agent]:
        """Asignar agente con balanceo de carga"""
        with self.lock:
            available = []
            for agent in self.agents.values():
                if agent.status == AgentStatus.IDLE:
                    if task.type in agent.capabilities or "*" in agent.capabilities:
                        load = len(agent.current_tasks)
                        available.append((load, agent))
            
            if not available:
                return None
            
            available.sort(key=lambda x: x[0])
            return available[0][1]
    
    def _notify_progress(self, task_id: str, progress: float, message: str):
        """Notificar progreso de tarea"""
        for callback in self.progress_callbacks:
            try:
                callback(task_id, progress, message)
            except Exception as e:
                self.logger.error(f"Error en callback de progreso: {e}")
    
    def _requeue_task(self, task: Task):
        """Reencolar tarea para reintento"""
        if task.retry_count < task.max_retries:
            task.retry_count += 1
            priority_value = 5 - task.priority.value
            self.task_queue.put((priority_value, time.time(), task.id))
            self.logger.info(f"Tarea {task.id} reencolada (intento {task.retry_count}/{task.max_retries})")
        else:
            self._handle_task_failure(task, Exception("Max retries exceeded"))
    
    def _handle_task_failure(self, task: Task, error: Exception):
        """Manejar fallo de tarea"""
        with self.lock:
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.now()
            task.error = str(error)
            
            if task.assigned_agent:
                agent = self.agents.get(task.assigned_agent)
                if agent and task.id in agent.current_tasks:
                    agent.current_tasks.remove(task.id)
                    if not agent.current_tasks:
                        agent.status = AgentStatus.IDLE
        
        self.stats["tasks_failed"] += 1
        self.logger.error(f"Tarea {task.id} falló: {error}")
    
    def _cleanup_loop(self):
        """Loop de limpieza de tareas antiguas"""
        while self.running:
            try:
                time.sleep(3600)
                self.cleanup_old_tasks()
            except Exception as e:
                self.logger.error(f"Error en limpieza: {e}")
    
    def _heartbeat_loop(self):
        """Loop de heartbeat para agentes"""
        while self.running:
            try:
                time.sleep(30)
                self._check_agent_heartbeats()
            except Exception as e:
                self.logger.error(f"Error en heartbeat: {e}")
    
    def _check_agent_heartbeats(self):
        """Verificar heartbeats de agentes"""
        now = datetime.now()
        with self.lock:
            for agent_id, agent in list(self.agents.items()):
                if (now - agent.last_heartbeat).seconds > 60:
                    self.logger.warning(f"Agente {agent.name} heartbeat timeout")
                    agent.status = AgentStatus.OFFLINE
    
    # ============================================================
    # AGENT SELECTION
    # ============================================================
    
    def _find_agent_for_task(self, task_type: str):
        """Encuentra el agente adecuado para un tipo de tarea"""
        for agent in self.agents.values():
            if task_type in agent.capabilities:
                return agent
            if hasattr(agent, 'can_handle') and agent.can_handle(task_type):
                return agent
        return None
    
    # ============================================================
    # Task Management
    # ============================================================
    
    def register_task_handler(self, task_type: str, handler: Callable):
        """Registrar handler para tipo de tarea"""
        self.task_handlers[task_type] = handler
        self.logger.info(f"Handler registrado para tarea: {task_type}")
    
    # ============================================================
    # Task Management
    # ============================================================
    
    def register_task_handler(self, task_type: str, handler: Callable):
        """Registrar handler para tipo de tarea"""
        self.task_handlers[task_type] = handler
        self.logger.info(f"Handler registrado para tarea: {task_type}")
    
    def create_task(self, task_type: str, data: Dict[str, Any],
                    priority: TaskPriority = TaskPriority.NORMAL,
                    source: str = "system", timeout: int = None) -> str:
        """Crear una nueva tarea"""
        with self.lock:
            self.task_counter += 1
            task_id = f"task_{self.task_counter}_{uuid4().hex[:8]}"
            
            task = Task(
                id=task_id,
                type=task_type,
                data=data,
                priority=priority,
                source=source,
                timeout=timeout or self.task_timeout_default
            )
            
            self.tasks[task_id] = task
            priority_value = 5 - priority.value
            self.task_queue.put((priority_value, time.time(), task_id))
            self.stats["tasks_created"] += 1
            
            self.logger.debug(f"Tarea creada: {task_id} (prioridad={priority.name})")
            return task_id
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Obtener una tarea por ID"""
        with self.lock:
            return self.tasks.get(task_id)
    
    def get_tasks(self, status: Optional[TaskStatus] = None, limit: int = 100) -> List[Task]:
        """Obtener lista de tareas"""
        with self.lock:
            tasks = list(self.tasks.values())
            if status:
                tasks = [t for t in tasks if t.status == status]
            tasks.sort(key=lambda t: t.created_at, reverse=True)
            return tasks[:limit]
    
    def cancel_task(self, task_id: str, reason: str = "Cancelado por usuario") -> bool:
        """Cancelar una tarea"""
        with self.lock:
            task = self.tasks.get(task_id)
            if not task:
                return False
            
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                return False
            
            task.status = TaskStatus.CANCELLED
            task.error = reason
            task.completed_at = datetime.now()
            
            if task.assigned_agent:
                agent = self.agents.get(task.assigned_agent)
                if agent and task_id in agent.current_tasks:
                    agent.current_tasks.remove(task_id)
            
            self.stats["tasks_cancelled"] += 1
            self.logger.info(f"Tarea cancelada: {task_id} - {reason}")
            return True
    
    def retry_task(self, task_id: str) -> bool:
        """Reintentar una tarea fallida"""
        with self.lock:
            task = self.tasks.get(task_id)
            if not task or task.status != TaskStatus.FAILED:
                return False
            
            task.status = TaskStatus.PENDING
            task.started_at = None
            task.completed_at = None
            task.assigned_agent = None
            task.error = None
            task.retry_count += 1
            
            priority_value = 5 - task.priority.value
            self.task_queue.put((priority_value, time.time(), task_id))
            
            self.logger.info(f"Reintento programado: {task_id} (intento {task.retry_count})")
            return True
    
    def cleanup_old_tasks(self, max_age_hours: int = 24):
        """Limpiar tareas antiguas"""
        with self.lock:
            cutoff = datetime.now().timestamp() - (max_age_hours * 3600)
            to_remove = [tid for tid, t in self.tasks.items() 
                        if t.completed_at and t.completed_at.timestamp() < cutoff]
            
            for tid in to_remove:
                del self.tasks[tid]
            
            if to_remove:
                self.logger.info(f"Limpiadas {len(to_remove)} tareas antiguas")
    
    # ============================================================
    # Agent Management
    # ============================================================
    
    def register_agent(self, agent_id: str, name: str, agent_type: str,
                       capabilities: List[str], metadata: Optional[Dict] = None) -> bool:
        """Registrar un nuevo agente"""
        with self.lock:
            if agent_id in self.agents:
                self.logger.warning(f"Agente ya registrado: {agent_id}")
                return False
            
            agent = Agent(
                id=agent_id,
                name=name,
                type=agent_type,
                capabilities=capabilities,
                metadata=metadata or {}
            )
            
            self.agents[agent_id] = agent
            self.agent_capabilities[agent_id] = capabilities
            self.stats["agents_registered"] += 1
            self.stats["agents_active"] += 1
            
            self.logger.info(f"Agente registrado: {name} (tipo={agent_type})")
            return True
    
    def unregister_agent(self, agent_id: str) -> bool:
        """Desregistrar un agente"""
        with self.lock:
            if agent_id not in self.agents:
                return False
            
            agent = self.agents[agent_id]
            for task_id in agent.current_tasks:
                self.cancel_task(task_id, f"Agente {agent.name} desregistrado")
            
            del self.agents[agent_id]
            del self.agent_capabilities[agent_id]
            self.stats["agents_active"] -= 1
            
            self.logger.info(f"Agente desregistrado: {agent.name}")
            return True
    
    def update_agent_heartbeat(self, agent_id: str) -> bool:
        """Actualizar heartbeat de un agente"""
        with self.lock:
            agent = self.agents.get(agent_id)
            if not agent:
                return False
            
            agent.last_heartbeat = datetime.now()
            if agent.status == AgentStatus.OFFLINE:
                agent.status = AgentStatus.IDLE
            return True
    
    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Obtener un agente por ID"""
        with self.lock:
            return self.agents.get(agent_id)
    
    def get_agents(self, agent_type: Optional[str] = None) -> List[Agent]:
        """Obtener lista de agentes"""
        with self.lock:
            agents = list(self.agents.values())
            if agent_type:
                agents = [a for a in agents if a.type == agent_type]
            return agents
    
    # ============================================================
    # Statistics
    # ============================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas del supervisor"""
        with self.lock:
            uptime = None
            if self.stats["start_time"]:
                uptime = datetime.now() - self.stats["start_time"]
                uptime = str(uptime).split('.')[0]
            
            tasks_by_status = {}
            for status in TaskStatus:
                tasks_by_status[status.value] = len([t for t in self.tasks.values() if t.status == status])
            
            agents_by_type = {}
            for agent in self.agents.values():
                agents_by_type[agent.type] = agents_by_type.get(agent.type, 0) + 1
            
            return {
                **self.stats,
                "uptime": uptime,
                "tasks_by_status": tasks_by_status,
                "agents_by_type": agents_by_type,
                "total_tasks": len(self.tasks),
                "total_agents": len(self.agents),
                "queue_size": self.task_queue.qsize(),
                "blocked_ips_count": len(self.blocked_ips),
                "attacks_detected": len(self.attack_events)
            }
    
    def emergency_stop(self):
        """Parada de emergencia - cancelar todas las tareas en ejecución"""
        with self.lock:
            running = [t for t in self.tasks.values() if t.status == TaskStatus.RUNNING]
            for task in running:
                task.status = TaskStatus.CANCELLED
                task.error = "Emergency stop"
                task.completed_at = datetime.now()
                
                if task.assigned_agent:
                    agent = self.agents.get(task.assigned_agent)
                    if agent and task.id in agent.current_tasks:
                        agent.current_tasks.remove(task.id)
            
            self.logger.warning(f"Parada de emergencia: canceladas {len(running)} tareas")
    
    def stop(self):
        """Detener supervisor"""
        if not self.running:
            return
        
        self.logger.info("Deteniendo supervisor...")
        self.running = False
        
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=5)
        if self.cleanup_thread and self.cleanup_thread.is_alive():
            self.cleanup_thread.join(timeout=5)
        
        self._send_notification("🛑 SwarmIA detenido", "all")
        self.logger.info("Supervisor detenido")


# ============================================================
# Factory Function
# ============================================================

def create_supervisor(config=None) -> Supervisor:
    """Create supervisor instance"""
    return Supervisor(config)


# ============================================================
# Example Usage
# ============================================================

def example_usage():
    """Ejemplo de uso del supervisor"""
    print("👨‍💼 Supervisor Example with Anti-Hacking\n")
    
    supervisor = create_supervisor()
    
    # Registrar agentes de ejemplo
    supervisor.register_agent(
        agent_id="agent_chat_001",
        name="Chat Agent",
        agent_type="chat",
        capabilities=["process_message", "complete_conversation", "analyze_sentiment"]
    )
    
    supervisor.register_agent(
        agent_id="agent_agg_001",
        name="Aggressive Agent",
        agent_type="aggressive",
        capabilities=["execute_action", "monitor_system"]
    )
    
    # Iniciar supervisor
    if supervisor.start():
        print("✅ Supervisor iniciado\n")
        
        # Simular detección de ataque
        print("🔍 Simulando detección de ataque...")
        supervisor._detect_attack(
            source_ip="192.168.1.100",
            attack_type=AttackType.SSH_BRUTE,
            details={"username": "root", "attempts": 15},
            threat_level=ThreatLevel.HIGH
        )
        
        # Probar comando remoto simulado
        print("\n📡 Probando comando remoto...")
        response = supervisor.process_remote_command("status", "user_123", "telegram")
        print(response)
        
        time.sleep(2)
        
        # Obtener estadísticas
        stats = supervisor.get_stats()
        print(f"\n📊 Estadísticas:")
        print(f"  Tareas creadas: {stats['tasks_created']}")
        print(f"  Ataques detectados: {stats['attacks_detected']}")
        print(f"  IPs bloqueadas: {stats['blocked_ips_count']}")
        
        # Detener supervisor
        supervisor.stop()
        print("\n🛑 Supervisor detenido")
    else:
        print("❌ Error iniciando supervisor")


if __name__ == "__main__":
    example_usage()
