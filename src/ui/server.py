#!/usr/bin/env python3
"""
SwarmIA Dashboard Server - Versión Corregida
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
import qrcode
import io
import base64
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi import FastAPI, Request, Response, Depends, HTTPException, status, Cookie
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
# Database Functions
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

config = Config()

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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBasic()

# Templates and static files
BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR.mkdir(parents=True, exist_ok=True)

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Global state
supervisor = create_supervisor(config)
active_sessions: Dict[str, Dict] = {}

dashboard_stats = {
    "total_tasks": 0,
    "completed_tasks": 0,
    "active_agents": 0,
    "system_uptime": datetime.now(),
    "messages_processed": 0,
    "errors_count": 0
}

# WhatsApp state
whatsapp_qr = None
whatsapp_connected = False
whatsapp_status = "disconnected"

# ============================================================
# Authentication Functions
# ============================================================

def create_session_token(username: str) -> str:
    """Create a new session token"""
    token = secrets.token_urlsafe(32)
    active_sessions[token] = {
        "username": username,
        "created_at": datetime.now(),
        "last_activity": datetime.now()
    }
    return token

def verify_session_token(token: Optional[str] = Cookie(None)):
    """Verify session token from cookie"""
    if not token or token not in active_sessions:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid"
        )
    active_sessions[token]["last_activity"] = datetime.now()
    return active_sessions[token]

async def cleanup_sessions():
    """Remove sessions older than 24 hours"""
    while True:
        await asyncio.sleep(3600)
        now = datetime.now()
        expired_tokens = []
        for token, session in active_sessions.items():
            if now - session["last_activity"] > timedelta(hours=24):
                expired_tokens.append(token)
        for token in expired_tokens:
            del active_sessions[token]

# ============================================================
# Public Routes
# ============================================================

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page"""
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/api/login")
async def api_login(credentials: HTTPBasicCredentials = Depends(security)):
    """API login endpoint"""
    correct_username = secrets.compare_digest(credentials.username, "admin")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash, password_changed FROM users WHERE username = ?", ("admin",))
        result = cursor.fetchone()
        
        if not result:
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
    
    if password_changed == 0:
        correct_password = secrets.compare_digest(credentials.password, "admin")
        if correct_username and correct_password:
            token = create_session_token(credentials.username)
            response = JSONResponse({
                "success": True,
                "message": "Password change required",
                "username": credentials.username,
                "redirect": "/change-password"
            })
            response.set_cookie(key="session_token", value=token, httponly=True, max_age=86400)
            return response
    else:
        correct_password = secrets.compare_digest(credentials.password, password_hash)
    
    if not (correct_username and correct_password):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    
    token = create_session_token(credentials.username)
    response = JSONResponse({
        "success": True,
        "message": "Login successful",
        "username": credentials.username
    })
    response.set_cookie(key="session_token", value=token, httponly=True, max_age=86400, samesite="lax")
    return response

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
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
    """Get network information"""
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
        "api_url": f"http://{local_ip}:{config.SERVER_PORT}/api"
    }

# ============================================================
# Protected Routes (require authentication)
# ============================================================

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, session: Dict = Depends(verify_session_token)):
    """Main dashboard page"""
    supervisor_stats = supervisor.get_stats() if supervisor else {}
    
    stats = {
        "uptime": str(datetime.now() - dashboard_stats["system_uptime"]).split('.')[0],
        "active_tasks": supervisor_stats.get("queue_size", 0),
        "completed_tasks": supervisor_stats.get("tasks_completed", 0),
        "agents_online": supervisor_stats.get("agents_registered", 0),
        "messages_today": dashboard_stats["messages_processed"],
        "system_load": 0.0
    }
    
    tasks = supervisor.get_tasks(limit=5) if supervisor else []
    
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "username": session["username"],
            "stats": stats,
            "recent_tasks": tasks,
            "config": {"version": "2.0.0", "server_port": config.SERVER_PORT}
        }
    )

@app.get("/change-password", response_class=HTMLResponse)
async def change_password_page(request: Request, session: Dict = Depends(verify_session_token)):
    """Password change page"""
    return templates.TemplateResponse("change_password.html", {"request": request, "username": session["username"]})

