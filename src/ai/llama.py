#!/usr/bin/env python3
"""
Llama Local Model Handler for SwarmIA
Handles local Llama models (GGUF format) using llama-cpp-python
"""

import os
import json
import time
import logging
import threading
import queue
import subprocess
from typing import Dict, List, Optional, Any, Iterator
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field


# ============================================================
# Data Classes
# ============================================================

@dataclass
class LlamaRequest:
    """Request for Llama model"""
    request_id: str
    prompt: str
    messages: List[Dict[str, str]] = field(default_factory=list)
    temperature: float = 0.7
    max_tokens: int = 2048
    top_p: float = 0.9
    top_k: int = 40
    repeat_penalty: float = 1.1
    stop: List[str] = field(default_factory=lambda: ["</s>", "User:", "Assistant:"])
    stream: bool = False


@dataclass
class LlamaResponse:
    """Response from Llama model"""
    request_id: str
    content: str
    success: bool
    error: Optional[str] = None
    tokens: int = 0
    processing_time: float = 0.0


# ============================================================
# Exceptions
# ============================================================

class LlamaError(Exception):
    """Base exception for Llama errors"""
    pass


class LlamaModelNotFoundError(LlamaError):
    """Model file not found"""
    pass


class LlamaLoadError(LlamaError):
    """Error loading model"""
    pass


class LlamaTimeoutError(LlamaError):
    """Request timeout"""
    pass


# ============================================================
# Llama Handler
# ============================================================

