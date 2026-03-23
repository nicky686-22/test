#!/usr/bin/env python3
"""
SwarmIA Dashboard Server - Elegant Web Interface
FastAPI-based dashboard with admin authentication and real-time monitoring
"""

import os
import sys
import json
import secrets
import asyncio
import socket
import sqlite3
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi import FastAPI, Request, Response, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Import project modules
from src.core.config import Config
from src.core.supervisor import Supervisor, TaskPriority, create_supervisor

# ============================================================
# Database Functions (simplified)
# ============================================================

DB_PATH = Path(__file__).parent.parent.parent / "data" / "swarmia.db"

def get_db_connection():
    """Get database connection"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """Initialize database tables"""
    with get_db_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                password_changed INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS system_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                message TEXT,
                user TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()

# ============================================================
# FastAPI App Initialization
# ============================================================

# Configuración
config = Config()

# FastAPI app
app = FastAPI(
    title="SwarmIA Dashboard",
    description="Elegant dashboard for SwarmIA - The Enhanced AI Assistant",
    version="2.0.0",
    docs_url="/api/docs" if config.SERVER_DEBUG else None,
    redoc_url="/api/redoc" if config.SERVER_DEBUG else None
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if config.SERVER_DEBUG else ["http://localhost:8080", "http://127.0.0.1:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBasic()

# Templates and static files
BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

# Crear directorios si no existen
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR.mkdir(parents=True, exist_ok=True)

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Global state
supervisor = create_supervisor(config)
active_sessions: Dict[str, Dict] = {}

# Dashboard stats
dashboard_stats = {
    "total_tasks": 0,
    "completed_tasks": 0,
    "active_agents": 0,
    "system_uptime": datetime.now(),
    "messages_processed": 0,
    "errors_count": 0
}

# ============================================================
# Authentication Functions
# ============================================================

def verify_admin_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    """Verify admin credentials"""
    correct_username = secrets.compare_digest(credentials.username, "admin")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash, password_changed FROM users WHERE username = ?", ("admin",))
        result = cursor.fetchone()
        
        if not result:
            # Create default admin
            cursor.execute(
                "INSERT INTO users (username, password_hash, password_changed) VALUES (?, ?, ?)",
                ("admin", "admin", 0)
            )
            conn.commit()
            password_hash = "admin"
            password_changed = 0
        else:
            password_hash = result["password_hash"]
            password_changed = result["password_changed"]
    
    # Check password
    if password_changed == 0:
        # First login with default password
        correct_password = secrets.compare_digest(credentials.password, "admin")
        if correct_username and correct_password:
            raise HTTPException(
                status_code=status.HTTP_307_TEMPORARY_REDIRECT,
                detail="Password change required",
                headers={"Location": "/change-password"}
            )
    else:
        correct_password = secrets.compare_digest(credentials.password, password_hash)
    
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    return credentials.username

def create_session_token(username: str) -> str:
    """Create a new session token"""
    token = secrets.token_urlsafe(32)
    active_sessions[token] = {
        "username": username,
        "created_at": datetime.now(),
        "last_activity": datetime.now()
    }
    return token

def verify_session_token(request: Request):
    """Verify session token from cookie"""
    token = request.cookies.get("session_token")
    if not token or token not in active_sessions:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid"
        )
    
    # Update last activity
    active_sessions[token]["last_activity"] = datetime.now()
    return active_sessions[token]

async def cleanup_sessions():
    """Remove sessions older than 24 hours"""
    while True:
        await asyncio.sleep(3600)  # Run every hour
        now = datetime.now()
        expired_tokens = []
        for token, session in active_sessions.items():
            if now - session["last_activity"] > timedelta(hours=24):
                expired_tokens.append(token)
        for token in expired_tokens:
            del active_sessions[token]

# ============================================================
# Routes
# ============================================================

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, session: Dict = Depends(verify_session_token)):
    """Main dashboard page"""
    # Get stats from supervisor
    supervisor_stats = supervisor.get_stats() if supervisor else {}
    
    stats = {
        "uptime": str(datetime.now() - dashboard_stats["system_uptime"]).split('.')[0],
        "active_tasks": supervisor_stats.get("queue_size", 0),
        "completed_tasks": supervisor_stats.get("tasks_completed", 0),
        "agents_online": supervisor_stats.get("agents_registered", 0),
        "messages_today": dashboard_stats["messages_processed"],
        "system_load": 0.0
    }
    
    # Get recent tasks
    tasks = supervisor.get_tasks(limit=5) if supervisor else []
    
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "username": session["username"],
            "stats": stats,
            "recent_tasks": tasks,
            "config": {
                "version": "2.0.0",
                "server_port": config.SERVER_PORT
            }
        }
    )

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page"""
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/api/login")
async def api_login(credentials: HTTPBasicCredentials = Depends(security)):
    """API login endpoint"""
    username = verify_admin_credentials(credentials)
    
    token = create_session_token(username)
    
    response = JSONResponse({
        "success": True,
        "message": "Login successful",
        "username": username
    })
    
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        max_age=86400,
        samesite="lax"
    )
    
    return response

