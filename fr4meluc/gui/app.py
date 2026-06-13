"""Entry point de la GUI: crea QApplication y lanza la ventana principal."""
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont

from .main_window import MainWindow


def run_gui(argv=None):
    app = QApplication(argv or sys.argv)
    app.setApplicationName("Fr4meLuc Enterprise")
    app.setOrganizationName("Fr4meLuc")

    font = QFont("Segoe UI", 10)
    app.setFont(font)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())
