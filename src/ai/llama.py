#!/usr/bin/env python3
"""
Llama Local Model Handler for SwarmIA
Handles local Llama models (GGUF format)
"""

import os
import json
import logging
import subprocess
import threading
import queue
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

class LlamaHandler:
    """Handler for local Llama models"""
    
    def __init__(self, model_path: str, model_name: str = "Local Llama"):
        self.model_path = Path(model_path)
        self.model_name = model_name
        self.logger = self._setup_logger()
        
        # Check if model exists
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")
        
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
        
        self.logger.info(f"Llama handler initialized with model: {model_name} ({model_path})")
    
    def _setup_logger(self):
        """Setup logger"""
        logger = logging.getLogger("swarmia.ai.llama")
        logger.setLevel(logging.INFO)
        return logger
    
    def _get_model_info(self) -> Dict:
        """Get model information from file"""
        # Simple model info extraction
        # In production, you might use llama.cpp or similar
        file_size = self.model_path.stat().st_size
        file_name = self.model_path.name
        
        # Try to parse GGUF info from filename
        info = {
            "path": str(self.model_path),
            "size_gb": round(file_size / (1024**3), 2),
            "filename": file_name,
            "format": "GGUF" if file_name.endswith(".gguf") else "Unknown"
        }
        
        # Common model patterns in filename
        if "qwen" in file_name.lower():
            info["family"] = "Qwen"
        elif "llama" in file_name.lower():
            info["family"] = "Llama"
        elif "mistral" in file_name.lower():
            info["family"] = "Mistral"
        elif "phi" in file_name.lower():
            info["family"] = "Phi"
        else:
            info["family"] = "Unknown"
        
        # Quantization detection
        quant_patterns = ["q4_k_m", "q5_k_m", "q6_k", "q8_0", "f16"]
        for pattern in quant_patterns:
            if pattern in file_name.lower():
                info["quantization"] = pattern
                break
        
        return info
    
    def start(self):
        """Start the model processing thread"""
        if self.running:
            self.logger.warning("Llama handler already running")
            return
        
        self.running = True
        self.processing_thread = threading.Thread(
            target=self._process_requests,
            daemon=True,
            name="llama-processor"
        )
        self.processing_thread.start()
        
        self.logger.info("Llama handler started")
        return True
    
    def stop(self):
        """Stop the model processing thread"""
        self.running = False
        
        if self.processing_thread:
            self.processing_thread.join(timeout=5)
            self.processing_thread = None
        
        self.logger.info("Llama handler stopped")
    
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
                self.logger.error(f"Error processing request: {e}")
                self.stats["errors"] += 1
    
    def _handle_request(self, request: Dict):
        """Handle a single request"""
        request_id = request.get("request_id")
        prompt = request.get("prompt")
        system_message = request.get("system_message")
        
        try:
            self.logger.info(f"Processing request {request_id}")
            
            # In production, this would call llama.cpp or similar
            # For now, simulate a response
            response = self._simulate_llama_response(prompt, system_message)
            
            # Update stats
            self.stats["requests_processed"] += 1
            self.stats["tokens_generated"] += len(response.split())
            
            # Put response in queue
            self.response_queue.put({
                "request_id": request_id,
                "response": response,
                "success": True
            })
            
        except Exception as e:
            self.logger.error(f"Failed to process request {request_id}: {e}")
            self.stats["errors"] += 1
            
            self.response_queue.put({
                "request_id": request_id,
                "error": str(e),
                "success": False
            })
    
    def _simulate_llama_response(self, prompt: str, system_message: str = None) -> str:
        """Simulate Llama response (placeholder for actual model inference)"""
        # This is a simulation - in production, integrate with llama.cpp, ollama, etc.
        
        responses = [
            f"I understand you're asking: '{prompt}'. As a local AI model, I can help with that.",
            f"Based on your query '{prompt}', here's what I think...",
            f"Great question! Regarding '{prompt}', my analysis suggests...",
            f"I've processed your request about '{prompt}'. Here's my response...",
            f"Thank you for your question. About '{prompt}', I believe..."
        ]
        
        import random
        response = random.choice(responses)
        
        # Add some context if system message provided
        if system_message:
            response = f"[System: {system_message}] {response}"
        
        # Simulate processing time
        time.sleep(0.5)
        
        return response
    
    def chat_completion(self, 
                       messages: List[Dict[str, str]], 
                       temperature: float = 0.7,
                       max_tokens: int = 1000) -> Dict:
        """
        Get chat completion from local model
        
        Args:
            messages: List of message dicts
            temperature: Creativity (0.0 to 1.0)
            max_tokens: Maximum tokens
        
        Returns:
            Response dict
        """
        # Convert messages to prompt
        prompt = self._messages_to_prompt(messages)
        
        # Create request
        request_id = f"req_{int(time.time())}_{self.stats['requests_processed']}"
        
        request = {
            "request_id": request_id,
            "prompt": prompt,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "messages": messages
        }
        
        # Queue request
        self.request_queue.put(request)
        
        # Wait for response (with timeout)
        start_time = time.time()
        timeout = 30  # seconds
        
        while time.time() - start_time < timeout:
            try:
                response = self.response_queue.get(timeout=0.1)
                if response["request_id"] == request_id:
                    if response["success"]:
                        return {
                            "choices": [{
                                "message": {
                                    "role": "assistant",
                                    "content": response["response"]
                                }
                            }],
                            "usage": {
                                "prompt_tokens": len(prompt.split()),
                                "completion_tokens": len(response["response"].split()),
                                "total_tokens": len(prompt.split()) + len(response["response"].split())
                            }
                        }
                    else:
                        raise ValueError(f"Request failed: {response.get('error')}")
            except queue.Empty:
                continue
        
        raise TimeoutError("Request timed out")
    
    def _messages_to_prompt(self, messages: List[Dict[str, str]]) -> str:
        """Convert messages list to prompt string"""
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
        
        return "\n".join(prompt_parts)
    
    def quick_chat(self, prompt: str, system_message: str = None) -> str:
        """
        Quick chat interface
        
        Args:
            prompt: User prompt
            system_message: Optional system message
        
        Returns:
            Assistant response
        """
        messages = []
        
        if system_message:
            messages.append({"role": "system", "content": system_message})
        
        messages.append({"role": "user", "content": prompt})
        
        response = self.chat_completion(messages)
        
        if "choices" in response and len(response["choices"]) > 0:
            return response["choices"][0]["message"]["content"]
        else:
            raise ValueError("No response from model")
    
    def check_connection(self) -> bool:
        """Check if model is accessible"""
        return self.model_path.exists() and self.model_path.stat().st_size > 0
    
    def get_models(self) -> List[str]:
        """Get available models (local files)"""
        model_dir = self.model_path.parent
        models = []
        
        if model_dir.exists():
            for file in model_dir.iterdir():
                if file.suffix.lower() in ['.gguf', '.bin', '.pt', '.safetensors']:
                    models.append(file.name)
        
        return models if models else [self.model_path.name]
    
    def get_stats(self) -> Dict:
        """Get handler statistics"""
        uptime = datetime.now() - self.stats["start_time"]
        
        return {
            "provider": "Local Llama",
            "model_name": self.model_name,
            "model_path": str(self.model_path),
            "model_info": self.model_info,
            "stats": {
                **self.stats,
                "uptime": str(uptime),
                "queue_size": self.request_queue.qsize()
            },
            "running": self.running,
            "timestamp": datetime.now().isoformat()
        }


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


# Example usage
def example_usage():
    """Example of using Llama handler"""
    # Example model path (adjust to your system)
    model_path = "/path/to/your/model.gguf"
    
    if not os.path.exists(model_path):
        print(f"⚠️  Model file not found: {model_path}")
        print("💡 Using simulation mode")
        # Create with dummy path for simulation
        handler = create_llama_handler("/tmp/dummy.gguf", "Simulated Llama")
    else:
        handler = create_llama_handler(model_path, "My Local Model")
    
    # Start handler
    if handler.start():
        print("✅ Llama handler started")
        
        # Test connection
        if handler.check_connection():
            print("✅ Model connection successful")
            
            # Quick chat (simulated)
            response = handler.quick_chat("Hello, how are you?")
            print(f"🤖 Response: {response}")
            
            # Get stats
            stats = handler.get_stats()
            print(f"\n📊 Stats: {json.dumps(stats, indent=2, default=str)}")
            
            # Stop handler
            handler.stop()
            print("\n🛑 Llama handler stopped")
        else:
            print("❌ Model connection failed")
    else:
        print("❌ Failed to start Llama handler")


if __name__ == "__main__":
    example_usage()