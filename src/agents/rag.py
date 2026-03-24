#!/usr/bin/env python3
"""
Agente RAG - Retrieval Augmented Generation (Memoria a largo plazo)
Soporta: Embeddings, búsqueda vectorial, memoria persistente, contexto histórico
Capacidades: almacenar conocimiento, buscar, recordar, aprender de conversaciones
"""

import os
import sys
import json
import hashlib
import pickle
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from collections import defaultdict
import asyncio

# Importaciones opcionales para embeddings
try:
    import chromadb
    from chromadb.utils import embedding_functions
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False

from src.core.agente import Agente, TipoAgente, ResultadoTarea
from src.core.supervisor import Supervisor
from src.core.config import Config


class AgenteRAG(Agente):
    """
    Agente RAG - Memoria a largo plazo y búsqueda semántica
    Permite a SwarmIA recordar conversaciones anteriores y buscar información relevante
    """
    
    def __init__(self, supervisor: Supervisor, config: Config):
        super().__init__(
            id_agente="rag",
            nombre="Agente RAG",
            tipo=TipoAgente.RAG,
            supervisor=supervisor,
            version="1.0.0"
        )
        self.config = config
        
        # Directorio de memoria
        self.memoria_dir = Path("data/memoria")
        self.memoria_dir.mkdir(parents=True, exist_ok=True)
        
        # Almacenamiento
        self.memoria: List[Dict] = []
        self.conversaciones: Dict[str, List[Dict]] = {}
        self.conocimiento: Dict[str, Any] = {}
        self.embeddings: Dict[str, List[float]] = {}
        
        # Configuración
        self.max_memoria = int(os.getenv("RAG_MAX_MEMORY", "10000"))
        self.similaridad_umbral = float(os.getenv("RAG_SIMILARITY_THRESHOLD", "0.7"))
        
        # Cliente ChromaDB
        self.chroma_client = None
        self.collection = None
        self.embedding_model = None
        
        self._inicializar()
        self._registrar_capacidades()
        self.logger.info("Agente RAG iniciado")
    
    def _inicializar(self):
        """Inicializar sistemas de memoria"""
        
        # Cargar memoria existente
        self._cargar_memoria()
        
        # Inicializar ChromaDB si está disponible
        if CHROMA_AVAILABLE:
            try:
                self.chroma_client = chromadb.PersistentClient(path=str(self.memoria_dir / "chroma"))
                
                # Crear o obtener colección
                self.collection = self.chroma_client.get_or_create_collection(
                    name="swarmia_memoria",
                    embedding_function=embedding_functions.SentenceTransformerEmbeddingFunction()
                )
                self.logger.info("ChromaDB inicializado")
            except Exception as e:
                self.logger.warning(f"Error inicializando ChromaDB: {e}")
        
        # Inicializar modelo de embeddings
        if TRANSFORMERS_AVAILABLE and not self.embedding_model:
            try:
                self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
                self.logger.info("Modelo de embeddings cargado")
            except Exception as e:
                self.logger.warning(f"Error cargando modelo: {e}")
    
    def _cargar_memoria(self):
        """Cargar memoria desde disco"""
        memoria_file = self.memoria_dir / "memoria.json"
        if memoria_file.exists():
            try:
                with open(memoria_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.memoria = data.get("memoria", [])
                    self.conocimiento = data.get("conocimiento", {})
                self.logger.info(f"Memoria cargada: {len(self.memoria)} items")
            except Exception as e:
                self.logger.error(f"Error cargando memoria: {e}")
    
    def _guardar_memoria(self):
        """Guardar memoria en disco"""
        memoria_file = self.memoria_dir / "memoria.json"
        try:
            with open(memoria_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "memoria": self.memoria[-self.max_memoria:],
                    "conocimiento": self.conocimiento,
                    "ultima_actualizacion": datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"Error guardando memoria: {e}")
    
    def _registrar_capacidades(self):
        """Registrar capacidades del agente"""
        
        self.registrar_capacidad(
            nombre="recordar",
            descripcion="Recordar información de conversaciones pasadas",
            parametros=["consulta"],
            ejemplos=["recordar qué hablamos sobre Python", "qué dijo el usuario la última vez"],
            nivel_riesgo="bajo"
        )
        
        self.registrar_capacidad(
            nombre="aprender",
            descripcion="Aprender nueva información",
            parametros=["informacion", "categoria"],
            ejemplos=["aprender que al usuario le gusta Python", "guardar configuración"],
            nivel_riesgo="bajo"
        )
        
        self.registrar_capacidad(
            nombre="olvidar",
            descripcion="Olvidar información específica",
            parametros=["consulta"],
            ejemplos=["olvidar conversación sobre X", "borrar memoria"],
            nivel_riesgo="medio"
        )
        
        self.registrar_capacidad(
            nombre="contexto",
            descripcion="Obtener contexto relevante para la conversación",
            parametros=["mensaje"],
            ejemplos=["contexto para ayudar mejor", "información relevante"],
            nivel_riesgo="bajo"
        )
        
        self.registrar_capacidad(
            nombre="resumir",
            descripcion="Resumir conversaciones pasadas",
            parametros=["sesion"],
            ejemplos=["resumir conversación", "qué hablamos hoy"],
            nivel_riesgo="bajo"
        )
        
        self.registrar_capacidad(
            nombre="estadisticas",
            descripcion="Ver estadísticas de memoria",
            ejemplos=["estadísticas de memoria", "cuánto recuerdo"],
            nivel_riesgo="bajo"
        )
    
    async def ejecutar(self, tarea: Dict[str, Any]) -> ResultadoTarea:
        """Ejecuta tarea según tipo"""
        tipo = tarea.get("tipo", "")
        desc = tarea.get("descripcion", "").lower()
        parametros = tarea.get("parametros", {})
        
        if "recordar" in tipo or "recordar" in desc:
            return await self._recordar(desc, parametros)
        
        elif "aprender" in tipo or "aprender" in desc or "guardar" in desc:
            return await self._aprender(desc, parametros)
        
        elif "olvidar" in tipo or "olvidar" in desc or "borrar" in desc:
            return await self._olvidar(desc, parametros)
        
        elif "contexto" in tipo or "contexto" in desc:
            return await self._contexto(desc, parametros)
        
        elif "resumir" in tipo or "resumir" in desc:
            return await self._resumir(desc, parametros)
        
        elif "estadisticas" in tipo or "estadisticas" in desc:
            return await self._estadisticas()
        
        else:
            return ResultadoTarea(exito=False, error=f"No sé cómo manejar: {tipo}")
    
    # ============================================================
    # FUNCIONES DE MEMORIA
    # ============================================================
    
    def _generar_embedding(self, texto: str) -> Optional[List[float]]:
        """Generar embedding para un texto"""
        if self.embedding_model:
            try:
                embedding = self.embedding_model.encode(texto)
                return embedding.tolist()
            except Exception as e:
                self.logger.error(f"Error generando embedding: {e}")
        return None
    
    def _buscar_similares(self, consulta: str, limite: int = 5) -> List[Dict]:
        """Buscar items similares en memoria"""
        resultados = []
        
        # Usar ChromaDB si está disponible
        if self.collection:
            try:
                results = self.collection.query(
                    query_texts=[consulta],
                    n_results=limite
                )
                for i, doc in enumerate(results['documents'][0]):
                    resultados.append({
                        "texto": doc,
                        "score": 1 - results['distances'][0][i] if results.get('distances') else 1.0,
                        "metadatos": results['metadatas'][0][i] if results.get('metadatas') else {}
                    })
            except Exception as e:
                self.logger.error(f"Error en búsqueda ChromaDB: {e}")
        
        # Fallback: búsqueda simple por palabras clave
        if not resultados:
            consulta_words = set(consulta.lower().split())
            for item in self.memoria:
                texto = item.get("texto", "").lower()
                coincidencias = sum(1 for word in consulta_words if word in texto)
                if coincidencias > 0:
                    score = coincidencias / len(consulta_words)
                    resultados.append({
                        "texto": item.get("texto"),
                        "score": score,
                        "metadatos": item.get("metadatos", {}),
                        "timestamp": item.get("timestamp")
                    })
            
            resultados.sort(key=lambda x: x["score"], reverse=True)
            resultados = resultados[:limite]
        
        return resultados
    
    def _guardar_memoria_item(self, texto: str, metadatos: Dict = None):
        """Guardar un item en memoria"""
        item = {
            "id": hashlib.md5(f"{texto}{datetime.now().isoformat()}".encode()).hexdigest()[:16],
            "texto": texto,
            "metadatos": metadatos or {},
            "timestamp": datetime.now().isoformat()
        }
        
        self.memoria.append(item)
        
        # Guardar en ChromaDB
        if self.collection:
            try:
                self.collection.add(
                    ids=[item["id"]],
                    documents=[texto],
                    metadatas=[item["metadatos"]]
                )
            except Exception as e:
                self.logger.error(f"Error guardando en ChromaDB: {e}")
        
        # Limitar tamaño
        if len(self.memoria) > self.max_memoria:
            self.memoria = self.memoria[-self.max_memoria:]
        
        self._guardar_memoria()
    
    # ============================================================
    # MÉTODOS PRINCIPALES
    # ============================================================
    
    async def _recordar(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Recordar información relevante"""
        consulta = parametros.get("consulta") or self._extraer_consulta(desc)
        
        if not consulta:
            return ResultadoTarea(exito=False, error="¿Qué quieres que recuerde?")
        
        resultados = self._buscar_similares(consulta, limite=5)
        
        if not resultados:
            return ResultadoTarea(
                exito=True,
                datos={"mensaje": "No recuerdo información sobre eso", "resultados": []}
            )
        
        # Formatear resultados
        items = []
        for r in resultados:
            if r["score"] > self.similaridad_umbral:
                items.append({
                    "texto": r["texto"],
                    "relevancia": round(r["score"] * 100, 1),
                    "timestamp": r.get("metadatos", {}).get("timestamp", r.get("timestamp"))
                })
        
        if not items:
            return ResultadoTarea(
                exito=True,
                datos={"mensaje": "No encontré nada muy relevante", "resultados": []}
            )
        
        return ResultadoTarea(
            exito=True,
            datos={
                "consulta": consulta,
                "resultados": items,
                "total": len(items),
                "mensaje": f"Encontré {len(items)} recuerdos relevantes"
            }
        )
    
    async def _aprender(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Aprender nueva información"""
        informacion = parametros.get("informacion") or self._extraer_informacion(desc)
        categoria = parametros.get("categoria", "general")
        
        if not informacion:
            return ResultadoTarea(exito=False, error="¿Qué quieres que aprenda?")
        
        # Guardar en memoria
        self._guardar_memoria_item(informacion, {
            "categoria": categoria,
            "fuente": "usuario",
            "timestamp": datetime.now().isoformat()
        })
        
        # Guardar en conocimiento estructurado
        if categoria not in self.conocimiento:
            self.conocimiento[categoria] = []
        
        self.conocimiento[categoria].append({
            "informacion": informacion,
            "aprendido": datetime.now().isoformat()
        })
        
        self._guardar_memoria()
        
        return ResultadoTarea(
            exito=True,
            datos={
                "informacion": informacion[:100],
                "categoria": categoria,
                "mensaje": f"✅ He aprendido: {informacion[:100]}..."
            }
        )
    
    async def _olvidar(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Olvidar información"""
        consulta = parametros.get("consulta") or self._extraer_consulta(desc)
        
        if not consulta:
            return ResultadoTarea(exito=False, error="¿Qué quieres que olvide?")
        
        # Buscar items similares
        resultados = self._buscar_similares(consulta, limite=10)
        
        if not resultados:
            return ResultadoTarea(exito=False, error="No encontré nada que olvidar sobre eso")
        
        # Eliminar items con alta relevancia
        eliminados = []
        for r in resultados:
            if r["score"] > 0.8:
                # Encontrar y eliminar de memoria
                texto = r["texto"]
                self.memoria = [m for m in self.memoria if m.get("texto") != texto]
                eliminados.append(texto[:100])
        
        if eliminados:
            self._guardar_memoria()
            return ResultadoTarea(
                exito=True,
                datos={
                    "eliminados": eliminados,
                    "total": len(eliminados),
                    "mensaje": f"Olvidé {len(eliminados)} cosas sobre eso"
                }
            )
        else:
            return ResultadoTarea(
                exito=False,
                error="No encontré nada lo suficientemente relevante para olvidar"
            )
    
    async def _contexto(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Obtener contexto relevante para una conversación"""
        mensaje = parametros.get("mensaje") or desc
        
        # Buscar información relevante
        resultados = self._buscar_similares(mensaje, limite=3)
        
        # También buscar en conocimiento estructurado
        contexto = {
            "mensaje_actual": mensaje,
            "recuerdos": [],
            "conocimiento": []
        }
        
        for r in resultados:
            if r["score"] > self.similaridad_umbral:
                contexto["recuerdos"].append({
                    "texto": r["texto"],
                    "relevancia": r["score"]
                })
        
        # Agregar conocimiento de categorías relevantes
        for categoria, items in self.conocimiento.items():
            if categoria in mensaje.lower() or any(item["informacion"].lower() in mensaje.lower() for item in items[-3:]):
                contexto["conocimiento"].extend(items[-3:])
        
        return ResultadoTarea(
            exito=True,
            datos={
                "contexto": contexto,
                "recuerdos_encontrados": len(contexto["recuerdos"]),
                "conocimiento_relevante": len(contexto["conocimiento"])
            }
        )
    
    async def _resumir(self, desc: str, parametros: Dict) -> ResultadoTarea:
        """Resumir conversaciones pasadas"""
        sesion = parametros.get("sesion") or self._extraer_sesion(desc)
        
        # Buscar conversaciones de esta sesión
        conversaciones = []
        for item in self.memoria:
            if item.get("metadatos", {}).get("sesion") == sesion:
                conversaciones.append(item["texto"])
        
        if not conversaciones:
            return ResultadoTarea(
                exito=False,
                error=f"No encontré conversaciones para la sesión '{sesion or 'actual'}'"
            )
        
        # Generar resumen simple
        resumen = {
            "sesion": sesion or "actual",
            "total_mensajes": len(conversaciones),
            "primer_mensaje": conversaciones[0][:100] if conversaciones else None,
            "ultimo_mensaje": conversaciones[-1][:100] if conversaciones else None,
            "temas": self._extraer_temas(conversaciones)
        }
        
        return ResultadoTarea(
            exito=True,
            datos=resumen
        )
    
    async def _estadisticas(self) -> ResultadoTarea:
        """Ver estadísticas de memoria"""
        stats = {
            "total_recuerdos": len(self.memoria),
            "categorias": list(self.conocimiento.keys()),
            "conocimiento_por_categoria": {k: len(v) for k, v in self.conocimiento.items()},
            "max_capacidad": self.max_memoria,
            "porcentaje_uso": round(len(self.memoria) / self.max_memoria * 100, 1),
            "chromadb_activo": self.collection is not None,
            "modelo_embeddings": self.embedding_model is not None
        }
        
        return ResultadoTarea(
            exito=True,
            datos=stats
        )
    
    # ============================================================
    # UTILIDADES
    # ============================================================
    
    def _extraer_consulta(self, desc: str) -> Optional[str]:
        """Extraer consulta de la descripción"""
        import re
        # Buscar después de "recordar", "acerca de", etc.
        patterns = [
            r"recordar\s+(?:sobre|de|acerca de)?\s*(.+)",
            r"qué\s+(?:dijimos|hablamos|sabemos)\s+(?:sobre|de)?\s*(.+)",
            r"(?:buscar|encontrar)\s+(.+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, desc, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None
    
    def _extraer_informacion(self, desc: str) -> Optional[str]:
        """Extraer información para aprender"""
        import re
        patterns = [
            r"aprender\s+(?:que|de|sobre)?\s*(.+)",
            r"guardar\s+(?:que|la información)?\s*(.+)",
            r"recuerda\s+(?:que)?\s*(.+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, desc, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return desc if len(desc) < 200 else None
    
    def _extraer_sesion(self, desc: str) -> Optional[str]:
        """Extraer nombre de sesión"""
        import re
        match = re.search(r"(?:sesión|conversación)\s+([a-zA-Z0-9_-]+)", desc, re.IGNORECASE)
        if match:
            return match.group(1)
        return "default"
    
    def _extraer_temas(self, textos: List[str]) -> List[str]:
        """Extraer temas principales de textos"""
        # Simple extracción de palabras comunes
        palabras_comunes = ["el", "la", "los", "las", "de", "en", "que", "y", "a", "por", "para", "con"]
        todas_palabras = []
        
        for texto in textos:
            palabras = texto.lower().split()
            todas_palabras.extend([p for p in palabras if p not in palabras_comunes and len(p) > 3])
        
        # Contar frecuencias
        from collections import Counter
        contador = Counter(todas_palabras)
        
        return [palabra for palabra, _ in contador.most_common(5)]


# ============================================================
# Factory Function
# ============================================================

def crear_agente_rag(supervisor: Supervisor, config: Config) -> AgenteRAG:
    """Crea instancia del agente RAG"""
    return AgenteRAG(supervisor, config)
