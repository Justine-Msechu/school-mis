"""Finance Report — collection rates, outstanding balances, by class."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QAbstractItemView, QGridLayout, QSizePolicy
)
from PyQt6.QtGui import QColor
from database.db import fetch_all, fetch_one

INPUT = "QComboBox{border:1px solid #D1D5DB;border-radius:6px;padding:6px 10px;font-size:13px;background:white;}"


def _stat(label, value, color):
    f = QFrame()
    f.setStyleSheet(f"QFrame{{background:white;border:1px solid #E5E7EB;border-radius:10px;}}")
    f.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    f.setMinimumHeight(90)
    lay = QVBoxLayout(f); lay.setContentsMargins(16, 12, 16, 12)
    v = QLabel(value); v.setStyleSheet(f"font-size:20px;font-weight:700;color:{color};")
    l = QLabel(label); l.setStyleSheet("font-size:12px;color:#6B7280;")
    lay.addWidget(v); lay.addWidget(l)
    return f, v


class FinanceReportWidget(QWidget):
    COLS = ["Class", "Students Billed", "Total Billed (TZS)", "Collected (TZS)",
            "Outstanding (TZS)", "Waived (TZS)", "Collection Rate"]

    def __init__(self):
        super().__init__()
        self._stats = {}
        self._build()
        self.load_table()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 20, 28, 20); layout.setSpacing(14)

        row0 = QHBoxLayout()
        t = QLabel("Finance Report")
        t.setStyleSheet("font-size:20px;font-weight:700;color:#111827;")
        row0.addWidget(t); row0.addStretch()
        self.year_cb = QComboBox(); self.year_cb.setStyleSheet(INPUT)
        self.year_cb.addItem("All years", None)
        for y in fetch_all("SELECT id,label FROM academic_years ORDER BY id DESC"):
            self.year_cb.addItem(y["label"], y["id"])
        self.year_cb.currentIndexChanged.connect(self.load_table)
        row0.addWidget(QLabel("Year:")); row0.addWidget(self.year_cb)
        layout.addLayout(row0)

        # Summary cards
        grid = QGridLayout(); grid.setSpacing(12)
        for i, (key, lbl, color) in enumerate([
            ("billed",     "Total Billed",      "#DC2626"),
            ("collected",  "Collected",          "#059669"),
            ("outstanding","Outstanding",        "#D97706"),
            ("waived",     "Waived",             "#7C3AED"),
            ("rate",       "Collection Rate",    "#2563EB"),
            ("orphans",    "Exempt Students",    "#0891B2"),
        ]):
            f, v = _stat(lbl, "—", color)
            self._stats[key] = v
            grid.addWidget(f, i // 3, i % 3)
        layout.addLayout(grid)

        # By-class breakdown
        lbl = QLabel("Breakdown by class")
        lbl.setStyleSheet("font-size:14px;font-weight:600;color:#374151;margin-top:4px;")
        layout.addWidget(lbl)

        self.table = QTableWidget()
        self.table.setColumnCount(len(self.COLS))
        self.table.setHorizontalHeaderLabels(self.COLS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet("""
            QTableWidget{border:1px solid #E5E7EB;border-radius:8px;
                gridline-color:#F3F4F6;font-size:13px;}
            QHeaderView::section{background:#F9FAFB;font-weight:600;
                padding:8px;border:none;border-bottom:1px solid #E5E7EB;color:#374151;}
            QTableWidget::item{padding:6px 8px;}
        """)
        layout.addWidget(self.table)

    def load_table(self):
        year_id = self.year_cb.currentData()
        year_cond = "AND sb.academic_year_id=?" if year_id else ""
        params = (year_id,) if year_id else ()

        # Overall summary
        totals = fetch_one(f"""
            SELECT COALESCE(SUM(sb.amount_due),0)     AS billed,
                   COALESCE(SUM(sb.amount_paid),0)    AS collected,
                   COALESCE(SUM(sb.discount_amount),0) AS waived,
                   COUNT(DISTINCT CASE WHEN sb.status='waived' THEN sb.student_id END) AS exempt_count
            FROM student_bills sb WHERE 1=1 {year_cond}
        """, params)

        if totals:
            billed     = totals["billed"]
            collected  = totals["collected"]
            waived     = totals["waived"]
            outstanding = max(billed - collected - waived, 0)
            rate = f"{(collected/billed*100):.1f}%" if billed > 0 else "N/A"
            self._stats["billed"].setText(f"TZS {billed:,.0f}")
            self._stats["collected"].setText(f"TZS {collected:,.0f}")
            self._stats["outstanding"].setText(f"TZS {outstanding:,.0f}")
            self._stats["waived"].setText(f"TZS {waived:,.0f}")
            self._stats["rate"].setText(rate)
            self._stats["orphans"].setText(str(totals["exempt_count"]))

        # By class
        rows = fetch_all(f"""
            SELECT c.name AS class_name,
                   COUNT(DISTINCT sb.student_id)          AS students,
                   COALESCE(SUM(sb.amount_due),0)         AS billed,
                   COALESCE(SUM(sb.amount_paid),0)        AS collected,
                   COALESCE(SUM(sb.discount_amount),0)    AS waived
            FROM student_bills sb
            JOIN students s ON s.id=sb.student_id
            LEFT JOIN classes c ON c.id=s.class_id
            WHERE 1=1 {year_cond}
            GROUP BY c.id ORDER BY c.grade_level, c.name
        """, params)

        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            billed = row["billed"]
            collected = row["collected"]
            waived = row["waived"]
            outstanding = max(billed - collected - waived, 0)
            rate = f"{(collected/billed*100):.1f}%" if billed > 0 else "N/A"
            rate_ok = billed > 0 and (collected / billed) >= 0.8

            for c, v in enumerate([
                row["class_name"] or "Unassigned",
                str(row["students"]),
                f"{billed:,.0f}",
                f"{collected:,.0f}",
                f"{outstanding:,.0f}",
                f"{waived:,.0f}",
                rate,
            ]):
                item = QTableWidgetItem(v)
                if c == 6:  # rate column
                    item.setForeground(QColor("#065F46" if rate_ok else "#991B1B"))
                self.table.setItem(r, c, item)
