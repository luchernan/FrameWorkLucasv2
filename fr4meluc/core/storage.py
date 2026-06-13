"""CRUD de alto nivel sobre la DB SQLite de Fr4meLuc.

Todas las funciones abren y cierran su propia conexión para que el CLI
y la futura GUI puedan usarlas sin gestionar transacciones manualmente.
"""

from datetime import datetime
from .db import get_connection, init_db


# ─────────────────────────────────────────────────────────────
#  CLIENTS
# ─────────────────────────────────────────────────────────────

def get_or_create_client(name: str, contact: str = "", notes: str = "") -> int:
    """Devuelve el id del cliente. Lo crea si no existe."""
    with get_connection() as conn:
        row = conn.execute("SELECT id FROM clients WHERE name = ?", (name,)).fetchone()
        if row:
            return row["id"]
        cur = conn.execute(
            "INSERT INTO clients (name, contact, notes) VALUES (?, ?, ?)",
            (name, contact, notes),
        )
        return cur.lastrowid


def list_clients() -> list:
    with get_connection() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM clients ORDER BY name").fetchall()]


# ─────────────────────────────────────────────────────────────
#  PROJECTS
# ─────────────────────────────────────────────────────────────

def get_or_create_project(client_id: int, name: str, scope: str = "") -> int:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM projects WHERE client_id = ? AND name = ?",
            (client_id, name),
        ).fetchone()
        if row:
            return row["id"]
        cur = conn.execute(
            "INSERT INTO projects (client_id, name, scope) VALUES (?, ?, ?)",
            (client_id, name, scope),
        )
        return cur.lastrowid


def list_projects(client_id: int | None = None) -> list:
    with get_connection() as conn:
        if client_id is not None:
            rows = conn.execute(
                "SELECT p.*, c.name AS client_name FROM projects p "
                "JOIN clients c ON p.client_id = c.id WHERE p.client_id = ? ORDER BY p.created_at DESC",
                (client_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT p.*, c.name AS client_name FROM projects p "
                "JOIN clients c ON p.client_id = c.id ORDER BY p.created_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]


# ─────────────────────────────────────────────────────────────
#  SCANS
# ─────────────────────────────────────────────────────────────

def create_scan(target: str, workspace_dir: str,
                project_id: int | None = None,
                profile: str = "manual") -> int:
    """Inserta un nuevo escaneo y devuelve su id."""
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO scans (project_id, target, workspace_dir, profile) VALUES (?, ?, ?, ?)",
            (project_id, target, workspace_dir, profile),
        )
        return cur.lastrowid


def finish_scan(scan_id: int, status: str = "completed", notes: str = "") -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE scans SET status = ?, finished_at = ?, notes = ? WHERE id = ?",
            (status, datetime.now().isoformat(sep=" ", timespec="seconds"), notes, scan_id),
        )


def get_project_scans(project_id: int) -> list:
    with get_connection() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM scans WHERE project_id = ? ORDER BY started_at DESC",
            (project_id,),
        ).fetchall()]


def get_scan(scan_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM scans WHERE id = ?", (scan_id,)).fetchone()
        return dict(row) if row else None


# ─────────────────────────────────────────────────────────────
#  FINDINGS
# ─────────────────────────────────────────────────────────────

def save_finding(scan_id: int, category: str, title: str,
                 severity: str = "info", detail: str = "", evidence: str = "") -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO findings (scan_id, category, title, severity, detail, evidence) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (scan_id, category, title, severity, detail, evidence),
        )
        return cur.lastrowid


def get_scan_findings(scan_id: int) -> list:
    with get_connection() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM findings WHERE scan_id = ? ORDER BY severity, category",
            (scan_id,),
        ).fetchall()]


# ─────────────────────────────────────────────────────────────
#  DIFF entre dos escaneos del mismo proyecto
# ─────────────────────────────────────────────────────────────

def diff_scans(scan_id_a: int, scan_id_b: int) -> dict:
    """Compara los findings de dos escaneos.

    Retorna:
        new       → findings en B que no estaban en A  (aparecieron)
        resolved  → findings en A que no están en B   (desaparecieron)
        persisted → findings en ambos                 (siguen presentes)

    La clave de comparación es (category, title) — dos hallazgos son
    "el mismo" si tienen la misma categoría y el mismo nombre.
    """
    findings_a = {(f["category"], f["title"]): f for f in get_scan_findings(scan_id_a)}
    findings_b = {(f["category"], f["title"]): f for f in get_scan_findings(scan_id_b)}

    keys_a = set(findings_a)
    keys_b = set(findings_b)

    return {
        "new":       [findings_b[k] for k in (keys_b - keys_a)],
        "resolved":  [findings_a[k] for k in (keys_a - keys_b)],
        "persisted": [findings_b[k] for k in (keys_a & keys_b)],
        "scan_a":    get_scan(scan_id_a),
        "scan_b":    get_scan(scan_id_b),
    }


# ─────────────────────────────────────────────────────────────
#  Importar workspace existente a la DB
# ─────────────────────────────────────────────────────────────

