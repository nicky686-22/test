#!/usr/bin/env python3
"""
Agente Monitor - Monitoreo de recursos del sistema en tiempo real
Multiplataforma (Windows/Linux/macOS)
Capacidades: CPU, memoria, disco, red, procesos, alertas, histórico
"""

import os
import sys
import subprocess
import platform
import time
import threading
import json
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from pathlib import Path
from collections import deque

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

from src.core.agente import Agente, TipoAgente, ResultadoTarea
from src.core.supervisor import Supervisor
from src.core.config import Config

# Importar psutil si está disponible
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


class AgenteMonitor(Agente):
    """
    Agente de monitoreo multiplataforma.
    Capacidades: CPU, memoria, disco, red, procesos, alertas, histórico
    """
    
    def __init__(self, supervisor: Supervisor, config: Config):
        super().__init__(
            id_agente="monitor",
            nombre="Agente Monitor",
            tipo=TipoAgente.MONITOR,
            supervisor=supervisor,
            version="2.0.0"
        )
        self.config = config
        self.sistema = platform.system().lower()
        
        # Historial de métricas
        self.historial = {
            "cpu": deque(maxlen=3600),      # 1 hora (cada segundo)
            "memoria": deque(maxlen=3600),
            "disco": deque(maxlen=3600),
            "red": deque(maxlen=3600)
        }
        
        # Umbrales de alerta
        self.umbrales = {
            "cpu": 80,           # % de CPU
            "memoria": 85,       # % de memoria
            "disco": 90,         # % de disco
            "red": 1000000       # bytes/segundo
        }
        
        # Estado de monitoreo
        self.monitoreando = False
        self.hilo_monitoreo = None
        self.alertas = deque(maxlen=100)
        
        # Verificar psutil
        self.psutil_disponible = PSUTIL_AVAILABLE
        if not self.psutil_disponible:
            self.logger.warning("psutil no instalado. Instalar con: pip install psutil")
        
        self._registrar_capacidades()
        self.logger.info(f"Agente Monitor iniciado. SO: {self.sistema}")
    
    def _registrar_capacidades(self):
        """Registrar todas las capacidades"""
        
        # Monitoreo básico
        self.registrar_capacidad("cpu", "Uso de CPU en tiempo real")
        self.registrar_capacidad("memoria", "Uso de memoria RAM")
        self.registrar_capacidad("disco", "Uso de disco")
        self.registrar_capacidad("red", "Tráfico de red")
        self.registrar_capacidad("procesos", "Procesos en ejecución")
        
        # Monitoreo continuo
        self.registrar_capacidad("monitorear", "Iniciar monitoreo continuo")
        self.registrar_capacidad("detener_monitoreo", "Detener monitoreo continuo")
        self.registrar_capacidad("estado_monitor", "Estado del monitor")
        
        # Histórico y alertas
        self.registrar_capacidad("historial", "Ver histórico de métricas")
        self.registrar_capacidad("alertas", "Ver alertas generadas")
        self.registrar_capacidad("umbrales", "Configurar umbrales de alerta")
        
        # Reportes
        self.registrar_capacidad("reporte", "Generar reporte de estado")
        self.registrar_capacidad("top", "Procesos que más consumen")
        
        # Sistema
        self.registrar_capacidad("uptime", "Tiempo activo del sistema")
        self.registrar_capacidad("temperatura", "Temperatura del sistema")
        self.registrar_capacidad("bateria", "Estado de la batería")
    
    async def ejecutar(self, tarea: Dict[str, Any]) -> ResultadoTarea:
        """Ejecuta tarea según tipo"""
        tipo = tarea.get("tipo", "")
        desc = tarea.get("descripcion", "").lower()
        parametros = tarea.get("parametros", {})
        
        # Monitoreo básico
        if "cpu" in tipo or "cpu" in desc:
            return await self._cpu()
        elif "memoria" in tipo or "ram" in desc:
            return await self._memoria()
        elif "disco" in tipo or "espacio" in desc:
            return await self._disco()
        elif "red" in tipo or "tráfico" in desc:
            return await self._red()
        elif "procesos" in tipo:
            return await self._procesos(desc, parametros)
        
        # Monitoreo continuo
        elif "monitorear" in tipo or "iniciar monitoreo" in desc:
            return await self._iniciar_monitoreo(parametros)
        elif "detener_monitoreo" in tipo:
            return await self._detener_monitoreo()
        elif "estado_monitor" in tipo:
            return await self._estado_monitor()
        
        # Histórico y alertas
        elif "historial" in tipo:
            return await self._historial(parametros)
        elif "alertas" in tipo:
            return await self._alertas()
        elif "umbrales" in tipo:
            return await self._umbrales(desc, parametros)
        
        # Reportes
        elif "reporte" in tipo:
            return await self._reporte()
        elif "top" in tipo:
            return await self._top()
        
        # Sistema
        elif "uptime" in tipo or "tiempo activo" in desc:
            return await self._uptime()
        elif "temperatura" in tipo:
            return await self._temperatura()
        elif "bateria" in tipo:
            return await self._bateria()
        
        else:
            return ResultadoTarea(exito=False, error=f"No sé cómo manejar: {tipo}")
    
    # ============================================================
    # MONITOREO BÁSICO
    # ============================================================
    
    async def _cpu(self) -> ResultadoTarea:
        """Obtener uso de CPU"""
        if self.psutil_disponible:
            import psutil
            datos = {
                "porcentaje": psutil.cpu_percent(interval=1),
                "por_nucleo": psutil.cpu_percent(interval=1, percpu=True),
                "nucleos_fisicos": psutil.cpu_count(logical=False),
                "nucleos_logicos": psutil.cpu_count(logical=True),
                "frecuencia": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None,
                "tiempo": datetime.now().isoformat()
            }
            
            # Guardar en historial
            self._guardar_historico("cpu", datos["porcentaje"])
            
            return ResultadoTarea(exito=True, datos=datos)
        
        # Fallback con comandos
        if self.sistema == "windows":
            r = self._ejecutar("wmic cpu get loadpercentage")
            porcentaje = re.search(r'(\d+)', r["salida"])
            datos = {"porcentaje": int(porcentaje.group(1)) if porcentaje else 0}
        else:
            r = self._ejecutar("top -bn1 | grep 'Cpu(s)'")
            match = re.search(r'(\d+\.\d+)\s*id', r["salida"])
            if match:
                idle = float(match.group(1))
                datos = {"porcentaje": 100 - idle}
            else:
                datos = {"porcentaje": 0}
        
        self._guardar_historico("cpu", datos["porcentaje"])
        return ResultadoTarea(exito=True, datos=datos)
    
    async def _memoria(self) -> ResultadoTarea:
        """Obtener uso de memoria"""
        if self.psutil_disponible:
            import psutil
            mem = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            datos = {
                "total": mem.total,
                "total_gb": round(mem.total / (1024**3), 2),
                "disponible": mem.available,
                "disponible_gb": round(mem.available / (1024**3), 2),
                "usado": mem.used,
                "usado_gb": round(mem.used / (1024**3), 2),
                "porcentaje": mem.percent,
                "swap_total": swap.total,
                "swap_usado": swap.used,
                "swap_porcentaje": swap.percent
            }
            
            self._guardar_historico("memoria", datos["porcentaje"])
            return ResultadoTarea(exito=True, datos=datos)
        
        # Fallback con comandos
        if self.sistema == "windows":
            r = self._ejecutar("wmic OS get TotalVisibleMemorySize,FreePhysicalMemory")
            datos = {"salida": r["salida"]}
        else:
            r = self._ejecutar("free -h")
            datos = {"salida": r["salida"]}
        
        return ResultadoTarea(exito=True, datos=datos)
    
    async def _disco(self) -> ResultadoTarea:
        """Obtener uso de disco"""
        if self.psutil_disponible:
            import psutil
            particiones = []
            for part in psutil.disk_partitions():
                try:
                    uso = psutil.disk_usage(part.mountpoint)
                    particiones.append({
                        "dispositivo": part.device,
                        "punto_montaje": part.mountpoint,
                        "total_gb": round(uso.total / (1024**3), 2),
                        "usado_gb": round(uso.used / (1024**3), 2),
                        "libre_gb": round(uso.free / (1024**3), 2),
                        "porcentaje": uso.percent
                    })
                    # Guardar en historial
                    self._guardar_historico("disco", uso.percent)
                except:
                    pass
            
            return ResultadoTarea(exito=True, datos={"particiones": particiones})
        
        # Fallback
        r = self._ejecutar("df -h" if self.sistema != "windows" else "wmic logicaldisk get size,freespace,caption")
        return ResultadoTarea(exito=r["exito"], datos={"disco": r["salida"]})
    
    async def _red(self) -> ResultadoTarea:
        """Obtener tráfico de red"""
        if self.psutil_disponible:
            import psutil
            net = psutil.net_io_counters()
            datos = {
                "bytes_enviados": net.bytes_sent,
                "bytes_recibidos": net.bytes_recv,
                "paquetes_enviados": net.packets_sent,
                "paquetes_recibidos": net.packets_recv,
                "err_in": net.errin,
                "err_out": net.errout
            }
            
            self._guardar_historico("red", net.bytes_recv)
            return ResultadoTarea(exito=True, datos=datos)
        
        # Fallback
        if self.sistema == "windows":
            r = self._ejecutar("netstat -e")
        else:
            r = self._ejecutar("ifconfig | grep -i 'RX bytes'")
        
        return ResultadoTarea(exito=r["exito"], datos={"red": r["salida"]})
    
    async def _procesos(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Listar procesos"""
        filtro = parametros.get("filtro")
        limite = parametros.get("limite", 20)
        
        if self.psutil_disponible:
            import psutil
            procesos = []
            for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status', 'create_time']):
                try:
                    info = p.info
                    if filtro:
                        if filtro.lower() in info['name'].lower():
                            procesos.append(info)
                    else:
                        procesos.append(info)
                except:
                    pass
            
            # Ordenar por CPU
            procesos.sort(key=lambda x: x.get('cpu_percent', 0), reverse=True)
            
            return ResultadoTarea(
                exito=True,
                datos={"procesos": procesos[:limite], "total": len(procesos)}
            )
        
        # Fallback
        cmd = "ps aux" if self.sistema != "windows" else "tasklist"
        if filtro:
            cmd += f" | grep -i {filtro}" if self.sistema != "windows" else f" | findstr /i {filtro}"
        
        r = self._ejecutar(cmd)
        return ResultadoTarea(exito=r["exito"], datos={"procesos": r["salida"]})
    
    # ============================================================
    # MONITOREO CONTINUO
    # ============================================================
    
    async def _iniciar_monitoreo(self, parametros: Dict) -> ResultadoTarea:
        """Iniciar monitoreo continuo"""
        if self.monitoreando:
            return ResultadoTarea(exito=False, error="Monitoreo ya está activo")
        
        intervalo = parametros.get("intervalo", 5)  # segundos
        self.monitoreando = True
        self.hilo_monitoreo = threading.Thread(target=self._bucle_monitoreo, args=(intervalo,), daemon=True)
        self.hilo_monitoreo.start()
        
        return ResultadoTarea(
            exito=True,
            datos={"estado": "monitoreando", "intervalo": intervalo}
        )
    
    async def _detener_monitoreo(self) -> ResultadoTarea:
        """Detener monitoreo continuo"""
        self.monitoreando = False
        if self.hilo_monitoreo:
            self.hilo_monitoreo.join(timeout=2)
        
        return ResultadoTarea(exito=True, datos={"estado": "detenido"})
    
    async def _estado_monitor(self) -> ResultadoTarea:
        """Estado del monitor"""
        return ResultadoTarea(
            exito=True,
            datos={
                "monitoreando": self.monitoreando,
                "historial_cpu": len(self.historial["cpu"]),
                "historial_memoria": len(self.historial["memoria"]),
                "ultimas_alertas": len(self.alertas)
            }
        )
    
    def _bucle_monitoreo(self, intervalo: int):
        """Bucle de monitoreo continuo (ejecuta en hilo separado)"""
        while self.monitoreando:
            try:
                # Obtener métricas actuales
                if self.psutil_disponible:
                    import psutil
                    cpu = psutil.cpu_percent(interval=1)
                    mem = psutil.virtual_memory().percent
                    
                    # Verificar alertas
                    if cpu > self.umbrales["cpu"]:
                        self._generar_alerta("cpu", f"CPU al {cpu}% (umbral: {self.umbrales['cpu']}%)")
                    
                    if mem > self.umbrales["memoria"]:
                        self._generar_alerta("memoria", f"Memoria al {mem}% (umbral: {self.umbrales['memoria']}%)")
                    
                    # Guardar en historial
                    self._guardar_historico("cpu", cpu)
                    self._guardar_historico("memoria", mem)
                
                time.sleep(intervalo)
            except Exception as e:
                self.logger.error(f"Error en monitoreo: {e}")
    
    # ============================================================
    # HISTÓRICO Y ALERTAS
    # ============================================================
    
    def _guardar_historico(self, tipo: str, valor: float):
        """Guardar métrica en historial"""
        self.historial[tipo].append({
            "valor": valor,
            "timestamp": datetime.now().isoformat()
        })
    
    def _generar_alerta(self, tipo: str, mensaje: str):
        """Generar una alerta"""
        alerta = {
            "tipo": tipo,
            "mensaje": mensaje,
            "timestamp": datetime.now().isoformat()
        }
        self.alertas.append(alerta)
        self.logger.warning(f"⚠️ ALERTA: {mensaje}")
    
    async def _historial(self, parametros: Dict) -> ResultadoTarea:
        """Ver histórico de métricas"""
        tipo = parametros.get("tipo", "cpu")
        limite = parametros.get("limite", 100)
        
        if tipo not in self.historial:
            return ResultadoTarea(exito=False, error=f"Tipo no válido: {tipo}")
        
        historico = list(self.historial[tipo])[-limite:]
        
        return ResultadoTarea(
            exito=True,
            datos={
                "tipo": tipo,
                "datos": historico,
                "total": len(historico)
            }
        )
    
    async def _alertas(self) -> ResultadoTarea:
        """Ver alertas generadas"""
        return ResultadoTarea(
            exito=True,
            datos={"alertas": list(self.alertas)}
        )
    
    async def _umbrales(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Configurar o ver umbrales de alerta"""
        if parametros:
            # Configurar umbrales
            for key in ["cpu", "memoria", "disco", "red"]:
                if key in parametros:
                    self.umbrales[key] = parametros[key]
            
            return ResultadoTarea(
                exito=True,
                datos={"umbrales": self.umbrales, "mensaje": "Umbrales actualizados"}
            )
        
        # Ver umbrales actuales
        return ResultadoTarea(exito=True, datos={"umbrales": self.umbrales})
    
    # ============================================================
    # REPORTES
    # ============================================================
    
    async def _reporte(self) -> ResultadoTarea:
        """Generar reporte completo del sistema"""
        if not self.psutil_disponible:
            return ResultadoTarea(exito=False, error="psutil requerido para reporte completo")
        
        import psutil
        
        # Recopilar todas las métricas
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        net = psutil.net_io_counters()
        
        reporte = {
            "timestamp": datetime.now().isoformat(),
            "sistema": platform.system(),
            "hostname": platform.node(),
            "cpu": {
                "porcentaje": cpu,
                "nucleos": psutil.cpu_count(),
                "frecuencia": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None
            },
            "memoria": {
                "total_gb": round(mem.total / (1024**3), 2),
                "usado_gb": round(mem.used / (1024**3), 2),
                "libre_gb": round(mem.free / (1024**3), 2),
                "porcentaje": mem.percent
            },
            "disco": {
                "total_gb": round(disk.total / (1024**3), 2),
                "usado_gb": round(disk.used / (1024**3), 2),
                "libre_gb": round(disk.free / (1024**3), 2),
                "porcentaje": disk.percent
            },
            "red": {
                "bytes_enviados": net.bytes_sent,
                "bytes_recibidos": net.bytes_recv,
                "mb_enviados": round(net.bytes_sent / (1024**2), 2),
                "mb_recibidos": round(net.bytes_recv / (1024**2), 2)
            },
            "alertas_activas": len([a for a in self.alertas if "alerta" in a])
        }
        
        return ResultadoTarea(exito=True, datos={"reporte": reporte})
    
    async def _top(self) -> ResultadoTarea:
        """Procesos que más consumen"""
        if self.psutil_disponible:
            import psutil
            procesos = []
            for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    procesos.append(p.info)
                except:
                    pass
            
            # Top por CPU
            cpu_top = sorted(procesos, key=lambda x: x.get('cpu_percent', 0), reverse=True)[:10]
            # Top por memoria
            mem_top = sorted(procesos, key=lambda x: x.get('memory_percent', 0), reverse=True)[:10]
            
            return ResultadoTarea(
                exito=True,
                datos={
                    "top_cpu": cpu_top,
                    "top_memoria": mem_top
                }
            )
        
        # Fallback
        r = self._ejecutar("ps aux --sort=-%cpu | head -10" if self.sistema != "windows" else "tasklist")
        return ResultadoTarea(exito=r["exito"], datos={"top": r["salida"]})
    
    # ============================================================
    # SISTEMA
    # ============================================================
    
    async def _uptime(self) -> ResultadoTarea:
        """Tiempo activo del sistema"""
        if self.psutil_disponible:
            import psutil
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            ahora = datetime.now()
            uptime = ahora - boot_time
            
            return ResultadoTarea(
                exito=True,
                datos={
                    "boot_time": boot_time.isoformat(),
                    "uptime": str(uptime).split('.')[0],
                    "dias": uptime.days,
                    "horas": uptime.seconds // 3600,
                    "minutos": (uptime.seconds // 60) % 60
                }
            )
        
        # Fallback
        r = self._ejecutar("uptime" if self.sistema != "windows" else "systeminfo | findstr 'System Boot Time'")
        return ResultadoTarea(exito=r["exito"], datos={"uptime": r["salida"]})
    
    async def _temperatura(self) -> ResultadoTarea:
        """Temperatura del sistema"""
        if self.psutil_disponible:
            import psutil
            try:
                temps = psutil.sensors_temperatures()
                if temps:
                    return ResultadoTarea(
                        exito=True,
                        datos={"temperaturas": {k: [t._asdict() for t in v] for k, v in temps.items()}}
                    )
            except:
                pass
        
        # Fallback Linux
        if self.sistema == "linux":
            r = self._ejecutar("sensors")
            return ResultadoTarea(exito=r["exito"], datos={"temperatura": r["salida"]})
        
        return ResultadoTarea(exito=False, error="Temperatura no disponible en este sistema")
    
    async def _bateria(self) -> ResultadoTarea:
        """Estado de la batería"""
        if self.psutil_disponible:
            import psutil
            try:
                battery = psutil.sensors_battery()
                if battery:
                    return ResultadoTarea(
                        exito=True,
                        datos={
                            "porcentaje": battery.percent,
                            "cargando": battery.power_plugged,
                            "tiempo_restante": battery.secsleft if battery.secsleft > 0 else None
                        }
                    )
            except:
                pass
        
        return ResultadoTarea(exito=False, error="Batería no disponible o es un equipo de escritorio")
    
    # ============================================================
    # UTILIDADES
    # ============================================================
    
    def _ejecutar(self, comando: str) -> Dict:
        """Ejecuta comando y devuelve resultado"""
        try:
            r = subprocess.run(comando, shell=True, capture_output=True, text=True, timeout=30)
            return {"exito": r.returncode == 0, "salida": r.stdout, "error": r.stderr}
        except Exception as e:
            return {"exito": False, "error": str(e)}


# ============================================================
# Factory Function
# ============================================================

def crear_agente_monitor(supervisor: Supervisor, config: Config) -> AgenteMonitor:
    """Crea instancia del agente de monitoreo"""
    return AgenteMonitor(supervisor, config)
