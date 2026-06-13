"""Validación de input y comprobación de dependencias del sistema."""
import re
import shutil
from .ui import _info, _warn, _ok

REQUIRED_TOOLS = [
    'ping', 'nmap', 'gobuster', 'nikto', 'searchsploit', 'arp-scan',
    'ffuf', 'wpscan', 'hydra', 'sqlmap', 'enum4linux', 'john', 'nuclei',
]


def validate_target(target: str) -> bool:
    """Valida que el target sea IP válida o hostname razonable."""
    if re.match(r'^\d{1,3}(\.\d{1,3}){3}$', target):
        parts = target.split('.')
        return all(0 <= int(p) <= 255 for p in parts)
    if re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9\-\.]{0,253}[a-zA-Z0-9])?$', target):
        return True
    return False


def check_dependencies() -> list:
    """Comprueba REQUIRED_TOOLS, imprime resumen y devuelve la lista de faltantes."""
    _info("Comprobando dependencias del sistema...")
    missing = [t for t in REQUIRED_TOOLS if shutil.which(t) is None]
    if missing:
        _warn(f"Herramientas faltantes: {', '.join(missing)}")
        _warn("Algunas funciones del script fallarán. Instálalas antes de continuar.")
    else:
        _ok("Todas las dependencias están disponibles.")
    print()
    return missing
