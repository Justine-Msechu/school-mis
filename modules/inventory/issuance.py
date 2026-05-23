"""Issuance — issue stock items to students after verifying payment."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QDialog,
    QFormLayout, QComboBox, QLineEdit, QSpinBox,
    QMessageBox, QAbstractItemView, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from database.db import fetch_all, fetch_one, execute, db_write
from auth.session import session

BTN_PRIMARY = """QPushButton{background:#D97706;color:white;border:none;border-radius:7px;
    padding:8px 18px;font-size:13px;font-weight:600;}QPushButton:hover{background:#B45309;}"""
BTN_OUTLINE = """QPushButton{background:white;color:#374151;border:1px solid #D1D5DB;
    border-radius:7px;padding:8px 18px;font-size:13px;}QPushButton:hover{background:#F9FAFB;}"""
INPUT = """QLineEdit,QComboBox,QSpinBox{
    border:1px solid #D1D5DB;border-radius:6px;padding:6px 10px;font-size:13px;background:white;}"""


class IssueDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Issue Item to Student")
        self.setMinimumWidth(500)
        self.setStyleSheet(INPUT + "QDialog{background:#F9FAFB;}")
        self._student = None
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20); layout.setSpacing(14)
        title = QLabel("Issue Stock Item to Student")
        title.setStyleSheet("font-size:16px;font-weight:700;color:#111827;")
        layout.addWidget(title)

        # Student lookup by admission no or control number
        lookup_row = QHBoxLayout()
        self.adm_input = QLineEdit()
        self.adm_input.setPlaceholderText("Enter admission number or control number")
        lookup_btn = QPushButton("Look up")
        lookup_btn.setStyleSheet(BTN_OUTLINE)
        lookup_btn.clicked.connect(self._lookup_student)
        lookup_row.addWidget(self.adm_input, 1); lookup_row.addWidget(lookup_btn)
        layout.addLayout(lookup_row)

        # Student payment status card
        self.status_card = QFrame()
        self.status_card.setVisible(False)
        self.status_card.setStyleSheet(
            "QFrame{border:1px solid #E5E7EB;border-radius:8px;background:white;}"
        )
        sc = QVBoxLayout(self.status_card); sc.setContentsMargins(14, 10, 14, 10)
        self.status_student  = QLabel("")
        self.status_student.setStyleSheet("font-size:13px;font-weight:700;color:#111827;")
        self.status_balance  = QLabel("")
        self.status_balance.setStyleSheet("font-size:12px;color:#374151;")
        self.status_welfare  = QLabel("")
        self.status_welfare.setStyleSheet("font-size:12px;color:#7C3AED;")
        sc.addWidget(self.status_student); sc.addWidget(self.status_balance)
        sc.addWidget(self.status_welfare)
        layout.addWidget(self.status_card)

        form = QFormLayout(); form.setSpacing(9)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.item_cb = QComboBox()
        self._fill_items()

        self.qty = QSpinBox(); self.qty.setRange(1, 999); self.qty.setValue(1)
        self.notes = QLineEdit(); self.notes.setPlaceholderText("Optional notes")

        for lbl, wgt in [
            ("Item *", self.item_cb), ("Quantity", self.qty), ("Notes", self.notes)
        ]:
            l = QLabel(lbl); l.setStyleSheet("font-size:13px;color:#374151;")
            form.addRow(l, wgt)
        layout.addLayout(form)

        row = QHBoxLayout(); row.addStretch()
        c = QPushButton("Cancel"); c.setStyleSheet(BTN_OUTLINE)
        self.issue_btn = QPushButton("Issue Item"); self.issue_btn.setStyleSheet(BTN_PRIMARY)
        self.issue_btn.setEnabled(False)
        c.clicked.connect(self.reject); self.issue_btn.clicked.connect(self._issue)
        row.addWidget(c); row.addWidget(self.issue_btn)
        layout.addLayout(row)

    def _fill_items(self):
        self.item_cb.clear()
        self.item_cb.addItem("-- Select item --", None)
        for it in fetch_all(
            "SELECT id,name,stock_qty,unit FROM inventory_items WHERE is_active=1 AND stock_qty>0"
        ):
            self.item_cb.addItem(f"{it['name']} ({it['stock_qty']} {it['unit']} in stock)", it["id"])

    def _lookup_student(self):
        ref = self.adm_input.text().strip()
        if not ref:
            QMessageBox.warning(self, "Required", "Enter an admission number or control number."); return

        # Try by admission number first, then control number
        student = fetch_one(
            "SELECT * FROM students WHERE admission_no=? AND is_active=1", (ref,)
        )
        if not student:
            bill = fetch_one(
                "SELECT sb.*, s.* FROM student_bills sb "
                "JOIN students s ON s.id=sb.student_id WHERE sb.control_number=?", (ref,)
            )
            if bill:
                student = fetch_one("SELECT * FROM students WHERE id=?", (bill["student_id"],))

        if not student:
            QMessageBox.warning(self, "Not Found",
                f"No student found for: {ref}"); return

        self._student = dict(student)

        # Check welfare status
        welfare = fetch_one(
            "SELECT * FROM welfare_records WHERE student_id=?", (student["id"],)
        )
        is_exempt = (
            student["student_category"] == "orphan" or
            (welfare and welfare["support_type"] == "full_fees")
        )

        # Check payment status
        unpaid_bills = fetch_all(
            "SELECT COUNT(*) AS n FROM student_bills "
            "WHERE student_id=? AND status IN ('unpaid','partial')", (student["id"],)
        )
        unpaid_count = unpaid_bills[0]["n"] if unpaid_bills else 0

        self.status_student.setText(
            f"Student: {student['first_name']} {student['last_name']} ({student['admission_no']})"
        )

        if is_exempt:
            self.status_balance.setText("Fee status: EXEMPT (orphan/welfare waiver)")
            self.status_balance.setStyleSheet("font-size:12px;color:#059669;font-weight:600;")
            self.status_card.setStyleSheet(
                "QFrame{border:1px solid #A7F3D0;border-radius:8px;background:#ECFDF5;}"
            )
            self.issue_btn.setEnabled(True)
        elif unpaid_count == 0:
            self.status_balance.setText("Fee status: All bills paid")
            self.status_balance.setStyleSheet("font-size:12px;color:#059669;font-weight:600;")
            self.status_card.setStyleSheet(
                "QFrame{border:1px solid #A7F3D0;border-radius:8px;background:#ECFDF5;}"
            )
            self.issue_btn.setEnabled(True)
        else:
            self.status_balance.setText(
                f"Fee status: {unpaid_count} unpaid/partial bill(s) outstanding — issuance BLOCKED"
            )
            self.status_balance.setStyleSheet("font-size:12px;color:#991B1B;font-weight:600;")
            self.status_card.setStyleSheet(
                "QFrame{border:1px solid #FECACA;border-radius:8px;background:#FEF2F2;}"
            )
            self.issue_btn.setEnabled(False)

        if welfare:
            self.status_welfare.setText(
                f"Welfare: {welfare['category'].replace('_',' ').title()} — "
                f"{welfare['support_type'].replace('_',' ').title()}"
            )
        else:
            self.status_welfare.setText("")

        self.status_card.setVisible(True)
        self._fill_items()

    def _issue(self):
        if not self._student:
            QMessageBox.warning(self, "No Student", "Look up a student first."); return
        item_id = self.item_cb.currentData()
        if not item_id:
            QMessageBox.warning(self, "Required", "Select an item."); return
        qty = self.qty.value()

        it = fetch_one("SELECT name, stock_qty FROM inventory_items WHERE id=?", (item_id,))
        if it["stock_qty"] < qty:
            QMessageBox.warning(self, "Insufficient Stock",
                f"Only {it['stock_qty']} in stock. Cannot issue {qty}."); return

        db_write(
            "INSERT INTO inventory_transactions(item_id,type,qty,student_id,notes,recorded_by)"
            " VALUES(?,?,?,?,?,?)",
            (item_id, "issued", qty, self._student["id"],
             self.notes.text().strip(), session.user_id),
            action="item_issued", table="inventory_transactions",
            detail=f"Issued {qty}x {it['name']} to student {self._student['admission_no']}",
            user_id=session.user_id
        )
        execute(
            "UPDATE inventory_items SET stock_qty=stock_qty-? WHERE id=?",
            (qty, item_id)
        )
        self.accept()


