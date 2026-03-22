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
        "package.json",
        "SKILL.md",
        
        # Scripts
        "scripts/install.sh",
        "scripts/install.bat",
        "scripts/verify_installation.py",
        
        # Core
        "src/core/main.py",
        "src/core/config.py",
        "src/core/supervisor.py",
        "src/core/updater.py",
        
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
        "src/ui/templates/change_password.html",
        "src/ui/static/css/style.css"
    ]
    
    REQUIRED_IMPORTS = {
        "src/core/main.py": [
            "Config", "Supervisor", "create_update_checker",
            "create_chat_agent", "create_aggressive_agent",
            "setup_communication_gateway", "create_app"
        ],
        "src/core/config.py": ["Config", "get_config"],
        "src/core/supervisor.py": ["Supervisor", "TaskPriority", "create_supervisor"],
        "src/core/updater.py": ["UpdateChecker", "create_update_checker"],
        "src/ai/deepseek.py": ["DeepSeekHandler", "create_deepseek_handler"],
        "src/ai/llama.py": ["LlamaHandler", "create_llama_handler"],
        "src/agents/chat.py": ["ChatAgent", "create_chat_agent"],
        "src/agents/aggressive.py": ["AggressiveAgent", "create_aggressive_agent"],
        "src/gateway/communication.py": ["CommunicationGateway", "setup_communication_gateway"],
        "src/ui/server.py": ["create_app"]
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
        print("🔍 Verifying SwarmIA Installation...")
        print("=" * 60)
        
        self.verify_files()
        self.verify_imports()
        self.verify_syntax()
        self.verify_configs()
        
        self.print_summary()
        
        return self.is_complete()
    
    def verify_files(self):
        """Verify all required files exist"""
        print("\n📁 Checking required files...")
        
        for file_path in self.REQUIRED_FILES:
            full_path = self.base_dir / file_path
            self.results["files"]["total"] += 1
            
            if full_path.exists():
                self.results["files"]["present"].append(file_path)
                print(f"  ✅ {file_path}")
            else:
                self.results["files"]["missing"].append(file_path)
                print(f"  ❌ {file_path} (MISSING)")
    
    def verify_imports(self):
        """Verify required imports in Python files"""
        print("\n📦 Checking Python imports...")
        
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
                    # Check if import is present (exact or as part of module)
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
                    print(f"  ⚠️  {file_path}: Missing {', '.join(file_imports_missing)}")
                else:
                    self.results["imports"]["present"].append(file_path)
                    print(f"  ✅ {file_path}: All imports present")
                    
            except SyntaxError as e:
                self.results["imports"]["missing"].append({
                    "file": file_path,
                    "missing": ["SYNTAX ERROR - " + str(e)]
                })
                print(f"  ❌ {file_path}: Syntax error - {e}")
            except Exception as e:
                self.results["imports"]["missing"].append({
                    "file": file_path,
                    "missing": ["ERROR - " + str(e)]
                })
                print(f"  ❌ {file_path}: Error - {e}")
    
    def verify_syntax(self):
        """Verify Python syntax is valid"""
        print("\n🐍 Checking Python syntax...")
        
        # Find all Python files
        python_files = []
        for root, dirs, files in os.walk(self.base_dir / "src"):
            for file in files:
                if file.endswith('.py'):
                    python_files.append(Path(root) / file)
        
        for py_file in python_files:
            rel_path = py_file.relative_to(self.base_dir)
            
            try:
                # Try to parse the file
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
        print("\n⚙️  Checking configuration files...")
        
        config_files = [
            "requirements.txt",
            "package.json"
        ]
        
        # Check for expected config templates
        config_templates = [
            "config/config.yaml",
            "config/ai_config.json",
            "config/communication.json",
            "config/aggressive_config.json",
            "config/update_settings.json"
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
                    elif config_file == 'requirements.txt':
                        # Just check it's readable
                        with open(full_path, 'r') as f:
                            f.read()
                    
                    self.results["configs"]["present"].append(config_file)
                    print(f"  ✅ {config_file}")
                    
                except Exception as e:
                    self.results["configs"]["missing"].append({
                        "file": config_file,
                        "error": str(e)
                    })
                    print(f"  ❌ {config_file}: Parse error - {e}")
            else:
                self.results["configs"]["missing"].append({
                    "file": config_file,
                    "error": "File not found"
                })
                print(f"  ❌ {config_file}: Not found")
        
        # Check config templates (they might not exist yet)
        for config_template in config_templates:
            full_path = self.base_dir / config_template
            if full_path.exists():
                print(f"  📄 {config_template} (exists)")
            else:
                print(f"  📝 {config_template} (template - will be created)")
    
    def print_summary(self):
        """Print verification summary"""
        print("\n" + "=" * 60)
        print("📊 VERIFICATION SUMMARY")
        print("=" * 60)
        
        # Files summary
        total_files = self.results["files"]["total"]
        missing_files = len(self.results["files"]["missing"])
        present_files = len(self.results["files"]["present"])
        
        print(f"\n📁 Files: {present_files}/{total_files} present")
        if missing_files > 0:
            print(f"  ❌ Missing files:")
            for file in self.results["files"]["missing"]:
                print(f"    - {file}")
        
        # Imports summary
        import_issues = len(self.results["imports"]["missing"])
        print(f"\n📦 Imports: {len(self.results['imports']['present'])} files OK")
        if import_issues > 0:
            print(f"  ⚠️  Import issues:")
            for issue in self.results["imports"]["missing"]:
                print(f"    - {issue['file']}: {', '.join(issue['missing'])}")
        
        # Syntax summary
        syntax_errors = len(self.results["syntax"]["errors"])
        valid_files = len(self.results["syntax"]["valid"])
        print(f"\n🐍 Syntax: {valid_files} files valid")
        if syntax_errors > 0:
            print(f"  ❌ Syntax errors:")
            for error in self.results["syntax"]["errors"]:
                print(f"    - {error['file']}: {error['error']}")
        
        # Configs summary
        config_issues = len(self.results["configs"]["missing"])
        print(f"\n⚙️  Configs: {len(self.results['configs']['present'])} files OK")
        if config_issues > 0:
            print(f"  ⚠️  Config issues:")
            for issue in self.results["configs"]["missing"]:
                print(f"    - {issue['file']}: {issue['error']}")
        
        # Overall status
        print("\n" + "=" * 60)
        if self.is_complete():
            print("🎉 SWARMIA INSTALLATION IS COMPLETE AND READY!")
            print("\nNext steps:")
            print("1. Run: sudo ./scripts/install.sh (Linux)")
            print("2. Or: Run install.bat as Administrator (Windows)")
            print("3. Access dashboard at http://[YOUR_IP]:3000")
            print("4. Login with admin/admin (change immediately!)")
        else:
            print("⚠️  SWARMIA INSTALLATION HAS ISSUES")
            print("\nPlease fix the issues above before installation.")
        
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
        
        print(f"\n📄 Report saved to: {output_file}")


def main():
    """Main function"""
    from datetime import datetime
    
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