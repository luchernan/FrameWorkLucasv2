"""Wrapper de enum4linux: enumeración SMB/AD en entornos Windows."""
import os
import shutil
from colorama import Fore

from ..ui import edu_print
from ..runner import run_cmd


def run_enum4linux(target, workspace_dir):
    if shutil.which('enum4linux') is None:
        print(f"{Fore.RED}[!] Enum4linux no está instalado.")
        return

    edu_print(
        tool="Enum4Linux",
        phase="Reconocimiento Avanzado de Entornos Windows",
        explanation=f"- 'enum4linux -a {target}':\n"
                    f"- Si el host devolvió TTL 128 y tiene puertos 139/445 expuestos,\n"
                    f"- esta herramienta extrae usuarios, grupos y shares vía Null Sessions."
    )

    log_file = os.path.join(workspace_dir, "nmap", "enum4linux_windows.txt")
    run_cmd(['enum4linux', '-a', target], capture_output=True, log_file=log_file)
