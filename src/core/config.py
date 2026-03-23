    #!/usr/bin/env python3
"""
SwarmIA Configuration Module
Manejo de configuración centralizada
"""

import os
import json
import socket
import requests
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import timedelta
import yaml


class Config:
    """Configuración central de SwarmIA"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Inicializar configuración
        
        Args:
            config_path: Ruta opcional al archivo de configuración
        """
        # Directorios base
        self.BASE_DIR = Path(__file__).parent.parent.parent
        self.CONFIG_DIR = self.BASE_DIR / "config"
        self.LOGS_DIR = self.BASE_DIR / "logs"
        self.DATA_DIR = self.BASE_DIR / "data"
        self.STATIC_DIR = self.BASE_DIR / "static"
        self.TEMPLATES_DIR = self.BASE_DIR / "templates"
        
        # Crear directorios necesarios
        for d in [self.CONFIG_DIR, self.LOGS_DIR, self.DATA_DIR, 
                  self.STATIC_DIR, self.TEMPLATES_DIR]:
            d.mkdir(parents=True, exist_ok=True)
        
        # Configuración del servidor
        self.SERVER_HOST = os.getenv("SWARMIA_HOST", "0.0.0.0")
        self.SERVER_PORT = int(os.getenv("SWARMIA_PORT", "8080"))
        self.SERVER_WORKERS = int(os.getenv("SWARMIA_WORKERS", "1"))
        self.SERVER_DEBUG = os.getenv("SWARMIA_DEBUG", "false").lower() == "true"
        
        # Configuración de la IA
        self.AI_DEFAULT_PROVIDER = os.getenv("AI_PROVIDER", "deepseek")
        self.AI_MAX_TOKENS = int(os.getenv("AI_MAX_TOKENS", "4096"))
        self.AI_TEMPERATURE = float(os.getenv("AI_TEMPERATURE", "0.7"))
        
        # DeepSeek API
        self.DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
        self.DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        self.DEEPSEEK_API_URL = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/v1")
        
        # Llama local
        self.LLAMA_MODEL_PATH = os.getenv("LLAMA_MODEL_PATH", "")
        self.LLAMA_CONTEXT_SIZE = int(os.getenv("LLAMA_CONTEXT_SIZE", "4096"))
        self.LLAMA_THREADS = int(os.getenv("LLAMA_THREADS", "4"))
        
        # WhatsApp
        self.WHATSAPP_ENABLED = os.getenv("WHATSAPP_ENABLED", "false").lower() == "true"
        self.WHATSAPP_SESSION_FILE = os.getenv("WHATSAPP_SESSION_FILE", "whatsapp_session.json")
        
        # Telegram
        self.TELEGRAM_ENABLED = os.getenv("TELEGRAM_ENABLED", "false").lower() == "true"
        self.TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
        
        # Seguridad
        self.JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
        self.JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-this-secret-key-in-production")
        self.JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))  # 24 horas
        
        # Credenciales admin
        self.ADMIN_USER = os.getenv("ADMIN_USER", "admin")
        self.ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH", "")
        
        # Redis (opcional)
        self.REDIS_ENABLED = os.getenv("REDIS_ENABLED", "false").lower() == "true"
        self.REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
        self.REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
        self.REDIS_DB = int(os.getenv("REDIS_DB", "0"))
        
        # ============================================================
        # AGGRESSIVE AGENT CONFIGURATION - PENTESTING TOOLS
        # ⚠️ SOLO PARA PRUEBAS AUTORIZADAS ⚠️
        # ============================================================
        # Habilitar agente agresivo (false por defecto por seguridad)
        self.AGGRESSIVE_ENABLED = os.getenv("AGGRESSIVE_ENABLED", "false").lower() == "true"
        
        # Modo de operación: normal, aggressive, ultra, stealth
        self.AGGRESSIVE_MODE = os.getenv("AGGRESSIVE_MODE", "normal").lower()
        
        # Intensidad de escaneo: light, normal, aggressive, ultra, stealth
        self.AGGRESSIVE_INTENSITY = os.getenv("AGGRESSIVE_INTENSITY", "normal").lower()
        
        # Redes permitidas (obligatorio para activar)
        self.AGGRESSIVE_ALLOWED_NETWORKS = os.getenv("AGGRESSIVE_ALLOWED_NETWORKS", "")
        
        # Límites de rendimiento
        self.AGGRESSIVE_MAX_THREADS = int(os.getenv("AGGRESSIVE_MAX_THREADS", "50"))
        self.AGGRESSIVE_TIMEOUT = int(os.getenv("AGGRESSIVE_TIMEOUT", "5"))
        self.AGGRESSIVE_MAX_TARGETS = int(os.getenv("AGGRESSIVE_MAX_TARGETS", "100"))
        
        # SSH Brute Force
        self.AGGRESSIVE_SSH_ENABLED = os.getenv("AGGRESSIVE_SSH_ENABLED", "true").lower() == "true"
        
        # Modo sigiloso
        self.AGGRESSIVE_STEALTH = os.getenv("AGGRESSIVE_STEALTH", "false").lower() == "true"
        self.AGGRESSIVE_DELAY_BETWEEN_REQUESTS = float(os.getenv("AGGRESSIVE_DELAY", "0"))
        
        # HTTP Attacks
        self.AGGRESSIVE_HTTP_ENABLED = os.getenv("AGGRESSIVE_HTTP_ENABLED", "true").lower() == "true"
        
        # Exploits
        self.AGGRESSIVE_CVE_CHECK = os.getenv("AGGRESSIVE_CVE_CHECK", "true").lower() == "true"
        self.AGGRESSIVE_DEFAULT_CREDS = os.getenv("AGGRESSIVE_DEFAULT_CREDS", "true").lower() == "true"
        
        # Cargar desde archivo si existe
        self._load_from_file(config_path)
    
    def _load_from_file(self, config_path: Optional[str] = None):
        """Cargar configuración desde archivo YAML"""
        if config_path is None:
            config_path = self.CONFIG_DIR / "config.yaml"
        else:
            config_path = Path(config_path)
        
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    data = yaml.safe_load(f) or {}
                
                # Actualizar configuración desde archivo
                for key, value in data.items():
                    if hasattr(self, key):
                        setattr(self, key, value)
                
                # Cargar configuración específica del agente agresivo
                if "aggressive" in data:
                    agg = data["aggressive"]
                    self.AGGRESSIVE_ENABLED = agg.get("enabled", self.AGGRESSIVE_ENABLED)
                    self.AGGRESSIVE_MODE = agg.get("mode", self.AGGRESSIVE_MODE)
                    self.AGGRESSIVE_INTENSITY = agg.get("intensity", self.AGGRESSIVE_INTENSITY)
                    self.AGGRESSIVE_MAX_THREADS = agg.get("max_threads", self.AGGRESSIVE_MAX_THREADS)
                    self.AGGRESSIVE_TIMEOUT = agg.get("timeout", self.AGGRESSIVE_TIMEOUT)
                    self.AGGRESSIVE_STEALTH = agg.get("stealth_mode", self.AGGRESSIVE_STEALTH)
                    
                    # Redes permitidas (si viene como lista, convertir a string)
                    if "allowed_networks" in agg:
                        networks = agg["allowed_networks"]
                        if isinstance(networks, list):
                            self.AGGRESSIVE_ALLOWED_NETWORKS = ",".join(networks)
                        else:
                            self.AGGRESSIVE_ALLOWED_NETWORKS = str(networks)
                        
            except Exception as e:
                print(f"⚠️ Error loading config file: {e}")
    
    def get_local_ip(self) -> str:
        """Obtener IP local"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"
    
    def get_public_ip(self) -> str:
        """Obtener IP pública"""
        try:
            response = requests.get("https://api.ipify.org?format=json", timeout=5)
            return response.json().get("ip", "unknown")
        except Exception:
            return "unknown"
    
    def validate(self) -> bool:
        """Validar configuración"""
        errors = []
        
        # Validar puerto
        if not (1 <= self.SERVER_PORT <= 65535):
            errors.append(f"Invalid port: {self.SERVER_PORT}")
        
        # Validar AI provider
        if self.AI_DEFAULT_PROVIDER not in ["deepseek", "llama", "mock"]:
            errors.append(f"Unknown AI provider: {self.AI_DEFAULT_PROVIDER}")
        
        # Validar DeepSeek API key si está habilitado
        if self.AI_DEFAULT_PROVIDER == "deepseek" and not self.DEEPSEEK_API_KEY:
            errors.append("DeepSeek API key is required when using DeepSeek provider")
        
        # Validar modelo Llama
        if self.AI_DEFAULT_PROVIDER == "llama" and not self.LLAMA_MODEL_PATH:
            errors.append("Llama model path is required when using Llama provider")
        elif self.AI_DEFAULT_PROVIDER == "llama":
            model_path = Path(self.LLAMA_MODEL_PATH)
            if not model_path.exists():
                errors.append(f"Llama model not found: {self.LLAMA_MODEL_PATH}")
        
        # Validar Telegram bot token
        if self.TELEGRAM_ENABLED and not self.TELEGRAM_BOT_TOKEN:
            errors.append("Telegram bot token is required when Telegram is enabled")
        
        # Validar JWT secret key
        if self.JWT_SECRET_KEY == "change-this-secret-key-in-production":
            errors.append("WARNING: Using default JWT secret key. Change it in production!")
        
        return len(errors) == 0
    
    def save(self, config_path: Optional[str] = None) -> bool:
        """Guardar configuración a archivo YAML"""
        if config_path is None:
            config_path = self.CONFIG_DIR / "config.yaml"
        else:
            config_path = Path(config_path)
        
        # Datos a guardar (solo atributos relevantes)
        data = {
            "SERVER_HOST": self.SERVER_HOST,
            "SERVER_PORT": self.SERVER_PORT,
            "SERVER_WORKERS": self.SERVER_WORKERS,
            "AI_DEFAULT_PROVIDER": self.AI_DEFAULT_PROVIDER,
            "AI_MAX_TOKENS": self.AI_MAX_TOKENS,
            "AI_TEMPERATURE": self.AI_TEMPERATURE,
            "DEEPSEEK_MODEL": self.DEEPSEEK_MODEL,
            "LLAMA_CONTEXT_SIZE": self.LLAMA_CONTEXT_SIZE,
            "WHATSAPP_ENABLED": self.WHATSAPP_ENABLED,
            "TELEGRAM_ENABLED": self.TELEGRAM_ENABLED,
            "JWT_ALGORITHM": self.JWT_ALGORITHM,
            "JWT_EXPIRE_MINUTES": self.JWT_EXPIRE_MINUTES,
            "REDIS_ENABLED": self.REDIS_ENABLED
        }
        
        try:
            with open(config_path, 'w') as f:
                yaml.dump(data, f, default_flow_style=False)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir configuración a diccionario"""
        return {
            "paths": {
                "base_dir": str(self.BASE_DIR),
                "config_dir": str(self.CONFIG_DIR),
                "logs_dir": str(self.LOGS_DIR),
                "data_dir": str(self.DATA_DIR)
            },
            "server": {
                "host": self.SERVER_HOST,
                "port": self.SERVER_PORT,
                "workers": self.SERVER_WORKERS,
                "debug": self.SERVER_DEBUG
            },
            "ai": {
                "default_provider": self.AI_DEFAULT_PROVIDER,
                "max_tokens": self.AI_MAX_TOKENS,
                "temperature": self.AI_TEMPERATURE
            },
            "security": {
                "jwt_algorithm": self.JWT_ALGORITHM,
                "jwt_expire_minutes": self.JWT_EXPIRE_MINUTES
            },
            "gateways": {
                "whatsapp_enabled": self.WHATSAPP_ENABLED,
                "telegram_enabled": self.TELEGRAM_ENABLED
            }
        }


