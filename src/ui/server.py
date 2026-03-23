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
async def api_change_password(
    request: Request,
    current_password: str = None,
    new_password: str = None,
    confirm_password: str = None
):
    """Change password API"""
    # Get data from request body
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
    
    # Convert to dict for JSON serialization
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
