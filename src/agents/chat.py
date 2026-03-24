#!/usr/bin/env python3
"""
Chat Agent Module
Handles conversational AI interactions with DeepSeek and Llama
Integrated with anti-hacking system for message analysis
"""

import os
import sys
import logging
import re
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

from src.core.config import Config
from src.core.supervisor import Supervisor, AttackType, ThreatLevel
from src.core.agente import Agente, TipoAgente, ResultadoTarea, EstadoAgente

# Import AI handlers
try:
    from src.ai.deepseek import create_deepseek_handler, DeepSeekError
    from src.ai.llama import create_llama_handler, LlamaError
except ImportError:
    # Fallback para cuando los módulos no existen
    class DeepSeekError(Exception): pass
    class LlamaError(Exception): pass
    def create_deepseek_handler(api_key, model): return None
    def create_llama_handler(model_path, model_name): return None


# ============================================================
# Message Analyzer for Security
# ============================================================

class MessageSecurityAnalyzer:
    """Analiza mensajes para detectar contenido malicioso"""
    
    def __init__(self, supervisor: Supervisor):
        self.supervisor = supervisor
        self.logger = logging.getLogger("swarmia.chat.security")
        
        # Patrones de ataque comunes
        self.attack_patterns = {
            "sql_injection": [
                r"(?i)(SELECT|INSERT|UPDATE|DELETE|DROP|UNION).*(FROM|INTO|WHERE)",
                r"(?i)(\bOR\b|\bAND\b).*=",
                r"(--|#|;|\|)",
                r"(?i)(xp_cmdshell|sp_executesql|exec\s+master)",
            ],
            "xss": [
                r"<script.*?>.*?</script>",
                r"on\w+\s*=",
                r"javascript:",
                r"<iframe.*?>",
                r"<img.*?onerror=",
            ],
            "command_injection": [
                r"(?i)(;|\||&&|`).*(ls|dir|cat|echo|wget|curl|nc|bash|sh)",
                r"(?i)(\$\{.*?\})",
                r"(?i)(eval|exec|system|passthru|shell_exec)",
            ],
            "path_traversal": [
                r"\.\./",
                r"\.\.\\",
                r"/etc/passwd",
                r"/etc/shadow",
                r"C:\\Windows\\System32",
            ],
            "ssh_brute": [
                r"(?i)(password|passwd|root|admin).*(attempt|try|login)",
                r"(?i)(ssh).*(brute|force|attack)",
            ]
        }
        
        # Palabras clave sospechosas
        self.suspicious_keywords = [
            "hack", "crack", "exploit", "vulnerability", "backdoor",
            "bypass", "inject", "payload", "shell", "root", "admin",
            "password", "credential", "dump", "breach", "attack"
        ]
    
    def analyze(self, message: str, sender: str) -> Dict[str, Any]:
        """
        Analizar mensaje en busca de contenido malicioso
        
        Returns:
            Dict con resultado del análisis
        """
        result = {
            "is_malicious": False,
            "attack_type": None,
            "threat_level": ThreatLevel.LOW,
            "patterns_found": [],
            "suspicious_keywords": []
        }
        
        # Verificar patrones de ataque
        for attack_type, patterns in self.attack_patterns.items():
            for pattern in patterns:
                if re.search(pattern, message, re.IGNORECASE):
                    result["is_malicious"] = True
                    result["attack_type"] = attack_type
                    result["patterns_found"].append(pattern)
                    result["threat_level"] = self._get_threat_level(attack_type)
                    break
            if result["is_malicious"]:
                break
        
        # Verificar palabras clave sospechosas
        for keyword in self.suspicious_keywords:
            if keyword.lower() in message.lower():
                result["suspicious_keywords"].append(keyword)
                if not result["is_malicious"]:
                    result["is_malicious"] = True
                    result["attack_type"] = "suspicious"
                    result["threat_level"] = ThreatLevel.LOW
        
        # Si es malicioso, notificar al supervisor
        if result["is_malicious"]:
            self.logger.warning(f"Mensaje malicioso detectado de {sender}: {message[:100]}")
            
            self.supervisor._detect_attack(
                source_ip=sender,
                attack_type=AttackType(result["attack_type"]) if result["attack_type"] in [a.value for a in AttackType] else AttackType.SUSPICIOUS,
                details={
                    "message": message[:500],
                    "patterns": result["patterns_found"],
                    "keywords": result["suspicious_keywords"]
                },
                threat_level=result["threat_level"]
            )
        
        return result
    
    def _get_threat_level(self, attack_type: str) -> ThreatLevel:
        """Obtener nivel de amenaza según tipo de ataque"""
        levels = {
            "sql_injection": ThreatLevel.HIGH,
            "xss": ThreatLevel.MEDIUM,
            "command_injection": ThreatLevel.CRITICAL,
            "path_traversal": ThreatLevel.HIGH,
            "ssh_brute": ThreatLevel.MEDIUM,
            "suspicious": ThreatLevel.LOW
        }
        return levels.get(attack_type, ThreatLevel.MEDIUM)


