#!/usr/bin/env python3
"""
Agente SSH - Conexión remota y ejecución de comandos en máquinas remotas
Multiplataforma: Linux, Windows (con OpenSSH), macOS
Capacidades: SSH, SCP, ejecución remota, transferencia de archivos, múltiples hosts
"""

import os
import sys
import subprocess
import platform
import re
import json
import time
import threading
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from pathlib import Path
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

from src.core.agente import Agente, TipoAgente, ResultadoTarea
from src.core.supervisor import Supervisor
from src.core.config import Config

# Importar paramiko si está disponible (mejor para SSH)
try:
    import paramiko
    PARAMIKO_AVAILABLE = True
except ImportError:
    PARAMIKO_AVAILABLE = False
    paramiko = None

# Para SCP
try:
    from scp import SCPClient
    SCP_AVAILABLE = True
except ImportError:
    SCP_AVAILABLE = False


class AgenteSSH(Agente):
    """
    Agente SSH - Ejecuta comandos en máquinas remotas y locales
    Capacidades: conexión SSH, ejecución remota, transferencia de archivos, múltiples hosts
    """
    
    def __init__(self, supervisor: Supervisor, config: Config):
        super().__init__(
            id_agente="ssh",
            nombre="Agente SSH",
            tipo=TipoAgente.SEGURIDAD,  # Puede ir en SEGURIDAD o crear tipo SSH
            supervisor=supervisor,
            version="2.0.0"
        )
        self.config = config
        
        # Gestión de sesiones SSH
        self.sesiones: Dict[str, paramiko.SSHClient] = {}
        self.hosts_config: Dict[str, Dict] = self._cargar_hosts()
        
        # Pool de ejecución
        self.executor = ThreadPoolExecutor(max_workers=10)
        
        self._registrar_capacidades()
        
        if PARAMIKO_AVAILABLE:
            self.logger.info("Agente SSH iniciado. Paramiko disponible")
        else:
            self.logger.warning("Paramiko no instalado. Instalar con: pip install paramiko scp")
    
    def _cargar_hosts(self) -> Dict[str, Dict]:
        """Cargar configuración de hosts desde archivo"""
        hosts_file = Path("config/hosts.json")
        if hosts_file.exists():
            try:
                with open(hosts_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def _guardar_hosts(self):
        """Guardar configuración de hosts"""
        hosts_file = Path("config/hosts.json")
        hosts_file.parent.mkdir(exist_ok=True)
        with open(hosts_file, 'w') as f:
            json.dump(self.hosts_config, f, indent=2)
    
    def _registrar_capacidades(self):
        """Registrar todas las capacidades del agente SSH"""
        
        # Conexión remota
        self.registrar_capacidad(
            nombre="ssh_conectar",
            descripcion="Conectar a un servidor remoto por SSH",
            parametros=["host", "usuario", "password", "key"],
            ejemplos=["conectar a 192.168.1.10 con usuario root", "ssh a servidor.com"],
            nivel_riesgo="medio"
        )
        
        self.registrar_capacidad(
            nombre="ssh_ejecutar",
            descripcion="Ejecutar comando en servidor remoto",
            parametros=["host", "comando"],
            ejemplos=["ejecutar 'ls -la' en 192.168.1.10", "crear carpeta en remoto"],
            nivel_riesgo="alto"
        )
        
        self.registrar_capacidad(
            nombre="ssh_multiples",
            descripcion="Ejecutar comando en múltiples servidores",
            parametros=["hosts", "comando"],
            ejemplos=["crear carpeta en 192.168.1.10,192.168.1.20,servidor"],
            nivel_riesgo="alto"
        )
        
        self.registrar_capacidad(
            nombre="scp_enviar",
            descripcion="Transferir archivo a servidor remoto",
            parametros=["host", "origen", "destino"],
            ejemplos=["enviar script.py a 192.168.1.10:/tmp/"],
            nivel_riesgo="medio"
        )
        
        self.registrar_capacidad(
            nombre="scp_recibir",
            descripcion="Descargar archivo desde servidor remoto",
            parametros=["host", "origen", "destino"],
            ejemplos=["descargar /var/log/syslog de 192.168.1.10"],
            nivel_riesgo="medio"
        )
        
        self.registrar_capacidad(
            nombre="ssh_mkdir",
            descripcion="Crear carpeta en servidor remoto",
            parametros=["host", "ruta"],
            ejemplos=["crear carpeta /backup en 192.168.1.10"],
            nivel_riesgo="bajo"
        )
        
        self.registrar_capacidad(
            nombre="ssh_scp_multiples",
            descripcion="Distribuir tarea a múltiples servidores",
            parametros=["hosts", "comando", "archivo"],
            ejemplos=["crear 3 carpetas en 2 servidores y hacer backup"],
            nivel_riesgo="alto"
        )
        
        self.registrar_capacidad(
            nombre="hosts",
            descripcion="Listar hosts configurados",
            ejemplos=["listar servidores", "ver hosts disponibles"],
            nivel_riesgo="bajo"
        )
        
        self.registrar_capacidad(
            nombre="host_add",
            descripcion="Agregar un host a la configuración",
            parametros=["nombre", "host", "usuario"],
            ejemplos=["agregar servidor1 con ip 192.168.1.10 usuario root"],
            nivel_riesgo="medio"
        )
    
    # ============================================================
    # CONEXIÓN SSH
    # ============================================================
    
    def _conectar(self, host: str, usuario: str = None, password: str = None, key_path: str = None) -> paramiko.SSHClient:
        """Conectar a un host SSH"""
        if not PARAMIKO_AVAILABLE:
            raise Exception("Paramiko no instalado. pip install paramiko")
        
        # Buscar en hosts configurados
        host_config = None
        for nombre, cfg in self.hosts_config.items():
            if cfg.get("host") == host or nombre == host:
                host_config = cfg
                break
        
        if host_config:
            usuario = usuario or host_config.get("usuario", "root")
            password = password or host_config.get("password")
            key_path = key_path or host_config.get("key_path")
        
        if not usuario:
            usuario = "root"
        
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            if key_path:
                key = paramiko.RSAKey.from_private_key_file(os.path.expanduser(key_path))
                client.connect(host, username=usuario, pkey=key, timeout=10)
            elif password:
                client.connect(host, username=usuario, password=password, timeout=10)
            else:
                # Intentar con clave por defecto
                key_path = os.path.expanduser("~/.ssh/id_rsa")
                if os.path.exists(key_path):
                    key = paramiko.RSAKey.from_private_key_file(key_path)
                    client.connect(host, username=usuario, pkey=key, timeout=10)
                else:
                    raise Exception(f"No hay credenciales para {host}")
            
            return client
        except Exception as e:
            raise Exception(f"Error conectando a {host}: {e}")
    
    def _ejecutar_remoto(self, client: paramiko.SSHClient, comando: str, timeout: int = 60) -> Dict:
        """Ejecutar comando en sesión SSH"""
        try:
            stdin, stdout, stderr = client.exec_command(comando, timeout=timeout)
            salida = stdout.read().decode('utf-8', errors='ignore')
            error = stderr.read().decode('utf-8', errors='ignore')
            return {
                "exito": True,
                "salida": salida,
                "error": error if error else None,
                "comando": comando
            }
        except Exception as e:
            return {"exito": False, "error": str(e)}
    
    # ============================================================
    # EJECUCIÓN DE TAREAS
    # ============================================================
    
    async def ejecutar(self, tarea: Dict[str, Any]) -> ResultadoTarea:
        """Ejecutar tarea según tipo"""
        tipo = tarea.get("tipo", "")
        desc = tarea.get("descripcion", "").lower()
        parametros = tarea.get("parametros", {})
        
        # Gestión de hosts
        if "hosts" in tipo or "listar servidores" in desc:
            return await self._listar_hosts()
        elif "host_add" in tipo or "agregar servidor" in desc:
            return await self._agregar_host(desc, parametros)
        
        # Conexión simple
        elif "ssh_conectar" in tipo or "conectar" in desc:
            return await self._ssh_conectar(desc, parametros)
        
        # Ejecución en un host
        elif "ssh_ejecutar" in tipo or "ejecutar" in desc:
            return await self._ssh_ejecutar(desc, parametros)
        
        # Crear carpeta remota
        elif "ssh_mkdir" in tipo or "crear carpeta" in desc or "mkdir" in desc:
            return await self._ssh_mkdir(desc, parametros)
        
        # Múltiples hosts (la función clave)
        elif "ssh_multiples" in tipo or "multiples" in desc or "varios" in desc:
            return await self._ssh_multiples(desc, parametros)
        
        # Distribución de tareas
        elif "ssh_scp_multiples" in tipo:
            return await self._distribuir_tarea(desc, parametros)
        
        # Transferencia de archivos
        elif "scp_enviar" in tipo or "enviar" in desc:
            return await self._scp_enviar(desc, parametros)
        elif "scp_recibir" in tipo or "descargar" in desc:
            return await self._scp_recibir(desc, parametros)
        
        else:
            return ResultadoTarea(exito=False, error=f"No sé cómo manejar: {tipo}")
    
    # ============================================================
    # GESTIÓN DE HOSTS
    # ============================================================
    
    async def _listar_hosts(self) -> ResultadoTarea:
        """Listar hosts configurados"""
        hosts = []
        for nombre, cfg in self.hosts_config.items():
            hosts.append({
                "nombre": nombre,
                "host": cfg.get("host"),
                "usuario": cfg.get("usuario"),
                "conectado": cfg.get("conectado", False)
            })
        
        return ResultadoTarea(
            exito=True,
            datos={
                "hosts": hosts,
                "total": len(hosts)
            }
        )
    
    async def _agregar_host(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Agregar un host a la configuración"""
        nombre = parametros.get("nombre")
        host = parametros.get("host")
        usuario = parametros.get("usuario", "root")
        password = parametros.get("password")
        key_path = parametros.get("key_path")
        
        # Extraer de descripción si no vienen
        if not nombre:
            import re
            match = re.search(r"servidor\s+([a-zA-Z0-9_]+)", desc)
            nombre = match.group(1) if match else f"host_{len(self.hosts_config)+1}"
        
        if not host:
            match = re.search(r"ip\s+([\d\.]+)", desc)
            host = match.group(1) if match else None
        
        if not host:
            return ResultadoTarea(exito=False, error="Especifica la IP del host")
        
        self.hosts_config[nombre] = {
            "nombre": nombre,
            "host": host,
            "usuario": usuario,
            "password": password,
            "key_path": key_path,
            "agregado": datetime.now().isoformat()
        }
        self._guardar_hosts()
        
        return ResultadoTarea(
            exito=True,
            datos={
                "nombre": nombre,
                "host": host,
                "mensaje": f"Host {nombre} ({host}) agregado correctamente"
            }
        )
    
    # ============================================================
    # OPERACIONES SSH BÁSICAS
    # ============================================================
    
    async def _ssh_conectar(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Probar conexión SSH"""
        host = parametros.get("host") or self._extraer_host(desc)
        usuario = parametros.get("usuario", "root")
        
        if not host:
            return ResultadoTarea(exito=False, error="Especifica el host")
        
        try:
            client = self._conectar(host, usuario)
            client.close()
            return ResultadoTarea(
                exito=True,
                datos={"host": host, "usuario": usuario, "mensaje": f"Conexión exitosa a {host}"}
            )
        except Exception as e:
            return ResultadoTarea(exito=False, error=str(e))
    
    async def _ssh_ejecutar(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Ejecutar comando en un host remoto"""
        host = parametros.get("host") or self._extraer_host(desc)
        comando = parametros.get("comando") or self._extraer_comando(desc)
        
        if not host:
            return ResultadoTarea(exito=False, error="Especifica el host")
        if not comando:
            return ResultadoTarea(exito=False, error="Especifica el comando")
        
        try:
            client = self._conectar(host)
            resultado = self._ejecutar_remoto(client, comando)
            client.close()
            
            return ResultadoTarea(
                exito=resultado["exito"],
                datos={
                    "host": host,
                    "comando": comando,
                    "salida": resultado.get("salida", ""),
                    "error": resultado.get("error")
                }
            )
        except Exception as e:
            return ResultadoTarea(exito=False, error=str(e))
    
    async def _ssh_mkdir(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Crear carpeta en host remoto"""
        host = parametros.get("host") or self._extraer_host(desc)
        ruta = parametros.get("ruta") or self._extraer_ruta(desc)
        
        if not host:
            return ResultadoTarea(exito=False, error="Especifica el host")
        if not ruta:
            return ResultadoTarea(exito=False, error="Especifica la ruta de la carpeta")
        
        try:
            client = self._conectar(host)
            comando = f"mkdir -p {ruta}"
            resultado = self._ejecutar_remoto(client, comando)
            client.close()
            
            return ResultadoTarea(
                exito=resultado["exito"],
                datos={
                    "host": host,
                    "ruta": ruta,
                    "mensaje": f"Carpeta '{ruta}' creada en {host}" if resultado["exito"] else resultado.get("error")
                }
            )
        except Exception as e:
            return ResultadoTarea(exito=False, error=str(e))
    
    # ============================================================
    # OPERACIONES CON MÚLTIPLES HOSTS (LA FUNCIÓN CLAVE)
    # ============================================================
    
    async def _ssh_multiples(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """
        Ejecutar comando en múltiples hosts
        Esta es la función que permite: "crear carpetas en 2 máquinas distintas"
        """
        hosts = parametros.get("hosts", [])
        comando = parametros.get("comando")
        
        # Extraer hosts de la descripción
        if not hosts:
            hosts = self._extraer_hosts(desc)
        
        if not hosts:
            return ResultadoTarea(exito=False, error="Especifica los hosts (ej: en 192.168.1.10,192.168.1.20)")
        
        if not comando:
            comando = self._extraer_comando(desc)
        
        if not comando:
            return ResultadoTarea(exito=False, error="Especifica el comando a ejecutar")
        
        # Ejecutar en paralelo en todos los hosts
        resultados = []
        fallos = 0
        exitos = 0
        
        def ejecutar_en_host(host):
            try:
                client = self._conectar(host)
                resultado = self._ejecutar_remoto(client, comando)
                client.close()
                return {
                    "host": host,
                    "exito": resultado["exito"],
                    "salida": resultado.get("salida", ""),
                    "error": resultado.get("error")
                }
            except Exception as e:
                return {
                    "host": host,
                    "exito": False,
                    "error": str(e)
                }
        
        # Ejecutar en paralelo
        loop = asyncio.get_event_loop()
        tareas = [loop.run_in_executor(self.executor, ejecutar_en_host, host) for host in hosts]
        resultados = await asyncio.gather(*tareas)
        
        for r in resultados:
            if r["exito"]:
                exitos += 1
            else:
                fallos += 1
        
        return ResultadoTarea(
            exito=exitos > 0,
            datos={
                "total_hosts": len(hosts),
                "exitos": exitos,
                "fallos": fallos,
                "resultados": resultados,
                "comando": comando
            }
        )
    
    async def _distribuir_tarea(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """
        Distribuir una tarea compleja a múltiples hosts
        Ejemplo: "crea 3 carpetas en diferentes lugares con códigos en 2 máquinas distintas y respaldo"
        """
        hosts = parametros.get("hosts", [])
        tareas_por_host = parametros.get("tareas", {})
        
        # Extraer información de la descripción
        if not hosts:
            hosts = self._extraer_hosts(desc)
        
        # Detectar qué tipo de tarea es
        if "carpeta" in desc.lower() or "mkdir" in desc.lower():
            # Es una tarea de crear carpetas
            rutas = self._extraer_rutas(desc)
            
            if not rutas:
                rutas = ["/tmp/carpeta1", "/tmp/carpeta2", "/tmp/carpeta3"]
            
            resultados = []
            for host in hosts:
                for ruta in rutas:
                    try:
                        client = self._conectar(host)
                        comando = f"mkdir -p {ruta}"
                        resultado = self._ejecutar_remoto(client, comando)
                        client.close()
                        resultados.append({
                            "host": host,
                            "ruta": ruta,
                            "exito": resultado["exito"],
                            "salida": resultado.get("salida")
                        })
                    except Exception as e:
                        resultados.append({
                            "host": host,
                            "ruta": ruta,
                            "exito": False,
                            "error": str(e)
                        })
            
            return ResultadoTarea(
                exito=True,
                datos={
                    "tarea": "crear_carpetas",
                    "hosts": hosts,
                    "rutas": rutas,
                    "resultados": resultados,
                    "total_operaciones": len(hosts) * len(rutas)
                }
            )
        
        return ResultadoTarea(exito=False, error="Tarea no reconocida para distribución")
    
    async def _scp_enviar(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Enviar archivo a host remoto"""
        if not SCP_AVAILABLE:
            return ResultadoTarea(exito=False, error="SCP no disponible. pip install scp")
        
        host = parametros.get("host") or self._extraer_host(desc)
        origen = parametros.get("origen") or self._extraer_ruta(desc, "origen")
        destino = parametros.get("destino") or self._extraer_ruta(desc, "destino", "/tmp/")
        
        if not host or not origen:
            return ResultadoTarea(exito=False, error="Especifica host y archivo origen")
        
        try:
            client = self._conectar(host)
            with SCPClient(client.get_transport()) as scp:
                scp.put(origen, destino)
            client.close()
            
            return ResultadoTarea(
                exito=True,
                datos={
                    "host": host,
                    "origen": origen,
                    "destino": destino,
                    "mensaje": f"Archivo enviado a {host}:{destino}"
                }
            )
        except Exception as e:
            return ResultadoTarea(exito=False, error=str(e))
    
    async def _scp_recibir(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Recibir archivo desde host remoto"""
        if not SCP_AVAILABLE:
            return ResultadoTarea(exito=False, error="SCP no disponible")
        
        host = parametros.get("host") or self._extraer_host(desc)
        origen = parametros.get("origen") or self._extraer_ruta(desc, "origen")
        destino = parametros.get("destino") or self._extraer_ruta(desc, "destino", ".")
        
        if not host or not origen:
            return ResultadoTarea(exito=False, error="Especifica host y archivo origen")
        
        try:
            client = self._conectar(host)
            with SCPClient(client.get_transport()) as scp:
                scp.get(origen, destino)
            client.close()
            
            return ResultadoTarea(
                exito=True,
                datos={
                    "host": host,
                    "origen": origen,
                    "destino": destino,
                    "mensaje": f"Archivo descargado de {host}:{origen}"
                }
            )
        except Exception as e:
            return ResultadoTarea(exito=False, error=str(e))
    
    # ============================================================
    # EXTRACTORES DE TEXTO
    # ============================================================
    
    def _extraer_host(self, desc: str) -> Optional[str]:
        """Extraer un host de la descripción"""
        # Buscar IP
        ip_pattern = r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'
        match = re.search(ip_pattern, desc)
        if match:
            return match.group(1)
        
        # Buscar nombre de host configurado
        for nombre, cfg in self.hosts_config.items():
            if nombre in desc or cfg.get("host") in desc:
                return cfg.get("host")
        
        return None
    
    def _extraer_hosts(self, desc: str) -> List[str]:
        """Extraer múltiples hosts de la descripción"""
        hosts = []
        
        # Buscar IPs
        ip_pattern = r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'
        ips = re.findall(ip_pattern, desc)
        hosts.extend(ips)
        
        # Buscar nombres de hosts configurados
        for nombre, cfg in self.hosts_config.items():
            if nombre in desc:
                hosts.append(cfg.get("host"))
        
        # Eliminar duplicados
        return list(set(hosts))
    
    def _extraer_comando(self, desc: str) -> Optional[str]:
        """Extraer comando de la descripción"""
        # Buscar después de "ejecutar", "crear", etc.
        patterns = [
            r"ejecutar\s+(.+)",
            r"crear\s+(.+)",
            r"comando\s+(.+)",
            r"correr\s+(.+)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, desc)
            if match:
                return match.group(1)
        
        return None
    
    def _extraer_ruta(self, desc: str, tipo: str = "ruta", predeterminado: str = None) -> Optional[str]:
        """Extraer ruta de la descripción"""
        ruta_pattern = r'(?:en|ruta|path)\s+([/\w\.\-]+)'
        match = re.search(ruta_pattern, desc)
        if match:
            return match.group(1)
        return predeterminado
    
    def _extraer_rutas(self, desc: str) -> List[str]:
        """Extraer múltiples rutas de la descripción"""
        rutas = []
        ruta_pattern = r'(?:en|ruta|path)\s+([/\w\.\-]+)'
        matches = re.findall(ruta_pattern, desc)
        rutas.extend(matches)
        
        # Si no hay rutas específicas, usar algunas por defecto
        if not rutas:
            # Buscar números para múltiples carpetas
            numeros = re.findall(r'(\d+)\s+carpetas?', desc)
            if numeros:
                cantidad = int(numeros[0])
                rutas = [f"/tmp/carpeta{i}" for i in range(1, cantidad + 1)]
            else:
                rutas = ["/tmp/carpeta1", "/tmp/carpeta2", "/tmp/carpeta3"]
        
        return rutas
    
    # ============================================================
    # UTILIDADES
    # ============================================================
    
    def _ejecutar_local(self, comando: str) -> Dict:
        """Ejecutar comando localmente (fallback)"""
        try:
            r = subprocess.run(comando, shell=True, capture_output=True, text=True, timeout=30)
            return {"exito": r.returncode == 0, "salida": r.stdout, "error": r.stderr}
        except Exception as e:
            return {"exito": False, "error": str(e)}


# ============================================================
# Factory Function
# ============================================================

def crear_agente_ssh(supervisor: Supervisor, config: Config) -> AgenteSSH:
    """Crea instancia del agente SSH"""
    return AgenteSSH(supervisor, config)
