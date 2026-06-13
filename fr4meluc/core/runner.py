"""Ejecución de comandos del sistema con captura opcional y logging."""
import subprocess
from datetime import datetime
from colorama import Fore, Style

from .ui import _line, _err


def run_cmd(cmd_list, capture_output=False, log_file=None, timeout=None):
    """Ejecuta un comando subprocess. Imprime cabecera, captura si se pide, escribe log.

    Devuelve el output (str) si capture_output/log_file, True si OK sin captura, None en error.
    """
    cmd_str = ' '.join(cmd_list)
    print()
    _line("─", Fore.YELLOW)
    print(f"  {Fore.YELLOW}▶ {Style.BRIGHT}COMANDO:{Style.RESET_ALL}  {Fore.WHITE}{cmd_str}")
    _line("─", Fore.YELLOW)
    print()
    try:
        if capture_output or log_file:
            result = subprocess.run(cmd_list, capture_output=True, text=True, timeout=timeout)
            output = result.stdout + (result.stderr if result.stderr else "")
            print(output)

            if log_file:
                with open(log_file, "w", encoding="utf-8") as f:
                    f.write("=== Reporte generado por el Framework Educativo de Pentesting ===\n")
                    f.write(f"Comando Ejecutado: {cmd_str}\n")
                    f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write("===============================================================\n\n")
                    f.write(output)
                print(f"\n{Fore.GREEN}[+] -> Evidencia guardada exitosamente en: {log_file}")

            return output
        else:
            subprocess.run(cmd_list, timeout=timeout)
            return True

    except subprocess.TimeoutExpired:
        _err(f"La herramienta '{cmd_list[0]}' superó el tiempo límite y fue abortada.")
        return None
    except FileNotFoundError:
        _err(f"La herramienta '{cmd_list[0]}' no se encuentra instalada en el sistema.")
        return None
    except Exception as e:
        _err(f"Error inesperado ejecutando '{cmd_list[0]}': {e}")
        return None
