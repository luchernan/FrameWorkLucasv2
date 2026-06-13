"""Wizard de nuevo escaneo: target(s) → perfil → herramientas → lanzar."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QCheckBox, QFrame, QGridLayout,
    QTextEdit, QGroupBox, QSpinBox, QFileDialog, QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QObject
import subprocess, os, shutil, threading

from ..theme import ACCENT, TEXT_MUTED, WARNING, DANGER, SUCCESS
from ...core.db import init_db
from ...core.storage import create_scan, finish_scan, save_finding
from ...core.workspace import create_workspace


# ─────────────────────────────────────────────────────────────
#  Worker que ejecuta el escaneo en background
# ─────────────────────────────────────────────────────────────
class ScanWorker(QObject):
    output   = pyqtSignal(str)      # línea de output
    finished = pyqtSignal(int)      # scan_id al terminar

    def __init__(self, config: dict):
        super().__init__()
        self._cfg = config
        self._stop = False

    def run(self):
        cfg = self._cfg
        targets = cfg["targets"]
        tools   = cfg["tools"]
        profile = cfg["profile"]

        for target in targets:
            workspace_dir = create_workspace(target)
            if workspace_dir is None:
                self.output.emit(f"[ERR] No se pudo crear workspace para {target}")
                continue

            scan_id = create_scan(
                target, workspace_dir,
                project_id=cfg.get("project_id"),
                profile=profile,
            )
            self.output.emit(f"\n[+] Iniciando escaneo → {target}  (scan_id={scan_id})")
            self.output.emit(f"[+] Workspace: {workspace_dir}\n")

            if "nmap" in tools:
                self._run_tool(["nmap", "-p-", "--open", "-T4", "--min-rate", "5000", "-n", "-Pn", target],
                               f"NMAP fase1 [{target}]")
                # Fase 2 si hay puertos (simplificado — en Linux real se parsea la fase1)
                self._run_tool(["nmap", "-p", "22,80,443", "-sC", "-sV", target],
                               f"NMAP fase2 [{target}]")
                self._persist_nmap(scan_id, workspace_dir)

            if "gobuster" in tools and shutil.which("gobuster"):
                wl = "/usr/share/wordlists/dirbuster/directory-list-lowercase-2.3-medium.txt"
                if os.path.exists(wl):
                    self._run_tool(["gobuster", "dir", "-u", f"http://{target}", "-w", wl, "--no-progress"],
                                   f"GOBUSTER [{target}]")

            if "nuclei" in tools and shutil.which("nuclei"):
                self._run_tool(["nuclei", "-u", f"http://{target}", "-jsonl", "-silent"],
                               f"NUCLEI [{target}]")
                self._persist_nuclei(scan_id, workspace_dir)

            if "nikto" in tools and shutil.which("nikto"):
                log = os.path.join(workspace_dir, "web", "nikto_resultados.txt")
                self._run_tool(["nikto", "-h", f"http://{target}", "-o", log, "-Format", "txt", "-nointeractive"],
                               f"NIKTO [{target}]")

            finish_scan(scan_id, status="completed")
            self.output.emit(f"\n[✔] Escaneo completado → {target}  (scan_id={scan_id})")
            self.finished.emit(scan_id)

    def _run_tool(self, cmd: list, label: str):
        if self._stop:
            return
        if not shutil.which(cmd[0]):
            self.output.emit(f"[SKIP] {cmd[0]} no está instalado (ejecuta en Linux)")
            return
        self.output.emit(f"\n── {label} ──")
        self.output.emit(f"▶  {' '.join(cmd)}\n")
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in proc.stdout:
                if self._stop:
                    proc.terminate()
                    break
                self.output.emit(line.rstrip())
            proc.wait()
        except FileNotFoundError:
            self.output.emit(f"[ERR] {cmd[0]} no encontrado")
        except Exception as e:
            self.output.emit(f"[ERR] {e}")

    def _persist_nmap(self, scan_id, workspace_dir):
        from ...core.parsers import parse_nmap
        nmap_xml = os.path.join(workspace_dir, "nmap", "nmap.xml")
        for p in parse_nmap(nmap_xml):
            if p["state"] == "open":
                save_finding(scan_id, "port",
                             f"{p['port']}/{p['protocol']} {p['service']}",
                             "info", p.get("version", ""))

    def _persist_nuclei(self, scan_id, workspace_dir):
        from ...core.parsers import parse_nuclei
        for v in parse_nuclei(workspace_dir):
            save_finding(scan_id, "nuclei",
                         v.get("name") or v.get("template-id", "?"),
                         v.get("severity", "info"),
                         v.get("matched-at", ""))

    def stop(self):
        self._stop = True


# ─────────────────────────────────────────────────────────────
#  Perfiles predefinidos
# ─────────────────────────────────────────────────────────────
PROFILES = {
    "Quick Recon":   {"tools": ["nmap"],                      "desc": "Solo Nmap. Rápido, sin ruido web."},
    "Web Full":      {"tools": ["nmap","gobuster","nuclei","nikto"], "desc": "Suite web completa."},
    "AD / Windows":  {"tools": ["nmap","enum4linux"],         "desc": "Orientado a Active Directory."},
    "Personalizado": {"tools": [],                            "desc": "Elige tú las herramientas."},
}

ALL_TOOLS = ["nmap", "gobuster", "ffuf", "nuclei", "nikto", "wpscan",
             "sqlmap", "hydra", "enum4linux", "searchsploit"]


class ScanWizardView(QWidget):
    scan_started = pyqtSignal(int)   # scan_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self._project_id: int | None = None
        self._worker: ScanWorker | None = None
        self._thread: QThread | None = None
        self._build_ui()

    def set_project(self, project_id: int, project_name: str):
        self._project_id = project_id
        self._lbl_project.setText(f"Proyecto: {project_name}")

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(20)

        hdr = QLabel("Nuevo Escaneo")
        hdr.setObjectName("title")
        root.addWidget(hdr)

        self._lbl_project = QLabel("Proyecto: (ninguno seleccionado)")
        self._lbl_project.setStyleSheet(f"color:{TEXT_MUTED};")
        root.addWidget(self._lbl_project)

        # ── Configuración ──────────────────────────────────────────
        cfg_frame = QFrame()
        cfg_frame.setObjectName("card")
        cfg = QGridLayout(cfg_frame)
        cfg.setContentsMargins(20, 16, 20, 16)
        cfg.setSpacing(12)

        cfg.addWidget(QLabel("Target(s)"), 0, 0)
        self._targets_edit = QLineEdit()
        self._targets_edit.setPlaceholderText("192.168.1.1  o  192.168.1.1,192.168.1.2  o cargar CSV →")
        cfg.addWidget(self._targets_edit, 0, 1, 1, 2)
        btn_csv = QPushButton("CSV…")
        btn_csv.setFixedWidth(60)
        btn_csv.clicked.connect(self._load_csv)
        cfg.addWidget(btn_csv, 0, 3)

        cfg.addWidget(QLabel("Perfil"), 1, 0)
        self._profile_combo = QComboBox()
        for name, p in PROFILES.items():
            self._profile_combo.addItem(name)
        self._profile_combo.currentTextChanged.connect(self._on_profile_changed)
        cfg.addWidget(self._profile_combo, 1, 1)

        cfg.addWidget(QLabel("Workers paralelos"), 1, 2)
        self._workers_spin = QSpinBox()
        self._workers_spin.setRange(1, 16)
        self._workers_spin.setValue(2)
        cfg.addWidget(self._workers_spin, 1, 3)

        root.addWidget(cfg_frame)

        # ── Herramientas ───────────────────────────────────────────
        tools_group = QGroupBox("Herramientas")
        tg = QHBoxLayout(tools_group)
        self._tool_checks: dict[str, QCheckBox] = {}
        for tool in ALL_TOOLS:
            cb = QCheckBox(tool)
            self._tool_checks[tool] = cb
            tg.addWidget(cb)
        tg.addStretch()
        root.addWidget(tools_group)

        # ── Botones de acción ──────────────────────────────────────
        btn_row = QHBoxLayout()
        self._btn_launch = QPushButton("▶  Lanzar Escaneo")
        self._btn_launch.setObjectName("btn_primary")
        self._btn_launch.setMinimumHeight(40)
        self._btn_launch.clicked.connect(self._launch)
        self._btn_stop = QPushButton("■  Detener")
        self._btn_stop.setObjectName("btn_danger")
        self._btn_stop.setMinimumHeight(40)
        self._btn_stop.setEnabled(False)
        self._btn_stop.clicked.connect(self._stop)
        btn_row.addWidget(self._btn_launch)
        btn_row.addWidget(self._btn_stop)
        root.addLayout(btn_row)

        # ── Terminal de output ─────────────────────────────────────
        self._output = QTextEdit()
        self._output.setObjectName("terminal")
        self._output.setReadOnly(True)
        self._output.setMinimumHeight(300)
        root.addWidget(self._output)

        # Aplicar perfil inicial
        self._on_profile_changed(self._profile_combo.currentText())

    def _on_profile_changed(self, name: str):
        profile = PROFILES.get(name, {})
        active_tools = profile.get("tools", [])
        is_custom = (name == "Personalizado")
        for tool, cb in self._tool_checks.items():
            cb.setChecked(tool in active_tools)
            cb.setEnabled(is_custom)

    def _load_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, "Cargar targets desde CSV", "", "CSV (*.csv *.txt)")
        if path:
            with open(path) as f:
                targets = [l.strip() for l in f if l.strip()]
            self._targets_edit.setText(",".join(targets))

    def _launch(self):
        raw = self._targets_edit.text().strip()
        if not raw:
            QMessageBox.warning(self, "Error", "Introduce al menos un target.")
            return

        targets = [t.strip() for t in raw.replace("\n", ",").split(",") if t.strip()]
        tools   = [t for t, cb in self._tool_checks.items() if cb.isChecked()]
        profile = self._profile_combo.currentText()

        self._output.clear()
        self._output.append(f"[Fr4meLuc] Lanzando {len(targets)} target(s) | Perfil: {profile} | Tools: {', '.join(tools) or 'ninguna'}\n")

        config = {
            "targets": targets,
            "tools": tools,
            "profile": profile,
            "project_id": self._project_id,
            "workers": self._workers_spin.value(),
        }

        self._worker = ScanWorker(config)
        self._thread = QThread()
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.output.connect(self._append_output)
        self._worker.finished.connect(self._on_finished)
        self._thread.start()

        self._btn_launch.setEnabled(False)
        self._btn_stop.setEnabled(True)

    def _stop(self):
        if self._worker:
            self._worker.stop()
        self._append_output("\n[!] Escaneo detenido por el usuario.")
        self._btn_launch.setEnabled(True)
        self._btn_stop.setEnabled(False)

    def _append_output(self, line: str):
        self._output.append(line)
        self._output.verticalScrollBar().setValue(
            self._output.verticalScrollBar().maximum()
        )

    def _on_finished(self, scan_id: int):
        self._btn_launch.setEnabled(True)
        self._btn_stop.setEnabled(False)
        if self._thread:
            self._thread.quit()
        self.scan_started.emit(scan_id)
