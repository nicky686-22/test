#!/usr/bin/env python3
"""
Agente Paquetes - Gestión de paquetes y programas
Multiplataforma (Windows/Linux/macOS)
Capacidades: instalar, desinstalar, actualizar, buscar, listar paquetes
"""

import os
import sys
import subprocess
import platform
import re
import json
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

from src.core.agente import Agente, TipoAgente, ResultadoTarea
from src.core.supervisor import Supervisor
from src.core.config import Config


class AgentePaquetes(Agente):
    """
    Agente de gestión de paquetes multiplataforma.
    Capacidades: instalar, desinstalar, actualizar, buscar, listar paquetes
    Soporta: apt (Debian/Ubuntu), yum (RHEL/CentOS), pacman (Arch), winget (Windows), brew (macOS), pip, npm
    """
    
    def __init__(self, supervisor: Supervisor, config: Config):
        super().__init__(
            id_agente="paquetes",
            nombre="Agente Paquetes",
            tipo=TipoAgente.PAQUETES,
            supervisor=supervisor,
            version="2.0.0"
        )
        self.config = config
        self.sistema = platform.system().lower()
        self._detectar_gestores()
        self._registrar_capacidades()
        self.logger.info(f"Agente Paquetes iniciado. SO: {self.sistema}")
        self.logger.info(f"Gestores detectados: {self.gestores_disponibles}")
    
    def _detectar_gestores(self):
        """Detectar gestores de paquetes disponibles en el sistema"""
        self.gestores = {
            "apt": {
                "disponible": False,
                "comando": "apt",
                "tipo": "sistema",
                "sistema": "linux",
                "instalar": "sudo apt install -y {paquete}",
                "desinstalar": "sudo apt remove -y {paquete}",
                "actualizar": "sudo apt update && sudo apt upgrade -y",
                "buscar": "apt search {paquete}",
                "listar": "apt list --installed",
                "info": "apt show {paquete}"
            },
            "yum": {
                "disponible": False,
                "comando": "yum",
                "tipo": "sistema",
                "sistema": "linux",
                "instalar": "sudo yum install -y {paquete}",
                "desinstalar": "sudo yum remove -y {paquete}",
                "actualizar": "sudo yum update -y",
                "buscar": "yum search {paquete}",
                "listar": "yum list installed",
                "info": "yum info {paquete}"
            },
            "pacman": {
                "disponible": False,
                "comando": "pacman",
                "tipo": "sistema",
                "sistema": "linux",
                "instalar": "sudo pacman -S --noconfirm {paquete}",
                "desinstalar": "sudo pacman -R --noconfirm {paquete}",
                "actualizar": "sudo pacman -Syu --noconfirm",
                "buscar": "pacman -Ss {paquete}",
                "listar": "pacman -Q",
                "info": "pacman -Qi {paquete}"
            },
            "winget": {
                "disponible": False,
                "comando": "winget",
                "tipo": "sistema",
                "sistema": "windows",
                "instalar": "winget install --silent {paquete}",
                "desinstalar": "winget uninstall --silent {paquete}",
                "actualizar": "winget upgrade --all",
                "buscar": "winget search {paquete}",
                "listar": "winget list",
                "info": "winget show {paquete}"
            },
            "choco": {
                "disponible": False,
                "comando": "choco",
                "tipo": "sistema",
                "sistema": "windows",
                "instalar": "choco install {paquete} -y",
                "desinstalar": "choco uninstall {paquete} -y",
                "actualizar": "choco upgrade all -y",
                "buscar": "choco find {paquete}",
                "listar": "choco list --local-only",
                "info": "choco info {paquete}"
            },
            "brew": {
                "disponible": False,
                "comando": "brew",
                "tipo": "sistema",
                "sistema": "darwin",
                "instalar": "brew install {paquete}",
                "desinstalar": "brew uninstall {paquete}",
                "actualizar": "brew update && brew upgrade",
                "buscar": "brew search {paquete}",
                "listar": "brew list",
                "info": "brew info {paquete}"
            },
            "pip": {
                "disponible": False,
                "comando": "pip",
                "tipo": "python",
                "sistema": "multiplataforma",
                "instalar": "pip install {paquete}",
                "desinstalar": "pip uninstall -y {paquete}",
                "actualizar": "pip install --upgrade {paquete}",
                "buscar": "pip search {paquete}",
                "listar": "pip list",
                "info": "pip show {paquete}"
            },
            "pip3": {
                "disponible": False,
                "comando": "pip3",
                "tipo": "python",
                "sistema": "multiplataforma",
                "instalar": "pip3 install {paquete}",
                "desinstalar": "pip3 uninstall -y {paquete}",
                "actualizar": "pip3 install --upgrade {paquete}",
                "buscar": "pip3 search {paquete}",
                "listar": "pip3 list",
                "info": "pip3 show {paquete}"
            },
            "npm": {
                "disponible": False,
                "comando": "npm",
                "tipo": "node",
                "sistema": "multiplataforma",
                "instalar": "npm install -g {paquete}",
                "desinstalar": "npm uninstall -g {paquete}",
                "actualizar": "npm update -g",
                "buscar": "npm search {paquete}",
                "listar": "npm list -g --depth=0",
                "info": "npm view {paquete}"
            }
        }
        
        # Detectar gestores disponibles
        self.gestores_disponibles = []
        for nombre, gestor in self.gestores.items():
            try:
                resultado = subprocess.run(
                    f"which {gestor['comando']}" if self.sistema != "windows" else f"where {gestor['comando']}",
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if resultado.returncode == 0:
                    gestor["disponible"] = True
                    self.gestores_disponibles.append(nombre)
            except:
                pass
    
    def _registrar_capacidades(self):
        """Registrar todas las capacidades"""
        
        # Gestión de paquetes
        self.registrar_capacidad("instalar", "Instalar un paquete o programa")
        self.registrar_capacidad("desinstalar", "Desinstalar un paquete o programa")
        self.registrar_capacidad("actualizar", "Actualizar paquetes del sistema")
        self.registrar_capacidad("actualizar_paquete", "Actualizar un paquete específico")
        
        # Información
        self.registrar_capacidad("buscar", "Buscar paquetes disponibles")
        self.registrar_capacidad("listar", "Listar paquetes instalados")
        self.registrar_capacidad("info", "Información de un paquete")
        self.registrar_capacidad("versiones", "Ver versiones disponibles")
        
        # Gestores
        self.registrar_capacidad("gestores", "Listar gestores disponibles")
        self.registrar_capacidad("gestor_recomendado", "Gestor recomendado para el sistema")
        
        # Limpieza
        self.registrar_capacidad("limpiar", "Limpiar caché de paquetes")
        self.registrar_capacidad("dependencias", "Instalar dependencias desde requirements.txt")
    
    async def ejecutar(self, tarea: Dict[str, Any]) -> ResultadoTarea:
        """Ejecuta tarea según tipo"""
        tipo = tarea.get("tipo", "")
        desc = tarea.get("descripcion", "").lower()
        parametros = tarea.get("parametros", {})
        
        # Gestores
        if "gestores" in tipo:
            return await self._listar_gestores()
        elif "gestor_recomendado" in tipo:
            return await self._gestor_recomendado()
        
        # Gestión de paquetes
        elif "instalar" in tipo or "install" in desc:
            return await self._instalar(desc, parametros)
        elif "desinstalar" in tipo or "remove" in desc or "uninstall" in desc:
            return await self._desinstalar(desc, parametros)
        elif "actualizar" in tipo and "paquete" in tipo:
            return await self._actualizar_paquete(desc, parametros)
        elif "actualizar" in tipo or "update" in desc or "upgrade" in desc:
            return await self._actualizar_sistema(parametros)
        
        # Información
        elif "buscar" in tipo or "search" in desc:
            return await self._buscar(desc, parametros)
        elif "listar" in tipo or "list" in desc:
            return await self._listar(parametros)
        elif "info" in tipo:
            return await self._info(desc, parametros)
        elif "versiones" in tipo:
            return await self._versiones(desc, parametros)
        
        # Limpieza
        elif "limpiar" in tipo or "clean" in desc:
            return await self._limpiar()
        elif "dependencias" in tipo or "requirements" in desc:
            return await self._instalar_dependencias(desc, parametros)
        
        else:
            return ResultadoTarea(exito=False, error=f"No sé cómo manejar: {tipo}")
    
    # ============================================================
    # UTILIDADES
    # ============================================================
    
    def _ejecutar(self, comando: str) -> Dict:
        """Ejecuta comando y devuelve resultado"""
        try:
            r = subprocess.run(comando, shell=True, capture_output=True, text=True, timeout=120)
            return {"exito": r.returncode == 0, "salida": r.stdout, "error": r.stderr}
        except subprocess.TimeoutExpired:
            return {"exito": False, "error": "Timeout (120s)"}
        except Exception as e:
            return {"exito": False, "error": str(e)}
    
    def _obtener_paquete(self, desc: str, predeterminado: str = None) -> str:
        """Extraer nombre del paquete de la descripción"""
        patrones = [
            r"(?:instalar|install|desinstalar|remove|uninstall|buscar|search|info)\s+([^\s]+)",
            r"paquete\s+([^\s]+)",
            r"([a-zA-Z0-9\-_\.]+)"
        ]
        
        for patron in patrones:
            match = re.search(patron, desc)
            if match:
                return match.group(1)
        
        return predeterminado
    
    def _seleccionar_gestor(self, tipo: str = None) -> Optional[str]:
        """Selecciona el mejor gestor para la operación"""
        if tipo == "python":
            if "pip3" in self.gestores_disponibles:
                return "pip3"
            if "pip" in self.gestores_disponibles:
                return "pip"
        elif tipo == "node":
            if "npm" in self.gestores_disponibles:
                return "npm"
        elif tipo == "sistema":
            # Priorizar gestores del sistema según SO
            if self.sistema == "linux":
                for g in ["apt", "yum", "pacman"]:
                    if g in self.gestores_disponibles:
                        return g
            elif self.sistema == "windows":
                for g in ["winget", "choco"]:
                    if g in self.gestores_disponibles:
                        return g
            elif self.sistema == "darwin":
                if "brew" in self.gestores_disponibles:
                    return "brew"
        
        # Si no se especifica tipo, devolver el primer gestor disponible
        if self.gestores_disponibles:
            return self.gestores_disponibles[0]
        
        return None
    
    # ============================================================
    # GESTORES
    # ============================================================
    
    async def _listar_gestores(self) -> ResultadoTarea:
        """Listar gestores de paquetes disponibles"""
        gestores_info = []
        for nombre, gestor in self.gestores.items():
            gestores_info.append({
                "nombre": nombre,
                "disponible": gestor["disponible"],
                "tipo": gestor["tipo"],
                "comando": gestor["comando"]
            })
        
        return ResultadoTarea(
            exito=True,
            datos={
                "gestores": gestores_info,
                "disponibles": self.gestores_disponibles,
                "sistema": self.sistema
            }
        )
    
    async def _gestor_recomendado(self) -> ResultadoTarea:
        """Obtener gestor recomendado para el sistema"""
        gestor = self._seleccionar_gestor("sistema")
        
        return ResultadoTarea(
            exito=True,
            datos={
                "gestor_recomendado": gestor,
                "sistema": self.sistema,
                "todos": self.gestores_disponibles
            }
        )
    
    # ============================================================
    # GESTIÓN DE PAQUETES
    # ============================================================
    
    async def _instalar(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Instalar un paquete"""
        paquete = parametros.get("paquete") or self._obtener_paquete(desc)
        if not paquete:
            return ResultadoTarea(exito=False, error="Especifica qué paquete instalar")
        
        tipo = parametros.get("tipo")  # sistema, python, node
        gestor_nombre = parametros.get("gestor") or self._seleccionar_gestor(tipo)
        
        if not gestor_nombre:
            return ResultadoTarea(exito=False, error="No hay gestor de paquetes disponible")
        
        gestor = self.gestores[gestor_nombre]
        comando = gestor["instalar"].format(paquete=paquete)
        
        self.logger.info(f"Instalando {paquete} con {gestor_nombre}")
        resultado = self._ejecutar(comando)
        
        return ResultadoTarea(
            exito=resultado["exito"],
            datos={
                "paquete": paquete,
                "gestor": gestor_nombre,
                "comando": comando,
                "salida": resultado["salida"],
                "error": resultado["error"]
            }
        )
    
    async def _desinstalar(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Desinstalar un paquete"""
        paquete = parametros.get("paquete") or self._obtener_paquete(desc)
        if not paquete:
            return ResultadoTarea(exito=False, error="Especifica qué paquete desinstalar")
        
        tipo = parametros.get("tipo")
        gestor_nombre = parametros.get("gestor") or self._seleccionar_gestor(tipo)
        
        if not gestor_nombre:
            return ResultadoTarea(exito=False, error="No hay gestor de paquetes disponible")
        
        gestor = self.gestores[gestor_nombre]
        comando = gestor["desinstalar"].format(paquete=paquete)
        
        self.logger.info(f"Desinstalando {paquete} con {gestor_nombre}")
        resultado = self._ejecutar(comando)
        
        return ResultadoTarea(
            exito=resultado["exito"],
            datos={
                "paquete": paquete,
                "gestor": gestor_nombre,
                "comando": comando,
                "salida": resultado["salida"]
            }
        )
    
    async def _actualizar_sistema(self, parametros: Dict) -> ResultadoTarea:
        """Actualizar todos los paquetes del sistema"""
        gestor_nombre = parametros.get("gestor") or self._seleccionar_gestor("sistema")
        
        if not gestor_nombre:
            return ResultadoTarea(exito=False, error="No hay gestor de paquetes disponible")
        
        gestor = self.gestores[gestor_nombre]
        comando = gestor["actualizar"]
        
        self.logger.info(f"Actualizando sistema con {gestor_nombre}")
        resultado = self._ejecutar(comando)
        
        return ResultadoTarea(
            exito=resultado["exito"],
            datos={
                "gestor": gestor_nombre,
                "comando": comando,
                "salida": resultado["salida"]
            }
        )
    
    async def _actualizar_paquete(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Actualizar un paquete específico"""
        paquete = parametros.get("paquete") or self._obtener_paquete(desc)
        if not paquete:
            return ResultadoTarea(exito=False, error="Especifica qué paquete actualizar")
        
        tipo = parametros.get("tipo")
        gestor_nombre = parametros.get("gestor") or self._seleccionar_gestor(tipo)
        
        if not gestor_nombre:
            return ResultadoTarea(exito=False, error="No hay gestor de paquetes disponible")
        
        gestor = self.gestores[gestor_nombre]
        comando = gestor["actualizar_paquete"].format(paquete=paquete) if "actualizar_paquete" in gestor else f"{gestor['comando']} upgrade {paquete}"
        
        self.logger.info(f"Actualizando {paquete} con {gestor_nombre}")
        resultado = self._ejecutar(comando)
        
        return ResultadoTarea(
            exito=resultado["exito"],
            datos={
                "paquete": paquete,
                "gestor": gestor_nombre,
                "salida": resultado["salida"]
            }
        )
    
    # ============================================================
    # INFORMACIÓN
    # ============================================================
    
    async def _buscar(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Buscar paquetes"""
        patron = parametros.get("patron") or self._obtener_paquete(desc)
        if not patron:
            return ResultadoTarea(exito=False, error="Especifica qué buscar")
        
        tipo = parametros.get("tipo")
        gestor_nombre = parametros.get("gestor") or self._seleccionar_gestor(tipo)
        
        if not gestor_nombre:
            return ResultadoTarea(exito=False, error="No hay gestor de paquetes disponible")
        
        gestor = self.gestores[gestor_nombre]
        comando = gestor["buscar"].format(paquete=patron)
        
        resultado = self._ejecutar(comando)
        
        # Extraer resultados
        resultados = []
        if resultado["exito"]:
            lineas = resultado["salida"].split("\n")
            for linea in lineas[:20]:  # Limitar a 20 resultados
                if patron in linea:
                    resultados.append(linea.strip())
        
        return ResultadoTarea(
            exito=resultado["exito"],
            datos={
                "patron": patron,
                "gestor": gestor_nombre,
                "resultados": resultados,
                "total": len(resultados)
            }
        )
    
    async def _listar(self, parametros: Dict) -> ResultadoTarea:
        """Listar paquetes instalados"""
        tipo = parametros.get("tipo")
        gestor_nombre = parametros.get("gestor") or self._seleccionar_gestor(tipo)
        limite = parametros.get("limite", 50)
        
        if not gestor_nombre:
            return ResultadoTarea(exito=False, error="No hay gestor de paquetes disponible")
        
        gestor = self.gestores[gestor_nombre]
        comando = gestor["listar"]
        
        resultado = self._ejecutar(comando)
        
        # Extraer lista de paquetes
        paquetes = []
        if resultado["exito"]:
            lineas = resultado["salida"].split("\n")
            for linea in lineas[:limite]:
                if linea.strip() and not linea.startswith("Listing"):
                    paquetes.append(linea.strip())
        
        return ResultadoTarea(
            exito=resultado["exito"],
            datos={
                "gestor": gestor_nombre,
                "paquetes": paquetes,
                "total": len(paquetes)
            }
        )
    
    async def _info(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Información de un paquete"""
        paquete = parametros.get("paquete") or self._obtener_paquete(desc)
        if not paquete:
            return ResultadoTarea(exito=False, error="Especifica qué paquete consultar")
        
        tipo = parametros.get("tipo")
        gestor_nombre = parametros.get("gestor") or self._seleccionar_gestor(tipo)
        
        if not gestor_nombre:
            return ResultadoTarea(exito=False, error="No hay gestor de paquetes disponible")
        
        gestor = self.gestores[gestor_nombre]
        comando = gestor["info"].format(paquete=paquete)
        
        resultado = self._ejecutar(comando)
        
        return ResultadoTarea(
            exito=resultado["exito"],
            datos={
                "paquete": paquete,
                "gestor": gestor_nombre,
                "informacion": resultado["salida"]
            }
        )
    
    async def _versiones(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Ver versiones disponibles de un paquete"""
        paquete = parametros.get("paquete") or self._obtener_paquete(desc)
        if not paquete:
            return ResultadoTarea(exito=False, error="Especifica qué paquete consultar")
        
        versiones = []
        
        # Para pip
        if "pip" in self.gestores_disponibles:
            r = self._ejecutar(f"pip index versions {paquete}")
            if r["exito"]:
                match = re.findall(r'(\d+\.\d+\.\d+)', r["salida"])
                versiones.extend(match[:10])
        
        # Para npm
        if "npm" in self.gestores_disponibles:
            r = self._ejecutar(f"npm view {paquete} versions --json")
            if r["exito"]:
                try:
                    versions_json = json.loads(r["salida"])
                    versiones.extend(versions_json[-10:])
                except:
                    pass
        
        return ResultadoTarea(
            exito=len(versiones) > 0,
            datos={
                "paquete": paquete,
                "versiones": versiones,
                "total": len(versiones)
            }
        )
    
    # ============================================================
    # LIMPIEZA Y DEPENDENCIAS
    # ============================================================
    
    async def _limpiar(self) -> ResultadoTarea:
        """Limpiar caché de paquetes"""
        resultados = []
        
        if "apt" in self.gestores_disponibles:
            r = self._ejecutar("sudo apt clean")
            resultados.append({"gestor": "apt", "resultado": r["exito"]})
            r = self._ejecutar("sudo apt autoclean")
            resultados.append({"gestor": "apt", "autoclean": r["exito"]})
        
        if "yum" in self.gestores_disponibles:
            r = self._ejecutar("sudo yum clean all")
            resultados.append({"gestor": "yum", "resultado": r["exito"]})
        
        if "pacman" in self.gestores_disponibles:
            r = self._ejecutar("sudo pacman -Sc --noconfirm")
            resultados.append({"gestor": "pacman", "resultado": r["exito"]})
        
        if "pip" in self.gestores_disponibles:
            r = self._ejecutar("pip cache purge")
            resultados.append({"gestor": "pip", "resultado": r["exito"]})
        
        if "npm" in self.gestores_disponibles:
            r = self._ejecutar("npm cache clean --force")
            resultados.append({"gestor": "npm", "resultado": r["exito"]})
        
        return ResultadoTarea(
            exito=True,
            datos={"limpiezas": resultados}
        )
    
    async def _instalar_dependencias(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Instalar dependencias desde archivo requirements.txt o package.json"""
        archivo = parametros.get("archivo")
        tipo = parametros.get("tipo", "pip")
        
        if not archivo:
            # Buscar archivos comunes
            if os.path.exists("requirements.txt"):
                archivo = "requirements.txt"
                tipo = "pip"
            elif os.path.exists("package.json"):
                archivo = "package.json"
                tipo = "npm"
            else:
                return ResultadoTarea(exito=False, error="No se encontró archivo de dependencias")
        
        if tipo == "pip":
            comando = f"pip install -r {archivo}"
        elif tipo == "npm":
            comando = f"npm install"
        else:
            return ResultadoTarea(exito=False, error=f"Tipo no soportado: {tipo}")
        
        self.logger.info(f"Instalando dependencias desde {archivo}")
        resultado = self._ejecutar(comando)
        
        return ResultadoTarea(
            exito=resultado["exito"],
            datos={
                "archivo": archivo,
                "tipo": tipo,
                "comando": comando,
                "salida": resultado["salida"]
            }
        )


# ============================================================
# Factory Function
# ============================================================

def crear_agente_paquetes(supervisor: Supervisor, config: Config) -> AgentePaquetes:
    """Crea instancia del agente de paquetes"""
    return AgentePaquetes(supervisor, config)