def show_config():
    """Mostrar configuración actual (para debugging)"""
    config = Config()
    
    print("SwarmIA Configuration")
    print("="*60)
    
    print("\n📁 Paths:")
    print(f"  Base Directory: {config.BASE_DIR}")
    print(f"  Config Directory: {config.CONFIG_DIR}")
    print(f"  Logs Directory: {config.LOGS_DIR}")
    print(f"  Data Directory: {config.DATA_DIR}")
    
    print("\n🌐 Server:")
    print(f"  Host: {config.SERVER_HOST}")
    print(f"  Port: {config.SERVER_PORT}")
    print(f"  Workers: {config.SERVER_WORKERS}")
    print(f"  Debug: {config.SERVER_DEBUG}")
    
    print("\n🤖 AI:")
    print(f"  Default Provider: {config.AI_DEFAULT_PROVIDER}")
    print(f"  Max Tokens: {config.AI_MAX_TOKENS}")
    print(f"  Temperature: {config.AI_TEMPERATURE}")
    
    if config.AI_DEFAULT_PROVIDER == "deepseek":
        print(f"  DeepSeek Model: {config.DEEPSEEK_MODEL}")
        api_key_masked = config.DEEPSEEK_API_KEY[:8] + "..." if config.DEEPSEEK_API_KEY else "NOT SET"
        print(f"  DeepSeek API Key: {api_key_masked}")
    elif config.AI_DEFAULT_PROVIDER == "llama":
        print(f"  Llama Model Path: {config.LLAMA_MODEL_PATH or 'NOT SET'}")
        print(f"  Llama Context Size: {config.LLAMA_CONTEXT_SIZE}")
    
    print("\n📱 Gateways:")
    print(f"  WhatsApp: {'✓ Enabled' if config.WHATSAPP_ENABLED else '✗ Disabled'}")
    print(f"  Telegram: {'✓ Enabled' if config.TELEGRAM_ENABLED else '✗ Disabled'}")
    
    if config.TELEGRAM_ENABLED:
        token_masked = config.TELEGRAM_BOT_TOKEN[:8] + "..." if config.TELEGRAM_BOT_TOKEN else "NOT SET"
        print(f"  Telegram Bot Token: {token_masked}")
    
    # ============================================================
    # AGGRESSIVE AGENT CONFIGURATION
    # ============================================================
    print("\n⚔️ AGGRESSIVE AGENT:")
    print(f"  Enabled: {'✓ Yes' if config.AGGRESSIVE_ENABLED else '✗ No'}")
    if config.AGGRESSIVE_ENABLED:
        print(f"  Mode: {config.AGGRESSIVE_MODE.upper()}")
        print(f"  Intensity: {config.AGGRESSIVE_INTENSITY}")
        print(f"  Max Threads: {config.AGGRESSIVE_MAX_THREADS}")
        print(f"  Timeout: {config.AGGRESSIVE_TIMEOUT}s")
        print(f"  Stealth Mode: {'✓' if config.AGGRESSIVE_STEALTH else '✗'}")
        print(f"  SSH Brute Force: {'✓' if config.AGGRESSIVE_SSH_ENABLED else '✗'}")
        print(f"  Allowed Networks: {config.AGGRESSIVE_ALLOWED_NETWORKS or 'NOT SET'}")
        
        # Validación de seguridad
        if not config.AGGRESSIVE_ALLOWED_NETWORKS:
            print(f"  ⚠️ WARNING: No networks allowed! Aggressive agent will be disabled.")
        elif config.AGGRESSIVE_MODE == "ultra":
            print(f"  🔥 ULTRA MODE ACTIVATED - MAXIMUM AGGRESSION 🔥")
    
    print("\n🔐 Security:")
    print(f"  JWT Algorithm: {config.JWT_ALGORITHM}")
    print(f"  JWT Expire Minutes: {config.JWT_EXPIRE_MINUTES} ({config.JWT_EXPIRE_MINUTES//60} hours)")
    print(f"  Admin User: {config.ADMIN_USER}")
    print(f"  Admin Password: {'✓ Set' if config.ADMIN_PASSWORD_HASH else '⚠️ NOT SET (default: admin)'}")
    
    print("\n📊 System Info:")
    print(f"  Local IP: {config.get_local_ip()}")
    print(f"  Public IP: {config.get_public_ip()}")
    
    print("\n" + "="*60)
    
    # Validate configuration
    if config.validate():
        print("✅ Configuration is valid")
    else:
        print("❌ Configuration has errors")
    
    # Save configuration if not exists
    config_file = config.CONFIG_DIR / "config.yaml"
    if not config_file.exists():
        if config.save():
            print(f"💾 Default configuration saved to {config_file}")
        else:
            print(f"⚠️ Could not save default configuration")
    else:
        print(f"📄 Configuration file: {config_file}")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    # Si se ejecuta directamente, mostrar configuración
    show_config()
