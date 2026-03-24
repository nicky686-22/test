#!/usr/bin/env python3
"""
Agente Cloud - Gestión de almacenamiento en la nube
Soporta: AWS S3, Google Drive, Dropbox
Capacidades: subir, descargar, listar, sincronizar, backups
"""

import os
import sys
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import mimetypes

# Importaciones opcionales
try:
    import boto3
    from botocore.exceptions import ClientError
    AWS_AVAILABLE = True
except ImportError:
    AWS_AVAILABLE = False

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

try:
    import dropbox
    DROPBOX_AVAILABLE = True
except ImportError:
    DROPBOX_AVAILABLE = False

from src.core.agente import Agente, TipoAgente, ResultadoTarea
from src.core.supervisor import Supervisor
from src.core.config import Config


class AgenteCloud(Agente):
    """
    Agente Cloud - Gestión de almacenamiento en la nube
    Soporta: AWS S3, Google Drive, Dropbox
    """
    
    def __init__(self, supervisor: Supervisor, config: Config):
        super().__init__(
            id_agente="cloud",
            nombre="Agente Cloud",
            tipo=TipoAgente.CLOUD,
            supervisor=supervisor,
            version="1.0.0"
        )
        self.config = config
        
        # Clientes cloud
        self.s3_client = None
        self.s3_bucket = None
        self.drive_service = None
        self.dropbox_client = None
        
        # Directorio para archivos temporales
        self.temp_dir = Path("/tmp/swarmia_cloud")
        self.temp_dir.mkdir(exist_ok=True)
        
        # Cargar configuraciones
        self._cargar_configuraciones()
        
        self._registrar_capacidades()
        self._mostrar_disponibilidad()
        self.logger.info("Agente Cloud iniciado")
    
    def _cargar_configuraciones(self):
        """Cargar configuraciones de servicios cloud desde .env"""
        
        # AWS S3
        if AWS_AVAILABLE:
            aws_key = os.getenv("AWS_ACCESS_KEY_ID", "")
            aws_secret = os.getenv("AWS_SECRET_ACCESS_KEY", "")
            self.s3_bucket = os.getenv("AWS_BUCKET", "")
            
            if aws_key and aws_secret:
                try:
                    self.s3_client = boto3.client(
                        's3',
                        aws_access_key_id=aws_key,
                        aws_secret_access_key=aws_secret,
                        region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1")
                    )
                    self.logger.info("AWS S3 configurado")
                except Exception as e:
                    self.logger.error(f"Error configurando AWS: {e}")
        
        # Google Drive
        if GOOGLE_AVAILABLE:
            creds_file = os.getenv("GOOGLE_CREDENTIALS_FILE", "")
            if creds_file and Path(creds_file).exists():
                try:
                    credentials = service_account.Credentials.from_service_account_file(
                        creds_file,
                        scopes=['https://www.googleapis.com/auth/drive']
                    )
                    self.drive_service = build('drive', 'v3', credentials=credentials)
                    self.logger.info("Google Drive configurado")
                except Exception as e:
                    self.logger.error(f"Error configurando Google Drive: {e}")
        
        # Dropbox
        if DROPBOX_AVAILABLE:
            dropbox_token = os.getenv("DROPBOX_ACCESS_TOKEN", "")
            if dropbox_token:
                try:
                    self.dropbox_client = dropbox.Dropbox(dropbox_token)
                    self.logger.info("Dropbox configurado")
                except Exception as e:
                    self.logger.error(f"Error configurando Dropbox: {e}")
    
    def _mostrar_disponibilidad(self):
        """Mostrar qué servicios cloud están disponibles"""
        self.logger.info("Servicios cloud disponibles:")
        self.logger.info(f"  AWS S3: {'✅' if self.s3_client else '❌ (pip install boto3)'}")
        self.logger.info(f"  Google Drive: {'✅' if self.drive_service else '❌ (pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib)'}")
        self.logger.info(f"  Dropbox: {'✅' if self.dropbox_client else '❌ (pip install dropbox)'}")
    
    def _registrar_capacidades(self):
        """Registrar capacidades del agente"""
        
        self.registrar_capacidad(
            nombre="cloud_subir",
            descripcion="Subir archivo a la nube",
            parametros=["servicio", "archivo", "destino"],
            ejemplos=["subir backup.tar.gz a S3", "subir foto a Google Drive", "upload archivo a Dropbox"],
            nivel_riesgo="bajo"
        )
        
        self.registrar_capacidad(
            nombre="cloud_descargar",
            descripcion="Descargar archivo desde la nube",
            parametros=["servicio", "origen", "destino"],
            ejemplos=["descargar archivo de S3", "obtener foto de Google Drive"],
            nivel_riesgo="bajo"
        )
        
        self.registrar_capacidad(
            nombre="cloud_listar",
            descripcion="Listar archivos en la nube",
            parametros=["servicio", "ruta"],
            ejemplos=["listar archivos en S3", "ver contenido de Google Drive"],
            nivel_riesgo="bajo"
        )
        
        self.registrar_capacidad(
            nombre="cloud_eliminar",
            descripcion="Eliminar archivo de la nube",
            parametros=["servicio", "ruta"],
            ejemplos=["eliminar archivo de S3", "borrar de Dropbox"],
            nivel_riesgo="medio"
        )
        
        self.registrar_capacidad(
            nombre="cloud_sincronizar",
            descripcion="Sincronizar carpeta local con la nube",
            parametros=["servicio", "local", "remoto"],
            ejemplos=["sincronizar backups con S3", "sync carpeta con Google Drive"],
            nivel_riesgo="bajo"
        )
        
        self.registrar_capacidad(
            nombre="cloud_backup",
            descripcion="Crear backup en la nube",
            parametros=["servicio", "archivo", "nombre"],
            ejemplos=["backup de base de datos a S3", "respaldar archivo en Dropbox"],
            nivel_riesgo="bajo"
        )
        
        self.registrar_capacidad(
            nombre="cloud_servicios",
            descripcion="Listar servicios cloud configurados",
            ejemplos=["qué servicios cloud tengo", "listar cloud disponibles"],
            nivel_riesgo="bajo"
        )
    
    async def ejecutar(self, tarea: Dict[str, Any]) -> ResultadoTarea:
        """Ejecuta tarea según tipo"""
        tipo = tarea.get("tipo", "")
        desc = tarea.get("descripcion", "").lower()
        parametros = tarea.get("parametros", {})
        
        if "cloud_subir" in tipo or "subir" in desc or "upload" in desc:
            return await self._subir(desc, parametros)
        
        elif "cloud_descargar" in tipo or "descargar" in desc or "download" in desc:
            return await self._descargar(desc, parametros)
        
        elif "cloud_listar" in tipo or "listar" in desc:
            return await self._listar(desc, parametros)
        
        elif "cloud_eliminar" in tipo or "eliminar" in desc or "borrar" in desc:
            return await self._eliminar(desc, parametros)
        
        elif "cloud_sincronizar" in tipo or "sincronizar" in desc or "sync" in desc:
            return await self._sincronizar(desc, parametros)
        
        elif "cloud_backup" in tipo or "backup" in desc:
            return await self._backup(desc, parametros)
        
        elif "cloud_servicios" in tipo:
            return await self._listar_servicios()
        
        else:
            return ResultadoTarea(exito=False, error=f"No sé cómo manejar: {tipo}")
    
    # ============================================================
    # UTILIDADES
    # ============================================================
    
    def _detectar_servicio(self, desc: str) -> Optional[str]:
        """Detectar qué servicio cloud usar"""
        if "s3" in desc or "aws" in desc:
            return "s3"
        elif "google" in desc or "drive" in desc or "gdrive" in desc:
            return "google"
        elif "dropbox" in desc:
            return "dropbox"
        return None
    
    def _extraer_archivo(self, desc: str) -> Optional[str]:
        """Extraer nombre de archivo de la descripción"""
        import re
        match = re.search(r'(?:archivo|file)[:\s]+([^\s]+)', desc, re.IGNORECASE)
        if match:
            return match.group(1)
        
        match = re.search(r'([\w\-\.\/]+\.\w+)', desc)
        if match:
            return match.group(1)
        
        return None
    
    def _extraer_destino(self, desc: str) -> Optional[str]:
        """Extraer destino de la descripción"""
        import re
        match = re.search(r'(?:destino|to)[:\s]+([^\s]+)', desc, re.IGNORECASE)
        if match:
            return match.group(1)
        return None
    
    def _extraer_ruta_remota(self, desc: str) -> Optional[str]:
        """Extraer ruta remota de la descripción"""
        import re
        match = re.search(r'(?:ruta|path)[:\s]+([^\s]+)', desc, re.IGNORECASE)
        if match:
            return match.group(1)
        
        # Para S3: bucket/key
        match = re.search(r's3://([^\s]+)', desc)
        if match:
            return match.group(1)
        
        return None
    
    # ============================================================
    # AWS S3
    # ============================================================
    
    async def _s3_subir(self, archivo: str, destino: str = None) -> Dict:
        """Subir archivo a S3"""
        if not self.s3_client:
            return {"exito": False, "error": "AWS S3 no configurado"}
        
        if not destino:
            destino = os.path.basename(archivo)
        
        bucket = self.s3_bucket
        if not bucket:
            return {"exito": False, "error": "AWS_BUCKET no configurado"}
        
        try:
            self.logger.info(f"Subiendo {archivo} a S3://{bucket}/{destino}")
            
            # Detectar tipo MIME
            mime_type, _ = mimetypes.guess_type(archivo)
            if not mime_type:
                mime_type = 'application/octet-stream'
            
            self.s3_client.upload_file(
                archivo, bucket, destino,
                ExtraArgs={'ContentType': mime_type}
            )
            
            return {
                "exito": True,
                "servicio": "s3",
                "archivo": archivo,
                "destino": f"s3://{bucket}/{destino}",
                "tamaño": Path(archivo).stat().st_size
            }
        except Exception as e:
            return {"exito": False, "error": str(e)}
    
    async def _s3_descargar(self, origen: str, destino: str) -> Dict:
        """Descargar archivo desde S3"""
        if not self.s3_client:
            return {"exito": False, "error": "AWS S3 no configurado"}
        
        bucket = self.s3_bucket
        if not bucket:
            return {"exito": False, "error": "AWS_BUCKET no configurado"}
        
        try:
            self.logger.info(f"Descargando S3://{bucket}/{origen} -> {destino}")
            self.s3_client.download_file(bucket, origen, destino)
            
            return {
                "exito": True,
                "servicio": "s3",
                "origen": f"s3://{bucket}/{origen}",
                "destino": destino
            }
        except Exception as e:
            return {"exito": False, "error": str(e)}
    
    async def _s3_listar(self, prefix: str = "") -> Dict:
        """Listar archivos en S3"""
        if not self.s3_client:
            return {"exito": False, "error": "AWS S3 no configurado"}
        
        bucket = self.s3_bucket
        if not bucket:
            return {"exito": False, "error": "AWS_BUCKET no configurado"}
        
        try:
            response = self.s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)
            
            archivos = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    archivos.append({
                        "nombre": obj['Key'],
                        "tamaño": obj['Size'],
                        "modificado": obj['LastModified'].isoformat()
                    })
            
            return {
                "exito": True,
                "servicio": "s3",
                "bucket": bucket,
                "archivos": archivos,
                "total": len(archivos)
            }
        except Exception as e:
            return {"exito": False, "error": str(e)}
    
    async def _s3_eliminar(self, ruta: str) -> Dict:
        """Eliminar archivo de S3"""
        if not self.s3_client:
            return {"exito": False, "error": "AWS S3 no configurado"}
        
        bucket = self.s3_bucket
        if not bucket:
            return {"exito": False, "error": "AWS_BUCKET no configurado"}
        
        try:
            self.s3_client.delete_object(Bucket=bucket, Key=ruta)
            return {
                "exito": True,
                "servicio": "s3",
                "eliminado": f"s3://{bucket}/{ruta}"
            }
        except Exception as e:
            return {"exito": False, "error": str(e)}
    
    # ============================================================
    # GOOGLE DRIVE
    # ============================================================
    
    async def _drive_subir(self, archivo: str, destino: str = None) -> Dict:
        """Subir archivo a Google Drive"""
        if not self.drive_service:
            return {"exito": False, "error": "Google Drive no configurado"}
        
        try:
            file_metadata = {'name': destino or os.path.basename(archivo)}
            
            # Si hay carpeta destino
            if destino and '/' in destino:
                folder_id = await self._drive_get_folder_id(destino.split('/')[0])
                if folder_id:
                    file_metadata['parents'] = [folder_id]
            
            media = MediaFileUpload(archivo, resumable=True)
            file = self.drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, size'
            ).execute()
            
            return {
                "exito": True,
                "servicio": "google",
                "archivo": archivo,
                "file_id": file.get('id'),
                "nombre": file.get('name')
            }
        except Exception as e:
            return {"exito": False, "error": str(e)}
    
    async def _drive_descargar(self, origen: str, destino: str) -> Dict:
        """Descargar archivo desde Google Drive"""
        if not self.drive_service:
            return {"exito": False, "error": "Google Drive no configurado"}
        
        try:
            # Buscar archivo por nombre
            results = self.drive_service.files().list(
                q=f"name='{origen}'",
                fields="files(id, name)"
            ).execute()
            
            files = results.get('files', [])
            if not files:
                return {"exito": False, "error": f"Archivo no encontrado: {origen}"}
            
            file_id = files[0]['id']
            
            request = self.drive_service.files().get_media(fileId=file_id)
            
            with open(destino, 'wb') as f:
                downloader = MediaIoBaseDownload(f, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
            
            return {
                "exito": True,
                "servicio": "google",
                "origen": origen,
                "destino": destino
            }
        except Exception as e:
            return {"exito": False, "error": str(e)}
    
    async def _drive_listar(self, folder: str = "") -> Dict:
        """Listar archivos en Google Drive"""
        if not self.drive_service:
            return {"exito": False, "error": "Google Drive no configurado"}
        
        try:
            query = "trashed=false"
            if folder:
                query += f" and name='{folder}'"
            
            results = self.drive_service.files().list(
                q=query,
                fields="files(id, name, mimeType, size, createdTime)"
            ).execute()
            
            archivos = []
            for file in results.get('files', []):
                archivos.append({
                    "id": file['id'],
                    "nombre": file['name'],
                    "tipo": file['mimeType'],
                    "tamaño": file.get('size', 0),
                    "creado": file.get('createdTime')
                })
            
            return {
                "exito": True,
                "servicio": "google",
                "archivos": archivos,
                "total": len(archivos)
            }
        except Exception as e:
            return {"exito": False, "error": str(e)}
    
    async def _drive_get_folder_id(self, folder_name: str) -> Optional[str]:
        """Obtener ID de una carpeta en Google Drive"""
        try:
            results = self.drive_service.files().list(
                q=f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'",
                fields="files(id)"
            ).execute()
            files = results.get('files', [])
            return files[0]['id'] if files else None
        except:
            return None
    
    # ============================================================
    # DROPBOX
    # ============================================================
    
    async def _dropbox_subir(self, archivo: str, destino: str = None) -> Dict:
        """Subir archivo a Dropbox"""
        if not self.dropbox_client:
            return {"exito": False, "error": "Dropbox no configurado"}
        
        if not destino:
            destino = f"/{os.path.basename(archivo)}"
        elif not destino.startswith('/'):
            destino = f"/{destino}"
        
        try:
            with open(archivo, 'rb') as f:
                response = self.dropbox_client.files_upload(f.read(), destino)
            
            return {
                "exito": True,
                "servicio": "dropbox",
                "archivo": archivo,
                "destino": response.path_display,
                "revision": response.rev
            }
        except Exception as e:
            return {"exito": False, "error": str(e)}
    
    async def _dropbox_descargar(self, origen: str, destino: str) -> Dict:
        """Descargar archivo desde Dropbox"""
        if not self.dropbox_client:
            return {"exito": False, "error": "Dropbox no configurado"}
        
        if not origen.startswith('/'):
            origen = f"/{origen}"
        
        try:
            metadata, response = self.dropbox_client.files_download(origen)
            
            with open(destino, 'wb') as f:
                f.write(response.content)
            
            return {
                "exito": True,
                "servicio": "dropbox",
                "origen": origen,
                "destino": destino
            }
        except Exception as e:
            return {"exito": False, "error": str(e)}
    
    async def _dropbox_listar(self, ruta: str = "") -> Dict:
        """Listar archivos en Dropbox"""
        if not self.dropbox_client:
            return {"exito": False, "error": "Dropbox no configurado"}
        
        if not ruta:
            ruta = ""
        
        try:
            response = self.dropbox_client.files_list_folder(ruta)
            
            archivos = []
            for entry in response.entries:
                archivos.append({
                    "nombre": entry.name,
                    "tipo": "carpeta" if isinstance(entry, dropbox.files.FolderMetadata) else "archivo",
                    "ruta": entry.path_display,
                    "tamaño": getattr(entry, 'size', 0)
                })
            
            return {
                "exito": True,
                "servicio": "dropbox",
                "archivos": archivos,
                "total": len(archivos)
            }
        except Exception as e:
            return {"exito": False, "error": str(e)}
    
    # ============================================================
    # MÉTODOS PRINCIPALES
    # ============================================================
    
    async def _subir(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Subir archivo a la nube"""
        servicio = parametros.get("servicio") or self._detectar_servicio(desc)
        archivo = parametros.get("archivo") or self._extraer_archivo(desc)
        destino = parametros.get("destino") or self._extraer_destino(desc)
        
        if not servicio:
            return ResultadoTarea(exito=False, error="Especifica el servicio cloud (s3, google, dropbox)")
        
        if not archivo or not Path(archivo).exists():
            return ResultadoTarea(exito=False, error=f"Archivo no encontrado: {archivo}")
        
        if servicio == "s3":
            resultado = await self._s3_subir(archivo, destino)
        elif servicio == "google":
            resultado = await self._drive_subir(archivo, destino)
        elif servicio == "dropbox":
            resultado = await self._dropbox_subir(archivo, destino)
        else:
            return ResultadoTarea(exito=False, error=f"Servicio no soportado: {servicio}")
        
        return ResultadoTarea(
            exito=resultado.get("exito", False),
            datos=resultado
        )
    
    async def _descargar(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Descargar archivo desde la nube"""
        servicio = parametros.get("servicio") or self._detectar_servicio(desc)
        origen = parametros.get("origen") or self._extraer_ruta_remota(desc)
        destino = parametros.get("destino") or self._extraer_archivo(desc) or "descarga"
        
        if not servicio:
            return ResultadoTarea(exito=False, error="Especifica el servicio cloud (s3, google, dropbox)")
        
        if not origen:
            return ResultadoTarea(exito=False, error="Especifica el archivo a descargar")
        
        if servicio == "s3":
            resultado = await self._s3_descargar(origen, destino)
        elif servicio == "google":
            resultado = await self._drive_descargar(origen, destino)
        elif servicio == "dropbox":
            resultado = await self._dropbox_descargar(origen, destino)
        else:
            return ResultadoTarea(exito=False, error=f"Servicio no soportado: {servicio}")
        
        return ResultadoTarea(
            exito=resultado.get("exito", False),
            datos=resultado
        )
    
    async def _listar(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Listar archivos en la nube"""
        servicio = parametros.get("servicio") or self._detectar_servicio(desc)
        ruta = parametros.get("ruta") or ""
        
        if not servicio:
            return ResultadoTarea(exito=False, error="Especifica el servicio cloud (s3, google, dropbox)")
        
        if servicio == "s3":
            resultado = await self._s3_listar(ruta)
        elif servicio == "google":
            resultado = await self._drive_listar(ruta)
        elif servicio == "dropbox":
            resultado = await self._dropbox_listar(ruta)
        else:
            return ResultadoTarea(exito=False, error=f"Servicio no soportado: {servicio}")
        
        return ResultadoTarea(
            exito=resultado.get("exito", False),
            datos=resultado
        )
    
    async def _eliminar(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Eliminar archivo de la nube"""
        servicio = parametros.get("servicio") or self._detectar_servicio(desc)
        ruta = parametros.get("ruta") or self._extraer_ruta_remota(desc)
        
        if not servicio:
            return ResultadoTarea(exito=False, error="Especifica el servicio cloud")
        
        if not ruta:
            return ResultadoTarea(exito=False, error="Especifica el archivo a eliminar")
        
        if servicio == "s3":
            resultado = await self._s3_eliminar(ruta)
        elif servicio == "google":
            resultado = await self._drive_eliminar(ruta)
        elif servicio == "dropbox":
            resultado = await self._dropbox_eliminar(ruta)
        else:
            return ResultadoTarea(exito=False, error=f"Servicio no soportado: {servicio}")
        
        return ResultadoTarea(
            exito=resultado.get("exito", False),
            datos=resultado
        )
    
    async def _sincronizar(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Sincronizar carpeta local con la nube"""
        servicio = parametros.get("servicio") or self._detectar_servicio(desc)
        local = parametros.get("local") or "."
        remoto = parametros.get("remoto") or ""
        
        if not servicio:
            return ResultadoTarea(exito=False, error="Especifica el servicio cloud")
        
        local_path = Path(local)
        if not local_path.exists():
            return ResultadoTarea(exito=False, error=f"Carpeta local no existe: {local}")
        
        resultados = []
        
        if local_path.is_file():
            # Subir archivo único
            if servicio == "s3":
                resultado = await self._s3_subir(str(local_path), remoto)
            elif servicio == "google":
                resultado = await self._drive_subir(str(local_path), remoto)
            elif servicio == "dropbox":
                resultado = await self._dropbox_subir(str(local_path), remoto)
            resultados.append(resultado)
        else:
            # Sincronizar carpeta
            for item in local_path.rglob("*"):
                if item.is_file():
                    rel_path = str(item.relative_to(local_path))
                    dest = f"{remoto}/{rel_path}" if remoto else rel_path
                    
                    if servicio == "s3":
                        resultado = await self._s3_subir(str(item), dest)
                    elif servicio == "google":
                        resultado = await self._drive_subir(str(item), dest)
                    elif servicio == "dropbox":
                        resultado = await self._dropbox_subir(str(item), dest)
                    resultados.append(resultado)
        
        exitos = sum(1 for r in resultados if r.get("exito"))
        
        return ResultadoTarea(
            exito=exitos > 0,
            datos={
                "servicio": servicio,
                "local": str(local_path),
                "remoto": remoto,
                "total": len(resultados),
                "exitos": exitos,
                "resultados": resultados[:10]  # limitar para no saturar
            }
        )
    
    async def _backup(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Crear backup en la nube"""
        archivo = parametros.get("archivo") or self._extraer_archivo(desc)
        nombre = parametros.get("nombre") or f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        servicio = parametros.get("servicio") or self._detectar_servicio(desc) or "s3"
        
        if not archivo:
            return ResultadoTarea(exito=False, error="Especifica el archivo a respaldar")
        
        if not Path(archivo).exists():
            return ResultadoTarea(exito=False, error=f"Archivo no encontrado: {archivo}")
        
        # Agregar timestamp al nombre
        nombre_backup = f"{nombre}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        if servicio == "s3":
            resultado = await self._s3_subir(archivo, f"backups/{nombre_backup}")
        elif servicio == "google":
            resultado = await self._drive_subir(archivo, nombre_backup)
        elif servicio == "dropbox":
            resultado = await self._dropbox_subir(archivo, f"/backups/{nombre_backup}")
        else:
            return ResultadoTarea(exito=False, error=f"Servicio no soportado: {servicio}")
        
        return ResultadoTarea(
            exito=resultado.get("exito", False),
            datos={
                "servicio": servicio,
                "archivo": archivo,
                "backup": nombre_backup,
                "resultado": resultado
            }
        )
    
    async def _listar_servicios(self) -> ResultadoTarea:
        """Listar servicios cloud configurados"""
        servicios = []
        
        if self.s3_client:
            servicios.append({
                "nombre": "AWS S3",
                "configurado": True,
                "bucket": self.s3_bucket
            })
        
        if self.drive_service:
            servicios.append({
                "nombre": "Google Drive",
                "configurado": True,
                "cuenta": os.getenv("GOOGLE_CREDENTIALS_FILE", "")
            })
        
        if self.dropbox_client:
            servicios.append({
                "nombre": "Dropbox",
                "configurado": True,
                "cuenta": os.getenv("DROPBOX_ACCESS_TOKEN", "")[:20] + "..."
            })
        
        return ResultadoTarea(
            exito=True,
            datos={"servicios": servicios, "total": len(servicios)}
        )
    
    async def _drive_eliminar(self, nombre: str) -> Dict:
        """Eliminar archivo de Google Drive"""
        if not self.drive_service:
            return {"exito": False, "error": "Google Drive no configurado"}
        
        try:
            results = self.drive_service.files().list(
                q=f"name='{nombre}'",
                fields="files(id)"
            ).execute()
            
            files = results.get('files', [])
            if not files:
                return {"exito": False, "error": f"Archivo no encontrado: {nombre}"}
            
            self.drive_service.files().delete(fileId=files[0]['id']).execute()
            
            return {
                "exito": True,
                "servicio": "google",
                "eliminado": nombre
            }
        except Exception as e:
            return {"exito": False, "error": str(e)}
    
    async def _dropbox_eliminar(self, ruta: str) -> Dict:
        """Eliminar archivo de Dropbox"""
        if not self.dropbox_client:
            return {"exito": False, "error": "Dropbox no configurado"}
        
        if not ruta.startswith('/'):
            ruta = f"/{ruta}"
        
        try:
            self.dropbox_client.files_delete_v2(ruta)
            return {
                "exito": True,
                "servicio": "dropbox",
                "eliminado": ruta
            }
        except Exception as e:
            return {"exito": False, "error": str(e)}


# ============================================================
# Factory Function
# ============================================================

def crear_agente_cloud(supervisor: Supervisor, config: Config) -> AgenteCloud:
    """Crea instancia del agente cloud"""
    return AgenteCloud(supervisor, config)
