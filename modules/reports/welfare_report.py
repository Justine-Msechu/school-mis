"""Welfare Report — orphan roster, support types, exemption values."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QGridLayout,
    QAbstractItemView, QSizePolicy
)
from PyQt6.QtGui import QColor
from database.db import fetch_all, fetch_one

CAT_COLORS = {
    "orphan":      "#991B1B",
    "half_orphan": "#92400E",
    "sponsored":   "#065F46",
    "vulnerable":  "#4C1D95",
}


def _stat(label, value, color):
    f = QFrame()
    f.setStyleSheet("QFrame{background:white;border:1px solid #E5E7EB;border-radius:10px;}")
    f.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    f.setMinimumHeight(90)
    lay = QVBoxLayout(f); lay.setContentsMargins(16, 12, 16, 12)
    v = QLabel(value); v.setStyleSheet(f"font-size:20px;font-weight:700;color:{color};")
    l = QLabel(label); l.setStyleSheet("font-size:12px;color:#6B7280;")
    lay.addWidget(v); lay.addWidget(l)
    return f, v


class WelfareReportWidget(QWidget):
    COLS = ["Student", "Adm No", "Class", "Category", "Support Type",
            "Sponsor", "Verified", "Fees Waived (TZS)"]

    def __init__(self):
        super().__init__()
        self._stats = {}
        self._build()
        self.load_table()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 20, 28, 20); layout.setSpacing(14)

        t = QLabel("Welfare Report")
        t.setStyleSheet("font-size:20px;font-weight:700;color:#111827;")
        layout.addWidget(t)

        grid = QGridLayout(); grid.setSpacing(12)
        for i, (key, lbl, color) in enumerate([
            ("total",       "Total Welfare Students", "#7C3AED"),
            ("orphans",     "Orphans",                "#DC2626"),
            ("sponsored",   "Sponsored",              "#059669"),
            ("full_exempt", "Full Fee Exempt",        "#D97706"),
            ("verified",    "Verified Records",       "#0891B2"),
            ("waived_val",  "Total Fees Waived",      "#991B1B"),
        ]):
            f, v = _stat(lbl, "—", color)
            self._stats[key] = v
            grid.addWidget(f, i // 3, i % 3)
        layout.addLayout(grid)

        lbl = QLabel("Welfare Student Roster")
        lbl.setStyleSheet("font-size:14px;font-weight:600;color:#374151;margin-top:4px;")
        layout.addWidget(lbl)

        self.table = QTableWidget()
        self.table.setColumnCount(len(self.COLS))
        self.table.setHorizontalHeaderLabels(self.COLS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(False)
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
        counts = fetch_one("""
            SELECT COUNT(*) AS total,
                   SUM(CASE WHEN category='orphan' THEN 1 ELSE 0 END) AS orphans,
                   SUM(CASE WHEN category='sponsored' THEN 1 ELSE 0 END) AS sponsored,
                   SUM(CASE WHEN support_type='full_fees' THEN 1 ELSE 0 END) AS full_exempt,
                   SUM(CASE WHEN verified=1 THEN 1 ELSE 0 END) AS verified
            FROM welfare_records
        """)
        if counts:
            self._stats["total"].setText(str(counts["total"] or 0))
            self._stats["orphans"].setText(str(counts["orphans"] or 0))
            self._stats["sponsored"].setText(str(counts["sponsored"] or 0))
            self._stats["full_exempt"].setText(str(counts["full_exempt"] or 0))
            self._stats["verified"].setText(str(counts["verified"] or 0))

        waived = fetch_one("""
            SELECT COALESCE(SUM(sb.amount_due * fw.discount_percent/100),0) AS t
            FROM fee_waivers fw
            JOIN student_bills sb ON sb.id=fw.bill_id
        """)
        waiv_val = waived["t"] if waived else 0
        self._stats["waived_val"].setText(f"TZS {waiv_val:,.0f}")

        rows = fetch_all("""
            SELECT s.first_name||' '||s.last_name AS student, s.admission_no,
                   c.name AS class_name, wr.category, wr.support_type,
                   wr.sponsor_name, wr.sponsor_org, wr.verified,
                   COALESCE(SUM(sb.amount_due * fw.discount_percent/100),0) AS waived_total
            FROM welfare_records wr
            JOIN students s ON s.id=wr.student_id
            LEFT JOIN classes c ON c.id=s.class_id
            LEFT JOIN fee_waivers fw ON fw.student_id=s.id
            LEFT JOIN student_bills sb ON sb.id=fw.bill_id
            GROUP BY s.id ORDER BY wr.category, s.last_name
        """)
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            fg = CAT_COLORS.get(row["category"], "#374151")
            sponsor = row["sponsor_name"] or row["sponsor_org"] or "—"
            for c, v in enumerate([
                row["student"], row["admission_no"],
                row["class_name"] or "—",
                row["category"].replace("_", " ").title(),
                row["support_type"].replace("_", " ").title(),
                sponsor,
                "Yes" if row["verified"] else "No",
                f"{row['waived_total']:,.0f}",
            ]):
                item = QTableWidgetItem(v)
                item.setForeground(QColor(fg))
                self.table.setItem(r, c, item)
