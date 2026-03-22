#!/usr/bin/env python3
"""
SwarmIA Dashboard Server - Elegant Web Interface
FastAPI-based dashboard with admin authentication and real-time monitoring
"""

import os
import json
import secrets
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

from fastapi import FastAPI, Request, Response, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import sqlite3

# Import project modules
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.config import Config
from core.supervisor import Supervisor, TaskPriority
from models.database import get_db_connection, init_database

# Initialize FastAPI app
app = FastAPI(
    title="SwarmIA Dashboard",
    description="Elegant dashboard for SwarmIA - The Enhanced OpenClaw",
    version="1.0.0",
    docs_url="/api/docs" if Config.DEBUG else None,
    redoc_url="/api/redoc" if Config.DEBUG else None
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if Config.DEBUG else ["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBasic()

# Templates and static files
BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# Global state
supervisor = Supervisor()
config = Config()
active_sessions: Dict[str, Dict] = {}
dashboard_stats = {
    "total_tasks": 0,
    "completed_tasks": 0,
    "active_agents": 0,
    "system_uptime": datetime.now(),
    "messages_processed": 0,
    "errors_count": 0
}

# Authentication functions
def verify_admin_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    """Verify admin credentials and force password change if still default"""
    correct_username = secrets.compare_digest(credentials.username, "admin")
    
    # Check if password has been changed from default
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT password_changed FROM users WHERE username = ?", ("admin",))
        result = cursor.fetchone()
        
        password_changed = result[0] if result else False
        default_password = "admin" if not password_changed else None
    
    if default_password:
        correct_password = secrets.compare_digest(credentials.password, default_password)
        if correct_password:
            # First login with default password - force change
            raise HTTPException(
                status_code=status.HTTP_307_TEMPORARY_REDIRECT,
                detail="Password change required",
                headers={"Location": "/change-password"}
            )
    else:
        # Check against stored hash
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT password_hash FROM users WHERE username = ?", ("admin",))
            result = cursor.fetchone()
            if result:
                stored_hash = result[0]
                # In production, use proper password hashing (bcrypt, argon2)
                # For MVP, using simple comparison
                correct_password = secrets.compare_digest(credentials.password, stored_hash)
            else:
                correct_password = False
    
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

# Cleanup old sessions periodically
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

# Routes
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, session: Dict = Depends(verify_session_token)):
    """Main dashboard page"""
    # Get system stats
    stats = {
        "uptime": str(datetime.now() - dashboard_stats["system_uptime"]).split('.')[0],
        "active_tasks": supervisor.get_active_task_count(),
        "completed_tasks": dashboard_stats["completed_tasks"],
        "agents_online": len(supervisor.get_available_agents()),
        "messages_today": dashboard_stats["messages_processed"],
        "system_load": os.getloadavg()[0] if hasattr(os, 'getloadavg') else 0.0
    }
    
    # Get recent tasks
    recent_tasks = supervisor.get_recent_tasks(limit=10)
    
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "username": session["username"],
            "stats": stats,
            "recent_tasks": recent_tasks,
            "config": config.get_public_config()
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
    
    # Create session token
    token = create_session_token(username)
    
    response = JSONResponse({
        "success": True,
        "message": "Login successful",
        "username": username
    })
    
    # Set session cookie (secure in production)
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        max_age=86400,  # 24 hours
        samesite="lax"
    )
    
    return response

@app.get("/change-password", response_class=HTMLResponse)
async def change_password_page(request: Request):
    """Password change page (forced on first login)"""
    return templates.TemplateResponse("change_password.html", {"request": request})

@app.post("/api/change-password")
async def api_change_password(
    request: Request,
    current_password: str,
    new_password: str,
    confirm_password: str
):
    """Change password API"""
    if new_password != confirm_password:
        raise HTTPException(status_code=400, detail="New passwords don't match")
    
    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    
    # Verify current password
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash, password_changed FROM users WHERE username = 'admin'")
        result = cursor.fetchone()
        
        if not result:
            raise HTTPException(status_code=500, detail="User not found")
        
        stored_hash, password_changed = result
        
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
    ai_config = config.get_ai_config()
    communication_config = config.get_communication_config()
    
    return templates.TemplateResponse(
        "config.html",
        {
            "request": request,
            "username": session["username"],
            "ai_config": ai_config,
            "communication_config": communication_config,
            "available_models": config.get_available_models()
        }
    )

@app.post("/api/config/ai")
async def update_ai_config(
    request: Request,
    ai_type: str,
    api_key: Optional[str] = None,
    model_path: Optional[str] = None,
    model_name: Optional[str] = None
):
    """Update AI configuration"""
    session = verify_session_token(request)
    
    if ai_type not in ["deepseek", "llama"]:
        raise HTTPException(status_code=400, detail="Invalid AI type")
    
    config.update_ai_config(ai_type, {
        "api_key": api_key,
        "model_path": model_path,
        "model_name": model_name,
        "enabled": True
    })
    
    return {"success": True, "message": f"{ai_type.capitalize()} configuration updated"}

@app.post("/api/config/communication")
async def update_communication_config(
    request: Request,
    platform: str,
    enabled: bool,
    config_data: Dict[str, Any]
):
    """Update communication platform configuration"""
    session = verify_session_token(request)
    
    if platform not in ["whatsapp", "telegram"]:
        raise HTTPException(status_code=400, detail="Invalid platform")
    
    config.update_communication_config(platform, {
        "enabled": enabled,
        **config_data
    })
    
    return {"success": True, "message": f"{platform.capitalize()} configuration updated"}

