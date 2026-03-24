#!/usr/bin/env python3
"""
Agente Base de Datos - Conexión y gestión de bases de datos
Soporta: MySQL, PostgreSQL, SQLite, MongoDB
Capacidades: consultas, backups, monitoreo
"""

import os
import sys
import json
import sqlite3
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from pathlib import Path

# Importaciones opcionales por base de datos
try:
    import pymysql
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False

try:
    import psycopg2
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False

try:
    from pymongo import MongoClient
    MONGO_AVAILABLE = True
except ImportError:
    MONGO_AVAILABLE = False

from src.core.agente import Agente, TipoAgente, ResultadoTarea
from src.core.supervisor import Supervisor
from src.core.config import Config


class AgenteBaseDatos(Agente):
    """
    Agente Base de Datos - Gestiona conexiones y operaciones con BD
    Soporta: MySQL, PostgreSQL, SQLite, MongoDB
    """
    
    def __init__(self, supervisor: Supervisor, config: Config):
        super().__init__(
            id_agente="base_datos",
            nombre="Agente Base de Datos",
            tipo=TipoAgente.BASE_DATOS,
            supervisor=supervisor,
            version="1.0.0"
        )
        self.config = config
        
        # Conexiones activas
        self.conexiones: Dict[str, Any] = {}
        
        # Directorio para backups
        self.backup_dir = Path("data/backups/bd")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        self._registrar_capacidades()
        self._mostrar_disponibilidad()
        self.logger.info("Agente Base de Datos iniciado")
    
    def _mostrar_disponibilidad(self):
        """Mostrar qué bases de datos están disponibles"""
        self.logger.info("Disponibilidad de drivers:")
        self.logger.info(f"  MySQL: {'✅' if MYSQL_AVAILABLE else '❌ (pip install pymysql)'}")
        self.logger.info(f"  PostgreSQL: {'✅' if POSTGRES_AVAILABLE else '❌ (pip install psycopg2-binary)'}")
        self.logger.info(f"  MongoDB: {'✅' if MONGO_AVAILABLE else '❌ (pip install pymongo)'}")
        self.logger.info(f"  SQLite: ✅ (incluido)")
    
    def _registrar_capacidades(self):
        """Registrar capacidades del agente"""
        
        self.registrar_capacidad(
            nombre="bd_conectar",
            descripcion="Conectar a una base de datos",
            parametros=["tipo", "host", "puerto", "usuario", "password", "base"],
            ejemplos=[
                "conectar a MySQL en localhost con usuario root",
                "conectar a PostgreSQL en servidor.com"
            ],
            nivel_riesgo="medio"
        )
        
        self.registrar_capacidad(
            nombre="bd_consulta",
            descripcion="Ejecutar una consulta SQL",
            parametros=["conexion", "consulta"],
            ejemplos=["ejecutar SELECT * FROM usuarios", "consultar tabla productos"],
            nivel_riesgo="alto"
        )
        
        self.registrar_capacidad(
            nombre="bd_insertar",
            descripcion="Insertar datos en una tabla",
            parametros=["conexion", "tabla", "datos"],
            ejemplos=["insertar usuario con nombre Juan", "agregar producto a inventario"],
            nivel_riesgo="alto"
        )
        
        self.registrar_capacidad(
            nombre="bd_actualizar",
            descripcion="Actualizar datos en una tabla",
            parametros=["conexion", "tabla", "datos", "condicion"],
            ejemplos=["actualizar precio del producto 123", "cambiar estado de usuario"],
            nivel_riesgo="alto"
        )
        
        self.registrar_capacidad(
            nombre="bd_eliminar",
            descripcion="Eliminar datos de una tabla",
            parametros=["conexion", "tabla", "condicion"],
            ejemplos=["eliminar usuario inactivo", "borrar registros antiguos"],
            nivel_riesgo="critico"
        )
        
        self.registrar_capacidad(
            nombre="bd_backup",
            descripcion="Crear backup de la base de datos",
            parametros=["conexion", "destino"],
            ejemplos=["backup de la base de datos", "respaldar BD"],
            nivel_riesgo="medio"
        )
        
        self.registrar_capacidad(
            nombre="bd_restaurar",
            descripcion="Restaurar backup de base de datos",
            parametros=["conexion", "archivo"],
            ejemplos=["restaurar backup de ayer", "recuperar BD desde archivo"],
            nivel_riesgo="critico"
        )
        
        self.registrar_capacidad(
            nombre="bd_tablas",
            descripcion="Listar tablas de la base de datos",
            parametros=["conexion"],
            ejemplos=["listar tablas", "qué tablas hay"],
            nivel_riesgo="bajo"
        )
        
        self.registrar_capacidad(
            nombre="bd_esquema",
            descripcion="Ver estructura de una tabla",
            parametros=["conexion", "tabla"],
            ejemplos=["ver estructura de usuarios", "esquema de productos"],
            nivel_riesgo="bajo"
        )
    
    async def ejecutar(self, tarea: Dict[str, Any]) -> ResultadoTarea:
        """Ejecuta tarea según tipo"""
        tipo = tarea.get("tipo", "")
        desc = tarea.get("descripcion", "").lower()
        parametros = tarea.get("parametros", {})
        
        if "bd_conectar" in tipo or "conectar" in desc:
            return await self._conectar(desc, parametros)
        
        elif "bd_consulta" in tipo or "consulta" in desc or "select" in desc:
            return await self._consulta(desc, parametros)
        
        elif "bd_insertar" in tipo or "insertar" in desc:
            return await self._insertar(desc, parametros)
        
        elif "bd_actualizar" in tipo or "actualizar" in desc or "update" in desc:
            return await self._actualizar(desc, parametros)
        
        elif "bd_eliminar" in tipo or "eliminar" in desc or "delete" in desc:
            return await self._eliminar(desc, parametros)
        
        elif "bd_backup" in tipo or "backup" in desc:
            return await self._backup(desc, parametros)
        
        elif "bd_restaurar" in tipo or "restaurar" in desc:
            return await self._restaurar(desc, parametros)
        
        elif "bd_tablas" in tipo or "listar tablas" in desc:
            return await self._listar_tablas(desc, parametros)
        
        elif "bd_esquema" in tipo or "estructura" in desc:
            return await self._esquema(desc, parametros)
        
        else:
            return ResultadoTarea(exito=False, error=f"No sé cómo manejar: {tipo}")
    
    # ============================================================
    # CONEXIÓN
    # ============================================================
    
    async def _conectar(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Conectar a una base de datos"""
        tipo = parametros.get("tipo") or self._extraer_tipo(desc)
        nombre_conexion = parametros.get("nombre", "default")
        
        if not tipo:
            return ResultadoTarea(exito=False, error="Especifica el tipo de BD (mysql, postgres, sqlite, mongodb)")
        
        if tipo == "sqlite":
            ruta = parametros.get("ruta") or self._extraer_ruta(desc, "data/db.sqlite")
            try:
                conn = sqlite3.connect(ruta)
                self.conexiones[nombre_conexion] = {
                    "tipo": "sqlite",
                    "conexion": conn,
                    "ruta": ruta
                }
                return ResultadoTarea(
                    exito=True,
                    datos={"tipo": "sqlite", "ruta": ruta, "mensaje": f"Conectado a SQLite: {ruta}"}
                )
            except Exception as e:
                return ResultadoTarea(exito=False, error=str(e))
        
        elif tipo == "mysql":
            if not MYSQL_AVAILABLE:
                return ResultadoTarea(exito=False, error="MySQL no disponible. Instalar: pip install pymysql")
            
            host = parametros.get("host") or self._extraer_host(desc, "localhost")
            puerto = parametros.get("puerto", 3306)
            usuario = parametros.get("usuario") or self._extraer_usuario(desc, "root")
            password = parametros.get("password")
            base = parametros.get("base") or self._extraer_base(desc)
            
            try:
                conn = pymysql.connect(
                    host=host,
                    port=puerto,
                    user=usuario,
                    password=password,
                    database=base,
                    charset='utf8mb4'
                )
                self.conexiones[nombre_conexion] = {
                    "tipo": "mysql",
                    "conexion": conn,
                    "host": host,
                    "puerto": puerto,
                    "usuario": usuario,
                    "base": base
                }
                return ResultadoTarea(
                    exito=True,
                    datos={"tipo": "mysql", "host": host, "base": base, "mensaje": f"Conectado a MySQL: {host}:{puerto}/{base}"}
                )
            except Exception as e:
                return ResultadoTarea(exito=False, error=str(e))
        
        elif tipo == "postgres" or tipo == "postgresql":
            if not POSTGRES_AVAILABLE:
                return ResultadoTarea(exito=False, error="PostgreSQL no disponible. Instalar: pip install psycopg2-binary")
            
            host = parametros.get("host") or self._extraer_host(desc, "localhost")
            puerto = parametros.get("puerto", 5432)
            usuario = parametros.get("usuario") or self._extraer_usuario(desc, "postgres")
            password = parametros.get("password")
            base = parametros.get("base") or self._extraer_base(desc)
            
            try:
                conn = psycopg2.connect(
                    host=host,
                    port=puerto,
                    user=usuario,
                    password=password,
                    dbname=base
                )
                self.conexiones[nombre_conexion] = {
                    "tipo": "postgres",
                    "conexion": conn,
                    "host": host,
                    "puerto": puerto,
                    "usuario": usuario,
                    "base": base
                }
                return ResultadoTarea(
                    exito=True,
                    datos={"tipo": "postgres", "host": host, "base": base, "mensaje": f"Conectado a PostgreSQL: {host}:{puerto}/{base}"}
                )
            except Exception as e:
                return ResultadoTarea(exito=False, error=str(e))
        
        elif tipo == "mongodb":
            if not MONGO_AVAILABLE:
                return ResultadoTarea(exito=False, error="MongoDB no disponible. Instalar: pip install pymongo")
            
            host = parametros.get("host") or self._extraer_host(desc, "localhost")
            puerto = parametros.get("puerto", 27017)
            base = parametros.get("base") or self._extraer_base(desc)
            
            try:
                client = MongoClient(f"mongodb://{host}:{puerto}/")
                db = client[base]
                self.conexiones[nombre_conexion] = {
                    "tipo": "mongodb",
                    "conexion": client,
                    "db": db,
                    "host": host,
                    "puerto": puerto,
                    "base": base
                }
                return ResultadoTarea(
                    exito=True,
                    datos={"tipo": "mongodb", "host": host, "base": base, "mensaje": f"Conectado a MongoDB: {host}:{puerto}/{base}"}
                )
            except Exception as e:
                return ResultadoTarea(exito=False, error=str(e))
        
        else:
            return ResultadoTarea(exito=False, error=f"Tipo de BD no soportado: {tipo}")
    
    # ============================================================
    # CONSULTAS
    # ============================================================
    
    async def _consulta(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Ejecutar consulta SQL"""
        conexion_nombre = parametros.get("conexion", "default")
        consulta = parametros.get("consulta") or self._extraer_consulta(desc)
        
        if not consulta:
            return ResultadoTarea(exito=False, error="Especifica la consulta a ejecutar")
        
        if conexion_nombre not in self.conexiones:
            return ResultadoTarea(exito=False, error=f"No hay conexión activa: {conexion_nombre}")
        
        conn_info = self.conexiones[conexion_nombre]
        
        try:
            if conn_info["tipo"] == "sqlite":
                cursor = conn_info["conexion"].cursor()
                cursor.execute(consulta)
                resultados = cursor.fetchall()
                columnas = [description[0] for description in cursor.description] if cursor.description else []
                return ResultadoTarea(
                    exito=True,
                    datos={
                        "columnas": columnas,
                        "filas": len(resultados),
                        "resultados": [dict(zip(columnas, row)) for row in resultados] if columnas else resultados
                    }
                )
            
            elif conn_info["tipo"] == "mysql":
                cursor = conn_info["conexion"].cursor(pymysql.cursors.DictCursor)
                cursor.execute(consulta)
                if consulta.strip().upper().startswith("SELECT"):
                    resultados = cursor.fetchall()
                    return ResultadoTarea(
                        exito=True,
                        datos={
                            "columnas": list(resultados[0].keys()) if resultados else [],
                            "filas": len(resultados),
                            "resultados": resultados
                        }
                    )
                else:
                    conn_info["conexion"].commit()
                    return ResultadoTarea(
                        exito=True,
                        datos={"afectadas": cursor.rowcount, "mensaje": f"{cursor.rowcount} filas afectadas"}
                    )
            
            elif conn_info["tipo"] == "postgres":
                cursor = conn_info["conexion"].cursor()
                cursor.execute(consulta)
                if consulta.strip().upper().startswith("SELECT"):
                    columnas = [desc[0] for desc in cursor.description]
                    resultados = cursor.fetchall()
                    return ResultadoTarea(
                        exito=True,
                        datos={
                            "columnas": columnas,
                            "filas": len(resultados),
                            "resultados": [dict(zip(columnas, row)) for row in resultados]
                        }
                    )
                else:
                    conn_info["conexion"].commit()
                    return ResultadoTarea(
                        exito=True,
                        datos={"afectadas": cursor.rowcount}
                    )
            
            elif conn_info["tipo"] == "mongodb":
                # Para MongoDB, la consulta es diferente
                return ResultadoTarea(exito=False, error="Para MongoDB usa consultas específicas")
            
        except Exception as e:
            return ResultadoTarea(exito=False, error=str(e))
    
    async def _insertar(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Insertar datos en una tabla"""
        conexion_nombre = parametros.get("conexion", "default")
        tabla = parametros.get("tabla") or self._extraer_tabla(desc)
        datos = parametros.get("datos", {})
        
        if not tabla:
            return ResultadoTarea(exito=False, error="Especifica la tabla")
        
        if not datos:
            datos = self._extraer_datos(desc)
        
        if not datos:
            return ResultadoTarea(exito=False, error="Especifica los datos a insertar")
        
        if conexion_nombre not in self.conexiones:
            return ResultadoTarea(exito=False, error=f"No hay conexión activa: {conexion_nombre}")
        
        conn_info = self.conexiones[conexion_nombre]
        
        try:
            columnas = ", ".join(datos.keys())
            placeholders = ", ".join(["%s"] * len(datos))
            consulta = f"INSERT INTO {tabla} ({columnas}) VALUES ({placeholders})"
            valores = list(datos.values())
            
            if conn_info["tipo"] == "sqlite":
                cursor = conn_info["conexion"].cursor()
                cursor.execute(consulta, valores)
                conn_info["conexion"].commit()
                return ResultadoTarea(
                    exito=True,
                    datos={"id": cursor.lastrowid, "mensaje": "Registro insertado correctamente"}
                )
            
            elif conn_info["tipo"] == "mysql":
                cursor = conn_info["conexion"].cursor()
                cursor.execute(consulta, valores)
                conn_info["conexion"].commit()
                return ResultadoTarea(
                    exito=True,
                    datos={"id": cursor.lastrowid, "mensaje": "Registro insertado correctamente"}
                )
            
            elif conn_info["tipo"] == "postgres":
                cursor = conn_info["conexion"].cursor()
                cursor.execute(consulta, valores)
                conn_info["conexion"].commit()
                return ResultadoTarea(
                    exito=True,
                    datos={"id": cursor.lastrowid if hasattr(cursor, 'lastrowid') else None}
                )
            
        except Exception as e:
            return ResultadoTarea(exito=False, error=str(e))
    
    async def _actualizar(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Actualizar datos en una tabla"""
        conexion_nombre = parametros.get("conexion", "default")
        tabla = parametros.get("tabla") or self._extraer_tabla(desc)
        datos = parametros.get("datos", {})
        condicion = parametros.get("condicion") or self._extraer_condicion(desc)
        
        if not tabla:
            return ResultadoTarea(exito=False, error="Especifica la tabla")
        
        if not datos:
            datos = self._extraer_datos(desc)
        
        if not condicion:
            return ResultadoTarea(exito=False, error="Especifica la condición (WHERE)")
        
        if conexion_nombre not in self.conexiones:
            return ResultadoTarea(exito=False, error=f"No hay conexión activa: {conexion_nombre}")
        
        try:
            set_clause = ", ".join([f"{k} = %s" for k in datos.keys()])
            consulta = f"UPDATE {tabla} SET {set_clause} WHERE {condicion}"
            valores = list(datos.values())
            
            conn_info = self.conexiones[conexion_nombre]
            
            if conn_info["tipo"] == "sqlite":
                cursor = conn_info["conexion"].cursor()
                cursor.execute(consulta, valores)
                conn_info["conexion"].commit()
                return ResultadoTarea(
                    exito=True,
                    datos={"afectadas": cursor.rowcount, "mensaje": f"{cursor.rowcount} filas actualizadas"}
                )
            
            elif conn_info["tipo"] == "mysql":
                cursor = conn_info["conexion"].cursor()
                cursor.execute(consulta, valores)
                conn_info["conexion"].commit()
                return ResultadoTarea(
                    exito=True,
                    datos={"afectadas": cursor.rowcount}
                )
            
        except Exception as e:
            return ResultadoTarea(exito=False, error=str(e))
    
    async def _eliminar(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Eliminar datos de una tabla"""
        conexion_nombre = parametros.get("conexion", "default")
        tabla = parametros.get("tabla") or self._extraer_tabla(desc)
        condicion = parametros.get("condicion") or self._extraer_condicion(desc)
        
        if not tabla:
            return ResultadoTarea(exito=False, error="Especifica la tabla")
        
        if not condicion:
            return ResultadoTarea(exito=False, error="Especifica la condición (WHERE)")
        
        if conexion_nombre not in self.conexiones:
            return ResultadoTarea(exito=False, error=f"No hay conexión activa: {conexion_nombre}")
        
        try:
            consulta = f"DELETE FROM {tabla} WHERE {condicion}"
            conn_info = self.conexiones[conexion_nombre]
            
            if conn_info["tipo"] == "sqlite":
                cursor = conn_info["conexion"].cursor()
                cursor.execute(consulta)
                conn_info["conexion"].commit()
                return ResultadoTarea(
                    exito=True,
                    datos={"afectadas": cursor.rowcount, "mensaje": f"{cursor.rowcount} filas eliminadas"}
                )
            
            elif conn_info["tipo"] == "mysql":
                cursor = conn_info["conexion"].cursor()
                cursor.execute(consulta)
                conn_info["conexion"].commit()
                return ResultadoTarea(
                    exito=True,
                    datos={"afectadas": cursor.rowcount}
                )
            
        except Exception as e:
            return ResultadoTarea(exito=False, error=str(e))
    
    # ============================================================
    # BACKUP Y RESTAURAR
    # ============================================================
    
    async def _backup(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Crear backup de la base de datos"""
        conexion_nombre = parametros.get("conexion", "default")
        
        if conexion_nombre not in self.conexiones:
            return ResultadoTarea(exito=False, error=f"No hay conexión activa: {conexion_nombre}")
        
        conn_info = self.conexiones[conexion_nombre]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archivo = self.backup_dir / f"{conn_info['tipo']}_{conn_info.get('base', 'db')}_{timestamp}.sql"
        
        try:
            if conn_info["tipo"] == "sqlite":
                # Para SQLite, copiar archivo
                import shutil
                origen = conn_info["ruta"]
                shutil.copy2(origen, archivo)
                return ResultadoTarea(
                    exito=True,
                    datos={"archivo": str(archivo), "tamaño": archivo.stat().st_size}
                )
            
            elif conn_info["tipo"] == "mysql":
                # Usar mysqldump
                import subprocess
                cmd = f"mysqldump -h {conn_info['host']} -P {conn_info['puerto']} -u {conn_info['usuario']} {conn_info['base']} > {archivo}"
                if conn_info.get('password'):
                    os.environ['MYSQL_PWD'] = conn_info['password']
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                return ResultadoTarea(
                    exito=result.returncode == 0,
                    datos={"archivo": str(archivo), "salida": result.stdout[:500]}
                )
            
            else:
                return ResultadoTarea(
                    exito=False,
                    error=f"Backup no implementado para {conn_info['tipo']}"
                )
                
        except Exception as e:
            return ResultadoTarea(exito=False, error=str(e))
    
    async def _restaurar(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Restaurar backup"""
        archivo = parametros.get("archivo") or self._extraer_archivo(desc)
        conexion_nombre = parametros.get("conexion", "default")
        
        if not archivo:
            return ResultadoTarea(exito=False, error="Especifica el archivo de backup")
        
        archivo_path = Path(archivo)
        if not archivo_path.exists():
            return ResultadoTarea(exito=False, error=f"Archivo no encontrado: {archivo}")
        
        if conexion_nombre not in self.conexiones:
            return ResultadoTarea(exito=False, error=f"No hay conexión activa: {conexion_nombre}")
        
        conn_info = self.conexiones[conexion_nombre]
        
        try:
            if conn_info["tipo"] == "sqlite":
                import shutil
                shutil.copy2(archivo_path, conn_info["ruta"])
                return ResultadoTarea(exito=True, datos={"mensaje": f"Restaurado desde {archivo}"})
            
            elif conn_info["tipo"] == "mysql":
                import subprocess
                cmd = f"mysql -h {conn_info['host']} -P {conn_info['puerto']} -u {conn_info['usuario']} {conn_info['base']} < {archivo}"
                if conn_info.get('password'):
                    os.environ['MYSQL_PWD'] = conn_info['password']
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                return ResultadoTarea(
                    exito=result.returncode == 0,
                    datos={"mensaje": "Restaurado correctamente"}
                )
            
        except Exception as e:
            return ResultadoTarea(exito=False, error=str(e))
    
    # ============================================================
    # METADATOS
    # ============================================================
    
    async def _listar_tablas(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Listar tablas de la base de datos"""
        conexion_nombre = parametros.get("conexion", "default")
        
        if conexion_nombre not in self.conexiones:
            return ResultadoTarea(exito=False, error=f"No hay conexión activa: {conexion_nombre}")
        
        conn_info = self.conexiones[conexion_nombre]
        
        try:
            if conn_info["tipo"] == "sqlite":
                cursor = conn_info["conexion"].cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tablas = [row[0] for row in cursor.fetchall()]
                return ResultadoTarea(exito=True, datos={"tablas": tablas})
            
            elif conn_info["tipo"] == "mysql":
                cursor = conn_info["conexion"].cursor()
                cursor.execute("SHOW TABLES")
                tablas = [row[0] for row in cursor.fetchall()]
                return ResultadoTarea(exito=True, datos={"tablas": tablas})
            
            elif conn_info["tipo"] == "postgres":
                cursor = conn_info["conexion"].cursor()
                cursor.execute("SELECT tablename FROM pg_tables WHERE schemaname='public'")
                tablas = [row[0] for row in cursor.fetchall()]
                return ResultadoTarea(exito=True, datos={"tablas": tablas})
            
        except Exception as e:
            return ResultadoTarea(exito=False, error=str(e))
    
    async def _esquema(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Ver estructura de una tabla"""
        conexion_nombre = parametros.get("conexion", "default")
        tabla = parametros.get("tabla") or self._extraer_tabla(desc)
        
        if not tabla:
            return ResultadoTarea(exito=False, error="Especifica la tabla")
        
        if conexion_nombre not in self.conexiones:
            return ResultadoTarea(exito=False, error=f"No hay conexión activa: {conexion_nombre}")
        
        conn_info = self.conexiones[conexion_nombre]
        
        try:
            if conn_info["tipo"] == "sqlite":
                cursor = conn_info["conexion"].cursor()
                cursor.execute(f"PRAGMA table_info({tabla})")
                columnas = [{"nombre": row[1], "tipo": row[2], "nullable": not row[3], "pk": row[5]} for row in cursor.fetchall()]
                return ResultadoTarea(exito=True, datos={"tabla": tabla, "columnas": columnas})
            
            elif conn_info["tipo"] == "mysql":
                cursor = conn_info["conexion"].cursor()
                cursor.execute(f"DESCRIBE {tabla}")
                columnas = [{"campo": row[0], "tipo": row[1], "null": row[2], "key": row[3], "default": row[4], "extra": row[5]} for row in cursor.fetchall()]
                return ResultadoTarea(exito=True, datos={"tabla": tabla, "columnas": columnas})
            
        except Exception as e:
            return ResultadoTarea(exito=False, error=str(e))
    
    # ============================================================
    # EXTRACTORES
    # ============================================================
    
    def _extraer_tipo(self, desc: str) -> Optional[str]:
        if "mysql" in desc:
            return "mysql"
        elif "postgres" in desc or "postgresql" in desc:
            return "postgres"
        elif "sqlite" in desc:
            return "sqlite"
        elif "mongo" in desc:
            return "mongodb"
        return None
    
    def _extraer_host(self, desc: str, default: str = "localhost") -> str:
        import re
        match = re.search(r'host[:\s]+([^\s]+)', desc)
        return match.group(1) if match else default
    
    def _extraer_usuario(self, desc: str, default: str = "root") -> str:
        import re
        match = re.search(r'usuario[:\s]+([^\s]+)', desc)
        return match.group(1) if match else default
    
    def _extraer_base(self, desc: str) -> Optional[str]:
        import re
        match = re.search(r'base[:\s]+([^\s]+)', desc)
        return match.group(1) if match else None
    
    def _extraer_tabla(self, desc: str) -> Optional[str]:
        import re
        match = re.search(r'tabla[:\s]+([^\s]+)', desc)
        return match.group(1) if match else None
    
    def _extraer_consulta(self, desc: str) -> Optional[str]:
        import re
        match = re.search(r'consulta[:\s]+(.+)', desc)
        if match:
            return match.group(1)
        if "select" in desc.lower():
            return desc
        return None
    
    def _extraer_datos(self, desc: str) -> Dict:
        import re
        datos = {}
        match = re.search(r'con datos[:\s]+(.+)', desc)
        if match:
            try:
                return json.loads(match.group(1))
            except:
                pass
        return datos
    
    def _extraer_condicion(self, desc: str) -> Optional[str]:
        import re
        match = re.search(r'donde[:\s]+(.+)', desc)
        return match.group(1) if match else None
    
    def _extraer_ruta(self, desc: str, default: str) -> str:
        import re
        match = re.search(r'ruta[:\s]+([^\s]+)', desc)
        return match.group(1) if match else default
    
    def _extraer_archivo(self, desc: str) -> Optional[str]:
        import re
        match = re.search(r'archivo[:\s]+([^\s]+)', desc)
        return match.group(1) if match else None


# ============================================================
# Factory Function
# ============================================================

def crear_agente_base_datos(supervisor: Supervisor, config: Config) -> AgenteBaseDatos:
    """Crea instancia del agente de base de datos"""
    return AgenteBaseDatos(supervisor, config)
