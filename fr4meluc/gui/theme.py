"""Paleta de colores y estilos globales de la GUI Fr4meLuc Enterprise."""

# Colores base
BG_DARK   = "#0f111a"
BG_CARD   = "#1a1e29"
BG_PANEL  = "#141720"
ACCENT    = "#00ff88"
ACCENT2   = "#00d4ff"
DANGER    = "#ef4444"
WARNING   = "#f59e0b"
SUCCESS   = "#10b981"
TEXT_MAIN = "#e2e8f0"
TEXT_MUTED= "#64748b"
BORDER    = "#2a2f3e"

SEV_COLORS = {
    "critical": "#7c3aed",
    "high":     "#ef4444",
    "medium":   "#f59e0b",
    "low":      "#3b82f6",
    "info":     "#64748b",
}

STYLESHEET = f"""
/* ─── App global ─── */
QMainWindow, QDialog, QWidget {{
    background-color: {BG_DARK};
    color: {TEXT_MAIN};
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 13px;
}}

/* ─── Sidebar ─── */
#sidebar {{
    background-color: {BG_CARD};
    border-right: 1px solid {BORDER};
}}
#sidebar QPushButton {{
    background: transparent;
    color: {TEXT_MUTED};
    border: none;
    border-radius: 8px;
    padding: 10px 16px;
    text-align: left;
    font-size: 13px;
}}
#sidebar QPushButton:hover {{
    background-color: rgba(255,255,255,0.06);
    color: {TEXT_MAIN};
}}
#sidebar QPushButton[active="true"] {{
    background-color: rgba(0, 255, 136, 0.12);
    color: {ACCENT};
    font-weight: bold;
}}

/* ─── Cards ─── */
QFrame#card {{
    background-color: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 12px;
}}

/* ─── Tables ─── */
QTableWidget {{
    background-color: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 8px;
    gridline-color: {BORDER};
    color: {TEXT_MAIN};
    selection-background-color: rgba(0,255,136,0.15);
}}
QTableWidget::item {{ padding: 6px 12px; }}
QHeaderView::section {{
    background-color: {BG_PANEL};
    color: {TEXT_MUTED};
    border: none;
    padding: 8px 12px;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 1px;
}}

/* ─── Inputs ─── */
QLineEdit, QTextEdit, QComboBox, QSpinBox {{
    background-color: {BG_PANEL};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 8px 12px;
    color: {TEXT_MAIN};
}}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{
    border-color: {ACCENT};
}}

/* ─── Buttons ─── */
QPushButton {{
    background-color: {BG_PANEL};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 8px 18px;
    color: {TEXT_MAIN};
    font-weight: 500;
}}
QPushButton:hover {{
    border-color: {ACCENT};
    color: {ACCENT};
}}
QPushButton#btn_primary {{
    background-color: {ACCENT};
    color: #0f111a;
    border: none;
    font-weight: bold;
}}
QPushButton#btn_primary:hover {{
    background-color: #00e577;
    color: #0f111a;
}}
QPushButton#btn_danger {{
    background-color: rgba(239,68,68,0.15);
    border-color: {DANGER};
    color: {DANGER};
}}

/* ─── Tabs ─── */
QTabWidget::pane {{
    border: 1px solid {BORDER};
    border-radius: 8px;
    background: {BG_CARD};
}}
QTabBar::tab {{
    background: transparent;
    color: {TEXT_MUTED};
    padding: 8px 20px;
    border-bottom: 2px solid transparent;
}}
QTabBar::tab:selected {{
    color: {ACCENT};
    border-bottom: 2px solid {ACCENT};
}}

/* ─── ScrollBar ─── */
QScrollBar:vertical {{
    background: {BG_DARK};
    width: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: {TEXT_MUTED}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}

/* ─── Labels ─── */
QLabel#title {{
    font-size: 22px;
    font-weight: bold;
    color: {TEXT_MAIN};
}}
QLabel#subtitle {{
    font-size: 13px;
    color: {TEXT_MUTED};
}}
QLabel#section_header {{
    font-size: 12px;
    font-weight: bold;
    color: {TEXT_MUTED};
    letter-spacing: 1px;
    text-transform: uppercase;
}}

/* ─── Terminal output ─── */
QTextEdit#terminal {{
    background-color: #080a10;
    color: #a9f8cb;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 12px;
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 8px;
}}

/* ─── Progress bar ─── */
QProgressBar {{
    background-color: {BG_PANEL};
    border: 1px solid {BORDER};
    border-radius: 4px;
    height: 6px;
    text-align: center;
}}
QProgressBar::chunk {{
    background-color: {ACCENT};
    border-radius: 4px;
}}

/* ─── Checkbox ─── */
QCheckBox {{ color: {TEXT_MAIN}; spacing: 8px; }}
QCheckBox::indicator {{
    width: 16px; height: 16px;
    border-radius: 4px;
    border: 1px solid {BORDER};
    background: {BG_PANEL};
}}
QCheckBox::indicator:checked {{
    background-color: {ACCENT};
    border-color: {ACCENT};
}}

/* ─── Splitter ─── */
QSplitter::handle {{ background: {BORDER}; }}
"""
