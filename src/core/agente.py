#!/usr/bin/env python3
"""
Agente de Archivos - Crea, lee, escribe y maneja archivos y carpetas
"""

import os
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any

from src.core.agente import Agente, TipoAgente, EstadoAgente


class AgenteArchivos(Agente):
    """Agente que maneja archivos y carpetas"""
    
    def __init__(self, supervisor, config):
        super().__init__(
            id_agente="agente_archivos",
            nombre="Agente de Archivos",
            tipo=TipoAgente.ARCHIVOS,
            supervisor=supervisor
        )
        self.config = config
        self.directorio_trabajo = Path.cwd()
        
        # Registrar capacidades
        self.registrar_capacidad("crear_carpeta", "Crear una nueva carpeta o directorio")
        self.registrar_capacidad("crear_archivo", "Crear un nuevo archivo")
        self.registrar_capacidad("listar_archivos", "Listar archivos en un directorio")
        self.registrar_capacidad("leer_archivo", "Leer el contenido de un archivo")
        self.registrar_capacidad("borrar_archivo", "Eliminar un archivo o carpeta")
        
        self.logger.info(f"Agente de Archivos iniciado. Directorio: {self.directorio_trabajo}")
    
    async def ejecutar(self, tarea: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecutar tarea según el tipo"""
        tipo = tarea.get("tipo", "")
        descripcion = tarea.get("descripcion", "")
        datos = tarea.get("datos", {})
        
        if "carpeta" in tipo or "mkdir" in descripcion.lower():
            return await self._crear_carpeta(descripcion, datos)
        
        elif "archivo" in tipo or "touch" in descripcion.lower():
            return await self._crear_archivo(descripcion, datos)
        
        elif "listar" in tipo or "ls" in descripcion.lower():
            return await self._listar_archivos(descripcion, datos)
        
        elif "leer" in tipo or "cat" in descripcion.lower():
            return await self._leer_archivo(descripcion, datos)
        
        elif "borrar" in tipo or "eliminar" in tipo or "rm" in descripcion.lower():
            return await self._borrar_archivo(descripcion, datos)
        
        else:
            return {"exito": False, "error": f"No sé cómo manejar: {tipo}"}
    
    async def _crear_carpeta(self, descripcion: str, datos: Dict) -> Dict[str, Any]:
        """Crear una carpeta"""
        import re
        
        # Extraer nombre de carpeta
        nombre = datos.get("nombre_carpeta")
        if not nombre:
            match = re.search(r"(?:crear carpeta|crea carpeta|mkdir)\s+([^\s]+)", descripcion.lower())
            nombre = match.group(1) if match else "nueva_carpeta"
        
        ruta = Path(nombre)
        
        try:
            ruta.mkdir(exist_ok=True)
            return {
                "exito": True,
                "carpeta": str(ruta.absolute()),
                "mensaje": f"Carpeta creada: {ruta.absolute()}"
            }
        except Exception as e:
            return {"exito": False, "error": f"Error creando carpeta: {e}"}
    
    async def _crear_archivo(self, descripcion: str, datos: Dict) -> Dict[str, Any]:
        """Crear un archivo"""
        import re
        
        nombre = datos.get("nombre_archivo")
        if not nombre:
            match = re.search(r"(?:crear archivo|crea archivo|touch)\s+([^\s]+)", descripcion.lower())
            nombre = match.group(1) if match else "archivo.txt"
        
        contenido = datos.get("contenido", "")
        if not contenido and "contenido:" in descripcion:
            contenido = descripcion.split("contenido:")[-1].strip()
        
        ruta = Path(nombre)
        
        try:
            with open(ruta, 'w') as f:
                f.write(contenido)
            
            return {
                "exito": True,
                "archivo": str(ruta.absolute()),
                "contenido": contenido,
                "mensaje": f"Archivo creado: {ruta.absolute()}"
            }
        except Exception as e:
            return {"exito": False, "error": f"Error creando archivo: {e}"}
    
    async def _listar_archivos(self, descripcion: str, datos: Dict) -> Dict[str, Any]:
        """Listar archivos"""
        import re
        
        directorio = datos.get("directorio", ".")
        match = re.search(r"(?:listar|ls)\s+([^\s]+)", descripcion.lower())
        if match:
            directorio = match.group(1)
        
        ruta = Path(directorio)
        
        if not ruta.exists():
            return {"exito": False, "error": f"No existe: {directorio}"}
        
        try:
            items = []
            for item in ruta.iterdir():
                items.append({
                    "nombre": item.name,
                    "tipo": "carpeta" if item.is_dir() else "archivo",
                    "tamaño": item.stat().st_size if item.is_file() else 0
                })
            
            return {
                "exito": True,
                "directorio": str(ruta.absolute()),
                "items": items,
                "cantidad": len(items)
            }
        except Exception as e:
            return {"exito": False, "error": str(e)}
    
    async def _leer_archivo(self, descripcion: str, datos: Dict) -> Dict[str, Any]:
        """Leer contenido de un archivo"""
        import re
        
        nombre = datos.get("nombre_archivo")
        if not nombre:
            match = re.search(r"(?:leer|cat)\s+([^\s]+)", descripcion.lower())
            nombre = match.group(1) if match else None
        
        if not nombre:
            return {"exito": False, "error": "No especificaste qué archivo leer"}
        
        ruta = Path(nombre)
        
        if not ruta.exists():
            return {"exito": False, "error": f"El archivo {nombre} no existe"}
        
        try:
            with open(ruta, 'r') as f:
                contenido = f.read()
            
            return {
                "exito": True,
                "archivo": str(ruta.absolute()),
                "contenido": contenido,
                "tamaño": len(contenido)
            }
        except Exception as e:
            return {"exito": False, "error": str(e)}
    
    async def _borrar_archivo(self, descripcion: str, datos: Dict) -> Dict[str, Any]:
        """Borrar archivo o carpeta"""
        import re
        import shutil
        
        nombre = datos.get("nombre")
        if not nombre:
            match = re.search(r"(?:borrar|eliminar|rm)\s+([^\s]+)", descripcion.lower())
            nombre = match.group(1) if match else None
        
        if not nombre:
            return {"exito": False, "error": "No especificaste qué borrar"}
        
        ruta = Path(nombre)
        
        if not ruta.exists():
            return {"exito": False, "error": f"No existe: {nombre}"}
        
        try:
            if ruta.is_dir():
                shutil.rmtree(ruta)
            else:
                ruta.unlink()
            
            return {
                "exito": True,
                "mensaje": f"Eliminado: {ruta.absolute()}"
            }
        except Exception as e:
            return {"exito": False, "error": str(e)}


def crear_agente_archivos(supervisor, config) -> AgenteArchivos:
    """Crear una instancia del agente de archivos"""
    return AgenteArchivos(supervisor, config)