def import_workspace(workspace_dir: str,
                     project_id: int | None = None) -> int:
    """Lee los artefactos de un workspace previo y los persiste como un escaneo.

    Parsea:
      - nmap/nmap.xml           → findings category="port"
      - web/nuclei.json         → findings category="nuclei"
      - web/gobuster_*.txt      → findings category="directory"
    """
    import os
    from .parsers import parse_nmap, parse_nuclei

    # Extraer la IP del nombre de la carpeta (workspace_1_2_3_4 → 1.2.3.4)
    base = os.path.basename(workspace_dir.rstrip("/\\"))
    target = base.replace("workspace_", "").replace("_", ".")

    scan_id = create_scan(target, workspace_dir, project_id=project_id, profile="imported")

    # Puertos de Nmap
    nmap_xml = os.path.join(workspace_dir, "nmap", "nmap.xml")
    for port in parse_nmap(nmap_xml):
        if port["state"] == "open":
            save_finding(
                scan_id,
                category="port",
                title=f"{port['port']}/{port['protocol']} {port['service']}",
                severity="info",
                detail=port.get("version", ""),
            )

    # Hallazgos Nuclei
    for vuln in parse_nuclei(workspace_dir):
        save_finding(
            scan_id,
            category="nuclei",
            title=vuln.get("name") or vuln.get("template-id", "?"),
            severity=vuln.get("severity", "info"),
            detail=vuln.get("matched-at", ""),
        )

    finish_scan(scan_id, status="imported")
    return scan_id


# ─────────────────────────────────────────────────────────────
#  SCHEDULER JOBS
# ─────────────────────────────────────────────────────────────

def list_scheduler_jobs(enabled_only: bool = True) -> list:
    """Devuelve los jobs del scheduler, opcionalmente solo los habilitados.

    Args:
        enabled_only: si True, filtra a enabled = 1.

    Returns:
        Lista de dicts (una fila por job), ordenada por id.
    """
    with get_connection() as conn:
        if enabled_only:
            rows = conn.execute(
                "SELECT * FROM scheduler_jobs WHERE enabled = 1 ORDER BY id"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM scheduler_jobs ORDER BY id"
            ).fetchall()
        return [dict(r) for r in rows]


def update_job_last_run(job_id: int) -> None:
    """Marca last_run = ahora para el job indicado."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE scheduler_jobs SET last_run = ? WHERE id = ?",
            (datetime.now().isoformat(sep=" ", timespec="seconds"), job_id),
        )


# ─────────────────────────────────────────────────────────────
#  FINISH + NOTIFY (nueva función — NO modifica finish_scan)
# ─────────────────────────────────────────────────────────────

_SETTINGS_FILE = "fr4meluc_settings.json"


def _load_settings() -> dict:
    """Carga la configuración de integraciones desde fr4meluc_settings.json.

    Devuelve {} si el archivo no existe o no es JSON válido. Nunca lanza.
    """
    import json

    try:
        with open(_SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except FileNotFoundError:
        return {}
    except (ValueError, OSError):
        return {}


def finish_scan_with_notify(scan_id: int, settings: dict | None = None,
                            status: str = "completed", notes: str = "") -> None:
    """Cierra un escaneo y dispara todas las integraciones habilitadas.

    No modifica finish_scan: la llama y luego notifica. Las integraciones se
    importan de forma perezosa para evitar imports circulares (integrations
    no debe arrastrarse al cargar storage).

    Cada integración se invoca solo si su clave de configuración está presente
    en `settings`. Ningún fallo de integración interrumpe el resto.

    Args:
        scan_id: escaneo a cerrar.
        settings: dict de configuración; si es None se carga del archivo.
        status: estado final del scan.
        notes: notas a persistir en el scan.
    """
    import sys

    # 1. Cerrar el scan primero (comportamiento idéntico al flujo existente).
    finish_scan(scan_id, status=status, notes=notes)

    # 4. Cargar settings del archivo si no se pasaron.
    if settings is None:
        settings = _load_settings()
    settings = settings or {}

    # 2. + 3. Construir el resumen y contar severidades a partir de los findings.
    scan = get_scan(scan_id)
    if scan is None:
        sys.stderr.write(f"[notify] scan_id {scan_id} no existe; se omite notificación.\n")
        return

    findings = get_scan_findings(scan_id)
    critical_count = sum(1 for f in findings if str(f.get("severity", "")).lower() == "critical")
    high_count = sum(1 for f in findings if str(f.get("severity", "")).lower() == "high")

    scan_summary = {
        "scan_id": scan_id,
        "target": scan.get("target"),
        "status": scan.get("status", status),
        "findings_count": len(findings),
        "critical_count": critical_count,
        "high_count": high_count,
    }

    # 5. Disparar integraciones según las claves presentes. Imports perezosos.
    if settings.get("slack_webhook"):
        try:
            from .integrations.slack import notify_slack
            notify_slack(scan_summary, settings)
        except Exception as exc:  # noqa: BLE001 — una integración no debe romper el cierre
            sys.stderr.write(f"[notify] Slack falló: {exc}\n")

    if settings.get("teams_webhook"):
        try:
            from .integrations.teams import notify_teams
            notify_teams(scan_summary, settings)
        except Exception as exc:  # noqa: BLE001
            sys.stderr.write(f"[notify] Teams falló: {exc}\n")

    if settings.get("webhook_url"):
        try:
            from .integrations.webhook import notify_webhook
            notify_webhook(scan_summary, settings)
        except Exception as exc:  # noqa: BLE001
            sys.stderr.write(f"[notify] Webhook falló: {exc}\n")

    if all(settings.get(k) for k in ("jira_url", "jira_user", "jira_token", "jira_project")):
        try:
            from .integrations.jira import create_jira_issues
            create_jira_issues(findings, settings, scan_summary)
        except Exception as exc:  # noqa: BLE001
            sys.stderr.write(f"[notify] Jira falló: {exc}\n")
