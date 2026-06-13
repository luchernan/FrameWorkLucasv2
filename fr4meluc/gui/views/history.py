"""Vista de Histórico de escaneos y Diff entre dos escaneos."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QSplitter, QComboBox, QTextEdit, QScrollArea,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from ..theme import (
    ACCENT, TEXT_MUTED, SUCCESS, WARNING, DANGER,
    BG_CARD, SEV_COLORS, BORDER,
)
from ...core.db import get_connection
from ...core.storage import diff_scans, get_scan_findings


def _fetch_all_scans() -> list:
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT s.id, s.target, s.status, s.started_at, s.profile,
                   p.name AS project_name, c.name AS client_name
            FROM scans s
            LEFT JOIN projects p ON s.project_id = p.id
            LEFT JOIN clients  c ON p.client_id  = c.id
            ORDER BY s.started_at DESC
        """).fetchall()
    return [dict(r) for r in rows]


class HistoryView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._scans: list = []
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(20)

        hdr = QLabel("Histórico y Diff de Escaneos")
        hdr.setObjectName("title")
        root.addWidget(hdr)

        sub = QLabel("Selecciona dos escaneos del mismo target/proyecto para comparar hallazgos.")
        sub.setObjectName("subtitle")
        root.addWidget(sub)

        splitter = QSplitter(Qt.Orientation.Vertical)

        # ── Tabla de escaneos ───────────────────────────────
        top_frame = QFrame()
        top_frame.setObjectName("card")
        tl = QVBoxLayout(top_frame)
        tl.setContentsMargins(16, 16, 16, 16)

        tbl_hdr = QHBoxLayout()
        tbl_hdr.addWidget(QLabel("Escaneos"))
        tbl_hdr.addStretch()
        btn_refresh = QPushButton("↺ Actualizar")
        btn_refresh.clicked.connect(self.refresh)
        tbl_hdr.addWidget(btn_refresh)
        tl.addLayout(tbl_hdr)

        self._tbl = QTableWidget(0, 6)
        self._tbl.setHorizontalHeaderLabels(["ID", "Target", "Cliente", "Proyecto", "Estado", "Fecha"])
        self._tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self._tbl.setColumnWidth(0, 55)
        self._tbl.verticalHeader().setVisible(False)
        self._tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._tbl.setAlternatingRowColors(True)
        self._tbl.setStyleSheet("alternate-background-color: #1d2236;")
        self._tbl.itemSelectionChanged.connect(self._on_selection)
        tl.addWidget(self._tbl)
        splitter.addWidget(top_frame)

        # ── Panel diff ──────────────────────────────────────
        bottom_frame = QFrame()
        bottom_frame.setObjectName("card")
        bl = QVBoxLayout(bottom_frame)
        bl.setContentsMargins(16, 16, 16, 16)
        bl.setSpacing(12)

        diff_hdr = QHBoxLayout()
        diff_hdr.addWidget(QLabel("Comparar escaneos:"))

        self._combo_a = QComboBox()
        self._combo_a.setMinimumWidth(200)
        diff_hdr.addWidget(QLabel("Base:"))
        diff_hdr.addWidget(self._combo_a)

        self._combo_b = QComboBox()
        self._combo_b.setMinimumWidth(200)
        diff_hdr.addWidget(QLabel("Nuevo:"))
        diff_hdr.addWidget(self._combo_b)

        btn_diff = QPushButton("Generar Diff")
        btn_diff.setObjectName("btn_primary")
        btn_diff.clicked.connect(self._run_diff)
        diff_hdr.addWidget(btn_diff)
        diff_hdr.addStretch()
        bl.addLayout(diff_hdr)

        self._diff_output = QTextEdit()
        self._diff_output.setObjectName("terminal")
        self._diff_output.setReadOnly(True)
        self._diff_output.setMinimumHeight(220)
        self._diff_output.setPlaceholderText("El resultado del diff aparecerá aquí…")
        bl.addWidget(self._diff_output)
        splitter.addWidget(bottom_frame)

        splitter.setSizes([350, 300])
        root.addWidget(splitter)

    def refresh(self):
        self._scans = _fetch_all_scans()
        self._tbl.setRowCount(len(self._scans))

        STATUS_C = {"completed": SUCCESS, "running": WARNING, "failed": DANGER,
                    "imported": ACCENT, "manual": TEXT_MUTED}

        self._combo_a.clear()
        self._combo_b.clear()

        for r, s in enumerate(self._scans):
            self._tbl.setItem(r, 0, QTableWidgetItem(str(s["id"])))
            self._tbl.setItem(r, 1, QTableWidgetItem(s["target"]))
            self._tbl.setItem(r, 2, QTableWidgetItem(s.get("client_name") or "—"))
            self._tbl.setItem(r, 3, QTableWidgetItem(s.get("project_name") or "—"))
            si = QTableWidgetItem(s["status"])
            si.setForeground(QColor(STATUS_C.get(s["status"], TEXT_MUTED)))
            self._tbl.setItem(r, 4, si)
            self._tbl.setItem(r, 5, QTableWidgetItem((s["started_at"] or "")[:16]))

            label = f"#{s['id']} — {s['target']} ({(s['started_at'] or '')[:10]})"
            self._combo_a.addItem(label, userData=s["id"])
            self._combo_b.addItem(label, userData=s["id"])

        # Seleccionar B = más reciente, A = segundo más reciente por defecto
        if self._combo_b.count() >= 2:
            self._combo_b.setCurrentIndex(0)
            self._combo_a.setCurrentIndex(1)

    def _on_selection(self):
        """Al seleccionar una fila, pre-cargar los combos de diff."""
        rows = self._tbl.selectedIndexes()
        if not rows:
            return
        r = self._tbl.currentRow()
        s = self._scans[r] if r < len(self._scans) else None
        if s:
            # buscar el índice en el combo
            for i in range(self._combo_b.count()):
                if self._combo_b.itemData(i) == s["id"]:
                    self._combo_b.setCurrentIndex(i)
                    break

    def _run_diff(self):
        id_a = self._combo_a.currentData()
        id_b = self._combo_b.currentData()
        if id_a is None or id_b is None:
            return
        if id_a == id_b:
            self._diff_output.setPlainText("Selecciona dos escaneos distintos.")
            return

        self._diff_output.clear()
        d = diff_scans(int(id_a), int(id_b))

        scan_a = d["scan_a"]
        scan_b = d["scan_b"]

        lines = []
        lines.append(f"═══ DIFF  #{id_a} ({scan_a['target'] if scan_a else '?'})  →  #{id_b} ({scan_b['target'] if scan_b else '?'}) ═══\n")

        if d["new"]:
            lines.append(f"✘  NUEVOS hallazgos ({len(d['new'])}) — aparecieron en #{id_b}:")
            for f in sorted(d["new"], key=lambda x: x["severity"]):
                lines.append(f"   [{f['severity'].upper():<8}]  {f['category']:<14}  {f['title']}")
            lines.append("")

        if d["resolved"]:
            lines.append(f"✔  RESUELTOS ({len(d['resolved'])}) — desaparecieron desde #{id_a}:")
            for f in sorted(d["resolved"], key=lambda x: x["severity"]):
                lines.append(f"   [{f['severity'].upper():<8}]  {f['category']:<14}  {f['title']}")
            lines.append("")

        if d["persisted"]:
            lines.append(f"⚠  PERSISTENTES ({len(d['persisted'])}) — presentes en ambos:")
            for f in sorted(d["persisted"], key=lambda x: x["severity"]):
                lines.append(f"   [{f['severity'].upper():<8}]  {f['category']:<14}  {f['title']}")
            lines.append("")

        if not d["new"] and not d["resolved"]:
            lines.append("✔  Sin diferencias — los hallazgos son idénticos en ambos escaneos.")

        self._diff_output.setPlainText("\n".join(lines))
