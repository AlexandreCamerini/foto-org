"""Tema dark-first — tokens definidos em docs/DIRECAO_DE_ARTE.md."""

BG_WINDOW = "#1E1E1E"
BG_PANEL = "#252526"
BG_CARD = "#2D2D30"
BORDER = "#3E3E42"
TEXT_PRIMARY = "#E8E8E8"
TEXT_SECONDARY = "#9DA0A6"
TEXT_DISABLED = "#6B6E76"
ACCENT = "#3B82F6"
CONF_ALTA = "#34D399"
CONF_MEDIA = "#FBBF24"
CONF_BAIXA = "#F87171"

QSS = f"""
QMainWindow, QWidget {{
    background-color: {BG_WINDOW};
    color: {TEXT_PRIMARY};
    font-size: 13px;
}}

QWidget#painelLateral, QWidget#painelInspetor {{
    background-color: {BG_PANEL};
}}

QLabel#tituloPainel {{
    color: {TEXT_SECONDARY};
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1px;
    padding: 12px 12px 4px 12px;
}}

QLabel#textoSecundario {{
    color: {TEXT_SECONDARY};
    font-size: 11px;
}}

QSplitter::handle {{
    background-color: {BORDER};
    width: 1px;
}}

QStatusBar {{
    background-color: {BG_PANEL};
    color: {TEXT_SECONDARY};
    font-size: 11px;
    border-top: 1px solid {BORDER};
}}

QPushButton {{
    background-color: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 6px 16px;
}}
QPushButton:hover {{ border-color: {ACCENT}; }}
QPushButton:default {{
    background-color: {ACCENT};
    border-color: {ACCENT};
    color: white;
}}
QPushButton:disabled {{ color: {TEXT_DISABLED}; }}

QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: 4px;
    min-height: 24px;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
    margin: 2px;
}}
QScrollBar::handle:horizontal {{
    background: {BORDER};
    border-radius: 4px;
    min-width: 24px;
}}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}

QListView {{
    background-color: {BG_WINDOW};
    border: none;
    outline: none;
}}
QListView::item {{
    color: {TEXT_SECONDARY};
    border: 2px solid transparent;
    border-radius: 6px;
    padding: 2px;
}}
QListView::item:selected {{
    border-color: {ACCENT};
    background-color: transparent;
    color: {TEXT_PRIMARY};
}}

QWidget#painelLateral QListWidget {{
    background-color: {BG_PANEL};
    border: none;
    outline: none;
}}
QWidget#painelLateral QListWidget::item {{
    padding: 6px 12px;
    border: none;
}}
QWidget#painelLateral QListWidget::item:selected {{
    background-color: {BG_CARD};
    color: {TEXT_PRIMARY};
    border-left: 2px solid {ACCENT};
}}

QLineEdit {{
    background-color: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 5px 8px;
}}
QLineEdit:focus {{ border-color: {ACCENT}; }}

QComboBox {{
    background-color: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 4px 8px;
    min-width: 90px;
}}
QComboBox QAbstractItemView {{
    background-color: {BG_CARD};
    border: 1px solid {BORDER};
    selection-background-color: {ACCENT};
}}

QSlider::groove:horizontal {{
    height: 3px;
    background: {BORDER};
    border-radius: 1px;
}}
QSlider::handle:horizontal {{
    width: 12px;
    height: 12px;
    margin: -5px 0;
    border-radius: 6px;
    background: {TEXT_SECONDARY};
}}
QSlider::handle:horizontal:hover {{ background: {ACCENT}; }}

QScrollArea {{ border: none; }}
"""
