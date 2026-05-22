"""Fees & Payments module."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QDialog,
    QFormLayout, QComboBox, QLineEdit, QDoubleSpinBox,
    QMessageBox, QAbstractItemView, QDateEdit, QFrame
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QColor
from database.db import fetch_all, fetch_one, execute
import random, string

BTN_PRIMARY = """QPushButton{background:#DC2626;color:white;border:none;border-radius:7px;
    padding:8px 18px;font-size:13px;font-weight:600;}QPushButton:hover{background:#B91C1C;}"""
BTN_OUTLINE = """QPushButton{background:white;color:#374151;border:1px solid #D1D5DB;
    border-radius:7px;padding:8px 18px;font-size:13px;}QPushButton:hover{background:#F9FAFB;}"""
INPUT = """QLineEdit,QComboBox,QDoubleSpinBox,QDateEdit{
    border:1px solid #D1D5DB;border-radius:6px;padding:6px 10px;
    font-size:13px;background:white;}"""


def gen_receipt():
    return "RCP" + "".join(random.choices(string.digits, k=6))


class PaymentDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Record Payment")
        self.setMinimumWidth(440)
        self.setStyleSheet(INPUT + "QDialog{background:#F9FAFB;}")
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20); layout.setSpacing(14)

        title = QLabel("Record Fee Payment")
        title.setStyleSheet("font-size:16px;font-weight:700;color:#111827;")
        layout.addWidget(title)

        form = QFormLayout(); form.setSpacing(9)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.student_cb = QComboBox()
        for s in fetch_all("SELECT id,admission_no,first_name,last_name FROM students WHERE is_active=1 ORDER BY last_name"):
            self.student_cb.addItem(f"{s['admission_no']} — {s['first_name']} {s['last_name']}", s["id"])

        self.fee_type_cb = QComboBox()
        self.fee_type_cb.addItem("— Select fee type —", None)
        for f in fetch_all("SELECT id,name,amount FROM fee_types ORDER BY name"):
            self.fee_type_cb.addItem(f"{f['name']} (TZS {f['amount']:,.0f})", f["id"])
        self.fee_type_cb.currentIndexChanged.connect(self._auto_amount)

        self.amount = QDoubleSpinBox()
        self.amount.setRange(0, 9_999_999); self.amount.setPrefix("TZS ")
        self.amount.setSingleStep(1000); self.amount.setDecimals(0)

        self.method = QComboBox()
        self.method.addItems(["Cash", "Mobile Money (M-Pesa)", "Bank Transfer", "Cheque"])

        self.date_pick = QDateEdit()
        self.date_pick.setCalendarPopup(True)
        self.date_pick.setDate(QDate.currentDate())
        self.date_pick.setDisplayFormat("dd/MM/yyyy")

        self.receipt = QLineEdit(); self.receipt.setText(gen_receipt())
        self.notes   = QLineEdit(); self.notes.setPlaceholderText("Optional notes")

        for lbl, wgt in [
            ("Student *", self.student_cb), ("Fee type *", self.fee_type_cb),
            ("Amount (TZS) *", self.amount), ("Payment method", self.method),
            ("Payment date", self.date_pick), ("Receipt no", self.receipt),
            ("Notes", self.notes),
        ]:
            l = QLabel(lbl); l.setStyleSheet("font-size:13px;color:#374151;")
            form.addRow(l, wgt)

        layout.addLayout(form)

        row = QHBoxLayout(); row.addStretch()
        c = QPushButton("Cancel"); c.setStyleSheet(BTN_OUTLINE)
        s = QPushButton("Save payment"); s.setStyleSheet(BTN_PRIMARY)
        c.clicked.connect(self.reject); s.clicked.connect(self._save)
        row.addWidget(c); row.addWidget(s)
        layout.addLayout(row)

    def _auto_amount(self):
        fid = self.fee_type_cb.currentData()
        if fid:
            f = fetch_one("SELECT amount FROM fee_types WHERE id=?", (fid,))
            if f: self.amount.setValue(f["amount"])

    def _save(self):
        if not self.fee_type_cb.currentData():
            QMessageBox.warning(self, "Validation", "Please select a fee type."); return
        if self.amount.value() <= 0:
            QMessageBox.warning(self, "Validation", "Amount must be greater than zero."); return

        year = fetch_one("SELECT id FROM academic_years WHERE is_current=1")
        execute("""
            INSERT INTO fee_payments
                (student_id,fee_type_id,academic_year_id,amount_paid,
                 payment_date,receipt_no,payment_method,notes)
            VALUES (?,?,?,?,?,?,?,?)
        """, (
            self.student_cb.currentData(),
            self.fee_type_cb.currentData(),
            year["id"] if year else None,
            self.amount.value(),
            self.date_pick.date().toString("yyyy-MM-dd"),
            self.receipt.text().strip(),
            self.method.currentText(),
            self.notes.text().strip(),
        ))
        self.accept()


class FeeTypeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Fee Type"); self.setMinimumWidth(360)
        self.setStyleSheet(INPUT + "QDialog{background:#F9FAFB;}")
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20); layout.setSpacing(14)
        title = QLabel("New Fee Type")
        title.setStyleSheet("font-size:16px;font-weight:700;color:#111827;")
        layout.addWidget(title)

        form = QFormLayout(); form.setSpacing(9)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.name = QLineEdit(); self.name.setPlaceholderText("e.g. School Fees")
        self.amt  = QDoubleSpinBox(); self.amt.setRange(0,9_999_999)
        self.amt.setPrefix("TZS "); self.amt.setSingleStep(1000); self.amt.setDecimals(0)
        self.desc = QLineEdit()

        for lbl, wgt in [("Name *", self.name), ("Amount", self.amt), ("Description", self.desc)]:
            l = QLabel(lbl); l.setStyleSheet("font-size:13px;color:#374151;")
            form.addRow(l, wgt)
        layout.addLayout(form)

        row = QHBoxLayout(); row.addStretch()
        c = QPushButton("Cancel"); c.setStyleSheet(BTN_OUTLINE)
        s = QPushButton("Add");    s.setStyleSheet(BTN_PRIMARY)
        c.clicked.connect(self.reject); s.clicked.connect(self._save)
        row.addWidget(c); row.addWidget(s)
        layout.addLayout(row)

    def _save(self):
        if not self.name.text().strip():
            QMessageBox.warning(self, "Validation", "Name is required."); return
        execute("INSERT INTO fee_types(name,amount,description) VALUES(?,?,?)",
                (self.name.text().strip(), self.amt.value(), self.desc.text().strip()))
        self.accept()


class FeesWidget(QWidget):
    COLS = ["Receipt", "Student", "Fee Type", "Amount (TZS)", "Method", "Date"]

    def __init__(self):
        super().__init__()
        self._build()
        self.load_table()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24); layout.setSpacing(16)

        row0 = QHBoxLayout()
        t = QLabel("Fees & Payments")
        t.setStyleSheet("font-size:22px;font-weight:700;color:#111827;")
        row0.addWidget(t); row0.addStretch()
        add_fee_type = QPushButton("+ Fee type"); add_fee_type.setStyleSheet(BTN_OUTLINE)
        add_fee_type.clicked.connect(self._add_fee_type)
        add_pay = QPushButton("+ Record payment"); add_pay.setStyleSheet(BTN_PRIMARY)
        add_pay.clicked.connect(self._record_payment)
        row0.addWidget(add_fee_type); row0.addWidget(add_pay)
        layout.addLayout(row0)

        # Summary card
        self.sum_lbl = QLabel("Total this month: TZS 0")
        self.sum_lbl.setStyleSheet("""
            background:#FEF2F2;color:#991B1B;border-radius:8px;
            padding:10px 16px;font-size:14px;font-weight:600;
        """)
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
            QTableWidget::item:selected{background:#FEF2F2;color:#991B1B;}
        """)
        layout.addWidget(self.table)

    def load_table(self):
        rows = fetch_all("""
            SELECT fp.receipt_no, s.first_name||' '||s.last_name AS student,
                   ft.name AS fee_name, fp.amount_paid, fp.payment_method, fp.payment_date
            FROM fee_payments fp
            JOIN students s ON s.id=fp.student_id
            JOIN fee_types ft ON ft.id=fp.fee_type_id
            ORDER BY fp.payment_date DESC LIMIT 200
        """)
        self.table.setRowCount(len(rows))
        total = 0
        for r, row in enumerate(rows):
            total += row["amount_paid"]
            for c, v in enumerate([
                row["receipt_no"] or "—",
                row["student"],
                row["fee_name"],
                f"{row['amount_paid']:,.0f}",
                row["payment_method"],
                row["payment_date"],
            ]):
                self.table.setItem(r, c, QTableWidgetItem(v))

        month_total = fetch_one(
            "SELECT COALESCE(SUM(amount_paid),0) AS t FROM fee_payments "
            "WHERE strftime('%Y-%m',payment_date)=strftime('%Y-%m','now')"
        )
        t = month_total["t"] if month_total else 0
        self.sum_lbl.setText(f"Total collected this month: TZS {t:,.0f}   |   All-time (shown): TZS {total:,.0f}")

    def _record_payment(self):
        if PaymentDialog(self).exec(): self.load_table()

    def _add_fee_type(self):
        FeeTypeDialog(self).exec()
