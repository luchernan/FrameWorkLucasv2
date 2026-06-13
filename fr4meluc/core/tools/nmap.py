"""Wrapper de Nmap: escaneo en dos fases (descubrimiento + enumeración profunda)."""
import os
import re
from colorama import Fore, Style

from ..ui import _box_title, _section, _opt, _prompt, _line, _info, _warn, _ok, edu_print
from ..runner import run_cmd
from ..parsers import extract_domains_from_nmap
from ..network import add_to_hosts


def run_nmap(ip, workspace_dir):
    """Devuelve dict con has_web, web_protocol y domains aceptados (añadidos a /etc/hosts)."""
    _box_title("CONFIGURACION DEL ESCANEO  --  Nmap", Fore.YELLOW)
    _section("Elige tu perfil de descubrimiento de puertos", color=Fore.YELLOW)
    _opt(1, "Rapido y Ruidoso",
         status=f"{Fore.RED}[T4  |  --min-rate 5000  |  Alta deteccion por IDS]{Style.RESET_ALL}")
    _opt(2, "Lento y Silencioso (Stealth)",
         status=f"{Fore.GREEN}[T2  |  Evasion basica de Firewalls/IDS]{Style.RESET_ALL}")
    print()
    _line("─", Fore.YELLOW)
    speed_opc = _prompt("Perfil de escaneo (1/2) [Default: 1]")

    if speed_opc == '2':
        nmap_f1_cmd = ['nmap', '-p-', '--open', '-T2', '-n', '-Pn', ip]
        edu_print(
            tool="nmap (Fase 1: Descubrimiento Silencioso)",
            phase="Escaneo Cauteloso de 65535 Puertos",
            explanation="- 'nmap -p- --open -T2 -n -Pn <ip>':\n"
                        "- Busca puertos abiertos lentamente (-T2) limitando la tasa de paquetes.\n"
                        "- Ideal para no saturar la red o intentar evadir reglas simples de IDS/IPS."
        )
        _warn("Iniciando Fase 1 en modo SIGILO. Esto puede tardar varios minutos...")
    else:
        nmap_f1_cmd = ['nmap', '-p-', '--open', '-T4', '--min-rate', '5000', '-n', '-Pn', ip]
        edu_print(
            tool="nmap (Fase 1: Descubrimiento Rápido)",
            phase="Escaneo Agresivo de 65535 Puertos",
            explanation="- 'nmap -p- --open -T4 --min-rate 5000 -n -Pn <ip>':\n"
                        "- Busca a máxima velocidad puertos abiertos en todo el rango (1-65535).\n"
                        "- '--min-rate 5000': Fuerza a enviar 5000 paquetes por segundo (Muy agresivo/Ruidoso)."
        )
        _info("Iniciando Fase 1 en modo RÁPIDO. Esto puede tardar entre 10 y 60 segundos...")

    output_f1 = run_cmd(nmap_f1_cmd, capture_output=True)

    puertos = []
    if output_f1:
        puertos = re.findall(r'^(\d+)/tcp\s+open', output_f1, re.MULTILINE)

    if not puertos:
        print(f"\n{Fore.RED}[!] FASE 1 COMPLETADA: No se descubrió NINGÚN puerto abierto por TCP.")
        print(f"{Fore.RED}[!] Es posible que el host esté caído, bloqueando Pings o protegido por Firewall.{Style.RESET_ALL}")
        return {'has_web': False, 'web_protocol': 'http://', 'domains': []}

    puertos_str = ','.join(puertos)
    print(f"\n{Fore.GREEN}[+] FASE 1 COMPLETADA: Se encontraron los puertos abiertos: {Style.BRIGHT}{puertos_str}{Style.RESET_ALL}\n")

    edu_print(
        tool="nmap (Fase 2: Enumeración Profunda)",
        phase="Extracción de Servicios y Vulnerabilidades",
        explanation=f"- 'nmap -p {puertos_str} -sC -sV <ip>':\n"
                    f"- Solo se atacarán los puertos descubiertos para ahorrar horas de tiempo.\n"
                    "- Aplica Scripts Básicos (-sC) y Detecta Versiones Exactas (-sV)."
    )

    log_file = os.path.join(workspace_dir, "nmap", "escaneo_principal.txt")
    xml_file = os.path.join(workspace_dir, "nmap", "nmap.xml")
    output_f2 = run_cmd(['nmap', '-oX', xml_file, '-p', puertos_str, '-sC', '-sV', ip],
                       capture_output=True, log_file=log_file)

    accepted_domains = []
    has_web = False
    web_protocol = 'http://'

    if output_f2:
        domains = extract_domains_from_nmap(output_f2)
        if domains:
            print(f"\n{Fore.MAGENTA}--- ¡Atención! Nmap detectó nombre(s) de Dominio asociados ---{Style.RESET_ALL}")
            for dom in domains:
                if add_to_hosts(ip, dom):
                    accepted_domains.append(dom)
                    print(f"\n{Fore.GREEN}==================================================================")
                    print(f'{Fore.GREEN}[!] TIP EDUCATIVO: Has descubierto un "Virtual Host" (VHost / Dominio).{Style.RESET_ALL}')
                    print(f"    El dominio activo en el Framework cambiará automáticamente de '{ip}' a '{dom}'.")
                    print(f"{Fore.GREEN}==================================================================\n")

        if re.search(r'\d+/tcp\s+open\s+(ssl/http|https)', output_f2, re.IGNORECASE):
            has_web = True
            web_protocol = 'https://'
            print(f"{Fore.GREEN}[+] DETECCIÓN: Servidor seguro (HTTPS). Las herramientas web se adaptarán.{Style.RESET_ALL}")
        elif re.search(r'\d+/tcp\s+open\s+http\b', output_f2, re.IGNORECASE):
            has_web = True
            web_protocol = 'http://'
            print(f"{Fore.GREEN}[+] DETECCIÓN: Servidor clásico (HTTP).{Style.RESET_ALL}")

    return {'has_web': has_web, 'web_protocol': web_protocol, 'domains': accepted_domains}
