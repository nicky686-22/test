#!/usr/bin/env python3
"""
DeepSeek API Handler for SwarmIA
Handles communication with DeepSeek API
"""

import os
import json
import logging
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime

class DeepSeekHandler:
    """Handler for DeepSeek API"""
    
    def __init__(self, api_key: str, model: str = "deepseek-chat"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.deepseek.com/v1"
        self.logger = self._setup_logger()
        
        # Session for connection pooling
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        })
        
        self.logger.info(f"DeepSeek handler initialized with model: {model}")
    
    def _setup_logger(self):
        """Setup logger"""
        logger = logging.getLogger("swarmia.ai.deepseek")
        logger.setLevel(logging.INFO)
        return logger
    
    def chat_completion(self, 
                       messages: List[Dict[str, str]], 
                       temperature: float = 0.7,
                       max_tokens: int = 2000,
                       stream: bool = False) -> Dict:
        """
        Get chat completion from DeepSeek
        
        Args:
            messages: List of message dicts with role and content
            temperature: Creativity (0.0 to 1.0)
            max_tokens: Maximum tokens in response
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
            "stream": stream
        }
        
        try:
            self.logger.info(f"Sending request to DeepSeek API (messages: {len(messages)})")
            response = self.session.post(url, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            
            # Log token usage
            if "usage" in result:
                usage = result["usage"]
                self.logger.info(f"Token usage - Prompt: {usage.get('prompt_tokens', 0)}, "
                               f"Completion: {usage.get('completion_tokens', 0)}, "
                               f"Total: {usage.get('total_tokens', 0)}")
            
            return result
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"DeepSeek API request failed: {e}")
            raise
    
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
            raise ValueError("No response from DeepSeek API")
    
    def check_connection(self) -> bool:
        """Check if API connection works"""
        try:
            # Simple test request
            test_messages = [{"role": "user", "content": "Say 'OK' if you're working."}]
            response = self.chat_completion(test_messages, max_tokens=10)
            return "choices" in response
        except:
            return False
    
    def get_models(self) -> List[str]:
        """Get available models"""
        try:
            url = f"{self.base_url}/models"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            models_data = response.json()
            return [model["id"] for model in models_data.get("data", [])]
        except:
            return ["deepseek-chat", "deepseek-coder"]
    
    def get_stats(self) -> Dict:
        """Get handler statistics"""
        return {
            "provider": "DeepSeek",
            "model": self.model,
            "api_key_set": bool(self.api_key),
            "base_url": self.base_url,
            "timestamp": datetime.now().isoformat()
        }


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


# Example usage
def example_usage():
    """Example of using DeepSeek handler"""
    import os
    
    # Get API key from environment or config
    api_key = os.getenv("DEEPSEEK_API_KEY", "your-api-key-here")
    
    if api_key == "your-api-key-here":
        print("⚠️  Please set DEEPSEEK_API_KEY environment variable")
        return
    
    handler = create_deepseek_handler(api_key)
    
    # Test connection
    if handler.check_connection():
        print("✅ DeepSeek API connection successful")
        
        # Quick chat
        response = handler.quick_chat("Hello, how are you?")
        print(f"🤖 Response: {response[:100]}...")
        
        # Get stats
        stats = handler.get_stats()
        print(f"\n📊 Stats: {stats}")
    else:
        print("❌ DeepSeek API connection failed")


if __name__ == "__main__":
    example_usage()