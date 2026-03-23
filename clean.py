#!/usr/bin/env python3
"""
SwarmIA Cleanup Script
Elimina completamente la instalación de SwarmIA para una reinstalación limpia
"""

import os
import sys
import shutil
import subprocess
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
    
    # Detener servicio systemd
    success, _, _ = run_command("sudo systemctl stop swarmia 2>/dev/null")
    if success:
        print_success("Servicio swarmia detenido")
    
    # Deshabilitar servicio
    run_command("sudo systemctl disable swarmia 2>/dev/null")
    
    # Matar procesos restantes
    run_command("sudo pkill -f 'swarmia' 2>/dev/null")
    run_command("sudo pkill -f 'src.core.main' 2>/dev/null")
    run_command("sudo pkill -f 'src.ui.server' 2>/dev/null")
    
    # Esperar a que terminen
    time.sleep(1)
    print_success("Procesos terminados")

def remove_installation_dir():
    """Eliminar directorio de instalación"""
    print_step("2/8", "Eliminando directorio de instalación...")
    
    install_dir = Path("/opt/swarmia")
    
    if install_dir.exists():
        try:
            shutil.rmtree(install_dir)
            print_success(f"Eliminado: {install_dir}")
        except Exception as e:
            print_error(f"No se pudo eliminar {install_dir}: {e}")
            return False
    else:
        print_warning(f"Directorio no existe: {install_dir}")
    
    return True

def remove_systemd_service():
    """Eliminar archivo de servicio systemd"""
    print_step("3/8", "Eliminando servicio systemd...")
    
    service_file = Path("/etc/systemd/system/swarmia.service")
    
    if service_file.exists():
        try:
            service_file.unlink()
            run_command("sudo systemctl daemon-reload")
            print_success(f"Eliminado: {service_file}")
        except Exception as e:
            print_error(f"No se pudo eliminar {service_file}: {e}")
            return False
    else:
        print_warning(f"Archivo de servicio no existe")
    
    return True

def remove_global_command():
    """Eliminar comando global swarmia"""
    print_step("4/8", "Eliminando comando global...")
    
    cmd_file = Path("/usr/local/bin/swarmia")
    
    if cmd_file.exists():
        try:
            cmd_file.unlink()
            print_success(f"Eliminado: {cmd_file}")
        except Exception as e:
            print_error(f"No se pudo eliminar {cmd_file}: {e}")
            return False
    else:
        print_warning(f"Comando global no existe")
    
    return True

def clean_pip_cache():
    """Limpiar caché de pip"""
    print_step("5/8", "Limpiando caché de pip...")
    
    # Caché del sistema
    run_command("sudo rm -rf /root/.cache/pip 2>/dev/null")
    
    # Caché del usuario
    home = Path.home()
    pip_cache = home / ".cache" / "pip"
    if pip_cache.exists():
        try:
            shutil.rmtree(pip_cache)
            print_success("Caché de pip eliminada")
        except:
            print_warning("No se pudo eliminar caché de pip")
    
    print_success("Limpieza de caché completada")

def clean_logs():
    """Eliminar archivos de log"""
    print_step("6/8", "Eliminando archivos de log...")
    
    log_files = [
        "/var/log/swarmia.log",
        "/var/log/swarmia/swarmia.log",
        "/opt/swarmia/logs/*",
        "/tmp/swarmia_*.sh"
    ]
    
    for log_pattern in log_files:
        run_command(f"sudo rm -rf {log_pattern} 2>/dev/null")
    
    print_success("Archivos de log eliminados")

def clean_venv():
    """Limpiar entornos virtuales"""
    print_step("7/8", "Limpiando entornos virtuales...")
    
    # Buscar y eliminar entornos virtuales
    venv_dirs = [
        "/opt/swarmia/venv",
        "/opt/swarmia/.venv",
        "venv", ".venv"
    ]
    
    for venv_dir in venv_dirs:
        path = Path(venv_dir)
        if path.exists():
            try:
                shutil.rmtree(path)
                print_success(f"Eliminado: {path}")
            except:
                pass
    
    print_success("Entornos virtuales limpiados")

def verify_cleanup():
    """Verificar que todo se eliminó correctamente"""
    print_step("8/8", "Verificando limpieza...")
    
    issues = []
    
    # Verificar directorio de instalación
    if Path("/opt/swarmia").exists():
        issues.append("/opt/swarmia aún existe")
    
    # Verificar servicio
    if Path("/etc/systemd/system/swarmia.service").exists():
        issues.append("Archivo de servicio aún existe")
    
    # Verificar comando global
    if Path("/usr/local/bin/swarmia").exists():
        issues.append("Comando global aún existe")
    
    # Verificar procesos
    result = run_command("pgrep -f 'swarmia'", capture=True)
    if result[0]:
        issues.append("Procesos de SwarmIA aún corriendo")
    
    if issues:
        print_warning("Se encontraron elementos residuales:")
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
        print(f"  1. Para reinstalar, ejecuta:")
        print(f"     {Colors.YELLOW}curl -sSL https://raw.githubusercontent.com/nicky686-22/test/main/scripts/install.sh | sudo bash{Colors.NC}")
        print()
        print(f"  2. Para verificar la limpieza:")
        print(f"     {Colors.YELLOW}ls -la /opt/ | grep swarmia{Colors.NC}")
        print(f"     {Colors.YELLOW}systemctl status swarmia{Colors.NC}")
    else:
        print(f"{Colors.YELLOW}⚠️  LIMPIEZA INCOMPLETA{Colors.NC}")
        print()
        print(f"{Colors.YELLOW}Algunos elementos no se pudieron eliminar.{Colors.NC}")
        print(f"Puedes intentar eliminar manualmente con: {Colors.NC}")
        print(f"  sudo rm -rf /opt/swarmia")
        print(f"  sudo rm -f /etc/systemd/system/swarmia.service")
        print(f"  sudo rm -f /usr/local/bin/swarmia")
    
    print(f"{Colors.CYAN}{'='*60}{Colors.NC}")

def main():
    """Función principal"""
    print_banner()
    
    # Confirmar limpieza
    print_warning("Esta acción eliminará COMPLETAMENTE SwarmIA del sistema.")
    print_warning("Toda la configuración, datos y logs serán eliminados.")
    print()
    
    response = input(f"{Colors.YELLOW}¿Estás seguro de que deseas continuar? (escribe 'SI' para confirmar): {Colors.NC}")
    
    if response.upper() != "SI":
        print()
        print_warning("Limpieza cancelada.")
        return 0
    
    print()
    print(f"{Colors.GREEN}Iniciando limpieza...{Colors.NC}")
    print()
    
    # Ejecutar limpieza
    clean_success = True
    
    try:
        stop_services()
        clean_success &= remove_installation_dir()
        clean_success &= remove_systemd_service()
        clean_success &= remove_global_command()
        clean_pip_cache()
        clean_logs()
        clean_venv()
        
        # Verificar resultado final
        verification = verify_cleanup()
        clean_success = clean_success and verification
        
    except KeyboardInterrupt:
        print()
        print_warning("Limpieza interrumpida por el usuario.")
        return 1
    except Exception as e:
        print_error(f"Error inesperado: {e}")
        clean_success = False
    
    # Mostrar resumen
    print_summary(clean_success)
    
    return 0 if clean_success else 1

if __name__ == "__main__":
    sys.exit(main())