@app.post("/api/change-password")
async def api_change_password(request: Request, session: Dict = Depends(verify_session_token)):
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
        cursor.execute("SELECT password_hash FROM users WHERE username = 'admin'")
        result = cursor.fetchone()
        
        if not result:
            raise HTTPException(status_code=500, detail="User not found")
        
        stored_hash = result["password_hash"]
        
        if not secrets.compare_digest(current_password, stored_hash):
            raise HTTPException(status_code=400, detail="Current password is incorrect")
        
        cursor.execute(
            "UPDATE users SET password_hash = ?, password_changed = 1 WHERE username = 'admin'",
            (new_password,)
        )
        conn.commit()
    
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
async def get_agents_status(request: Request, session: Dict = Depends(verify_session_token)):
    """Get real-time agent status"""
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

@app.get("/api/tasks")
async def get_all_tasks(request: Request, limit: int = 100, session: Dict = Depends(verify_session_token)):
    """Get all tasks (for tasks page)"""
    tasks = supervisor.get_tasks(limit=limit) if supervisor else []
    
    tasks_data = []
    for task in tasks:
        tasks_data.append({
            "id": task.id,
            "type": task.type,
            "description": task.type,
            "status": task.status.value,
            "priority": task.priority.name,
            "agent_type": task.assigned_agent,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "duration": (task.completed_at - task.started_at).total_seconds() if task.completed_at and task.started_at else None
        })
    
    return {"tasks": tasks_data}

@app.get("/api/tasks/recent")
async def get_recent_tasks(request: Request, limit: int = 20, session: Dict = Depends(verify_session_token)):
    """Get recent tasks"""
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
async def cancel_task(task_id: str, request: Request, session: Dict = Depends(verify_session_token)):
    """Cancel a running task"""
    success = supervisor.cancel_task(task_id) if supervisor else False
    if not success:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found or not cancellable")
    return {"success": True, "message": f"Task '{task_id}' cancelled"}

@app.get("/logs", response_class=HTMLResponse)
async def logs_page(request: Request, session: Dict = Depends(verify_session_token)):
    """System logs page"""
    return templates.TemplateResponse(
        "logs.html",
        {
            "request": request,
            "username": session["username"],
            "log_files": ["swarmia.log", "gateway.log", "supervisor.log"]
        }
    )

@app.get("/api/logs/{log_file}")
async def get_log_file(log_file: str, request: Request, lines: int = 100, session: Dict = Depends(verify_session_token)):
    """Get log file contents"""
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
async def get_system_stats(request: Request, session: Dict = Depends(verify_session_token)):
    """Get system statistics"""
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

# ============================================================
# Configuration Endpoints
# ============================================================

@app.get("/api/config")
async def get_full_config(request: Request, session: Dict = Depends(verify_session_token)):
    """Get full configuration"""
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
async def update_ai_config(request: Request, session: Dict = Depends(verify_session_token)):
    """Update AI configuration"""
    data = await request.json()
    
    try:
        # Guardar en .env
        env_path = Path("/opt/swarmia/.env")
        if env_path.exists():
            with open(env_path, 'r') as f:
                lines = f.readlines()
            
            updated = False
            for i, line in enumerate(lines):
                if line.startswith("DEEPSEEK_API_KEY="):
                    lines[i] = f"DEEPSEEK_API_KEY={data.get('deepseek', {}).get('api_key', '')}\n"
                    updated = True
                    break
            
            if not updated:
                lines.append(f"DEEPSEEK_API_KEY={data.get('deepseek', {}).get('api_key', '')}\n")
            
            with open(env_path, 'w') as f:
                f.writelines(lines)
        
        # Guardar en config.yaml
        config_path = Path("/opt/swarmia/config/config.yaml")
        if config_path.exists():
            import yaml
            with open(config_path, 'r') as f:
                full_config = yaml.safe_load(f) or {}
            
            if "ai" not in full_config:
                full_config["ai"] = {}
            full_config["ai"]["provider"] = data.get("provider")
            full_config["ai"]["deepseek"] = data.get("deepseek", {})
            full_config["ai"]["llama"] = data.get("llama", {})
            full_config["ai"]["assistant_name"] = data.get("assistant_name")
            full_config["ai"]["system_prompt"] = data.get("system_prompt")
            
            with open(config_path, 'w') as f:
                yaml.dump(full_config, f, default_flow_style=False)
        
        return {"success": True, "message": "Configuración IA guardada"}
    except Exception as e:
        return {"success": False, "message": str(e)}

