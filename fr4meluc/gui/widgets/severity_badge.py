"""Badge de severidad inline para tablas y listas."""
from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import Qt
from ..theme import SEV_COLORS


class SeverityBadge(QLabel):
    def __init__(self, severity: str = "info", parent=None):
        super().__init__(parent)
        sev = severity.lower()
        color = SEV_COLORS.get(sev, SEV_COLORS["info"])
        self.setText(sev.upper())
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedWidth(80)
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {color}22;
                color: {color};
                border: 1px solid {color}66;
                border-radius: 4px;
                padding: 2px 6px;
                font-size: 11px;
                font-weight: bold;
            }}
        """)
