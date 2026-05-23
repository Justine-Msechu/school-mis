"""Billing — generate student bills from fee structures, view balances."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QMessageBox, QAbstractItemView
)
from PyQt6.QtGui import QColor
from database.db import fetch_all, fetch_one
from services.finance_service import finance_service
from services.base import ServiceError, PolicyViolation

BTN_PRIMARY = """QPushButton{background:#DC2626;color:white;border:none;border-radius:7px;
    padding:8px 18px;font-size:13px;font-weight:600;}QPushButton:hover{background:#B91C1C;}"""
BTN_OUTLINE = """QPushButton{background:white;color:#374151;border:1px solid #D1D5DB;
    border-radius:7px;padding:8px 18px;font-size:13px;}QPushButton:hover{background:#F9FAFB;}"""
INPUT = "QComboBox{border:1px solid #D1D5DB;border-radius:6px;padding:6px 10px;font-size:13px;background:white;}"

STATUS_COLORS = {
    "paid":    ("#D1FAE5", "#065F46"),
    "partial": ("#FEF3C7", "#92400E"),
    "unpaid":  ("#FEE2E2", "#991B1B"),
    "waived":  ("#EDE9FE", "#4C1D95"),
}


class BillingWidget(QWidget):
    COLS = ["Control No", "Student", "Adm No", "Fee Type", "Due", "Paid", "Balance", "Status"]

    def __init__(self):
        super().__init__()
        self._build()
        self.load_table()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 20, 28, 20); layout.setSpacing(14)

        row0 = QHBoxLayout()
        t = QLabel("Student Billing")
        t.setStyleSheet("font-size:20px;font-weight:700;color:#111827;")
        row0.addWidget(t); row0.addStretch()

        run_btn = QPushButton("Run Billing for Current Year")
        run_btn.setStyleSheet(BTN_PRIMARY)
        run_btn.clicked.connect(self._run_billing)
        row0.addWidget(run_btn)
        layout.addLayout(row0)

        # Filters
        bar = QHBoxLayout(); bar.setSpacing(12)
        self.year_cb = QComboBox(); self.year_cb.setStyleSheet(INPUT)
        self.year_cb.addItem("All years", None)
        for y in fetch_all("SELECT id,label FROM academic_years ORDER BY id DESC"):
            self.year_cb.addItem(y["label"], y["id"])
        self.year_cb.currentIndexChanged.connect(self.load_table)

        self.status_cb = QComboBox(); self.status_cb.setStyleSheet(INPUT)
        self.status_cb.addItems(["All", "unpaid", "partial", "paid", "waived"])
        self.status_cb.currentIndexChanged.connect(self.load_table)

        bar.addWidget(QLabel("Year:")); bar.addWidget(self.year_cb)
        bar.addWidget(QLabel("Status:")); bar.addWidget(self.status_cb)
        bar.addStretch()
        layout.addLayout(bar)

        # Summary strip
        self.sum_lbl = QLabel("")
        self.sum_lbl.setStyleSheet("background:#FEF2F2;color:#991B1B;border-radius:8px;"
                                   "padding:10px 16px;font-size:13px;font-weight:600;")
        layout.addWidget(self.sum_lbl)

        self.table = QTableWidget()
        self.table.setColumnCount(len(self.COLS))
        self.table.setHorizontalHeaderLabels(self.COLS)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
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
        year_id = self.year_cb.currentData()
        status_txt = self.status_cb.currentText()

        sql = """
            SELECT sb.id, sb.control_number,
                   s.first_name||' '||s.last_name AS student,
                   s.admission_no, ft.name AS fee_name,
                   sb.amount_due, sb.amount_paid, sb.discount_amount, sb.status
            FROM student_bills sb
            JOIN students s ON s.id=sb.student_id
            JOIN fee_structures fs ON fs.id=sb.fee_structure_id
            JOIN fee_types ft ON ft.id=fs.fee_type_id
            WHERE 1=1
        """
        params = []
        if year_id:
            sql += " AND sb.academic_year_id=?"
            params.append(year_id)
        if status_txt != "All":
            sql += " AND sb.status=?"
            params.append(status_txt)
        sql += " ORDER BY sb.status, s.last_name"

        rows = fetch_all(sql, params)
        self.table.setRowCount(len(rows))
        self._ids = []

        total_due = total_paid = total_bal = 0
        for r, row in enumerate(rows):
            self._ids.append(row["id"])
            bal = row["amount_due"] - row["amount_paid"] - row["discount_amount"]
            total_due  += row["amount_due"]
            total_paid += row["amount_paid"]
            total_bal  += max(bal, 0)
            bg, fg = STATUS_COLORS.get(row["status"], ("#FFFFFF", "#111827"))
            for c, v in enumerate([
                row["control_number"],
                row["student"],
                row["admission_no"],
                row["fee_name"],
                f"{row['amount_due']:,.0f}",
                f"{row['amount_paid']:,.0f}",
                f"{max(bal,0):,.0f}",
                row["status"].upper(),
            ]):
                item = QTableWidgetItem(v)
                item.setBackground(QColor(bg)); item.setForeground(QColor(fg))
                self.table.setItem(r, c, item)

        self.sum_lbl.setText(
            f"Total billed: TZS {total_due:,.0f}   |   "
            f"Collected: TZS {total_paid:,.0f}   |   "
            f"Outstanding: TZS {total_bal:,.0f}   |   "
            f"Bills: {len(rows)}"
        )

    def _run_billing(self):
        year = fetch_one("SELECT * FROM academic_years WHERE is_current=1")
        if not year:
            QMessageBox.warning(self, "No Year", "No current academic year set."); return

        count = fetch_one(
            "SELECT COUNT(*) AS n FROM fee_structures WHERE academic_year_id=?", (year["id"],)
        )
        if not count or count["n"] == 0:
            QMessageBox.information(self, "No Structures",
                "No fee structures found for the current year.\n"
                "Add fee structures first."); return

        reply = QMessageBox.question(
            self, "Run Billing",
            f"Generate bills for all active students under '{year['label']}'?\n"
            "Orphan/welfare-exempt students will be automatically waived.\n"
            "Existing bills will not be duplicated.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            result = finance_service.run_billing(year["id"])
        except (ServiceError, PolicyViolation) as e:
            QMessageBox.warning(self, "Billing Error", str(e)); return

        self.load_table()
        QMessageBox.information(
            self, "Billing Complete",
            f"Bills created: {result['billed']}\n"
            f"Auto-waived (orphan/exempt): {result['waived']}\n"
            f"Already existed (skipped): {result['skipped']}"
        )
