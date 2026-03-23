#!/usr/bin/env python3
"""
SwarmIA Installation Verification Script
Verifies that all files are present and code is complete
"""

import os
import sys
import json
import yaml
from pathlib import Path
import importlib.util
import ast
from datetime import datetime

class InstallationVerifier:
    """Verifies SwarmIA installation completeness"""
    
    REQUIRED_FILES = [
        # Root files
        "README.md",
        "LICENSE",
        "requirements.txt",
        ".env.example",
        
        # Scripts
        "scripts/install.sh",
        "scripts/install.bat",
        "scripts/swarmia_core.sh",
        "scripts/verify_installation.py",
        
        # Core
        "src/core/main.py",
        "src/core/config.py",
        "src/core/supervisor.py",
        
        # AI
        "src/ai/deepseek.py",
        "src/ai/llama.py",
        
        # Agents
        "src/agents/chat.py",
        "src/agents/aggressive.py",
        
        # Gateway
        "src/gateway/communication.py",
        
        # UI
        "src/ui/server.py",
        "src/ui/templates/login.html",
        "src/ui/templates/dashboard.html",
        "src/ui/templates/agents.html",
        "src/ui/templates/tasks.html",
        "src/ui/templates/config.html",
        "src/ui/templates/logs.html",
        "src/ui/templates/chat.html",
        "src/ui/templates/change_password.html",
        "src/ui/static/css/style.css",
        
        # Config
        "config/config.example.yaml",
    ]
    
    REQUIRED_IMPORTS = {
        "src/core/main.py": [
            "Config", "create_supervisor", "create_chat_agent",
            "create_aggressive_agent", "setup_communication_gateway", "app"
        ],
        "src/core/config.py": ["Config"],
        "src/core/supervisor.py": ["Supervisor", "TaskPriority", "create_supervisor"],
        "src/ai/deepseek.py": ["DeepSeekHandler", "create_deepseek_handler"],
        "src/ai/llama.py": ["LlamaHandler", "create_llama_handler"],
        "src/agents/chat.py": ["ChatAgent", "create_chat_agent"],
        "src/agents/aggressive.py": ["AggressiveAgent", "create_aggressive_agent"],
        "src/gateway/communication.py": ["CommunicationGateway", "setup_communication_gateway"],
        "src/ui/server.py": ["app", "main"]
    }
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.results = {
            "files": {"total": 0, "missing": [], "present": []},
            "imports": {"missing": [], "present": []},
            "syntax": {"errors": [], "valid": []},
            "configs": {"missing": [], "present": []}
        }
    
    def verify_all(self):
        """Run all verification checks"""
        print("🔍 Verificando instalación de SwarmIA...")
        print("=" * 60)
        
        self.verify_files()
        self.verify_imports()
        self.verify_syntax()
        self.verify_configs()
        
        self.print_summary()
        
        return self.is_complete()
    
    def verify_files(self):
        """Verify all required files exist"""
        print("\n📁 Verificando archivos requeridos...")
        
        for file_path in self.REQUIRED_FILES:
            full_path = self.base_dir / file_path
            self.results["files"]["total"] += 1
            
            if full_path.exists():
                self.results["files"]["present"].append(file_path)
                print(f"  ✅ {file_path}")
            else:
                self.results["files"]["missing"].append(file_path)
                print(f"  ❌ {file_path} (FALTANTE)")
    
    def verify_imports(self):
        """Verify required imports in Python files"""
        print("\n📦 Verificando imports de Python...")
        
        for file_path, required_imports in self.REQUIRED_IMPORTS.items():
            full_path = self.base_dir / file_path
            
            if not full_path.exists():
                continue
            
            try:
                with open(full_path, 'r') as f:
                    content = f.read()
                
                # Parse AST to find imports
                tree = ast.parse(content)
                
                # Get all imports
                imports = []
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imports.append(alias.name)
                    elif isinstance(node, ast.ImportFrom):
                        module = node.module or ""
                        for alias in node.names:
                            imports.append(f"{module}.{alias.name}" if module else alias.name)
                
                # Check required imports
                file_imports_present = []
                file_imports_missing = []
                
                for required in required_imports:
                    found = False
                    for imp in imports:
                        if required in imp or imp.endswith(f".{required}"):
                            found = True
                            break
                    
                    if found:
                        file_imports_present.append(required)
                    else:
                        file_imports_missing.append(required)
                
                if file_imports_missing:
                    self.results["imports"]["missing"].append({
                        "file": file_path,
                        "missing": file_imports_missing
                    })
                    print(f"  ⚠️  {file_path}: Faltan {', '.join(file_imports_missing)}")
                else:
                    self.results["imports"]["present"].append(file_path)
                    print(f"  ✅ {file_path}: Todos los imports presentes")
                    
            except SyntaxError as e:
                self.results["imports"]["missing"].append({
                    "file": file_path,
                    "missing": ["ERROR DE SINTAXIS - " + str(e)]
                })
                print(f"  ❌ {file_path}: Error de sintaxis - {e}")
            except Exception as e:
                self.results["imports"]["missing"].append({
                    "file": file_path,
                    "missing": ["ERROR - " + str(e)]
                })
                print(f"  ❌ {file_path}: Error - {e}")
    
    def verify_syntax(self):
        """Verify Python syntax is valid"""
        print("\n🐍 Verificando sintaxis de Python...")
        
        # Find all Python files
        python_files = []
        src_dir = self.base_dir / "src"
        if src_dir.exists():
            for root, dirs, files in os.walk(src_dir):
                for file in files:
                    if file.endswith('.py'):
                        python_files.append(Path(root) / file)
        
        for py_file in python_files:
            rel_path = py_file.relative_to(self.base_dir)
            
            try:
                with open(py_file, 'r') as f:
                    ast.parse(f.read())
                
                self.results["syntax"]["valid"].append(str(rel_path))
                print(f"  ✅ {rel_path}")
                
            except SyntaxError as e:
                self.results["syntax"]["errors"].append({
                    "file": str(rel_path),
                    "error": str(e)
                })
                print(f"  ❌ {rel_path}: {e}")
            except Exception as e:
                self.results["syntax"]["errors"].append({
                    "file": str(rel_path),
                    "error": str(e)
                })
                print(f"  ❌ {rel_path}: {e}")
    
    def verify_configs(self):
        """Verify configuration files can be parsed"""
        print("\n⚙️  Verificando archivos de configuración...")
        
        config_files = [
            "requirements.txt",
            ".env.example",
            "config/config.example.yaml"
        ]
        
        for config_file in config_files:
            full_path = self.base_dir / config_file
            
            if full_path.exists():
                try:
                    if config_file.endswith('.json'):
                        with open(full_path, 'r') as f:
                            json.load(f)
                    elif config_file.endswith('.yaml') or config_file.endswith('.yml'):
                        with open(full_path, 'r') as f:
                            yaml.safe_load(f)
                    elif config_file == 'requirements.txt' or config_file == '.env.example':
                        with open(full_path, 'r') as f:
                            f.read()
                    
                    self.results["configs"]["present"].append(config_file)
                    print(f"  ✅ {config_file}")
                    
                except Exception as e:
                    self.results["configs"]["missing"].append({
                        "file": config_file,
                        "error": str(e)
                    })
                    print(f"  ❌ {config_file}: Error de parseo - {e}")
            else:
                self.results["configs"]["missing"].append({
                    "file": config_file,
                    "error": "Archivo no encontrado"
                })
                print(f"  ❌ {config_file}: No encontrado")
    
    def print_summary(self):
        """Print verification summary"""
        print("\n" + "=" * 60)
        print("📊 RESUMEN DE VERIFICACIÓN")
        print("=" * 60)
        
        # Files summary
        total_files = self.results["files"]["total"]
        missing_files = len(self.results["files"]["missing"])
        present_files = len(self.results["files"]["present"])
        
        print(f"\n📁 Archivos: {present_files}/{total_files} presentes")
        if missing_files > 0:
            print(f"  ❌ Archivos faltantes:")
            for file in self.results["files"]["missing"]:
                print(f"    - {file}")
        
        # Imports summary
        import_issues = len(self.results["imports"]["missing"])
        print(f"\n📦 Imports: {len(self.results['imports']['present'])} archivos OK")
        if import_issues > 0:
            print(f"  ⚠️  Problemas de imports:")
            for issue in self.results["imports"]["missing"]:
                print(f"    - {issue['file']}: {', '.join(issue['missing'])}")
        
        # Syntax summary
        syntax_errors = len(self.results["syntax"]["errors"])
        valid_files = len(self.results["syntax"]["valid"])
        print(f"\n🐍 Sintaxis: {valid_files} archivos válidos")
        if syntax_errors > 0:
            print(f"  ❌ Errores de sintaxis:")
            for error in self.results["syntax"]["errors"]:
                print(f"    - {error['file']}: {error['error']}")
        
        # Configs summary
        config_issues = len(self.results["configs"]["missing"])
        print(f"\n⚙️  Configuración: {len(self.results['configs']['present'])} archivos OK")
        if config_issues > 0:
            print(f"  ⚠️  Problemas de configuración:")
            for issue in self.results["configs"]["missing"]:
                print(f"    - {issue['file']}: {issue['error']}")
        
        # Overall status
        print("\n" + "=" * 60)
        if self.is_complete():
            print("🎉 ¡LA INSTALACIÓN DE SWARMIA ESTÁ COMPLETA Y LISTA!")
            print("\nPróximos pasos:")
            print("1. Ejecuta: curl -sSL https://raw.githubusercontent.com/nicky686-22/test/main/scripts/install.sh | sudo bash")
            print("2. Accede al dashboard en http://[TU_IP]:8080")
            print("3. Inicia sesión con admin/admin (cambia inmediatamente!)")
        else:
            print("⚠️  LA INSTALACIÓN DE SWARMIA TIENE PROBLEMAS")
            print("\nPor favor corrige los problemas indicados antes de instalar.")
        
        print("=" * 60)
    
    def is_complete(self) -> bool:
        """Check if installation is complete"""
        return (
            len(self.results["files"]["missing"]) == 0 and
            len(self.results["imports"]["missing"]) == 0 and
            len(self.results["syntax"]["errors"]) == 0 and
            len(self.results["configs"]["missing"]) == 0
        )
    
    def generate_report(self, output_file: Path):
        """Generate verification report"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "base_directory": str(self.base_dir),
            "results": self.results,
            "complete": self.is_complete(),
            "summary": {
                "files_total": self.results["files"]["total"],
                "files_missing": len(self.results["files"]["missing"]),
                "imports_issues": len(self.results["imports"]["missing"]),
                "syntax_errors": len(self.results["syntax"]["errors"]),
                "config_issues": len(self.results["configs"]["missing"])
            }
        }
        
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"\n📄 Reporte guardado en: {output_file}")


def main():
    """Main function"""
    # Set base directory
    base_dir = Path(__file__).parent.parent
    
    # Create verifier
    verifier = InstallationVerifier(base_dir)
    
    # Run verification
    complete = verifier.verify_all()
    
    # Generate report
    report_file = base_dir / "verification_report.json"
    verifier.generate_report(report_file)
    
    # Return exit code
    return 0 if complete else 1


if __name__ == "__main__":
    sys.exit(main())
