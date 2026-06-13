"""Generador de informes PDF profesionales para Fr4meLuc Enterprise.

Renderiza un informe de auditoría completo (portada, resumen ejecutivo,
hallazgos, recomendaciones, alcance y anexos) a PDF usando WeasyPrint.

Decisiones de diseño:
  * Sin CDN de fuentes — WeasyPrint renderiza offline en Kali. Solo fuentes
    del sistema (`font-family: sans-serif`).
  * Logo embebido como base64 inline. Si falta o no se puede leer, se omite.
  * Marca "CONFIDENCIAL" en cada página vía CSS `@page`, no como div de cuerpo.
  * Degradación elegante: si WeasyPrint no está instalado, imprime un mensaje
    y devuelve None sin lanzar excepción.
"""

import os
import html

from .storage import get_scan, get_scan_findings


# ─────────────────────────────────────────────────────────────
#  Constantes de severidad
# ─────────────────────────────────────────────────────────────

# Orden de presentación: critical → high → medium → low → info
_SEV_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}

# Mapeo CVSS aproximado por severidad.
_SEV_CVSS = {
    "critical": 9.5,
    "high": 8.0,
    "medium": 5.5,
    "low": 2.0,
    "info": 0.0,
}

# Etiqueta legible en español por severidad.
_SEV_LABEL = {
    "critical": "CRÍTICO",
    "high": "ALTO",
    "medium": "MEDIO",
    "low": "BAJO",
    "info": "INFO",
}

# Clase CSS del badge de riesgo global / severidad por nivel.
_RISK_CLASS = {
    "critical": "risk-critical",
    "high": "risk-high",
    "medium": "risk-medium",
    "low": "risk-low",
    "info": "risk-info",
}

_SEV_BADGE_CLASS = {
    "critical": "sev-critical",
    "high": "sev-high",
    "medium": "sev-medium",
    "low": "sev-low",
    "info": "sev-info",
}

# Texto de recomendación por nivel (estático, tiered).
_RECOMMENDATION = {
    "critical": "Remediación inmediata requerida (< 24h). Escalar a CISO.",
    "high": "Remediación urgente (< 72h). Revisar controles de acceso.",
    "medium": "Planificar remediación en el siguiente ciclo (< 30 días).",
    "low": "Incluir en backlog de seguridad (< 90 días).",
    "info": "Revisar como mejora de visibilidad. Sin urgencia operativa.",
}

# Acciones recomendadas de alto nivel por severidad máxima detectada (top-3).
_TOP_ACTIONS = {
    "critical": [
        "Aislar o contener los activos críticos afectados de inmediato.",
        "Activar el plan de respuesta a incidentes y notificar al CISO.",
        "Aplicar parches o mitigaciones de emergencia en < 24 horas.",
    ],
    "high": [
        "Priorizar la remediación de los hallazgos de severidad alta (< 72h).",
        "Reforzar los controles de acceso y autenticación del perímetro.",
        "Verificar la exposición pública de los servicios afectados.",
    ],
    "medium": [
        "Programar la remediación de hallazgos medios en el siguiente ciclo.",
        "Endurecer la configuración de los servicios identificados.",
        "Revisar el cumplimiento de las políticas de hardening internas.",
    ],
    "low": [
        "Registrar los hallazgos de baja severidad en el backlog de seguridad.",
        "Evaluar el impacto acumulado de las debilidades menores.",
        "Mantener la monitorización continua del entorno evaluado.",
    ],
    "info": [
        "Revisar los hallazgos informativos como mejora de visibilidad.",
        "Documentar la superficie de exposición para futuras auditorías.",
        "Mantener el inventario de servicios actualizado.",
    ],
}


# ─────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────

