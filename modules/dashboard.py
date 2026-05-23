"""Dashboard — summary cards shown on startup."""

from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QColor, QFont, QImage, QPixmap
from database.db import fetch_one
from datetime import date

_ICON_DIR = Path(__file__).parent.parent / "assets" / "Icons" / "PNG"


def _stat_icon(n: int, color: str, size: int = 28) -> QPixmap:
    src = QPixmap(str(_ICON_DIR / f"Icon {n}.png"))
    if src.isNull():
        return QPixmap()
    src = src.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio,
                     Qt.TransformationMode.SmoothTransformation)
    img = src.toImage().convertToFormat(QImage.Format.Format_ARGB32)
    c = QColor(color)
    r, g, b = c.red(), c.green(), c.blue()
    for y in range(img.height()):
        for x in range(img.width()):
            lum = (QColor(img.pixel(x, y)).red() + QColor(img.pixel(x, y)).green()
                   + QColor(img.pixel(x, y)).blue()) // 3
            img.setPixelColor(x, y, QColor(r, g, b, 255 - lum))
    return QPixmap.fromImage(img)


class StatCard(QFrame):
    def __init__(self, title, value, color="#2563EB", icon_num=0):
        super().__init__()
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(f"""
            QFrame {{
                background: white;
                border-radius: 12px;
                border: 1px solid #E5E7EB;
            }}
        """)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(110)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(6)

        top = QHBoxLayout()
        icon_lbl = QLabel()
        if icon_num:
            pix = _stat_icon(icon_num, color)
            icon_lbl.setPixmap(pix)
        top.addWidget(icon_lbl)
        top.addStretch()
        layout.addLayout(top)

        self.value_lbl = QLabel(str(value))
        self.value_lbl.setStyleSheet(f"font-size: 28px; font-weight: 700; color: {color};")
        layout.addWidget(self.value_lbl)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size: 13px; color: #6B7280;")
        layout.addWidget(title_lbl)

    def set_value(self, v):
        self.value_lbl.setText(str(v))


class DashboardWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.build_ui()
        self.refresh()

    def build_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(28, 24, 28, 24)
        main.setSpacing(20)

        # Header
        today = date.today().strftime("%A, %d %B %Y")
        header = QLabel(f"Good morning  —  {today}")
        header.setStyleSheet("font-size: 15px; color: #6B7280;")
        main.addWidget(header)

        title = QLabel("School Dashboard")
        title.setStyleSheet("font-size: 22px; font-weight: 700; color: #111827;")
        main.addWidget(title)

        # Stat cards grid
        grid = QGridLayout()
        grid.setSpacing(14)

        self.card_students  = StatCard("Total students",       "—", "#2563EB", 10)
        self.card_teachers  = StatCard("Teachers & staff",     "—", "#059669", 41)
        self.card_classes   = StatCard("Active classes",       "—", "#7C3AED", 38)
        self.card_present   = StatCard("Present today",        "—", "#D97706",  2)
        self.card_fees      = StatCard("Fees this month (TZS)","—", "#DC2626",  3)
        self.card_absent    = StatCard("Absent today",         "—", "#6B7280",  2)
        self.card_welfare   = StatCard("Welfare students",     "—", "#9333EA",  5)
        self.card_unpaid    = StatCard("Unpaid bills",         "—", "#B91C1C",  3)
        self.card_low_stock = StatCard("Low stock items",      "—", "#B45309",  6)

        for i, card in enumerate([
            self.card_students, self.card_teachers, self.card_classes,
            self.card_present,  self.card_fees,     self.card_absent,
            self.card_welfare,  self.card_unpaid,   self.card_low_stock,
        ]):
            grid.addWidget(card, i // 3, i % 3)

        main.addLayout(grid)

        # Quick info banner
        info = QLabel(
            "Tip: start by adding your classes, then enrol students. "
            "Use the sidebar to navigate between modules."
        )
        info.setWordWrap(True)
        info.setStyleSheet("""
            background: #EFF6FF; color: #1D4ED8;
            border-radius: 8px; padding: 12px 16px;
            font-size: 13px;
        """)
        main.addWidget(info)
        main.addStretch()

    def refresh(self):
        today = date.today().isoformat()

        r = fetch_one("SELECT COUNT(*) AS n FROM students WHERE is_active=1")
        self.card_students.set_value(r["n"] if r else 0)

        r = fetch_one("SELECT COUNT(*) AS n FROM teachers WHERE is_active=1")
        self.card_teachers.set_value(r["n"] if r else 0)

        r = fetch_one("SELECT COUNT(*) AS n FROM classes")
        self.card_classes.set_value(r["n"] if r else 0)

        r = fetch_one(
            "SELECT COUNT(*) AS n FROM attendance WHERE date=? AND status='Present'", (today,)
        )
        self.card_present.set_value(r["n"] if r else 0)

        r = fetch_one(
            "SELECT COUNT(*) AS n FROM attendance WHERE date=? AND status='Absent'", (today,)
        )
        self.card_absent.set_value(r["n"] if r else 0)

        r = fetch_one(
            "SELECT COALESCE(SUM(amount_paid),0) AS total FROM fee_payments "
            "WHERE strftime('%Y-%m', payment_date) = strftime('%Y-%m', 'now')"
        )
        total = r["total"] if r else 0
        self.card_fees.set_value(f"{total:,.0f}")

        r = fetch_one("SELECT COUNT(*) AS n FROM welfare_records")
        self.card_welfare.set_value(r["n"] if r else 0)

        r = fetch_one(
            "SELECT COUNT(*) AS n FROM student_bills WHERE status IN ('unpaid','partial')"
        )
        self.card_unpaid.set_value(r["n"] if r else 0)

        r = fetch_one(
            "SELECT COUNT(*) AS n FROM inventory_items "
            "WHERE is_active=1 AND stock_qty <= reorder_qty"
        )
        self.card_low_stock.set_value(r["n"] if r else 0)
