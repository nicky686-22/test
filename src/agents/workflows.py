#!/usr/bin/env python3
"""
Agente Workflows - Coordinación de tareas complejas y automatizaciones
Permite encadenar acciones de múltiples agentes en flujos de trabajo con dependencias
"""

import json
import yaml
import asyncio
import threading
import time
import re
from typing import Dict, Any, Optional, List, Callable, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
from dataclasses import dataclass, field
from queue import Queue

from src.core.agente import Agente, TipoAgente, ResultadoTarea
from src.core.supervisor import Supervisor, TaskPriority
from src.core.config import Config


class WorkflowStatus(Enum):
    """Estado de un workflow"""
    PENDIENTE = "pendiente"
    EJECUTANDO = "ejecutando"
    COMPLETADO = "completado"
    FALLIDO = "fallido"
    PAUSADO = "pausado"
    CANCELADO = "cancelado"


class WorkflowTrigger(Enum):
    """Tipo de trigger para workflow"""
    MANUAL = "manual"
    PROGRAMADO = "programado"
    EVENTO = "evento"
    WEBHOOK = "webhook"


@dataclass
class WorkflowStep:
    """Paso individual de un workflow"""
    id: str
    nombre: str
    agente: str  # agente que ejecuta (archivos, ssh, web, etc)
    accion: str  # acción a ejecutar
    parametros: Dict[str, Any] = field(default_factory=dict)
    dependencias: List[str] = field(default_factory=list)  # IDs de pasos que deben completarse antes
    condicion: Optional[str] = None  # condición para ejecutar
    on_failure: str = "stop"  # stop, continue, retry
    timeout: int = 60
    max_retries: int = 3
    resultado: Optional[Any] = None
    estado: str = "pendiente"  # pendiente, ejecutando, completado, fallido, saltado
    error: Optional[str] = None
    tarea_id: Optional[str] = None  # ID de la tarea creada en supervisor


@dataclass
class Workflow:
    """Workflow completo"""
    id: str
    nombre: str
    descripcion: str
    pasos: List[WorkflowStep]
    trigger: WorkflowTrigger = WorkflowTrigger.MANUAL
    schedule: Optional[str] = None  # cron expression
    variables: Dict[str, Any] = field(default_factory=dict)
    estado: WorkflowStatus = WorkflowStatus.PENDIENTE
    creado: datetime = field(default_factory=datetime.now)
    ejecutado: Optional[datetime] = None
    completado: Optional[datetime] = None
    ejecuciones: int = 0
    ultimo_resultado: Optional[Dict] = None
    notificar_resultado: bool = True
    notificar_canal: str = "telegram"  # telegram, whatsapp, email, all