class LlamaHandler:
    """
    Handler for local Llama models using llama-cpp-python
    Falls back to simulation if library not installed
    """
    
    def __init__(self, model_path: str, model_name: str = "Local Llama"):
        """
        Initialize Llama handler
        
        Args:
            model_path: Path to GGUF model file
            model_name: Display name for the model
        """
        self.model_path = Path(model_path)
        self.model_name = model_name
        self.logger = self._setup_logger()
        self._llama = None
        
        # Check if model exists
        if not self.model_path.exists():
            raise LlamaModelNotFoundError(f"Archivo de modelo no encontrado: {model_path}")
        
        # Model info
        self.model_info = self._get_model_info()
        
        # Processing queue
        self.request_queue = queue.Queue()
        self.response_queue = queue.Queue()
        self.processing_thread = None
        self.running = False
        
        # Statistics
        self.stats = {
            "requests_processed": 0,
            "tokens_generated": 0,
            "errors": 0,
            "start_time": datetime.now()
        }
        
        # Try to load actual model
        self._try_load_model()
        
        self.logger.info(f"Handler de Llama inicializado con modelo: {model_name}")
    
    def _setup_logger(self) -> logging.Logger:
        """Setup logger"""
        logger = logging.getLogger("swarmia.ai.llama")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _try_load_model(self):
        """Try to load actual Llama model using llama-cpp-python"""
        try:
            from llama_cpp import Llama
            
            self.logger.info(f"Cargando modelo Llama desde: {self.model_path}")
            
            self._llama = Llama(
                model_path=str(self.model_path),
                n_ctx=4096,           # Context size
                n_threads=4,          # CPU threads
                n_gpu_layers=0,       # GPU layers (0 = CPU only)
                verbose=False
            )
            
            self.logger.info("Modelo Llama cargado correctamente")
            self._using_real_model = True
            
        except ImportError:
            self.logger.warning("llama-cpp-python no instalado. Usando modo simulación.")
            self.logger.warning("Instalar con: pip install llama-cpp-python")
            self._using_real_model = False
        except Exception as e:
            self.logger.warning(f"No se pudo cargar modelo real: {e}. Usando modo simulación.")
            self._using_real_model = False
    
    def _get_model_info(self) -> Dict:
        """Get model information from file"""
        file_size = self.model_path.stat().st_size
        file_name = self.model_path.name
        
        info = {
            "path": str(self.model_path),
            "size_gb": round(file_size / (1024**3), 2),
            "size_mb": round(file_size / (1024**2), 2),
            "filename": file_name,
            "format": "GGUF" if file_name.endswith(".gguf") else "Desconocido"
        }
        
        # Detect model family
        name_lower = file_name.lower()
        if "qwen" in name_lower:
            info["family"] = "Qwen"
        elif "llama" in name_lower or "llama" in name_lower:
            info["family"] = "Llama"
        elif "mistral" in name_lower:
            info["family"] = "Mistral"
        elif "phi" in name_lower:
            info["family"] = "Phi"
        elif "gemma" in name_lower:
            info["family"] = "Gemma"
        elif "deepseek" in name_lower:
            info["family"] = "DeepSeek"
        else:
            info["family"] = "Desconocido"
        
        # Detect quantization
        quant_patterns = ["q4_k_m", "q4_k_s", "q5_k_m", "q5_k_s", "q6_k", "q8_0", "f16", "fp16", "q2_k"]
        for pattern in quant_patterns:
            if pattern in name_lower:
                info["quantization"] = pattern
                break
        
        # Detect size (7B, 13B, 70B, etc)
        size_patterns = ["7b", "13b", "34b", "70b", "8b", "3b", "1b", "72b"]
        for pattern in size_patterns:
            if pattern in name_lower:
                info["size"] = pattern.upper()
                break
        
        return info
    
    def start(self) -> bool:
        """Start the model processing thread"""
        if self.running:
            self.logger.warning("Handler de Llama ya está en ejecución")
            return True
        
        self.running = True
        self.processing_thread = threading.Thread(
            target=self._process_requests,
            daemon=True,
            name="llama-processor"
        )
        self.processing_thread.start()
        
        self.logger.info("Handler de Llama iniciado")
        return True
    
    def stop(self):
        """Stop the model processing thread"""
        self.running = False
        
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=5)
            self.processing_thread = None
        
        # Clear queues
        self._clear_queues()
        
        self.logger.info("Handler de Llama detenido")
    
    def _clear_queues(self):
        """Clear pending requests"""
        while not self.request_queue.empty():
            try:
                self.request_queue.get_nowait()
                self.request_queue.task_done()
            except queue.Empty:
                break
        
        while not self.response_queue.empty():
            try:
                self.response_queue.get_nowait()
                self.response_queue.task_done()
            except queue.Empty:
                break
    
    def _process_requests(self):
        """Process requests from queue"""
        while self.running:
            try:
                request = self.request_queue.get(timeout=1)
                self._handle_request(request)
                self.request_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Error procesando solicitud: {e}")
                self.stats["errors"] += 1
    
    def _handle_request(self, request: LlamaRequest):
        """Handle a single request"""
        start_time = time.time()
        
        try:
            self.logger.debug(f"Procesando solicitud {request.request_id}")
            
            # Generate response using real model or simulation
            if self._using_real_model and self._llama:
                content = self._generate_with_llama(request)
            else:
                content = self._generate_simulated(request)
            
            processing_time = time.time() - start_time
            tokens = len(content.split())
            
            # Update stats
            self.stats["requests_processed"] += 1
            self.stats["tokens_generated"] += tokens
            
            # Create response
            response = LlamaResponse(
                request_id=request.request_id,
                content=content,
                success=True,
                tokens=tokens,
                processing_time=processing_time
            )
            
        except Exception as e:
            self.logger.error(f"Error en solicitud {request.request_id}: {e}")
            self.stats["errors"] += 1
            
            response = LlamaResponse(
                request_id=request.request_id,
                content="",
                success=False,
                error=str(e),
                processing_time=time.time() - start_time
            )
        
        # Put response in queue
        self.response_queue.put(response)
    
    def _generate_with_llama(self, request: LlamaRequest) -> str:
        """
        Generate response using actual llama-cpp-python
        
        Args:
            request: LlamaRequest object
        
        Returns:
            Generated text
        """
        # Build prompt from messages
        prompt = self._messages_to_prompt(request.messages) if request.messages else request.prompt
        
        # Generate
        output = self._llama(
            prompt=prompt,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            top_p=request.top_p,
            top_k=request.top_k,
            repeat_penalty=request.repeat_penalty,
            stop=request.stop,
            echo=False
        )
        
        # Extract response text
        if "choices" in output and len(output["choices"]) > 0:
            return output["choices"][0]["text"].strip()
        else:
            raise LlamaError("No se recibió respuesta del modelo")
    
    def _generate_simulated(self, request: LlamaRequest) -> str:
        """
        Simulate Llama response (fallback when llama-cpp not available)
        
        Args:
            request: LlamaRequest object
        
        Returns:
            Simulated response
        """
        # Build prompt
        prompt = self._messages_to_prompt(request.messages) if request.messages else request.prompt
        
        # Simulate model-specific responses
        model_family = self.model_info.get("family", "Desconocido")
        
        responses = {
            "Llama": [
                f"Como modelo Llama, entiendo tu consulta sobre '{prompt[:50]}...'. Mi análisis indica que...",
                f"Según mi conocimiento como modelo Llama, puedo ayudarte con eso. {prompt[:100]}",
                f"Basado en mi entrenamiento, aquí está mi respuesta: {prompt[:100]}"
            ],
            "Qwen": [
                f"Como modelo Qwen, procesaré tu solicitud sobre '{prompt[:50]}...'.",
                f"Qwen al servicio: {prompt[:100]}",
                f"Analizando tu consulta como Qwen: {prompt[:100]}"
            ],
            "Mistral": [
                f"Mistral responde a tu pregunta: {prompt[:100]}",
                f"Como modelo Mistral, puedo ayudarte con eso. {prompt[:100]}"
            ],
            "Phi": [
                f"Phi-3 procesando tu consulta: {prompt[:100]}",
                f"Según Phi-3: {prompt[:100]}"
            ]
        }
        
        import random
        default_responses = [
            f"Procesando tu consulta sobre '{prompt[:50]}...'. Aquí está mi respuesta.",
            f"He analizado tu pregunta: '{prompt[:100]}'. Mi respuesta es:",
            f"Entiendo tu consulta. Mi modelo local ha procesado: {prompt[:100]}"
        ]
        
        response_template = responses.get(model_family, default_responses)
        response = random.choice(response_template)
        
        # Add system message context if available
        if request.messages:
            for msg in request.messages:
                if msg.get("role") == "system":
                    response = f"[Contexto del sistema] {response}"
                    break
        
        # Simulate processing time
        time.sleep(0.3)
        
        return response
    
    def _messages_to_prompt(self, messages: List[Dict[str, str]]) -> str:
        """
        Convert messages list to prompt string
        
        Args:
            messages: List of message dicts
        
        Returns:
            Formatted prompt
        """
        prompt_parts = []
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                prompt_parts.append(f"System: {content}")
            elif role == "user":
                prompt_parts.append(f"User: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")
        
        # Add assistant prefix for completion
        if not messages or messages[-1].get("role") != "assistant":
            prompt_parts.append("Assistant: ")
        
        return "\n".join(prompt_parts)
    
    def chat_completion(self, 
                       messages: List[Dict[str, str]], 
                       temperature: float = 0.7,
                       max_tokens: int = 2048,
                       timeout: int = 60) -> Dict:
        """
        Get chat completion from local model
        
        Args:
            messages: List of message dicts
            temperature: Creativity (0.0 to 1.0)
            max_tokens: Maximum tokens
            timeout: Request timeout in seconds
        
        Returns:
            Response dict
        """
        # Create request
        request_id = f"req_{int(time.time() * 1000)}_{self.stats['requests_processed']}"
        
        request = LlamaRequest(
            request_id=request_id,
            prompt="",
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        # Queue request
        self.request_queue.put(request)
        
        # Wait for response with timeout
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                response = self.response_queue.get(timeout=0.1)
                if response.request_id == request_id:
                    if response.success:
                        return {
                            "choices": [{
                                "message": {
                                    "role": "assistant",
                                    "content": response.content
                                }
                            }],
                            "usage": {
                                "prompt_tokens": sum(len(m.get("content", "").split()) for m in messages),
                                "completion_tokens": response.tokens,
                                "total_tokens": response.tokens + sum(len(m.get("content", "").split()) for m in messages)
                            },
                            "model": self.model_name,
                            "processing_time": response.processing_time
                        }
                    else:
                        raise LlamaError(response.error)
            except queue.Empty:
                continue
        
        raise LlamaTimeoutError(f"Timeout después de {timeout} segundos")
    
    def quick_chat(self, prompt: str, system_message: str = None, **kwargs) -> str:
        """
        Quick chat interface
        
        Args:
            prompt: User prompt
            system_message: Optional system message
            **kwargs: Additional parameters
        
        Returns:
            Assistant response
        """
        messages = []
        
        if system_message:
            messages.append({"role": "system", "content": system_message})
        
        messages.append({"role": "user", "content": prompt})
        
        response = self.chat_completion(messages, **kwargs)
        
        if "choices" in response and len(response["choices"]) > 0:
            return response["choices"][0]["message"]["content"]
        else:
            raise LlamaError("No se recibió respuesta del modelo")
    
    def check_connection(self) -> Dict[str, Any]:
        """
        Check if model is accessible
        
        Returns:
            Dict with connection status
        """
        info = {
            "connected": self.model_path.exists(),
            "model_path": str(self.model_path),
            "model_exists": self.model_path.exists(),
            "file_size_gb": self.model_info.get("size_gb", 0),
            "using_real_model": self._using_real_model
        }
        
        if not self.model_path.exists():
            info["error"] = "Archivo de modelo no encontrado"
        elif not self._using_real_model:
            info["warning"] = "Usando modo simulación. Instala llama-cpp-python para usar modelo real"
        
        return info
    
    def get_models(self) -> List[str]:
        """
        Get available models in same directory
        
        Returns:
            List of available model files
        """
        model_dir = self.model_path.parent
        models = []
        
        if model_dir.exists():
            for file in model_dir.iterdir():
                if file.suffix.lower() in ['.gguf', '.bin', '.pt', '.safetensors']:
                    models.append(file.name)
        
        return models if models else [self.model_path.name]
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get handler statistics
        
        Returns:
            Dict with handler statistics
        """
        uptime = datetime.now() - self.stats["start_time"]
        
        return {
            "provider": "Local Llama",
            "model_name": self.model_name,
            "model_path": str(self.model_path),
            "model_info": self.model_info,
            "using_real_model": self._using_real_model,
            "stats": {
                "requests_processed": self.stats["requests_processed"],
                "tokens_generated": self.stats["tokens_generated"],
                "errors": self.stats["errors"],
                "uptime": str(uptime).split('.')[0],
                "queue_size": self.request_queue.qsize()
            },
            "running": self.running,
            "timestamp": datetime.now().isoformat()
        }


# ============================================================
# Factory Function
# ============================================================

def create_llama_handler(model_path: str, model_name: str = "Local Llama") -> LlamaHandler:
    """
    Create Llama handler instance
    
    Args:
        model_path: Path to model file
        model_name: Name for the model
    
    Returns:
        LlamaHandler instance
    """
    return LlamaHandler(model_path, model_name)


# ============================================================
# Example Usage
# ============================================================

def example_usage():
    """Example of using Llama handler"""
    import os
    
    print("🚀 Probando Handler de Llama\n")
    
    # Example model path - adjust to your system
    model_path = os.getenv("LLAMA_MODEL_PATH", "/path/to/your/model.gguf")
    
    # Check if model exists
    if not os.path.exists(model_path):
        print(f"⚠️  Archivo de modelo no encontrado: {model_path}")
        print("💡 Usando modo simulación con ruta dummy")
        model_path = "/tmp/dummy.gguf"
    
    try:
        handler = create_llama_handler(model_path, "Mi Modelo Local")
        
        # Start handler
        if handler.start():
            print("✅ Handler de Llama iniciado\n")
            
            # Check connection
            connection = handler.check_connection()
            print("📡 Estado de conexión:")
            for key, value in connection.items():
                print(f"  {key}: {value}")
            
            if connection["connected"]:
                print("\n🤖 Probando chat...")
                
                # Quick chat
                response = handler.quick_chat(
                    "¿Qué puedes hacer?",
                    system_message="Eres un asistente útil y conciso."
                )
                print(f"Respuesta: {response}\n")
                
                # Get stats
                stats = handler.get_stats()
                print("📊 Estadísticas:")
                print(f"  Modelo: {stats['model_name']}")
                print(f"  Tamaño: {stats['model_info'].get('size_gb', 0)} GB")
                print(f"  Familia: {stats['model_info'].get('family', 'Desconocido')}")
                print(f"  Usando modelo real: {stats['using_real_model']}")
                print(f"  Solicitudes procesadas: {stats['stats']['requests_processed']}")
                print(f"  Tokens generados: {stats['stats']['tokens_generated']}")
            
            # Stop handler
            handler.stop()
            print("\n🛑 Handler de Llama detenido")
        else:
            print("❌ Error al iniciar handler")
            
    except LlamaModelNotFoundError as e:
        print(f"❌ {e}")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    example_usage()
