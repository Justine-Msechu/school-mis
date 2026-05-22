"""
ui/theme.py — Theme definitions for School MIS.
Three themes: light (default), dark, ocean.
GLOBAL_STYLE stays as an alias for backwards-compat imports.
"""

_FONTS = '"Segoe UI", "Ubuntu", "Noto Sans", sans-serif'

# ── Light (default) ────────────────────────────────────────────────────────────
LIGHT_STYLE = f"""
QWidget {{
    color: #111827;
    font-family: {_FONTS};
    font-size: 13px;
}}
QMainWindow, QDialog {{ background-color: #F3F4F6; }}
QLabel {{ color: #111827; background: transparent; }}

QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QDateEdit {{
    color: #111827; background-color: #FFFFFF;
    border: 1px solid #D1D5DB; border-radius: 6px; padding: 6px 10px;
    selection-background-color: #DBEAFE; selection-color: #1E3A8A;
}}
QLineEdit:focus, QTextEdit:focus, QDateEdit:focus,
QSpinBox:focus, QDoubleSpinBox:focus {{ border-color: #2563EB; }}
QLineEdit:disabled, QTextEdit:disabled {{ background-color: #F9FAFB; color: #9CA3AF; }}
QLineEdit::placeholder {{ color: #9CA3AF; }}

QComboBox {{
    color: #111827; background-color: #FFFFFF;
    border: 1px solid #D1D5DB; border-radius: 6px; padding: 6px 10px; min-height: 20px;
}}
QComboBox:focus {{ border-color: #2563EB; }}
QComboBox::drop-down {{ border: none; width: 24px; }}
QComboBox::down-arrow {{ width: 12px; height: 12px; }}
QComboBox QAbstractItemView {{
    color: #111827; background-color: #FFFFFF;
    border: 1px solid #D1D5DB; border-radius: 4px;
    selection-background-color: #EFF6FF; selection-color: #1D4ED8; outline: none;
}}

QPushButton {{
    color: #374151; background-color: #FFFFFF;
    border: 1px solid #D1D5DB; border-radius: 7px; padding: 7px 16px; font-size: 13px;
}}
QPushButton:hover  {{ background-color: #F9FAFB; border-color: #9CA3AF; }}
QPushButton:pressed {{ background-color: #F3F4F6; }}
QPushButton:disabled {{ color: #9CA3AF; background-color: #F9FAFB; }}

QTableWidget {{
    color: #111827; background-color: #FFFFFF;
    alternate-background-color: #F9FAFB;
    gridline-color: #F3F4F6;
    border: 1px solid #E5E7EB; border-radius: 8px;
}}
QTableWidget::item {{ color: #111827; padding: 6px 8px; }}
QTableWidget::item:selected {{ background-color: #EFF6FF; color: #1E40AF; }}
QHeaderView::section {{
    color: #374151; background-color: #F9FAFB; font-weight: 600;
    padding: 8px 10px; border: none; border-bottom: 1px solid #E5E7EB;
}}
QHeaderView::section:hover {{ background-color: #F3F4F6; }}

QTabWidget::pane {{ border: 1px solid #E5E7EB; border-radius: 8px; background: #FFFFFF; }}
QTabBar::tab {{
    color: #6B7280; background: #F3F4F6; border: 1px solid #E5E7EB;
    border-bottom: none; padding: 8px 18px; margin-right: 2px;
    border-top-left-radius: 6px; border-top-right-radius: 6px;
}}
QTabBar::tab:selected {{ color: #1D4ED8; background: #FFFFFF; font-weight: 600; }}
QTabBar::tab:hover:!selected {{ background: #E5E7EB; }}

QGroupBox {{
    color: #374151; font-weight: 600; border: 1px solid #E5E7EB;
    border-radius: 8px; margin-top: 14px; padding: 12px;
}}
QGroupBox::title {{
    color: #374151; subcontrol-origin: margin; left: 12px;
    padding: 0 6px; background: #F3F4F6;
}}

QMessageBox {{ background-color: #FFFFFF; }}
QMessageBox QLabel {{ color: #111827; font-size: 13px; }}

QScrollBar:vertical {{
    border: none; background: #F1F5F9; width: 8px; margin: 0;
}}
QScrollBar::handle:vertical {{ background: #CBD5E1; border-radius: 4px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: #94A3B8; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{ border: none; background: #F1F5F9; height: 8px; margin: 0; }}
QScrollBar::handle:horizontal {{ background: #CBD5E1; border-radius: 4px; min-width: 30px; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

QToolTip {{
    color: #FFFFFF; background-color: #1E293B; border: none;
    padding: 4px 8px; border-radius: 4px; font-size: 12px;
}}
QFrame[frameShape="4"], QFrame[frameShape="5"] {{ color: #E5E7EB; }}
QCalendarWidget QWidget {{ color: #111827; background: #FFFFFF; }}
QCalendarWidget QAbstractItemView {{
    color: #111827; selection-background-color: #DBEAFE; selection-color: #1E40AF;
}}
"""