@app.post("/api/config/ai/test")
async def test_ai_connection(request: Request, session: Dict = Depends(verify_session_token)):
    """Test AI connection"""
    api_key = config.DEEPSEEK_API_KEY
    
    if not api_key:
        return {"success": False, "message": "Clave API de DeepSeek no configurada"}
    
    try:
        import requests
        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": "deepseek-chat", "messages": [{"role": "user", "content": "OK"}], "max_tokens": 5},
            timeout=10
        )
        if response.status_code == 200:
            return {"success": True, "message": "Conexión exitosa con DeepSeek"}
        else:
            return {"success": False, "message": f"Error: {response.status_code}"}
    except Exception as e:
        return {"success": False, "message": f"Error de conexión: {str(e)}"}

# ============================================================
# WhatsApp Endpoints
# ============================================================

@app.post("/api/whatsapp/qr")
async def generate_whatsapp_qr(request: Request, session: Dict = Depends(verify_session_token)):
    """Generate WhatsApp QR code"""
    global whatsapp_qr, whatsapp_connected, whatsapp_status
    
    try:
        if whatsapp_connected:
            return {"success": True, "connected": True, "message": "WhatsApp ya está conectado"}
        
        # Generar código QR simulado (en producción usarías whatsapp-web.js)
        import random
        import string
        
        qr_data = f"whatsapp://connect?session={''.join(random.choices(string.ascii_letters + string.digits, k=32))}"
        
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        qr_base64 = base64.b64encode(buffered.getvalue()).decode()
        
        whatsapp_qr = qr_base64
        whatsapp_status = "waiting_qr"
        
        return {
            "success": True,
            "qr": qr_base64,
            "message": "Escanea el código QR con WhatsApp",
            "status": whatsapp_status
        }
    except Exception as e:
        return {"success": False, "message": str(e)}

@app.get("/api/whatsapp/status")
async def get_whatsapp_status(request: Request, session: Dict = Depends(verify_session_token)):
    """Get WhatsApp connection status"""
    global whatsapp_connected, whatsapp_status, whatsapp_qr
    
    return {
        "connected": whatsapp_connected,
        "status": whatsapp_status,
        "qr_available": whatsapp_qr is not None
    }

@app.post("/api/whatsapp/disconnect")
async def disconnect_whatsapp(request: Request, session: Dict = Depends(verify_session_token)):
    """Disconnect WhatsApp"""
    global whatsapp_connected, whatsapp_status, whatsapp_qr
    
    whatsapp_connected = False
    whatsapp_status = "disconnected"
    whatsapp_qr = None
    
    return {"success": True, "message": "WhatsApp desconectado"}

# ============================================================
# Telegram Endpoints
# ============================================================

@app.post("/api/config/telegram")
async def update_telegram_config(request: Request, session: Dict = Depends(verify_session_token)):
    """Update Telegram configuration"""
    data = await request.json()
    
    try:
        env_path = Path("/opt/swarmia/.env")
        if env_path.exists():
            with open(env_path, 'r') as f:
                lines = f.readlines()
            
            # Actualizar TELEGRAM_ENABLED
            updated = False
            for i, line in enumerate(lines):
                if line.startswith("TELEGRAM_ENABLED="):
                    lines[i] = f"TELEGRAM_ENABLED={str(data.get('enabled', False)).lower()}\n"
                    updated = True
                    break
            if not updated:
                lines.append(f"TELEGRAM_ENABLED={str(data.get('enabled', False)).lower()}\n")
            
            # Actualizar TELEGRAM_BOT_TOKEN
            updated = False
            for i, line in enumerate(lines):
                if line.startswith("TELEGRAM_BOT_TOKEN="):
                    lines[i] = f"TELEGRAM_BOT_TOKEN={data.get('bot_token', '')}\n"
                    updated = True
                    break
            if not updated:
                lines.append(f"TELEGRAM_BOT_TOKEN={data.get('bot_token', '')}\n")
            
            # Actualizar TELEGRAM_ALLOWED_USERS
            updated = False
            for i, line in enumerate(lines):
                if line.startswith("TELEGRAM_ALLOWED_USERS="):
                    lines[i] = f"TELEGRAM_ALLOWED_USERS={data.get('allowed_users', '')}\n"
                    updated = True
                    break
            if not updated:
                lines.append(f"TELEGRAM_ALLOWED_USERS={data.get('allowed_users', '')}\n")
            
            with open(env_path, 'w') as f:
                f.writelines(lines)
        
        return {"success": True, "message": "Configuración Telegram guardada"}
    except Exception as e:
        return {"success": False, "message": str(e)}

