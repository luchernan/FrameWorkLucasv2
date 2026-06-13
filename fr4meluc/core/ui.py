"""UI helpers — toda la presentación en terminal vive aquí.

Esto permite que el motor (core/tools/*) sea puramente lógico y reutilizable
desde la futura GUI PyQt6 sin arrastrar dependencias de colorama.
"""
import os
import sys
import time
import itertools
from colorama import Fore, Style

W = 72  # Ancho global del terminal


# ─────────────────────────────────────────────────────────────
#  Educational mode toggle
# ─────────────────────────────────────────────────────────────
_EDU_ENABLED = True


def set_educational(enabled: bool) -> None:
    """Activa/desactiva la capa educativa (edu_print). Útil para --quiet o GUI pro."""
    global _EDU_ENABLED
    _EDU_ENABLED = bool(enabled)


def is_educational() -> bool:
    return _EDU_ENABLED


# ─────────────────────────────────────────────────────────────
#  Primitivas de pintado
# ─────────────────────────────────────────────────────────────
def _clr():
    """Limpia la pantalla de forma compatible."""
    os.system('clear' if os.name == 'posix' else 'cls')


def _line(char="═", color=Fore.CYAN):
    print(f"{color}{char * W}{Style.RESET_ALL}")


def _box_title(title, color=Fore.CYAN, icon=""):
    inner = W - 2
    label = f" {title} "
    pad = inner - len(label)
    left = pad // 2
    right = pad - left
    print(f"{color}╔{'═' * inner}╗")
    print(f"{color}║{' ' * left}{Style.BRIGHT}{label}{Style.RESET_ALL}{color}{' ' * right}║")
    print(f"{color}╚{'═' * inner}╝{Style.RESET_ALL}")


def _section(title, icon="", color=Fore.BLUE):
    label = f" {title} "
    side = (W - len(label) - 2) // 2
    rest = W - side - len(label) - 2
    print(f"\n{color}{'─' * side}[{Style.BRIGHT}{label}{Style.RESET_ALL}{color}]{'─' * rest}{Style.RESET_ALL}")


def _opt(num, desc, status=None, color=Fore.WHITE, icon=""):
    num_str = f"{Fore.CYAN}{Style.BRIGHT} [{num:>2}]{Style.RESET_ALL}"
    desc_str = f"{color}{desc}{Style.RESET_ALL}"
    status_str = f"  {status}" if status else ""
    print(f"{num_str}   {desc_str}{status_str}")


def _prompt(msg="Selección"):
    return input(f"\n  {Fore.GREEN}╰─{Style.BRIGHT}❯{Style.RESET_ALL} {Fore.WHITE}{msg}: {Style.RESET_ALL}").strip()


def _ok(msg):   print(f"  {Fore.GREEN}✔  {msg}{Style.RESET_ALL}")
def _warn(msg): print(f"  {Fore.YELLOW}⚠  {msg}{Style.RESET_ALL}")
def _err(msg):  print(f"  {Fore.RED}✘  {msg}{Style.RESET_ALL}")
def _info(msg): print(f"  {Fore.CYAN}ℹ  {msg}{Style.RESET_ALL}")


def _badge(text, color=Fore.GREEN):
    return f"{color}[{text}]{Style.RESET_ALL}"


# ─────────────────────────────────────────────────────────────
#  Spinner para procesos largos
# ─────────────────────────────────────────────────────────────
def _spinner_run(label, proc):
    """Spinner animado con tiempo transcurrido mientras proc (Popen) sigue corriendo."""
    frames = itertools.cycle(['|', '/', '-', '\\'])
    start = time.time()
    try:
        while proc.poll() is None:
            elapsed = int(time.time() - start)
            frame = next(frames)
            sys.stdout.write(
                f"\r  {Fore.YELLOW}[{frame}]{Style.RESET_ALL}  {Fore.WHITE}{label}{Style.RESET_ALL}  "
                f"{Fore.CYAN}({elapsed}s){Style.RESET_ALL}   "
            )
            sys.stdout.flush()
            time.sleep(0.12)
    except KeyboardInterrupt:
        proc.terminate()
    finally:
        sys.stdout.write("\r" + " " * 72 + "\r")
        sys.stdout.flush()


# ─────────────────────────────────────────────────────────────
#  Banner principal
# ─────────────────────────────────────────────────────────────
def print_banner():
    _clr()
    lines = [
        f"{Fore.GREEN}{Style.BRIGHT}",
        "   ███████╗██████╗ ██╗  ██╗███╗   ███╗███████╗██╗      ██╗   ██╗ ██████╗",
        "   ██╔════╝██╔══██╗██║  ██║████╗ ████║██╔════╝██║      ██║   ██║██╔════╝",
        "   █████╗  ██████╔╝███████║██╔████╔██║█████╗  ██║      ██║   ██║██║     ",
        "   ██╔══╝  ██╔══██╗╚════██║██║╚██╔╝██║██╔══╝  ██║      ██║   ██║██║     ",
        "   ██║     ██║  ██║     ██║██║ ╚═╝ ██║███████╗███████╗ ╚██████╔╝╚██████╗",
        "   ╚═╝     ╚═╝  ╚═╝     ╚═╝╚═╝     ╚═╝╚══════╝╚══════╝  ╚═════╝  ╚═════╝",
        f"{Style.RESET_ALL}",
    ]
    for line in lines:
        sys.stdout.write(line + "\n")
        sys.stdout.flush()
        time.sleep(0.06)

    _line("═", Fore.GREEN)
    center_text = "  Fr4meLuc  |  Educational Pentesting Framework  v3.0  |  Linux & Ethical Use Only"
    pad = (W - len(center_text)) // 2
    print(f"{Fore.GREEN}{'═' * pad}{Style.BRIGHT}{Fore.YELLOW}{center_text}{Style.RESET_ALL}{Fore.GREEN}{'═' * (W - pad - len(center_text))}")
    _line("═", Fore.GREEN)
    print()


# ─────────────────────────────────────────────────────────────
#  Capa educativa
# ─────────────────────────────────────────────────────────────
def edu_print(tool, phase, explanation):
    """Caja educativa antes de ejecutar comando. Silenciable con set_educational(False)."""
    if not _EDU_ENABLED:
        return
    print(f"{Fore.CYAN}╔{'═' * (W-2)}╗")
    label = f"  [?] EDUCATIVO  --  {tool}"[:W-2]
    inner_pad = max(0, W - 2 - len(label))
    print(f"{Fore.CYAN}║{Style.BRIGHT}{Fore.WHITE}{label}{' ' * inner_pad}{Style.RESET_ALL}{Fore.CYAN}║")
    print(f"{Fore.CYAN}╠{'═' * (W-2)}╣")
    phase_row = f"  >> Fase: {phase}"
    if len(phase_row) > W - 2:
        phase_row = phase_row[:W - 5] + "..."
    print(f"{Fore.CYAN}║{Fore.YELLOW}{phase_row}{' ' * max(0, W-2-len(phase_row))}{Fore.CYAN}║")
    print(f"{Fore.CYAN}╠{'─' * (W-2)}╣")
    for expline in explanation.strip().split("\n"):
        row = f"  {expline}"
        if len(row) > W - 2:
            row = row[:W - 5] + "..."
        overflow = max(0, W - 2 - len(row))
        print(f"{Fore.CYAN}║{Fore.WHITE}{row}{' ' * overflow}{Fore.CYAN}║")
    print(f"{Fore.CYAN}╚{'═' * (W-2)}╝{Style.RESET_ALL}")
    print()