@app.get("/change-password", response_class=HTMLResponse)
async def change_password_page(request: Request):
    """Password change page"""
    return templates.TemplateResponse("change_password.html", {"request": request})

@app.post("/api/change-password")
async def api_change_password(request: Request):
    """Change password API"""
    data = await request.json()
    current_password = data.get("current_password")
    new_password = data.get("new_password")
    confirm_password = data.get("confirm_password")
    
    if not all([current_password, new_password, confirm_password]):
        raise HTTPException(status_code=400, detail="All fields are required")
    
    if new_password != confirm_password:
        raise HTTPException(status_code=400, detail="New passwords don't match")
    
    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash, password_changed FROM users WHERE username = 'admin'")
        result = cursor.fetchone()
        
        if not result:
            raise HTTPException(status_code=500, detail="User not found")
        
        stored_hash = result["password_hash"]
        
        # Check current password
        if not secrets.compare_digest(current_password, stored_hash):
            raise HTTPException(status_code=400, detail="Current password is incorrect")
        
        # Update password
        cursor.execute(
            "UPDATE users SET password_hash = ?, password_changed = 1 WHERE username = 'admin'",
            (new_password,)
        )
        conn.commit()
    
    # Clear all sessions
    active_sessions.clear()
    
    return {"success": True, "message": "Password changed successfully"}

@app.get("/config", response_class=HTMLResponse)
async def config_page(request: Request, session: Dict = Depends(verify_session_token)):
    """Configuration page"""
    return templates.TemplateResponse(
        "config.html",
        {
            "request": request,
            "username": session["username"],
            "ai_config": {
                "provider": config.AI_DEFAULT_PROVIDER,
                "deepseek_enabled": bool(config.DEEPSEEK_API_KEY),
                "llama_enabled": bool(config.LLAMA_MODEL_PATH)
            },
            "communication_config": {
                "whatsapp_enabled": config.WHATSAPP_ENABLED,
                "telegram_enabled": config.TELEGRAM_ENABLED
            },
            "available_models": ["deepseek", "llama"]
        }
    )

@app.get("/agents", response_class=HTMLResponse)
async def agents_page(request: Request, session: Dict = Depends(verify_session_token)):
    """Agents monitoring page"""
    agents = supervisor.get_agents() if supervisor else []
    
    return templates.TemplateResponse(
        "agents.html",
        {
            "request": request,
            "username": session["username"],
            "agents": [{"id": a.id, "name": a.name, "type": a.type, "status": a.status.value} for a in agents],
            "agent_types": ["chat", "aggressive"]
        }
    )

@app.get("/api/agents/status")
async def get_agents_status(request: Request):
    """Get real-time agent status"""
    session = verify_session_token(request)
    
    agents = supervisor.get_agents() if supervisor else []
    return {
        "agents": [{"id": a.id, "name": a.name, "type": a.type, "status": a.status.value} for a in agents],
        "timestamp": datetime.now().isoformat()
    }

