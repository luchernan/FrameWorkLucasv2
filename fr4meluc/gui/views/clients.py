"""Vista de Clientes y Proyectos con CRUD completo."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QSplitter,
    QDialog, QFormLayout, QLineEdit, QDialogButtonBox, QMessageBox,
    QFrame, QTextEdit,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

from ..theme import ACCENT, TEXT_MUTED, SUCCESS, WARNING, BG_CARD
from ...core.storage import (
    list_clients, list_projects,
    get_or_create_client, get_or_create_project,
)
from ...core.db import get_connection


class _ClientDialog(QDialog):
    def __init__(self, parent=None, data: dict = None):
        super().__init__(parent)
        self.setWindowTitle("Cliente" if not data else "Editar Cliente")
        self.setMinimumWidth(380)
        form = QFormLayout(self)
        self.name_edit    = QLineEdit(data.get("name", "") if data else "")
        self.contact_edit = QLineEdit(data.get("contact", "") if data else "")
        self.notes_edit   = QTextEdit(data.get("notes", "") if data else "")
        self.notes_edit.setMaximumHeight(80)
        form.addRow("Nombre *", self.name_edit)
        form.addRow("Contacto",  self.contact_edit)
        form.addRow("Notas",     self.notes_edit)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        form.addRow(btns)

    def get_data(self):
        return {
            "name":    self.name_edit.text().strip(),
            "contact": self.contact_edit.text().strip(),
            "notes":   self.notes_edit.toPlainText().strip(),
        }


class _ProjectDialog(QDialog):
    def __init__(self, parent=None, client_id: int = None):
        super().__init__(parent)
        self.setWindowTitle("Nuevo Proyecto")
        self.setMinimumWidth(380)
        self._client_id = client_id
        form = QFormLayout(self)
        self.name_edit  = QLineEdit()
        self.scope_edit = QTextEdit()
        self.scope_edit.setPlaceholderText("IPs, rangos, dominios…")
        self.scope_edit.setMaximumHeight(80)
        form.addRow("Nombre *", self.name_edit)
        form.addRow("Scope",    self.scope_edit)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        form.addRow(btns)

    def get_data(self):
        return {
            "client_id": self._client_id,
            "name":  self.name_edit.text().strip(),
            "scope": self.scope_edit.toPlainText().strip(),
        }


class ClientsView(QWidget):
    project_selected = pyqtSignal(int, str)   # project_id, project_name

    def __init__(self, parent=None):
        super().__init__(parent)
        self._selected_client_id = None
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(16)

        # Header
        hdr_row = QHBoxLayout()
        hdr = QLabel("Clientes y Proyectos")
        hdr.setObjectName("title")
        hdr_row.addWidget(hdr)
        hdr_row.addStretch()
        btn_add = QPushButton("+ Nuevo Cliente")
        btn_add.setObjectName("btn_primary")
        btn_add.clicked.connect(self._add_client)
        hdr_row.addWidget(btn_add)
        root.addLayout(hdr_row)

        # Splitter: lista clientes | lista proyectos
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ── Clientes ──
        client_frame = QFrame()
        client_frame.setObjectName("card")
        cl = QVBoxLayout(client_frame)
        cl.setContentsMargins(12, 12, 12, 12)
        cl.addWidget(QLabel("Clientes"))
        self._tbl_clients = QTableWidget(0, 2)
        self._tbl_clients.setHorizontalHeaderLabels(["Nombre", "Contacto"])
        self._tbl_clients.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._tbl_clients.verticalHeader().setVisible(False)
        self._tbl_clients.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._tbl_clients.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._tbl_clients.itemSelectionChanged.connect(self._on_client_selected)
        cl.addWidget(self._tbl_clients)

        btn_del_client = QPushButton("Eliminar cliente")
        btn_del_client.setObjectName("btn_danger")
        btn_del_client.clicked.connect(self._del_client)
        cl.addWidget(btn_del_client)
        splitter.addWidget(client_frame)

        # ── Proyectos ──
        proj_frame = QFrame()
        proj_frame.setObjectName("card")
        pl = QVBoxLayout(proj_frame)
        pl.setContentsMargins(12, 12, 12, 12)
        proj_hdr = QHBoxLayout()
        proj_hdr.addWidget(QLabel("Proyectos"))
        proj_hdr.addStretch()
        btn_add_proj = QPushButton("+ Proyecto")
        btn_add_proj.setObjectName("btn_primary")
        btn_add_proj.clicked.connect(self._add_project)
        proj_hdr.addWidget(btn_add_proj)
        pl.addLayout(proj_hdr)

        self._tbl_projects = QTableWidget(0, 3)
        self._tbl_projects.setHorizontalHeaderLabels(["Nombre", "Estado", "Scope"])
        self._tbl_projects.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._tbl_projects.verticalHeader().setVisible(False)
        self._tbl_projects.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._tbl_projects.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._tbl_projects.doubleClicked.connect(self._open_project)
        pl.addWidget(self._tbl_projects)

        info = QLabel("Doble clic en un proyecto para abrirlo")
        info.setStyleSheet(f"color: {TEXT_MUTED}; font-size:11px;")
        pl.addWidget(info)
        splitter.addWidget(proj_frame)

        splitter.setSizes([340, 560])
        root.addWidget(splitter)

    def refresh(self):
        # Clientes
        clients = list_clients()
        self._clients_data = {i: c for i, c in enumerate(clients)}
        self._tbl_clients.setRowCount(len(clients))
        for r, c in enumerate(clients):
            self._tbl_clients.setItem(r, 0, QTableWidgetItem(c["name"]))
            self._tbl_clients.setItem(r, 1, QTableWidgetItem(c.get("contact") or ""))
        self._load_projects()

    def _load_projects(self):
        projects = list_projects(self._selected_client_id)
        self._projects_data = {i: p for i, p in enumerate(projects)}
        self._tbl_projects.setRowCount(len(projects))
        STATUS_C = {"active": SUCCESS, "closed": TEXT_MUTED}
        for r, p in enumerate(projects):
            self._tbl_projects.setItem(r, 0, QTableWidgetItem(p["name"]))
            si = QTableWidgetItem(p.get("status", "active"))
            si.setForeground(QColor(STATUS_C.get(p.get("status", "active"), TEXT_MUTED)))
            self._tbl_projects.setItem(r, 1, si)
            self._tbl_projects.setItem(r, 2, QTableWidgetItem(p.get("scope") or ""))

    def _on_client_selected(self):
        rows = self._tbl_clients.selectedItems()
        if not rows:
            self._selected_client_id = None
        else:
            r = self._tbl_clients.currentRow()
            c = self._clients_data.get(r)
            self._selected_client_id = c["id"] if c else None
        self._load_projects()

    def _add_client(self):
        dlg = _ClientDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            d = dlg.get_data()
            if not d["name"]:
                QMessageBox.warning(self, "Error", "El nombre es obligatorio.")
                return
            get_or_create_client(d["name"], d["contact"], d["notes"])
            self.refresh()

    def _del_client(self):
        if not self._selected_client_id:
            return
        r = QMessageBox.question(self, "Confirmar", "¿Eliminar cliente y todos sus proyectos?")
        if r == QMessageBox.StandardButton.Yes:
            with get_connection() as conn:
                conn.execute("DELETE FROM clients WHERE id=?", (self._selected_client_id,))
            self._selected_client_id = None
            self.refresh()

    def _add_project(self):
        if not self._selected_client_id:
            QMessageBox.information(self, "Info", "Selecciona primero un cliente.")
            return
        dlg = _ProjectDialog(self, self._selected_client_id)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            d = dlg.get_data()
            if not d["name"]:
                QMessageBox.warning(self, "Error", "El nombre es obligatorio.")
                return
            get_or_create_project(d["client_id"], d["name"], d["scope"])
            self._load_projects()

    def _open_project(self):
        r = self._tbl_projects.currentRow()
        p = self._projects_data.get(r)
        if p:
            self.project_selected.emit(p["id"], p["name"])
