"""Payments — record fee payments using control numbers."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QDialog,
    QFormLayout, QComboBox, QLineEdit, QDoubleSpinBox,
    QMessageBox, QAbstractItemView, QDateEdit, QFrame
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QColor
from database.db import fetch_all, fetch_one, execute, db_write, gen_receipt_number
from auth.session import session
from utils.pdf_export import print_receipt

BTN_PRIMARY = """QPushButton{background:#DC2626;color:white;border:none;border-radius:7px;
    padding:8px 18px;font-size:13px;font-weight:600;}QPushButton:hover{background:#B91C1C;}"""
BTN_OUTLINE = """QPushButton{background:white;color:#374151;border:1px solid #D1D5DB;
    border-radius:7px;padding:8px 18px;font-size:13px;}QPushButton:hover{background:#F9FAFB;}"""
INPUT = """QLineEdit,QComboBox,QDoubleSpinBox,QDateEdit{
    border:1px solid #D1D5DB;border-radius:6px;padding:6px 10px;font-size:13px;background:white;}"""


class PaymentDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Record Payment")
        self.setMinimumWidth(480)
        self.setStyleSheet(INPUT + "QDialog{background:#F9FAFB;}")
        self._bill = None
        self._saved_receipt = None   # populated after successful save
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20); layout.setSpacing(14)

        title = QLabel("Record Fee Payment")
        title.setStyleSheet("font-size:16px;font-weight:700;color:#111827;")
        layout.addWidget(title)

        # Control number lookup
        lookup_row = QHBoxLayout()
        self.ctrl_input = QLineEdit()
        self.ctrl_input.setPlaceholderText("Enter control number (e.g. SCH-2025-ST0001-T1-001)")
        lookup_btn = QPushButton("Look up")
        lookup_btn.setStyleSheet(BTN_OUTLINE)
        lookup_btn.clicked.connect(self._lookup)
        lookup_row.addWidget(self.ctrl_input, 1); lookup_row.addWidget(lookup_btn)
        layout.addLayout(lookup_row)

        # Bill info card (shown after lookup)
        self.info_card = QFrame()
        self.info_card.setStyleSheet(
            "QFrame{background:#EFF6FF;border:1px solid #BFDBFE;border-radius:8px;padding:4px;}"
        )
        self.info_card.setVisible(False)
        ic = QVBoxLayout(self.info_card); ic.setContentsMargins(14, 10, 14, 10); ic.setSpacing(4)
        self.info_student = QLabel("")
        self.info_student.setStyleSheet("font-size:13px;font-weight:600;color:#1E40AF;")
        self.info_fee     = QLabel("")
        self.info_fee.setStyleSheet("font-size:12px;color:#374151;")
        self.info_balance = QLabel("")
        self.info_balance.setStyleSheet("font-size:12px;color:#374151;")
        ic.addWidget(self.info_student); ic.addWidget(self.info_fee)
        ic.addWidget(self.info_balance)
        layout.addWidget(self.info_card)

        form = QFormLayout(); form.setSpacing(9)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.amount = QDoubleSpinBox()
        self.amount.setRange(0, 9_999_999); self.amount.setPrefix("TZS ")
        self.amount.setSingleStep(1000); self.amount.setDecimals(0)

        self.method = QComboBox()
        self.method.addItems(["Cash", "Mobile Money", "Bank Transfer", "Cheque"])

        self.ref_no = QLineEdit()
        self.ref_no.setPlaceholderText("M-Pesa code, bank ref, cheque no (optional)")

        self.date_pick = QDateEdit(); self.date_pick.setCalendarPopup(True)
        self.date_pick.setDate(QDate.currentDate()); self.date_pick.setDisplayFormat("dd/MM/yyyy")

        self.receipt = QLineEdit(); self.receipt.setText(gen_receipt_number())
        self.notes   = QLineEdit(); self.notes.setPlaceholderText("Optional notes")

        for lbl, wgt in [
            ("Amount (TZS) *", self.amount),
            ("Payment method", self.method),
            ("Reference no", self.ref_no),
            ("Payment date", self.date_pick),
            ("Receipt no", self.receipt),
            ("Notes", self.notes),
        ]:
            l = QLabel(lbl); l.setStyleSheet("font-size:13px;color:#374151;")
            form.addRow(l, wgt)
        layout.addLayout(form)

        row = QHBoxLayout(); row.addStretch()
        c = QPushButton("Cancel"); c.setStyleSheet(BTN_OUTLINE)
        s = QPushButton("Save payment"); s.setStyleSheet(BTN_PRIMARY)
        self.print_btn = QPushButton("Save + Print Receipt"); self.print_btn.setStyleSheet(BTN_PRIMARY)
        c.clicked.connect(self.reject)
        s.clicked.connect(lambda: self._save(print_after=False))
        self.print_btn.clicked.connect(lambda: self._save(print_after=True))
        row.addWidget(c); row.addWidget(s); row.addWidget(self.print_btn)
        layout.addLayout(row)

    def _lookup(self):
        ctrl = self.ctrl_input.text().strip()
        if not ctrl:
            QMessageBox.warning(self, "Required", "Enter a control number."); return

        bill = fetch_one("""
            SELECT sb.*, s.first_name||' '||s.last_name AS student,
                   s.admission_no, ft.name AS fee_name
            FROM student_bills sb
            JOIN students s ON s.id=sb.student_id
            JOIN fee_structures fs ON fs.id=sb.fee_structure_id
            JOIN fee_types ft ON ft.id=fs.fee_type_id
            WHERE sb.control_number=?
        """, (ctrl,))

        if not bill:
            QMessageBox.warning(self, "Not Found",
                f"No bill found for control number:\n{ctrl}"); return

        if bill["status"] == "paid":
            QMessageBox.information(self, "Already Paid",
                f"This bill is already fully paid.\nReceipt already issued."); return

        if bill["status"] == "waived":
            QMessageBox.information(self, "Waived",
                "This bill has been waived (student is exempt from this fee)."); return

        self._bill = dict(bill)
        balance = bill["amount_due"] - bill["amount_paid"] - bill["discount_amount"]
        self.info_student.setText(f"Student: {bill['student']} ({bill['admission_no']})")
        self.info_fee.setText(f"Fee: {bill['fee_name']}   |   Total due: TZS {bill['amount_due']:,.0f}")
        self.info_balance.setText(
            f"Paid so far: TZS {bill['amount_paid']:,.0f}   |   "
            f"Balance: TZS {max(balance,0):,.0f}"
        )
        self.info_card.setVisible(True)
        self.amount.setValue(max(balance, 0))

    def _save(self, print_after=False):
        if not self._bill:
            QMessageBox.warning(self, "No Bill", "Look up a control number first."); return
        if self.amount.value() <= 0:
            QMessageBox.warning(self, "Validation", "Amount must be greater than zero."); return

        bill = self._bill
        new_paid   = bill["amount_paid"] + self.amount.value()
        new_status = "paid" if new_paid >= (bill["amount_due"] - bill["discount_amount"]) else "partial"
        receipt_no = self.receipt.text().strip()
        pay_date   = self.date_pick.date().toString("yyyy-MM-dd")

        db_write(
            """INSERT INTO fee_payments
                (bill_id, student_id, academic_year_id, amount_paid,
                 payment_date, control_number, receipt_no,
                 payment_method, reference_no, notes, recorded_by)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (bill["id"], bill["student_id"], bill["academic_year_id"],
             self.amount.value(), pay_date, bill["control_number"],
             receipt_no, self.method.currentText(),
             self.ref_no.text().strip(), self.notes.text().strip(),
             session.user_id),
            action="payment_recorded", table="fee_payments",
            detail=f"Receipt {receipt_no} TZS {self.amount.value():,.0f}",
            user_id=session.user_id,
            after_state={
                "receipt_no": receipt_no, "amount": self.amount.value(),
                "method": self.method.currentText(), "status": new_status,
            }
        )

        execute("UPDATE student_bills SET amount_paid=?, status=? WHERE id=?",
                (new_paid, new_status, bill["id"]))

        if print_after:
            # Fetch class name for receipt
            cls_row = fetch_one(
                "SELECT c.name FROM students s LEFT JOIN classes c ON c.id=s.class_id"
                " WHERE s.id=?", (bill["student_id"],)
            )
            self._saved_receipt = {
                "receipt_no":    receipt_no,
                "control_number": bill["control_number"],
                "student":       self.info_student.text().replace("Student: ", "").split(" (")[0],
                "admission_no":  bill.get("admission_no", ""),
                "class_name":    cls_row["name"] if cls_row else "—",
                "fee_name":      bill.get("fee_name", ""),
                "amount_paid":   self.amount.value(),
                "amount_due":    bill["amount_due"],
                "discount_amount": bill["discount_amount"],
                "payment_method": self.method.currentText(),
                "reference_no":  self.ref_no.text().strip(),
                "payment_date":  pay_date,
                "recorded_by":   session.full_name,
                "balance":       max(bill["amount_due"] - new_paid - bill["discount_amount"], 0),
                "status":        new_status,
            }

        self.accept()


class PaymentsWidget(QWidget):
    COLS = ["Receipt", "Control No", "Student", "Amount (TZS)", "Method", "Ref No", "Date", "Recorded By"]

    def __init__(self):
        super().__init__()
        self._rows_data = []
        self._build()
        self.load_table()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 20, 28, 20); layout.setSpacing(14)

        row0 = QHBoxLayout()
        t = QLabel("Fee Payments")
        t.setStyleSheet("font-size:20px;font-weight:700;color:#111827;")
        row0.addWidget(t); row0.addStretch()
        reprint = QPushButton("Reprint Receipt"); reprint.setStyleSheet(BTN_OUTLINE)
        reprint.clicked.connect(self._reprint)
        add = QPushButton("+ Record Payment"); add.setStyleSheet(BTN_PRIMARY)
        add.clicked.connect(self._record)
        row0.addWidget(reprint); row0.addWidget(add)
        layout.addLayout(row0)

        self.sum_lbl = QLabel("")
        self.sum_lbl.setStyleSheet("background:#FEF2F2;color:#991B1B;border-radius:8px;"
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
            QTableWidget::item:selected{background:#FEF2F2;color:#991B1B;}
        """)
        layout.addWidget(self.table)

    def load_table(self):
        rows = fetch_all("""
            SELECT fp.receipt_no, fp.control_number,
                   s.first_name||' '||s.last_name AS student,
                   s.admission_no,
                   fp.amount_paid, fp.payment_method, fp.reference_no,
                   fp.payment_date, u.full_name AS recorder,
                   sb.amount_due, sb.discount_amount, sb.status AS bill_status,
                   ft.name AS fee_name,
                   c.name AS class_name
            FROM fee_payments fp
            JOIN students s ON s.id=fp.student_id
            LEFT JOIN users u ON u.id=fp.recorded_by
            LEFT JOIN student_bills sb ON sb.id=fp.bill_id
            LEFT JOIN fee_structures fs ON fs.id=sb.fee_structure_id
            LEFT JOIN fee_types ft ON ft.id=fs.fee_type_id
            LEFT JOIN classes c ON c.id=s.class_id
            ORDER BY fp.payment_date DESC LIMIT 500
        """)
        self._rows_data = [dict(r) for r in rows]
        self.table.setRowCount(len(rows))
        total = 0
        for r, row in enumerate(rows):
            total += row["amount_paid"]
            for c, v in enumerate([
                row["receipt_no"] or "—",
                row["control_number"] or "—",
                row["student"],
                f"{row['amount_paid']:,.0f}",
                row["payment_method"],
                row["reference_no"] or "—",
                row["payment_date"],
                row["recorder"] or "—",
            ]):
                self.table.setItem(r, c, QTableWidgetItem(v))

        month = fetch_one(
            "SELECT COALESCE(SUM(amount_paid),0) AS t FROM fee_payments "
            "WHERE strftime('%Y-%m',payment_date)=strftime('%Y-%m','now')"
        )
        mt = month["t"] if month else 0
        self.sum_lbl.setText(
            f"This month: TZS {mt:,.0f}   |   Shown total: TZS {total:,.0f}   |   Transactions: {len(rows)}"
        )

    def _reprint(self):
        idx = self.table.currentRow()
        if idx < 0 or idx >= len(self._rows_data):
            QMessageBox.information(self, "Select Row", "Select a payment row to reprint."); return
        row = self._rows_data[idx]
        amount_due = row.get("amount_due") or 0
        amount_paid = row.get("amount_paid") or 0
        discount = row.get("discount_amount") or 0
        data = {
            "receipt_no":      row["receipt_no"] or "—",
            "control_number":  row["control_number"] or "—",
            "student":         row["student"],
            "admission_no":    row["admission_no"],
            "class_name":      row.get("class_name") or "—",
            "fee_name":        row.get("fee_name") or "—",
            "amount_paid":     amount_paid,
            "amount_due":      amount_due,
            "discount_amount": discount,
            "payment_method":  row["payment_method"],
            "reference_no":    row["reference_no"] or "—",
            "payment_date":    row["payment_date"],
            "recorded_by":     row["recorder"] or "—",
            "balance":         max(amount_due - amount_paid - discount, 0),
            "status":          row.get("bill_status") or "—",
        }
        print_receipt(self, data)

    def _record(self):
        dlg = PaymentDialog(self)
        if dlg.exec():
            self.load_table()
            if dlg._saved_receipt:
                print_receipt(self, dlg._saved_receipt)
