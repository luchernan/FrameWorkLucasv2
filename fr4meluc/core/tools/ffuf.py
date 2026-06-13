"""Wrapper de FFuF: fuzzing de subdominios virtuales (VHost)."""
import os
import shutil
import subprocess
from colorama import Fore, Style

from ..ui import _line, _ok, _err, _spinner_run, edu_print


def run_ffuf_subdomains(target, protocol, domain, workspace_dir):
    """Lanza ffuf con Host header FUZZ.<domain> para descubrir subdominios."""
    base_url = f"{protocol}{target}/"

    if not domain:
        print(f"{Fore.RED}[!] ERROR: Necesitas haber descubierto y configurado un Dominio (vía Nmap).")
        return

    if shutil.which('ffuf') is None:
        print(f"{Fore.RED}[!] La herramienta 'ffuf' no está instalada.")
        return

    print(f"\n{Fore.GREEN}[*] Inicializando Suite FFUF contra {base_url} (Dominio Base: {domain}){Style.RESET_ALL}")

    wordlist = input(
        f"{Fore.CYAN}[?] Especifica ruta al diccionario DNS/Subdominios (pulsa enter para usar por defecto: "
        f"/usr/share/wordlists/dirbuster/directory-list-lowercase-2.3-medium.txt): "
    ).strip()
    if not wordlist:
        wordlist = "/usr/share/wordlists/dirbuster/directory-list-lowercase-2.3-medium.txt"

    if not os.path.exists(wordlist):
        print(f"{Fore.RED}[!] No existe la ruta del diccionario especificado: {wordlist}")
        print(f"{Fore.YELLOW}[!] En Kali: sudo apt install seclists.")
        return

    edu_print(
        tool="ffuf (Fuzz Faster U Fool)",
        phase="Reconocimiento Avanzado (Fuerza Bruta de Subdominios Virtuales)",
        explanation=f"- Envía miles de peticiones HTTP modificando la cabecera 'Host: [palabra].{domain}'.\n"
                    f"- Sirve para hallar paneles ocultos como ftp.{domain} o admin.{domain}.\n"
                    f"- Usamos '-fc 301,302,400' para ocultar redirecciones o fallos."
    )

    print(f"\n{Fore.YELLOW}[!] AVISO: FFUF operará en segundo plano silenciosamente.{Style.RESET_ALL}")

    log_file = os.path.join(workspace_dir, "web", f"ffuf_subdominios_{domain.replace('.', '_')}.txt")
    json_file = os.path.join(workspace_dir, "web", f"ffuf_{domain.replace('.', '_')}.json")
    cmd = ['ffuf', '-s', '-c', '-t', '200', '-w', wordlist,
           '-H', f"Host: FUZZ.{domain}",
           '-u', base_url, '-o', json_file, '-of', 'json']

    _line("-", Fore.YELLOW)
    print(f"  {Fore.YELLOW}>> COMANDO:{Style.RESET_ALL}  {Fore.WHITE}{' '.join(cmd)}")
    _line("-", Fore.YELLOW)
    print()

    try:
        with open(log_file, 'w', encoding='utf-8') as lf:
            proc = subprocess.Popen(cmd, stdout=lf, stderr=subprocess.DEVNULL)
        _spinner_run("FFuF buscando subdominios...", proc)
        proc.wait()
    except FileNotFoundError:
        _err("FFuF no encontrado.")
        return

    _ok(f"FFuF finalizado. Resultados en: {json_file}")
