"""Wrapper de John The Ripper: cracking offline de hashes."""
import os
import shutil
import subprocess
from colorama import Fore, Style

from ..ui import edu_print
from ..runner import run_cmd


def run_hash_cracking(workspace_dir):
    if shutil.which('john') is None:
        print(f"{Fore.RED}[!] John The Ripper no está instalado. Instálalo con: sudo apt install john")
        return

    print(f"\n{Fore.GREEN}[*] Inicializando Suite JOHN THE RIPPER (Cracking de Hashes offline){Style.RESET_ALL}")

    hash_input = input(f"{Fore.CYAN}[?] Introduce el hash a crackear (ej. $1$abcde$12345) o Enter para salir: ").strip()
    if not hash_input:
        return

    wordlist = input(f"{Fore.CYAN}[?] Ruta del diccionario (Enter para /usr/share/wordlists/rockyou.txt): ").strip()
    if not wordlist:
        wordlist = "/usr/share/wordlists/rockyou.txt"

    if not os.path.exists(wordlist):
        print(f"{Fore.RED}[!] No se encontró el diccionario: {wordlist}")
        return

    edu_print(
        tool="John The Ripper",
        phase="Explotación / Escalamiento (Descifrado Offline)",
        explanation="- 'john --wordlist=diccionario hash.txt':\n"
                    "- Intenta adivinar la contraseña original probando miles de palabras contra el hash."
    )

    hash_file = os.path.join(workspace_dir, "exploits", "target_hash.txt")
    with open(hash_file, "w") as f:
        f.write(hash_input + "\n")

    print(f"{Fore.YELLOW}[>] Guardando Hash en: {hash_file}{Style.RESET_ALL}")
    log_file = os.path.join(workspace_dir, "exploits", "john_cracking_results.txt")

    print(f"{Fore.YELLOW}[>] Ejecutando John... Esto puede tardar.{Style.RESET_ALL}")
    run_cmd(['john', f'--wordlist={wordlist}', hash_file], capture_output=False, log_file=log_file)
    print(f"\n{Fore.GREEN}[*] Ejecutando john --show para ver resultados...{Style.RESET_ALL}")
    subprocess.run(['john', '--show', hash_file])
