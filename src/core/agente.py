
#!/usr/bin/env python3
"""
Clase Base Agente - Núcleo de todos los agentes de SwarmIA
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
from dataclasses import dataclass, field


class TipoAgente(Enum):
    """Tipos de agentes especializados"""
    SUPERVISOR = "supervisor"
    CHAT = "chat"
    SISTEMA = "sistema"
    ARCHIVOS = "archivos"
    RED = "red"
    SEGURIDAD = "seguridad"
    PENTEST = "pentest"
    AGGRESSIVE = "aggressive"
    MONITOR = "monitor"
    AUTOMATIZACION = "automatizacion"
    PAQUETES = "paquetes"


class EstadoAgente(Enum):
    """Estados del ciclo de vida del agente"""
    INICIALIZANDO = "inicializando"
    ACTIVO = "activo"
    OCUPADO = "ocupado"
    PAUSADO = "pausado"
    ERROR = "error"
    DETENIDO = "detenido"


@dataclass
class Capacidad:
    """Define una capacidad que un agente puede ofrecer"""
    nombre: str
    descripcion: str
    parametros: List[str] = field(default_factory=list)
    ejemplos: List[str] = field(default_factory=list)
    requiere_permiso: bool = False
    nivel_riesgo: str = "bajo"


@dataclass
class ResultadoTarea:
    """Estructura estandarizada para resultados de tareas"""
    exito: bool
    datos: Any = None
    error: Optional[str] = None
    tiempo_ejecucion: float = 0.0
    agente_id: Optional[str] = None
    tarea_id: Optional[str] = None
    metadatos: Dict[str, Any] = field(default_factory=dict)


class Agente(ABC):
    """Clase base abstracta para todos los agentes"""
    
    def __init__(
        self,
        id_agente: str,
        nombre: str,
        tipo: TipoAgente,
        supervisor: Any,
        version: str = "1.0.0"
    ):
        self.id = id_agente
        self.nombre = nombre
        self.tipo = tipo
        self.version = version
        self.supervisor = supervisor
        self.estado = EstadoAgente.INICIALIZANDO
        self.capacidades: List[Capacidad] = []
        
        self.estadisticas = {
            "tareas_completadas": 0,
            "tareas_fallidas": 0,
            "tareas_totales": 0,
            "tiempo_total": 0.0,
            "inicio": datetime.now()
        }
        
        self.logger = logging.getLogger(f"swarmia.agentes.{id_agente}")
        self.logger.info(f"Agente {nombre} v{version} inicializado")
    
    def registrar_capacidad(self, nombre: str, descripcion: str, **kwargs):
        """Registra una capacidad del agente"""
        capacidad = Capacidad(nombre=nombre, descripcion=descripcion, **kwargs)
        self.capacidades.append(capacidad)
        self.logger.debug(f"Capacidad registrada: {nombre}")
    
    def puede_manejar(self, intencion: str) -> Optional[Capacidad]:
        """Verifica si puede manejar una intención"""
        for cap in self.capacidades:
            if cap.nombre == intencion or intencion in cap.nombre:
                return cap
        return None
    
    @abstractmethod
    async def ejecutar(self, tarea: Dict[str, Any]) -> ResultadoTarea:
        """Ejecuta una tarea - debe implementarse por cada agente"""
        pass
    
    async def ejecutar_tarea(self, tarea: Dict) -> ResultadoTarea:
        """Wrapper con logging, estadísticas y manejo de errores"""
        inicio = datetime.now()
        self.estado = EstadoAgente.OCUPADO
        tarea_id = tarea.get("id", "unknown")
        
        self.logger.info(f"[{tarea_id}] Ejecutando: {tarea.get('descripcion', '')[:100]}")
        
        try:
            resultado = await self.ejecutar(tarea)
            resultado.tiempo_ejecucion = (datetime.now() - inicio).total_seconds()
            resultado.agente_id = self.id
            resultado.tarea_id = tarea_id
            
            self.estadisticas["tareas_totales"] += 1
            self.estadisticas["tiempo_total"] += resultado.tiempo_ejecucion
            
            if resultado.exito:
                self.estadisticas["tareas_completadas"] += 1
                self.logger.info(f"[{tarea_id}] ✅ Completada en {resultado.tiempo_ejecucion:.2f}s")
            else:
                self.estadisticas["tareas_fallidas"] += 1
                self.logger.error(f"[{tarea_id}] ❌ Fallida: {resultado.error}")
            
            return resultado
            
        except Exception as e:
            self.estadisticas["tareas_fallidas"] += 1
            self.logger.error(f"[{tarea_id}] 💥 Error: {e}")
            return ResultadoTarea(exito=False, error=str(e))
        finally:
            self.estado = EstadoAgente.ACTIVO
    
    def obtener_estado(self) -> Dict[str, Any]:
        """Obtiene el estado actual del agente"""
        tiempo_activo = datetime.now() - self.estadisticas["inicio"]
        
        return {
            "id": self.id,
            "nombre": self.nombre,
            "tipo": self.tipo.value,
            "version": self.version,
            "estado": self.estado.value,
            "capacidades": [c.nombre for c in self.capacidades],
            "estadisticas": {
                "tareas_completadas": self.estadisticas["tareas_completadas"],
                "tareas_fallidas": self.estadisticas["tareas_fallidas"],
                "tareas_totales": self.estadisticas["tareas_totales"],
                "tiempo_promedio": f"{(self.estadisticas['tiempo_total'] / max(1, self.estadisticas['tareas_totales'])):.2f}s",
                "tiempo_activo": str(tiempo_activo).split('.')[0]
            }
        }
