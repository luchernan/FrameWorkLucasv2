"""Gestión del directorio de evidencias por target."""
import os
from colorama import Fore


def create_workspace(ip: str):
    """Crea el árbol workspace_<ip>/ con subcarpetas estándar.

    Devuelve la ruta base o None en error de permisos.
    """
    base_dir = f"workspace_{ip.replace('.', '_')}"
    dirs = [
        base_dir,
        os.path.join(base_dir, "nmap"),
        os.path.join(base_dir, "web"),
        os.path.join(base_dir, "exploits"),
        os.path.join(base_dir, "os_discovery"),
    ]

    created_any = False
    try:
        for d in dirs:
            if not os.path.exists(d):
                os.makedirs(d)
                created_any = True
    except PermissionError:
        print(f"\n{Fore.RED}[!] ERROR DE PERMISOS: No se puede crear la carpeta '{base_dir}'.")
        print(f"{Fore.RED}[!] Solución: ejecuta con privilegios (sudo) o cambia a un directorio con permisos de escritura.")
        return None

    if created_any:
        print(f"{Fore.GREEN}[+] Creado entorno de trabajo estructurado en: ./{base_dir}/")
        print(f"{Fore.GREEN}[+] Todas las evidencias capturadas se guardarán automáticamente en esta carpeta.")

    return base_dir