# ── Dark ───────────────────────────────────────────────────────────────────────
DARK_STYLE = f"""
QWidget {{
    color: #E2E8F0;
    font-family: {_FONTS};
    font-size: 13px;
    background-color: #1E293B;
}}
QMainWindow, QDialog {{ background-color: #1E293B; }}
QLabel {{ color: #E2E8F0; background: transparent; }}

QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QDateEdit {{
    color: #F1F5F9; background-color: #0F172A;
    border: 1px solid #475569; border-radius: 6px; padding: 6px 10px;
    selection-background-color: #1D4ED8; selection-color: #FFFFFF;
}}
QLineEdit:focus, QTextEdit:focus, QDateEdit:focus,
QSpinBox:focus, QDoubleSpinBox:focus {{ border-color: #3B82F6; }}
QLineEdit:disabled, QTextEdit:disabled {{ background-color: #1E293B; color: #64748B; }}
QLineEdit::placeholder {{ color: #64748B; }}

QComboBox {{
    color: #F1F5F9; background-color: #0F172A;
    border: 1px solid #475569; border-radius: 6px; padding: 6px 10px; min-height: 20px;
}}
QComboBox:focus {{ border-color: #3B82F6; }}
QComboBox::drop-down {{ border: none; width: 24px; }}
QComboBox::down-arrow {{ width: 12px; height: 12px; }}
QComboBox QAbstractItemView {{
    color: #F1F5F9; background-color: #0F172A;
    border: 1px solid #475569; border-radius: 4px;
    selection-background-color: #1D4ED8; selection-color: #FFFFFF; outline: none;
}}

QPushButton {{
    color: #E2E8F0; background-color: #334155;
    border: 1px solid #475569; border-radius: 7px; padding: 7px 16px; font-size: 13px;
}}
QPushButton:hover  {{ background-color: #475569; border-color: #64748B; }}
QPushButton:pressed {{ background-color: #1E293B; }}
QPushButton:disabled {{ color: #64748B; background-color: #1E293B; }}

QTableWidget {{
    color: #E2E8F0; background-color: #0F172A;
    alternate-background-color: #1E293B;
    gridline-color: #334155;
    border: 1px solid #334155; border-radius: 8px;
}}
QTableWidget::item {{ color: #E2E8F0; padding: 6px 8px; }}
QTableWidget::item:selected {{ background-color: #1D4ED8; color: #FFFFFF; }}
QHeaderView::section {{
    color: #CBD5E1; background-color: #1E293B; font-weight: 600;
    padding: 8px 10px; border: none; border-bottom: 1px solid #334155;
}}
QHeaderView::section:hover {{ background-color: #334155; }}

QTabWidget::pane {{ border: 1px solid #334155; border-radius: 8px; background: #0F172A; }}
QTabBar::tab {{
    color: #94A3B8; background: #1E293B; border: 1px solid #334155;
    border-bottom: none; padding: 8px 18px; margin-right: 2px;
    border-top-left-radius: 6px; border-top-right-radius: 6px;
}}
QTabBar::tab:selected {{ color: #60A5FA; background: #0F172A; font-weight: 600; }}
QTabBar::tab:hover:!selected {{ background: #334155; }}

QGroupBox {{
    color: #CBD5E1; font-weight: 600; border: 1px solid #334155;
    border-radius: 8px; margin-top: 14px; padding: 12px;
}}
QGroupBox::title {{
    color: #CBD5E1; subcontrol-origin: margin; left: 12px;
    padding: 0 6px; background: #1E293B;
}}

QMessageBox {{ background-color: #1E293B; }}
QMessageBox QLabel {{ color: #E2E8F0; font-size: 13px; }}

QScrollBar:vertical {{ border: none; background: #0F172A; width: 8px; margin: 0; }}
QScrollBar::handle:vertical {{ background: #475569; border-radius: 4px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: #64748B; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{ border: none; background: #0F172A; height: 8px; margin: 0; }}
QScrollBar::handle:horizontal {{ background: #475569; border-radius: 4px; min-width: 30px; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

QToolTip {{
    color: #FFFFFF; background-color: #0F172A; border: 1px solid #334155;
    padding: 4px 8px; border-radius: 4px; font-size: 12px;
}}
QFrame[frameShape="4"], QFrame[frameShape="5"] {{ color: #334155; }}
QCalendarWidget QWidget {{ color: #E2E8F0; background: #1E293B; }}
QCalendarWidget QAbstractItemView {{
    color: #E2E8F0; selection-background-color: #1D4ED8; selection-color: #FFFFFF;
}}
"""

