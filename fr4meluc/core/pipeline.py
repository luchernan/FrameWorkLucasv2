"""Motor de pipeline data-driven para el modo automático de Fr4meLuc.

Diseño:
  - RULES es una lista de tuplas (condition_fn, action_fn) a nivel de módulo.
  - El bucle de `run_pipeline` NUNCA cambia; solo se edita la lista RULES.
  - Las condiciones inspeccionan el NOMBRE del servicio (no solo el puerto):
    detección web por puerto 80/443 O por servicio que contenga http/https/ssl.

Las acciones llaman `run_cmd` directamente con flags de automatización
hardcodeados. No se importan los wrappers interactivos (nmap.py, gobuster.py…)
para mantener el modo automático desacoplado de la UI/menús.

Cada acción parsea su salida y persiste hallazgos vía `save_finding`.
"""

import os

from .runner import run_cmd
from .storage import save_finding


# ─────────────────────────────────────────────────────────────
#  Helpers de detección sobre la lista de puertos parseada
# ─────────────────────────────────────────────────────────────

def _port_is_open(port: dict) -> bool:
    """Un puerto cuenta como abierto si su estado es 'open' (o si falta el estado).

    parse_nmap siempre informa 'state'; si por alguna razón viene ausente,
    asumimos abierto para no descartar trabajo silenciosamente.
    """
    state = (port.get("state") or "").lower()
    return state == "open" or state == ""


def _port_number(port: dict) -> str:
    """Devuelve el número de puerto como string (parse_nmap lo entrega como str)."""
    return str(port.get("port") or "").strip()


def _service_text(port: dict) -> str:
    """Concatena nombre de servicio y versión en minúsculas para matching robusto."""
    service = str(port.get("service") or "")
    version = str(port.get("version") or "")
    return f"{service} {version}".lower()


def _is_web_port(port: dict) -> bool:
    """True si el puerto abierto parece servir web.

    Coincide por número (80/443) O por nombre de servicio que contenga
    http/https/ssl — así detectamos web en puertos no estándar (8080, 8443…).
    """
    if not _port_is_open(port):
        return False
    if _port_number(port) in ("80", "443"):
        return True
    text = _service_text(port)
    return "http" in text or "https" in text or "ssl" in text


def _is_smb_port(port: dict) -> bool:
    """True si hay un puerto 445 abierto (SMB)."""
    return _port_is_open(port) and _port_number(port) == "445"


def _is_wordpress(port: dict) -> bool:
    """True si el servicio/versión menciona wordpress (case-insensitive)."""
    return _port_is_open(port) and "wordpress" in _service_text(port)


# ─────────────────────────────────────────────────────────────
#  Condiciones de RULES — operan sobre la lista COMPLETA de puertos
# ─────────────────────────────────────────────────────────────

def _cond_web(ports: list) -> bool:
    """¿Algún puerto abierto sirve web?"""
    return any(_is_web_port(p) for p in ports)


def _cond_smb(ports: list) -> bool:
    """¿Hay un 445 abierto?"""
    return any(_is_smb_port(p) for p in ports)


def _cond_wordpress(ports: list) -> bool:
    """¿Algún servicio menciona WordPress?"""
    return any(_is_wordpress(p) for p in ports)


# ─────────────────────────────────────────────────────────────
#  Parsers de evidencia → findings
# ─────────────────────────────────────────────────────────────

def _looks_like_result_line(line: str) -> bool:
    """Heurística: una línea es un resultado si parece una ruta o trae status code.

    - Empieza por '/'  (gobuster en modo dir lista rutas).
    - Contiene 'Status:' (formato gobuster -q).
    - Contiene un patrón de código HTTP entre paréntesis tipo '(Status: 200)'.
    - wpscan: líneas con '[+]' que suelen marcar hallazgos.
    """
    stripped = line.strip()
    if not stripped:
        return False
    if stripped.startswith("/"):
        return True
    if "Status:" in stripped:
        return True
    if stripped.startswith("[+]"):
        return True
    return False


def _save_lines_as_findings(scan_id: int, category: str, title: str,
                            severity: str, output: str) -> int:
    """Guarda un finding por cada línea de `output` que parezca un resultado.

    Devuelve el número de findings guardados. Si no hay líneas-resultado pero
    sí hubo salida, guarda un único finding-resumen para no perder evidencia.
    """
    if not output:
        return 0

    saved = 0
    for raw_line in output.splitlines():
        if _looks_like_result_line(raw_line):
            detail = raw_line.strip()[:500]
            save_finding(
                scan_id,
                category=category,
                title=title,
                severity=severity,
                detail=detail,
                evidence=detail,
            )
            saved += 1

    if saved == 0:
        # Hubo ejecución pero ninguna línea matcheó: conservar resumen.
        save_finding(
            scan_id,
            category=category,
            title=f"{title} (sin resultados parseables)",
            severity="info",
            detail=output[:500],
        )
        saved = 1

    return saved


# ─────────────────────────────────────────────────────────────
#  Acciones de RULES — ejecutan herramienta y persisten findings
# ─────────────────────────────────────────────────────────────

