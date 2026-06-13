"""Wrapper de SQLMap: detección/explotación automatizada de inyecciones SQL."""
import os
import shutil
from colorama import Fore, Style

from ..ui import edu_print
from ..runner import run_cmd


def run_sqlmap(workspace_dir):
    if shutil.which('sqlmap') is None:
        print(f"{Fore.RED}[!] SQLMap no está instalado en tu sistema.")
        return

    print(f"\n{Fore.GREEN}[*] Inicializando Suite SQLMap (Inyección SQL Automatizada){Style.RESET_ALL}")
    url_target = input(f"{Fore.CYAN}[?] Introduce la URL vulnerable a probar (Ej: http://10.0.0.1/item.php?id=1): ").strip()

    if not url_target:
        return

    edu_print(
        tool="SQLMap",
        phase="Explotación Web Activa (Inyecciones SQL)",
        explanation="- 'sqlmap -u \"<url_con_parametro>\" --batch --dbs':\n"
                    "- Volcar DBs ciegamente o basadas en errores.\n"
                    "- '--batch': responde con defaults a todas las preguntas.\n"
                    "- '--dbs': enumera las Bases de Datos disponibles."
    )

    log_file = os.path.join(workspace_dir, "web", "sqlmap_databases.txt")
    run_cmd(['sqlmap', '-u', url_target, '--batch', '--dbs'],
            capture_output=True, log_file=log_file)
