"""Descarga de LinPEAS / WinPEAS para escalada de privilegios."""
import os
import subprocess
from colorama import Fore, Style

from ..ui import _line


def download_peas(workspace_dir):
    print(f"\n{Fore.GREEN}[*] Descargando scripts de escalada de privilegios (PEAS)...{Style.RESET_ALL}")
    payload_dir = os.path.join(workspace_dir, "payloads")
    if not os.path.exists(payload_dir):
        os.makedirs(payload_dir)

    linpeas_url = "https://github.com/peass-ng/PEASS-ng/releases/latest/download/linpeas.sh"
    winpeas_url = "https://github.com/peass-ng/PEASS-ng/releases/latest/download/winPEASany.exe"

    _line("-", Fore.YELLOW)
    print(f"{Fore.CYAN}[>] Descargando LinPEAS...{Style.RESET_ALL}")
    subprocess.run(['wget', '-q', '--show-progress', '-O', os.path.join(payload_dir, 'linpeas.sh'), linpeas_url])

    print(f"{Fore.CYAN}[>] Descargando WinPEAS...{Style.RESET_ALL}")
    subprocess.run(['wget', '-q', '--show-progress', '-O', os.path.join(payload_dir, 'winpeas.exe'), winpeas_url])
    _line("-", Fore.YELLOW)

    print(f"\n{Fore.GREEN}[+] Descargas completadas en: {payload_dir}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}[*] Sugerencia: Usa ahora la opción de 'Servidor HTTP' para servirlos a la víctima.{Style.RESET_ALL}")
