"""Vista de Scheduler: programar escaneos recurrentes con APScheduler."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QDialog, QFormLayout, QLineEdit, QComboBox, QDialogButtonBox,
    QCheckBox, QMessageBox,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor
import json, threading
from datetime import datetime

from ..theme import ACCENT, TEXT_MUTED, SUCCESS, WARNING, DANGER, BORDER
from ...core.db import get_connection, init_db


# ─────────────────────────────────────────────────────────────
#  Tabla de jobs en SQLite (schema extendido en runtime)
# ─────────────────────────────────────────────────────────────
def _ensure_jobs_table():
    with get_connection() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS scheduled_jobs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            targets     TEXT NOT NULL,
            tools       TEXT NOT NULL,
            cron        TEXT NOT NULL,
            profile     TEXT DEFAULT 'Quick Recon',
            project_id  INTEGER,
            enabled     INTEGER DEFAULT 1,
            last_run    TEXT,
            next_run    TEXT,
            status      TEXT DEFAULT 'pending'
        )""")


def _list_jobs() -> list:
    _ensure_jobs_table()
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM scheduled_jobs ORDER BY id DESC").fetchall()
    return [dict(r) for r in rows]


def _save_job(data: dict) -> int:
    _ensure_jobs_table()
    with get_connection() as conn:
        cur = conn.execute("""
            INSERT INTO scheduled_jobs (name, targets, tools, cron, profile, project_id, enabled)
            VALUES (:name, :targets, :tools, :cron, :profile, :project_id, :enabled)
        """, data)
        return cur.lastrowid


def _toggle_job(job_id: int, enabled: bool):
    with get_connection() as conn:
        conn.execute("UPDATE scheduled_jobs SET enabled=? WHERE id=?", (int(enabled), job_id))


