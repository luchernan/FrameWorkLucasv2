"""Wrapper de Nikto: scanner clásico de vulnerabilidades web."""
import os
import shutil
import subprocess
from colorama import Fore, Style

from ..ui import _line, _ok, _info, _err, _spinner_run, edu_print, W


def run_nikto(target, protocol, workspace_dir):
    base_url = f"{protocol}{target}"

    if shutil.which('nikto') is None:
        _err("Nikto no encontrado. Instala con: sudo apt install nikto")
        return

    edu_print(
        tool="Nikto",
        phase="Escaneo de Vulnerabilidades Web Clasico",
        explanation="- 'nikto -h <url>': Herramienta estandar de auditoria web.\n"
                    "- Detecta ficheros peligrosos, versiones de servidor, cabeceras inseguras.\n"
                    "- Mas de 6700 checks incluidos. Ideal como primer analisis rapido."
    )

    log_file = os.path.join(workspace_dir, "web", "nikto_resultados.txt")
    cmd = ['nikto', '-h', base_url, '-o', log_file, '-Format', 'txt', '-nointeractive']

    _line("-", Fore.YELLOW)
    print(f"  {Fore.YELLOW}>> COMANDO:{Style.RESET_ALL}  {Fore.WHITE}{' '.join(cmd)}")
    _line("-", Fore.YELLOW)
    print()

    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        _spinner_run("Nikto auditando servidor web...", proc)
        proc.wait()
    except FileNotFoundError:
        _err("Nikto no encontrado.")
        return

    findings = []
    if os.path.exists(log_file):
        with open(log_file, 'r', encoding='utf-8', errors='replace') as lf:
            for line in lf:
                line = line.rstrip()
                if line.startswith('+'):
                    findings.append(line[1:].strip())

    if findings:
        _ok(f"Nikto encontro {len(findings)} hallazgo(s):")
        print()
        for h in findings:
            display = h if len(h) <= W - 6 else h[:W - 9] + "..."
            print(f"  {Fore.YELLOW}[+]{Style.RESET_ALL} {Fore.WHITE}{display}{Style.RESET_ALL}")
        print()
        _ok(f"Log completo en: {log_file}")
    else:
        _info("Nikto no reporto hallazgos significativos.")
