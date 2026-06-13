"""Wrapper de SearchSploit: busca exploits públicos a partir del escaneo de Nmap."""
import os
import re
import shutil
from colorama import Fore, Style

from ..ui import edu_print
from ..runner import run_cmd


def _clean_service_version(raw_service, raw_version):
    """Limpia ruido típico de Nmap (httpd, sshd…) para una query útil a searchsploit."""
    version_no_os = re.sub(r'\(.*?\)', '', raw_version).strip()
    tokens = version_no_os.split()
    ignored = ['httpd', 'smbd', 'sshd', 'ftpd']
    safe_tokens = [t for t in tokens if t.lower() not in ignored]
    if not safe_tokens:
        return raw_service
    return f"{safe_tokens[0]} {safe_tokens[1]}" if len(safe_tokens) > 1 else safe_tokens[0]


def run_searchsploit(workspace_dir):
    if shutil.which('searchsploit') is None:
        print(f"{Fore.RED}[!] Searchsploit/Exploit-DB no instalados.")
        return

    nmap_file = os.path.join(workspace_dir, "nmap", "escaneo_principal.txt")
    if not os.path.exists(nmap_file):
        print(f"{Fore.RED}[!] No se puede automatizar SearchSploit: primero ejecuta Nmap (Opción 2).")
        return

    edu_print(
        tool="searchsploit",
        phase="Análisis de Vulnerabilidades Automatizado",
        explanation="- El script extraerá dinámicamente los servicios y versiones descubiertos por Nmap.\n"
                    "- Luego, buscará automáticamente Exploits Públicos (CVEs) para cada uno."
    )

    print(f"{Fore.CYAN}[*] Analizando resultados de Nmap para extraer versiones de servicios...{Style.RESET_ALL}")

    services_found = []
    with open(nmap_file, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            match = re.match(r'^\d+/\w+\s+open\s+([\w\-]+)\s+(.+)$', line.strip())
            if match:
                servicio = match.group(1).strip()
                version = match.group(2).strip()
                query = _clean_service_version(servicio, version)
                if query and query not in [q for _, q in services_found]:
                    services_found.append((servicio, query))

    if not services_found:
        print(f"{Fore.YELLOW}[!] Nmap no logró determinar versiones exactas. Sin material para searchsploit.")
        return

    for srv, query in services_found:
        print(f"\n{Fore.GREEN}[*] Buscando exploits para => {Style.BRIGHT}{srv}: {query}{Style.RESET_ALL}")
        cmd = ['searchsploit'] + query.split()
        safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', query)
        log_file = os.path.join(workspace_dir, "exploits", f"exploits_{srv}_{safe_name}.txt")
        run_cmd(cmd, capture_output=True, log_file=log_file)
