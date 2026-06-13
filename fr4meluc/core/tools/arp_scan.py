"""Descubrimiento de red local con arp-scan."""
import shutil
from colorama import Fore, Style

from ..ui import edu_print
from ..runner import run_cmd
from ..network import get_network_interfaces


def do_arp_scan(target_menu_cb):
    """target_menu_cb: callable(ip) que abre el menú de ataque para una IP elegida."""
    if shutil.which('arp-scan') is None:
        print(f"{Fore.RED}[!] Herramienta no instalada. (Kali Linux: sudo apt install arp-scan).")
        return

    edu_print(
        tool="arp-scan",
        phase="Reconocimiento Inicial (Descubrimiento de Hosts Locales)",
        explanation="- 'sudo arp-scan -I [interfaz] -l': Emite paquetes ARP broadcast por interfaz.\n"
                    "- Podrás seleccionar visualmente qué tarjeta de red usar para descubrir hosts conectados."
    )

    while True:
        interfaces = get_network_interfaces()

        if not interfaces:
            print(f"{Fore.YELLOW}[*] No se detectaron interfaces extra, probando modo por defecto...")
            success = run_cmd(['sudo', 'arp-scan', '-l'])
        else:
            print(f"\n{Fore.CYAN}[*] Interfaces de Red Detectadas:{Style.RESET_ALL}")
            for i, iface in enumerate(interfaces, 1):
                print(f"  {Fore.WHITE}{i}) {iface}{Style.RESET_ALL}")

            opc_todas = len(interfaces) + 1
            print(f"  {Fore.GREEN}{opc_todas}) Escanear en TODAS simultáneamente{Style.RESET_ALL}")
            print(f"  {Fore.RED}0) Salir / Volver al Menú Principal{Style.RESET_ALL}")

            opc = input(f"\n{Fore.CYAN}[?] Elige una opción (0-{opc_todas}): {Style.RESET_ALL}").strip()

            if opc == '0':
                return

            success = False
            if opc.isdigit() and 1 <= int(opc) <= len(interfaces):
                selected_iface = interfaces[int(opc) - 1]
                print(f"\n{Fore.MAGENTA}=== Escaneando por interfaz: {Style.BRIGHT}{selected_iface}{Style.NORMAL} (Timeout 15s) ==={Style.RESET_ALL}")
                if 'docker' in selected_iface.lower():
                    print(f"{Fore.YELLOW}[!] AVISO DOCKER: Si Arp-scan se queda 'congelado', pulsa 'Ctrl+C' para forzar su detención.{Style.RESET_ALL}")
                result = run_cmd(['sudo', 'arp-scan', '-I', selected_iface, '-l'], timeout=15)
                if result is not None:
                    success = True
                print("-" * 65)
            elif opc == str(opc_todas):
                for iface in interfaces:
                    print(f"\n{Fore.MAGENTA}=== Escaneando por interfaz: {Style.BRIGHT}{iface}{Style.NORMAL} (Timeout 15s) ==={Style.RESET_ALL}")
                    if 'docker' in iface.lower():
                        print(f"{Fore.YELLOW}[!] AVISO DOCKER: Ctrl+C para forzar parada.{Style.RESET_ALL}")
                    result = run_cmd(['sudo', 'arp-scan', '-I', iface, '-l'], timeout=15)
                    if result is not None:
                        success = True
                    print("-" * 65)
            else:
                print(f"{Fore.RED}[!] Selección inválida.{Style.RESET_ALL}")
                continue

        if success:
            print(f"\n{Fore.CYAN}[?] Escaneo de red finalizado.")
            accion = input(f"{Fore.CYAN}[?] Escribe IP para atacar, 'otra' para buscar en otra interfaz, o 'salir': {Style.RESET_ALL}").strip().lower()
            if accion == 'salir':
                return
            elif accion == 'otra' or accion == '':
                continue
            else:
                target_menu_cb(accion)
                return