# ── Ocean Blue ─────────────────────────────────────────────────────────────────
OCEAN_STYLE = f"""
QWidget {{
    color: #0F172A;
    font-family: {_FONTS};
    font-size: 13px;
}}
QMainWindow, QDialog {{ background-color: #EFF6FF; }}
QLabel {{ color: #0F172A; background: transparent; }}

QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QDateEdit {{
    color: #0F172A; background-color: #FFFFFF;
    border: 1px solid #BFDBFE; border-radius: 6px; padding: 6px 10px;
    selection-background-color: #DBEAFE; selection-color: #1E3A8A;
}}
QLineEdit:focus, QTextEdit:focus, QDateEdit:focus,
QSpinBox:focus, QDoubleSpinBox:focus {{ border-color: #1D4ED8; }}
QLineEdit:disabled, QTextEdit:disabled {{ background-color: #EFF6FF; color: #93C5FD; }}
QLineEdit::placeholder {{ color: #93C5FD; }}

QComboBox {{
    color: #0F172A; background-color: #FFFFFF;
    border: 1px solid #BFDBFE; border-radius: 6px; padding: 6px 10px; min-height: 20px;
}}
QComboBox:focus {{ border-color: #1D4ED8; }}
QComboBox::drop-down {{ border: none; width: 24px; }}
QComboBox::down-arrow {{ width: 12px; height: 12px; }}
QComboBox QAbstractItemView {{
    color: #0F172A; background-color: #FFFFFF;
    border: 1px solid #BFDBFE; border-radius: 4px;
    selection-background-color: #DBEAFE; selection-color: #1E40AF; outline: none;
}}

QPushButton {{
    color: #1D4ED8; background-color: #EFF6FF;
    border: 1px solid #BFDBFE; border-radius: 7px; padding: 7px 16px; font-size: 13px;
}}
QPushButton:hover  {{ background-color: #DBEAFE; border-color: #93C5FD; }}
QPushButton:pressed {{ background-color: #BFDBFE; }}
QPushButton:disabled {{ color: #93C5FD; background-color: #EFF6FF; }}

QTableWidget {{
    color: #0F172A; background-color: #FFFFFF;
    alternate-background-color: #EFF6FF;
    gridline-color: #DBEAFE;
    border: 1px solid #BFDBFE; border-radius: 8px;
}}
QTableWidget::item {{ color: #0F172A; padding: 6px 8px; }}
QTableWidget::item:selected {{ background-color: #DBEAFE; color: #1E40AF; }}
QHeaderView::section {{
    color: #1E40AF; background-color: #DBEAFE; font-weight: 600;
    padding: 8px 10px; border: none; border-bottom: 1px solid #BFDBFE;
}}
QHeaderView::section:hover {{ background-color: #BFDBFE; }}

QTabWidget::pane {{ border: 1px solid #BFDBFE; border-radius: 8px; background: #FFFFFF; }}
QTabBar::tab {{
    color: #3B82F6; background: #EFF6FF; border: 1px solid #BFDBFE;
    border-bottom: none; padding: 8px 18px; margin-right: 2px;
    border-top-left-radius: 6px; border-top-right-radius: 6px;
}}
QTabBar::tab:selected {{ color: #1D4ED8; background: #FFFFFF; font-weight: 600; }}
QTabBar::tab:hover:!selected {{ background: #DBEAFE; }}

QGroupBox {{
    color: #1E40AF; font-weight: 600; border: 1px solid #BFDBFE;
    border-radius: 8px; margin-top: 14px; padding: 12px;
}}
QGroupBox::title {{
    color: #1E40AF; subcontrol-origin: margin; left: 12px;
    padding: 0 6px; background: #EFF6FF;
}}

QMessageBox {{ background-color: #FFFFFF; }}
QMessageBox QLabel {{ color: #0F172A; font-size: 13px; }}

QScrollBar:vertical {{ border: none; background: #EFF6FF; width: 8px; margin: 0; }}
QScrollBar::handle:vertical {{ background: #93C5FD; border-radius: 4px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: #60A5FA; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{ border: none; background: #EFF6FF; height: 8px; margin: 0; }}
QScrollBar::handle:horizontal {{ background: #93C5FD; border-radius: 4px; min-width: 30px; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

QToolTip {{
    color: #FFFFFF; background-color: #1E40AF; border: none;
    padding: 4px 8px; border-radius: 4px; font-size: 12px;
}}
QFrame[frameShape="4"], QFrame[frameShape="5"] {{ color: #BFDBFE; }}
QCalendarWidget QWidget {{ color: #0F172A; background: #FFFFFF; }}
QCalendarWidget QAbstractItemView {{
    color: #0F172A; selection-background-color: #DBEAFE; selection-color: #1E40AF;
}}
"""

# ── Theme registry ─────────────────────────────────────────────────────────────
THEMES = {
    "light": {
        "name":       "Light",
        "style":      LIGHT_STYLE,
        "content_bg": "#F3F4F6",
        "preview":    ("#F3F4F6", "#FFFFFF", "#2563EB"),  # bg, panel, accent
    },
    "dark": {
        "name":       "Dark",
        "style":      DARK_STYLE,
        "content_bg": "#1E293B",
        "preview":    ("#1E293B", "#0F172A", "#3B82F6"),
    },
    "ocean": {
        "name":       "Ocean Blue",
        "style":      OCEAN_STYLE,
        "content_bg": "#EFF6FF",
        "preview":    ("#EFF6FF", "#FFFFFF", "#1D4ED8"),
    },
}

# Backwards-compat alias used in main.py
GLOBAL_STYLE = LIGHT_STYLE
