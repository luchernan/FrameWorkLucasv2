# Fr4meLuc Enterprise v3.0

![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python)
![Plataforma](https://img.shields.io/badge/Plataforma-Kali%20Linux-557C94?logo=linux)
![Licencia](https://img.shields.io/badge/Licencia-MIT-green)
![Tests](https://img.shields.io/badge/Tests-21%20passed-brightgreen)
![Estado](https://img.shields.io/badge/Estado-v3.0%20Enterprise-blue)

> **Framework de pentesting empresarial con CLI interactivo, GUI PyQt6, automatización por pipeline, reportes PDF/DOCX y daemon de scheduling.**  
> Diseñado para auditores profesionales, equipos de red team y entornos CTF autorizados.

```
   ███████╗██████╗ ██╗  ██╗███╗   ███╗███████╗██╗      ██╗   ██╗ ██████╗
   ██╔════╝██╔══██╗██║  ██║████╗ ████║██╔════╝██║      ██║   ██║██╔════╝
   █████╗  ██████╔╝███████║██╔████╔██║█████╗  ██║      ██║   ██║██║
   ██╔══╝  ██╔══██╗╚════██║██║╚██╔╝██║██╔══╝  ██║      ██║   ██║██║
   ██║     ██║  ██║     ██║██║ ╚═╝ ██║███████╗███████╗ ╚██████╔╝╚██████╗
   ╚═╝     ╚═╝  ╚═╝     ╚═╝╚═╝     ╚═╝╚══════╝╚══════╝  ╚═════╝  ╚═════╝
  ══════════════════  Fr4meLuc Enterprise  v3.0  |  Kali Linux  ══════════
```

---

## Instalación rápida

### Opción A — pip (recomendado para desarrollo)

```bash
git clone https://github.com/luchernan/FrameWorkLucasv2
cd FrameWorkLucasv2
pip install -e ".[gui]"
pip install weasyprint python-docx
```

### Opción B — paquete .deb (instalación global en Kali)

```bash
./build_deb.sh
sudo dpkg -i fr4meluc_3.0.0_all.deb
```

### Herramientas del sistema

```bash
sudo apt install -y nmap gobuster nikto ffuf wpscan hydra sqlmap \
  enum4linux exploitdb netcat-traditional arp-scan john nuclei
```

---

## Uso

```bash
# CLI interactivo (modo clásico)
sudo fr4meluc

# CLI silencioso — sin capa educativa
sudo fr4meluc --quiet

# Generar reporte PDF de un escaneo existente
fr4meluc --report-pdf <scan_id>

# Generar reporte DOCX
fr4meluc --report-docx <scan_id>

# Daemon de scheduling (APScheduler)
fr4meluc --daemon

# GUI empresarial (requiere display X11)
fr4meluc-gui

# Compatibilidad con versiones anteriores
sudo python3 motor.py
```

---

## Qué hay en v3.0

### Fase 0 — Refactor completo
`motor.py` (1700 líneas) troceado en módulos independientes. `motor.py` sigue funcionando como shim de compatibilidad.

```
fr4meluc/
├── core/           → lógica pura (runner, parsers, db, storage, pipeline, parallel, daemon)
│   ├── tools/      → 1 wrapper por herramienta (nmap, gobuster, ffuf, nuclei…)
│   └── integrations/ → Slack, Teams, Jira, webhook
├── cli/main.py     → CLI interactivo completo
└── gui/            → GUI PyQt6 enterprise (6 vistas)
    └── views/      → dashboard, clients, scan_wizard, history, scheduler, settings
```

### Fase 1 — Persistencia SQLite
Base de datos `fr4meluc.db` (creada en el directorio de trabajo):

| Tabla | Contenido |
|---|---|
| `clients` | Empresas / clientes auditados |
| `projects` | Campañas de auditoría |
| `scans` | Ejecuciones del framework |
| `findings` | Hallazgos individuales (puerto, CVE, directorio…) |
| `scheduler_jobs` | Jobs de scheduling con expresión cron |

### Fase 2 — GUI PyQt6 Enterprise
Dark theme profesional con 6 vistas:
- **Dashboard** — KPIs: escaneos activos, hallazgos totales, distribución por severidad
- **Clientes** — CRUD de clientes y proyectos
- **Scan Wizard** — asistente de escaneo con perfiles (Quick / Web Full / AD / Personalizado), multi-target con CSV, terminal live
- **Historial** — diff visual entre escaneos del mismo proyecto
- **Scheduler** — jobs cron con APScheduler
- **Settings** — Slack / Teams / Jira / webhook / datos corporativos para reportes

### Fase 3 — Automatización empresarial

#### Pipeline condicional (`core/pipeline.py`)
Motor data-driven: `RULES = [(condition_fn, action_fn, name), ...]`. Sin if/elif.

| Condición | Acción automática |
|---|---|
| Puerto 80/443 abierto **o** servicio HTTP (cualquier puerto) | gobuster dir + nuclei |
| Puerto 445 abierto | enum4linux |
| Servicio/versión contiene "wordpress" | wpscan |

```bash
# Añadir una regla nueva = añadir una tupla a RULES. El bucle no cambia.
```

#### Multi-target paralelo (`core/parallel.py`)
```python
from fr4meluc.core.parallel import run_parallel

scan_ids = run_parallel(
    targets=['10.0.0.1', '10.0.0.2', '10.0.0.3'],
    project_id=1,
    profile='auto',
    max_workers=4,   # ThreadPoolExecutor
)
```
Aislamiento por worker: un target fallido no aborta los demás.

#### Daemon APScheduler (`fr4meluc --daemon`)
Lee jobs de `scheduler_jobs` en la DB y los ejecuta según expresión cron. Logging estructurado JSON con rotación:
```json
{"ts":"2026-06-13T20:05:17.734Z","level":"INFO","msg":"Fr4meLuc daemon started. 2 jobs loaded."}
```
Unidad systemd incluida: `fr4meluc-daemon.service`.

#### Integraciones (`core/integrations/`)
Se disparan automáticamente al finalizar un escaneo si están configuradas en `fr4meluc_settings.json`:

| Integración | Activación |
|---|---|
| Slack | `slack_webhook` presente |
| Microsoft Teams | `teams_webhook` presente |
| Jira | `jira_url` + `jira_user` + `jira_token` + `jira_project` presentes |
| Webhook genérico | `webhook_url` presente |

Jira crea un issue por cada finding con severidad `critical` o `high`.

### Fase 4 — Reportes profesionales

Menú opciones 16/17/18 o flags CLI:

| Formato | Comando menú | Flag CLI |
|---|---|---|
| HTML (dashboard) | Opción 16 | — |
| **PDF** (WeasyPrint) | Opción 17 | `--report-pdf <scan_id>` |
| **DOCX** (python-docx) | Opción 18 | `--report-docx <scan_id>` |

Secciones en PDF y DOCX:
1. **Portada corporativa** — logo (base64), empresa, auditor, fecha, "CONFIDENCIAL"
2. **Resumen ejecutivo** — `RIESGO GLOBAL: CRÍTICO / ALTO / MEDIO / BAJO / INFO`
3. **Tabla de hallazgos** — ordenada critical→info, CVSS aproximado
4. **Recomendaciones** — guía de remediación por severidad (24h / 72h / 30d / 90d)
5. **Alcance y disclaimer** — punto-en-tiempo, sin garantía de seguridad total
6. **Anexos** — logs .txt del workspace

Configuración en `fr4meluc_settings.json`:
```json
{
  "company_name": "Acme Security S.L.",
  "company_logo": "/path/to/logo.png",
  "auditor_name": "John Doe",
  "auditor_email": "john@acme.com",
  "report_footer": "© 2026 Acme Security. Confidencial."
}
```

### Fase 6 — Hardening y empaquetado

```bash
# Tests unitarios (21 tests, ~0.16s)
pytest tests/ -v

# Construir .deb
./build_deb.sh
sudo dpkg -i fr4meluc_3.0.0_all.deb

# Daemon como servicio systemd
sudo cp fr4meluc-daemon.service /lib/systemd/system/
sudo systemctl enable fr4meluc-daemon
sudo systemctl start fr4meluc-daemon
sudo journalctl -u fr4meluc-daemon -f
```

---

## Workspace por objetivo

```
workspace_10_0_0_1/
├── nmap/
│   ├── nmap.xml                  ← parseado por pipeline + reportes
│   └── escaneo_principal.txt
├── web/
│   ├── gobuster_auto.txt         ← pipeline automático
│   ├── nuclei_auto.json          ← pipeline automático
│   ├── gobuster_directorios.txt  ← modo manual
│   ├── nuclei.json
│   ├── nikto_resultados.txt
│   ├── wpscan_auto.txt
│   └── ffuf_*.json
├── smb/
│   └── enum4linux_auto.txt       ← pipeline automático
├── exploits/
│   └── hydra_ssh_bruteforce.txt
├── payloads/
│   └── linpeas.sh
├── Reporte_Pentest_10_0_0_1.html
├── Reporte_Pentest_10_0_0_1.pdf  ← nuevo en v3.0
└── Reporte_Pentest_10_0_0_1.docx ← nuevo en v3.0
```

---

## Flujo de trabajo recomendado

```
Modo manual (CLI interactivo):
  1. ARP-Scan → descubrir IPs en la red
  2. Seleccionar objetivo → crea workspace + registro en DB
  3. Ping TTL → identificar SO
  4. Nmap 2 fases → puertos, servicios, dominio automático (/etc/hosts)
  5. Gobuster + Nuclei + Nikto → enumeración web
  6. FFuF → subdominios virtuales (requiere dominio)
  7. WPScan → si WordPress detectado
  8. SearchSploit → exploits por servicio
  9. Hydra → fuerza bruta SSH/FTP
  10. Opción 17/18 → PDF o DOCX entregable

Modo automático (pipeline + daemon):
  1. Configurar job en scheduler (GUI → Scheduler o INSERT en scheduler_jobs)
  2. fr4meluc --daemon
  3. [pipeline dispara gobuster+nuclei/enum4linux/wpscan según puertos]
  4. [integración envía Slack/Jira al terminar]
  5. fr4meluc --report-pdf <scan_id>
```

---

## Herramientas verificadas al arranque

`nmap` · `gobuster` · `nikto` · `ffuf` · `wpscan` · `hydra` · `sqlmap` · `enum4linux` · `searchsploit` · `arp-scan` · `ping` · `john` · `nuclei`

---

## Tests

```
tests/
├── test_parsers.py   → extract_domains, parse_nmap, parse_nuclei (7 tests)
├── test_storage.py   → CRUD, diff_scans, scheduler_jobs (6 tests, DB aislada)
└── test_pipeline.py  → condiciones + run_pipeline con run_cmd mockeado (8 tests)
```

```bash
pytest tests/ -v
# 21 passed in 0.16s
```

---

## Aviso legal

> ⚠️ **Herramienta diseñada EXCLUSIVAMENTE para uso en entornos autorizados:**  
> CTFs, máquinas virtuales propias, HackTheBox, TryHackMe, redes de laboratorio con permiso explícito.  
>  
> **Usar esta herramienta contra sistemas sin autorización escrita es ilegal.**  
> El autor no asume responsabilidad por uso indebido.

---

## Probado en

- Kali Linux 2024.x / 2025.x
- Metasploitable 2/3
- HackTheBox / TryHackMe
- DVWA en Docker

---

## Licencia

MIT — ver [LICENSE](LICENSE)
