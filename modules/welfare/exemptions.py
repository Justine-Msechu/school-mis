"""Exemptions — read-only overview of all waived/exempt students."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView
)
from PyQt6.QtGui import QColor
from database.db import fetch_all, fetch_one

BTN_OUTLINE = """QPushButton{background:white;color:#374151;border:1px solid #D1D5DB;
    border-radius:7px;padding:8px 18px;font-size:13px;}QPushButton:hover{background:#F9FAFB;}"""


class ExemptionsWidget(QWidget):
    COLS = ["Student", "Adm No", "Category", "Waiver Type", "Discount %",
            "Bill / Scope", "Academic Year", "Fee Name", "Bill Amount (TZS)"]

    def __init__(self):
        super().__init__()
        self._build()
        self.load_table()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 20, 28, 20); layout.setSpacing(14)

        row0 = QHBoxLayout()
        t = QLabel("Fee Exemptions Overview")
        t.setStyleSheet("font-size:20px;font-weight:700;color:#111827;")
        row0.addWidget(t); row0.addStretch()
        layout.addLayout(row0)

        self.sum_lbl = QLabel("")
        self.sum_lbl.setStyleSheet("background:#EDE9FE;color:#4C1D95;border-radius:8px;"
                                   "padding:10px 16px;font-size:13px;font-weight:600;")
        layout.addWidget(self.sum_lbl)

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
        rows = fetch_all("""
            SELECT fw.id, s.first_name||' '||s.last_name AS student,
                   s.admission_no, wr.category,
                   fw.waiver_type, fw.discount_percent,
                   sb.control_number, ay.label AS year,
                   ft.name AS fee_name, sb.amount_due
            FROM fee_waivers fw
            JOIN students s ON s.id=fw.student_id
            LEFT JOIN welfare_records wr ON wr.student_id=fw.student_id
            LEFT JOIN student_bills sb ON sb.id=fw.bill_id
            LEFT JOIN fee_structures fs ON fs.id=sb.fee_structure_id
            LEFT JOIN fee_types ft ON ft.id=fs.fee_type_id
            LEFT JOIN academic_years ay ON ay.id=fw.academic_year_id
            ORDER BY fw.created_at DESC
        """)
        self.table.setRowCount(len(rows))
        total_exempted = 0
        for r, row in enumerate(rows):
            exempt_val = (row["amount_due"] or 0) * (row["discount_percent"] / 100)
            total_exempted += exempt_val
            for c, v in enumerate([
                row["student"], row["admission_no"],
                (row["category"] or "—").replace("_", " ").title(),
                row["waiver_type"].replace("_", " ").title(),
                f"{row['discount_percent']:.0f}%",
                row["control_number"] or "All outstanding",
                row["year"] or "—",
                row["fee_name"] or "—",
                f"{row['amount_due']:,.0f}" if row["amount_due"] else "—",
            ]):
                item = QTableWidgetItem(v)
                if row["discount_percent"] == 100:
                    item.setForeground(QColor("#4C1D95"))
                self.table.setItem(r, c, item)

        self.sum_lbl.setText(
            f"Total exemptions: {len(rows)}   |   "
            f"Total fees waived: TZS {total_exempted:,.0f}"
        )
