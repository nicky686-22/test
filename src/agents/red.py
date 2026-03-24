#!/usr/bin/env python3
"""
Agente Red - Herramientas de red multiplataforma (Windows/Linux/macOS)
Capacidades: interfaces, conexiones, ping, traceroute, DNS, escaneo, WHOIS, etc.
"""

import os
import sys
import subprocess
import platform
import socket
import re
import ipaddress
import threading
import time
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

from src.core.agente import Agente, TipoAgente, ResultadoTarea
from src.core.supervisor import Supervisor


class AgenteRed(Agente):
    """
    Agente de red multiplataforma.
    Capacidades: interfaces, conexiones, ping, traceroute, DNS, escaneo de puertos, WHOIS
    """
    
    def __init__(self, supervisor: Supervisor, config: Config):
        super().__init__(
            id_agente="red",
            nombre="Agente Red",
            tipo=TipoAgente.RED,
            supervisor=supervisor,
            version="2.0.0"
        )
        self.config = config
        self.sistema = platform.system().lower()
        self._registrar_capacidades()
        self.logger.info(f"Agente Red iniciado. SO: {self.sistema}")
    
    def _registrar_capacidades(self):
        """Registrar todas las capacidades"""
        
        # Interfaces y direcciones
        self.registrar_capacidad("interfaces", "Lista interfaces de red", ["todas", "detalles"])
        self.registrar_capacidad("mi_ip", "Muestra IP local y pública")
        self.registrar_capacidad("mac", "Direcciones MAC de las interfaces")
        
        # Conexiones
        self.registrar_capacidad("conexiones", "Conexiones de red activas")
        self.registrar_capacidad("puertos_abiertos", "Puertos abiertos en el sistema")
        self.registrar_capacidad("escuchar", "Puertos en escucha")
        
        # Diagnóstico
        self.registrar_capacidad("ping", "Prueba de conectividad", ["objetivo", "cantidad"])
        self.registrar_capacidad("traceroute", "Ruta a un destino", ["objetivo"])
        self.registrar_capacidad("dns", "Resolución DNS", ["dominio"])
        self.registrar_capacidad("reverso", "Resolución inversa", ["ip"])
        self.registrar_capacidad("whois", "Información WHOIS", ["dominio"])
        
        # Escaneo
        self.registrar_capacidad("escanear", "Escaneo de puertos", ["objetivo", "puertos"])
        self.registrar_capacidad("escanear_red", "Escaneo de red", ["red"])
        
        # Estadísticas
        self.registrar_capacidad("estadisticas", "Estadísticas de red", ["interfaz"])
        self.registrar_capacidad("velocidad", "Prueba de velocidad (latencia)")
        
        # Configuración
        self.registrar_capacidad("dns_servers", "Servidores DNS configurados")
        self.registrar_capacidad("gateway", "Puerta de enlace predeterminada")
        self.registrar_capacidad("ruta", "Tabla de enrutamiento")
    
    async def ejecutar(self, tarea: Dict[str, Any]) -> ResultadoTarea:
        """Ejecuta tarea según tipo"""
        tipo = tarea.get("tipo", "")
        desc = tarea.get("descripcion", "").lower()
        
        # Interfaces
        if "interfaces" in tipo or "ifconfig" in desc or "ip addr" in desc:
            return await self._interfaces()
        elif "mi_ip" in tipo or "mi ip" in desc or "ip local" in desc:
            return await self._mi_ip()
        elif "mac" in tipo:
            return await self._mac()
        
        # Conexiones
        elif "conexiones" in tipo or "netstat" in desc:
            return await self._conexiones()
        elif "puertos_abiertos" in tipo:
            return await self._puertos_abiertos()
        elif "escuchar" in tipo or "listening" in desc:
            return await self._puertos_escucha()
        
        # Diagnóstico
        elif "ping" in tipo or "ping" in desc:
            return await self._ping(desc)
        elif "traceroute" in tipo or "tracert" in desc:
            return await self._traceroute(desc)
        elif "dns" in tipo or "nslookup" in desc or "resolver" in desc:
            return await self._dns(desc)
        elif "reverso" in tipo:
            return await self._reverso(desc)
        elif "whois" in tipo:
            return await self._whois(desc)
        
        # Escaneo
        elif "escanear" in tipo and "red" not in tipo:
            return await self._escanear_puertos(desc)
        elif "escanear_red" in tipo:
            return await self._escanear_red(desc)
        
        # Estadísticas
        elif "estadisticas" in tipo or "stat" in desc:
            return await self._estadisticas(desc)
        elif "velocidad" in tipo:
            return await self._velocidad(desc)
        
        # Configuración
        elif "dns_servers" in tipo:
            return await self._dns_servers()
        elif "gateway" in tipo:
            return await self._gateway()
        elif "ruta" in tipo or "route" in desc:
            return await self._ruta()
        
        else:
            return ResultadoTarea(exito=False, error=f"No sé cómo manejar: {tipo}")
    
    # ============================================================
    # UTILIDADES
    # ============================================================
    
    def _ejecutar(self, comando: str) -> Dict:
        """Ejecuta comando y devuelve resultado"""
        try:
            r = subprocess.run(comando, shell=True, capture_output=True, text=True, timeout=30)
            return {"exito": r.returncode == 0, "salida": r.stdout, "error": r.stderr}
        except subprocess.TimeoutExpired:
            return {"exito": False, "error": "Timeout"}
        except Exception as e:
            return {"exito": False, "error": str(e)}
    
    def _obtener_objetivo(self, desc: str, predeterminado: str = "google.com") -> str:
        """Extrae objetivo de la descripción"""
        import re
        # Buscar IP o dominio
        ip_pattern = r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'
        dominio_pattern = r'[a-zA-Z0-9][a-zA-Z0-9-]{0,61}[a-zA-Z0-9](?:\.[a-zA-Z]{2,})+'
        
        ip_match = re.search(ip_pattern, desc)
        if ip_match:
            return ip_match.group()
        
        dom_match = re.search(dominio_pattern, desc)
        if dom_match:
            return dom_match.group()
        
        # Buscar después de palabras clave
        for kw in ["ping", "traceroute", "tracert", "dns", "whois", "escanear", "scan"]:
            if kw in desc:
                parts = desc.split(kw)
                if len(parts) > 1:
                    words = parts[1].strip().split()
                    if words:
                        return words[0]
        
        return predeterminado
    
    # ============================================================
    # INTERFACES
    # ============================================================
    
    async def _interfaces(self) -> ResultadoTarea:
        """Lista interfaces de red"""
        if self.sistema == "windows":
            r = self._ejecutar("ipconfig /all")
        elif self.sistema == "darwin":  # macOS
            r = self._ejecutar("ifconfig")
        else:  # Linux
            r = self._ejecutar("ip addr show")
        
        return ResultadoTarea(exito=r["exito"], datos={"interfaces": r["salida"]})
    
    async def _mi_ip(self) -> ResultadoTarea:
        """Obtiene IP local y pública"""
        # IP local
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip_local = s.getsockname()[0]
            s.close()
        except:
            ip_local = "127.0.0.1"
        
        # IP pública
        try:
            import requests
            ip_publica = requests.get("https://api.ipify.org", timeout=5).text
        except:
            ip_publica = "No disponible"
        
        # IPs de todas las interfaces
        ips = []
        try:
            hostname = socket.gethostname()
            for addr in socket.gethostbyname_ex(hostname)[2]:
                if not addr.startswith("127."):
                    ips.append(addr)
        except:
            pass
        
        return ResultadoTarea(exito=True, datos={
            "ip_local": ip_local,
            "ip_publica": ip_publica,
            "todas_las_ips": ips,
            "hostname": socket.gethostname()
        })
    
    async def _mac(self) -> ResultadoTarea:
        """Obtiene direcciones MAC"""
        if self.sistema == "windows":
            r = self._ejecutar("getmac /v")
        elif self.sistema == "darwin":
            r = self._ejecutar("ifconfig | grep ether")
        else:
            r = self._ejecutar("ip link show | grep link/ether")
        
        return ResultadoTarea(exito=r["exito"], datos={"mac": r["salida"]})
    
    # ============================================================
    # CONEXIONES
    # ============================================================
    
    async def _conexiones(self) -> ResultadoTarea:
        """Conexiones activas"""
        if self.sistema == "windows":
            r = self._ejecutar("netstat -an")
        else:
            r = self._ejecutar("ss -tuln")
        
        return ResultadoTarea(exito=r["exito"], datos={"conexiones": r["salida"]})
    
    async def _puertos_abiertos(self) -> ResultadoTarea:
        """Puertos abiertos en el sistema"""
        if self.sistema == "windows":
            r = self._ejecutar("netstat -an | findstr LISTEN")
        else:
            r = self._ejecutar("ss -tuln | grep LISTEN")
        
        return ResultadoTarea(exito=r["exito"], datos={"puertos": r["salida"]})
    
    async def _puertos_escucha(self) -> ResultadoTarea:
        """Puertos en escucha con proceso"""
        if self.sistema == "windows":
            r = self._ejecutar("netstat -ano | findstr LISTEN")
        else:
            r = self._ejecutar("sudo lsof -i -P -n | grep LISTEN")
        
        return ResultadoTarea(exito=r["exito"], datos={"escuchando": r["salida"]})
    
    # ============================================================
    # DIAGNÓSTICO
    # ============================================================
    
    async def _ping(self, desc: str) -> ResultadoTarea:
        """Prueba de ping"""
        objetivo = self._obtener_objetivo(desc, "google.com")
        cantidad = 3
        
        # Extraer cantidad si se especifica
        import re
        match = re.search(r"(\d+)\s*(?:veces|times|packets)", desc)
        if match:
            cantidad = int(match.group(1))
        
        if self.sistema == "windows":
            cmd = f"ping -n {cantidad} {objetivo}"
        else:
            cmd = f"ping -c {cantidad} {objetivo}"
        
        inicio = time.time()
        r = self._ejecutar(cmd)
        latencia = round((time.time() - inicio) * 1000, 2)
        
        return ResultadoTarea(
            exito=r["exito"],
            datos={
                "objetivo": objetivo,
                "paquetes": cantidad,
                "latencia_ms": latencia,
                "resultado": r["salida"]
            }
        )
    
    async def _traceroute(self, desc: str) -> ResultadoTarea:
        """Traceroute a un destino"""
        objetivo = self._obtener_objetivo(desc, "google.com")
        
        if self.sistema == "windows":
            cmd = f"tracert -d {objetivo}"
        elif self.sistema == "darwin":
            cmd = f"traceroute -n {objetivo}"
        else:
            cmd = f"traceroute -n {objetivo}"
        
        r = self._ejecutar(cmd)
        
        return ResultadoTarea(
            exito=r["exito"],
            datos={
                "objetivo": objetivo,
                "ruta": r["salida"]
            }
        )
    
    async def _dns(self, desc: str) -> ResultadoTarea:
        """Resolución DNS"""
        dominio = self._obtener_objetivo(desc, "google.com")
        
        try:
            # Primero intentar con socket
            ips = socket.gethostbyname_ex(dominio)
            resultado = {
                "dominio": dominio,
                "ips": ips[2],
                "alias": ips[0] if ips[0] != dominio else None,
                "metodo": "socket"
            }
            return ResultadoTarea(exito=True, datos=resultado)
        except:
            pass
        
        # Fallback con comandos
        if self.sistema == "windows":
            cmd = f"nslookup {dominio}"
        else:
            cmd = f"dig +short {dominio}"
        
        r = self._ejecutar(cmd)
        
        return ResultadoTarea(
            exito=r["exito"],
            datos={
                "dominio": dominio,
                "resultado": r["salida"],
                "metodo": "comando"
            }
        )
    
    async def _reverso(self, desc: str) -> ResultadoTarea:
        """Resolución inversa (IP -> dominio)"""
        import re
        ip_pattern = r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'
        match = re.search(ip_pattern, desc)
        
        if not match:
            return ResultadoTarea(exito=False, error="Proporciona una IP válida")
        
        ip = match.group()
        
        try:
            hostname = socket.gethostbyaddr(ip)[0]
            return ResultadoTarea(
                exito=True,
                datos={"ip": ip, "hostname": hostname}
            )
        except:
            return ResultadoTarea(
                exito=False,
                error=f"No se pudo resolver {ip}",
                datos={"ip": ip}
            )
    
    async def _whois(self, desc: str) -> ResultadoTarea:
        """Consulta WHOIS"""
        dominio = self._obtener_objetivo(desc, "google.com")
        
        # Intentar con whois si está instalado
        try:
            r = self._ejecutar(f"whois {dominio}")
            if r["exito"]:
                # Limitar a 2000 caracteres
                salida = r["salida"][:2000]
                return ResultadoTarea(
                    exito=True,
                    datos={"dominio": dominio, "whois": salida}
                )
        except:
            pass
        
        # Fallback con API pública
        try:
            import requests
            response = requests.get(f"https://whois-api.com/?domain={dominio}", timeout=10)
            return ResultadoTarea(
                exito=True,
                datos={"dominio": dominio, "whois": response.text[:2000]}
            )
        except:
            return ResultadoTarea(
                exito=False,
                error="WHOIS no disponible. Instala whois o conecta a internet."
            )
    
    # ============================================================
    # ESCANEO
    # ============================================================
    
    async def _escanear_puertos(self, desc: str) -> ResultadoTarea:
        """Escaneo de puertos en un host"""
        objetivo = self._obtener_objetivo(desc, "localhost")
        
        # Extraer puertos
        import re
        puertos = []
        puertos_match = re.search(r"puertos?\s+([\d,\s-]+)", desc)
        if puertos_match:
            parte = puertos_match.group(1)
            if "-" in parte:
                inicio, fin = parte.split("-")
                puertos = list(range(int(inicio), int(fin) + 1))
            else:
                puertos = [int(p.strip()) for p in parte.split(",")]
        
        # Puertos por defecto
        if not puertos:
            puertos = [22, 80, 443, 3306, 5432, 8080, 8443]
        
        # Escanear
        abiertos = []
        for puerto in puertos:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex((objetivo, puerto))
                if result == 0:
                    servicio = self._servicio_por_puerto(puerto)
                    abiertos.append({"puerto": puerto, "servicio": servicio})
                sock.close()
            except:
                pass
        
        return ResultadoTarea(
            exito=len(abiertos) > 0,
            datos={
                "objetivo": objetivo,
                "puertos_abiertos": abiertos,
                "total": len(abiertos)
            }
        )
    
    def _servicio_por_puerto(self, puerto: int) -> str:
        """Servicio común por puerto"""
        servicios = {
            21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 53: "DNS",
            80: "HTTP", 110: "POP3", 143: "IMAP", 443: "HTTPS", 445: "SMB",
            3306: "MySQL", 3389: "RDP", 5432: "PostgreSQL", 6379: "Redis",
            8080: "HTTP-Alt", 8443: "HTTPS-Alt", 27017: "MongoDB"
        }
        return servicios.get(puerto, "Desconocido")
    
    async def _escanear_red(self, desc: str) -> ResultadoTarea:
        """Escaneo de red local"""
        import re
        # Extraer red (ej: 192.168.1.0/24)
        red_match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d{1,2})', desc)
        
        if not red_match:
            # Intentar detectar red local
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
                s.close()
                red = f"{ip.rsplit('.', 1)[0]}.0/24"
            except:
                red = "192.168.1.0/24"
        else:
            red = red_match.group(1)
        
        hosts = []
        try:
            network = ipaddress.ip_network(red, strict=False)
            for ip in network.hosts():
                # Ping simple
                if self.sistema == "windows":
                    cmd = f"ping -n 1 -w 500 {ip}"
                else:
                    cmd = f"ping -c 1 -W 1 {ip}"
                
                r = self._ejecutar(cmd)
                if r["exito"]:
                    hosts.append(str(ip))
                
                if len(hosts) >= 20:  # Límite para no saturar
                    break
        except:
            pass
        
        return ResultadoTarea(
            exito=len(hosts) > 0,
            datos={
                "red": red,
                "hosts_activos": hosts,
                "total": len(hosts)
            }
        )
    
    # ============================================================
    # ESTADÍSTICAS
    # ============================================================
    
    async def _estadisticas(self, desc: str) -> ResultadoTarea:
        """Estadísticas de red"""
        if self.sistema == "windows":
            r = self._ejecutar("netstat -e")
        else:
            r = self._ejecutar("netstat -i")
        
        return ResultadoTarea(exito=r["exito"], datos={"estadisticas": r["salida"]})
    
    async def _velocidad(self, desc: str) -> ResultadoTarea:
        """Prueba de velocidad (latencia)"""
        objetivo = self._obtener_objetivo(desc, "google.com")
        
        tiempos = []
        for i in range(3):
            inicio = time.time()
            try:
                subprocess.run(
                    ["ping", "-n", "1", objetivo] if self.sistema == "windows" else ["ping", "-c", "1", objetivo],
                    capture_output=True,
                    timeout=5
                )
                tiempos.append((time.time() - inicio) * 1000)
            except:
                pass
        
        if tiempos:
            return ResultadoTarea(
                exito=True,
                datos={
                    "objetivo": objetivo,
                    "min_ms": round(min(tiempos), 2),
                    "max_ms": round(max(tiempos), 2),
                    "promedio_ms": round(sum(tiempos) / len(tiempos), 2),
                    "paquetes": len(tiempos)
                }
            )
        else:
            return ResultadoTarea(exito=False, error="No se pudo medir velocidad")
    
    # ============================================================
    # CONFIGURACIÓN
    # ============================================================
    
    async def _dns_servers(self) -> ResultadoTarea:
        """Servidores DNS configurados"""
        if self.sistema == "windows":
            r = self._ejecutar("ipconfig /all | findstr DNS")
        else:
            r = self._ejecutar("cat /etc/resolv.conf | grep nameserver")
        
        return ResultadoTarea(exito=r["exito"], datos={"dns_servers": r["salida"]})
    
    async def _gateway(self) -> ResultadoTarea:
        """Puerta de enlace predeterminada"""
        if self.sistema == "windows":
            r = self._ejecutar("ipconfig | findstr Gateway")
        else:
            r = self._ejecutar("ip route | grep default")
        
        return ResultadoTarea(exito=r["exito"], datos={"gateway": r["salida"]})
    
    async def _ruta(self) -> ResultadoTarea:
        """Tabla de enrutamiento"""
        if self.sistema == "windows":
            r = self._ejecutar("route print")
        else:
            r = self._ejecutar("ip route show")
        
        return ResultadoTarea(exito=r["exito"], datos={"ruta": r["salida"]})


