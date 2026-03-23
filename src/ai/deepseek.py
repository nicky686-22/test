#!/usr/bin/env python3
"""
DeepSeek API Handler for SwarmIA
Handles communication with DeepSeek API with retry logic and error handling
"""

import os
import json
import time
import logging
import requests
from typing import Dict, List, Optional, Any, Iterator
from datetime import datetime
from functools import wraps


# ============================================================
# Decorators
# ============================================================

def retry_on_failure(max_retries=3, delay=1, backoff=2):
    """
    Decorator to retry API calls on failure
    
    Args:
        max_retries: Maximum number of retries
        delay: Initial delay in seconds
        backoff: Multiplier for delay after each retry
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            _delay = delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        time.sleep(_delay)
                        _delay *= backoff
                    else:
                        raise
            
            raise last_exception
        return wrapper
    return decorator


# ============================================================
# Exceptions
# ============================================================

class DeepSeekError(Exception):
    """Base exception for DeepSeek errors"""
    pass


class DeepSeekAPIError(DeepSeekError):
    """API error from DeepSeek"""
    pass


class DeepSeekRateLimitError(DeepSeekError):
    """Rate limit exceeded"""
    pass


class DeepSeekAuthenticationError(DeepSeekError):
    """Authentication failed"""
    pass


# ============================================================
# DeepSeek Handler
# ============================================================

class DeepSeekHandler:
    """Handler for DeepSeek API with retry logic and error handling"""
    
    def __init__(self, api_key: str, model: str = "deepseek-chat"):
        """
        Initialize DeepSeek handler
        
        Args:
            api_key: DeepSeek API key
            model: Model to use (deepseek-chat or deepseek-coder)
        """
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.deepseek.com/v1"
        self.logger = self._setup_logger()
        
        # Request timeout
        self.timeout = 30
        self.stream_timeout = 60
        
        # Session for connection pooling
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        })
        
        # Rate limiting tracking
        self._last_request_time = 0
        self._min_request_interval = 0.1  # 100ms between requests
        
        self.logger.info(f"Handler de DeepSeek inicializado con modelo: {model}")
    
    def _setup_logger(self) -> logging.Logger:
        """Setup logger"""
        logger = logging.getLogger("swarmia.ai.deepseek")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _rate_limit(self):
        """Implement rate limiting"""
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()
    
    def _handle_error(self, response: requests.Response) -> None:
        """
        Handle API error responses
        
        Args:
            response: Requests response object
        """
        status_code = response.status_code
        
        if status_code == 401:
            raise DeepSeekAuthenticationError(
                "Error de autenticación: Clave API inválida"
            )
        elif status_code == 429:
            # Rate limit exceeded
            retry_after = response.headers.get("Retry-After", 60)
            raise DeepSeekRateLimitError(
                f"Límite de tasa excedido. Reintentar después de {retry_after} segundos"
            )
        elif 400 <= status_code < 500:
            error_data = response.json() if response.text else {}
            error_message = error_data.get("error", {}).get("message", f"Error {status_code}")
            raise DeepSeekAPIError(f"Error de API: {error_message}")
        elif status_code >= 500:
            raise DeepSeekAPIError(f"Error del servidor DeepSeek: {status_code}")
    
    @retry_on_failure(max_retries=3, delay=1, backoff=2)
    def chat_completion(self, 
                       messages: List[Dict[str, str]], 
                       temperature: float = 0.7,
                       max_tokens: int = 4096,
                       top_p: float = 1.0,
                       frequency_penalty: float = 0.0,
                       presence_penalty: float = 0.0,
                       stream: bool = False) -> Dict:
        """
        Get chat completion from DeepSeek
        
        Args:
            messages: List of message dicts with role and content
            temperature: Creativity (0.0 to 1.0)
            max_tokens: Maximum tokens in response
            top_p: Nucleus sampling parameter
            frequency_penalty: Penalty for frequent tokens
            presence_penalty: Penalty for new topics
            stream: Whether to stream response
        
        Returns:
            Response dict with completion
        """
        url = f"{self.base_url}/chat/completions"
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
            "frequency_penalty": frequency_penalty,
            "presence_penalty": presence_penalty,
            "stream": stream
        }
        
        # Apply rate limiting
        self._rate_limit()
        
        try:
            self.logger.info(f"Enviando solicitud a DeepSeek API ({len(messages)} mensajes)")
            
            response = self.session.post(
                url, 
                json=payload, 
                timeout=self.stream_timeout if stream else self.timeout,
                stream=stream
            )
            
            if not response.ok:
                self._handle_error(response)
            
            if stream:
                # Return response object for streaming
                return response
            
            result = response.json()
            
            # Log token usage
            if "usage" in result:
                usage = result["usage"]
                self.logger.info(
                    f"Uso de tokens - Prompt: {usage.get('prompt_tokens', 0)}, "
                    f"Completado: {usage.get('completion_tokens', 0)}, "
                    f"Total: {usage.get('total_tokens', 0)}"
                )
            
            return result
            
        except requests.exceptions.Timeout:
            self.logger.error("Timeout en solicitud a DeepSeek API")
            raise DeepSeekAPIError("Timeout en la solicitud")
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error en solicitud a DeepSeek API: {e}")
            raise DeepSeekAPIError(f"Error de red: {e}")
    
    def chat_completion_stream(self, 
                              messages: List[Dict[str, str]],
                              temperature: float = 0.7,
                              max_tokens: int = 4096) -> Iterator[str]:
        """
        Get streaming chat completion from DeepSeek
        
        Args:
            messages: List of message dicts with role and content
            temperature: Creativity (0.0 to 1.0)
            max_tokens: Maximum tokens in response
        
        Yields:
            Text chunks as they arrive
        """
        response = self.chat_completion(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True
        )
        
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        if "choices" in chunk and len(chunk["choices"]) > 0:
                            delta = chunk["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                    except json.JSONDecodeError:
                        continue
    
    def quick_chat(self, prompt: str, system_message: str = None, **kwargs) -> str:
        """
        Quick chat interface
        
        Args:
            prompt: User prompt
            system_message: Optional system message
            **kwargs: Additional parameters for chat_completion
        
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
            raise DeepSeekAPIError("No se recibió respuesta de DeepSeek API")
    
    def quick_chat_stream(self, prompt: str, system_message: str = None, **kwargs) -> Iterator[str]:
        """
        Quick chat interface with streaming
        
        Args:
            prompt: User prompt
            system_message: Optional system message
            **kwargs: Additional parameters for chat_completion
        
        Yields:
            Text chunks as they arrive
        """
        messages = []
        
        if system_message:
            messages.append({"role": "system", "content": system_message})
        
        messages.append({"role": "user", "content": prompt})
        
        yield from self.chat_completion_stream(messages, **kwargs)
    
    def check_connection(self) -> Dict[str, Any]:
        """
        Check if API connection works
        
        Returns:
            Dict with connection status and info
        """
        try:
            test_messages = [{"role": "user", "content": "Say 'OK' if you're working."}]
            response = self.chat_completion(test_messages, max_tokens=10)
            
            return {
                "connected": True,
                "message": "Conexión exitosa",
                "model": self.model,
                "response": response.get("choices", [{}])[0].get("message", {}).get("content", "")
            }
        except DeepSeekAuthenticationError as e:
            return {
                "connected": False,
                "message": str(e),
                "error_type": "authentication"
            }
        except DeepSeekRateLimitError as e:
            return {
                "connected": False,
                "message": str(e),
                "error_type": "rate_limit"
            }
        except Exception as e:
            return {
                "connected": False,
                "message": f"Error de conexión: {e}",
                "error_type": "unknown"
            }
    
    def get_models(self) -> List[str]:
        """
        Get available models
        
        Returns:
            List of available model IDs
        """
        try:
            url = f"{self.base_url}/models"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            models_data = response.json()
            return [model["id"] for model in models_data.get("data", [])]
        except Exception as e:
            self.logger.warning(f"No se pudo obtener lista de modelos: {e}")
            return ["deepseek-chat", "deepseek-coder"]
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get handler statistics
        
        Returns:
            Dict with handler statistics
        """
        return {
            "provider": "DeepSeek",
            "model": self.model,
            "api_key_set": bool(self.api_key),
            "api_key_masked": self.api_key[:8] + "..." if self.api_key else "no configurada",
            "base_url": self.base_url,
            "timeout": self.timeout,
            "timestamp": datetime.now().isoformat(),
            "status": "ready" if self.api_key else "missing_api_key"
        }
    
    def close(self):
        """Close the session"""
        self.session.close()
        self.logger.info("Sesión de DeepSeek cerrada")


# ============================================================
# Factory Function
# ============================================================

def create_deepseek_handler(api_key: str, model: str = "deepseek-chat") -> DeepSeekHandler:
    """
    Create DeepSeek handler instance
    
    Args:
        api_key: DeepSeek API key
        model: Model to use
    
    Returns:
        DeepSeekHandler instance
    """
    return DeepSeekHandler(api_key, model)


# ============================================================
# Example Usage
# ============================================================

def example_usage():
    """Example of using DeepSeek handler"""
    import os
    
    print("🚀 Probando Handler de DeepSeek\n")
    
    # Get API key from environment or config
    api_key = os.getenv("DEEPSEEK_API_KEY", "")
    
    if not api_key:
        print("⚠️  Configura DEEPSEEK_API_KEY en variables de entorno")
        print("   export DEEPSEEK_API_KEY='tu-api-key-aqui'")
        return
    
    handler = create_deepseek_handler(api_key)
    
    # Test connection
    connection = handler.check_connection()
    if connection["connected"]:
        print("✅ Conexión a DeepSeek API exitosa\n")
        
        # Quick chat
        print("📝 Enviando mensaje de prueba...")
        response = handler.quick_chat(
            "Hola, ¿cómo estás? Cuéntame brevemente qué puedes hacer.",
            system_message="Eres un asistente útil y conciso."
        )
        print(f"🤖 Respuesta:\n{response[:200]}...\n")
        
        # Test streaming
        print("📡 Probando streaming...")
        full_response = ""
        for chunk in handler.quick_chat_stream(
            "Dame una lista de 3 consejos para ser productivo",
            system_message="Sé breve y conciso."
        ):
            full_response += chunk
            print(chunk, end="", flush=True)
        print("\n")
        
        # Get stats
        stats = handler.get_stats()
        print(f"📊 Estadísticas:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        # Get models
        models = handler.get_models()
        print(f"\n📋 Modelos disponibles: {', '.join(models)}")
        
    else:
        print(f"❌ Conexión fallida: {connection['message']}")
    
    handler.close()


if __name__ == "__main__":
    example_usage()
