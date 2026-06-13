"""Ventana principal de Fr4meLuc Enterprise GUI."""
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QLabel, QStackedWidget, QFrame, QSizePolicy,
)
from PyQt6.QtCore import Qt, QSize, pyqtSlot
from PyQt6.QtGui import QFont, QIcon

from .theme import STYLESHEET, ACCENT, TEXT_MUTED, BG_CARD, BG_DARK, BORDER
from .views.dashboard  import DashboardView
from .views.clients    import ClientsView
from .views.scan_wizard import ScanWizardView
from .views.history    import HistoryView
from .views.scheduler  import SchedulerView
from .views.settings   import SettingsView
from ..core.db import init_db


NAV_ITEMS = [
    ("dashboard", "⊞  Dashboard",     0),
    ("clients",   "👥  Clientes",      1),
    ("scan",      "▶  Nuevo Escaneo", 2),
    ("history",   "📋  Histórico",     3),
    ("scheduler", "🕐  Scheduler",     4),
    ("settings",  "⚙  Configuración", 5),
]


class SidebarButton(QPushButton):
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setMinimumHeight(44)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        init_db()
        self.setWindowTitle("Fr4meLuc Enterprise v3.0")
        self.resize(1280, 800)
        self.setMinimumSize(1024, 680)
        self.setStyleSheet(STYLESHEET)
        self._build_ui()
        self._nav_to(0)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Sidebar ──────────────────────────────────────────
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(220)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(12, 20, 12, 20)
        sidebar_layout.setSpacing(4)

        # Logo / título
        logo_lbl = QLabel("Fr4meLuc")
        logo_lbl.setStyleSheet(f"color: {ACCENT}; font-size: 20px; font-weight: bold; padding: 8px 8px 4px 8px;")
        ver_lbl = QLabel("Enterprise v3.0")
        ver_lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px; padding: 0 8px 16px 8px;")
        sidebar_layout.addWidget(logo_lbl)
        sidebar_layout.addWidget(ver_lbl)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"border: 1px solid {BORDER}; margin: 0 0 8px 0;")
        sidebar_layout.addWidget(sep)

        # Botones de navegación
        self._nav_btns: dict[int, SidebarButton] = {}
        for key, label, idx in NAV_ITEMS:
            btn = SidebarButton(label)
            btn.clicked.connect(lambda checked, i=idx: self._nav_to(i))
            sidebar_layout.addWidget(btn)
            self._nav_btns[idx] = btn

        sidebar_layout.addStretch()

        # Pie de sidebar
        sidebar_layout.addWidget(QLabel(
            '<span style="color: #2a2f3e; font-size:10px;">Linux & Ethical Use Only</span>'
        ))

        layout.addWidget(sidebar)

        # ── Stack de vistas ──────────────────────────────────
        self._stack = QStackedWidget()

        self._dashboard = DashboardView()
        self._clients   = ClientsView()
        self._wizard    = ScanWizardView()
        self._history   = HistoryView()
        self._scheduler = SchedulerView()
        self._settings  = SettingsView()

        for view in (self._dashboard, self._clients, self._wizard,
                     self._history, self._scheduler, self._settings):
            self._stack.addWidget(view)

        layout.addWidget(self._stack)

        # ── Conexiones entre vistas ──────────────────────────
        # Desde Clientes → abrir proyecto en el wizard
        self._clients.project_selected.connect(self._on_project_selected)
        # Desde Wizard → escaneo completado → refrescar dashboard e historial
        self._wizard.scan_started.connect(self._on_scan_done)

    @pyqtSlot(int)
    def _nav_to(self, idx: int):
        self._stack.setCurrentIndex(idx)

        # Marcar botón activo
        for i, btn in self._nav_btns.items():
            btn.setChecked(i == idx)
            btn.setProperty("active", "true" if i == idx else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        # Refresh de datos al entrar a una vista
        view = self._stack.currentWidget()
        if hasattr(view, "refresh"):
            view.refresh()

    @pyqtSlot(int, str)
    def _on_project_selected(self, project_id: int, project_name: str):
        self._wizard.set_project(project_id, project_name)
        self._nav_to(2)  # Ir al wizard

    @pyqtSlot(int)
    def _on_scan_done(self, scan_id: int):
        self._dashboard.refresh()
        self._history.refresh()
