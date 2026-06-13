"""Integración Jira Cloud — crea un issue por hallazgo critical/high.

Usa la REST API v3 (Atlassian Document Format para la descripción) con auth
Basic (email:api_token).

Contrato de error: NUNCA lanza. Cada issue se intenta de forma aislada; un
fallo se registra en stderr y el bucle continúa con el resto.
"""

import sys

import requests
from requests.auth import HTTPBasicAuth

_TIMEOUT_SECONDS = 15
_REPORTABLE_SEVERITIES = ("critical", "high")
_REQUIRED_KEYS = ("jira_url", "jira_user", "jira_token", "jira_project")


def create_jira_issues(findings: list, settings: dict, scan_summary: dict) -> list:
    """Crea issues de Jira para los findings critical/high.

    Args:
        findings: lista de dicts de hallazgos (claves: severity, title, detail…).
        settings: debe contener jira_url, jira_user, jira_token, jira_project.
        scan_summary: resumen del escaneo (no usado en el payload base, pero
                      disponible para contexto futuro y para mantener el contrato).

    Returns:
        Lista de claves de issues creados (p.ej. ['SEC-12', 'SEC-13']).
        Vacía si falta configuración o no hay findings reportables.
    """
    settings = settings or {}
    if any(not settings.get(k) for k in _REQUIRED_KEYS):
        return []

    jira_url = str(settings["jira_url"]).rstrip("/")
    auth = HTTPBasicAuth(settings["jira_user"], settings["jira_token"])
    project_key = settings["jira_project"]
    endpoint = f"{jira_url}/rest/api/3/issue"
    headers = {"Content-Type": "application/json", "Accept": "application/json"}

    created_keys: list = []

    for finding in findings or []:
        severity = str(finding.get("severity", "")).lower()
        if severity not in _REPORTABLE_SEVERITIES:
            continue

        title = finding.get("title", "Untitled finding")
        detail = finding.get("detail", "") or ""
        priority = "Highest" if severity == "critical" else "High"

        payload = {
            "fields": {
                "project": {"key": project_key},
                "summary": f"[Fr4meLuc] {severity.upper()}: {title}",
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": detail or " "}],
                        }
                    ],
                },
                "issuetype": {"name": "Bug"},
                "priority": {"name": priority},
            }
        }

        try:
            resp = requests.post(
                endpoint,
                json=payload,
                auth=auth,
                headers=headers,
                timeout=_TIMEOUT_SECONDS,
            )
            resp.raise_for_status()
            data = resp.json()
            key = data.get("key")
            if key:
                created_keys.append(key)
            else:
                sys.stderr.write(
                    f"[jira] Respuesta sin 'key' para finding '{title}': {data}\n"
                )
        except requests.exceptions.RequestException as exc:
            sys.stderr.write(f"[jira] Error creando issue para '{title}': {exc}\n")
            continue
        except ValueError as exc:
            # resp.json() falló: respuesta no-JSON. Registrar y seguir.
            sys.stderr.write(f"[jira] Respuesta no-JSON para '{title}': {exc}\n")
            continue

    return created_keys
