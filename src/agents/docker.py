#!/usr/bin/env python3
"""
Agente Docker - Gestión de contenedores Docker y Kubernetes
Soporta: Docker, Docker Compose, Kubernetes (kubectl)
Capacidades: contenedores, imágenes, volúmenes, redes, despliegues
"""

import os
import sys
import json
import subprocess
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

# Importaciones opcionales
try:
    import docker
    from docker.errors import APIError, NotFound
    DOCKER_PY_AVAILABLE = True
except ImportError:
    DOCKER_PY_AVAILABLE = False
    docker = None

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

from src.core.agente import Agente, TipoAgente, ResultadoTarea
from src.core.supervisor import Supervisor
from src.core.config import Config


class AgenteDocker(Agente):
    """
    Agente Docker - Gestión de contenedores Docker y Kubernetes
    Soporta: Docker, Docker Compose, Kubernetes
    """
    
    def __init__(self, supervisor: Supervisor, config: Config):
        super().__init__(
            id_agente="docker",
            nombre="Agente Docker",
            tipo=TipoAgente.DOCKER,
            supervisor=supervisor,
            version="1.0.0"
        )
        self.config = config
        
        # Clientes
        self.docker_client = None
        self.docker_available = False
        
        # Directorio para archivos de compose
        self.compose_dir = Path("config/docker")
        self.compose_dir.mkdir(parents=True, exist_ok=True)
        
        self._cargar_configuraciones()
        self._registrar_capacidades()
        self._mostrar_disponibilidad()
        self.logger.info("Agente Docker iniciado")
    
    def _cargar_configuraciones(self):
        """Cargar configuraciones de Docker"""
        
        # Docker
        if DOCKER_PY_AVAILABLE:
            try:
                self.docker_client = docker.from_env()
                self.docker_client.ping()
                self.docker_available = True
                self.logger.info("Docker conectado correctamente")
            except Exception as e:
                self.logger.warning(f"Docker no disponible: {e}")
                self.docker_available = False
        else:
            # Intentar usar docker CLI
            try:
                subprocess.run(["docker", "version"], capture_output=True, timeout=5)
                self.docker_available = True
                self.logger.info("Docker CLI disponible")
            except:
                self.logger.warning("Docker no disponible")
    
    def _mostrar_disponibilidad(self):
        """Mostrar disponibilidad de herramientas"""
        self.logger.info("Herramientas disponibles:")
        self.logger.info(f"  Docker API: {'✅' if self.docker_available else '❌'}")
        self.logger.info(f"  Docker Compose: {'✅' if self._compose_available() else '❌'}")
        self.logger.info(f"  kubectl: {'✅' if self._kubectl_available() else '❌'}")
    
    def _compose_available(self) -> bool:
        """Verificar si Docker Compose está disponible"""
        try:
            subprocess.run(["docker-compose", "version"], capture_output=True, timeout=5)
            return True
        except:
            return False
    
    def _kubectl_available(self) -> bool:
        """Verificar si kubectl está disponible"""
        try:
            subprocess.run(["kubectl", "version", "--client"], capture_output=True, timeout=5)
            return True
        except:
            return False
    
    def _registrar_capacidades(self):
        """Registrar capacidades del agente"""
        
        # Contenedores
        self.registrar_capacidad(
            nombre="docker_ps",
            descripcion="Listar contenedores Docker",
            parametros=["todos"],
            ejemplos=["listar contenedores", "docker ps", "contenedores en ejecución"],
            nivel_riesgo="bajo"
        )
        
        self.registrar_capacidad(
            nombre="docker_start",
            descripcion="Iniciar contenedor",
            parametros=["nombre"],
            ejemplos=["iniciar contenedor nginx", "docker start mi_app"],
            nivel_riesgo="medio"
        )
        
        self.registrar_capacidad(
            nombre="docker_stop",
            descripcion="Detener contenedor",
            parametros=["nombre"],
            ejemplos=["detener contenedor", "docker stop nginx"],
            nivel_riesgo="medio"
        )
        
        self.registrar_capacidad(
            nombre="docker_restart",
            descripcion="Reiniciar contenedor",
            parametros=["nombre"],
            ejemplos=["reiniciar contenedor", "docker restart mi_servicio"],
            nivel_riesgo="medio"
        )
        
        self.registrar_capacidad(
            nombre="docker_rm",
            descripcion="Eliminar contenedor",
            parametros=["nombre", "force"],
            ejemplos=["eliminar contenedor viejo", "docker rm mi_app"],
            nivel_riesgo="alto"
        )
        
        self.registrar_capacidad(
            nombre="docker_run",
            descripcion="Ejecutar nuevo contenedor",
            parametros=["imagen", "nombre", "puertos", "volumenes"],
            ejemplos=["ejecutar nginx en puerto 8080", "docker run -p 80:80 nginx"],
            nivel_riesgo="medio"
        )
        
        self.registrar_capacidad(
            nombre="docker_logs",
            descripcion="Ver logs de contenedor",
            parametros=["nombre", "lineas"],
            ejemplos=["ver logs de nginx", "logs del contenedor"],
            nivel_riesgo="bajo"
        )
        
        # Imágenes
        self.registrar_capacidad(
            nombre="docker_images",
            descripcion="Listar imágenes Docker",
            ejemplos=["listar imágenes", "docker images"],
            nivel_riesgo="bajo"
        )
        
        self.registrar_capacidad(
            nombre="docker_pull",
            descripcion="Descargar imagen Docker",
            parametros=["imagen"],
            ejemplos=["descargar imagen nginx", "docker pull ubuntu"],
            nivel_riesgo="bajo"
        )
        
        self.registrar_capacidad(
            nombre="docker_build",
            descripcion="Construir imagen Docker",
            parametros=["ruta", "tag"],
            ejemplos=["construir imagen con Dockerfile", "docker build ."],
            nivel_riesgo="medio"
        )
        
        self.registrar_capacidad(
            nombre="docker_rmi",
            descripcion="Eliminar imagen Docker",
            parametros=["imagen"],
            ejemplos=["eliminar imagen no usada", "docker rmi mi_imagen"],
            nivel_riesgo="alto"
        )
        
        # Volúmenes
        self.registrar_capacidad(
            nombre="docker_volumes",
            descripcion="Listar volúmenes",
            ejemplos=["listar volúmenes", "docker volume ls"],
            nivel_riesgo="bajo"
        )
        
        self.registrar_capacidad(
            nombre="docker_volume_create",
            descripcion="Crear volumen",
            parametros=["nombre"],
            ejemplos=["crear volumen para datos", "docker volume create"],
            nivel_riesgo="bajo"
        )
        
        # Redes
        self.registrar_capacidad(
            nombre="docker_networks",
            descripcion="Listar redes Docker",
            ejemplos=["listar redes", "docker network ls"],
            nivel_riesgo="bajo"
        )
        
        # Docker Compose
        self.registrar_capacidad(
            nombre="compose_up",
            descripcion="Levantar servicios con docker-compose",
            parametros=["archivo", "servicio"],
            ejemplos=["levantar servicios con docker-compose", "docker-compose up"],
            nivel_riesgo="medio"
        )
        
        self.registrar_capacidad(
            nombre="compose_down",
            descripcion="Detener servicios con docker-compose",
            parametros=["archivo"],
            ejemplos=["detener servicios", "docker-compose down"],
            nivel_riesgo="medio"
        )
        
        self.registrar_capacidad(
            nombre="compose_logs",
            descripcion="Ver logs de docker-compose",
            parametros=["archivo"],
            ejemplos=["logs de docker-compose"],
            nivel_riesgo="bajo"
        )
        
        # Kubernetes
        self.registrar_capacidad(
            nombre="kubectl_get",
            descripcion="Listar recursos Kubernetes",
            parametros=["tipo"],
            ejemplos=["listar pods", "kubectl get pods", "ver servicios"],
            nivel_riesgo="bajo"
        )
        
        self.registrar_capacidad(
            nombre="kubectl_apply",
            descripcion="Aplicar configuración Kubernetes",
            parametros=["archivo"],
            ejemplos=["aplicar deployment", "kubectl apply -f deployment.yaml"],
            nivel_riesgo="alto"
        )
        
        self.registrar_capacidad(
            nombre="kubectl_delete",
            descripcion="Eliminar recurso Kubernetes",
            parametros=["tipo", "nombre"],
            ejemplos=["eliminar pod", "kubectl delete deployment mi-app"],
            nivel_riesgo="alto"
        )
    
    async def ejecutar(self, tarea: Dict[str, Any]) -> ResultadoTarea:
        """Ejecuta tarea según tipo"""
        tipo = tarea.get("tipo", "")
        desc = tarea.get("descripcion", "").lower()
        parametros = tarea.get("parametros", {})
        
        # Contenedores
        if "docker_ps" in tipo or "listar contenedores" in desc or "docker ps" in desc:
            return await self._docker_ps(parametros)
        
        elif "docker_start" in tipo or "iniciar contenedor" in desc:
            return await self._docker_start(desc, parametros)
        
        elif "docker_stop" in tipo or "detener contenedor" in desc:
            return await self._docker_stop(desc, parametros)
        
        elif "docker_restart" in tipo or "reiniciar contenedor" in desc:
            return await self._docker_restart(desc, parametros)
        
        elif "docker_rm" in tipo or "eliminar contenedor" in desc:
            return await self._docker_rm(desc, parametros)
        
        elif "docker_run" in tipo or "ejecutar contenedor" in desc:
            return await self._docker_run(desc, parametros)
        
        elif "docker_logs" in tipo or "ver logs" in desc:
            return await self._docker_logs(desc, parametros)
        
        # Imágenes
        elif "docker_images" in tipo or "listar imágenes" in desc:
            return await self._docker_images()
        
        elif "docker_pull" in tipo or "descargar imagen" in desc:
            return await self._docker_pull(desc, parametros)
        
        elif "docker_build" in tipo or "construir imagen" in desc:
            return await self._docker_build(desc, parametros)
        
        elif "docker_rmi" in tipo or "eliminar imagen" in desc:
            return await self._docker_rmi(desc, parametros)
        
        # Volúmenes
        elif "docker_volumes" in tipo or "listar volúmenes" in desc:
            return await self._docker_volumes()
        
        elif "docker_volume_create" in tipo or "crear volumen" in desc:
            return await self._docker_volume_create(desc, parametros)
        
        # Redes
        elif "docker_networks" in tipo or "listar redes" in desc:
            return await self._docker_networks()
        
        # Docker Compose
        elif "compose_up" in tipo or "docker-compose up" in desc:
            return await self._compose_up(desc, parametros)
        
        elif "compose_down" in tipo or "docker-compose down" in desc:
            return await self._compose_down(desc, parametros)
        
        elif "compose_logs" in tipo:
            return await self._compose_logs(desc, parametros)
        
        # Kubernetes
        elif "kubectl_get" in tipo or "kubectl get" in desc:
            return await self._kubectl_get(desc, parametros)
        
        elif "kubectl_apply" in tipo or "kubectl apply" in desc:
            return await self._kubectl_apply(desc, parametros)
        
        elif "kubectl_delete" in tipo or "kubectl delete" in desc:
            return await self._kubectl_delete(desc, parametros)
        
        else:
            return ResultadoTarea(exito=False, error=f"No sé cómo manejar: {tipo}")
    
    # ============================================================
    # CONTENEDORES
    # ============================================================
    
    async def _docker_ps(self, parametros: Dict) -> ResultadoTarea:
        """Listar contenedores"""
        if not self.docker_available:
            return ResultadoTarea(exito=False, error="Docker no disponible")
        
        todos = parametros.get("todos", False)
        
        if self.docker_client:
            try:
                containers = self.docker_client.containers.list(all=todos)
                resultados = []
                for c in containers:
                    resultados.append({
                        "id": c.id[:12],
                        "nombre": c.name,
                        "imagen": c.image.tags[0] if c.image.tags else c.image.id[:12],
                        "estado": c.status,
                        "creado": c.attrs.get('Created', ''),
                        "puertos": c.ports
                    })
                return ResultadoTarea(
                    exito=True,
                    datos={"contenedores": resultados, "total": len(resultados)}
                )
            except Exception as e:
                return ResultadoTarea(exito=False, error=str(e))
        else:
            # Usar CLI
            cmd = ["docker", "ps", "-a" if todos else ""]
            result = self._ejecutar_comando(cmd)
            return ResultadoTarea(
                exito=result["exito"],
                datos={"salida": result["salida"]}
            )
    
    async def _docker_start(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Iniciar contenedor"""
        nombre = parametros.get("nombre") or self._extraer_nombre_contenedor(desc)
        
        if not nombre:
            return ResultadoTarea(exito=False, error="Especifica el contenedor a iniciar")
        
        if self.docker_client:
            try:
                container = self.docker_client.containers.get(nombre)
                container.start()
                return ResultadoTarea(
                    exito=True,
                    datos={"contenedor": nombre, "mensaje": f"Contenedor {nombre} iniciado"}
                )
            except Exception as e:
                return ResultadoTarea(exito=False, error=str(e))
        else:
            result = self._ejecutar_comando(["docker", "start", nombre])
            return ResultadoTarea(
                exito=result["exito"],
                datos={"salida": result["salida"]}
            )
    
    async def _docker_stop(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Detener contenedor"""
        nombre = parametros.get("nombre") or self._extraer_nombre_contenedor(desc)
        
        if not nombre:
            return ResultadoTarea(exito=False, error="Especifica el contenedor a detener")
        
        if self.docker_client:
            try:
                container = self.docker_client.containers.get(nombre)
                container.stop()
                return ResultadoTarea(
                    exito=True,
                    datos={"contenedor": nombre, "mensaje": f"Contenedor {nombre} detenido"}
                )
            except Exception as e:
                return ResultadoTarea(exito=False, error=str(e))
        else:
            result = self._ejecutar_comando(["docker", "stop", nombre])
            return ResultadoTarea(
                exito=result["exito"],
                datos={"salida": result["salida"]}
            )
    
    async def _docker_restart(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Reiniciar contenedor"""
        nombre = parametros.get("nombre") or self._extraer_nombre_contenedor(desc)
        
        if not nombre:
            return ResultadoTarea(exito=False, error="Especifica el contenedor a reiniciar")
        
        if self.docker_client:
            try:
                container = self.docker_client.containers.get(nombre)
                container.restart()
                return ResultadoTarea(
                    exito=True,
                    datos={"contenedor": nombre, "mensaje": f"Contenedor {nombre} reiniciado"}
                )
            except Exception as e:
                return ResultadoTarea(exito=False, error=str(e))
        else:
            result = self._ejecutar_comando(["docker", "restart", nombre])
            return ResultadoTarea(
                exito=result["exito"],
                datos={"salida": result["salida"]}
            )
    
    async def _docker_rm(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Eliminar contenedor"""
        nombre = parametros.get("nombre") or self._extraer_nombre_contenedor(desc)
        force = parametros.get("force", False)
        
        if not nombre:
            return ResultadoTarea(exito=False, error="Especifica el contenedor a eliminar")
        
        if self.docker_client:
            try:
                container = self.docker_client.containers.get(nombre)
                container.remove(force=force)
                return ResultadoTarea(
                    exito=True,
                    datos={"contenedor": nombre, "mensaje": f"Contenedor {nombre} eliminado"}
                )
            except Exception as e:
                return ResultadoTarea(exito=False, error=str(e))
        else:
            cmd = ["docker", "rm"]
            if force:
                cmd.append("-f")
            cmd.append(nombre)
            result = self._ejecutar_comando(cmd)
            return ResultadoTarea(
                exito=result["exito"],
                datos={"salida": result["salida"]}
            )
    
    async def _docker_run(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Ejecutar nuevo contenedor"""
        imagen = parametros.get("imagen") or self._extraer_imagen(desc)
        nombre = parametros.get("nombre")
        puertos = parametros.get("puertos", {})
        volumenes = parametros.get("volumenes", [])
        
        if not imagen:
            return ResultadoTarea(exito=False, error="Especifica la imagen a ejecutar")
        
        if self.docker_client:
            try:
                # Construir parámetros
                kwargs = {
                    "image": imagen,
                    "detach": True,
                    "name": nombre,
                    "ports": puertos,
                    "volumes": volumenes
                }
                container = self.docker_client.containers.run(**kwargs)
                return ResultadoTarea(
                    exito=True,
                    datos={
                        "id": container.id[:12],
                        "nombre": container.name,
                        "imagen": imagen,
                        "mensaje": f"Contenedor {container.name} iniciado"
                    }
                )
            except Exception as e:
                return ResultadoTarea(exito=False, error=str(e))
        else:
            cmd = ["docker", "run", "-d"]
            if nombre:
                cmd.extend(["--name", nombre])
            for host, cont in puertos.items():
                cmd.extend(["-p", f"{host}:{cont}"])
            for vol in volumenes:
                cmd.extend(["-v", vol])
            cmd.append(imagen)
            result = self._ejecutar_comando(cmd)
            return ResultadoTarea(
                exito=result["exito"],
                datos={"salida": result["salida"]}
            )
    
    async def _docker_logs(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Ver logs de contenedor"""
        nombre = parametros.get("nombre") or self._extraer_nombre_contenedor(desc)
        lineas = parametros.get("lineas", 50)
        
        if not nombre:
            return ResultadoTarea(exito=False, error="Especifica el contenedor")
        
        if self.docker_client:
            try:
                container = self.docker_client.containers.get(nombre)
                logs = container.logs(tail=lineas).decode('utf-8')
                return ResultadoTarea(
                    exito=True,
                    datos={"contenedor": nombre, "logs": logs, "lineas": len(logs.splitlines())}
                )
            except Exception as e:
                return ResultadoTarea(exito=False, error=str(e))
        else:
            result = self._ejecutar_comando(["docker", "logs", "--tail", str(lineas), nombre])
            return ResultadoTarea(
                exito=result["exito"],
                datos={"salida": result["salida"]}
            )
    
    # ============================================================
    # IMÁGENES
    # ============================================================
    
    async def _docker_images(self) -> ResultadoTarea:
        """Listar imágenes"""
        if not self.docker_available:
            return ResultadoTarea(exito=False, error="Docker no disponible")
        
        if self.docker_client:
            try:
                images = self.docker_client.images.list()
                resultados = []
                for img in images:
                    resultados.append({
                        "repositorio": img.tags[0] if img.tags else "<none>",
                        "id": img.id[:12],
                        "tamaño": img.attrs.get('Size', 0),
                        "creado": img.attrs.get('Created', '')
                    })
                return ResultadoTarea(
                    exito=True,
                    datos={"imagenes": resultados, "total": len(resultados)}
                )
            except Exception as e:
                return ResultadoTarea(exito=False, error=str(e))
        else:
            result = self._ejecutar_comando(["docker", "images"])
            return ResultadoTarea(
                exito=result["exito"],
                datos={"salida": result["salida"]}
            )
    
    async def _docker_pull(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Descargar imagen"""
        imagen = parametros.get("imagen") or self._extraer_imagen(desc)
        
        if not imagen:
            return ResultadoTarea(exito=False, error="Especifica la imagen a descargar")
        
        if self.docker_client:
            try:
                self.logger.info(f"Descargando imagen {imagen}")
                for line in self.docker_client.api.pull(imagen, stream=True, decode=True):
                    if 'status' in line:
                        self.logger.debug(line['status'])
                return ResultadoTarea(
                    exito=True,
                    datos={"imagen": imagen, "mensaje": f"Imagen {imagen} descargada"}
                )
            except Exception as e:
                return ResultadoTarea(exito=False, error=str(e))
        else:
            result = self._ejecutar_comando(["docker", "pull", imagen])
            return ResultadoTarea(
                exito=result["exito"],
                datos={"salida": result["salida"]}
            )
    
    async def _docker_build(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Construir imagen"""
        ruta = parametros.get("ruta") or "."
        tag = parametros.get("tag") or f"swarmia_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        if self.docker_client:
            try:
                self.logger.info(f"Construyendo imagen {tag} desde {ruta}")
                image, logs = self.docker_client.images.build(path=ruta, tag=tag)
                return ResultadoTarea(
                    exito=True,
                    datos={"imagen": tag, "id": image.id[:12], "mensaje": f"Imagen {tag} construida"}
                )
            except Exception as e:
                return ResultadoTarea(exito=False, error=str(e))
        else:
            result = self._ejecutar_comando(["docker", "build", "-t", tag, ruta])
            return ResultadoTarea(
                exito=result["exito"],
                datos={"salida": result["salida"]}
            )
    
    async def _docker_rmi(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Eliminar imagen"""
        imagen = parametros.get("imagen") or self._extraer_imagen(desc)
        
        if not imagen:
            return ResultadoTarea(exito=False, error="Especifica la imagen a eliminar")
        
        if self.docker_client:
            try:
                self.docker_client.images.remove(imagen)
                return ResultadoTarea(
                    exito=True,
                    datos={"imagen": imagen, "mensaje": f"Imagen {imagen} eliminada"}
                )
            except Exception as e:
                return ResultadoTarea(exito=False, error=str(e))
        else:
            result = self._ejecutar_comando(["docker", "rmi", imagen])
            return ResultadoTarea(
                exito=result["exito"],
                datos={"salida": result["salida"]}
            )
    
    # ============================================================
    # VOLÚMENES
    # ============================================================
    
    async def _docker_volumes(self) -> ResultadoTarea:
        """Listar volúmenes"""
        if not self.docker_available:
            return ResultadoTarea(exito=False, error="Docker no disponible")
        
        if self.docker_client:
            try:
                volumes = self.docker_client.volumes.list()
                resultados = [{"nombre": v.name, "driver": v.attrs.get('Driver'), "mountpoint": v.attrs.get('Mountpoint')} for v in volumes]
                return ResultadoTarea(
                    exito=True,
                    datos={"volumenes": resultados, "total": len(resultados)}
                )
            except Exception as e:
                return ResultadoTarea(exito=False, error=str(e))
        else:
            result = self._ejecutar_comando(["docker", "volume", "ls"])
            return ResultadoTarea(
                exito=result["exito"],
                datos={"salida": result["salida"]}
            )
    
    async def _docker_volume_create(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Crear volumen"""
        nombre = parametros.get("nombre") or f"vol_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        if self.docker_client:
            try:
                volume = self.docker_client.volumes.create(name=nombre)
                return ResultadoTarea(
                    exito=True,
                    datos={"nombre": volume.name, "mensaje": f"Volumen {nombre} creado"}
                )
            except Exception as e:
                return ResultadoTarea(exito=False, error=str(e))
        else:
            result = self._ejecutar_comando(["docker", "volume", "create", nombre])
            return ResultadoTarea(
                exito=result["exito"],
                datos={"salida": result["salida"]}
            )
    
    # ============================================================
    # REDES
    # ============================================================
    
    async def _docker_networks(self) -> ResultadoTarea:
        """Listar redes"""
        if not self.docker_available:
            return ResultadoTarea(exito=False, error="Docker no disponible")
        
        if self.docker_client:
            try:
                networks = self.docker_client.networks.list()
                resultados = [{"nombre": n.name, "driver": n.attrs.get('Driver'), "subnet": n.attrs.get('IPAM', {}).get('Config', [{}])[0].get('Subnet')} for n in networks]
                return ResultadoTarea(
                    exito=True,
                    datos={"redes": resultados, "total": len(resultados)}
                )
            except Exception as e:
                return ResultadoTarea(exito=False, error=str(e))
        else:
            result = self._ejecutar_comando(["docker", "network", "ls"])
            return ResultadoTarea(
                exito=result["exito"],
                datos={"salida": result["salida"]}
            )
    
    # ============================================================
    # DOCKER COMPOSE
    # ============================================================
    
    async def _compose_up(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Levantar servicios con docker-compose"""
        archivo = parametros.get("archivo") or "docker-compose.yml"
        servicio = parametros.get("servicio")
        
        if not Path(archivo).exists():
            archivo = self.compose_dir / archivo
            if not archivo.exists():
                return ResultadoTarea(exito=False, error=f"Archivo no encontrado: {archivo}")
        
        cmd = ["docker-compose", "-f", str(archivo), "up", "-d"]
        if servicio:
            cmd.append(servicio)
        
        result = self._ejecutar_comando(cmd)
        return ResultadoTarea(
            exito=result["exito"],
            datos={"salida": result["salida"]}
        )
    
    async def _compose_down(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Detener servicios con docker-compose"""
        archivo = parametros.get("archivo") or "docker-compose.yml"
        
        if not Path(archivo).exists():
            archivo = self.compose_dir / archivo
            if not archivo.exists():
                return ResultadoTarea(exito=False, error=f"Archivo no encontrado: {archivo}")
        
        result = self._ejecutar_comando(["docker-compose", "-f", str(archivo), "down"])
        return ResultadoTarea(
            exito=result["exito"],
            datos={"salida": result["salida"]}
        )
    
    async def _compose_logs(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Ver logs de docker-compose"""
        archivo = parametros.get("archivo") or "docker-compose.yml"
        lineas = parametros.get("lineas", 50)
        
        if not Path(archivo).exists():
            archivo = self.compose_dir / archivo
            if not archivo.exists():
                return ResultadoTarea(exito=False, error=f"Archivo no encontrado: {archivo}")
        
        result = self._ejecutar_comando(["docker-compose", "-f", str(archivo), "logs", "--tail", str(lineas)])
        return ResultadoTarea(
            exito=result["exito"],
            datos={"salida": result["salida"]}
        )
    
    # ============================================================
    # KUBERNETES
    # ============================================================
    
    async def _kubectl_get(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Listar recursos Kubernetes"""
        recurso = parametros.get("recurso") or "pods"
        namespace = parametros.get("namespace", "default")
        
        cmd = ["kubectl", "get", recurso, "-n", namespace]
        result = self._ejecutar_comando(cmd)
        return ResultadoTarea(
            exito=result["exito"],
            datos={"salida": result["salida"]}
        )
    
    async def _kubectl_apply(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Aplicar configuración Kubernetes"""
        archivo = parametros.get("archivo")
        
        if not archivo:
            return ResultadoTarea(exito=False, error="Especifica el archivo YAML")
        
        if not Path(archivo).exists():
            return ResultadoTarea(exito=False, error=f"Archivo no encontrado: {archivo}")
        
        result = self._ejecutar_comando(["kubectl", "apply", "-f", archivo])
        return ResultadoTarea(
            exito=result["exito"],
            datos={"salida": result["salida"]}
        )
    
    async def _kubectl_delete(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Eliminar recurso Kubernetes"""
        recurso = parametros.get("recurso")
        nombre = parametros.get("nombre")
        
        if not recurso or not nombre:
            return ResultadoTarea(exito=False, error="Especifica recurso y nombre (ej: pod mi-app)")
        
        result = self._ejecutar_comando(["kubectl", "delete", recurso, nombre])
        return ResultadoTarea(
            exito=result["exito"],
            datos={"salida": result["salida"]}
        )
    
    # ============================================================
    # UTILIDADES
    # ============================================================
    
    def _ejecutar_comando(self, cmd: List[str]) -> Dict:
        """Ejecutar comando y devolver resultado"""
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            return {
                "exito": result.returncode == 0,
                "salida": result.stdout,
                "error": result.stderr
            }
        except subprocess.TimeoutExpired:
            return {"exito": False, "error": "Timeout"}
        except Exception as e:
            return {"exito": False, "error": str(e)}
    
    def _extraer_nombre_contenedor(self, desc: str) -> Optional[str]:
        """Extraer nombre de contenedor de la descripción"""
        import re
        # Buscar después de palabras clave
        for kw in ["contenedor", "container", "start", "stop", "restart"]:
            match = re.search(rf'{kw}\s+([a-zA-Z0-9_-]+)', desc, re.IGNORECASE)
            if match:
                return match.group(1)
        return None
    
    def _extraer_imagen(self, desc: str) -> Optional[str]:
        """Extraer nombre de imagen de la descripción"""
        import re
        match = re.search(r'([a-zA-Z0-9/:_.-]+)', desc)
        if match:
            return match.group(1)
        return None


# ============================================================
# Factory Function
# ============================================================

def crear_agente_docker(supervisor: Supervisor, config: Config) -> AgenteDocker:
    """Crea instancia del agente Docker"""
    return AgenteDocker(supervisor, config)