@app.post("/api/config/telegram/test")
async def test_telegram_bot(request: Request, session: Dict = Depends(verify_session_token)):
    """Test Telegram bot"""
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
                "username": bot_info.get("result", {}).get("username", "unknown"),
                "message": "Bot conectado correctamente"
            }
        else:
            return {"success": False, "message": "Token inválido"}
    except Exception as e:
        return {"success": False, "message": str(e)}

# ============================================================
# WhatsApp Configuration Endpoint
# ============================================================

@app.post("/api/config/whatsapp")
async def update_whatsapp_config(request: Request, session: Dict = Depends(verify_session_token)):
    """Update WhatsApp configuration"""
    data = await request.json()
    
    try:
        env_path = Path("/opt/swarmia/.env")
        if env_path.exists():
            with open(env_path, 'r') as f:
                lines = f.readlines()
            
            updated = False
            for i, line in enumerate(lines):
                if line.startswith("WHATSAPP_ENABLED="):
                    lines[i] = f"WHATSAPP_ENABLED={str(data.get('enabled', False)).lower()}\n"
                    updated = True
                    break
            if not updated:
                lines.append(f"WHATSAPP_ENABLED={str(data.get('enabled', False)).lower()}\n")
            
            with open(env_path, 'w') as f:
                f.writelines(lines)
        
        return {"success": True, "message": "Configuración WhatsApp guardada"}
    except Exception as e:
        return {"success": False, "message": str(e)}

# ============================================================
# System Configuration Endpoints
# ============================================================

@app.post("/api/config/system")
async def update_system_config(request: Request, session: Dict = Depends(verify_session_token)):
    """Update system configuration"""
    data = await request.json()
    
    try:
        env_path = Path("/opt/swarmia/.env")
        if env_path.exists():
            with open(env_path, 'r') as f:
                lines = f.readlines()
            
            if "server" in data:
                for i, line in enumerate(lines):
                    if line.startswith("SWARMIA_HOST="):
                        lines[i] = f"SWARMIA_HOST={data['server'].get('host', '0.0.0.0')}\n"
                    elif line.startswith("SWARMIA_PORT="):
                        lines[i] = f"SWARMIA_PORT={data['server'].get('port', 8080)}\n"
                    elif line.startswith("SWARMIA_DEBUG="):
                        lines[i] = f"SWARMIA_DEBUG={str(data['server'].get('debug', False)).lower()}\n"
            
            with open(env_path, 'w') as f:
                f.writelines(lines)
        
        return {"success": True, "message": "Configuración del sistema guardada"}
    except Exception as e:
        return {"success": False, "message": str(e)}

@app.post("/api/config/reset")
async def reset_config(request: Request, session: Dict = Depends(verify_session_token)):
    """Reset configuration to defaults"""
    try:
        env_path = Path("/opt/swarmia/.env")
        example_path = Path("/opt/swarmia/.env.example")
        
        if example_path.exists():
            import shutil
            shutil.copy(example_path, env_path)
        
        config_path = Path("/opt/swarmia/config/config.yaml")
        example_config_path = Path("/opt/swarmia/config/config.example.yaml")
        
        if example_config_path.exists():
            import shutil
            shutil.copy(example_config_path, config_path)
        
        return {"success": True, "message": "Configuración restablecida"}
    except Exception as e:
        return {"success": False, "message": str(e)}

