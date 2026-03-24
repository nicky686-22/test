#!/usr/bin/env python3
"""
Agente API - Exposición de servicios de SwarmIA como API REST
Soporta: Endpoints personalizados, webhooks, integración con sistemas externos
Capacidades: crear endpoints, webhooks, autenticación API, documentación
"""

import os
import sys
import json
import asyncio
import secrets
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable
from pathlib import Path
from functools import wraps

# Importaciones FastAPI
try:
    from fastapi import FastAPI, APIRouter, HTTPException, Depends, Header, Request, BackgroundTasks
    from fastapi.responses import JSONResponse, PlainTextResponse
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
    from pydantic import BaseModel, Field
    import uvicorn
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    FastAPI = None
    APIRouter = None
    HTTPBearer = None

from src.core.agente import Agente, TipoAgente, ResultadoTarea
from src.core.supervisor import Supervisor
from src.core.config import Config


class AgenteAPI(Agente):
    """
    Agente API - Expone servicios de SwarmIA como API REST
    Permite integrar SwarmIA con otros sistemas mediante webhooks y endpoints
    """
    
    def __init__(self, supervisor: Supervisor, config: Config):
        super().__init__(
            id_agente="api",
            nombre="Agente API",
            tipo=TipoAgente.API,
            supervisor=supervisor,
            version="1.0.0"
        )
        self.config = config
        
        # Configuración API
        self.api_port = int(os.getenv("API_PORT", "8081"))
        self.api_key = os.getenv("API_KEY", secrets.token_urlsafe(32))
        self.webhook_secret = os.getenv("WEBHOOK_SECRET", secrets.token_urlsafe(32))
        
        # Endpoints registrados
        self.endpoints: Dict[str, Dict] = {}
        self.webhooks: Dict[str, Dict] = {}
        
        # Historial de peticiones
        self.peticiones: List[Dict] = []
        self.peticiones_max = 1000
        
        # Servidor API
        self.api_app = None
        self.api_server = None
        self.api_running = False
        
        self._registrar_capacidades()
        self._iniciar_servidor()
        self.logger.info(f"Agente API iniciado. Puerto: {self.api_port}")
        self.logger.info(f"API Key: {self.api_key[:20]}...")
    
    def _iniciar_servidor(self):
        """Iniciar servidor FastAPI en segundo plano"""
        if not FASTAPI_AVAILABLE:
            self.logger.warning("FastAPI no instalado. Instalar con: pip install fastapi uvicorn")
            return
        
        def run_server():
            self.api_app = FastAPI(title="SwarmIA API", version="2.0.0")
            self._configurar_endpoints_base()
            uvicorn.run(self.api_app, host="0.0.0.0", port=self.api_port, log_level="warning")
        
        import threading
        thread = threading.Thread(target=run_server, daemon=True)
        thread.start()
        self.api_running = True
        self.logger.info(f"Servidor API iniciado en http://0.0.0.0:{self.api_port}")
    
    def _configurar_endpoints_base(self):
        """Configurar endpoints base de la API"""
        from fastapi import FastAPI
        
        # Endpoint de salud
        @self.api_app.get("/health")
        async def health():
            return {"status": "healthy", "timestamp": datetime.now().isoformat()}
        
        # Endpoint de info
        @self.api_app.get("/info")
        async def info():
            return {
                "name": "SwarmIA API",
                "version": "2.0.0",
                "endpoints": list(self.endpoints.keys()),
                "webhooks": list(self.webhooks.keys())
            }
        
        # Endpoint para webhooks
        @self.api_app.post("/webhook/{nombre}")
        async def webhook_handler(nombre: str, request: Request, background_tasks: BackgroundTasks):
            """Manejar webhooks entrantes"""
            if nombre not in self.webhooks:
                raise HTTPException(status_code=404, detail=f"Webhook '{nombre}' no encontrado")
            
            # Verificar firma si está configurada
            signature = request.headers.get("X-Webhook-Signature")
            body = await request.body()
            
            webhook = self.webhooks[nombre]
            if webhook.get("verify_signature") and signature:
                expected = hmac.new(
                    self.webhook_secret.encode(),
                    body,
                    hashlib.sha256
                ).hexdigest()
                if not hmac.compare_digest(signature, expected):
                    raise HTTPException(status_code=401, detail="Firma inválida")
            
            # Procesar webhook
            try:
                data = await request.json()
            except:
                data = {"body": body.decode()}
            
            # Registrar petición
            self._registrar_peticion("webhook", nombre, data)
            
            # Crear tarea en supervisor
            if webhook.get("create_task"):
                self.supervisor.create_task(
                    task_type=webhook.get("task_type", "webhook"),
                    data={
                        "webhook": nombre,
                        "payload": data,
                        "timestamp": datetime.now().isoformat()
                    },
                    source="webhook"
                )
            
            return {"status": "received", "webhook": nombre}
    
    def _registrar_peticion(self, tipo: str, endpoint: str, data: Any):
        """Registrar petición en historial"""
        self.peticiones.append({
            "tipo": tipo,
            "endpoint": endpoint,
            "data": str(data)[:500],
            "timestamp": datetime.now().isoformat()
        })
        if len(self.peticiones) > self.peticiones_max:
            self.peticiones = self.peticiones[-self.peticiones_max:]
    
    def _registrar_capacidades(self):
        """Registrar capacidades del agente"""
        
        self.registrar_capacidad(
            nombre="api_endpoint_crear",
            descripcion="Crear un endpoint personalizado",
            parametros=["ruta", "metodo", "accion"],
            ejemplos=["crear endpoint /status que devuelva estado", "api endpoint"],
            nivel_riesgo="medio"
        )
        
        self.registrar_capacidad(
            nombre="api_endpoint_listar",
            descripcion="Listar endpoints creados",
            ejemplos=["listar endpoints", "qué endpoints tengo"],
            nivel_riesgo="bajo"
        )
        
        self.registrar_capacidad(
            nombre="api_endpoint_eliminar",
            descripcion="Eliminar un endpoint",
            parametros=["ruta"],
            ejemplos=["eliminar endpoint /status"],
            nivel_riesgo="medio"
        )
        
        self.registrar_capacidad(
            nombre="webhook_crear",
            descripcion="Crear un webhook",
            parametros=["nombre", "url", "eventos"],
            ejemplos=["crear webhook para GitHub", "webhook de despliegue"],
            nivel_riesgo="medio"
        )
        
        self.registrar_capacidad(
            nombre="webhook_listar",
            descripcion="Listar webhooks creados",
            ejemplos=["listar webhooks"],
            nivel_riesgo="bajo"
        )
        
        self.registrar_capacidad(
            nombre="webhook_eliminar",
            descripcion="Eliminar un webhook",
            parametros=["nombre"],
            ejemplos=["eliminar webhook github"],
            nivel_riesgo="medio"
        )
        
        self.registrar_capacidad(
            nombre="api_llamar",
            descripcion="Llamar a una API externa",
            parametros=["url", "metodo", "datos"],
            ejemplos=["llamar a API de clima", "consultar servicio externo"],
            nivel_riesgo="bajo"
        )
        
        self.registrar_capacidad(
            nombre="api_estado",
            descripcion="Ver estado de la API",
            ejemplos=["estado de la API", "ver si API está activa"],
            nivel_riesgo="bajo"
        )
        
        self.registrar_capacidad(
            nombre="api_historial",
            descripcion="Ver historial de peticiones",
            ejemplos=["ver peticiones API", "historial de webhooks"],
            nivel_riesgo="bajo"
        )
    
    async def ejecutar(self, tarea: Dict[str, Any]) -> ResultadoTarea:
        """Ejecuta tarea según tipo"""
        tipo = tarea.get("tipo", "")
        desc = tarea.get("descripcion", "").lower()
        parametros = tarea.get("parametros", {})
        
        if "api_endpoint_crear" in tipo or "crear endpoint" in desc:
            return await self._api_endpoint_crear(desc, parametros)
        
        elif "api_endpoint_listar" in tipo or "listar endpoints" in desc:
            return await self._api_endpoint_listar()
        
        elif "api_endpoint_eliminar" in tipo or "eliminar endpoint" in desc:
            return await self._api_endpoint_eliminar(desc, parametros)
        
        elif "webhook_crear" in tipo or "crear webhook" in desc:
            return await self._webhook_crear(desc, parametros)
        
        elif "webhook_listar" in tipo or "listar webhooks" in desc:
            return await self._webhook_listar()
        
        elif "webhook_eliminar" in tipo or "eliminar webhook" in desc:
            return await self._webhook_eliminar(desc, parametros)
        
        elif "api_llamar" in tipo or "llamar api" in desc:
            return await self._api_llamar(desc, parametros)
        
        elif "api_estado" in tipo or "estado api" in desc:
            return await self._api_estado()
        
        elif "api_historial" in tipo or "historial" in desc:
            return await self._api_historial()
        
        else:
            return ResultadoTarea(exito=False, error=f"No sé cómo manejar: {tipo}")
    
    # ============================================================
    # GESTIÓN DE ENDPOINTS
    # ============================================================
    
    async def _api_endpoint_crear(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Crear un endpoint personalizado"""
        ruta = parametros.get("ruta") or self._extraer_ruta(desc)
        metodo = parametros.get("metodo", "GET").upper()
        accion = parametros.get("accion") or self._extraer_accion(desc)
        
        if not ruta:
            return ResultadoTarea(exito=False, error="Especifica la ruta del endpoint")
        
        if not accion:
            return ResultadoTarea(exito=False, error="Especifica qué hacer cuando se llame")
        
        # Guardar endpoint
        endpoint_id = f"{metodo}_{ruta}"
        self.endpoints[endpoint_id] = {
            "ruta": ruta,
            "metodo": metodo,
            "accion": accion,
            "parametros": parametros.get("parametros", {}),
            "creado": datetime.now().isoformat()
        }
        
        # Registrar en FastAPI si está disponible
        if FASTAPI_AVAILABLE and self.api_app:
            self._registrar_endpoint_fastapi(endpoint_id)
        
        return ResultadoTarea(
            exito=True,
            datos={
                "ruta": ruta,
                "metodo": metodo,
                "accion": accion,
                "mensaje": f"Endpoint {metodo} {ruta} creado"
            }
        )
    
    def _registrar_endpoint_fastapi(self, endpoint_id: str):
        """Registrar endpoint en FastAPI"""
        if not self.api_app:
            return
        
        endpoint = self.endpoints[endpoint_id]
        ruta = endpoint["ruta"]
        metodo = endpoint["metodo"].lower()
        accion = endpoint["accion"]
        
        async def handler(request: Request):
            # Registrar petición
            try:
                body = await request.json() if request.method != "GET" else {}
            except:
                body = {}
            
            self._registrar_peticion("endpoint", ruta, body)
            
            # Ejecutar acción según lo definido
            if accion == "status":
                stats = self.supervisor.get_stats() if self.supervisor else {}
                return {"status": "ok", "stats": stats}
            elif accion == "agentes":
                agents = self.supervisor.get_agents() if self.supervisor else []
                return {"agentes": [a.get_info() for a in agents]}
            elif accion == "tareas":
                tasks = self.supervisor.get_tasks(limit=20) if self.supervisor else []
                return {"tareas": [t.__dict__ for t in tasks]}
            else:
                # Crear tarea en supervisor
                task_id = self.supervisor.create_task(
                    task_type="api_call",
                    data={"endpoint": ruta, "payload": body},
                    source="api"
                )
                return {"task_id": task_id, "status": "created"}
        
        # Agregar a FastAPI según método
        router = APIRouter()
        router.add_api_route(ruta, handler, methods=[metodo])
        self.api_app.include_router(router)
    
    async def _api_endpoint_listar(self) -> ResultadoTarea:
        """Listar endpoints creados"""
        endpoints_list = []
        for endpoint_id, data in self.endpoints.items():
            endpoints_list.append({
                "ruta": data["ruta"],
                "metodo": data["metodo"],
                "accion": data["accion"],
                "creado": data["creado"]
            })
        
        return ResultadoTarea(
            exito=True,
            datos={"endpoints": endpoints_list, "total": len(endpoints_list)}
        )
    
    async def _api_endpoint_eliminar(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Eliminar un endpoint"""
        ruta = parametros.get("ruta") or self._extraer_ruta(desc)
        metodo = parametros.get("metodo", "GET").upper()
        
        if not ruta:
            return ResultadoTarea(exito=False, error="Especifica la ruta del endpoint")
        
        endpoint_id = f"{metodo}_{ruta}"
        if endpoint_id in self.endpoints:
            del self.endpoints[endpoint_id]
            return ResultadoTarea(
                exito=True,
                datos={"mensaje": f"Endpoint {metodo} {ruta} eliminado"}
            )
        else:
            return ResultadoTarea(exito=False, error=f"Endpoint no encontrado: {metodo} {ruta}")
    
    # ============================================================
    # GESTIÓN DE WEBHOOKS
    # ============================================================
    
    async def _webhook_crear(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Crear un webhook"""
        nombre = parametros.get("nombre") or self._extraer_nombre(desc)
        url = parametros.get("url") or self._extraer_url(desc)
        eventos = parametros.get("eventos", ["*"])
        create_task = parametros.get("create_task", True)
        
        if not nombre:
            return ResultadoTarea(exito=False, error="Especifica el nombre del webhook")
        
        if not url:
            return ResultadoTarea(exito=False, error="Especifica la URL del webhook")
        
        self.webhooks[nombre] = {
            "nombre": nombre,
            "url": url,
            "eventos": eventos,
            "create_task": create_task,
            "verify_signature": parametros.get("verify_signature", False),
            "creado": datetime.now().isoformat()
        }
        
        return ResultadoTarea(
            exito=True,
            datos={
                "nombre": nombre,
                "url": url,
                "endpoint": f"http://localhost:{self.api_port}/webhook/{nombre}",
                "mensaje": f"Webhook '{nombre}' creado. URL: /webhook/{nombre}"
            }
        )
    
    async def _webhook_listar(self) -> ResultadoTarea:
        """Listar webhooks creados"""
        webhooks_list = []
        for nombre, data in self.webhooks.items():
            webhooks_list.append({
                "nombre": nombre,
                "url": data["url"],
                "eventos": data["eventos"],
                "creado": data["creado"]
            })
        
        return ResultadoTarea(
            exito=True,
            datos={"webhooks": webhooks_list, "total": len(webhooks_list)}
        )
    
    async def _webhook_eliminar(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Eliminar un webhook"""
        nombre = parametros.get("nombre") or self._extraer_nombre(desc)
        
        if not nombre:
            return ResultadoTarea(exito=False, error="Especifica el nombre del webhook")
        
        if nombre in self.webhooks:
            del self.webhooks[nombre]
            return ResultadoTarea(
                exito=True,
                datos={"mensaje": f"Webhook '{nombre}' eliminado"}
            )
        else:
            return ResultadoTarea(exito=False, error=f"Webhook '{nombre}' no encontrado")
    
    # ============================================================
    # LLAMAR API EXTERNA
    # ============================================================
    
    async def _api_llamar(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Llamar a una API externa"""
        url = parametros.get("url") or self._extraer_url(desc)
        metodo = parametros.get("metodo", "GET").upper()
        datos = parametros.get("datos", {})
        headers = parametros.get("headers", {})
        
        if not url:
            return ResultadoTarea(exito=False, error="Especifica la URL de la API")
        
        try:
            import requests
            self.logger.info(f"Llamando API {metodo} {url}")
            
            if metodo == "GET":
                response = requests.get(url, headers=headers, timeout=30)
            elif metodo == "POST":
                response = requests.post(url, json=datos, headers=headers, timeout=30)
            elif metodo == "PUT":
                response = requests.put(url, json=datos, headers=headers, timeout=30)
            elif metodo == "DELETE":
                response = requests.delete(url, headers=headers, timeout=30)
            else:
                return ResultadoTarea(exito=False, error=f"Método no soportado: {metodo}")
            
            return ResultadoTarea(
                exito=response.status_code < 400,
                datos={
                    "url": url,
                    "metodo": metodo,
                    "status": response.status_code,
                    "contenido": response.text[:500],
                    "headers": dict(response.headers)
                }
            )
        except Exception as e:
            return ResultadoTarea(exito=False, error=str(e))
    
    # ============================================================
    # ESTADO E HISTORIAL
    # ============================================================
    
    async def _api_estado(self) -> ResultadoTarea:
        """Ver estado de la API"""
        return ResultadoTarea(
            exito=True,
            datos={
                "api_running": self.api_running,
                "puerto": self.api_port,
                "endpoints": len(self.endpoints),
                "webhooks": len(self.webhooks),
                "peticiones": len(self.peticiones),
                "api_key": self.api_key[:20] + "..."
            }
        )
    
    async def _api_historial(self) -> ResultadoTarea:
        """Ver historial de peticiones"""
        return ResultadoTarea(
            exito=True,
            datos={
                "peticiones": self.peticiones[-50:],
                "total": len(self.peticiones)
            }
        )
    
    # ============================================================
    # EXTRACTORES
    # ============================================================
    
    def _extraer_ruta(self, desc: str) -> Optional[str]:
        """Extraer ruta de la descripción"""
        import re
        match = re.search(r'/([a-zA-Z0-9_-]+)', desc)
        if match:
            return f"/{match.group(1)}"
        return None
    
    def _extraer_accion(self, desc: str) -> Optional[str]:
        """Extraer acción de la descripción"""
        if "status" in desc.lower():
            return "status"
        elif "agente" in desc.lower() or "agentes" in desc.lower():
            return "agentes"
        elif "tarea" in desc.lower() or "tareas" in desc.lower():
            return "tareas"
        return "task"
    
    def _extraer_nombre(self, desc: str) -> Optional[str]:
        """Extraer nombre de la descripción"""
        import re
        match = re.search(r'(?:webhook|nombre)[:\s]+([a-zA-Z0-9_-]+)', desc, re.IGNORECASE)
        if match:
            return match.group(1)
        return None
    
    def _extraer_url(self, desc: str) -> Optional[str]:
        """Extraer URL de la descripción"""
        import re
        match = re.search(r'https?://[^\s]+', desc)
        if match:
            return match.group(0)
        return None


# ============================================================
# Factory Function
# ============================================================

def crear_agente_api(supervisor: Supervisor, config: Config) -> AgenteAPI:
    """Crea instancia del agente API"""
    return AgenteAPI(supervisor, config)