def _action_web(workspace_dir: str, target: str, scan_id: int) -> None:
    """Modo web automático: gobuster (dir enum) + nuclei."""
    web_dir = os.path.join(workspace_dir, "web")
    os.makedirs(web_dir, exist_ok=True)

    gobuster_out = os.path.join(web_dir, "gobuster_auto.txt")
    gobuster_cmd = [
        "gobuster", "dir",
        "-u", f"http://{target}",
        "-w", "/usr/share/wordlists/dirb/common.txt",
        "-o", gobuster_out,
        "-q", "--no-error",
    ]
    gobuster_output = run_cmd(gobuster_cmd, capture_output=True)
    if isinstance(gobuster_output, str):
        # Preferir el archivo -o si gobuster lo escribió; fallback a stdout.
        file_output = _read_if_exists(gobuster_out)
        _save_lines_as_findings(
            scan_id,
            category="web",
            title="gobuster dir enum",
            severity="info",
            output=file_output if file_output else gobuster_output,
        )

    nuclei_out = os.path.join(web_dir, "nuclei_auto.json")
    nuclei_cmd = [
        "nuclei",
        "-u", f"http://{target}",
        "-o", nuclei_out,
        "-json",
        "-silent",
    ]
    run_cmd(nuclei_cmd, capture_output=True)
    _save_nuclei_findings(scan_id, nuclei_out)


def _action_smb(workspace_dir: str, target: str, scan_id: int) -> None:
    """Modo SMB automático: enum4linux."""
    smb_dir = os.path.join(workspace_dir, "smb")
    os.makedirs(smb_dir, exist_ok=True)

    enum_log = os.path.join(smb_dir, "enum4linux_auto.txt")
    enum_cmd = ["enum4linux", "-a", target]
    output = run_cmd(enum_cmd, capture_output=True, log_file=enum_log)
    if isinstance(output, str):
        save_finding(
            scan_id,
            category="smb",
            title="enum4linux scan",
            severity="info",
            detail=output[:500],
            evidence=enum_log,
        )


def _action_wordpress(workspace_dir: str, target: str, scan_id: int) -> None:
    """Modo WordPress automático: wpscan."""
    web_dir = os.path.join(workspace_dir, "web")
    os.makedirs(web_dir, exist_ok=True)

    wpscan_out = os.path.join(web_dir, "wpscan_auto.txt")
    wpscan_cmd = [
        "wpscan",
        "--url", f"http://{target}",
        "--no-update",
        "-o", wpscan_out,
    ]
    output = run_cmd(wpscan_cmd, capture_output=True)
    if isinstance(output, str):
        file_output = _read_if_exists(wpscan_out)
        _save_lines_as_findings(
            scan_id,
            category="web",
            title="wpscan",
            severity="info",
            output=file_output if file_output else output,
        )


# ─────────────────────────────────────────────────────────────
#  Utilidades de parseo de archivos de salida
# ─────────────────────────────────────────────────────────────

def _read_if_exists(path: str) -> str:
    """Lee un archivo si existe y no está vacío; devuelve '' en cualquier fallo."""
    if not os.path.exists(path):
        return ""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def _save_nuclei_findings(scan_id: int, nuclei_file: str) -> int:
    """Parsea el JSONL de nuclei y guarda un finding por vuln con su severidad real.

    Devuelve el número de findings guardados. Tolerante a líneas corruptas.
    """
    import json

    content = _read_if_exists(nuclei_file)
    if not content:
        return 0

    saved = 0
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            vuln = json.loads(line)
        except json.JSONDecodeError:
            continue
        info = vuln.get("info", {}) if isinstance(vuln, dict) else {}
        name = info.get("name") or vuln.get("template-id") or "nuclei finding"
        severity = (info.get("severity") or "info").lower()
        matched = vuln.get("matched-at") or vuln.get("host") or ""
        save_finding(
            scan_id,
            category="nuclei",
            title=str(name)[:200],
            severity=severity,
            detail=str(matched)[:500],
            evidence=line[:500],
        )
        saved += 1
    return saved


# ─────────────────────────────────────────────────────────────
#  RULES — data-driven. Solo esta lista cambia para añadir comportamiento.
#  Cada entrada: (condition_fn(ports) -> bool, action_fn(ws, target, scan_id), name)
# ─────────────────────────────────────────────────────────────

RULES = [
    (_cond_web, _action_web, "web (gobuster+nuclei)"),
    (_cond_smb, _action_smb, "smb (enum4linux)"),
    (_cond_wordpress, _action_wordpress, "wordpress (wpscan)"),
]


def run_pipeline(ports: list, workspace_dir: str, target: str, scan_id: int) -> list:
    """Ejecuta el pipeline automático contra un target ya escaneado.

    Itera RULES en orden; por cada regla cuya condición se cumpla, ejecuta la
    acción correspondiente (que a su vez persiste findings en la DB).

    Args:
        ports: lista de dicts de parse_nmap (claves: port, protocol, state, service, version).
        workspace_dir: carpeta de evidencias del target.
        target: IP o host objetivo.
        scan_id: id del escaneo en la DB al que se asocian los findings.

    Returns:
        Lista de nombres de herramientas/reglas que efectivamente se ejecutaron.
    """
    # Asegurar subdirectorios de evidencia antes de que cualquier acción escriba.
    os.makedirs(os.path.join(workspace_dir, "web"), exist_ok=True)
    os.makedirs(os.path.join(workspace_dir, "smb"), exist_ok=True)

    ports = ports or []
    ran: list = []

    for condition_fn, action_fn, name in RULES:
        if condition_fn(ports):
            action_fn(workspace_dir, target, scan_id)
            ran.append(name)
        # Si la condición no se cumple, la regla se omite intencionadamente.

    return ran
