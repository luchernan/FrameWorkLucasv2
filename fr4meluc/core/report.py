"""Generador de informe HTML maestro (Dashboard).

Versión 3.0 conserva el HTML actual. En Fase 4 se modernizará con plantilla Jinja2
y exporters DOCX/PDF reutilizando los parsers.
"""
import os
import sys
import subprocess
from datetime import datetime
from colorama import Fore, Style

from .parsers import parse_nmap, parse_nuclei, parse_ffuf


def generate_html_report(ip, domain, workspace_dir):
    """Genera un reporte HTML profesional, dinámico y estructurado, estilo Dashboard."""
    print(f"\n{Fore.BLUE}[*] Generando Reporte HTML Profesional de Auditoría (Dashboard)...{Style.RESET_ALL}")

    nmap_data = parse_nmap(os.path.join(workspace_dir, "nmap", "nmap.xml"))
    nuclei_vulns = parse_nuclei(workspace_dir)
    ffuf_results = parse_ffuf(workspace_dir, domain)

    html_file = os.path.join(workspace_dir, f"Reporte_Pentest_{ip.replace('.', '_')}.html")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    target_display = ip if domain is None else f"{ip} ({domain})"

    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Informe de Auditoría de Seguridad Pro - {now}</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-body: #0f111a;
            --primary: #00ff88;
            --secondary: #1a1e29;
            --accent: #f59e0b;
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
            --text-main: #e2e8f0;
            --text-muted: #94a3b8;
        }}
        body {{ font-family: 'Outfit', sans-serif; background-color: var(--bg-body); color: var(--text-main); margin: 0; padding: 0; display: flex; }}
        .sidebar {{ width: 250px; height: 100vh; background-color: var(--secondary); color: white; position: fixed; padding: 24px; box-sizing: border-box; border-right: 1px solid rgba(255,255,255,0.05); }}
        .main-content {{ margin-left: 250px; padding: 40px; width: 100%; max-width: 1200px; box-sizing: border-box; }}
        .header {{ background: linear-gradient(135deg, #1e2433, #11141e); color: white; padding: 40px; border-radius: 16px; margin-bottom: 40px; box-shadow: 0 10px 25px rgba(0, 255, 136, 0.1); position: relative; border: 1px solid rgba(0,255,136,0.2); }}
        .header h1 {{ margin: 0; font-size: 2.2rem; font-weight: 700; color: #fff; text-transform: uppercase; }}
        .header p {{ opacity: 0.9; font-size: 1rem; margin-top: 8px; color: var(--text-muted); }}
        .card {{ background: var(--secondary); border-radius: 12px; padding: 24px; margin-bottom: 32px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.5); border: 1px solid rgba(255,255,255,0.05); }}
        .section-title {{ display: flex; align-items: center; gap: 12px; border-bottom: 1px solid rgba(255,255,255,0.1); margin-bottom: 24px; padding-bottom: 12px; }}
        .section-title h2 {{ margin: 0; font-size: 1.3rem; color: #fff; font-weight: 600; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 8px; }}
        th, td {{ padding: 14px; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.05); }}
        th {{ background-color: rgba(0,0,0,0.2); font-weight: 600; text-transform: uppercase; font-size: 0.75rem; letter-spacing: 0.05em; color: var(--text-muted); }}
        .badge {{ padding: 6px 12px; border-radius: 9999px; font-size: 0.75rem; font-weight: 600; display: inline-block; }}
        .badge-info {{ background-color: rgba(59, 130, 246, 0.2); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.3); }}
        .badge-success {{ background-color: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); }}
        .badge-warning {{ background-color: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); }}
        .badge-danger {{ background-color: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); }}
        .severity-critical {{ border-left: 4px solid #7c3aed; }}
        .severity-high {{ border-left: 4px solid #ef4444; }}
        .severity-medium {{ border-left: 4px solid #f59e0b; }}
        .severity-low {{ border-left: 4px solid #3b82f6; }}
        .footer {{ text-align: center; color: var(--text-muted); padding: 40px; font-size: 0.85rem; border-top: 1px solid rgba(255,255,255,0.05); margin-top: 40px; }}
        .stats-row {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 40px; }}
        .stat-card {{ background: var(--secondary); border-radius: 12px; padding: 20px; text-align: center; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.5); border: 1px solid rgba(255,255,255,0.05); }}
        .stat-val {{ font-size: 2rem; font-weight: 700; color: var(--primary); }}
        .stat-label {{ font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin-top:5px; }}
        pre {{ font-family: monospace; background: #0b0d14; padding: 15px; border-radius: 8px; color: #a9b7c6; overflow-x: auto; border: 1px solid rgba(255,255,255,0.05); font-size: 0.85rem; }}
        code.inline {{ background: rgba(255,255,255,0.1); padding: 2px 6px; border-radius: 4px; font-family: monospace; color: #e2e8f0; }}
    </style>
</head>
<body>
    <div class="sidebar">
        <h3 style="color:var(--primary); margin-top:0;">Educational Pentest</h3>
        <p style="font-size: 0.8rem; color:var(--text-muted);">Framework Reporting</p>
        <hr style="border: 0; border-top: 1px solid rgba(255,255,255,0.1); margin: 20px 0;">
        <nav><p style="font-size: 0.9rem; color:#fff;"><strong>Target:</strong><br>{target_display}</p></nav>
    </div>

    <div class="main-content">
        <div class="header">
            <h1>Reporte de Fr4meLuc</h1>
            <p>Resumen analítico de reconocimiento y vulnerabilidades</p>
            <span style="position: absolute; top: 40px; right: 40px; background: rgba(0,255,136,0.1); color: var(--primary); padding: 8px 16px; border-radius: 8px; font-weight:600; font-size:0.85rem; border:1px solid rgba(0,255,136,0.2);">{now}</span>
        </div>

        <div class="stats-row">
            <div class="stat-card"><div class="stat-val">{len(nmap_data)}</div><div class="stat-label">Puertos Abiertos</div></div>
            <div class="stat-card"><div class="stat-val">{len(nuclei_vulns)}</div><div class="stat-label">Hallazgos Nuclei</div></div>
            <div class="stat-card"><div class="stat-val">{len(ffuf_results)}</div><div class="stat-label">Subdominios / Rutas</div></div>
            <div class="stat-card"><div class="stat-val">Evd.</div><div class="stat-label">Logs Maestros</div></div>
        </div>

        <div class="card">
            <div class="section-title"><h2>Reconocimiento de Puertos (Nmap)</h2></div>
            """

    if nmap_data:
        html_content += "<table><thead><tr><th>Puerto / Proto</th><th>Estado</th><th>Servicio</th><th>Versión Detectada</th></tr></thead><tbody>"
        for port in nmap_data:
            html_content += f"<tr><td><strong>{port['port']}/{port['protocol']}</strong></td><td><span class=\"badge badge-success\">{port['state']}</span></td><td>{port['service']}</td><td><code class=\"inline\">{port['version'] if port['version'] else 'N/D'}</code></td></tr>"
        html_content += "</tbody></table>"
    else:
        html_content += "<p style='color:var(--text-muted);'>No se encontraron puertos abiertos o no se corrió Nmap.</p>"

    html_content += '</div><div class="card"><div class="section-title"><h2>Vulnerabilidades (Nuclei)</h2></div>'

    if nuclei_vulns:
        html_content += "<table><thead><tr><th>Falla Detectada</th><th>Gravedad</th><th>Tipo</th><th>Evidencia Macheada</th></tr></thead><tbody>"
        for v in nuclei_vulns:
            sev_class = f"severity-{v['severity'].lower()}"
            badge_class = f"badge-{'danger' if v['severity'].lower() in ['critical', 'high'] else 'warning' if v['severity'].lower() == 'medium' else 'info'}"
            html_content += f'<tr class="{sev_class}"><td><strong>{v["name"]}</strong></td><td><span class="badge {badge_class}">{v["severity"]}</span></td><td>{v["type"]}</td><td><span style="font-size:0.8rem; color:var(--text-muted);">{v["matched-at"]}</span></td></tr>'
        html_content += "</tbody></table>"
    else:
        html_content += "<p style='color:var(--text-muted);'>No se detectaron hallazgos automáticos con Nuclei.</p>"

    html_content += '</div><div class="card"><div class="section-title"><h2>Subdominios Descubiertos (FFuF)</h2></div>'

    if ffuf_results:
        html_content += "<table><thead><tr><th>Subdominio Encontrado</th><th>HTTP Status</th><th>URL Completa</th></tr></thead><tbody>"
        for r in ffuf_results:
            html_content += f'<tr><td><code class="inline">{r["input"]}</code></td><td><span class="badge badge-info">{r["status"]}</span></td><td><a href="{r["url"]}" target="_blank" style="color:var(--primary); text-decoration:none;">{r["url"]}</a></td></tr>'
        html_content += "</tbody></table>"
    else:
        html_content += "<p style='color:var(--text-muted);'>No se realizó fuzzing de subdominios o no hubo hallazgos válidos.</p>"

    html_content += '</div><div class="card"><div class="section-title"><h2>Volcado de Evidencia RAW (Otras Herramientas)</h2></div>'

    found_logs = False
    for root, _, files in os.walk(workspace_dir):
        for file in files:
            if file.endswith('.txt'):
                found_logs = True
                file_path = os.path.join(root, file)
                module_name = os.path.basename(root).upper()
                html_content += f'<h4 style="color:#fff; margin-top:20px; border-bottom:1px dashed rgba(255,255,255,0.1); padding-bottom:5px;">{module_name}: {file}</h4><pre>'
                try:
                    with open(file_path, 'r', encoding="utf-8", errors="replace") as f:
                        lines = f.readlines()
                        clean_lines = []
                        skip = False
                        for l in lines:
                            if l.startswith("=== Reporte generado por"):
                                skip = True
                            if skip and l.startswith("========================="):
                                skip = False
                                continue
                            if not skip:
                                clean_lines.append(l)
                        content = "".join(clean_lines).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                        html_content += content
                except Exception:
                    html_content += "Error leyendo el archivo."
                html_content += "</pre>"

    if not found_logs:
        html_content += "<p style='color:var(--text-muted);'>No hay evidencias extra recopiladas.</p>"

    html_content += f'</div><div class="footer"><p>&copy; {datetime.now().year} Educational Pentesting Framework. Propietario: {os.getlogin() if hasattr(os, "getlogin") else "Admin"}</p></div></div></body></html>'

    with open(html_file, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"{Fore.GREEN}[+] ¡Reporte HTML generado exitosamente!{Style.RESET_ALL}")
    print(f"{Fore.GREEN}[+] Guardado en: {html_file}{Style.RESET_ALL}")

    try:
        if sys.platform == 'win32':
            os.startfile(html_file)
        else:
            subprocess.run(['xdg-open', html_file], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass
