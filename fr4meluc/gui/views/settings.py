"""Vista de Settings: integraciones, perfil corporativo, preferencias."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QFormLayout, QLineEdit, QCheckBox, QTabWidget,
    QGroupBox, QComboBox, QTextEdit, QFileDialog,
)
from PyQt6.QtCore import Qt
import json, os

from ..theme import ACCENT, TEXT_MUTED, SUCCESS, WARNING

SETTINGS_FILE = "fr4meluc_settings.json"


def load_settings() -> dict:
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_settings(data: dict):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(data, f, indent=2)


class SettingsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self._load()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(20)

        hdr_row = QHBoxLayout()
        hdr = QLabel("Configuración")
        hdr.setObjectName("title")
        hdr_row.addWidget(hdr)
        hdr_row.addStretch()
        btn_save = QPushButton("Guardar cambios")
        btn_save.setObjectName("btn_primary")
        btn_save.clicked.connect(self._save)
        hdr_row.addWidget(btn_save)
        root.addLayout(hdr_row)

        tabs = QTabWidget()

        # ── Tab 1: General ──────────────────────────────────
        general = QWidget()
        gf = QFormLayout(general)
        gf.setSpacing(12)
        gf.setContentsMargins(20, 16, 20, 16)

        self.edu_check   = QCheckBox("Activar textos educativos en CLI")
        self.edu_check.setChecked(True)
        self.quiet_check = QCheckBox("Modo silencioso por defecto (--quiet)")
        self.dark_check  = QCheckBox("Tema oscuro (requiere reinicio)")
        self.dark_check.setChecked(True)
        gf.addRow("Interfaz:", self.edu_check)
        gf.addRow("",          self.quiet_check)
        gf.addRow("",          self.dark_check)

        self.wordlist_edit = QLineEdit()
        self.wordlist_edit.setPlaceholderText("/usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt")
        btn_wl = QPushButton("…")
        btn_wl.setFixedWidth(36)
        btn_wl.clicked.connect(lambda: self._pick_file(self.wordlist_edit))
        wl_row = QHBoxLayout()
        wl_row.addWidget(self.wordlist_edit)
        wl_row.addWidget(btn_wl)
        wl_widget = QWidget()
        wl_widget.setLayout(wl_row)
        gf.addRow("Wordlist por defecto:", wl_widget)

        self.workers_edit = QLineEdit("2")
        gf.addRow("Workers paralelos:", self.workers_edit)

        tabs.addTab(general, "General")

        # ── Tab 2: Integraciones ────────────────────────────
        integrations = QWidget()
        il = QVBoxLayout(integrations)
        il.setContentsMargins(20, 16, 20, 16)
        il.setSpacing(16)

        # Slack
        slack_grp = QGroupBox("Slack")
        sf = QFormLayout(slack_grp)
        self.slack_webhook = QLineEdit()
        self.slack_webhook.setPlaceholderText("https://hooks.slack.com/services/…")
        self.slack_enabled = QCheckBox("Activar notificaciones Slack")
        sf.addRow("Webhook URL:", self.slack_webhook)
        sf.addRow("",             self.slack_enabled)
        il.addWidget(slack_grp)

        # Teams
        teams_grp = QGroupBox("Microsoft Teams")
        tf = QFormLayout(teams_grp)
        self.teams_webhook = QLineEdit()
        self.teams_webhook.setPlaceholderText("https://outlook.office.com/webhook/…")
        self.teams_enabled = QCheckBox("Activar notificaciones Teams")
        tf.addRow("Webhook URL:", self.teams_webhook)
        tf.addRow("",             self.teams_enabled)
        il.addWidget(teams_grp)

        # Jira
        jira_grp = QGroupBox("Jira")
        jf = QFormLayout(jira_grp)
        self.jira_url     = QLineEdit()
        self.jira_url.setPlaceholderText("https://empresa.atlassian.net")
        self.jira_token   = QLineEdit()
        self.jira_token.setEchoMode(QLineEdit.EchoMode.Password)
        self.jira_project = QLineEdit()
        self.jira_project.setPlaceholderText("SEC")
        self.jira_enabled = QCheckBox("Crear ticket en Jira para hallazgos CRITICAL/HIGH")
        jf.addRow("URL Jira:",        self.jira_url)
        jf.addRow("API Token:",       self.jira_token)
        jf.addRow("Project Key:",     self.jira_project)
        jf.addRow("",                 self.jira_enabled)
        il.addWidget(jira_grp)

        # Webhook genérico
        wh_grp = QGroupBox("Webhook genérico")
        wf = QFormLayout(wh_grp)
        self.webhook_url     = QLineEdit()
        self.webhook_url.setPlaceholderText("https://tuservidor.com/api/findings")
        self.webhook_enabled = QCheckBox("Enviar hallazgos via POST JSON")
        wf.addRow("URL:", self.webhook_url)
        wf.addRow("",     self.webhook_enabled)
        il.addWidget(wh_grp)
        il.addStretch()

        tabs.addTab(integrations, "Integraciones")

        # ── Tab 3: Reporte corporativo ──────────────────────
        report_tab = QWidget()
        rf = QFormLayout(report_tab)
        rf.setSpacing(12)
        rf.setContentsMargins(20, 16, 20, 16)

        self.company_name  = QLineEdit()
        self.company_name.setPlaceholderText("Acme Security S.L.")
        self.company_logo  = QLineEdit()
        btn_logo = QPushButton("…")
        btn_logo.setFixedWidth(36)
        btn_logo.clicked.connect(lambda: self._pick_file(self.company_logo, images=True))
        logo_row = QHBoxLayout()
        logo_row.addWidget(self.company_logo)
        logo_row.addWidget(btn_logo)
        logo_widget = QWidget()
        logo_widget.setLayout(logo_row)

        self.auditor_name  = QLineEdit()
        self.auditor_email = QLineEdit()
        self.report_footer = QLineEdit()
        self.report_footer.setPlaceholderText("© 2026 Acme Security. Confidencial.")

        rf.addRow("Empresa:",        self.company_name)
        rf.addRow("Logo (PNG/JPG):", logo_widget)
        rf.addRow("Auditor:",        self.auditor_name)
        rf.addRow("Email:",          self.auditor_email)
        rf.addRow("Pie de página:",  self.report_footer)

        tabs.addTab(report_tab, "Reporte Corporativo")

        root.addWidget(tabs)
        root.addStretch()

    def _pick_file(self, target: QLineEdit, images: bool = False):
        filt = "Imágenes (*.png *.jpg *.jpeg *.svg)" if images else "Todos (*)"
        path, _ = QFileDialog.getOpenFileName(self, "Seleccionar archivo", "", filt)
        if path:
            target.setText(path)

    def _load(self):
        s = load_settings()
        self.edu_check.setChecked(s.get("edu_mode", True))
        self.quiet_check.setChecked(s.get("quiet", False))
        self.dark_check.setChecked(s.get("dark_theme", True))
        self.wordlist_edit.setText(s.get("wordlist", ""))
        self.workers_edit.setText(str(s.get("workers", 2)))
        self.slack_webhook.setText(s.get("slack_webhook", ""))
        self.slack_enabled.setChecked(s.get("slack_enabled", False))
        self.teams_webhook.setText(s.get("teams_webhook", ""))
        self.teams_enabled.setChecked(s.get("teams_enabled", False))
        self.jira_url.setText(s.get("jira_url", ""))
        self.jira_token.setText(s.get("jira_token", ""))
        self.jira_project.setText(s.get("jira_project", ""))
        self.jira_enabled.setChecked(s.get("jira_enabled", False))
        self.webhook_url.setText(s.get("webhook_url", ""))
        self.webhook_enabled.setChecked(s.get("webhook_enabled", False))
        self.company_name.setText(s.get("company_name", ""))
        self.company_logo.setText(s.get("company_logo", ""))
        self.auditor_name.setText(s.get("auditor_name", ""))
        self.auditor_email.setText(s.get("auditor_email", ""))
        self.report_footer.setText(s.get("report_footer", ""))

    def _save(self):
        data = {
            "edu_mode":       self.edu_check.isChecked(),
            "quiet":          self.quiet_check.isChecked(),
            "dark_theme":     self.dark_check.isChecked(),
            "wordlist":       self.wordlist_edit.text().strip(),
            "workers":        int(self.workers_edit.text().strip() or 2),
            "slack_webhook":  self.slack_webhook.text().strip(),
            "slack_enabled":  self.slack_enabled.isChecked(),
            "teams_webhook":  self.teams_webhook.text().strip(),
            "teams_enabled":  self.teams_enabled.isChecked(),
            "jira_url":       self.jira_url.text().strip(),
            "jira_token":     self.jira_token.text().strip(),
            "jira_project":   self.jira_project.text().strip(),
            "jira_enabled":   self.jira_enabled.isChecked(),
            "webhook_url":    self.webhook_url.text().strip(),
            "webhook_enabled":self.webhook_enabled.isChecked(),
            "company_name":   self.company_name.text().strip(),
            "company_logo":   self.company_logo.text().strip(),
            "auditor_name":   self.auditor_name.text().strip(),
            "auditor_email":  self.auditor_email.text().strip(),
            "report_footer":  self.report_footer.text().strip(),
        }
        save_settings(data)
        # Actualizar flag educativo en core
        from ...core.ui import set_educational
        set_educational(data["edu_mode"])

        btn = self.sender()
        if btn:
            orig = btn.text()
            btn.setText("✔ Guardado")
            btn.setStyleSheet(f"background-color: rgba(16,185,129,0.2); color: #10b981; border-color: #10b981;")
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(2000, lambda: (btn.setText(orig), btn.setStyleSheet("")))

    def refresh(self):
        self._load()
