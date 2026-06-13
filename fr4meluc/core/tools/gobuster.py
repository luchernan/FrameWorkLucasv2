"""Wrapper de Gobuster: enumeración de directorios web."""
import os
import re
import shutil
import subprocess
from colorama import Fore, Style

from ..ui import _line, _ok, _info, _warn, _err, _spinner_run, edu_print, W


def run_web_enum(target, protocol, workspace_dir):
    """Lanza gobuster sobre {protocol}{target} y muestra resumen tabular."""
    base_url = f"{protocol}{target}"
    print(f"\n{Fore.GREEN}[*] Inicializando Suite Web contra {base_url}{Style.RESET_ALL}")

    print(f"\n{Fore.MAGENTA}--- Continuamos con Módulo Gobuster ---{Style.RESET_ALL}")
    if not shutil.which('gobuster'):
        _warn("Gobuster no encontrado. Saltando modulo.")
        return

    wordlist = input(
        f"{Fore.CYAN}[?] Especifica ruta al diccionario HTTP (pulsa enter para usar por defecto: "
        f"/usr/share/wordlists/dirbuster/directory-list-lowercase-2.3-medium.txt): "
    ).strip()
    if not wordlist:
        wordlist = "/usr/share/wordlists/dirbuster/directory-list-lowercase-2.3-medium.txt"

    if not os.path.exists(wordlist):
        print(f"{Fore.RED}[!] No existe la ruta del diccionario especificado: {wordlist}")
        return

    edu_print(
        tool="gobuster",
        phase="Fuzzing / Bypass (Descubrimiento de rutas secretas HTTP)",
        explanation="- Realiza validaciones por fuerza bruta contra el sistema de directorios web.\n"
                    "- Utiliza un archivo plano de palabras (diccionario) que probara una por una en la URL.\n"
                    "- '--no-progress': Suprime la barra de progreso; solo mostramos el resumen final."
    )

    log_file = os.path.join(workspace_dir, "web", "gobuster_directorios.txt")
    cmd = ['gobuster', 'dir', '-u', base_url, '-w', wordlist, '--no-progress']
    _line("-", Fore.YELLOW)
    print(f"  {Fore.YELLOW}>> COMANDO:{Style.RESET_ALL}  {Fore.WHITE}{' '.join(cmd)}")
    _line("-", Fore.YELLOW)
    print()

    try:
        with open(log_file, 'w', encoding='utf-8') as lf:
            proc = subprocess.Popen(cmd, stdout=lf, stderr=subprocess.DEVNULL)
        _spinner_run("Gobuster escaneando directorios...", proc)
        proc.wait()
    except FileNotFoundError:
        _err("Gobuster no encontrado.")
        return

    found = []
    if os.path.exists(log_file):
        with open(log_file, 'r', encoding='utf-8', errors='replace') as lf:
            for line in lf:
                m = re.match(r'^(/\S*)\s+\(Status:\s*(\d+)\)\s*\[Size:\s*(\d+)\]', line.strip())
                if m:
                    found.append({'path': m.group(1), 'status': m.group(2), 'size': m.group(3)})

    if found:
        _ok(f"Gobuster encontro {len(found)} recurso(s):")
        print()
        p_w, s_w, sz_w = 40, 8, 10
        print(f"  {Fore.CYAN}{'RUTA':<{p_w}}  {'STATUS':<{s_w}}  {'BYTES':<{sz_w}}{Style.RESET_ALL}")
        print(f"  {Fore.CYAN}{'-'*p_w}  {'-'*s_w}  {'-'*sz_w}{Style.RESET_ALL}")
        for r in found:
            sc = Fore.GREEN if r['status'].startswith('2') else (Fore.YELLOW if r['status'].startswith('3') else Fore.RED)
            print(f"  {Fore.WHITE}{r['path']:<{p_w}}{Style.RESET_ALL}  {sc}{r['status']:<{s_w}}{Style.RESET_ALL}  {Fore.CYAN}{r['size']:<{sz_w}}{Style.RESET_ALL}")
        print()
        _ok(f"Log completo en: {log_file}")
    else:
        _info("Gobuster no encontro rutas accesibles con este diccionario.")
