
#!/usr/bin/env python3
"""
Agente Automatización - Tareas automáticas, schedulers, workflows
Multiplataforma (Windows/Linux/macOS)
Capacidades: tareas programadas, workflows, recordatorios, backups automáticos
"""

import os
import sys
import subprocess
import platform
import time
import threading
import json
import schedule
import re
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from pathlib import Path
from queue import Queue
import asyncio

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

from src.core.agente import Agente, TipoAgente, ResultadoTarea
from src.core.supervisor import Supervisor
from src.core.config import Config


class AgenteAutomatizacion(Agente):
    """
    Agente de automatización multiplataforma.
    Capacidades: tareas programadas, workflows, recordatorios, backups, monitoreo
    """
    
    def __init__(self, supervisor: Supervisor, config: Config):
        super().__init__(
            id_agente="automatizacion",
            nombre="Agente Automatización",
            tipo=TipoAgente.AUTOMATIZACION,
            supervisor=supervisor,
            version="2.0.0"
        )
        self.config = config
        self.sistema = platform.system().lower()
        
        # Tareas programadas
        self.tareas = {}
        self.tareas_programadas = {}
        self.hilo_scheduler = None
        self.scheduler_corriendo = False
        
        # Workflows
        self.workflows = {}
        
        # Cola de tareas
        self.cola_tareas = Queue()
        
        # Historial
        self.historial = []
        
        # Directorio de trabajo
        self.work_dir = Path.cwd() / "automatizacion"
        self.work_dir.mkdir(exist_ok=True)
        
        self._registrar_capacidades()
        self._cargar_tareas()
        self.logger.info(f"Agente Automatización iniciado. Directorio: {self.work_dir}")
    
    def _registrar_capacidades(self):
        """Registrar todas las capacidades"""
        
        # Tareas programadas
        self.registrar_capacidad("programar", "Programar una tarea para ejecutar después")
        self.registrar_capacidad("cron", "Programar tarea recurrente (cron style)")
        self.registrar_capacidad("tareas", "Listar tareas programadas")
        self.registrar_capacidad("cancelar", "Cancelar una tarea programada")
        
        # Workflows
        self.registrar_capacidad("workflow", "Crear un workflow de múltiples pasos")
        self.registrar_capacidad("ejecutar_workflow", "Ejecutar un workflow")
        self.registrar_capacidad("workflows", "Listar workflows disponibles")
        
        # Recordatorios
        self.registrar_capacidad("recordatorio", "Crear un recordatorio")
        self.registrar_capacidad("recordatorios", "Listar recordatorios activos")
        
        # Backups
        self.registrar_capacidad("backup", "Crear backup de archivos/carpetas")
        self.registrar_capacidad("restaurar", "Restaurar desde backup")
        
        # Monitoreo
        self.registrar_capacidad("monitorear_carpeta", "Monitorear cambios en carpeta")
        self.registrar_capacidad("monitorear_comando", "Monitorear salida de comando")
        
        # Limpieza
        self.registrar_capacidad("limpieza", "Limpiar archivos antiguos automáticamente")
    
    async def ejecutar(self, tarea: Dict[str, Any]) -> ResultadoTarea:
        """Ejecuta tarea según tipo"""
        tipo = tarea.get("tipo", "")
        desc = tarea.get("descripcion", "").lower()
        parametros = tarea.get("parametros", {})
        
        # Tareas programadas
        if "programar" in tipo or "delay" in desc:
            return await self._programar(desc, parametros)
        elif "cron" in tipo or "cada" in desc:
            return await self._cron(desc, parametros)
        elif "tareas" in tipo or "listar tareas" in desc:
            return await self._listar_tareas()
        elif "cancelar" in tipo:
            return await self._cancelar_tarea(desc, parametros)
        
        # Workflows
        elif "workflow" in tipo and "crear" in tipo:
            return await self._crear_workflow(desc, parametros)
        elif "ejecutar_workflow" in tipo or "ejecutar workflow" in desc:
            return await self._ejecutar_workflow(desc, parametros)
        elif "workflows" in tipo:
            return await self._listar_workflows()
        
        # Recordatorios
        elif "recordatorio" in tipo:
            return await self._crear_recordatorio(desc, parametros)
        elif "recordatorios" in tipo:
            return await self._listar_recordatorios()
        
        # Backups
        elif "backup" in tipo:
            return await self._crear_backup(desc, parametros)
        elif "restaurar" in tipo:
            return await self._restaurar_backup(desc, parametros)
        
        # Monitoreo
        elif "monitorear_carpeta" in tipo:
            return await self._monitorear_carpeta(desc, parametros)
        elif "monitorear_comando" in tipo:
            return await self._monitorear_comando(desc, parametros)
        
        # Limpieza
        elif "limpieza" in tipo or "limpiar" in desc:
            return await self._limpieza(desc, parametros)
        
        else:
            return ResultadoTarea(exito=False, error=f"No sé cómo manejar: {tipo}")
    
    # ============================================================
    # TAREAS PROGRAMADAS
    # ============================================================
    
    async def _programar(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Programar una tarea para ejecutar después de X segundos/minutos/horas"""
        tiempo = parametros.get("tiempo")
        unidad = parametros.get("unidad", "segundos")
        comando = parametros.get("comando")
        
        if not comando:
            # Extraer comando de descripción
            match = re.search(r"(?:programar|delay|esperar)\s+\d+\s*\w+\s+(.+)", desc)
            if match:
                comando = match.group(1)
            else:
                return ResultadoTarea(exito=False, error="Especifica qué ejecutar")
        
        if not tiempo:
            # Extraer tiempo de descripción
            match = re.search(r"(\d+)\s*(segundos?|minutos?|horas?)", desc)
            if match:
                tiempo = int(match.group(1))
                unidad = match.group(2)
            else:
                return ResultadoTarea(exito=False, error="Especifica el tiempo")
        
        # Convertir a segundos
        if "minuto" in unidad:
            segundos = tiempo * 60
        elif "hora" in unidad:
            segundos = tiempo * 3600
        else:
            segundos = tiempo
        
        tarea_id = f"tarea_{len(self.tareas) + 1}"
        ejecucion_en = datetime.now() + timedelta(seconds=segundos)
        
        self.tareas[tarea_id] = {
            "id": tarea_id,
            "comando": comando,
            "ejecucion_en": ejecucion_en.isoformat(),
            "estado": "programada",
            "tipo": "one_shot"
        }
        
        # Programar en thread separado
        def ejecutar():
            time.sleep(segundos)
            resultado = self._ejecutar_comando(comando)
            self.tareas[tarea_id]["estado"] = "completada"
            self.tareas[tarea_id]["resultado"] = resultado
            self._guardar_historial(tarea_id, comando, resultado)
        
        thread = threading.Thread(target=ejecutar, daemon=True)
        thread.start()
        
        return ResultadoTarea(
            exito=True,
            datos={
                "tarea_id": tarea_id,
                "comando": comando,
                "ejecucion_en": ejecucion_en.isoformat(),
                "mensaje": f"Tarea programada para ejecutar en {segundos} segundos"
            }
        )
    
    async def _cron(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Programar tarea recurrente estilo cron"""
        intervalo = parametros.get("intervalo")
        comando = parametros.get("comando")
        
        if not comando:
            match = re.search(r"(?:cron|cada)\s+[^\s]+\s+(.+)", desc)
            if match:
                comando = match.group(1)
        
        if not comando:
            return ResultadoTarea(exito=False, error="Especifica qué ejecutar")
        
        if not intervalo:
            if "segundo" in desc:
                intervalo = "segundos"
            elif "minuto" in desc:
                intervalo = "minutos"
            elif "hora" in desc:
                intervalo = "horas"
            elif "dia" in desc:
                intervalo = "dias"
            else:
                intervalo = "minutos"
        
        tarea_id = f"cron_{len(self.tareas_programadas) + 1}"
        
        # Iniciar scheduler si no está corriendo
        if not self.scheduler_corriendo:
            self._iniciar_scheduler()
        
        # Programar en schedule
        if intervalo == "segundos":
            schedule.every().seconds.do(self._ejecutar_recurrente, tarea_id, comando)
        elif intervalo == "minutos":
            schedule.every().minute.do(self._ejecutar_recurrente, tarea_id, comando)
        elif intervalo == "horas":
            schedule.every().hour.do(self._ejecutar_recurrente, tarea_id, comando)
        elif intervalo == "dias":
            schedule.every().day.do(self._ejecutar_recurrente, tarea_id, comando)
        
        self.tareas_programadas[tarea_id] = {
            "id": tarea_id,
            "comando": comando,
            "intervalo": intervalo,
            "estado": "activa",
            "ejecuciones": 0
        }
        
        return ResultadoTarea(
            exito=True,
            datos={
                "tarea_id": tarea_id,
                "comando": comando,
                "intervalo": intervalo,
                "mensaje": f"Tarea recurrente programada cada {intervalo}"
            }
        )
    
    async def _listar_tareas(self) -> ResultadoTarea:
        """Listar tareas programadas"""
        return ResultadoTarea(
            exito=True,
            datos={
                "tareas_unicas": list(self.tareas.values()),
                "tareas_recurrentes": list(self.tareas_programadas.values()),
                "total": len(self.tareas) + len(self.tareas_programadas)
            }
        )
    
    async def _cancelar_tarea(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Cancelar una tarea programada"""
        tarea_id = parametros.get("tarea_id")
        if not tarea_id:
            match = re.search(r"tarea[_\s]?(\d+)", desc)
            if match:
                tarea_id = match.group(1)
        
        if not tarea_id:
            return ResultadoTarea(exito=False, error="Especifica el ID de la tarea")
        
        if tarea_id in self.tareas:
            del self.tareas[tarea_id]
            return ResultadoTarea(exito=True, datos={"mensaje": f"Tarea {tarea_id} cancelada"})
        
        elif tarea_id in self.tareas_programadas:
            del self.tareas_programadas[tarea_id]
            return ResultadoTarea(exito=True, datos={"mensaje": f"Tarea recurrente {tarea_id} cancelada"})
        
        else:
            return ResultadoTarea(exito=False, error=f"Tarea {tarea_id} no encontrada")
    
    def _iniciar_scheduler(self):
        """Iniciar el scheduler en segundo plano"""
        def ejecutar_scheduler():
            while self.scheduler_corriendo:
                schedule.run_pending()
                time.sleep(1)
        
        self.scheduler_corriendo = True
        self.hilo_scheduler = threading.Thread(target=ejecutar_scheduler, daemon=True)
        self.hilo_scheduler.start()
    
    def _ejecutar_recurrente(self, tarea_id: str, comando: str):
        """Ejecutar tarea recurrente"""
        try:
            resultado = self._ejecutar_comando(comando)
            if tarea_id in self.tareas_programadas:
                self.tareas_programadas[tarea_id]["ejecuciones"] += 1
                self.tareas_programadas[tarea_id]["ultima"] = datetime.now().isoformat()
            self._guardar_historial(tarea_id, comando, resultado)
        except Exception as e:
            self.logger.error(f"Error en tarea recurrente {tarea_id}: {e}")
    
    # ============================================================
    # WORKFLOWS
    # ============================================================
    
    async def _crear_workflow(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Crear un workflow con múltiples pasos"""
        nombre = parametros.get("nombre")
        pasos = parametros.get("pasos", [])
        
        if not nombre:
            match = re.search(r"workflow\s+([a-zA-Z0-9_]+)", desc)
            nombre = match.group(1) if match else f"workflow_{len(self.workflows) + 1}"
        
        if not pasos:
            # Extraer pasos de la descripción
            pasos_texto = desc.split("pasos:")[-1] if "pasos:" in desc else desc
            pasos = [p.strip() for p in pasos_texto.split(",") if p.strip()]
        
        self.workflows[nombre] = {
            "nombre": nombre,
            "pasos": pasos,
            "creado": datetime.now().isoformat(),
            "ejecuciones": 0
        }
        
        # Guardar workflow
        self._guardar_workflow(nombre)
        
        return ResultadoTarea(
            exito=True,
            datos={
                "workflow": nombre,
                "pasos": pasos,
                "mensaje": f"Workflow '{nombre}' creado con {len(pasos)} pasos"
            }
        )
    
    async def _ejecutar_workflow(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Ejecutar un workflow existente"""
        nombre = parametros.get("nombre")
        
        if not nombre:
            match = re.search(r"workflow\s+([a-zA-Z0-9_]+)", desc)
            nombre = match.group(1) if match else None
        
        if not nombre or nombre not in self.workflows:
            return ResultadoTarea(exito=False, error=f"Workflow '{nombre}' no encontrado")
        
        workflow = self.workflows[nombre]
        resultados = []
        
        for i, paso in enumerate(workflow["pasos"]):
            self.logger.info(f"Ejecutando paso {i+1}/{len(workflow['pasos'])}: {paso}")
            resultado = self._ejecutar_comando(paso)
            resultados.append({
                "paso": i + 1,
                "comando": paso,
                "exito": resultado["exito"],
                "salida": resultado["salida"][:200] if resultado["exito"] else resultado.get("error", "")
            })
            
            if not resultado["exito"]:
                break
        
        workflow["ejecuciones"] += 1
        workflow["ultima_ejecucion"] = datetime.now().isoformat()
        
        return ResultadoTarea(
            exito=True,
            datos={
                "workflow": nombre,
                "pasos_totales": len(workflow["pasos"]),
                "pasos_ejecutados": len(resultados),
                "resultados": resultados
            }
        )
    
    async def _listar_workflows(self) -> ResultadoTarea:
        """Listar workflows disponibles"""
        return ResultadoTarea(
            exito=True,
            datos={"workflows": list(self.workflows.values())}
        )
    
    # ============================================================
    # RECORDATORIOS
    # ============================================================
    
    async def _crear_recordatorio(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Crear un recordatorio"""
        mensaje = parametros.get("mensaje")
        tiempo = parametros.get("tiempo")
        unidad = parametros.get("unidad", "minutos")
        
        if not mensaje:
            match = re.search(r"recordatorio\s+de\s+(.+)", desc)
            if match:
                mensaje = match.group(1)
            else:
                return ResultadoTarea(exito=False, error="Especifica el mensaje del recordatorio")
        
        if not tiempo:
            match = re.search(r"en\s+(\d+)\s*(segundos?|minutos?|horas?)", desc)
            if match:
                tiempo = int(match.group(1))
                unidad = match.group(2)
            else:
                return ResultadoTarea(exito=False, error="Especifica el tiempo")
        
        # Convertir a segundos
        if "minuto" in unidad:
            segundos = tiempo * 60
        elif "hora" in unidad:
            segundos = tiempo * 3600
        else:
            segundos = tiempo
        
        recordatorio_id = f"recordatorio_{len(self.tareas) + 1}"
        
        def ejecutar_recordatorio():
            time.sleep(segundos)
            print(f"\n🔔 RECORDATORIO: {mensaje}")
            self.logger.info(f"Recordatorio: {mensaje}")
        
        thread = threading.Thread(target=ejecutar_recordatorio, daemon=True)
        thread.start()
        
        return ResultadoTarea(
            exito=True,
            datos={
                "id": recordatorio_id,
                "mensaje": mensaje,
                "tiempo": f"{tiempo} {unidad}",
                "mensaje": f"Recordatorio programado para dentro de {tiempo} {unidad}"
            }
        )
    
    async def _listar_recordatorios(self) -> ResultadoTarea:
        """Listar recordatorios activos"""
        recordatorios = [t for t in self.tareas.values() if t.get("tipo") == "recordatorio"]
        return ResultadoTarea(
            exito=True,
            datos={"recordatorios": recordatorios}
        )
    
    # ============================================================
    # BACKUPS
    # ============================================================
    
    async def _crear_backup(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Crear backup de archivos o carpetas"""
        origen = parametros.get("origen")
        destino = parametros.get("destino")
        
        if not origen:
            match = re.search(r"backup\s+de\s+([^\s]+)", desc)
            origen = match.group(1) if match else "."
        
        if not destino:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            destino = self.work_dir / f"backup_{timestamp}.tar.gz"
        
        origen_path = Path(origen)
        destino_path = Path(destino) if isinstance(destino, Path) else Path(destino)
        
        # Crear backup con tar en Linux/macOS o zip en Windows
        if self.sistema == "windows":
            comando = f"powershell Compress-Archive -Path {origen_path} -DestinationPath {destino_path}"
        else:
            comando = f"tar -czf {destino_path} -C {origen_path.parent} {origen_path.name}"
        
        resultado = self._ejecutar_comando(comando)
        
        return ResultadoTarea(
            exito=resultado["exito"],
            datos={
                "origen": str(origen_path),
                "destino": str(destino_path),
                "tamano": destino_path.stat().st_size if destino_path.exists() else 0,
                "salida": resultado["salida"]
            }
        )
    
    async def _restaurar_backup(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Restaurar desde backup"""
        archivo = parametros.get("archivo")
        destino = parametros.get("destino", ".")
        
        if not archivo:
            match = re.search(r"restaurar\s+([^\s]+)", desc)
            archivo = match.group(1) if match else None
        
        if not archivo:
            return ResultadoTarea(exito=False, error="Especifica qué backup restaurar")
        
        archivo_path = Path(archivo)
        destino_path = Path(destino)
        
        if not archivo_path.exists():
            return ResultadoTarea(exito=False, error=f"Backup no encontrado: {archivo}")
        
        if self.sistema == "windows":
            comando = f"powershell Expand-Archive -Path {archivo_path} -DestinationPath {destino_path} -Force"
        else:
            comando = f"tar -xzf {archivo_path} -C {destino_path}"
        
        resultado = self._ejecutar_comando(comando)
        
        return ResultadoTarea(
            exito=resultado["exito"],
            datos={
                "archivo": str(archivo_path),
                "destino": str(destino_path),
                "salida": resultado["salida"]
            }
        )
    
    # ============================================================
    # MONITOREO
    # ============================================================
    
    async def _monitorear_carpeta(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Monitorear cambios en una carpeta"""
        carpeta = parametros.get("carpeta", ".")
        evento = parametros.get("evento", "cualquier")
        callback = parametros.get("callback")
        
        carpeta_path = Path(carpeta)
        if not carpeta_path.exists():
            return ResultadoTarea(exito=False, error=f"Carpeta no existe: {carpeta}")
        
        # Simple monitoreo con polling
        def monitorear():
            archivos_previos = set(carpeta_path.iterdir())
            while True:
                time.sleep(5)
                archivos_actuales = set(carpeta_path.iterdir())
                
                nuevos = archivos_actuales - archivos_previos
                eliminados = archivos_previos - archivos_actuales
                
                if nuevos and evento in ["crear", "cualquier"]:
                    self.logger.info(f"Nuevos archivos en {carpeta}: {[f.name for f in nuevos]}")
                
                if eliminados and evento in ["eliminar", "cualquier"]:
                    self.logger.info(f"Archivos eliminados en {carpeta}: {[f.name for f in eliminados]}")
                
                archivos_previos = archivos_actuales
        
        thread = threading.Thread(target=monitorear, daemon=True)
        thread.start()
        
        return ResultadoTarea(
            exito=True,
            datos={
                "carpeta": str(carpeta_path),
                "evento": evento,
                "estado": "monitoreando"
            }
        )
    
    async def _monitorear_comando(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Monitorear salida de un comando"""
        comando = parametros.get("comando")
        patron = parametros.get("patron")
        
        if not comando:
            match = re.search(r"monitorear\s+(.+)", desc)
            comando = match.group(1) if match else None
        
        if not comando:
            return ResultadoTarea(exito=False, error="Especifica qué comando monitorear")
        
        def monitorear():
            while True:
                resultado = self._ejecutar_comando(comando)
                if patron and patron in resultado["salida"]:
                    self.logger.info(f"Patrón encontrado en {comando}: {patron}")
                time.sleep(10)
        
        thread = threading.Thread(target=monitorear, daemon=True)
        thread.start()
        
        return ResultadoTarea(
            exito=True,
            datos={
                "comando": comando,
                "patron": patron,
                "estado": "monitoreando"
            }
        )
    
    # ============================================================
    # LIMPIEZA
    # ============================================================
    
    async def _limpieza(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Limpiar archivos antiguos automáticamente"""
        carpeta = parametros.get("carpeta", ".")
        dias = parametros.get("dias", 30)
        tipo = parametros.get("tipo", "todos")  # archivos, logs, temporales
        
        carpeta_path = Path(carpeta)
        if not carpeta_path.exists():
            return ResultadoTarea(exito=False, error=f"Carpeta no existe: {carpeta}")
        
        fecha_corte = datetime.now() - timedelta(days=dias)
        eliminados = []
        
        for item in carpeta_path.iterdir():
            if item.is_file():
                mtime = datetime.fromtimestamp(item.stat().st_mtime)
                if mtime < fecha_corte:
                    if tipo == "logs" and item.suffix != ".log":
                        continue
                    if tipo == "temporales" and item.suffix not in [".tmp", ".temp", ".cache"]:
                        continue
                    
                    try:
                        item.unlink()
                        eliminados.append(str(item.name))
                    except:
                        pass
        
        return ResultadoTarea(
            exito=True,
            datos={
                "carpeta": str(carpeta_path),
                "archivos_eliminados": eliminados,
                "total_eliminados": len(eliminados)
            }
        )
    
    # ============================================================
    # UTILIDADES
    # ============================================================
    
    def _ejecutar_comando(self, comando: str) -> Dict:
        """Ejecutar comando y devolver resultado"""
        try:
            r = subprocess.run(comando, shell=True, capture_output=True, text=True, timeout=60)
            return {"exito": r.returncode == 0, "salida": r.stdout, "error": r.stderr}
        except Exception as e:
            return {"exito": False, "error": str(e)}
    
    def _guardar_historial(self, tarea_id: str, comando: str, resultado: Dict):
        """Guardar historial de ejecución"""
        self.historial.append({
            "tarea_id": tarea_id,
            "comando": comando,
            "fecha": datetime.now().isoformat(),
            "exito": resultado.get("exito", False),
            "salida": resultado.get("salida", "")[:500]
        })
        
        # Mantener solo últimos 1000
        if len(self.historial) > 1000:
            self.historial = self.historial[-1000:]
    
    def _guardar_workflow(self, nombre: str):
        """Guardar workflow en disco"""
        archivo = self.work_dir / f"{nombre}.json"
        with open(archivo, "w") as f:
            json.dump(self.workflows[nombre], f, indent=2)
    
    def _cargar_tareas(self):
        """Cargar tareas guardadas"""
        for archivo in self.work_dir.glob("*.json"):
            try:
                with open(archivo, "r") as f:
                    datos = json.load(f)
                    if "nombre" in datos:
                        self.workflows[datos["nombre"]] = datos
            except:
                pass


# ============================================================
# Factory Function
# ============================================================

def crear_agente_automatizacion(supervisor: Supervisor, config: Config) -> AgenteAutomatizacion:
    """Crea instancia del agente de automatización"""
    return AgenteAutomatizacion(supervisor, config)