def _delete_job(job_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM scheduled_jobs WHERE id=?", (job_id,))


# ─────────────────────────────────────────────────────────────
#  Dialog para crear un job
# ─────────────────────────────────────────────────────────────
CRON_PRESETS = {
    "Cada hora":          "0 * * * *",
    "Diario a las 3am":   "0 3 * * *",
    "Semanal (lunes 3am)":"0 3 * * 1",
    "Cada 15 min":        "*/15 * * * *",
    "Personalizado":      "",
}

ALL_TOOLS = ["nmap", "gobuster", "nuclei", "nikto", "wpscan", "sqlmap", "hydra", "enum4linux"]


class _JobDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nuevo Job Programado")
        self.setMinimumWidth(420)
        form = QFormLayout(self)
        form.setSpacing(10)

        self.name_edit    = QLineEdit()
        self.name_edit.setPlaceholderText("Ej: Auditoría semanal perimetro")
        self.targets_edit = QLineEdit()
        self.targets_edit.setPlaceholderText("192.168.1.1,192.168.1.2,empresa.htb")

        self.preset_combo = QComboBox()
        for label in CRON_PRESETS:
            self.preset_combo.addItem(label)
        self.preset_combo.currentTextChanged.connect(self._on_preset)

        self.cron_edit = QLineEdit()
        self.cron_edit.setPlaceholderText("Expresión cron: minuto hora día mes semana")

        # Herramientas
        tools_widget = QWidget()
        tl = QHBoxLayout(tools_widget)
        tl.setContentsMargins(0, 0, 0, 0)
        self._tool_checks: dict[str, QCheckBox] = {}
        for t in ALL_TOOLS:
            cb = QCheckBox(t)
            self._tool_checks[t] = cb
            tl.addWidget(cb)
        self._tool_checks["nmap"].setChecked(True)

        form.addRow("Nombre *",     self.name_edit)
        form.addRow("Targets *",    self.targets_edit)
        form.addRow("Frecuencia",   self.preset_combo)
        form.addRow("Cron expr *",  self.cron_edit)
        form.addRow("Herramientas", tools_widget)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        form.addRow(btns)

        self._on_preset(self.preset_combo.currentText())

    def _on_preset(self, name: str):
        val = CRON_PRESETS.get(name, "")
        self.cron_edit.setText(val)
        self.cron_edit.setReadOnly(name != "Personalizado")

    def get_data(self) -> dict:
        tools = [t for t, cb in self._tool_checks.items() if cb.isChecked()]
        return {
            "name":       self.name_edit.text().strip(),
            "targets":    self.targets_edit.text().strip(),
            "tools":      json.dumps(tools),
            "cron":       self.cron_edit.text().strip(),
            "profile":    "Personalizado",
            "project_id": None,
            "enabled":    1,
        }


# ─────────────────────────────────────────────────────────────
#  Vista principal Scheduler
# ─────────────────────────────────────────────────────────────
class SchedulerView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._jobs: list = []
        self._build_ui()

        # Refrescar la tabla cada 30 s para mostrar last_run actualizado
        self._timer = QTimer(self)
        self._timer.setInterval(30_000)
        self._timer.timeout.connect(self.refresh)
        self._timer.start()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(20)

        hdr_row = QHBoxLayout()
        hdr = QLabel("Scheduler")
        hdr.setObjectName("title")
        hdr_row.addWidget(hdr)
        hdr_row.addStretch()

        btn_add = QPushButton("+ Nuevo Job")
        btn_add.setObjectName("btn_primary")
        btn_add.clicked.connect(self._add_job)
        hdr_row.addWidget(btn_add)
        root.addLayout(hdr_row)

        sub = QLabel("Programa escaneos recurrentes. Los jobs se ejecutan en background cuando la app está abierta.")
        sub.setObjectName("subtitle")
        root.addWidget(sub)

        # Nota APScheduler
        note = QFrame()
        note.setObjectName("card")
        nl = QHBoxLayout(note)
        nl.setContentsMargins(16, 12, 16, 12)
        nl_lbl = QLabel(
            "ℹ  Para producción en Linux instala APScheduler:  "
            "<code>pip install apscheduler</code>  y activa el daemon con "
            "<code>fr4meluc --daemon</code>"
        )
        nl_lbl.setStyleSheet(f"color:{TEXT_MUTED}; font-size:12px;")
        nl_lbl.setTextFormat(Qt.TextFormat.RichText)
        nl.addWidget(nl_lbl)
        root.addWidget(note)

        # Tabla de jobs
        frame = QFrame()
        frame.setObjectName("card")
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(16, 16, 16, 16)

        tbl_hdr = QHBoxLayout()
        tbl_hdr.addWidget(QLabel("Jobs programados"))
        tbl_hdr.addStretch()
        btn_del = QPushButton("Eliminar seleccionado")
        btn_del.setObjectName("btn_danger")
        btn_del.clicked.connect(self._del_job)
        btn_toggle = QPushButton("Activar / Pausar")
        btn_toggle.clicked.connect(self._toggle_job)
        tbl_hdr.addWidget(btn_toggle)
        tbl_hdr.addWidget(btn_del)
        fl.addLayout(tbl_hdr)

        self._tbl = QTableWidget(0, 7)
        self._tbl.setHorizontalHeaderLabels(
            ["ID", "Nombre", "Targets", "Cron", "Estado", "Última ejecución", "Próxima"]
        )
        self._tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self._tbl.setColumnWidth(0, 45)
        self._tbl.verticalHeader().setVisible(False)
        self._tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._tbl.setAlternatingRowColors(True)
        self._tbl.setStyleSheet("alternate-background-color: #1d2236;")
        fl.addWidget(self._tbl)
        root.addWidget(frame)
        root.addStretch()

    def refresh(self):
        self._jobs = _list_jobs()
        self._tbl.setRowCount(len(self._jobs))
        for r, j in enumerate(self._jobs):
            enabled = bool(j.get("enabled", 1))
            status_txt = "Activo" if enabled else "Pausado"
            status_col = SUCCESS if enabled else TEXT_MUTED

            self._tbl.setItem(r, 0, QTableWidgetItem(str(j["id"])))
            self._tbl.setItem(r, 1, QTableWidgetItem(j["name"]))
            self._tbl.setItem(r, 2, QTableWidgetItem(j["targets"][:40]))
            self._tbl.setItem(r, 3, QTableWidgetItem(j["cron"]))
            si = QTableWidgetItem(status_txt)
            si.setForeground(QColor(status_col))
            self._tbl.setItem(r, 4, si)
            self._tbl.setItem(r, 5, QTableWidgetItem(j.get("last_run") or "—"))
            self._tbl.setItem(r, 6, QTableWidgetItem(j.get("next_run") or "—"))

    def _add_job(self):
        dlg = _JobDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            d = dlg.get_data()
            if not d["name"] or not d["targets"] or not d["cron"]:
                QMessageBox.warning(self, "Error", "Nombre, targets y expresión cron son obligatorios.")
                return
            _save_job(d)
            self.refresh()

    def _del_job(self):
        r = self._tbl.currentRow()
        if r < 0 or r >= len(self._jobs):
            return
        job = self._jobs[r]
        if QMessageBox.question(self, "Confirmar", f"¿Eliminar job '{job['name']}'?") == QMessageBox.StandardButton.Yes:
            _delete_job(job["id"])
            self.refresh()

    def _toggle_job(self):
        r = self._tbl.currentRow()
        if r < 0 or r >= len(self._jobs):
            return
        job = self._jobs[r]
        new_state = not bool(job.get("enabled", 1))
        _toggle_job(job["id"], new_state)
        self.refresh()
