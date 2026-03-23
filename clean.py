#!/usr/bin/env python3
"""
SwarmIA Cleanup Script
Elimina completamente la instalación de SwarmIA para una reinstalación limpia
"""

import os
import sys
import shutil
import subprocess
import argparse
from pathlib import Path
import time

# Colores para terminal
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    NC = '\033[0m'

def print_banner():
    """Mostrar banner de limpieza"""
    print(f"""
{Colors.CYAN}╔══════════════════════════════════════════════════════════════╗
║                   🧹 SwarmIA Cleanup Script                         ║
║                   Eliminación completa del sistema                  ║
╚════════════════════════════════════════════════════════════════════╝{Colors.NC}
""")

def print_step(step, message):
    """Mostrar paso de limpieza"""
    print(f"{Colors.BLUE}[{step}] {message}{Colors.NC}")

def print_success(message):
    """Mostrar mensaje de éxito"""
    print(f"{Colors.GREEN}✅ {message}{Colors.NC}")

def print_error(message):
    """Mostrar mensaje de error"""
    print(f"{Colors.RED}❌ {message}{Colors.NC}")

def print_warning(message):
    """Mostrar mensaje de advertencia"""
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.NC}")

def run_command(cmd, capture=False):
    """Ejecutar comando del sistema"""
    try:
        if capture:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return result.returncode == 0, result.stdout, result.stderr
        else:
            result = subprocess.run(cmd, shell=True)
            return result.returncode == 0, "", ""
    except Exception as e:
        return False, "", str(e)

def stop_services():
    """Detener servicios de SwarmIA"""
    print_step("1/8", "Deteniendo servicios...")
    
    run_command("sudo systemctl stop swarmia 2>/dev/null")
    run_command("sudo systemctl disable swarmia 2>/dev/null")
    run_command("sudo pkill -f 'swarmia' 2>/dev/null")
    run_command("sudo pkill -f 'src.core.main' 2>/dev/null")
    run_command("sudo pkill -f 'src.ui.server' 2>/dev/null")
    time.sleep(1)
    print_success("Servicios detenidos")

def remove_installation_dir():
    """Eliminar directorio de instalación"""
    print_step("2/8", "Eliminando directorio de instalación...")
    install_dir = Path("/opt/swarmia")
    if install_dir.exists():
        shutil.rmtree(install_dir)
        print_success(f"Eliminado: {install_dir}")
    else:
        print_warning(f"Directorio no existe: {install_dir}")
    return True

def remove_systemd_service():
    """Eliminar archivo de servicio systemd"""
    print_step("3/8", "Eliminando servicio systemd...")
    service_file = Path("/etc/systemd/system/swarmia.service")
    if service_file.exists():
        service_file.unlink()
        run_command("sudo systemctl daemon-reload")
        print_success(f"Eliminado: {service_file}")
    else:
        print_warning("Archivo de servicio no existe")
    return True

def remove_global_command():
    """Eliminar comando global swarmia"""
    print_step("4/8", "Eliminando comando global...")
    cmd_file = Path("/usr/local/bin/swarmia")
    if cmd_file.exists():
        cmd_file.unlink()
        print_success(f"Eliminado: {cmd_file}")
    else:
        print_warning("Comando global no existe")
    return True

def clean_pip_cache():
    """Limpiar caché de pip"""
    print_step("5/8", "Limpiando caché de pip...")
    run_command("sudo rm -rf /root/.cache/pip 2>/dev/null")
    home = Path.home()
    pip_cache = home / ".cache" / "pip"
    if pip_cache.exists():
        shutil.rmtree(pip_cache)
    print_success("Caché de pip limpiada")

def clean_logs():
    """Eliminar archivos de log"""
    print_step("6/8", "Eliminando archivos de log...")
    log_patterns = [
        "/var/log/swarmia.log",
        "/var/log/swarmia/swarmia.log",
        "/tmp/swarmia_*.sh"
    ]
    for pattern in log_patterns:
        run_command(f"sudo rm -rf {pattern} 2>/dev/null")
    print_success("Logs eliminados")

def clean_venv():
    """Limpiar entornos virtuales"""
    print_step("7/8", "Limpiando entornos virtuales...")
    venv_dirs = ["/opt/swarmia/venv", "/opt/swarmia/.venv"]
    for venv_dir in venv_dirs:
        path = Path(venv_dir)
        if path.exists():
            shutil.rmtree(path)
    print_success("Entornos virtuales limpiados")

def verify_cleanup():
    """Verificar que todo se eliminó correctamente"""
    print_step("8/8", "Verificando limpieza...")
    issues = []
    if Path("/opt/swarmia").exists():
        issues.append("/opt/swarmia aún existe")
    if Path("/etc/systemd/system/swarmia.service").exists():
        issues.append("Archivo de servicio aún existe")
    if Path("/usr/local/bin/swarmia").exists():
        issues.append("Comando global aún existe")
    
    if issues:
        print_warning("Elementos residuales:")
        for issue in issues:
            print(f"  - {issue}")
        return False
    else:
        print_success("Limpieza completa verificada")
        return True

def print_summary(clean_success):
    """Mostrar resumen final"""
    print()
    print(f"{Colors.CYAN}{'='*60}{Colors.NC}")
    if clean_success:
        print(f"{Colors.GREEN}✅ LIMPIEZA COMPLETADA EXITOSAMENTE{Colors.NC}")
        print()
        print(f"{Colors.CYAN}El sistema SwarmIA ha sido eliminado por completo.{Colors.NC}")
        print()
        print(f"{Colors.BLUE}Próximos pasos:{Colors.NC}")
        print(f"  curl -sSL https://raw.githubusercontent.com/nicky686-22/test/main/scripts/install.sh | sudo bash")
    else:
        print(f"{Colors.YELLOW}⚠️  LIMPIEZA INCOMPLETA{Colors.NC}")
        print(f"Puedes eliminar manualmente: sudo rm -rf /opt/swarmia")
    print(f"{Colors.CYAN}{'='*60}{Colors.NC}")

def main():
    """Función principal"""
    parser = argparse.ArgumentParser()
    parser.add_argument('--no-interactive', action='store_true', help='Ejecutar sin confirmación')
    args = parser.parse_args()
    
    print_banner()
    
    if not args.no_interactive:
        print_warning("Esta acción eliminará COMPLETAMENTE SwarmIA del sistema.")
        print_warning("Toda la configuración, datos y logs serán eliminados.")
        print()
        response = input(f"{Colors.YELLOW}¿Estás seguro? (escribe 'SI' para confirmar): {Colors.NC}")
        if response.upper() != "SI":
            print()
            print_warning("Limpieza cancelada.")
            return 0
    
    print()
    print(f"{Colors.GREEN}Iniciando limpieza...{Colors.NC}")
    print()
    
    clean_success = True
    try:
        stop_services()
        clean_success &= remove_installation_dir()
        clean_success &= remove_systemd_service()
        clean_success &= remove_global_command()
        clean_pip_cache()
        clean_logs()
        clean_venv()
        verification = verify_cleanup()
        clean_success = clean_success and verification
    except Exception as e:
        print_error(f"Error inesperado: {e}")
        clean_success = False
    
    print_summary(clean_success)
    return 0 if clean_success else 1

if __name__ == "__main__":
    sys.exit(main())