# ============================================================
# Chat Agent (hereda de Agente)
# ============================================================

class ChatAgent(Agente):
    """
    Chat agent for conversational AI interactions
    Integrated with DeepSeek and Llama handlers
    """
    
    def __init__(self, supervisor: Supervisor, config: Config):
        """
        Initialize chat agent
        
        Args:
            supervisor: Supervisor instance
            config: Configuration object
        """
        # Llamar al constructor de la clase base Agente
        super().__init__(
            id_agente="chat",
            nombre="Agente Chat",
            tipo=TipoAgente.CHAT,
            supervisor=supervisor,
            version="1.0.0"
        )
        self.config = config
        
        # AI handlers
        self.deepseek_handler = None
        self.llama_handler = None
        self.active_ai = None
        
        # Security analyzer
        self.security_analyzer = MessageSecurityAnalyzer(supervisor)
        
        # Historial de conversaciones (contexto)
        self.conversation_history: Dict[str, List[Dict]] = {}
        self.max_history_length = 50
        
        # Registrar capacidades
        self._registrar_capacidades()
        
        self.logger.info("Chat agent initialized")
    
    def _registrar_capacidades(self):
        """Registrar capacidades del agente"""
        self.registrar_capacidad(
            nombre="chatear",
            descripcion="Mantiene conversaciones naturales con el usuario",
            parametros=["mensaje", "sesion"],
            ejemplos=["hola", "qué hora es", "cómo estás"],
            nivel_riesgo="bajo"
        )
        self.registrar_capacidad(
            nombre="preguntar",
            descripcion="Responde preguntas generales",
            parametros=["pregunta"],
            ejemplos=["qué es Linux", "cómo funciona SSH"],
            nivel_riesgo="bajo"
        )
    
    async def ejecutar(self, tarea: Dict[str, Any]) -> ResultadoTarea:
        """
        Ejecuta una tarea - método requerido por la clase base Agente
        """
        mensaje = tarea.get("descripcion", "")
        session_id = tarea.get("session_id", "default")
        
        respuesta = self.process_message(mensaje, {"session_id": session_id})
        
        return ResultadoTarea(
            exito=True,
            datos={"respuesta": respuesta},
            metadatos={"session_id": session_id}
        )
    
    def _setup_logger(self) -> logging.Logger:
        """Configurar logger"""
        logger = logging.getLogger("swarmia.agents.chat")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def start(self) -> bool:
        """
        Start the chat agent
        
        Returns:
            True if started successfully
        """
        try:
            self.logger.info("Starting chat agent...")
            self.estadisticas["inicio"] = datetime.now()
            
            # Determinar proveedor de IA activo
            ai_type = getattr(self.config, 'AI_DEFAULT_PROVIDER', 'deepseek')
            
            if ai_type == "deepseek":
                self.deepseek_handler = self._create_deepseek_handler()
                self.active_ai = "deepseek"
                self.logger.info("DeepSeek AI initialized")
            
            elif ai_type == "llama":
                self.llama_handler = self._create_llama_handler()
                self.active_ai = "llama"
                self.logger.info("Llama AI initialized")
            
            elif ai_type == "mock":
                self.active_ai = "mock"
                self.logger.info("Mock AI mode (development)")
            
            else:
                self.logger.error(f"Unknown AI type: {ai_type}")
                return False
            
            self.estado = EstadoAgente.ACTIVO
            self.logger.info(f"Chat agent started successfully (provider: {self.active_ai})")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start chat agent: {e}")
            return False
    
    def _create_deepseek_handler(self):
        """Create DeepSeek handler with actual implementation"""
        api_key = getattr(self.config, 'DEEPSEEK_API_KEY', '')
        model = getattr(self.config, 'DEEPSEEK_MODEL', 'deepseek-chat')
        
        if not api_key:
            self.logger.warning("DeepSeek API key not configured, using mock mode")
            return None
        
        try:
            handler = create_deepseek_handler(api_key, model)
            # Test connection
            if handler.check_connection():
                self.logger.info("DeepSeek connection successful")
            else:
                self.logger.warning("DeepSeek connection test failed")
            return handler
        except Exception as e:
            self.logger.error(f"Failed to create DeepSeek handler: {e}")
            return None
    
    def _create_llama_handler(self):
        """Create Llama handler with actual implementation"""
        model_path = getattr(self.config, 'LLAMA_MODEL_PATH', '')
        
        if not model_path:
            self.logger.warning("Llama model path not configured, using mock mode")
            return None
        
        try:
            handler = create_llama_handler(model_path, "Local Llama")
            self.logger.info("Llama handler created")
            return handler
        except Exception as e:
            self.logger.error(f"Failed to create Llama handler: {e}")
            return None
    
    def _get_system_prompt(self) -> str:
        """Obtener prompt del sistema desde configuración"""
        default_prompt = """Eres SwarmIA, un asistente de IA mejorado. 
Eres útil, conciso y eficiente. Siempre completas las tareas por completo.
Si te preguntan sobre seguridad, recomienda buenas prácticas.
Nunca compartas información sensible ni ejecutes comandos peligrosos sin confirmación."""
        
        return getattr(self.config, 'SYSTEM_PROMPT', default_prompt)
    
    def _get_conversation_context(self, session_id: str) -> List[Dict]:
        """Obtener contexto de conversación para una sesión"""
        if session_id not in self.conversation_history:
            self.conversation_history[session_id] = []
        
        # Devolver últimos N mensajes
        return self.conversation_history[session_id][-self.max_history_length:]
    
    def _add_to_history(self, session_id: str, role: str, content: str):
        """Agregar mensaje al historial de conversación"""
        if session_id not in self.conversation_history:
            self.conversation_history[session_id] = []
        
        self.conversation_history[session_id].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        
        # Limitar historial
        if len(self.conversation_history[session_id]) > self.max_history_length:
            self.conversation_history[session_id] = self.conversation_history[session_id][-self.max_history_length:]
    
    def _detect_offensive_language(self, message: str) -> bool:
        """Detectar lenguaje ofensivo"""
        offensive_words = ["hijo de puta", "puta", "mierda", "idiota", "imbecil", "estupido"]
        return any(word.lower() in message.lower() for word in offensive_words)
    
    def _generate_mock_response(self, message: str, context: Dict) -> str:
        """Generar respuesta simulada para desarrollo"""
        responses = [
            f"Recibí tu mensaje: '{message[:50]}...' ¿En qué más puedo ayudarte?",
            f"Interesante punto sobre '{message[:50]}'. Déjame pensar...",
            f"Entiendo tu consulta sobre '{message[:50]}'. Aquí está mi análisis:",
            "¡Buena pregunta! Como asistente de IA, puedo ayudarte con eso.",
            "Procesando tu solicitud... ¡Listo! ¿Algo más en lo que pueda ayudarte?"
        ]
        
        import random
        return random.choice(responses)
    
    def process_message(self, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Process a chat message with security analysis
        
        Args:
            message: User message
            context: Optional context dictionary (session_id, user_id, etc.)
        
        Returns:
            AI response
        """
        self.estadisticas["tareas_totales"] += 1
        
        # Obtener información de contexto
        session_id = context.get("session_id", "default") if context else "default"
        user_id = context.get("user_id", "unknown") if context else "unknown"
        
        # ============================================================
        # DETECTAR ACCIONES Y CREAR TAREAS (ANTES DE SEGURIDAD)
        # ============================================================
        
        mensaje_lower = message.lower()
        
        # Detectar creación de carpeta
                if "crear carpeta" in mensaje_lower or "mkdir" in mensaje_lower:
                    import re
                    match = re.search(r"(?:crear carpeta|mkdir)\s+([^\s]+)", mensaje_lower)
                    nombre_carpeta = match.group(1) if match else "nueva_carpeta"
                    
                    try:
                        task_id = self.supervisor.create_task(
                            task_type="crear_carpeta",
                            data={
                                "nombre": nombre_carpeta,
                                "ruta": ".",
                                "user_id": user_id
                            },
                            priority=TaskPriority.NORMAL,
                            source="chat"
                        )
                        return f"🔄 Tarea creada (ID: {task_id}) para crear la carpeta '{nombre_carpeta}'. El agente archivos la procesará."
                    except Exception as e:
                        return f"❌ Error creando tarea: {e}"
                
                # Detectar script de información del sistema
                if ("script" in mensaje_lower and ("información" in mensaje_lower or "info" in mensaje_lower)) or \
                   ("información del sistema" in mensaje_lower) or \
                   ("info sistema" in mensaje_lower):
                    try:
                        task_id = self.supervisor.create_task(
                            task_type="ejecutar_comando",
                            data={
                                "comando": "uname -a && echo '---' && free -h && echo '---' && df -h",
                                "description": "Obtener información del sistema",
                                "user_id": user_id
                            },
                            priority=TaskPriority.HIGH,
                            source="chat"
                        )
                        return f"🔄 Tarea creada (ID: {task_id}) para obtener información del sistema. Espera el resultado..."
                    except Exception as e:
                        return f"❌ Error creando tarea: {e}"
                
                # Detectar listar archivos
                if "listar archivos" in mensaje_lower or "ls" in mensaje_lower.split():
                    try:
                        task_id = self.supervisor.create_task(
                            task_type="listar_archivos",
                            data={
                                "ruta": ".",
                                "user_id": user_id
                            },
                            priority=TaskPriority.LOW,
                            source="chat"
                        )
                        return f"🔄 Tarea creada (ID: {task_id}) para listar archivos en el directorio actual."
                    except Exception as e:
                        return f"❌ Error creando tarea: {e}"
                
                # Detectar ejecutar comando genérico
                if "ejecutar" in mensaje_lower and "comando" in mensaje_lower:
                    import re
                    match = re.search(r"ejecutar comando\s+(.+)", mensaje_lower)
                    comando = match.group(1) if match else None
                    
                    if comando:
                        try:
                            task_id = self.supervisor.create_task(
                                task_type="ejecutar_comando",
                                data={
                                    "comando": comando,
                                    "description": message,
                                    "user_id": user_id
                                },
                                priority=TaskPriority.NORMAL,
                                source="chat"
                            )
                            return f"🔄 Tarea creada (ID: {task_id}) para ejecutar: {comando}"
                        except Exception as e:
                            return f"❌ Error creando tarea: {e}"
        
        # ============================================================
        # ANÁLISIS DE SEGURIDAD (para mensajes que no son acciones)
        # ============================================================
        
        # Análisis de seguridad del mensaje
        security_result = self.security_analyzer.analyze(message, user_id)
        
        if security_result["is_malicious"]:
            self.estadisticas["tareas_fallidas"] += 1
            self.logger.warning(f"Mensaje malicioso detectado: {security_result['attack_type']}")
            
            # Respuesta según nivel de amenaza
            if security_result["threat_level"] in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
                return "⚠️ *ADVERTENCIA DE SEGURIDAD* ⚠️\n\n" \
                       "Tu mensaje ha sido identificado como potencialmente malicioso.\n" \
                       "Este incidente ha sido registrado y reportado.\n\n" \
                       "Si crees que es un error, contacta al administrador."
            else:
                return "⚠️ He detectado contenido potencialmente peligroso en tu mensaje.\n" \
                       "Por favor, reformula tu pregunta de manera segura."
        
        # Detectar lenguaje ofensivo
        if self._detect_offensive_language(message):
            return "Por favor, mantén un lenguaje respetuoso. Estoy aquí para ayudarte de manera profesional."
        
        # Agregar mensaje al historial
        self._add_to_history(session_id, "user", message)
        
        try:
            # Generar respuesta según el proveedor activo
            if self.active_ai == "deepseek" and self.deepseek_handler:
                response = self._process_with_deepseek(message, context, session_id)
            elif self.active_ai == "llama" and self.llama_handler:
                response = self._process_with_llama(message, context, session_id)
            elif self.active_ai == "mock":
                response = self._generate_mock_response(message, context)
            else:
                response = "Error: No hay un proveedor de IA disponible. Verifica la configuración."
            
            # Agregar respuesta al historial
            self._add_to_history(session_id, "assistant", response)
            
            self.estadisticas["tareas_completadas"] += 1
            return response
            
        except DeepSeekError as e:
            self.estadisticas["tareas_fallidas"] += 1
            self.logger.error(f"DeepSeek error: {e}")
            return f"❌ Error con DeepSeek API: {str(e)}. Verifica tu API key."
        
        except LlamaError as e:
            self.estadisticas["tareas_fallidas"] += 1
            self.logger.error(f"Llama error: {e}")
            return f"❌ Error con Llama: {str(e)}. Verifica la ruta del modelo."
        
        except Exception as e:
            self.estadisticas["tareas_fallidas"] += 1
            self.logger.error(f"Error processing message: {e}")
            return f"❌ Error procesando tu mensaje: {str(e)}"
        
        def _process_with_deepseek(self, message: str, context: Dict, session_id: str) -> str:
            """Procesar mensaje con DeepSeek API"""
            # Obtener historial de conversación
            history = self._get_conversation_context(session_id)
            
            # Construir mensajes para la API
            messages = []
            
            # Agregar prompt del sistema
            system_prompt = self._get_system_prompt()
            messages.append({"role": "system", "content": system_prompt})
            
            # Agregar historial de conversación (últimos 10 mensajes para contexto)
            for msg in history[-10:]:
                messages.append({"role": msg["role"], "content": msg["content"]})
            
            # Agregar mensaje actual
            messages.append({"role": "user", "content": message})
            
            # Obtener parámetros de configuración
            temperature = getattr(self.config, 'AI_TEMPERATURE', 0.7)
            max_tokens = getattr(self.config, 'AI_MAX_TOKENS', 4096)
            
            # Llamar a la API
            response = self.deepseek_handler.chat_completion(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # Extraer respuesta
            if "choices" in response and len(response["choices"]) > 0:
                return response["choices"][0]["message"]["content"]
            else:
                raise DeepSeekError("No se recibió respuesta válida")
    
    def _process_with_llama(self, message: str, context: Dict, session_id: str) -> str:
        """Procesar mensaje con Llama local"""
        # Obtener historial
        history = self._get_conversation_context(session_id)
        
        # Construir mensajes
        messages = []
        
        # Prompt del sistema
        system_prompt = self._get_system_prompt()
        messages.append({"role": "system", "content": system_prompt})
        
        # Historial
        for msg in history[-10:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        
        # Mensaje actual
        messages.append({"role": "user", "content": message})
        
        # Obtener parámetros
        temperature = getattr(self.config, 'AI_TEMPERATURE', 0.7)
        max_tokens = getattr(self.config, 'AI_MAX_TOKENS', 2048)
        
        # Llamar a Llama
        response = self.llama_handler.chat_completion(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        if "choices" in response and len(response["choices"]) > 0:
            return response["choices"][0]["message"]["content"]
        else:
            raise LlamaError("No se recibió respuesta válida")
    
    def clear_history(self, session_id: str = None):
        """Limpiar historial de conversación"""
        if session_id:
            if session_id in self.conversation_history:
                self.conversation_history[session_id] = []
                self.logger.info(f"Historial limpiado para sesión: {session_id}")
        else:
            self.conversation_history.clear()
            self.logger.info("Todo el historial limpiado")
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas del chat agent"""
        uptime = None
        if self.estadisticas["inicio"]:
            uptime = datetime.now() - self.estadisticas["inicio"]
            uptime = str(uptime).split('.')[0]
        
        return {
            "provider": self.active_ai,
            "stats": {
                "messages_processed": self.estadisticas["tareas_totales"],
                "errors": self.estadisticas["tareas_fallidas"],
                "uptime": uptime,
                "active_sessions": len(self.conversation_history)
            },
            "config": {
                "max_history": self.max_history_length,
                "temperature": getattr(self.config, 'AI_TEMPERATURE', 0.7),
                "max_tokens": getattr(self.config, 'AI_MAX_TOKENS', 4096)
            }
        }
    
    def stop(self):
        """Stop the chat agent"""
        self.logger.info("Stopping chat agent...")
        
        # Cerrar handlers
        if self.deepseek_handler:
            try:
                self.deepseek_handler.close()
            except:
                pass
        
        self.deepseek_handler = None
        self.llama_handler = None
        self.active_ai = None
        
        # Limpiar historial
        self.conversation_history.clear()
        self.estado = EstadoAgente.DETENIDO
        self.logger.info("Chat agent stopped")


# ============================================================
# Factory Function
# ============================================================

def create_chat_agent(supervisor: Supervisor, config: Config) -> ChatAgent:
    """
    Create chat agent instance
    
    Args:
        supervisor: Supervisor instance
        config: Configuration object
    
    Returns:
        Chat agent instance
    """
    agent = ChatAgent(supervisor, config)
    agent.start()  # Inicializar el agente automáticamente
    return agent


# ============================================================
# Example Usage
# ============================================================

def example_usage():
    """Example of using chat agent"""
    print("💬 Chat Agent Example\n")
    
    # Mock config
    class MockConfig:
        AI_DEFAULT_PROVIDER = "mock"
        AI_TEMPERATURE = 0.7
        AI_MAX_TOKENS = 4096
        DEEPSEEK_API_KEY = ""
        LLAMA_MODEL_PATH = ""
        SYSTEM_PROMPT = "Eres un asistente útil."
    
    config = MockConfig()
    
    # Mock supervisor
    class MockSupervisor:
        def _detect_attack(self, source_ip, attack_type, details, threat_level):
            print(f"  🚨 Ataque detectado: {attack_type.value} desde {source_ip}")
    
    supervisor = MockSupervisor()
    agent = create_chat_agent(supervisor, config)
    
    print("✅ Chat agent started\n")
    
    # Mensaje normal
    print("📝 Mensaje normal:")
    response = agent.process_message("Hola, ¿cómo estás?", {"session_id": "test", "user_id": "user1"})
    print(f"  Respuesta: {response}\n")
    
    # Estadísticas
    stats = agent.get_stats()
    print("📊 Estadísticas:")
    print(f"  Proveedor: {stats['provider']}")
    print(f"  Mensajes procesados: {stats['stats']['messages_processed']}")
    
    # Stop agent
    agent.stop()
    print("\n✅ Chat agent stopped")


if __name__ == "__main__":
    example_usage()
