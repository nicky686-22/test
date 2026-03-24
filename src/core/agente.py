#!/usr/bin/env python3
"""
Agente de Archivos - Gestión profesional de archivos y directorios
"""

import os
import shutil
import subprocess
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from src.core.agente import Agente, TipoAgente, ResultadoTarea, Capacidad


class AgenteArchivos(Agente):
    """
    Agente especializado en operaciones con archivos y directorios.
    Capacidades: crear, leer, escribir, mover, copiar, eliminar, buscar, comprimir.
    """
    
    def __init__(self, supervisor, config):
        super().__init__(
            id_agente="archivos",
            nombre="Agente de Archivos",
            tipo=TipoAgente.ARCHIVOS,
            supervisor=supervisor,
            version="2.0.0"
        )
        self.config = config
        self.directorio_base = Path.cwd()
        
        # Registrar capacidades
        self._registrar_capacidades()
        
        self.logger.info(f"Agente de Archivos iniciado. Base: {self.directorio_base}")
    
    def _registrar_capacidades(self):
        """Registrar todas las capacidades del agente"""
        
        self.registrar_capacidad(
            nombre="crear_carpeta",
            descripcion="Crea una nueva carpeta o directorio",
            parametros=["nombre", "ruta"],
            ejemplos=["crear carpeta documentos", "mkdir proyecto"],
            nivel_riesgo="bajo"
        )
        
        self.registrar_capacidad(
            nombre="crear_archivo",
            descripcion="Crea un nuevo archivo con contenido opcional",
            parametros=["nombre", "contenido", "ruta"],
            ejemplos=["crear archivo hola.txt con contenido: Hola mundo"],
            nivel_riesgo="bajo"
        )
        
        self.registrar_capacidad(
            nombre="leer_archivo",
            descripcion="Lee el contenido de un archivo",
            parametros=["archivo"],
            ejemplos=["leer archivo config.json", "muestra el contenido de README.md"],
            nivel_riesgo="bajo"
        )
        
        self.registrar_capacidad(
            nombre="listar_archivos",
            descripcion="Lista archivos en un directorio",
            parametros=["ruta", "detallado", "recursivo"],
            ejemplos=["listar archivos", "ver carpeta actual", "ls -la"],
            nivel_riesgo="bajo"
        )
        
        self.registrar_capacidad(
            nombre="mover_archivo",
            descripcion="Mueve o renombra archivos/carpetas",
            parametros=["origen", "destino"],
            ejemplos=["mover archivo.txt a documentos/"],
            nivel_riesgo="medio"
        )
        
        self.registrar_capacidad(
            nombre="copiar_archivo",
            descripcion="Copia archivos o carpetas",
            parametros=["origen", "destino"],
            ejemplos=["copiar backup.zip a /tmp/"],
            nivel_riesgo="bajo"
        )
        
        self.registrar_capacidad(
            nombre="eliminar_archivo",
            descripcion="Elimina archivos o carpetas (cuidado)",
            parametros=["ruta", "fuerza"],
            ejemplos=["borrar archivo temporal.txt"],
            nivel_riesgo="alto"
        )
        
        self.registrar_capacidad(
            nombre="buscar_archivos",
            descripcion="Busca archivos por nombre, tipo o contenido",
            parametros=["patron", "ruta", "tipo"],
            ejemplos=["buscar archivos .py", "encontrar todos los logs"],
            nivel_riesgo="bajo"
        )
        
        self.registrar_capacidad(
            nombre="comprimir",
            descripcion="Comprime archivos o carpetas (zip/tar.gz)",
            parametros=["origen", "destino", "formato"],
            ejemplos=["comprimir carpeta proyectos", "hacer zip de documentos"],
            nivel_riesgo="bajo"
        )
        
        self.registrar_capacidad(
            nombre="descomprimir",
            descripcion="Descomprime archivos zip, tar, gz",
            parametros=["archivo", "destino"],
            ejemplos=["descomprimir backup.zip", "extraer archivo.tar.gz"],
            nivel_riesgo="bajo"
        )
    
    async def ejecutar(self, tarea: Dict[str, Any]) -> ResultadoTarea:
        """
        Ejecuta una tarea de archivos según el tipo detectado
        """
        tipo = tarea.get("tipo", "")
        descripcion = tarea.get("descripcion", "")
        parametros = tarea.get("parametros", {})
        
        # Detectar capacidad por tipo o por descripción
        if tipo == "crear_carpeta" or "crear carpeta" in descripcion.lower() or "mkdir" in descripcion.lower():
            return await self._crear_carpeta(descripcion, parametros)
        
        elif tipo == "crear_archivo" or "crear archivo" in descripcion.lower() or "touch" in descripcion.lower():
            return await self._crear_archivo(descripcion, parametros)
        
        elif tipo == "leer_archivo" or "leer archivo" in descripcion.lower() or "cat" in descripcion.lower():
            return await self._leer_archivo(descripcion, parametros)
        
        elif tipo == "listar_archivos" or "listar" in descripcion.lower() or "ls" in descripcion.lower():
            return await self._listar_archivos(descripcion, parametros)
        
        elif tipo == "mover_archivo" or "mover" in descripcion.lower() or "mv" in descripcion.lower():
            return await self._mover_archivo(descripcion, parametros)
        
        elif tipo == "copiar_archivo" or "copiar" in descripcion.lower() or "cp" in descripcion.lower():
            return await self._copiar_archivo(descripcion, parametros)
        
        elif tipo == "eliminar_archivo" or "borrar" in descripcion.lower() or "eliminar" in descripcion.lower() or "rm" in descripcion.lower():
            return await self._eliminar_archivo(descripcion, parametros)
        
        elif tipo == "buscar_archivos" or "buscar" in descripcion.lower() or "find" in descripcion.lower():
            return await self._buscar_archivos(descripcion, parametros)
        
        else:
            return ResultadoTarea(
                exito=False,
                error=f"No sé cómo manejar: {tipo}. Usa: crear_carpeta, crear_archivo, leer_archivo, listar_archivos, mover_archivo, copiar_archivo, eliminar_archivo, buscar_archivos"
            )
    
    # ============================================================
    # IMPLEMENTACIÓN DE CAPACIDADES
    # ============================================================
    
    async def _crear_carpeta(self, descripcion: str, parametros: Dict) -> ResultadoTarea:
        """Crear una nueva carpeta"""
        # Extraer nombre
        nombre = parametros.get("nombre")
        if not nombre:
            match = re.search(r"(?:crear carpeta|crea carpeta|mkdir)\s+([^\s]+)", descripcion.lower())
            nombre = match.group(1) if match else "nueva_carpeta"
        
        ruta = Path(nombre)
        
        try:
            ruta.mkdir(exist_ok=True, parents=True)
            return ResultadoTarea(
                exito=True,
                datos={
                    "carpeta": str(ruta.absolute()),
                    "nombre": ruta.name,
                    "ruta": str(ruta.absolute())
                },
                metadatos={"operacion": "crear_carpeta"}
            )
        except Exception as e:
            return ResultadoTarea(exito=False, error=f"Error creando carpeta: {e}")
    
    async def _crear_archivo(self, descripcion: str, parametros: Dict) -> ResultadoTarea:
        """Crear un archivo con contenido opcional"""
        # Extraer nombre
        nombre = parametros.get("nombre")
        if not nombre:
            match = re.search(r"(?:crear archivo|crea archivo|touch)\s+([^\s]+)", descripcion.lower())
            nombre = match.group(1) if match else "archivo.txt"
        
        # Extraer contenido
        contenido = parametros.get("contenido", "")
        if not contenido and "contenido:" in descripcion:
            contenido = descripcion.split("contenido:")[-1].strip()
        
        ruta = Path(nombre)
        
        try:
            with open(ruta, 'w', encoding='utf-8') as f:
                f.write(contenido)
            
            return ResultadoTarea(
                exito=True,
                datos={
                    "archivo": str(ruta.absolute()),
                    "nombre": ruta.name,
                    "tamaño": len(contenido),
                    "contenido": contenido[:500] if contenido else None
                }
            )
        except Exception as e:
            return ResultadoTarea(exito=False, error=f"Error creando archivo: {e}")
    
    async def _leer_archivo(self, descripcion: str, parametros: Dict) -> ResultadoTarea:
        """Leer contenido de un archivo"""
        nombre = parametros.get("archivo")
        if not nombre:
            match = re.search(r"(?:leer archivo|cat|mostrar)\s+([^\s]+)", descripcion.lower())
            nombre = match.group(1) if match else None
        
        if not nombre:
            return ResultadoTarea(exito=False, error="No especificaste qué archivo leer")
        
        ruta = Path(nombre)
        
        if not ruta.exists():
            return ResultadoTarea(exito=False, error=f"El archivo {nombre} no existe")
        
        try:
            with open(ruta, 'r', encoding='utf-8') as f:
                contenido = f.read()
            
            return ResultadoTarea(
                exito=True,
                datos={
                    "archivo": str(ruta.absolute()),
                    "contenido": contenido,
                    "tamaño": len(contenido),
                    "lineas": len(contenido.splitlines())
                }
            )
        except Exception as e:
            return ResultadoTarea(exito=False, error=f"Error leyendo archivo: {e}")
    
    async def _listar_archivos(self, descripcion: str, parametros: Dict) -> ResultadoTarea:
        """Listar archivos en un directorio"""
        # Extraer directorio
        directorio = parametros.get("ruta", ".")
        detallado = parametros.get("detallado", False)
        
        # Si hay un path en la descripción
        match = re.search(r"(?:ls|listar)\s+([^\s]+)", descripcion.lower())
        if match and not parametros.get("ruta"):
            directorio = match.group(1)
        
        ruta = Path(directorio)
        
        if not ruta.exists():
            return ResultadoTarea(exito=False, error=f"El directorio {directorio} no existe")
        
        try:
            items = []
            for item in ruta.iterdir():
                info = {
                    "nombre": item.name,
                    "tipo": "carpeta" if item.is_dir() else "archivo",
                    "ruta": str(item.absolute())
                }
                if detallado:
                    stat = item.stat()
                    info["tamaño"] = stat.st_size
                    info["modificado"] = datetime.fromtimestamp(stat.st_mtime).isoformat()
                
                items.append(info)
            
            return ResultadoTarea(
                exito=True,
                datos={
                    "directorio": str(ruta.absolute()),
                    "items": items,
                    "total": len(items),
                    "carpetas": sum(1 for i in items if i["tipo"] == "carpeta"),
                    "archivos": sum(1 for i in items if i["tipo"] == "archivo")
                }
            )
        except Exception as e:
            return ResultadoTarea(exito=False, error=f"Error listando archivos: {e}")
    
    async def _mover_archivo(self, descripcion: str, parametros: Dict) -> ResultadoTarea:
        """Mover o renombrar archivos/carpetas"""
        origen = parametros.get("origen")
        destino = parametros.get("destino")
        
        if not origen or not destino:
            # Intentar extraer de descripción
            match = re.search(r"(?:mover|mv)\s+([^\s]+)\s+([^\s]+)", descripcion.lower())
            if match:
                origen, destino = match.groups()
        
        if not origen or not destino:
            return ResultadoTarea(exito=False, error="Necesito origen y destino")
        
        ruta_origen = Path(origen)
        ruta_destino = Path(destino)
        
        if not ruta_origen.exists():
            return ResultadoTarea(exito=False, error=f"No existe: {origen}")
        
        try:
            shutil.move(str(ruta_origen), str(ruta_destino))
            return ResultadoTarea(
                exito=True,
                datos={
                    "origen": str(ruta_origen.absolute()),
                    "destino": str(ruta_destino.absolute())
                }
            )
        except Exception as e:
            return ResultadoTarea(exito=False, error=f"Error moviendo: {e}")
    
    async def _copiar_archivo(self, descripcion: str, parametros: Dict) -> ResultadoTarea:
        """Copiar archivos o carpetas"""
        origen = parametros.get("origen")
        destino = parametros.get("destino")
        
        if not origen or not destino:
            match = re.search(r"(?:copiar|cp)\s+([^\s]+)\s+([^\s]+)", descripcion.lower())
            if match:
                origen, destino = match.groups()
        
        if not origen or not destino:
            return ResultadoTarea(exito=False, error="Necesito origen y destino")
        
        ruta_origen = Path(origen)
        ruta_destino = Path(destino)
        
        if not ruta_origen.exists():
            return ResultadoTarea(exito=False, error=f"No existe: {origen}")
        
        try:
            if ruta_origen.is_dir():
                shutil.copytree(ruta_origen, ruta_destino)
            else:
                shutil.copy2(ruta_origen, ruta_destino)
            
            return ResultadoTarea(
                exito=True,
                datos={
                    "origen": str(ruta_origen.absolute()),
                    "destino": str(ruta_destino.absolute())
                }
            )
        except Exception as e:
            return ResultadoTarea(exito=False, error=f"Error copiando: {e}")
    
    async def _eliminar_archivo(self, descripcion: str, parametros: Dict) -> ResultadoTarea:
        """Eliminar archivos o carpetas"""
        ruta = parametros.get("ruta")
        
        if not ruta:
            match = re.search(r"(?:borrar|eliminar|rm)\s+([^\s]+)", descripcion.lower())
            ruta = match.group(1) if match else None
        
        if not ruta:
            return ResultadoTarea(exito=False, error="¿Qué quieres eliminar?")
        
        ruta_path = Path(ruta)
        
        if not ruta_path.exists():
            return ResultadoTarea(exito=False, error=f"No existe: {ruta}")
        
        try:
            if ruta_path.is_dir():
                shutil.rmtree(ruta_path)
            else:
                ruta_path.unlink()
            
            return ResultadoTarea(
                exito=True,
                datos={"eliminado": str(ruta_path.absolute())}
            )
        except Exception as e:
            return ResultadoTarea(exito=False, error=f"Error eliminando: {e}")
    
    async def _buscar_archivos(self, descripcion: str, parametros: Dict) -> ResultadoTarea:
        """Buscar archivos por patrón"""
        patron = parametros.get("patron")
        ruta = parametros.get("ruta", ".")
        
        if not patron:
            match = re.search(r"(?:buscar|find)\s+([^\s]+)", descripcion.lower())
            patron = match.group(1) if match else None
        
        if not patron:
            return ResultadoTarea(exito=False, error="¿Qué quieres buscar?")
        
        ruta_path = Path(ruta)
        resultados = []
        
        try:
            for item in ruta_path.rglob(f"*{patron}*"):
                resultados.append({
                    "nombre": item.name,
                    "ruta": str(item.absolute()),
                    "tipo": "carpeta" if item.is_dir() else "archivo"
                })
                if len(resultados) > 100:
                    resultados.append({"mensaje": "Demasiados resultados, mostrando los primeros 100"})
                    break
            
            return ResultadoTarea(
                exito=True,
                datos={
                    "patron": patron,
                    "directorio": str(ruta_path.absolute()),
                    "resultados": resultados,
                    "total": len(resultados)
                }
            )
        except Exception as e:
            return ResultadoTarea(exito=False, error=f"Error buscando: {e}")


def crear_agente_archivos(supervisor, config) -> AgenteArchivos:
    """Factory para crear el agente de archivos"""
    return AgenteArchivos(supervisor, config)