# ============================================================
# Aggressive Agent Endpoints
# ============================================================

@app.get("/api/aggressive/dependencies")
async def get_aggressive_dependencies(request: Request, session: Dict = Depends(verify_session_token)):
    """Check aggressive agent dependencies"""
    deps = {
        "paramiko": {"installed": False, "name": "paramiko", "version": None},
        "cryptography": {"installed": False, "name": "cryptography", "version": None},
        "requests": {"installed": False, "name": "requests", "version": None}
    }
    
    try:
        import paramiko
        deps["paramiko"]["installed"] = True
        deps["paramiko"]["version"] = paramiko.__version__
    except ImportError:
        pass
    
    try:
        import cryptography
        deps["cryptography"]["installed"] = True
        deps["cryptography"]["version"] = cryptography.__version__
    except ImportError:
        pass
    
    try:
        import requests
        deps["requests"]["installed"] = True
        deps["requests"]["version"] = requests.__version__
    except ImportError:
        pass
    
    return deps

@app.post("/api/aggressive/install")
async def install_aggressive_dependencies(request: Request, session: Dict = Depends(verify_session_token)):
    """Install missing aggressive agent dependencies"""
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
        for dep in missing:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", dep],
                capture_output=True,
                text=True,
                timeout=60
            )
            if result.returncode != 0:
                return {"success": False, "message": f"Error instalando {dep}: {result.stderr}"}
        
        return {"success": True, "message": f"Dependencias instaladas: {', '.join(missing)}"}
    except Exception as e:
        return {"success": False, "message": str(e)}

@app.post("/api/config/aggressive")
async def save_aggressive_config(request: Request, session: Dict = Depends(verify_session_token)):
    """Save aggressive agent configuration"""
    data = await request.json()
    
    try:
        env_path = Path("/opt/swarmia/.env")
        if env_path.exists():
            with open(env_path, 'r') as f:
                lines = f.readlines()
            
            # Actualizar variables
            updates = {
                "AGGRESSIVE_ENABLED": str(data.get("enabled", False)).lower(),
                "AGGRESSIVE_MODE": data.get("mode", "normal"),
                "AGGRESSIVE_MAX_THREADS": str(data.get("max_threads", 50)),
                "AGGRESSIVE_TIMEOUT": str(data.get("timeout", 5)),
                "AGGRESSIVE_STEALTH": str(data.get("stealth", False)).lower(),
                "AGGRESSIVE_SSH_ENABLED": str(data.get("ssh_enabled", True)).lower(),
                "AGGRESSIVE_ALLOWED_NETWORKS": data.get("allowed_networks", "")
            }
            
            for key, value in updates.items():
                updated = False
                for i, line in enumerate(lines):
                    if line.startswith(f"{key}="):
                        lines[i] = f"{key}={value}\n"
                        updated = True
                        break
                if not updated:
                    lines.append(f"{key}={value}\n")
            
            with open(env_path, 'w') as f:
                f.writelines(lines)
        
        return {"success": True, "message": "Configuración guardada correctamente"}
    except Exception as e:
        return {"success": False, "message": str(e)}

@app.post("/api/aggressive/test")
async def test_aggressive_config(request: Request, session: Dict = Depends(verify_session_token)):
    """Test aggressive agent configuration"""
    if not getattr(config, 'AGGRESSIVE_ENABLED', False):
        return {"success": False, "message": "El agente agresivo no está activado"}
    
    allowed_networks = getattr(config, 'AGGRESSIVE_ALLOWED_NETWORKS', '')
    if not allowed_networks:
        return {"success": False, "message": "No hay redes permitidas configuradas"}
    
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
            return {"success": False, "message": f"Faltan dependencias para modo ULTRA: {', '.join(missing)}"}
    
    return {"success": True, "message": f"✅ Configuración válida. Modo: {mode.upper()}"}

# ============================================================
# Startup/Shutdown Events
# ============================================================

@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    init_database()
    
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
    
    asyncio.create_task(cleanup_sessions())
    print(f"✅ Dashboard initialized on port {config.SERVER_PORT}")

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
👤 Default credentials: admin / admin (change on first login)
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