@app.get("/agents", response_class=HTMLResponse)
async def agents_page(request: Request, session: Dict = Depends(verify_session_token)):
    """Agents monitoring page"""
    agents = supervisor.get_agent_status()
    
    return templates.TemplateResponse(
        "agents.html",
        {
            "request": request,
            "username": session["username"],
            "agents": agents,
            "agent_types": supervisor.get_agent_types()
        }
    )

@app.get("/api/agents/status")
async def get_agents_status(request: Request):
    """Get real-time agent status (WebSocket compatible)"""
    session = verify_session_token(request)
    
    agents = supervisor.get_agent_status()
    return {"agents": agents, "timestamp": datetime.now().isoformat()}

@app.post("/api/agents/{agent_type}/restart")
async def restart_agent(agent_type: str, request: Request):
    """Restart a specific agent"""
    session = verify_session_token(request)
    
    success = supervisor.restart_agent(agent_type)
    if not success:
        raise HTTPException(status_code=404, detail=f"Agent type '{agent_type}' not found")
    
    return {"success": True, "message": f"Agent '{agent_type}' restarted"}

@app.get("/tasks", response_class=HTMLResponse)
async def tasks_page(request: Request, session: Dict = Depends(verify_session_token)):
    """Tasks monitoring page"""
    tasks = supervisor.get_all_tasks(limit=50)
    
    return templates.TemplateResponse(
        "tasks.html",
        {
            "request": request,
            "username": session["username"],
            "tasks": tasks,
            "task_priorities": TaskPriority.__members__
        }
    )

@app.get("/api/tasks/recent")
async def get_recent_tasks(request: Request, limit: int = 20):
    """Get recent tasks"""
    session = verify_session_token(request)
    
    tasks = supervisor.get_recent_tasks(limit=limit)
    return {"tasks": tasks}

@app.post("/api/tasks/{task_id}/cancel")
async def cancel_task(task_id: str, request: Request):
    """Cancel a running task"""
    session = verify_session_token(request)
    
    success = supervisor.cancel_task(task_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found or not cancellable")
    
    return {"success": True, "message": f"Task '{task_id}' cancelled"}

@app.get("/logs", response_class=HTMLResponse)
async def logs_page(request: Request, session: Dict = Depends(verify_session_token)):
    """System logs page"""
    log_files = config.get_log_files()
    
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
    
    if log_file not in config.get_log_files():
        raise HTTPException(status_code=404, detail="Log file not found")
    
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
    
    return {
        "dashboard_stats": dashboard_stats,
        "supervisor_stats": supervisor.get_stats(),
        "config_stats": config.get_stats(),
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/system/restart")
async def restart_system(request: Request):
    """Restart SwarmIA system (soft restart)"""
    session = verify_session_token(request)
    
    # This would trigger a system restart in production
    # For now, just log and return success
    config.log_system_event("SYSTEM_RESTART", f"Restart initiated by {session['username']}")
    
    return {
        "success": True,
        "message": "System restart initiated",
        "restart_time": datetime.now().isoformat()
    }

@app.get("/api/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "service": "swarmia-dashboard",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "uptime": str(datetime.now() - dashboard_stats["system_uptime"]),
        "active_sessions": len(active_sessions),
        "active_tasks": supervisor.get_active_task_count()
    }

@app.get("/api/network/info")
async def network_info():
    """Get network information for external access"""
    import socket
    
    try:
        # Get local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except:
        local_ip = "127.0.0.1"
    
    return {
        "local_ip": local_ip,
        "port": config.DASHBOARD_PORT,
        "dashboard_url": f"http://{local_ip}:{config.DASHBOARD_PORT}",
        "api_url": f"http://{local_ip}:{config.DASHBOARD_PORT}/api",
        "external_access_required": True,
        "instructions": f"Access dashboard at http://{local_ip}:{config.DASHBOARD_PORT} or http://YOUR_EXTERNAL_IP:{config.DASHBOARD_PORT}"
    }

@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    # Initialize database
    init_database()
    
    # Create default admin user if not exists
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO users (username, password_hash, password_changed, created_at)
            VALUES ('admin', 'admin', 0, datetime('now'))
        """)
        conn.commit()
    
    # Start session cleanup task
    asyncio.create_task(cleanup_sessions())
    
    # Log startup
    config.log_system_event("DASHBOARD_START", f"Dashboard started on port {config.DASHBOARD_PORT}")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    config.log_system_event("DASHBOARD_STOP", "Dashboard shutting down")

def main():
    """Main entry point for dashboard server"""
    print(f"🚀 Starting SwarmIA Dashboard on port {config.DASHBOARD_PORT}")
    print(f"📊 Dashboard URL: http://localhost:{config.DASHBOARD_PORT}")
    print(f"🔧 API Docs: http://localhost:{config.DASHBOARD_PORT}/api/docs")
    print(f"👤 Default credentials: admin / admin (change required on first login)")
    print(f"📡 Network info: http://localhost:{config.DASHBOARD_PORT}/api/network/info")
    
    uvicorn.run(
        "server:app",
        host="0.0.0.0",  # Listen on all interfaces
