# src/utils/env_manager.py

import os
import re
from pathlib import Path
from typing import Dict, Optional, Any


class EnvManager:
    """Gestor del archivo .env"""
    
    def __init__(self, env_path: Optional[Path] = None):
        if env_path is None:
            env_path = Path(__file__).parent.parent.parent / ".env"
        self.env_path = env_path
        self._cargar()
    
    def _cargar(self):
        """Cargar variables del .env"""
        self.variables = {}
        if self.env_path.exists():
            with open(self.env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        self.variables[key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """Obtener variable"""
        return self.variables.get(key, default)
    
    def set(self, key: str, value: str) -> bool:
        """Establecer variable"""
        self.variables[key] = value
        return self._guardar()
    
    def set_multiple(self, valores: Dict[str, str]) -> bool:
        """Establecer múltiples variables"""
        self.variables.update(valores)
        return self._guardar()
    
    def _guardar(self) -> bool:
        """Guardar variables al archivo .env"""
        try:
            # Leer líneas actuales para preservar comentarios
            lineas = []
            if self.env_path.exists():
                with open(self.env_path, 'r') as f:
                    lineas = f.readlines()
            
            # Actualizar líneas existentes
            keys_actualizadas = set()
            for i, linea in enumerate(lineas):
                if linea.strip() and not linea.strip().startswith('#') and '=' in linea:
                    key = linea.split('=')[0].strip()
                    if key in self.variables:
                        lineas[i] = f"{key}={self.variables[key]}\n"
                        keys_actualizadas.add(key)
            
            # Agregar nuevas variables
            for key, value in self.variables.items():
                if key not in keys_actualizadas:
                    lineas.append(f"{key}={value}\n")
            
            # Escribir archivo
            with open(self.env_path, 'w') as f:
                f.writelines(lineas)
            
            return True
        except Exception as e:
            print(f"Error guardando .env: {e}")
            return False
    
    def recargar(self):
        """Recargar variables después de cambios externos"""
        self._cargar()
    
    def mostrar_diferencias(self, otras: Dict[str, str]) -> Dict[str, tuple]:
        """Mostrar diferencias entre actual y otras"""
        diferencias = {}
        for key, value in otras.items():
            actual = self.variables.get(key)
            if actual != value:
                diferencias[key] = (actual, value)
        return diferencias
