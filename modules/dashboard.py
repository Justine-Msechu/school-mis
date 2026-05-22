"""Dashboard — summary cards shown on startup."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from database.db import fetch_one
from datetime import date


class StatCard(QFrame):
    def __init__(self, title, value, color="#2563EB", icon=""):
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
        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet(f"font-size: 22px; color: {color};")
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

        self.card_students  = StatCard("Total students",  "—", "#2563EB", "🎓")
        self.card_teachers  = StatCard("Teachers & staff","—", "#059669", "👩‍🏫")
        self.card_classes   = StatCard("Active classes",  "—", "#7C3AED", "🏫")
        self.card_present   = StatCard("Present today",   "—", "#D97706", "✅")
        self.card_fees      = StatCard("Fees this month (TZS)", "—", "#DC2626", "💰")
        self.card_absent    = StatCard("Absent today",    "—", "#6B7280", "📋")

        for i, card in enumerate([
            self.card_students, self.card_teachers, self.card_classes,
            self.card_present, self.card_fees, self.card_absent,
        ]):
            grid.addWidget(card, i // 3, i % 3)

        main.addLayout(grid)

        # Quick info banner
        info = QLabel(
            "💡  Tip: start by adding your classes, then enrol students. "
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