class IssuanceWidget(QWidget):
    COLS = ["Date", "Student", "Adm No", "Item", "Qty", "Type", "Notes", "Issued By"]

    def __init__(self):
        super().__init__()
        self._build()
        self.load_table()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 20, 28, 20); layout.setSpacing(14)

        row0 = QHBoxLayout()
        t = QLabel("Item Issuance Log")
        t.setStyleSheet("font-size:20px;font-weight:700;color:#111827;")
        row0.addWidget(t); row0.addStretch()
        issue_btn = QPushButton("+ Issue Item"); issue_btn.setStyleSheet(BTN_PRIMARY)
        issue_btn.clicked.connect(self._issue)
        row0.addWidget(issue_btn)
        layout.addLayout(row0)

        info = QLabel(
            "Students with outstanding unpaid fees are blocked from receiving items. "
            "Orphan/exempt students always pass the check."
        )
        info.setWordWrap(True)
        info.setStyleSheet("background:#FEF3C7;color:#92400E;border-radius:8px;"
                           "padding:10px 14px;font-size:12px;")
        layout.addWidget(info)

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
            QTableWidget::item:selected{background:#FEF3C7;color:#92400E;}
        """)
        layout.addWidget(self.table)

    def load_table(self):
        rows = fetch_all("""
            SELECT it.created_at, s.first_name||' '||s.last_name AS student,
                   s.admission_no, ii.name AS item_name,
                   it.qty, it.type, it.notes, u.full_name AS recorder
            FROM inventory_transactions it
            JOIN inventory_items ii ON ii.id=it.item_id
            LEFT JOIN students s ON s.id=it.student_id
            LEFT JOIN users u ON u.id=it.recorded_by
            WHERE it.type IN ('issued','returned')
            ORDER BY it.created_at DESC LIMIT 300
        """)
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, v in enumerate([
                (row["created_at"] or "")[:10],
                row["student"] or "—",
                row["admission_no"] or "—",
                row["item_name"],
                str(row["qty"]),
                row["type"].title(),
                row["notes"] or "—",
                row["recorder"] or "—",
            ]):
                item = QTableWidgetItem(v)
                if row["type"] == "returned":
                    item.setForeground(QColor("#9CA3AF"))
                self.table.setItem(r, c, item)

    def _issue(self):
        if IssueDialog(self).exec(): self.load_table()
