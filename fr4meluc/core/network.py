"""Operaciones de red: interfaces, /etc/hosts y fingerprint TTL."""
import os
import re
import sys
import subprocess
from colorama import Fore, Style

from .ui import edu_print
from .runner import run_cmd


def get_network_interfaces() -> list:
    """Lista todas las interfaces de red del sistema (Linux: /sys/class/net/)."""
    interfaces = []
    try:
        if sys.platform != 'win32':
            net_dir = '/sys/class/net/'
            if os.path.exists(net_dir):
                interfaces = list(os.listdir(net_dir))
    except Exception as e:
        print(f"{Fore.RED}[!] Fallo al obtener interfaces: {e}")
    return interfaces


def add_to_hosts(ip: str, domain: str) -> bool:
    """Pide confirmación y añade '<ip> <domain>' a /etc/hosts si no existe."""
    print(f"\n{Fore.GREEN}[!] Hemos detectado un dominio asociado a la IP: {Style.BRIGHT}{domain}{Style.RESET_ALL}")
    ans = input(f"{Fore.CYAN}[?] ¿Deseas inyectar '{ip} {domain}' en tu archivo /etc/hosts? (S/n): ").strip().lower()

    if ans == '' or ans == 's':
        try:
            entry = f"{ip} {domain}"
            with open('/etc/hosts', 'r') as f:
                if entry in f.read():
                    print(f"{Fore.YELLOW}[*] La entrada '{entry}' ya existía en /etc/hosts. Omitiendo.")
                    return True
            print(f"{Fore.YELLOW}[>] Ejecutando: sudo bash -c \"echo '{entry}' >> /etc/hosts\"")
            subprocess.run(['sudo', 'bash', '-c', f"echo '{entry}' >> /etc/hosts"], check=True)
            print(f"{Fore.GREEN}[+] ¡El dominio '{domain}' se añadió correctamente a /etc/hosts!")
            return True
        except subprocess.CalledProcessError:
            print(f"{Fore.RED}[!] Falló al modificar /etc/hosts. Quizás cancelaste el 'sudo'.")
        except Exception as e:
            print(f"{Fore.RED}[!] Error modificando /etc/hosts: {e}")
    else:
        print(f"{Fore.YELLOW}[*] Omitiendo grabación de /etc/hosts.")
    return False


def detect_os(ip: str, workspace_dir: str) -> None:
    """Fingerprint de SO basado en el TTL devuelto por un único ping."""
    edu_print(
        tool="ping",
        phase="Identificación de Sistema Operativo (Fingerprinting)",
        explanation="- 'ping -c 1 <ip>': Envía un (1) único paquete ICMP echo request al objetivo.\n"
                    "- Observaremos el valor TTL (Time To Live) contenido en el paquete de respuesta:\n"
                    "  -> Si el TTL ronda el valor 64, suele tratarse de un sistema operativo LINUX/UNIX.\n"
                    "  -> Si el TTL ronda el valor 128, suele tratarse de un sistema operativo WINDOWS."
    )

    log_file = os.path.join(workspace_dir, "os_discovery", "ping_ttl.txt")
    output = run_cmd(['ping', '-c', '1', ip], capture_output=True, log_file=log_file)

    if output:
        match = re.search(r'ttl=(\d+)', output, re.IGNORECASE)
        if match:
            ttl = int(match.group(1))
            print(f"{Fore.GREEN}[+] Paquete recibido. Se obtuvo un TTL de: {ttl}")
            if ttl <= 64:
                os_guess = "LINUX / NIX"
            elif ttl <= 128:
                os_guess = "WINDOWS"
            else:
                os_guess = "DISPOSITIVO DE RED (Cisco, Routers, etc.)"
            print(f"{Fore.CYAN}[->] Sistema Operativo Estimado: {os_guess}")
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"\n[!] Conclusión del Framework: El sistema objetivo parece ser {os_guess} (basado en su TTL de {ttl}).\n")
        else:
            print(f"{Fore.RED}[!] No se detectó un campo TTL válido en la respuesta. (Podrían bloquear ICMP/Ping)")