@app.get("/tasks", response_class=HTMLResponse)
async def tasks_page(request: Request, session: Dict = Depends(verify_session_token)):
    """Tasks monitoring page"""
    tasks = supervisor.get_tasks(limit=50) if supervisor else []
    
    return templates.TemplateResponse(
        "tasks.html",
        {
            "request": request,
            "username": session["username"],
            "tasks": tasks,
            "task_priorities": {"CRITICAL": 0, "HIGH": 1, "NORMAL": 2, "LOW": 3, "BACKGROUND": 4}
        }
    )

@app.get("/api/tasks/recent")
async def get_recent_tasks(request: Request, limit: int = 20):
    """Get recent tasks"""
    session = verify_session_token(request)
    
    tasks = supervisor.get_tasks(limit=limit) if supervisor else []
    
    tasks_data = []
    for task in tasks:
        tasks_data.append({
            "id": task.id,
            "type": task.type,
            "status": task.status.value,
            "priority": task.priority.name,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None
        })
    
    return {"tasks": tasks_data}

@app.post("/api/tasks/{task_id}/cancel")
async def cancel_task(task_id: str, request: Request):
    """Cancel a running task"""
    session = verify_session_token(request)
    
    success = supervisor.cancel_task(task_id) if supervisor else False
    if not success:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found or not cancellable")
    
    return {"success": True, "message": f"Task '{task_id}' cancelled"}

@app.get("/logs", response_class=HTMLResponse)
async def logs_page(request: Request, session: Dict = Depends(verify_session_token)):
    """System logs page"""
    log_files = ["swarmia.log", "gateway.log", "supervisor.log"]
    
    return templates.TemplateResponse(
        "logs.html",
        {
            "request": request,
            "username": session["username"],
            "log_files": log_files
        }
    )

@app.get("/api/logs/{log_file}")
async def get_log_file(log_file: str, request: Request, lines: int = 100):
    """Get log file contents"""
    session = verify_session_token(request)
    
    log_path = config.LOGS_DIR / log_file
    if not log_path.exists():
        raise HTTPException(status_code=404, detail="Log file not found")
    
    try:
        with open(log_path, 'r') as f:
            content = f.readlines()[-lines:]
        return {"lines": content, "file": log_file}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading log file: {str(e)}")

@app.get("/api/system/stats")
async def get_system_stats(request: Request):
    """Get system statistics"""
    session = verify_session_token(request)
    
    supervisor_stats = supervisor.get_stats() if supervisor else {}
    
    return {
        "dashboard_stats": {
            "uptime": str(datetime.now() - dashboard_stats["system_uptime"]).split('.')[0],
            "messages_processed": dashboard_stats["messages_processed"],
            "errors_count": dashboard_stats["errors_count"]
        },
        "supervisor_stats": supervisor_stats,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "service": "swarmia-dashboard",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat(),
        "uptime": str(datetime.now() - dashboard_stats["system_uptime"]).split('.')[0],
        "active_sessions": len(active_sessions)
    }

