"""Integración Microsoft Teams — notifica vía Incoming Webhook (MessageCard).

Contrato de error: NUNCA lanza. Fallos de red → stderr + return False.
"""

import sys

import requests

_TIMEOUT_SECONDS = 10


def notify_teams(scan_summary: dict, settings: dict) -> bool:
    """Publica una Adaptive/MessageCard mínima en el webhook de Teams.

    Args:
        scan_summary: dict con scan_id, target, status, findings_count,
                      critical_count, high_count.
        settings: dict que debe contener 'teams_webhook' (URL).

    Returns:
        True si el POST tuvo éxito (2xx); False si falta config o falla la red.
    """
    webhook = (settings or {}).get("teams_webhook")
    if not webhook:
        return False

    scan_id = scan_summary.get("scan_id")
    target = scan_summary.get("target")
    findings_count = scan_summary.get("findings_count", 0)
    critical_count = scan_summary.get("critical_count", 0)
    high_count = scan_summary.get("high_count", 0)

    payload = {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "summary": "Fr4meLuc Scan Complete",
        "themeColor": "FF0000",
        "title": "Fr4meLuc Scan Complete",
        "text": (
            f"Scan #{scan_id} on {target}: {findings_count} findings "
            f"({critical_count} CRITICAL, {high_count} HIGH)"
        ),
    }

    try:
        resp = requests.post(webhook, json=payload, timeout=_TIMEOUT_SECONDS)
        resp.raise_for_status()
        return True
    except requests.exceptions.RequestException as exc:
        sys.stderr.write(f"[teams] Error enviando notificación: {exc}\n")
        return False
