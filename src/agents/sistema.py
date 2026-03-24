#!/usr/bin/env python3
"""
Agente Sistema - Versión Completa Multiplataforma
Capacidades: procesos, servicios, red, hardware, logs, monitorización, etc.
"""

import os
import sys
import subprocess
import platform
import logging
import re
import json
import psutil  # pip install psutil
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

from src.core.agente import Agente, TipoAgente, ResultadoTarea
from src.core.supervisor import Supervisor


class AgenteSistema(Agente):
    """Agente sistema completo - Multiplataforma"""
    
    def __init__(self, supervisor: Supervisor, config: Config):
        super().__init__(
            id_agente="sistema",
            nombre="Agente Sistema",
            tipo=TipoAgente.SISTEMA,
            supervisor=supervisor,
            version="2.0.0"
        )
        self.config = config
        self.sistema = platform.system().lower()
        self._registrar_capacidades()
        
        # Verificar psutil
        try:
            import psutil
            self.psutil_disponible = True
        except ImportError:
            self.psutil_disponible = False
            self.logger.warning("psutil no instalado. Instalar con: pip install psutil")
        
        self.logger.info(f"Agente Sistema iniciado. SO: {self.sistema}")
    
    def _registrar_capacidades(self):
        """Registrar todas las capacidades"""
        
        # Básicas
        self.registrar_capacidad("ejecutar", "Ejecuta cualquier comando")
        self.registrar_capacidad("info_sistema", "Información del sistema")
        self.registrar_capacidad("donde_esta", "Ubicación de un comando")
        
        # Procesos
        self.registrar_capacidad("listar_procesos", "Lista procesos en ejecución")
        self.registrar_capacidad("matar_proceso", "Termina un proceso por PID o nombre")
        self.registrar_capacidad("top_procesos", "Procesos que más consumen CPU/RAM")
        
        # Servicios
        self.registrar_capacidad("listar_servicios", "Lista servicios del sistema")
        self.registrar_capacidad("estado_servicio", "Estado de un servicio")
        self.registrar_capacidad("control_servicio", "Iniciar/detener/reiniciar servicio")
        
        # Red
        self.registrar_capacidad("info_red", "Interfaces de red y direcciones IP")
        self.registrar_capacidad("conexiones", "Conexiones de red activas")
        self.registrar_capacidad("ping", "Prueba de conectividad")
        self.registrar_capacidad("dns", "Resolución DNS")
        self.registrar_capacidad("puertos_abiertos", "Puertos abiertos en el sistema")
        
        # Hardware
        self.registrar_capacidad("cpu", "Información de CPU")
        self.registrar_capacidad("memoria", "Uso de memoria RAM")
        self.registrar_capacidad("disco", "Uso de disco")
        self.registrar_capacidad("hardware", "Información de hardware completo")
        
        # Usuarios
        self.registrar_capacidad("usuarios", "Usuarios del sistema")
        self.registrar_capacidad("sesiones", "Sesiones activas")
        
        # Logs
        self.registrar_capacidad("logs", "Logs del sistema")
        self.registrar_capacidad("errores", "Últimos errores del sistema")
        
        # Paquetes
        self.registrar_capacidad("paquetes", "Paquetes instalados")
        
        # Monitorización
        self.registrar_capacidad("monitor", "Monitoreo en tiempo real")
    
    async def ejecutar(self, tarea: Dict[str, Any]) -> ResultadoTarea:
        """Ejecuta tarea según tipo"""
        tipo = tarea.get("tipo", "")
        desc = tarea.get("descripcion", "").lower()
        
        # ========== PROCESOS ==========
        if "listar_procesos" in tipo or "procesos" in desc:
            return await self._listar_procesos()
        
        elif "matar_proceso" in tipo or "matar" in desc or "kill" in desc:
            return await self._matar_proceso(desc)
        
        elif "top_procesos" in tipo or "top" in desc:
            return await self._top_procesos()
        
        # ========== SERVICIOS ==========
        elif "listar_servicios" in tipo or "servicios" in desc:
            return await self._listar_servicios()
        
        elif "estado_servicio" in tipo:
            return await self._estado_servicio(desc)
        
        elif "control_servicio" in tipo:
            return await self._control_servicio(desc)
        
        # ========== RED ==========
        elif "info_red" in tipo or "ip" in desc or "ifconfig" in desc:
            return await self._info_red()
        
        elif "conexiones" in tipo or "netstat" in desc:
            return await self._conexiones()
        
        elif "ping" in tipo or "ping" in desc:
            return await self._ping(desc)
        
        elif "dns" in tipo or "dns" in desc or "nslookup" in desc:
            return await self._dns(desc)
        
        elif "puertos_abiertos" in tipo:
            return await self._puertos_abiertos()
        
        # ========== HARDWARE ==========
        elif "cpu" in tipo or "cpu" in desc:
            return await self._cpu()
        
        elif "memoria" in tipo or "ram" in desc:
            return await self._memoria()
        
        elif "disco" in tipo or "espacio" in desc:
            return await self._disco()
        
        elif "hardware" in tipo:
            return await self._hardware()
        
        # ========== USUARIOS ==========
        elif "usuarios" in tipo:
            return await self._usuarios()
        
        elif "sesiones" in tipo:
            return await self._sesiones()
        
        # ========== LOGS ==========
        elif "logs" in tipo:
            return await self._logs()
        
        elif "errores" in tipo:
            return await self._errores()
        
        # ========== PAQUETES ==========
        elif "paquetes" in tipo:
            return await self._paquetes()
        
        # ========== MONITOR ==========
        elif "monitor" in tipo:
            return await self._monitor()
        
        # ========== BÁSICAS ==========
        elif "info_sistema" in tipo or "información" in desc:
            return await self._info_sistema()
        
        elif "donde_esta" in tipo or "which" in desc:
            return await self._donde_esta(desc)
        
        else:
            return await self._ejecutar_comando(desc)
    
    # ============================================================
    # IMPLEMENTACIÓN
    # ============================================================
    
    def _ejecutar(self, comando: str) -> Dict:
        """Ejecuta comando y devuelve resultado"""
        try:
            r = subprocess.run(comando, shell=True, capture_output=True, text=True, timeout=30)
            return {"exito": r.returncode == 0, "salida": r.stdout, "error": r.stderr}
        except Exception as e:
            return {"exito": False, "error": str(e)}
    
    # ---------- PROCESOS ----------
    async def _listar_procesos(self) -> ResultadoTarea:
        if self.psutil_disponible:
            import psutil
            procesos = []
            for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    procesos.append(p.info)
                except:
                    pass
            return ResultadoTarea(exito=True, datos={"procesos": procesos[:50]})
        
        # Fallback
        cmd = "ps aux" if self.sistema != "windows" else "tasklist"
        r = self._ejecutar(cmd)
        return ResultadoTarea(exito=r["exito"], datos={"procesos": r["salida"]})
    
    async def _matar_proceso(self, desc: str) -> ResultadoTarea:
        import re
        match = re.search(r"(?:matar|kill)\s+(\d+|[a-zA-Z]+)", desc)
        if not match:
            return ResultadoTarea(exito=False, error="Especifica PID o nombre del proceso")
        
        target = match.group(1)
        
        if target.isdigit():
            cmd = f"kill -9 {target}" if self.sistema != "windows" else f"taskkill /F /PID {target}"
        else:
            cmd = f"pkill -f {target}" if self.sistema != "windows" else f"taskkill /F /IM {target}.exe"
        
        r = self._ejecutar(cmd)
        return ResultadoTarea(exito=r["exito"], datos={"comando": cmd, "salida": r["salida"]})
    
    async def _top_procesos(self) -> ResultadoTarea:
        if self.psutil_disponible:
            import psutil
            procesos = []
            for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    procesos.append(p.info)
                except:
                    pass
            # Ordenar por CPU
            procesos.sort(key=lambda x: x.get('cpu_percent', 0), reverse=True)
            return ResultadoTarea(exito=True, datos={"top_cpu": procesos[:10]})
        
        r = self._ejecutar("ps aux --sort=-%cpu | head -10" if self.sistema != "windows" else "tasklist")
        return ResultadoTarea(exito=r["exito"], datos={"top": r["salida"]})
    
    # ---------- SERVICIOS ----------
    async def _listar_servicios(self) -> ResultadoTarea:
        if self.sistema == "windows":
            r = self._ejecutar("sc query | findstr SERVICE_NAME")
        else:
            r = self._ejecutar("systemctl list-units --type=service | head -30")
        return ResultadoTarea(exito=r["exito"], datos={"servicios": r["salida"]})
    
    async def _estado_servicio(self, desc: str) -> ResultadoTarea:
        import re
        match = re.search(r"(?:estado|status)\s+de\s+([^\s]+)", desc)
        servicio = match.group(1) if match else None
        if not servicio:
            return ResultadoTarea(exito=False, error="Especifica el servicio")
        
        if self.sistema == "windows":
            r = self._ejecutar(f"sc query {servicio}")
        else:
            r = self._ejecutar(f"systemctl status {servicio}")
        return ResultadoTarea(exito=r["exito"], datos={"servicio": servicio, "estado": r["salida"]})
    
    async def _control_servicio(self, desc: str) -> ResultadoTarea:
        import re
        acciones = ["iniciar", "start", "detener", "stop", "reiniciar", "restart"]
        accion = None
        for a in acciones:
            if a in desc:
                accion = a
                break
        
        match = re.search(rf"(?:{accion})\s+([^\s]+)", desc) if accion else None
        servicio = match.group(1) if match else None
        
        if not accion or not servicio:
            return ResultadoTarea(exito=False, error="Usa: iniciar nginx, detener apache, reiniciar mysql")
        
        cmd_map = {
            "iniciar": "start", "start": "start",
            "detener": "stop", "stop": "stop",
            "reiniciar": "restart", "restart": "restart"
        }
        
        if self.sistema == "windows":
            cmd = f"sc {cmd_map[accion]} {servicio}"
        else:
            cmd = f"sudo systemctl {cmd_map[accion]} {servicio}"
        
        r = self._ejecutar(cmd)
        return ResultadoTarea(exito=r["exito"], datos={"servicio": servicio, "accion": accion, "salida": r["salida"]})
    
    # ---------- RED ----------
    async def _info_red(self) -> ResultadoTarea:
        if self.sistema == "windows":
            r = self._ejecutar("ipconfig")
        else:
            r = self._ejecutar("ip addr show")
        return ResultadoTarea(exito=r["exito"], datos={"red": r["salida"]})
    
    async def _conexiones(self) -> ResultadoTarea:
        r = self._ejecutar("netstat -an" if self.sistema == "windows" else "ss -tuln")
        return ResultadoTarea(exito=r["exito"], datos={"conexiones": r["salida"]})
    
    async def _ping(self, desc: str) -> ResultadoTarea:
        import re
        match = re.search(r"ping\s+([^\s]+)", desc)
        objetivo = match.group(1) if match else "google.com"
        
        if self.sistema == "windows":
            cmd = f"ping -n 3 {objetivo}"
        else:
            cmd = f"ping -c 3 {objetivo}"
        
        r = self._ejecutar(cmd)
        return ResultadoTarea(exito=r["exito"], datos={"objetivo": objetivo, "resultado": r["salida"]})
    
    async def _dns(self, desc: str) -> ResultadoTarea:
        import re
        match = re.search(r"(?:dns|resolver)\s+([^\s]+)", desc)
        dominio = match.group(1) if match else "google.com"
        
        if self.sistema == "windows":
            cmd = f"nslookup {dominio}"
        else:
            cmd = f"dig +short {dominio}"
        
        r = self._ejecutar(cmd)
        return ResultadoTarea(exito=r["exito"], datos={"dominio": dominio, "resultado": r["salida"]})
    
    async def _puertos_abiertos(self) -> ResultadoTarea:
        r = self._ejecutar("netstat -an | findstr LISTEN" if self.sistema == "windows" else "ss -tuln | grep LISTEN")
        return ResultadoTarea(exito=r["exito"], datos={"puertos": r["salida"]})
    
    # ---------- HARDWARE ----------
    async def _cpu(self) -> ResultadoTarea:
        if self.psutil_disponible:
            import psutil
            return ResultadoTarea(exito=True, datos={
                "nucleos_fisicos": psutil.cpu_count(logical=False),
                "nucleos_logicos": psutil.cpu_count(logical=True),
                "porcentaje": psutil.cpu_percent(interval=1),
                "por_nucleo": psutil.cpu_percent(interval=1, percpu=True),
                "frecuencia": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None
            })
        r = self._ejecutar("lscpu | head -15" if self.sistema != "windows" else "wmic cpu get name,numberofcores")
        return ResultadoTarea(exito=r["exito"], datos={"cpu": r["salida"]})
    
    async def _memoria(self) -> ResultadoTarea:
        if self.psutil_disponible:
            import psutil
            mem = psutil.virtual_memory()
            swap = psutil.swap_memory()
            return ResultadoTarea(exito=True, datos={
                "total": mem.total,
                "disponible": mem.available,
                "usado": mem.used,
                "porcentaje": mem.percent,
                "swap_total": swap.total,
                "swap_usado": swap.used,
                "swap_porcentaje": swap.percent
            })
        r = self._ejecutar("free -h" if self.sistema != "windows" else "wmic OS get TotalVisibleMemorySize,FreePhysicalMemory")
        return ResultadoTarea(exito=r["exito"], datos={"memoria": r["salida"]})
    
    async def _disco(self) -> ResultadoTarea:
        if self.psutil_disponible:
            import psutil
            particiones = []
            for part in psutil.disk_partitions():
                try:
                    uso = psutil.disk_usage(part.mountpoint)
                    particiones.append({
                        "dispositivo": part.device,
                        "punto_montaje": part.mountpoint,
                        "total": uso.total,
                        "usado": uso.used,
                        "libre": uso.free,
                        "porcentaje": uso.percent
                    })
                except:
                    pass
            return ResultadoTarea(exito=True, datos={"particiones": particiones})
        
        r = self._ejecutar("df -h" if self.sistema != "windows" else "wmic logicaldisk get size,freespace,caption")
        return ResultadoTarea(exito=r["exito"], datos={"disco": r["salida"]})
    
    async def _hardware(self) -> ResultadoTarea:
        datos = {}
        
        if self.psutil_disponible:
            import psutil
            datos["cpu"] = {
                "nucleos": psutil.cpu_count(),
                "porcentaje": psutil.cpu_percent()
            }
            datos["memoria"] = psutil.virtual_memory()._asdict()
            datos["disco"] = []
            for p in psutil.disk_partitions():
                try:
                    datos["disco"].append(psutil.disk_usage(p.mountpoint)._asdict())
                except:
                    pass
        
        return ResultadoTarea(exito=True, datos=datos)
    
    # ---------- USUARIOS ----------
    async def _usuarios(self) -> ResultadoTarea:
        if self.psutil_disponible:
            import psutil
            return ResultadoTarea(exito=True, datos={"usuarios": [u._asdict() for u in psutil.users()]})
        
        r = self._ejecutar("who" if self.sistema != "windows" else "net user")
        return ResultadoTarea(exito=r["exito"], datos={"usuarios": r["salida"]})
    
    async def _sesiones(self) -> ResultadoTarea:
        r = self._ejecutar("who" if self.sistema != "windows" else "quser")
        return ResultadoTarea(exito=r["exito"], datos={"sesiones": r["salida"]})
    
    # ---------- LOGS ----------
    async def _logs(self) -> ResultadoTarea:
        if self.sistema == "windows":
            r = self._ejecutar("wevtutil qe System /c:20 /rd:true /f:text")
        else:
            r = self._ejecutar("journalctl -n 20 --no-pager")
        return ResultadoTarea(exito=r["exito"], datos={"logs": r["salida"]})
    
    async def _errores(self) -> ResultadoTarea:
        if self.sistema == "windows":
            r = self._ejecutar("wevtutil qe System /c:10 /rd:true /f:text /e:error")
        else:
            r = self._ejecutar("journalctl -p 3 -n 20 --no-pager")
        return ResultadoTarea(exito=r["exito"], datos={"errores": r["salida"]})
    
    # ---------- PAQUETES ----------
    async def _paquetes(self) -> ResultadoTarea:
        if self.sistema == "windows":
            r = self._ejecutar("winget list")
        else:
            r = self._ejecutar("apt list --installed | head -30" if os.path.exists("/usr/bin/apt") else "pip list")
        return ResultadoTarea(exito=r["exito"], datos={"paquetes": r["salida"]})
    
    # ---------- MONITOR ----------
    async def _monitor(self) -> ResultadoTarea:
        if self.psutil_disponible:
            import psutil
            return ResultadoTarea(exito=True, datos={
                "cpu": psutil.cpu_percent(interval=1),
                "memoria": psutil.virtual_memory().percent,
                "disco": psutil.disk_usage('/').percent,
                "red": psutil.net_io_counters()._asdict()
            })
        return ResultadoTarea(exito=False, error="Instalar psutil para monitorización completa")
    
    # ---------- BÁSICAS ----------
    async def _info_sistema(self) -> ResultadoTarea:
        return ResultadoTarea(exito=True, datos={
            "sistema": platform.system(),
            "version": platform.version(),
            "hostname": platform.node(),
            "usuario": os.getenv("USER", os.getenv("USERNAME")),
            "python": platform.python_version()
        })
    
    async def _donde_esta(self, desc: str) -> ResultadoTarea:
        import re
        match = re.search(r"(?:donde está|which|ubicación)\s+([^\s]+)", desc)
        comando = match.group(1) if match else None
        if not comando:
            return ResultadoTarea(exito=False, error="Especifica qué comando buscar")
        
        cmd = f"where {comando}" if self.sistema == "windows" else f"which {comando}"
        r = self._ejecutar(cmd)
        return ResultadoTarea(exito=r["exito"], datos={"comando": comando, "ruta": r["salida"]})
    
    async def _ejecutar_comando(self, comando: str) -> ResultadoTarea:
        if not comando:
            return ResultadoTarea(exito=False, error="No se especificó comando")
        r = self._ejecutar(comando)
        return ResultadoTarea(exito=r["exito"], datos={"salida": r["salida"], "error": r.get("error")})


def crear_agente_sistema(supervisor, config) -> AgenteSistema:
    return AgenteSistema(supervisor, config)
