"""Integración Webhook genérico — POST JSON del resumen de escaneo.

Contrato de error: NUNCA lanza. Fallos de red → stderr + return False.
"""

import sys
from datetime import datetime, timezone

import requests

_TIMEOUT_SECONDS = 10


def notify_webhook(scan_summary: dict, settings: dict) -> bool:
    """Envía el resumen del escaneo a un endpoint HTTP genérico.

    Args:
        scan_summary: dict con scan_id, target, status, findings_count,
                      critical_count, high_count.
        settings: dict que debe contener 'webhook_url' (URL).

    Returns:
        True si el POST tuvo éxito (2xx); False si falta config o falla la red.
    """
    url = (settings or {}).get("webhook_url")
    if not url:
        return False

    payload = {
        "source": "fr4meluc",
        "event": "scan_complete",
        "scan_id": scan_summary.get("scan_id"),
        "target": scan_summary.get("target"),
        "status": scan_summary.get("status"),
        "findings_count": scan_summary.get("findings_count", 0),
        "critical_count": scan_summary.get("critical_count", 0),
        "high_count": scan_summary.get("high_count", 0),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    try:
        resp = requests.post(url, json=payload, timeout=_TIMEOUT_SECONDS)
        resp.raise_for_status()
        return True
    except requests.exceptions.RequestException as exc:
        sys.stderr.write(f"[webhook] Error enviando notificación: {exc}\n")
        return False