def _load_settings() -> dict:
    """Carga `fr4meluc_settings.json` del cwd. Devuelve {} si falta o es inválido."""
    import json
    try:
        with open("fr4meluc_settings.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _logo_tag(logo_path: str) -> str:
    """Devuelve un <img> con el logo en base64, o '' si falta o no se puede leer."""
    import base64
    import mimetypes
    if not logo_path or not os.path.isfile(logo_path):
        return ""
    try:
        mime = mimetypes.guess_type(logo_path)[0] or "image/png"
        with open(logo_path, "rb") as f:
            data = base64.b64encode(f.read()).decode()
        return f'<img class="cover-logo" src="data:{mime};base64,{data}" alt="Logo">'
    except Exception:
        return ""


def _normalize_severity(value: str) -> str:
    """Normaliza una severidad arbitraria a una de las claves conocidas."""
    sev = (value or "").strip().lower()
    return sev if sev in _SEV_ORDER else "info"


def _sort_findings(findings: list) -> list:
    """Ordena hallazgos critical → high → medium → low → info."""
    return sorted(
        findings,
        key=lambda f: _SEV_ORDER.get(_normalize_severity(f.get("severity")), 4),
    )


def _severity_counts(findings: list) -> dict:
    """Cuenta hallazgos por severidad normalizada. Siempre incluye las 5 claves."""
    counts = {sev: 0 for sev in _SEV_ORDER}
    for f in findings:
        counts[_normalize_severity(f.get("severity"))] += 1
    return counts


def _overall_risk(findings: list) -> str:
    """Severidad más alta presente. 'info' si no hay hallazgos."""
    if not findings:
        return "info"
    return min(
        (_normalize_severity(f.get("severity")) for f in findings),
        key=lambda s: _SEV_ORDER[s],
    )


def _present_severities(findings: list) -> list:
    """Severidades realmente presentes, en orden de gravedad descendente."""
    present = {_normalize_severity(f.get("severity")) for f in findings}
    return sorted(present, key=lambda s: _SEV_ORDER[s])


def _truncate(text: str, limit: int) -> str:
    """Recorta un texto a `limit` caracteres, añadiendo elipsis si se trunca."""
    text = text or ""
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "…"


def _annex_html(workspace_dir: str) -> str:
    """Recorre workspace_dir buscando .txt y los renderiza en bloques <pre>.

    Cada archivo se trunca a 3000 caracteres y se escapa para HTML. Si no hay
    archivos .txt (o el directorio no existe), devuelve un aviso.
    """
    txt_files: list[str] = []
    if workspace_dir and os.path.isdir(workspace_dir):
        for root, _dirs, files in os.walk(workspace_dir):
            for name in sorted(files):
                if name.lower().endswith(".txt"):
                    txt_files.append(os.path.join(root, name))
    txt_files.sort()

    if not txt_files:
        return "<p>No se encontraron evidencias adicionales.</p>"

    blocks: list[str] = []
    for path in txt_files:
        rel = os.path.relpath(path, workspace_dir)
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except OSError as exc:
            content = f"[No se pudo leer el archivo: {exc}]"
        safe_name = html.escape(rel)
        safe_body = html.escape(_truncate(content, 3000))
        blocks.append(f"<h2>{safe_name}</h2>\n<pre>{safe_body}</pre>")
    return "\n".join(blocks)


def _build_html(scan: dict, findings: list, settings: dict,
                target: str, domain: str | None) -> str:
    """Construye el HTML completo del informe."""
    company = html.escape(settings.get("company_name") or "Fr4meLuc Enterprise")
    auditor = html.escape(settings.get("auditor_name") or "—")
    auditor_email = html.escape(settings.get("auditor_email") or "—")
    footer = html.escape(settings.get("report_footer") or "")
    logo_html = _logo_tag(settings.get("company_logo", ""))

    scan_date = scan.get("started_at") or "—"
    profile = scan.get("profile") or "—"
    safe_target = html.escape(target)
    subtitle = safe_target + (f"  /  {html.escape(domain)}" if domain else "")

    sorted_findings = _sort_findings(findings)
    counts = _severity_counts(findings)
    risk = _overall_risk(findings)
    risk_label = _SEV_LABEL[risk]
    risk_class = _RISK_CLASS[risk]
    present = _present_severities(findings)

    # ── Resumen ejecutivo: tabla de conteos ──
    count_rows = []
    for sev in _SEV_ORDER:  # orden fijo critical→info
        cvss = _SEV_CVSS[sev]
        count_rows.append(
            f"<tr><td><span class='sev {_SEV_BADGE_CLASS[sev]}'>{_SEV_LABEL[sev]}</span></td>"
            f"<td>{counts[sev]}</td><td>{cvss:.1f}</td></tr>"
        )
    counts_table = "\n".join(count_rows)

    # ── Top 3 acciones recomendadas (según severidad máxima) ──
    top_actions = _TOP_ACTIONS[risk]
    top_actions_html = "\n".join(
        f"<li>{html.escape(action)}</li>" for action in top_actions
    )

    # ── Tabla de hallazgos ──
    if sorted_findings:
        finding_rows = []
        for idx, f in enumerate(sorted_findings, start=1):
            sev = _normalize_severity(f.get("severity"))
            cvss = _SEV_CVSS[sev]
            title = html.escape(f.get("title") or "—")
            category = html.escape(f.get("category") or "—")
            detail = html.escape(_truncate(f.get("detail") or "", 200))
            badge = (
                f"<span class='sev {_SEV_BADGE_CLASS[sev]}'>{_SEV_LABEL[sev]}</span>"
            )
            finding_rows.append(
                f"<tr><td>{idx}</td><td>{title}</td><td>{badge}</td>"
                f"<td>{cvss:.1f}</td><td>{category}</td><td>{detail}</td></tr>"
            )
        findings_table = (
            "<table><thead><tr>"
            "<th>#</th><th>Título</th><th>Severidad</th><th>CVSS</th>"
            "<th>Categoría</th><th>Detalle</th>"
            "</tr></thead><tbody>\n" + "\n".join(finding_rows) + "\n</tbody></table>"
        )
    else:
        findings_table = "<p>No se registraron hallazgos para este escaneo.</p>"

    # ── Recomendaciones (solo niveles presentes) ──
    if present:
        rec_items = []
        for sev in present:
            rec_items.append(
                f"<h2><span class='sev {_SEV_BADGE_CLASS[sev]}'>{_SEV_LABEL[sev]}</span></h2>"
                f"<p>{html.escape(_RECOMMENDATION[sev])}</p>"
            )
        recommendations_html = "\n".join(rec_items)
    else:
        recommendations_html = "<p>Sin hallazgos que requieran recomendaciones.</p>"

    # ── Alcance y descargo de responsabilidad ──
    disclaimer_text = (
        f"Este informe representa el estado de seguridad del sistema evaluado en el "
        f"momento del análisis ({html.escape(str(scan_date))}). Los resultados son "
        f"válidos únicamente para el alcance definido: {safe_target}. No constituye "
        f"una garantía de seguridad total del sistema. Fr4meLuc es una herramienta "
        f"de apoyo para auditorías autorizadas."
    )

    # ── Anexos ──
    annexes_html = _annex_html(scan.get("workspace_dir") or "")

    bottom_center = "CONFIDENCIAL — NO DISTRIBUIR"
    if footer:
        bottom_center += f"  |  {footer}"

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  @page {{
    size: A4;
    margin: 2cm 2cm 3cm 2cm;
    @bottom-center {{
      content: "{bottom_center}";
      font-size: 8pt;
      color: #666;
    }}
    @bottom-right {{
      content: counter(page) " / " counter(pages);
      font-size: 8pt;
      color: #999;
    }}
  }}
  body {{ font-family: sans-serif; font-size: 10pt; color: #1a1a1a; margin: 0; }}

  .cover {{ page-break-after: always; min-height: 25cm; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; }}
  .cover-logo {{ max-width: 180px; max-height: 80px; margin-bottom: 40px; }}
  .cover-company {{ font-size: 14pt; color: #555; margin-bottom: 8px; }}
  .cover-title {{ font-size: 28pt; font-weight: bold; color: #1a1a2e; margin-bottom: 8px; }}
  .cover-subtitle {{ font-size: 12pt; color: #555; margin-bottom: 40px; }}
  .cover-meta {{ font-size: 10pt; color: #333; line-height: 2; }}
  .cover-confidential {{ margin-top: 40px; padding: 8px 24px; border: 2px solid #e53e3e; color: #e53e3e; font-weight: bold; font-size: 11pt; display: inline-block; }}

  .risk-badge {{ display: inline-block; padding: 12px 32px; border-radius: 4px; font-size: 18pt; font-weight: bold; color: white; margin: 20px 0; }}
  .risk-critical {{ background-color: #7c3aed; }}
  .risk-high {{ background-color: #dc2626; }}
  .risk-medium {{ background-color: #d97706; }}
  .risk-low {{ background-color: #2563eb; }}
  .risk-info {{ background-color: #6b7280; }}

  h1 {{ font-size: 18pt; color: #1a1a2e; border-bottom: 2px solid #1a1a2e; padding-bottom: 6px; margin-top: 30px; }}
  h2 {{ font-size: 13pt; color: #2d3748; margin-top: 20px; }}

  table {{ width: 100%; border-collapse: collapse; margin-top: 12px; font-size: 9pt; }}
  th {{ background-color: #1a1a2e; color: white; padding: 8px 6px; text-align: left; }}
  td {{ padding: 7px 6px; border-bottom: 1px solid #e2e8f0; vertical-align: top; }}
  tr:nth-child(even) td {{ background-color: #f8f9fa; }}

  .sev {{ padding: 2px 8px; border-radius: 3px; font-weight: bold; font-size: 8pt; color: white; display: inline-block; }}
  .sev-critical {{ background-color: #7c3aed; }}
  .sev-high {{ background-color: #dc2626; }}
  .sev-medium {{ background-color: #d97706; }}
  .sev-low {{ background-color: #2563eb; }}
  .sev-info {{ background-color: #6b7280; }}

  pre {{ background: #f4f4f4; padding: 10px; font-size: 7pt; font-family: monospace; border-left: 3px solid #ccc; overflow-wrap: break-word; white-space: pre-wrap; }}

  .disclaimer {{ background: #fff8e1; border-left: 4px solid #f59e0b; padding: 10px 14px; font-size: 9pt; color: #555; margin: 16px 0; }}

  .page-break {{ page-break-before: always; }}
</style>
</head>
<body>
  <!-- COVER PAGE -->
  <div class="cover">
    {logo_html}
    <div class="cover-company">{company}</div>
    <div class="cover-title">INFORME DE AUDITORÍA DE SEGURIDAD</div>
    <div class="cover-subtitle">{subtitle}</div>
    <div class="cover-meta">
      Auditor: {auditor}<br>
      Email: {auditor_email}<br>
      Fecha: {html.escape(str(scan_date))}<br>
      Perfil: {html.escape(str(profile))}
    </div>
    <div class="cover-confidential">CONFIDENCIAL</div>
  </div>

  <!-- EXECUTIVE SUMMARY -->
  <div class="page-break">
    <h1>Resumen Ejecutivo</h1>
    <div class="risk-badge {risk_class}">RIESGO GLOBAL: {risk_label}</div>
    <h2>Distribución de Hallazgos</h2>
    <table>
      <thead><tr><th>Severidad</th><th>Cantidad</th><th>CVSS Aprox.</th></tr></thead>
      <tbody>
        {counts_table}
      </tbody>
    </table>
    <h2>Acciones Recomendadas Prioritarias</h2>
    <ol>
      {top_actions_html}
    </ol>
  </div>

  <!-- FINDINGS TABLE -->
  <h1>Hallazgos Detallados</h1>
  {findings_table}

  <!-- RECOMMENDATIONS -->
  <div class="page-break">
    <h1>Recomendaciones</h1>
    {recommendations_html}
  </div>

  <!-- SCOPE & DISCLAIMER -->
  <h1>Alcance y Descargo de Responsabilidad</h1>
  <div class="disclaimer">{disclaimer_text}</div>

  <!-- ANNEXES -->
  <div class="page-break">
    <h1>Anexos — Evidencias</h1>
    {annexes_html}
  </div>
</body>
</html>"""


# ─────────────────────────────────────────────────────────────
#  API pública
# ─────────────────────────────────────────────────────────────

def generate_pdf_report(scan_id: int, workspace_dir: str, target: str,
                        domain: str | None = None) -> str | None:
    """Genera un informe PDF profesional para `scan_id`.

    Devuelve la ruta al PDF generado, o None si WeasyPrint no está disponible
    o si ocurre un error durante la generación.
    """
    try:
        from weasyprint import HTML
    except ImportError:
        print("[ERROR] WeasyPrint no está instalado. Instálalo con: pip install weasyprint")
        return None

    try:
        scan = get_scan(scan_id)
        if scan is None:
            print(f"[ERROR] Scan ID {scan_id} no encontrado en la DB.")
            return None

        findings = get_scan_findings(scan_id)
        settings = _load_settings()
        report_html = _build_html(scan, findings, settings, target, domain)

        output_path = os.path.join(
            workspace_dir, f"Reporte_Pentest_{target.replace('.', '_')}.pdf"
        )
        HTML(string=report_html).write_pdf(output_path)
        return output_path
    except Exception as exc:
        print(f"[ERROR] Fallo al generar el PDF: {exc}")
        return None
