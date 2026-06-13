Estoy desarrollando Fr4meLuc Enterprise v3.0, un framework de pentesting empresarial en Python con GUI PyQt6 y CLI. El código está en el repositorio local (necesito clonarlo o copiarlo desde Windows a Kali).
## Estado actual del proyecto
Todo el código está desarrollado en Windows. La estructura es:
fr4meluc/
├── core/ → lógica pura (ui, runner, workspace, parsers, db, storage, network, validation)
│ └── tools/ → 1 wrapper por herramienta: nmap, gobuster, ffuf, nuclei, nikto, wpscan, sqlmap, hydra, enum4linux, searchsploit, john, peas, http_server, netcat, arp_scan
├── cli/main.py → CLI interactivo completo con persistencia SQLite
├── gui/ → GUI PyQt6 enterprise con 6 vistas
│ └── views/ → dashboard, clients, scan_wizard, history, scheduler, settings
├── motor.py → shim legacy (sigue funcionando igual que antes)
└── pyproject.toml → entry points: fr4meluc (CLI) y fr4meluc-gui (GUI)

## Lo que YA está hecho
- Fase 0: Refactor completo — motor.py de 1700 líneas troceado en módulos
- Fase 1: Persistencia SQLite — clientes, proyectos, escaneos, findings, diff entre escaneos
- Fase 2: GUI PyQt6 — dark theme, dashboard con KPIs, CRUD clientes/proyectos, wizard de escaneo con perfiles (Quick/Web Full/AD/Personalizado), multi-target con CSV, live output terminal, histórico + diff visual, scheduler con cron, settings (Slack/Teams/Jira/webhook/reporte corporativo)
## Lo que falta hacer (en Linux)
### Fase 3 — Automatización empresarial completa
- Multi-target paralelo real con `concurrent.futures` (workers configurables)
- Motor de pipelines condicionales: si nmap encuentra puerto 80 → lanzar gobuster+nuclei; si detecta WordPress → wpscan; si TTL=128 y puerto 445 → enum4linux
- APScheduler daemon (`fr4meluc --daemon`) que ejecuta los jobs del scheduler en background
- Notificaciones al terminar escaneo: Slack webhook, Teams webhook, Jira ticket para CRITICAL/HIGH
### Fase 4 — Reportes profesionales
- PDF con WeasyPrint: portada corporativa (logo cliente + auditor), índice, resumen ejecutivo, tabla hallazgos con CVSS, recomendaciones, anexos con logs
- DOCX con python-docx: misma estructura, editable
- Usar datos de fr4meluc_settings.json (company_name, logo, auditor_name, etc.)
### Fase 5 — Integraciones activas (ya tienen UI, falta el backend)
- `core/integrations/slack.py` — POST al webhook con resumen del escaneo
- `core/integrations/teams.py` — card adaptativa MS Teams
- `core/integrations/jira.py` — crear issue via REST API para cada finding CRITICAL/HIGH
- `core/integrations/webhook.py` — POST JSON genérico
- Llamar a las integraciones al finalizar `finish_scan()` si están habilitadas en settings
### Fase 6 — Hardening y empaquetado
- `pytest` tests para: parsers, storage/diff, pipeline engine, run_cmd mock
- `.deb` package con `fpm` o `stdeb`
- `fr4meluc --daemon` mode con systemd unit file
- Logging estructurado JSON con rotación (logging.handlers.RotatingFileHandler)
- Instalar y verificar todas las herramientas: nmap, gobuster, ffuf, nuclei, nikto, wpscan, hydra, sqlmap, enum4linux, searchsploit, john, arp-scan
## Setup en Kali
```bash
# 1. Copiar el proyecto a Kali (desde Windows vía scp, USB o git)
cd ~/tools/Fr4meLuc
# 2. Crear entorno virtual
python3 -m venv venv
source venv/bin/activate
# 3. Instalar dependencias
pip install -e ".[gui]"
pip install apscheduler weasyprint python-docx requests pytest
# 4. Instalar herramientas del sistema
sudo apt install -y nmap gobuster nikto ffuf wpscan hydra sqlmap enum4linux exploitdb netcat-traditional arp-scan john nuclei
# 5. Verificar que todo funciona
python -c "from fr4meluc.core.db import init_db; init_db(); print('DB OK')"
sudo python -m fr4meluc.cli.main   # CLI clásico
python -m fr4meluc.gui.app         # GUI (requiere display X11)
Decisiones técnicas importantes
Python base en todo: no bash, no scripts externos
CLI DEBE seguir funcionando idéntico (motor.py como shim)
Modo educativo: toggle --quiet en CLI, checkbox en GUI Settings
DB SQLite local: fr4meluc.db en el directorio de trabajo
Settings en fr4meluc_settings.json en el directorio de trabajo
Objetivo final: .deb instalable en Kali, comando fr4meluc y fr4meluc-gui disponibles globalmente
Empieza por la Fase 3 (automatización). Primero muéstrame el planning de lo que vas a implementar y confirma conmigo antes de escribir código.
