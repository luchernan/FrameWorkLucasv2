"""Integración Slack — notifica el resumen de un escaneo vía Incoming Webhook.

Contrato de error: NUNCA lanza. Cualquier fallo de red se captura, se registra
en stderr y la función devuelve False.
"""

import sys

import requests

_TIMEOUT_SECONDS = 10


def notify_slack(scan_summary: dict, settings: dict) -> bool:
    """Publica el resumen del escaneo en el webhook de Slack.

    Args:
        scan_summary: dict con scan_id, target, status, findings_count,
                      critical_count, high_count.
        settings: dict que debe contener 'slack_webhook' (URL).

    Returns:
        True si el POST tuvo éxito (2xx); False si falta config o falla la red.
    """
    webhook = (settings or {}).get("slack_webhook")
    if not webhook:
        return False

    scan_id = scan_summary.get("scan_id")
    target = scan_summary.get("target")
    findings_count = scan_summary.get("findings_count", 0)
    critical_count = scan_summary.get("critical_count", 0)
    high_count = scan_summary.get("high_count", 0)

    payload = {
        "text": (
            f"Fr4meLuc scan #{scan_id} on {target} completed. "
            f"Findings: {findings_count} ({critical_count} CRITICAL, {high_count} HIGH)"
        )
    }

    try:
        resp = requests.post(webhook, json=payload, timeout=_TIMEOUT_SECONDS)
        resp.raise_for_status()
        return True
    except requests.exceptions.RequestException as exc:
        sys.stderr.write(f"[slack] Error enviando notificación: {exc}\n")
        return False
