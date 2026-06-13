"""Widget de tarjeta de estadística para el dashboard."""
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt
from ..theme import ACCENT, TEXT_MUTED, BG_CARD, BORDER


class StatCard(QFrame):
    def __init__(self, title: str, value: str = "0", color: str = ACCENT, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setMinimumWidth(140)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 18, 20, 18)
        lay.setSpacing(6)

        self._val_label = QLabel(value)
        self._val_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._val_label.setStyleSheet(f"font-size: 32px; font-weight: bold; color: {color};")

        self._title_label = QLabel(title.upper())
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title_label.setStyleSheet(f"font-size: 11px; color: {TEXT_MUTED}; letter-spacing: 1px;")

        lay.addWidget(self._val_label)
        lay.addWidget(self._title_label)

    def set_value(self, value: str) -> None:
        self._val_label.setText(str(value))