@app.get("/api/network/info")
async def network_info():
    """Get network information for external access"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except:
        local_ip = "127.0.0.1"
    
    return {
        "local_ip": local_ip,
        "port": config.SERVER_PORT,
        "dashboard_url": f"http://{local_ip}:{config.SERVER_PORT}",
        "api_url": f"http://{local_ip}:{config.SERVER_PORT}/api",
        "external_access_required": True,
        "instructions": f"Access dashboard at http://{local_ip}:{config.SERVER_PORT}"
    }

# ============================================================
# Aggressive Agent Endpoints
# ============================================================

@app.get("/api/aggressive/dependencies")
async def get_aggressive_dependencies(request: Request):
    """Verificar dependencias del agente agresivo"""
    session = verify_session_token(request)
    
    deps = {
        "paramiko": {"installed": False, "name": "paramiko", "version": None},
        "cryptography": {"installed": False, "name": "cryptography", "version": None},
        "requests": {"installed": False, "name": "requests", "version": None}
    }
    
    # Verificar paramiko
    try:
        import paramiko
        deps["paramiko"]["installed"] = True
        deps["paramiko"]["version"] = paramiko.__version__
    except ImportError:
        pass
    
    # Verificar cryptography
    try:
        import cryptography
        deps["cryptography"]["installed"] = True
        deps["cryptography"]["version"] = cryptography.__version__
    except ImportError:
        pass
    
    # Verificar requests
    try:
        import requests
        deps["requests"]["installed"] = True
        deps["requests"]["version"] = requests.__version__
    except ImportError:
        pass
    
    return deps


@app.post("/api/aggressive/install")
async def install_aggressive_dependencies(request: Request):
    """Instalar dependencias faltantes del agente agresivo"""
    session = verify_session_token(request)
    
    missing = []
    try:
        import paramiko
    except ImportError:
        missing.append("paramiko")
    
    try:
        import cryptography
    except ImportError:
        missing.append("cryptography")
    
    try:
        import requests
    except ImportError:
        missing.append("requests")
    
    if not missing:
        return {"success": True, "message": "Todas las dependencias ya están instaladas"}
    
    try:
        # Intentar instalar con pip
        for dep in missing:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", dep],
                capture_output=True,
                text=True,
                timeout=60
            )
            if result.returncode != 0:
                return {
                    "success": False, 
                    "message": f"Error instalando {dep}: {result.stderr}"
                }
        
        return {
            "success": True,
            "message": f"Dependencias instaladas correctamente: {', '.join(missing)}"
        }
        
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "message": "Timeout instalando dependencias. Intenta manualmente: pip install paramiko cryptography requests"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error instalando dependencias: {str(e)}"
        }


@app.post("/api/config/aggressive")
async def save_aggressive_config(request: Request):
    """Guardar configuración del agente agresivo"""
    session = verify_session_token(request)
    data = await request.json()
    
    try:
        import yaml
        
        config_path = config.CONFIG_DIR / "config.yaml"
        example_path = config.CONFIG_DIR / "config.example.yaml"
        
        # Si no existe config.yaml, crearlo desde el ejemplo
        if not config_path.exists():
            if example_path.exists():
                import shutil
                shutil.copy(example_path, config_path)
                print(f"📄 Creado {config_path} desde plantilla")
            else:
                # Si no hay ejemplo, crear uno básico
                config_path.parent.mkdir(parents=True, exist_ok=True)
                config_path.touch()
        
        # Cargar configuración existente
        with open(config_path, 'r') as f:
            full_config = yaml.safe_load(f) or {}
        
        # Procesar redes permitidas
        allowed_networks = data.get("allowed_networks", "")
        if isinstance(allowed_networks, str):
            networks_list = [n.strip() for n in allowed_networks.split('\n') if n.strip()]
        else:
            networks_list = []
        
        # Actualizar sección aggressive
        full_config["aggressive"] = {
            "enabled": data.get("enabled", False),
            "mode": data.get("mode", "normal"),
            "max_threads": data.get("max_threads", 50),
            "timeout": data.get("timeout", 5),
            "stealth_mode": data.get("stealth", False),
            "delay_between_requests": data.get("delay", 0.5),
            "ssh_enabled": data.get("ssh_enabled", True),
            "allowed_networks": networks_list,
            "wordlist": data.get("wordlist", "default")
        }
        
        # Guardar archivo YAML
        with open(config_path, 'w') as f:
            yaml.dump(full_config, f, default_flow_style=False)
        
        # También actualizar variables de entorno en .env
        env_path = config.BASE_DIR / ".env"
        env_example_path = config.BASE_DIR / ".env.example"
        
        # Si no existe .env, crearlo desde el ejemplo
        if not env_path.exists():
            if env_example_path.exists():
                import shutil
                shutil.copy(env_example_path, env_path)
                print(f"📄 Creado {env_path} desde plantilla")
        
        env_vars = {}
        if env_path.exists():
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key] = value
        
        env_vars["AGGRESSIVE_ENABLED"] = str(data.get("enabled", False)).lower()
        env_vars["AGGRESSIVE_MODE"] = data.get("mode", "normal")
        env_vars["AGGRESSIVE_MAX_THREADS"] = str(data.get("max_threads", 50))
        env_vars["AGGRESSIVE_TIMEOUT"] = str(data.get("timeout", 5))
        env_vars["AGGRESSIVE_STEALTH"] = str(data.get("stealth", False)).lower()
        env_vars["AGGRESSIVE_SSH_ENABLED"] = str(data.get("ssh_enabled", True)).lower()
        env_vars["AGGRESSIVE_ALLOWED_NETWORKS"] = ",".join(networks_list)
        
        with open(env_path, 'w') as f:
            for key, value in env_vars.items():
                f.write(f"{key}={value}\n")
        
        return {"success": True, "message": "Configuración guardada correctamente"}
        
    except Exception as e:
        return {"success": False, "message": str(e)}


@app.post("/api/aggressive/test")
async def test_aggressive_config(request: Request):
    """Probar configuración del agente agresivo"""
    session = verify_session_token(request)
    
    # Verificar si el agente agresivo está activado
    if not getattr(config, 'AGGRESSIVE_ENABLED', False):
        return {
            "success": False,
            "message": "El agente agresivo no está activado. Actívalo en configuración."
        }
    
    # Verificar redes permitidas
    allowed_networks = getattr(config, 'AGGRESSIVE_ALLOWED_NETWORKS', '')
    if not allowed_networks:
        return {
            "success": False,
            "message": "No hay redes permitidas configuradas. Debes agregar al menos una red."
        }
    
    # Verificar dependencias para modo ultra
    mode = getattr(config, 'AGGRESSIVE_MODE', 'normal')
    if mode == "ultra":
        missing = []
        try:
            import paramiko
        except ImportError:
            missing.append("paramiko")
        try:
            import cryptography
        except ImportError:
            missing.append("cryptography")
        
        if missing:
            return {
                "success": False,
                "message": f"Faltan dependencias para modo ULTRA: {', '.join(missing)}. Instálalas desde el dashboard."
            }
    
    return {
        "success": True,
        "message": f"✅ Configuración válida. Modo: {mode.upper()}, Redes: {allowed_networks[:100]}"
    }


@app.get("/api/config")
async def get_full_config(request: Request):
    """Obtener configuración completa"""
    session = verify_session_token(request)
    
    # Cargar redes permitidas
    allowed_networks = getattr(config, 'AGGRESSIVE_ALLOWED_NETWORKS', '')
    if isinstance(allowed_networks, list):
        networks_str = "\n".join(allowed_networks)
    else:
        networks_str = allowed_networks.replace(',', '\n')
    
    return {
        "ai": {
            "provider": config.AI_DEFAULT_PROVIDER,
            "deepseek": {
                "api_key": config.DEEPSEEK_API_KEY,
                "model": config.DEEPSEEK_MODEL,
                "max_tokens": config.AI_MAX_TOKENS,
                "temperature": config.AI_TEMPERATURE
            },
            "llama": {
                "model_path": config.LLAMA_MODEL_PATH,
                "context_size": config.LLAMA_CONTEXT_SIZE,
                "threads": config.LLAMA_THREADS
            },
            "assistant_name": "SwarmIA",
            "system_prompt": "Eres SwarmIA, un asistente de IA mejorado..."
        },
        "communication": {
            "whatsapp": {
                "enabled": config.WHATSAPP_ENABLED,
                "session_file": config.WHATSAPP_SESSION_FILE
            },
            "telegram": {
                "enabled": config.TELEGRAM_ENABLED,
                "bot_token": config.TELEGRAM_BOT_TOKEN,
                "allowed_users": os.getenv("TELEGRAM_ALLOWED_USERS", "")
            }
        },
        "aggressive": {
            "enabled": getattr(config, 'AGGRESSIVE_ENABLED', False),
            "mode": getattr(config, 'AGGRESSIVE_MODE', 'normal'),
            "max_threads": getattr(config, 'AGGRESSIVE_MAX_THREADS', 50),
            "timeout": getattr(config, 'AGGRESSIVE_TIMEOUT', 5),
            "stealth": getattr(config, 'AGGRESSIVE_STEALTH', False),
            "delay": getattr(config, 'AGGRESSIVE_DELAY_BETWEEN_REQUESTS', 0.5),
            "ssh_enabled": getattr(config, 'AGGRESSIVE_SSH_ENABLED', True),
            "allowed_networks": networks_str
        },
        "system": {
            "server": {
                "host": config.SERVER_HOST,
                "port": config.SERVER_PORT,
                "debug": config.SERVER_DEBUG
            },
            "storage": {
                "log_level": "INFO",
                "max_log_size": 100,
                "auto_cleanup": True
            },
            "security": {
                "session_timeout": config.JWT_EXPIRE_MINUTES // 60,
                "max_login_attempts": 5
            }
        }
    }


@app.post("/api/config/ai")
async def update_ai_config(request: Request):
    """Actualizar configuración de IA"""
    session = verify_session_token(request)
    data = await request.json()
    
    # Guardar configuración (implementación básica)
    try:
        config_path = config.CONFIG_DIR / "config.yaml"
        if config_path.exists():
            import yaml
            with open(config_path, 'r') as f:
                full_config = yaml.safe_load(f) or {}
        else:
            full_config = {}
        
        full_config["ai"] = {
            "provider": data.get("provider"),
            "deepseek": data.get("deepseek", {}),
            "llama": data.get("llama", {}),
            "assistant_name": data.get("assistant_name"),
            "system_prompt": data.get("system_prompt")
        }
        
        with open(config_path, 'w') as f:
            yaml.dump(full_config, f, default_flow_style=False)
        
        return {"success": True, "message": "Configuración IA guardada"}
    except Exception as e:
        return {"success": False, "message": str(e)}


@app.post("/api/config/ai/test")
async def test_ai_connection(request: Request):
    """Probar conexión con proveedor IA"""
    session = verify_session_token(request)
    
    provider = config.AI_DEFAULT_PROVIDER
    
    if provider == "deepseek":
        if not config.DEEPSEEK_API_KEY:
            return {"success": False, "message": "Clave API de DeepSeek no configurada"}
        
        try:
            import requests
            response = requests.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {config.DEEPSEEK_API_KEY}"},
                json={"model": "deepseek-chat", "messages": [{"role": "user", "content": "ping"}], "max_tokens": 5},
                timeout=10
            )
            if response.status_code == 200:
                return {"success": True, "message": "Conexión exitosa con DeepSeek"}
            else:
                return {"success": False, "message": f"Error: {response.status_code}"}
        except Exception as e:
            return {"success": False, "message": f"Error de conexión: {str(e)}"}
    
    elif provider == "llama":
        if not config.LLAMA_MODEL_PATH:
            return {"success": False, "message": "Ruta del modelo Llama no configurada"}
        return {"success": True, "message": "Modo local - verifica que el modelo exista"}
    
    return {"success": True, "message": "Modo simulación activo"}


@app.post("/api/config/whatsapp")
async def update_whatsapp_config(request: Request):
    """Actualizar configuración WhatsApp"""
    session = verify_session_token(request)
    data = await request.json()
    
    config.WHATSAPP_ENABLED = data.get("enabled", False)
    return {"success": True, "message": "Configuración WhatsApp guardada"}


@app.post("/api/config/telegram")
async def update_telegram_config(request: Request):
    """Actualizar configuración Telegram"""
    session = verify_session_token(request)
    data = await request.json()
    
    config.TELEGRAM_ENABLED = data.get("enabled", False)
    config.TELEGRAM_BOT_TOKEN = data.get("bot_token", "")
    return {"success": True, "message": "Configuración Telegram guardada"}


@app.post("/api/config/telegram/test")
async def test_telegram_bot(request: Request):
    """Probar bot de Telegram"""
    session = verify_session_token(request)
    data = await request.json()
    
    bot_token = data.get("bot_token", "")
    
    if not bot_token:
        return {"success": False, "message": "Token no proporcionado"}
    
    try:
        import requests
        response = requests.get(f"https://api.telegram.org/bot{bot_token}/getMe", timeout=10)
        if response.ok:
            bot_info = response.json()
            return {
                "success": True,
                "username": bot_info.get("result", {}).get("username", "unknown")
            }
        else:
            return {"success": False, "message": "Token inválido"}
    except Exception as e:
        return {"success": False, "message": str(e)}


@app.post("/api/config/system")
async def update_system_config(request: Request):
    """Actualizar configuración del sistema"""
    session = verify_session_token(request)
    data = await request.json()
    
    if "server" in data:
        config.SERVER_HOST = data["server"].get("host", config.SERVER_HOST)
        config.SERVER_PORT = data["server"].get("port", config.SERVER_PORT)
        config.SERVER_DEBUG = data["server"].get("debug", config.SERVER_DEBUG)
    
    return {"success": True, "message": "Configuración del sistema guardada"}


@app.post("/api/config/reset")
async def reset_config(request: Request):
    """Restablecer configuración a valores por defecto"""
    session = verify_session_token(request)
    
    # Restablecer configuración agresiva
    config.AGGRESSIVE_ENABLED = False
    config.AGGRESSIVE_MODE = "normal"
    
    return {"success": True, "message": "Configuración restablecida"}


@app.get("/api/config/export")
async def export_config(request: Request):
    """Exportar configuración actual"""
    session = verify_session_token(request)
    
    config_data = {
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat(),
        "config": {
            "server": {
                "host": config.SERVER_HOST,
                "port": config.SERVER_PORT,
                "debug": config.SERVER_DEBUG
            },
            "ai": {
                "provider": config.AI_DEFAULT_PROVIDER,
                "deepseek_model": config.DEEPSEEK_MODEL,
                "llama_path": config.LLAMA_MODEL_PATH
            },
            "aggressive": {
                "enabled": getattr(config, 'AGGRESSIVE_ENABLED', False),
                "mode": getattr(config, 'AGGRESSIVE_MODE', 'normal'),
                "max_threads": getattr(config, 'AGGRESSIVE_MAX_THREADS', 50),
                "allowed_networks": getattr(config, 'AGGRESSIVE_ALLOWED_NETWORKS', '')
            }
        }
    }
    
    return config_data


@app.post("/api/config/import")
async def import_config(request: Request):
    """Importar configuración"""
    session = verify_session_token(request)
    data = await request.json()
    
    # Implementación básica
    if "config" in data:
        cfg = data["config"]
        if "aggressive" in cfg:
            config.AGGRESSIVE_ENABLED = cfg["aggressive"].get("enabled", False)
            config.AGGRESSIVE_MODE = cfg["aggressive"].get("mode", "normal")
    
    return {"success": True, "message": "Configuración importada"}


# ============================================================
# Startup/Shutdown Events
# ============================================================

@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    # Initialize database
    init_database()
    
    # Create default admin user if not exists
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM users WHERE username = 'admin'")
        result = cursor.fetchone()
        
        if result["count"] == 0:
            cursor.execute(
                "INSERT INTO users (username, password_hash, password_changed) VALUES (?, ?, ?)",
                ("admin", "admin", 0)
            )
            conn.commit()
    
    # Start session cleanup task
    asyncio.create_task(cleanup_sessions())
    
    # Log startup
    print(f"✅ Dashboard initialized on port {config.SERVER_PORT}")
    
    # Mostrar estado del agente agresivo
    if getattr(config, 'AGGRESSIVE_ENABLED', False):
        mode = getattr(config, 'AGGRESSIVE_MODE', 'normal')
        if mode == 'ultra':
            print(f"🔥 ULTRA AGGRESSIVE MODE ACTIVATED - MAXIMUM AGGRESSION 🔥")
        else:
            print(f"⚔️ Aggressive agent enabled - Mode: {mode.upper()}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    print("🛑 Dashboard shutting down")

# ============================================================
# Main Entry Point
# ============================================================

def main():
    """Main entry point for dashboard server"""
    port = config.SERVER_PORT
    
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                 🚀 SwarmIA Dashboard Server                  ║
║                         v2.0.0                              ║
╚══════════════════════════════════════════════════════════════╝

📊 Dashboard URL: http://localhost:{port}
📡 Network: http://{config.get_local_ip()}:{port}
🔧 API Docs: http://localhost:{port}/api/docs (debug mode)
👤 Default credentials: admin / admin (change on first login)

💡 Keyboard shortcuts:
   Ctrl+Shift+T - Cambiar tema
   Ctrl+Shift+E - Exportar historial
   Ctrl+Shift+V - Comandos de voz
""")
    
    uvicorn.run(
        "src.ui.server:app",
        host="0.0.0.0",
        port=port,
        reload=config.SERVER_DEBUG,
        log_level="info" if config.SERVER_DEBUG else "warning"
    )


if __name__ == "__main__":
    main()
