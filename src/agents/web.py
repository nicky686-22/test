#!/usr/bin/env python3
"""
Agente Web - Peticiones HTTP/HTTPS, scraping, APIs REST, monitoreo web
Multiplataforma - Soporta requests, aiohttp, selenium (opcional)
"""

import asyncio
import json
import re
import time
import hashlib
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from urllib.parse import urlparse, urljoin
from pathlib import Path

import aiohttp
import requests
from bs4 import BeautifulSoup

from src.core.agente import Agente, TipoAgente, ResultadoTarea
from src.core.supervisor import Supervisor
from src.core.config import Config


class AgenteWeb(Agente):
    """
    Agente Web - Realiza peticiones HTTP, scraping, consume APIs REST
    Capacidades: GET, POST, scraping, monitoreo, webhooks
    """
    
    def __init__(self, supervisor: Supervisor, config: Config):
        super().__init__(
            id_agente="web",
            nombre="Agente Web",
            tipo=TipoAgente.WEB,
            supervisor=supervisor,
            version="1.0.0"
        )
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (SwarmIA Web Agent/1.0)'
        })
        
        # Cache para peticiones
        self.cache: Dict[str, Dict] = {}
        
        self._registrar_capacidades()
        self.logger.info("Agente Web iniciado")
    
    def _registrar_capacidades(self):
        """Registrar capacidades del agente"""
        
        self.registrar_capacidad(
            nombre="http_get",
            descripcion="Realiza una petición GET a una URL",
            parametros=["url", "headers", "params"],
            ejemplos=["obtener https://ejemplo.com", "GET api.github.com"],
            nivel_riesgo="bajo"
        )
        
        self.registrar_capacidad(
            nombre="http_post",
            descripcion="Realiza una petición POST a una URL",
            parametros=["url", "data", "json", "headers"],
            ejemplos=["enviar POST a api.com/data con {nombre: test}"],
            nivel_riesgo="medio"
        )
        
        self.registrar_capacidad(
            nombre="scraping",
            descripcion="Extrae información de una página web",
            parametros=["url", "selectores"],
            ejemplos=["extraer titulos de https://noticias.com", "scrapear precios"],
            nivel_riesgo="bajo"
        )
        
        self.registrar_capacidad(
            nombre="monitorear_web",
            descripcion="Monitorea cambios en una página web",
            parametros=["url", "intervalo", "selector"],
            ejemplos=["monitorear https://estado.com cada 5 minutos"],
            nivel_riesgo="bajo"
        )
        
        self.registrar_capacidad(
            nombre="api_consumir",
            descripcion="Consume una API REST",
            parametros=["url", "metodo", "datos"],
            ejemplos=["consumir API de clima", "llamar a https://api.ejemplo.com/users"],
            nivel_riesgo="medio"
        )
        
        self.registrar_capacidad(
            nombre="webhook",
            descripcion="Envía un webhook a una URL",
            parametros=["url", "payload"],
            ejemplos=["enviar webhook a Slack", "notificar a Discord"],
            nivel_riesgo="bajo"
        )
        
        self.registrar_capacidad(
            nombre="verificar_url",
            descripcion="Verifica si una URL está disponible",
            parametros=["url"],
            ejemplos=["verificar si https://google.com funciona"],
            nivel_riesgo="bajo"
        )
        
        self.registrar_capacidad(
            nombre="descargar_archivo",
            descripcion="Descarga un archivo desde una URL",
            parametros=["url", "destino"],
            ejemplos=["descargar imagen de https://ejemplo.com/foto.jpg"],
            nivel_riesgo="bajo"
        )
    
    async def ejecutar(self, tarea: Dict[str, Any]) -> ResultadoTarea:
        """Ejecuta tarea según tipo"""
        tipo = tarea.get("tipo", "")
        desc = tarea.get("descripcion", "").lower()
        parametros = tarea.get("parametros", {})
        
        if "http_get" in tipo or "get" in tipo or "obtener" in desc:
            return await self._http_get(desc, parametros)
        
        elif "http_post" in tipo or "post" in tipo or "enviar" in desc:
            return await self._http_post(desc, parametros)
        
        elif "scraping" in tipo or "extraer" in desc or "scrape" in desc:
            return await self._scraping(desc, parametros)
        
        elif "monitorear_web" in tipo or "monitorear" in desc:
            return await self._monitorear_web(desc, parametros)
        
        elif "api_consumir" in tipo or "api" in desc:
            return await self._api_consumir(desc, parametros)
        
        elif "webhook" in tipo:
            return await self._webhook(desc, parametros)
        
        elif "verificar_url" in tipo or "verificar" in desc:
            return await self._verificar_url(desc, parametros)
        
        elif "descargar" in tipo or "descargar_archivo" in tipo:
            return await self._descargar_archivo(desc, parametros)
        
        else:
            return ResultadoTarea(exito=False, error=f"No sé cómo manejar: {tipo}")
    
    # ============================================================
    # HTTP GET
    # ============================================================
    
    async def _http_get(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Realiza petición GET"""
        url = parametros.get("url") or self._extraer_url(desc)
        
        if not url:
            return ResultadoTarea(exito=False, error="Especifica una URL")
        
        headers = parametros.get("headers", {})
        params = parametros.get("params", {})
        timeout = parametros.get("timeout", 30)
        
        # Usar caché si está habilitado
        cache_key = f"get_{url}_{hashlib.md5(str(params).encode()).hexdigest()}"
        if cache_key in self.cache:
            cache_data = self.cache[cache_key]
            if time.time() - cache_data["timestamp"] < 60:  # cache por 60 segundos
                return ResultadoTarea(
                    exito=True,
                    datos=cache_data["data"],
                    metadatos={"cached": True}
                )
        
        try:
            self.logger.info(f"GET {url}")
            response = self.session.get(
                url, 
                headers=headers, 
                params=params, 
                timeout=timeout
            )
            
            resultado = {
                "url": url,
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "content_type": response.headers.get("content-type", ""),
                "content": response.text,
                "tamaño": len(response.content),
                "tiempo": response.elapsed.total_seconds()
            }
            
            # Guardar en caché
            self.cache[cache_key] = {
                "data": resultado,
                "timestamp": time.time()
            }
            
            return ResultadoTarea(
                exito=response.status_code < 400,
                datos=resultado
            )
            
        except requests.Timeout:
            return ResultadoTarea(exito=False, error=f"Timeout ({timeout}s)")
        except requests.ConnectionError:
            return ResultadoTarea(exito=False, error=f"No se pudo conectar a {url}")
        except Exception as e:
            return ResultadoTarea(exito=False, error=str(e))
    
    # ============================================================
    # HTTP POST
    # ============================================================
    
    async def _http_post(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Realiza petición POST"""
        url = parametros.get("url") or self._extraer_url(desc)
        
        if not url:
            return ResultadoTarea(exito=False, error="Especifica una URL")
        
        data = parametros.get("data")
        json_data = parametros.get("json")
        headers = parametros.get("headers", {})
        timeout = parametros.get("timeout", 30)
        
        try:
            self.logger.info(f"POST {url}")
            
            if json_data:
                response = self.session.post(
                    url, 
                    json=json_data, 
                    headers=headers, 
                    timeout=timeout
                )
            else:
                response = self.session.post(
                    url, 
                    data=data, 
                    headers=headers, 
                    timeout=timeout
                )
            
            resultado = {
                "url": url,
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "content": response.text,
                "tiempo": response.elapsed.total_seconds()
            }
            
            return ResultadoTarea(
                exito=response.status_code < 400,
                datos=resultado
            )
            
        except Exception as e:
            return ResultadoTarea(exito=False, error=str(e))
    
    # ============================================================
    # SCRAPING
    # ============================================================
    
    async def _scraping(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Extrae información de una página web"""
        url = parametros.get("url") or self._extraer_url(desc)
        
        if not url:
            return ResultadoTarea(exito=False, error="Especifica una URL")
        
        selectores = parametros.get("selectores", {})
        
        # Si no hay selectores, extraer selectores comunes de la descripción
        if not selectores:
            selectores = self._extraer_selectores(desc)
        
        try:
            self.logger.info(f"Scraping {url}")
            response = self.session.get(url, timeout=30)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            resultados = {}
            
            # Extraer según selectores
            for nombre, selector in selectores.items():
                if selector.startswith("."):  # clase CSS
                    elementos = soup.select(selector)
                    resultados[nombre] = [e.get_text(strip=True) for e in elementos]
                elif selector.startswith("#"):  # id
                    elemento = soup.select_one(selector)
                    resultados[nombre] = elemento.get_text(strip=True) if elemento else None
                elif selector == "title":
                    resultados["titulo"] = soup.title.string if soup.title else None
                elif selector == "links":
                    resultados["links"] = [a.get("href") for a in soup.find_all("a") if a.get("href")]
                elif selector == "images":
                    resultados["imagenes"] = [img.get("src") for img in soup.find_all("img") if img.get("src")]
                elif selector == "text":
                    resultados["texto"] = soup.get_text(strip=True)
                else:
                    elementos = soup.find_all(selector)
                    resultados[nombre] = [e.get_text(strip=True) for e in elementos]
            
            return ResultadoTarea(
                exito=True,
                datos={
                    "url": url,
                    "selectores_usados": selectores,
                    "resultados": resultados
                }
            )
            
        except Exception as e:
            return ResultadoTarea(exito=False, error=f"Error en scraping: {str(e)}")
    
    # ============================================================
    # MONITOREAR WEB
    # ============================================================
    
    async def _monitorear_web(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Monitorea cambios en una página web"""
        url = parametros.get("url") or self._extraer_url(desc)
        
        if not url:
            return ResultadoTarea(exito=False, error="Especifica una URL")
        
        intervalo = parametros.get("intervalo", 300)  # 5 minutos por defecto
        selector = parametros.get("selector", "body")
        notificar_cambios = parametros.get("notificar", True)
        
        # Obtener contenido actual
        try:
            response = self.session.get(url, timeout=30)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            if selector == "body":
                contenido_actual = response.text
            else:
                elemento = soup.select_one(selector)
                contenido_actual = elemento.get_text(strip=True) if elemento else ""
            
            # Guardar hash para comparar después
            hash_actual = hashlib.md5(contenido_actual.encode()).hexdigest()
            
            # Función de monitoreo (se ejecutará en loop)
            def monitorear():
                import time
                while True:
                    time.sleep(intervalo)
                    try:
                        nueva_resp = self.session.get(url, timeout=30)
                        nuevo_soup = BeautifulSoup(nueva_resp.text, 'html.parser')
                        
                        if selector == "body":
                            nuevo_contenido = nueva_resp.text
                        else:
                            nuevo_elemento = nuevo_soup.select_one(selector)
                            nuevo_contenido = nuevo_elemento.get_text(strip=True) if nuevo_elemento else ""
                        
                        nuevo_hash = hashlib.md5(nuevo_contenido.encode()).hexdigest()
                        
                        if nuevo_hash != hash_actual:
                            self.logger.info(f"Cambio detectado en {url}")
                            if notificar_cambios:
                                self._notificar_cambio(url, selector)
                            hash_actual = nuevo_hash
                            
                    except Exception as e:
                        self.logger.error(f"Error monitoreando {url}: {e}")
            
            # Iniciar monitoreo en thread separado
            import threading
            thread = threading.Thread(target=monitorear, daemon=True)
            thread.start()
            
            return ResultadoTarea(
                exito=True,
                datos={
                    "url": url,
                    "selector": selector,
                    "intervalo": intervalo,
                    "estado": "monitoreando",
                    "mensaje": f"Monitoreando {url} cada {intervalo} segundos"
                }
            )
            
        except Exception as e:
            return ResultadoTarea(exito=False, error=f"Error iniciando monitoreo: {str(e)}")
    
    def _notificar_cambio(self, url: str, selector: str):
        """Notificar cambio en la página"""
        # Crear tarea de notificación en el supervisor
        self.supervisor.create_task(
            task_type="notificar",
            data={
                "mensaje": f"📢 Cambio detectado en {url}\nSelector: {selector}",
                "nivel": "info"
            },
            source="web_monitor"
        )
    
    # ============================================================
    # API CONSUMIR
    # ============================================================
    
    async def _api_consumir(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Consume una API REST"""
        url = parametros.get("url") or self._extraer_url(desc)
        metodo = parametros.get("metodo", "GET").upper()
        datos = parametros.get("datos", {})
        headers = parametros.get("headers", {})
        
        if not url:
            return ResultadoTarea(exito=False, error="Especifica la URL de la API")
        
        try:
            self.logger.info(f"API {metodo} {url}")
            
            if metodo == "GET":
                response = self.session.get(url, headers=headers, params=datos, timeout=30)
            elif metodo == "POST":
                response = self.session.post(url, json=datos, headers=headers, timeout=30)
            elif metodo == "PUT":
                response = self.session.put(url, json=datos, headers=headers, timeout=30)
            elif metodo == "DELETE":
                response = self.session.delete(url, headers=headers, timeout=30)
            else:
                return ResultadoTarea(exito=False, error=f"Método no soportado: {metodo}")
            
            # Intentar parsear JSON
            try:
                contenido = response.json()
            except:
                contenido = response.text
            
            return ResultadoTarea(
                exito=response.status_code < 400,
                datos={
                    "url": url,
                    "metodo": metodo,
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "contenido": contenido
                }
            )
            
        except Exception as e:
            return ResultadoTarea(exito=False, error=str(e))
    
    # ============================================================
    # WEBHOOK
    # ============================================================
    
    async def _webhook(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Envía un webhook a una URL"""
        url = parametros.get("url") or self._extraer_url(desc)
        payload = parametros.get("payload", {})
        
        if not url:
            return ResultadoTarea(exito=False, error="Especifica la URL del webhook")
        
        # Si no hay payload, crear uno básico
        if not payload:
            payload = {
                "event": "swarmia_webhook",
                "timestamp": datetime.now().isoformat(),
                "data": {"mensaje": desc}
            }
        
        try:
            self.logger.info(f"Webhook a {url}")
            response = self.session.post(url, json=payload, timeout=10)
            
            return ResultadoTarea(
                exito=response.status_code < 400,
                datos={
                    "url": url,
                    "status_code": response.status_code,
                    "response": response.text[:500]
                }
            )
            
        except Exception as e:
            return ResultadoTarea(exito=False, error=str(e))
    
    # ============================================================
    # VERIFICAR URL
    # ============================================================
    
    async def _verificar_url(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Verifica si una URL está disponible"""
        url = parametros.get("url") or self._extraer_url(desc)
        
        if not url:
            return ResultadoTarea(exito=False, error="Especifica una URL")
        
        try:
            start = time.time()
            response = self.session.get(url, timeout=10, stream=True)
            response.close()
            
            tiempo = (time.time() - start) * 1000
            
            return ResultadoTarea(
                exito=response.status_code < 500,
                datos={
                    "url": url,
                    "status_code": response.status_code,
                    "tiempo_ms": round(tiempo, 2),
                    "disponible": response.status_code < 500
                }
            )
            
        except requests.Timeout:
            return ResultadoTarea(
                exito=False,
                datos={"url": url, "disponible": False, "error": "timeout"}
            )
        except Exception as e:
            return ResultadoTarea(
                exito=False,
                datos={"url": url, "disponible": False, "error": str(e)}
            )
    
    # ============================================================
    # DESCARGAR ARCHIVO
    # ============================================================
    
    async def _descargar_archivo(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Descarga un archivo desde una URL"""
        url = parametros.get("url") or self._extraer_url(desc)
        destino = parametros.get("destino")
        
        if not url:
            return ResultadoTarea(exito=False, error="Especifica una URL")
        
        if not destino:
            # Extraer nombre del archivo de la URL
            nombre = url.split("/")[-1].split("?")[0]
            if not nombre:
                nombre = "descarga"
            destino = f"./{nombre}"
        
        try:
            self.logger.info(f"Descargando {url} -> {destino}")
            response = self.session.get(url, stream=True, timeout=60)
            
            with open(destino, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            import os
            tamaño = os.path.getsize(destino)
            
            return ResultadoTarea(
                exito=True,
                datos={
                    "url": url,
                    "destino": destino,
                    "tamaño_bytes": tamaño,
                    "tamaño_mb": round(tamaño / (1024 * 1024), 2)
                }
            )
            
        except Exception as e:
            return ResultadoTarea(exito=False, error=str(e))
    
    # ============================================================
    # EXTRACTORES
    # ============================================================
    
    def _extraer_url(self, desc: str) -> Optional[str]:
        """Extrae URL de la descripción"""
        url_pattern = r'https?://[^\s]+'
        match = re.search(url_pattern, desc)
        if match:
            return match.group(0)
        return None
    
    def _extraer_selectores(self, desc: str) -> Dict[str, str]:
        """Extrae selectores de la descripción"""
        selectores = {}
        
        # Buscar patrones comunes
        if "titulo" in desc or "title" in desc:
            selectores["titulo"] = "title"
        
        if "links" in desc or "enlaces" in desc:
            selectores["links"] = "links"
        
        if "imagenes" in desc or "images" in desc:
            selectores["imagenes"] = "images"
        
        # Buscar selectores específicos
        clase_match = re.search(r'clase\s+([a-zA-Z0-9_-]+)', desc)
        if clase_match:
            selectores[f"elementos_{clase_match.group(1)}"] = f".{clase_match.group(1)}"
        
        id_match = re.search(r'id\s+([a-zA-Z0-9_-]+)', desc)
        if id_match:
            selectores[f"elemento_{id_match.group(1)}"] = f"#{id_match.group(1)}"
        
        if not selectores:
            selectores["contenido"] = "body"
        
        return selectores


# ============================================================
# Factory Function
# ============================================================

def crear_agente_web(supervisor: Supervisor, config: Config) -> AgenteWeb:
    """Crea instancia del agente web"""
    return AgenteWeb(supervisor, config)
