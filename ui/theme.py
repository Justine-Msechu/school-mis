"""
Global Qt stylesheet for School MIS.
Imported once in main.py via app.setStyleSheet(GLOBAL_STYLE).

Fixes: all text explicitly dark so nothing disappears on light backgrounds.
"""

GLOBAL_STYLE = """

/* ── Base widget text ──────────────────────────────────────────── */
QWidget {
    color: #111827;
    font-family: "Segoe UI", "Ubuntu", "Noto Sans", sans-serif;
    font-size: 13px;
}

QMainWindow, QDialog {
    background-color: #F3F4F6;
}

/* ── Labels ───────────────────────────────────────────────────── */
QLabel {
    color: #111827;
    background: transparent;
}

/* ── Input fields ─────────────────────────────────────────────── */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QDateEdit {
    color: #111827;
    background-color: #FFFFFF;
    border: 1px solid #D1D5DB;
    border-radius: 6px;
    padding: 6px 10px;
    selection-background-color: #DBEAFE;
    selection-color: #1E3A8A;
}
QLineEdit:focus, QTextEdit:focus, QDateEdit:focus,
QSpinBox:focus, QDoubleSpinBox:focus {
    border-color: #2563EB;
    outline: none;
}
QLineEdit:disabled, QTextEdit:disabled {
    background-color: #F9FAFB;
    color: #9CA3AF;
}
QLineEdit::placeholder { color: #9CA3AF; }

/* ── Combo boxes ──────────────────────────────────────────────── */
QComboBox {
    color: #111827;
    background-color: #FFFFFF;
    border: 1px solid #D1D5DB;
    border-radius: 6px;
    padding: 6px 10px;
    min-height: 20px;
}
QComboBox:focus { border-color: #2563EB; }
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox::down-arrow {
    width: 12px; height: 12px;
}
QComboBox QAbstractItemView {
    color: #111827;
    background-color: #FFFFFF;
    border: 1px solid #D1D5DB;
    border-radius: 4px;
    selection-background-color: #EFF6FF;
    selection-color: #1D4ED8;
    outline: none;
}

/* ── Push buttons ─────────────────────────────────────────────── */
QPushButton {
    color: #374151;
    background-color: #FFFFFF;
    border: 1px solid #D1D5DB;
    border-radius: 7px;
    padding: 7px 16px;
    font-size: 13px;
}
QPushButton:hover  { background-color: #F9FAFB; border-color: #9CA3AF; }
QPushButton:pressed { background-color: #F3F4F6; }
QPushButton:disabled { color: #9CA3AF; background-color: #F9FAFB; }

/* ── Tables ───────────────────────────────────────────────────── */
QTableWidget {
    color: #111827;
    background-color: #FFFFFF;
    alternate-background-color: #F9FAFB;
    gridline-color: #F3F4F6;
    border: 1px solid #E5E7EB;
    border-radius: 8px;
}
QTableWidget::item {
    color: #111827;
    padding: 6px 8px;
}
QTableWidget::item:selected {
    background-color: #EFF6FF;
    color: #1E40AF;
}
QHeaderView::section {
    color: #374151;
    background-color: #F9FAFB;
    font-weight: 600;
    padding: 8px 10px;
    border: none;
    border-bottom: 1px solid #E5E7EB;
}
QHeaderView::section:hover { background-color: #F3F4F6; }

/* ── Tab widget ───────────────────────────────────────────────── */
QTabWidget::pane {
    border: 1px solid #E5E7EB;
    border-radius: 8px;
    background: #FFFFFF;
}
QTabBar::tab {
    color: #6B7280;
    background: #F3F4F6;
    border: 1px solid #E5E7EB;
    border-bottom: none;
    padding: 8px 18px;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}
QTabBar::tab:selected {
    color: #1D4ED8;
    background: #FFFFFF;
    font-weight: 600;
}
QTabBar::tab:hover:!selected { background: #E5E7EB; }

/* ── Group box ────────────────────────────────────────────────── */
QGroupBox {
    color: #374151;
    font-weight: 600;
    border: 1px solid #E5E7EB;
    border-radius: 8px;
    margin-top: 14px;
    padding: 12px;
}
QGroupBox::title {
    color: #374151;
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    background: #F3F4F6;
}

/* ── Message boxes ────────────────────────────────────────────── */
QMessageBox { background-color: #FFFFFF; }
QMessageBox QLabel { color: #111827; font-size: 13px; }

/* ── Scrollbars ───────────────────────────────────────────────── */
QScrollBar:vertical {
    border: none; background: #F1F5F9; width: 8px; margin: 0;
}
QScrollBar::handle:vertical {
    background: #CBD5E1; border-radius: 4px; min-height: 30px;
}
QScrollBar::handle:vertical:hover { background: #94A3B8; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

QScrollBar:horizontal {
    border: none; background: #F1F5F9; height: 8px; margin: 0;
}
QScrollBar::handle:horizontal {
    background: #CBD5E1; border-radius: 4px; min-width: 30px;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

/* ── Tooltips ─────────────────────────────────────────────────── */
QToolTip {
    color: #FFFFFF;
    background-color: #1E293B;
    border: none;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 12px;
}

/* ── Frame dividers ───────────────────────────────────────────── */
QFrame[frameShape="4"], QFrame[frameShape="5"] {
    color: #E5E7EB;
}

/* ── Calendar popup ───────────────────────────────────────────── */
QCalendarWidget QWidget { color: #111827; background: #FFFFFF; }
QCalendarWidget QAbstractItemView {
    color: #111827;
    selection-background-color: #DBEAFE;
    selection-color: #1E40AF;
}
"""
