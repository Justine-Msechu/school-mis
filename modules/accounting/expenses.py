"""Expenses — record and view school/NGO expenses."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QDialog,
    QFormLayout, QComboBox, QLineEdit, QDoubleSpinBox, QDateEdit,
    QMessageBox, QAbstractItemView
)
from PyQt6.QtCore import Qt, QDate
from database.db import fetch_all, fetch_one, execute, db_write
from auth.session import session

BTN_PRIMARY = """QPushButton{background:#059669;color:white;border:none;border-radius:7px;
    padding:8px 18px;font-size:13px;font-weight:600;}QPushButton:hover{background:#047857;}"""
BTN_OUTLINE = """QPushButton{background:white;color:#374151;border:1px solid #D1D5DB;
    border-radius:7px;padding:8px 18px;font-size:13px;}QPushButton:hover{background:#F9FAFB;}"""
INPUT = """QLineEdit,QComboBox,QDoubleSpinBox,QDateEdit{
    border:1px solid #D1D5DB;border-radius:6px;padding:6px 10px;font-size:13px;background:white;}"""

EXPENSE_CATEGORIES = ["salaries", "utilities", "supplies", "maintenance", "transport", "welfare", "other"]


class ExpenseDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Record Expense")
        self.setMinimumWidth(440)
        self.setStyleSheet(INPUT + "QDialog{background:#F9FAFB;}")
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20); layout.setSpacing(14)
        title = QLabel("Record Expense")
        title.setStyleSheet("font-size:16px;font-weight:700;color:#111827;")
        layout.addWidget(title)

        form = QFormLayout(); form.setSpacing(9)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.cat_cb = QComboBox(); self.cat_cb.addItems(EXPENSE_CATEGORIES)
        self.desc = QLineEdit(); self.desc.setPlaceholderText("Description of expense")
        self.amount = QDoubleSpinBox()
        self.amount.setRange(0, 99_999_999); self.amount.setPrefix("TZS ")
        self.amount.setSingleStep(1000); self.amount.setDecimals(0)
        self.date_pick = QDateEdit(); self.date_pick.setCalendarPopup(True)
        self.date_pick.setDate(QDate.currentDate()); self.date_pick.setDisplayFormat("dd/MM/yyyy")
        self.receipt_ref = QLineEdit(); self.receipt_ref.setPlaceholderText("Receipt / voucher number")

        for lbl, wgt in [
            ("Category *", self.cat_cb), ("Description *", self.desc),
            ("Amount (TZS) *", self.amount), ("Date", self.date_pick),
            ("Receipt ref", self.receipt_ref),
        ]:
            l = QLabel(lbl); l.setStyleSheet("font-size:13px;color:#374151;")
            form.addRow(l, wgt)
        layout.addLayout(form)

        row = QHBoxLayout(); row.addStretch()
        c = QPushButton("Cancel"); c.setStyleSheet(BTN_OUTLINE)
        s = QPushButton("Save expense"); s.setStyleSheet(BTN_PRIMARY)
        c.clicked.connect(self.reject); s.clicked.connect(self._save)
        row.addWidget(c); row.addWidget(s)
        layout.addLayout(row)

    def _save(self):
        if not self.desc.text().strip():
            QMessageBox.warning(self, "Required", "Description is required."); return
        if self.amount.value() <= 0:
            QMessageBox.warning(self, "Required", "Amount must be greater than zero."); return

        db_write(
            """INSERT INTO expenses(category,description,amount,expense_date,receipt_ref,recorded_by)
               VALUES(?,?,?,?,?,?)""",
            (self.cat_cb.currentText(), self.desc.text().strip(),
             self.amount.value(), self.date_pick.date().toString("yyyy-MM-dd"),
             self.receipt_ref.text().strip(), session.user_id),
            action="expense_recorded", table="expenses",
            detail=f"{self.cat_cb.currentText()} TZS {self.amount.value():,.0f}",
            user_id=session.user_id
        )
        self.accept()


class ExpensesWidget(QWidget):
    COLS = ["Date", "Category", "Description", "Amount (TZS)", "Receipt Ref", "Recorded By"]

    def __init__(self):
        super().__init__()
        self._build()
        self.load_table()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 20, 28, 20); layout.setSpacing(14)

        row0 = QHBoxLayout()
        t = QLabel("Expenses")
        t.setStyleSheet("font-size:20px;font-weight:700;color:#111827;")
        row0.addWidget(t); row0.addStretch()
        add = QPushButton("+ Record Expense"); add.setStyleSheet(BTN_PRIMARY)
        add.clicked.connect(self._add)
        row0.addWidget(add)
        layout.addLayout(row0)

        self.sum_lbl = QLabel("")
        self.sum_lbl.setStyleSheet("background:#ECFDF5;color:#065F46;border-radius:8px;"
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
            QTableWidget::item:selected{background:#ECFDF5;color:#065F46;}
        """)
        layout.addWidget(self.table)

    def load_table(self):
        rows = fetch_all("""
            SELECT e.expense_date, e.category, e.description, e.amount,
                   e.receipt_ref, u.full_name AS recorder
            FROM expenses e LEFT JOIN users u ON u.id=e.recorded_by
            ORDER BY e.expense_date DESC LIMIT 500
        """)
        self.table.setRowCount(len(rows))
        total = 0
        for r, row in enumerate(rows):
            total += row["amount"]
            for c, v in enumerate([
                row["expense_date"], row["category"].title(),
                row["description"], f"{row['amount']:,.0f}",
                row["receipt_ref"] or "—", row["recorder"] or "—",
            ]):
                self.table.setItem(r, c, QTableWidgetItem(v))

        month = fetch_one(
            "SELECT COALESCE(SUM(amount),0) AS t FROM expenses "
            "WHERE strftime('%Y-%m',expense_date)=strftime('%Y-%m','now')"
        )
        mt = month["t"] if month else 0
        self.sum_lbl.setText(
            f"This month: TZS {mt:,.0f}   |   Shown total: TZS {total:,.0f}"
        )

    def _add(self):
        if ExpenseDialog(self).exec(): self.load_table()
