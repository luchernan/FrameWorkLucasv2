"""Vista principal: Dashboard con KPIs y actividad reciente."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from ..widgets.stat_card import StatCard
from ..theme import ACCENT, ACCENT2, WARNING, DANGER, SUCCESS, TEXT_MUTED, BG_CARD, SEV_COLORS
from ...core.db import init_db, get_connection


def _fetch_stats() -> dict:
    init_db()
    with get_connection() as conn:
        clients  = conn.execute("SELECT COUNT(*) FROM clients").fetchone()[0]
        projects = conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
        scans    = conn.execute("SELECT COUNT(*) FROM scans").fetchone()[0]
        findings = conn.execute("SELECT COUNT(*) FROM findings WHERE status='open'").fetchone()[0]
        critical = conn.execute(
            "SELECT COUNT(*) FROM findings WHERE severity IN ('critical','high') AND status='open'"
        ).fetchone()[0]
    return dict(clients=clients, projects=projects, scans=scans,
                findings=findings, critical=critical)


def _fetch_recent_scans(limit: int = 8) -> list:
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT s.id, s.target, s.status, s.started_at, s.profile,
                   p.name AS project_name, c.name AS client_name
            FROM scans s
            LEFT JOIN projects p ON s.project_id = p.id
            LEFT JOIN clients c  ON p.client_id  = c.id
            ORDER BY s.started_at DESC LIMIT ?
        """, (limit,)).fetchall()
    return [dict(r) for r in rows]


def _fetch_recent_findings(limit: int = 10) -> list:
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT f.title, f.severity, f.category, f.created_at, s.target
            FROM findings f
            JOIN scans s ON f.scan_id = s.id
            ORDER BY f.created_at DESC LIMIT ?
        """, (limit,)).fetchall()
    return [dict(r) for r in rows]


class DashboardView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(24)

        # ── Cabecera ──────────────────────────────────────────
        hdr = QLabel("Dashboard")
        hdr.setObjectName("title")
        sub = QLabel("Resumen de auditorías y hallazgos activos")
        sub.setObjectName("subtitle")
        root.addWidget(hdr)
        root.addWidget(sub)

        # ── KPI cards ────────────────────────────────────────
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(16)
        self._card_clients  = StatCard("Clientes",  color=ACCENT2)
        self._card_projects = StatCard("Proyectos", color=ACCENT)
        self._card_scans    = StatCard("Escaneos",  color=SUCCESS)
        self._card_findings = StatCard("Hallazgos abiertos", color=WARNING)
        self._card_critical = StatCard("Críticos / Altos", color=DANGER)
        for c in (self._card_clients, self._card_projects, self._card_scans,
                  self._card_findings, self._card_critical):
            kpi_row.addWidget(c)
        root.addLayout(kpi_row)

        # ── Dos columnas: escaneos recientes + hallazgos recientes ──
        cols = QHBoxLayout()
        cols.setSpacing(20)
        cols.addWidget(self._build_scans_table(), stretch=3)
        cols.addWidget(self._build_findings_table(), stretch=4)
        root.addLayout(cols)
        root.addStretch()

    def _build_scans_table(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("card")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(16, 16, 16, 16)

        lbl = QLabel("Escaneos Recientes")
        lbl.setStyleSheet("font-size:14px; font-weight:bold;")
        lay.addWidget(lbl)

        self._tbl_scans = QTableWidget(0, 4)
        self._tbl_scans.setHorizontalHeaderLabels(["Target", "Cliente", "Estado", "Fecha"])
        self._tbl_scans.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._tbl_scans.verticalHeader().setVisible(False)
        self._tbl_scans.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._tbl_scans.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._tbl_scans.setAlternatingRowColors(True)
        self._tbl_scans.setStyleSheet("alternate-background-color: #1d2236;")
        lay.addWidget(self._tbl_scans)
        return frame

    def _build_findings_table(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("card")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(16, 16, 16, 16)

        lbl = QLabel("Hallazgos Recientes")
        lbl.setStyleSheet("font-size:14px; font-weight:bold;")
        lay.addWidget(lbl)

        self._tbl_findings = QTableWidget(0, 4)
        self._tbl_findings.setHorizontalHeaderLabels(["Hallazgo", "Severidad", "Categoría", "Target"])
        self._tbl_findings.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._tbl_findings.verticalHeader().setVisible(False)
        self._tbl_findings.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._tbl_findings.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._tbl_findings.setAlternatingRowColors(True)
        self._tbl_findings.setStyleSheet("alternate-background-color: #1d2236;")
        lay.addWidget(self._tbl_findings)
        return frame

    def refresh(self):
        """Recarga todos los datos desde la DB."""
        stats = _fetch_stats()
        self._card_clients.set_value(str(stats["clients"]))
        self._card_projects.set_value(str(stats["projects"]))
        self._card_scans.set_value(str(stats["scans"]))
        self._card_findings.set_value(str(stats["findings"]))
        self._card_critical.set_value(str(stats["critical"]))

        # Escaneos recientes
        scans = _fetch_recent_scans()
        self._tbl_scans.setRowCount(len(scans))
        STATUS_COLOR = {"completed": SUCCESS, "running": WARNING, "failed": DANGER}
        for r, s in enumerate(scans):
            self._tbl_scans.setItem(r, 0, QTableWidgetItem(s["target"]))
            self._tbl_scans.setItem(r, 1, QTableWidgetItem(s.get("client_name") or "—"))
            status_item = QTableWidgetItem(s["status"])
            sc = STATUS_COLOR.get(s["status"], TEXT_MUTED)
            status_item.setForeground(QColor(sc))
            self._tbl_scans.setItem(r, 2, status_item)
            date_str = (s["started_at"] or "")[:16]
            self._tbl_scans.setItem(r, 3, QTableWidgetItem(date_str))

        # Hallazgos recientes
        findings = _fetch_recent_findings()
        self._tbl_findings.setRowCount(len(findings))
        for r, f in enumerate(findings):
            self._tbl_findings.setItem(r, 0, QTableWidgetItem(f["title"]))
            sev_item = QTableWidgetItem(f["severity"].upper())
            sev_color = SEV_COLORS.get(f["severity"].lower(), TEXT_MUTED)
            sev_item.setForeground(QColor(sev_color))
            self._tbl_findings.setItem(r, 1, sev_item)
            self._tbl_findings.setItem(r, 2, QTableWidgetItem(f["category"]))
            self._tbl_findings.setItem(r, 3, QTableWidgetItem(f.get("target") or "—"))