class AgenteWorkflows(Agente):
    """
    Agente de Workflows - Coordina tareas complejas entre múltiples agentes
    Crea tareas en el supervisor en el orden correcto con dependencias
    """
    
    def __init__(self, supervisor: Supervisor, config: Config):
        super().__init__(
            id_agente="workflows",
            nombre="Agente Workflows",
            tipo=TipoAgente.AUTOMATIZACION,
            supervisor=supervisor,
            version="1.0.0"
        )
        self.config = config
        self.workflows: Dict[str, Workflow] = {}
        self.workflows_activos: Dict[str, threading.Thread] = {}
        self.workflows_dir = Path("config/workflows")
        self.workflows_dir.mkdir(parents=True, exist_ok=True)
        
        self._registrar_capacidades()
        self._cargar_workflows()
        self._iniciar_scheduler()
        
        self.logger.info("Agente Workflows iniciado")
    
    def _registrar_capacidades(self):
        """Registrar capacidades del agente"""
        
        self.registrar_capacidad(
            nombre="workflow_crear",
            descripcion="Crear un nuevo workflow",
            parametros=["nombre", "descripcion", "pasos"],
            ejemplos=[
                "crear workflow backup que haga backup de BD, comprima y suba a S3",
                "crear workflow despliegue que clone repo, instale dependencias y reinicie servicio"
            ],
            nivel_riesgo="medio"
        )
        
        self.registrar_capacidad(
            nombre="workflow_ejecutar",
            descripcion="Ejecutar un workflow existente",
            parametros=["nombre"],
            ejemplos=["ejecutar workflow backup", "correr workflow despliegue"],
            nivel_riesgo="alto"
        )
        
        self.registrar_capacidad(
            nombre="workflow_listar",
            descripcion="Listar workflows disponibles",
            ejemplos=["listar workflows", "qué workflows tengo"],
            nivel_riesgo="bajo"
        )
        
        self.registrar_capacidad(
            nombre="workflow_eliminar",
            descripcion="Eliminar un workflow",
            parametros=["nombre"],
            ejemplos=["eliminar workflow backup"],
            nivel_riesgo="medio"
        )
        
        self.registrar_capacidad(
            nombre="workflow_programar",
            descripcion="Programar un workflow para ejecución automática",
            parametros=["nombre", "cron"],
            ejemplos=["programar backup cada día a las 3am", "programar cada hora"],
            nivel_riesgo="medio"
        )
        
        self.registrar_capacidad(
            nombre="workflow_estado",
            descripcion="Ver estado de un workflow o ejecución",
            parametros=["nombre", "ejecucion_id"],
            ejemplos=["estado del workflow backup", "ver ejecución de backup"],
            nivel_riesgo="bajo"
        )
        
        self.registrar_capacidad(
            nombre="workflow_cancelar",
            descripcion="Cancelar un workflow en ejecución",
            parametros=["nombre"],
            ejemplos=["cancelar workflow backup"],
            nivel_riesgo="medio"
        )
    
    async def ejecutar(self, tarea: Dict[str, Any]) -> ResultadoTarea:
        """Ejecutar tarea según tipo"""
        tipo = tarea.get("tipo", "")
        desc = tarea.get("descripcion", "").lower()
        parametros = tarea.get("parametros", {})
        
        if "workflow_crear" in tipo or "crear workflow" in desc:
            return await self._crear_workflow(desc, parametros)
        
        elif "workflow_ejecutar" in tipo or "ejecutar workflow" in desc:
            return await self._ejecutar_workflow(desc, parametros)
        
        elif "workflow_listar" in tipo or "listar workflows" in desc:
            return await self._listar_workflows()
        
        elif "workflow_eliminar" in tipo or "eliminar workflow" in desc:
            return await self._eliminar_workflow(desc, parametros)
        
        elif "workflow_programar" in tipo or "programar workflow" in desc:
            return await self._programar_workflow(desc, parametros)
        
        elif "workflow_estado" in tipo or "estado workflow" in desc:
            return await self._estado_workflow(desc, parametros)
        
        elif "workflow_cancelar" in tipo or "cancelar workflow" in desc:
            return await self._cancelar_workflow(desc, parametros)
        
        else:
            return ResultadoTarea(exito=False, error=f"No sé cómo manejar: {tipo}")
    
    # ============================================================
    # CREACIÓN DE WORKFLOWS
    # ============================================================
    
    async def _crear_workflow(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Crear un nuevo workflow desde descripción en lenguaje natural"""
        
        nombre = parametros.get("nombre") or self._extraer_nombre(desc)
        descripcion = parametros.get("descripcion", desc)
        pasos = parametros.get("pasos", [])
        
        if not nombre:
            nombre = f"workflow_{len(self.workflows) + 1}"
        
        # Si no hay pasos definidos, inferir de la descripción
        if not pasos:
            pasos = self._inferir_pasos(desc)
        
        if not pasos:
            return ResultadoTarea(
                exito=False,
                error="No se pudieron inferir los pasos. Especifica los pasos claramente.\n\n"
                      "Ejemplo: 'crear workflow backup que: 1) backup BD, 2) comprimir, 3) subir a S3'"
            )
        
        # Crear los pasos del workflow
        workflow_pasos = []
        for i, paso in enumerate(pasos):
            workflow_pasos.append(WorkflowStep(
                id=f"step_{i+1}",
                nombre=paso.get("nombre", f"Paso {i+1}"),
                agente=paso.get("agente") or self._detectar_agente(paso.get("accion", "")),
                accion=paso.get("accion") or paso.get("comando", ""),
                parametros=paso.get("parametros", {}),
                dependencias=paso.get("dependencias", [f"step_{j}" for j in paso.get("depende_de", [])]),
                condicion=paso.get("condicion"),
                on_failure=paso.get("on_failure", "stop"),
                timeout=paso.get("timeout", 60),
                max_retries=paso.get("max_retries", 3)
            ))
        
        workflow = Workflow(
            id=f"wf_{len(self.workflows) + 1}_{nombre.replace(' ', '_')}",
            nombre=nombre,
            descripcion=descripcion,
            pasos=workflow_pasos,
            variables=parametros.get("variables", {})
        )
        
        self.workflows[workflow.id] = workflow
        self._guardar_workflow(workflow)
        
        # Mostrar resumen de pasos
        resumen_pasos = "\n".join([
            f"  {i+1}. {p.nombre}: {p.agente} → {p.accion[:50]}" 
            for i, p in enumerate(workflow_pasos)
        ])
        
        return ResultadoTarea(
            exito=True,
            datos={
                "workflow_id": workflow.id,
                "nombre": nombre,
                "pasos": len(workflow_pasos),
                "detalle_pasos": resumen_pasos,
                "mensaje": f"✅ Workflow '{nombre}' creado con {len(workflow_pasos)} pasos"
            }
        )
    
    def _inferir_pasos(self, desc: str) -> List[Dict]:
        """Inferir pasos de un workflow desde descripción en lenguaje natural"""
        pasos = []
        desc_lower = desc.lower()
        
        # Detectar patrones comunes de workflows
        if "backup" in desc_lower:
            pasos = self._inferir_workflow_backup(desc)
        elif "despliegue" in desc_lower or "deploy" in desc_lower:
            pasos = self._inferir_workflow_despliegue(desc)
        elif "monitoreo" in desc_lower or "monitor" in desc_lower:
            pasos = self._inferir_workflow_monitoreo(desc)
        elif "limpieza" in desc_lower or "cleanup" in desc_lower:
            pasos = self._inferir_workflow_limpieza(desc)
        else:
            # Intentar extraer pasos de la descripción
            pasos = self._extraer_pasos_de_texto(desc)
        
        return pasos
    
    def _inferir_workflow_backup(self, desc: str) -> List[Dict]:
        """Inferir workflow de backup"""
        pasos = []
        
        # Paso 1: Backup de BD (si menciona BD)
        if "bd" in desc or "base de datos" in desc or "mysql" in desc or "postgres" in desc:
            pasos.append({
                "nombre": "Backup Base de Datos",
                "agente": "base_datos",
                "accion": "backup",
                "parametros": {"tipo": "completo"}
            })
        
        # Paso 2: Backup de archivos (si menciona archivos)
        if "archivo" in desc or "carpeta" in desc or "files" in desc:
            pasos.append({
                "nombre": "Backup Archivos",
                "agente": "archivos",
                "accion": "backup",
                "parametros": {"origen": "/data", "destino": "/backup"}
            })
        
        # Paso 3: Comprimir
        if "comprimir" in desc or "zip" in desc or "tar" in desc:
            pasos.append({
                "nombre": "Comprimir Backup",
                "agente": "archivos",
                "accion": "comprimir",
                "depende_de": [len(pasos) - 1] if pasos else []
            })
        
        # Paso 4: Subir a la nube
        if "s3" in desc or "google drive" in desc or "dropbox" in desc or "nube" in desc:
            pasos.append({
                "nombre": "Subir a la Nube",
                "agente": "cloud",
                "accion": "upload",
                "depende_de": [len(pasos) - 1] if pasos else []
            })
        
        # Paso 5: Notificar
        if "notificar" in desc or "telegram" in desc or "email" in desc:
            pasos.append({
                "nombre": "Notificar Resultado",
                "agente": "notificaciones",
                "accion": "enviar",
                "parametros": {"mensaje": "Backup completado"}
            })
        
        return pasos
    
    def _inferir_workflow_despliegue(self, desc: str) -> List[Dict]:
        """Inferir workflow de despliegue"""
        pasos = []
        
        # Paso 1: Clonar/clonar repositorio
        if "git" in desc or "clonar" in desc:
            pasos.append({
                "nombre": "Clonar Repositorio",
                "agente": "git",
                "accion": "clone"
            })
        
        # Paso 2: Instalar dependencias
        if "dependencias" in desc or "pip" in desc or "npm" in desc:
            pasos.append({
                "nombre": "Instalar Dependencias",
                "agente": "paquetes",
                "accion": "instalar",
                "depende_de": [0] if pasos else []
            })
        
        # Paso 3: Ejecutar tests
        if "test" in desc or "prueba" in desc:
            pasos.append({
                "nombre": "Ejecutar Tests",
                "agente": "sistema",
                "accion": "ejecutar",
                "parametros": {"comando": "pytest"},
                "depende_de": [len(pasos) - 1] if pasos else []
            })
        
        # Paso 4: Reiniciar servicio
        pasos.append({
            "nombre": "Reiniciar Servicio",
            "agente": "sistema",
            "accion": "servicio_reiniciar",
            "depende_de": [len(pasos) - 1] if pasos else []
        })
        
        return pasos
    
    def _inferir_workflow_monitoreo(self, desc: str) -> List[Dict]:
        """Inferir workflow de monitoreo"""
        pasos = []
        
        # Paso 1: Verificar servicios
        pasos.append({
            "nombre": "Verificar Servicios",
            "agente": "sistema",
            "accion": "servicios_estado"
        })
        
        # Paso 2: Verificar recursos
        if "cpu" in desc or "memoria" in desc or "disco" in desc:
            pasos.append({
                "nombre": "Verificar Recursos",
                "agente": "monitor",
                "accion": "recursos",
                "depende_de": []
            })
        
        # Paso 3: Verificar red
        if "red" in desc or "ping" in desc or "conectividad" in desc:
            pasos.append({
                "nombre": "Verificar Conectividad",
                "agente": "red",
                "accion": "ping",
                "depende_de": []
            })
        
        # Paso 4: Generar reporte
        pasos.append({
            "nombre": "Generar Reporte",
            "agente": "monitor",
            "accion": "reporte",
            "depende_de": list(range(len(pasos)))
        })
        
        return pasos
    
    def _inferir_workflow_limpieza(self, desc: str) -> List[Dict]:
        """Inferir workflow de limpieza"""
        pasos = []
        
        # Paso 1: Limpiar logs
        if "log" in desc:
            pasos.append({
                "nombre": "Limpiar Logs Antiguos",
                "agente": "archivos",
                "accion": "limpiar",
                "parametros": {"ruta": "/var/log", "dias": 30}
            })
        
        # Paso 2: Limpiar temporales
        pasos.append({
            "nombre": "Limpiar Archivos Temporales",
            "agente": "archivos",
            "accion": "limpiar",
            "parametros": {"ruta": "/tmp", "dias": 7}
        })
        
        # Paso 3: Limpiar caché
        if "cache" in desc:
            pasos.append({
                "nombre": "Limpiar Caché",
                "agente": "paquetes",
                "accion": "limpiar",
                "depende_de": []
            })
        
        return pasos
    
    def _extraer_pasos_de_texto(self, desc: str) -> List[Dict]:
        """Extraer pasos de texto estructurado (con números o viñetas)"""
        pasos = []
        
        # Buscar patrones como "1) ...", "2) ..." o "1. ...", "2. ..."
        patron = r'(?:(\d+)[\)\.]\s*([^;]+?)(?=(?:\d+[\)\.]|$))'
        matches = re.findall(patron, desc, re.DOTALL)
        
        for num, texto in matches:
            texto = texto.strip()
            # Inferir agente por palabras clave
            agente = self._detectar_agente(texto)
            pasos.append({
                "nombre": f"Paso {num}",
                "agente": agente,
                "accion": texto[:100],
                "parametros": {"descripcion": texto}
            })
        
        return pasos
    
    def _detectar_agente(self, accion: str) -> str:
        """Detectar qué agente debe ejecutar una acción"""
        accion_lower = accion.lower()
        
        # Mapeo de palabras clave a agentes
        mapeo = {
            "archivos": ["archivo", "carpeta", "mkdir", "touch", "cp", "mv", "rm", "ls"],
            "sistema": ["comando", "ejecutar", "run", "shell", "proceso", "servicio"],
            "red": ["ping", "dns", "nmap", "escanear", "puerto", "traceroute"],
            "seguridad": ["ssh", "firewall", "iptables", "certificado", "ssl"],
            "base_datos": ["bd", "mysql", "postgres", "mongodb", "consulta", "sql"],
            "web": ["http", "https", "api", "curl", "wget", "scraping"],
            "cloud": ["s3", "google", "dropbox", "nube", "upload"],
            "notificaciones": ["notificar", "telegram", "email", "slack", "alerta"],
            "monitor": ["cpu", "memoria", "disco", "proceso", "top"],
            "paquetes": ["instalar", "pip", "npm", "apt", "yum"],
            "git": ["git", "clone", "pull", "commit", "push"],
            "workflows": ["workflow", "flujo"]
        }
        
        for agente, palabras in mapeo.items():
            for palabra in palabras:
                if palabra in accion_lower:
                    return agente
        
        return "sistema"  # agente por defecto
    
    def _extraer_nombre(self, desc: str) -> str:
        """Extraer nombre del workflow de la descripción"""
        # Buscar "workflow [nombre]"
        match = re.search(r'workflow\s+([a-zA-Z0-9_]+)', desc, re.IGNORECASE)
        if match:
            return match.group(1)
        
        # Buscar "llamado [nombre]"
        match = re.search(r'llamado\s+([a-zA-Z0-9_]+)', desc, re.IGNORECASE)
        if match:
            return match.group(1)
        
        # Buscar "nombre [nombre]"
        match = re.search(r'nombre\s+([a-zA-Z0-9_]+)', desc, re.IGNORECASE)
        if match:
            return match.group(1)
        
        return None
    
    # ============================================================
    # EJECUCIÓN DE WORKFLOWS
    # ============================================================
    
    async def _ejecutar_workflow(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Ejecutar un workflow existente"""
        nombre = parametros.get("nombre") or self._extraer_nombre(desc)
        
        if not nombre:
            return ResultadoTarea(exito=False, error="Especifica qué workflow ejecutar")
        
        # Buscar workflow por nombre o ID
        workflow = None
        for wf in self.workflows.values():
            if wf.nombre == nombre or wf.id == nombre:
                workflow = wf
                break
        
        if not workflow:
            return ResultadoTarea(
                exito=False,
                error=f"Workflow '{nombre}' no encontrado. Workflows disponibles: {', '.join([w.nombre for w in self.workflows.values()])}"
            )
        
        # Iniciar ejecución en thread separado
        def ejecutar():
            self._ejecutar_workflow_sync(workflow)
        
        thread = threading.Thread(target=ejecutar, daemon=True)
        thread.start()
        
        return ResultadoTarea(
            exito=True,
            datos={
                "workflow": workflow.nombre,
                "estado": "ejecutando",
                "mensaje": f"🔄 Ejecutando workflow '{workflow.nombre}' con {len(workflow.pasos)} pasos"
            }
        )
    
    def _ejecutar_workflow_sync(self, workflow: Workflow):
        """Ejecutar workflow en modo síncrono (en thread)"""
        workflow.estado = WorkflowStatus.EJECUTANDO
        workflow.ejecutado = datetime.now()
        workflow.ejecuciones += 1
        
        self.logger.info(f"Ejecutando workflow: {workflow.nombre}")
        
        # Resetear estado de pasos
        for paso in workflow.pasos:
            paso.estado = "pendiente"
            paso.resultado = None
            paso.error = None
            paso.tarea_id = None
        
        # Ejecutar pasos en orden topológico (respetando dependencias)
        pasos_restantes = workflow.pasos.copy()
        pasos_completados = []
        fallo = False
        
        while pasos_restantes and not fallo:
            # Buscar pasos que tienen todas sus dependencias completadas
        for paso in workflow.pasos:
            if paso.estado != "pendiente":
                continue
            
            # Verificar dependencias
            dependencias_ok = True
            for dep_id in paso.dependencias:
                dep_paso = next((p for p in workflow.pasos if p.id == dep_id), None)
                if not dep_paso or dep_paso.estado != "completado":
                    dependencias_ok = False
                    break
            
            if not dependencias_ok:
                continue
            
            # Ejecutar paso
            self._ejecutar_paso(workflow, paso)
            
            if paso.estado == "fallido":
                if paso.on_failure == "stop":
                    fallo = True
                    break
                elif paso.on_failure == "continue":
                    continue
                elif paso.on_failure == "retry":
                    # Reintentar después de un tiempo
                    time.sleep(5)
                    self._ejecutar_paso(workflow, paso)
        
        # Actualizar estado final del workflow
        if fallo:
            workflow.estado = WorkflowStatus.FALLIDO
            self.logger.error(f"Workflow {workflow.nombre} falló")
        else:
            workflow.estado = WorkflowStatus.COMPLETADO
            workflow.completado = datetime.now()
            self.logger.info(f"Workflow {workflow.nombre} completado")
        
        # Notificar resultado
        if workflow.notificar_resultado:
            self._notificar_resultado(workflow)
    
    def _ejecutar_paso(self, workflow: Workflow, paso: WorkflowStep):
        """Ejecutar un paso del workflow creando una tarea en el supervisor"""
        paso.estado = "ejecutando"
        
        # Verificar condición
        if paso.condicion:
            if not self._evaluar_condicion(paso.condicion, workflow.variables):
                paso.estado = "saltado"
                return
        
        self.logger.info(f"Ejecutando paso {paso.id}: {paso.nombre} ({paso.agente} → {paso.accion})")
        
        # Crear tarea en el supervisor
        tarea_id = self.supervisor.create_task(
            task_type=paso.accion,
            data={
                "descripcion": paso.accion,
                "parametros": paso.parametros,
                "workflow_id": workflow.id,
                "paso_id": paso.id
            },
            priority=TaskPriority.NORMAL,
            source=f"workflow_{workflow.id}",
            timeout=paso.timeout
        )
        
        paso.tarea_id = tarea_id
        
        # Esperar resultado (con timeout)
        start_time = time.time()
        while time.time() - start_time < paso.timeout:
            tarea = self.supervisor.get_task(tarea_id)
            if tarea and tarea.status.value == "completed":
                paso.estado = "completado"
                paso.resultado = tarea.result
                break
            elif tarea and tarea.status.value == "failed":
                paso.estado = "fallido"
                paso.error = tarea.error
                break
            time.sleep(0.5)
        
        if paso.estado == "ejecutando":
            paso.estado = "fallido"
            paso.error = "Timeout"
            self.supervisor.cancel_task(tarea_id, "Workflow timeout")
    
    def _evaluar_condicion(self, condicion: str, variables: Dict) -> bool:
        """Evaluar una condición (ej: "{{resultado.status}} == 'success'")"""
        try:
            # Simple evaluación de variables
            for key, value in variables.items():
                condicion = condicion.replace(f"{{{{{key}}}}}", str(value))
            return eval(condicion)
        except:
            return True
    
    def _notificar_resultado(self, workflow: Workflow):
        """Notificar resultado del workflow"""
        pasos_resumen = []
        for paso in workflow.pasos:
            icono = "✅" if paso.estado == "completado" else "❌" if paso.estado == "fallido" else "⏭️"
            pasos_resumen.append(f"  {icono} {paso.nombre}: {paso.estado}")
        
        mensaje = f"""
📋 *WORKFLOW COMPLETADO*

*Nombre:* {workflow.nombre}
*Estado:* {workflow.estado.value.upper()}
*Duración:* {(workflow.completado - workflow.ejecutado).seconds if workflow.completado else 0} segundos
*Ejecuciones totales:* {workflow.ejecuciones}

*Pasos:*
{chr(10).join(pasos_resumen)}
        """
        
        # Crear tarea de notificación en supervisor
        self.supervisor.create_task(
            task_type="notificar",
            data={
                "mensaje": mensaje,
                "canal": workflow.notificar_canal
            },
            priority=TaskPriority.LOW,
            source="workflows"
        )
    
    # ============================================================
    # GESTIÓN DE WORKFLOWS
    # ============================================================
    
    async def _listar_workflows(self) -> ResultadoTarea:
        """Listar workflows disponibles"""
        workflows_info = []
        for wf in self.workflows.values():
            workflows_info.append({
                "nombre": wf.nombre,
                "id": wf.id,
                "descripcion": wf.descripcion[:100],
                "pasos": len(wf.pasos),
                "estado": wf.estado.value,
                "ejecuciones": wf.ejecuciones,
                "programado": wf.schedule is not None
            })
        
        return ResultadoTarea(
            exito=True,
            datos={
                "workflows": workflows_info,
                "total": len(workflows_info),
                "mensaje": f"{len(workflows_info)} workflows disponibles"
            }
        )
    
    async def _eliminar_workflow(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Eliminar un workflow"""
        nombre = parametros.get("nombre") or self._extraer_nombre(desc)
        
        if not nombre:
            return ResultadoTarea(exito=False, error="Especifica qué workflow eliminar")
        
        workflow_id = None
        for wf_id, wf in self.workflows.items():
            if wf.nombre == nombre or wf.id == nombre:
                workflow_id = wf_id
                break
        
        if not workflow_id:
            return ResultadoTarea(exito=False, error=f"Workflow '{nombre}' no encontrado")
        
        del self.workflows[workflow_id]
        self._eliminar_archivo_workflow(workflow_id)
        
        return ResultadoTarea(
            exito=True,
            datos={"nombre": nombre, "mensaje": f"Workflow '{nombre}' eliminado"}
        )
    
    async def _programar_workflow(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Programar un workflow para ejecución automática"""
        nombre = parametros.get("nombre") or self._extraer_nombre(desc)
        cron = parametros.get("cron")
        
        if not nombre:
            return ResultadoTarea(exito=False, error="Especifica qué workflow programar")
        
        if not cron:
            # Extraer cron de descripción
            if "cada" in desc:
                if "hora" in desc:
                    cron = "0 * * * *"
                elif "día" in desc or "dia" in desc:
                    cron = "0 0 * * *"
                else:
                    cron = "*/5 * * * *"  # cada 5 minutos
            else:
                return ResultadoTarea(exito=False, error="Especifica la programación (ej: cada hora, cada día a las 3am)")
        
        workflow = None
        for wf in self.workflows.values():
            if wf.nombre == nombre:
                workflow = wf
                break
        
        if not workflow:
            return ResultadoTarea(exito=False, error=f"Workflow '{nombre}' no encontrado")
        
        workflow.schedule = cron
        workflow.trigger = WorkflowTrigger.PROGRAMADO
        self._guardar_workflow(workflow)
        
        return ResultadoTarea(
            exito=True,
            datos={
                "workflow": nombre,
                "cron": cron,
                "mensaje": f"Workflow '{nombre}' programado con {cron}"
            }
        )
    
    async def _estado_workflow(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Ver estado de un workflow"""
        nombre = parametros.get("nombre") or self._extraer_nombre(desc)
        
        if not nombre:
            return ResultadoTarea(exito=False, error="Especifica qué workflow consultar")
        
        workflow = None
        for wf in self.workflows.values():
            if wf.nombre == nombre:
                workflow = wf
                break
        
        if not workflow:
            return ResultadoTarea(exito=False, error=f"Workflow '{nombre}' no encontrado")
        
        pasos_info = []
        for paso in workflow.pasos:
            pasos_info.append({
                "id": paso.id,
                "nombre": paso.nombre,
                "estado": paso.estado,
                "agente": paso.agente,
                "accion": paso.accion[:50],
                "error": paso.error,
                "tarea_id": paso.tarea_id
            })
        
        return ResultadoTarea(
            exito=True,
            datos={
                "workflow": workflow.nombre,
                "descripcion": workflow.descripcion,
                "estado": workflow.estado.value,
                "ejecuciones": workflow.ejecuciones,
                "ultima_ejecucion": workflow.ejecutado.isoformat() if workflow.ejecutado else None,
                "programado": workflow.schedule,
                "pasos": pasos_info,
                "total_pasos": len(pasos_info)
            }
        )
    
    async def _cancelar_workflow(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Cancelar un workflow en ejecución"""
        nombre = parametros.get("nombre") or self._extraer_nombre(desc)
        
        if not nombre:
            return ResultadoTarea(exito=False, error="Especifica qué workflow cancelar")
        
        workflow = None
        for wf in self.workflows.values():
            if wf.nombre == nombre:
                workflow = wf
                break
        
        if not workflow:
            return ResultadoTarea(exito=False, error=f"Workflow '{nombre}' no encontrado")
        
        if workflow.estado != WorkflowStatus.EJECUTANDO:
            return ResultadoTarea(
                exito=False,
                error=f"Workflow '{nombre}' no está en ejecución (estado: {workflow.estado.value})"
            )
        
        workflow.estado = WorkflowStatus.CANCELADO
        
        # Cancelar tareas pendientes
        for paso in workflow.pasos:
            if paso.estado == "ejecutando" and paso.tarea_id:
                self.supervisor.cancel_task(paso.tarea_id, "Workflow cancelado por usuario")
        
        return ResultadoTarea(
            exito=True,
            datos={"nombre": nombre, "mensaje": f"Workflow '{nombre}' cancelado"}
        )
    
    # ============================================================
    # PERSISTENCIA
    # ============================================================
    
    def _guardar_workflow(self, workflow: Workflow):
        """Guardar workflow en disco"""
        archivo = self.workflows_dir / f"{workflow.id}.json"
        datos = {
            "id": workflow.id,
            "nombre": workflow.nombre,
            "descripcion": workflow.descripcion,
            "pasos": [
                {
                    "id": p.id,
                    "nombre": p.nombre,
                    "agente": p.agente,
                    "accion": p.accion,
                    "parametros": p.parametros,
                    "dependencias": p.dependencias,
                    "condicion": p.condicion,
                    "on_failure": p.on_failure,
                    "timeout": p.timeout,
                    "max_retries": p.max_retries
                }
                for p in workflow.pasos
            ],
            "trigger": workflow.trigger.value,
            "schedule": workflow.schedule,
            "variables": workflow.variables,
            "notificar_resultado": workflow.notificar_resultado,
            "notificar_canal": workflow.notificar_canal,
            "creado": workflow.creado.isoformat()
        }
        
        with open(archivo, 'w') as f:
            json.dump(datos, f, indent=2, ensure_ascii=False)
    
    def _cargar_workflows(self):
        """Cargar workflows desde disco"""
        for archivo in self.workflows_dir.glob("*.json"):
            try:
                with open(archivo, 'r') as f:
                    datos = json.load(f)
                
                pasos = [
                    WorkflowStep(
                        id=p["id"],
                        nombre=p["nombre"],
                        agente=p["agente"],
                        accion=p["accion"],
                        parametros=p.get("parametros", {}),
                        dependencias=p.get("dependencias", []),
                        condicion=p.get("condicion"),
                        on_failure=p.get("on_failure", "stop"),
                        timeout=p.get("timeout", 60),
                        max_retries=p.get("max_retries", 3)
                    )
                    for p in datos.get("pasos", [])
                ]
                
                workflow = Workflow(
                    id=datos["id"],
                    nombre=datos["nombre"],
                    descripcion=datos.get("descripcion", ""),
                    pasos=pasos,
                    trigger=WorkflowTrigger(datos.get("trigger", "manual")),
                    schedule=datos.get("schedule"),
                    variables=datos.get("variables", {}),
                    notificar_resultado=datos.get("notificar_resultado", True),
                    notificar_canal=datos.get("notificar_canal", "telegram"),
                    creado=datetime.fromisoformat(datos.get("creado", datetime.now().isoformat()))
                )
                
                self.workflows[workflow.id] = workflow
                
            except Exception as e:
                self.logger.error(f"Error cargando workflow {archivo}: {e}")
    
    def _eliminar_archivo_workflow(self, workflow_id: str):
        """Eliminar archivo de workflow"""
        archivo = self.workflows_dir / f"{workflow_id}.json"
        if archivo.exists():
            archivo.unlink()
    
    def _iniciar_scheduler(self):
        """Iniciar scheduler para workflows programados"""
        def scheduler_loop():
            while True:
                try:
                    for workflow in self.workflows.values():
                        if workflow.trigger == WorkflowTrigger.PROGRAMADO and workflow.schedule:
                            # Verificar si debe ejecutarse
                            if self._debe_ejecutar(workflow):
                                self._ejecutar_workflow_sync(workflow)
                    time.sleep(60)  # verificar cada minuto
                except Exception as e:
                    self.logger.error(f"Error en scheduler: {e}")
        
        thread = threading.Thread(target=scheduler_loop, daemon=True)
        thread.start()
    
    def _debe_ejecutar(self, workflow: Workflow) -> bool:
        """Verificar si un workflow debe ejecutarse según su schedule"""
        if not workflow.schedule:
            return False
        
        # Simple implementación - se puede mejorar con croniter
        ahora = datetime.now()
        
        if workflow.schedule == "0 * * * *":  # cada hora
            return ahora.minute == 0 and (not workflow.ejecutado or (ahora - workflow.ejecutado).seconds >= 3600)
        
        elif workflow.schedule == "0 0 * * *":  # cada día
            return ahora.hour == 0 and ahora.minute == 0 and (not workflow.ejecutado or (ahora - workflow.ejecutado).days >= 1)
        
        elif workflow.schedule == "*/5 * * * *":  # cada 5 minutos
            return ahora.minute % 5 == 0 and (not workflow.ejecutado or (ahora - workflow.ejecutado).seconds >= 300)
        
        return False


# ============================================================
# Factory Function
# ============================================================

def crear_agente_workflows(supervisor: Supervisor, config: Config) -> AgenteWorkflows:
    """Crea instancia del agente de workflows"""
    return AgenteWorkflows(supervisor, config)
