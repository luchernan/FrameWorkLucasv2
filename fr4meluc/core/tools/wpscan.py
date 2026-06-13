"""Wrapper de WPScan: enumeración específica de WordPress."""
import os
import shutil
from colorama import Fore

from ..ui import edu_print
from ..runner import run_cmd


def run_wpscan(target, protocol, workspace_dir):
    base_url = f"{protocol}{target}/"

    if shutil.which('wpscan') is None:
        print(f"{Fore.RED}[!] WPScan no encontrado. (sudo apt install wpscan).")
        return

    edu_print(
        tool="WPScan",
        phase="Escaneo Específico de CMS (WordPress)",
        explanation="- 'wpscan --url <target> -e u,vp --update':\n"
                    "- '--update': BBDD de vulnerabilidades al día.\n"
                    "- '-e u': Enumera usuarios válidos del panel.\n"
                    "- '-e vp': Enumera Plugins Vulnerables contra wpvulndb."
    )

    log_file = os.path.join(workspace_dir, "web", "wpscan_resultados.txt")
    run_cmd(['wpscan', '--url', base_url, '-e', 'u,vp', '--update'],
            capture_output=True, log_file=log_file)