# ============================================================
# Factory Function
# ============================================================

def crear_agente_red(supervisor: Supervisor, config: Config) -> AgenteRed:
    """Crea instancia del agente de red"""
    return AgenteRed(supervisor, config)


# ============================================================
# Example Usage
# ============================================================

def example_usage():
    import asyncio
    
    print("=" * 70)
    print("🌐 Agente Red - Prueba Multiplataforma")
    print(f"Sistema: {platform.system()}")
    print("=" * 70)
    
    class MockSupervisor: pass
    class MockConfig: pass
    
    agent = crear_agente_red(MockSupervisor(), MockConfig())
    
    async def test():
        # Mi IP
        print("\n📡 Mi IP:")
        r = await agent._mi_ip()
        if r.exito:
            print(f"  Local: {r.datos['ip_local']}")
            print(f"  Pública: {r.datos['ip_publica']}")
        
        # Ping
        print("\n🏓 Ping a google.com:")
        r = await agent._ping("ping google.com")
        if r.exito:
            print(f"  Latencia: {r.datos['latencia_ms']}ms")
        
        # DNS
        print("\n🔍 DNS de google.com:")
        r = await agent._dns("dns google.com")
        if r.exito:
            print(f"  IPs: {r.datos.get('ips', 'No disponible')}")
        
        # Puertos abiertos
        print("\n🔓 Puertos abiertos en localhost:")
        r = await agent._escanear_puertos("escanear localhost")
        if r.exito:
            for p in r.datos['puertos_abiertos']:
                print(f"  {p['puerto']}: {p['servicio']}")
    
    asyncio.run(test())
    print("\n✅ Pruebas completadas")


if __name__ == "__main__":
    example_usage()
