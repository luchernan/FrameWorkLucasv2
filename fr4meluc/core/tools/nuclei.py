"""Wrapper de Nuclei: scanner basado en plantillas YAML."""
import os
import json
import shutil
import subprocess
from colorama import Fore, Style

from ..ui import _line, _ok, _info, _warn, _err, _spinner_run, edu_print, W


def run_nuclei(target, protocol, workspace_dir):
    """Ejecuta nuclei -jsonl y muestra tabla resumen por severidad."""
    base_url = f"{protocol}{target}/"

    if shutil.which('nuclei') is None:
        print(f"{Fore.RED}[!] Nuclei no está instalado en tu sistema.{Style.RESET_ALL}")
        ans = input(f"{Fore.CYAN}[?] ¿Deseas instalar Nuclei ahora automáticamente? (S/n): {Style.RESET_ALL}").strip().lower()
        if ans == '' or ans == 's':
            print(f"{Fore.YELLOW}[>] Ejecutando: sudo apt update && sudo apt install -y nuclei{Style.RESET_ALL}")
            try:
                subprocess.run(['sudo', 'apt', 'update'], check=True)
                subprocess.run(['sudo', 'apt', 'install', '-y', 'nuclei'], check=True)
                print(f"{Fore.GREEN}[+] Nuclei instalado. Actualizando plantillas...{Style.RESET_ALL}")
                subprocess.run(['nuclei', '-ut'])
            except subprocess.CalledProcessError:
                print(f"{Fore.RED}[!] Falló la instalación de Nuclei.{Style.RESET_ALL}")
                return
            except FileNotFoundError:
                print(f"{Fore.RED}[!] APT no disponible (¿no estás en Debian/Kali?).{Style.RESET_ALL}")
                return
        else:
            print(f"{Fore.YELLOW}[!] Instalación omitida.{Style.RESET_ALL}")
            return

    edu_print(
        tool="Nuclei",
        phase="Escaneo Automático Basado en Plantillas de Vulnerabilidad (CVEs)",
        explanation="- 'nuclei -u <target>':\n"
                    "- Marco moderno de testeo de debilidades basado en archivos YAML.\n"
                    "- Busca CVEs, desactualizaciones de librerías y fugas de datos."
    )

    _warn("Nuclei iniciara la prueba de plantillas. Esto tardara varios minutos...")
    print()

    json_file = os.path.join(workspace_dir, "web", "nuclei.json")
    cmd = ['nuclei', '-u', base_url, '-jsonl', '-silent']
    _line("-", Fore.YELLOW)
    print(f"  {Fore.YELLOW}>> COMANDO:{Style.RESET_ALL}  {Fore.WHITE}{' '.join(cmd)} > {json_file}")
    _line("-", Fore.YELLOW)
    print()

    try:
        with open(json_file, 'w', encoding='utf-8') as jf:
            proc = subprocess.Popen(cmd, stdout=jf, stderr=subprocess.DEVNULL)
        _spinner_run("Nuclei analizando plantillas de vulnerabilidades...", proc)
        proc.wait()
    except FileNotFoundError:
        _err("Nuclei no encontrado en el sistema.")
        return

    findings = []
    if os.path.exists(json_file):
        with open(json_file, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    findings.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

    print(f"\n{Fore.CYAN}╔{'═' * (W-2)}╗")
    header = "  RESULTADOS NUCLEI"
    print(f"{Fore.CYAN}║{Style.BRIGHT}{Fore.WHITE}{header}{' ' * (W-2-len(header))}{Style.RESET_ALL}{Fore.CYAN}║")
    print(f"{Fore.CYAN}╚{'═' * (W-2)}╝{Style.RESET_ALL}")

    if not findings:
        _info("Nuclei no encontro hallazgos.")
    else:
        _ok(f"Se encontraron {len(findings)} hallazgo(s):")
        print()
        sev_w, name_w, url_w = 10, 36, W - 10 - 36 - 6
        print(f"  {Fore.CYAN}{'SEVERIDAD':<{sev_w}}  {'NOMBRE':<{name_w}}  {'URL':<{url_w}}{Style.RESET_ALL}")
        print(f"  {Fore.CYAN}{'-'*sev_w}  {'-'*name_w}  {'-'*url_w}{Style.RESET_ALL}")
        for v in findings:
            sev = v.get('info', {}).get('severity', 'info').upper()
            name = (v.get('info', {}).get('name') or v.get('template-id', '?'))[:name_w]
            url = (v.get('matched-at') or '')[:url_w]
            sev_color = (Fore.RED if sev in ('CRITICAL', 'HIGH')
                         else Fore.YELLOW if sev == 'MEDIUM'
                         else Fore.CYAN)
            print(f"  {sev_color}{sev:<{sev_w}}{Style.RESET_ALL}  {Fore.WHITE}{name:<{name_w}}{Style.RESET_ALL}  {Fore.BLUE}{url}{Style.RESET_ALL}")
        print()
        _ok(f"Resultados completos guardados en: {json_file}")
