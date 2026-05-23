"""Waivers — manage fee discounts and exemptions."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QDialog,
    QFormLayout, QComboBox, QDoubleSpinBox, QLineEdit,
    QMessageBox, QAbstractItemView
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from database.db import fetch_all, fetch_one, execute, db_write
from auth.session import session

BTN_PRIMARY = """QPushButton{background:#7C3AED;color:white;border:none;border-radius:7px;
    padding:8px 18px;font-size:13px;font-weight:600;}QPushButton:hover{background:#6D28D9;}"""
BTN_DANGER = """QPushButton{background:#EF4444;color:white;border:none;border-radius:7px;
    padding:8px 18px;font-size:13px;font-weight:600;}QPushButton:hover{background:#DC2626;}"""
BTN_OUTLINE = """QPushButton{background:white;color:#374151;border:1px solid #D1D5DB;
    border-radius:7px;padding:8px 18px;font-size:13px;}QPushButton:hover{background:#F9FAFB;}"""
INPUT = """QLineEdit,QComboBox,QDoubleSpinBox{
    border:1px solid #D1D5DB;border-radius:6px;padding:6px 10px;font-size:13px;background:white;}"""

WAIVER_TYPES = ["orphan_exemption", "scholarship", "partial_discount", "staff_child", "other"]


class WaiverDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Waiver / Discount")
        self.setMinimumWidth(460)
        self.setStyleSheet(INPUT + "QDialog{background:#F9FAFB;}")
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20); layout.setSpacing(14)
        title = QLabel("Fee Waiver / Discount")
        title.setStyleSheet("font-size:16px;font-weight:700;color:#111827;")
        layout.addWidget(title)

        form = QFormLayout(); form.setSpacing(9)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.student_cb = QComboBox()
        for s in fetch_all(
            "SELECT id,admission_no,first_name,last_name FROM students WHERE is_active=1 ORDER BY last_name"
        ):
            self.student_cb.addItem(
                f"{s['admission_no']} — {s['first_name']} {s['last_name']}", s["id"]
            )
        self.student_cb.currentIndexChanged.connect(self._load_bills)

        self.bill_cb = QComboBox()
        self.bill_cb.addItem("Blanket waiver (all bills)", None)

        self.year_cb = QComboBox()
        for y in fetch_all("SELECT id,label FROM academic_years ORDER BY id DESC"):
            self.year_cb.addItem(y["label"], y["id"])

        self.type_cb = QComboBox()
        self.type_cb.addItems(WAIVER_TYPES)

        self.pct = QDoubleSpinBox()
        self.pct.setRange(1, 100); self.pct.setValue(100)
        self.pct.setSuffix(" %"); self.pct.setDecimals(0)

        self.reason = QLineEdit()
        self.reason.setPlaceholderText("Reason for waiver")

        for lbl, wgt in [
            ("Student *", self.student_cb),
            ("Specific bill", self.bill_cb),
            ("Academic year", self.year_cb),
            ("Waiver type *", self.type_cb),
            ("Discount %", self.pct),
            ("Reason", self.reason),
        ]:
            l = QLabel(lbl); l.setStyleSheet("font-size:13px;color:#374151;")
            form.addRow(l, wgt)
        layout.addLayout(form)

        self._load_bills()

        row = QHBoxLayout(); row.addStretch()
        c = QPushButton("Cancel"); c.setStyleSheet(BTN_OUTLINE)
        s = QPushButton("Apply Waiver"); s.setStyleSheet(BTN_PRIMARY)
        c.clicked.connect(self.reject); s.clicked.connect(self._save)
        row.addWidget(c); row.addWidget(s)
        layout.addLayout(row)

    def _load_bills(self):
        self.bill_cb.clear()
        self.bill_cb.addItem("Blanket waiver (all outstanding bills)", None)
        sid = self.student_cb.currentData()
        if sid:
            for b in fetch_all(
                """SELECT sb.id, sb.control_number, ft.name AS fee_name, sb.amount_due
                   FROM student_bills sb
                   JOIN fee_structures fs ON fs.id=sb.fee_structure_id
                   JOIN fee_types ft ON ft.id=fs.fee_type_id
                   WHERE sb.student_id=? AND sb.status IN ('unpaid','partial')""",
                (sid,)
            ):
                self.bill_cb.addItem(
                    f"{b['control_number']} — {b['fee_name']} TZS {b['amount_due']:,.0f}",
                    b["id"]
                )

    def _save(self):
        sid = self.student_cb.currentData()
        if not sid:
            QMessageBox.warning(self, "Required", "Select a student."); return

        bill_id = self.bill_cb.currentData()
        pct = self.pct.value()

        execute(
            """INSERT INTO fee_waivers
                (student_id, bill_id, academic_year_id, waiver_type,
                 discount_percent, approved_by, reason)
               VALUES (?,?,?,?,?,?,?)""",
            (sid, bill_id, self.year_cb.currentData(),
             self.type_cb.currentText(), pct,
             session.user_id, self.reason.text().strip())
        )

        # Apply to specific bill or all outstanding bills
        if bill_id:
            bills_to_update = [bill_id]
        else:
            bills_to_update = [
                b["id"] for b in fetch_all(
                    "SELECT id, amount_due, amount_paid FROM student_bills "
                    "WHERE student_id=? AND status IN ('unpaid','partial')", (sid,)
                )
            ]

        for bid in bills_to_update:
            b = fetch_one("SELECT amount_due, amount_paid FROM student_bills WHERE id=?", (bid,))
            if not b: continue
            discount = b["amount_due"] * (pct / 100)
            new_status = "waived" if pct == 100 else (
                "paid" if (b["amount_paid"] + discount) >= b["amount_due"] else "partial"
            )
            execute(
                "UPDATE student_bills SET discount_amount=?, status=? WHERE id=?",
                (discount, new_status, bid)
            )

        self.accept()


class WaiversWidget(QWidget):
    COLS = ["Student", "Adm No", "Waiver Type", "Discount %", "Bill / Scope", "Academic Year", "Reason", "Approved By"]

    def __init__(self):
        super().__init__()
        self._build()
        self.load_table()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 20, 28, 20); layout.setSpacing(14)

        row0 = QHBoxLayout()
        t = QLabel("Fee Waivers & Discounts")
        t.setStyleSheet("font-size:20px;font-weight:700;color:#111827;")
        row0.addWidget(t); row0.addStretch()
        add = QPushButton("+ Add Waiver"); add.setStyleSheet(BTN_PRIMARY)
        add.clicked.connect(self._add)
        row0.addWidget(add)
        layout.addLayout(row0)

        info = QLabel(
            "Orphan students are automatically waived 100% when billing runs. "
            "Use this page to add scholarships, partial discounts, or staff-child exemptions."
        )
        info.setWordWrap(True)
        info.setStyleSheet("background:#EDE9FE;color:#4C1D95;border-radius:8px;"
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
            QTableWidget::item:selected{background:#EDE9FE;color:#4C1D95;}
        """)
        layout.addWidget(self.table)

    def load_table(self):
        rows = fetch_all("""
            SELECT fw.id, s.first_name||' '||s.last_name AS student,
                   s.admission_no, fw.waiver_type, fw.discount_percent,
                   sb.control_number, ay.label AS year,
                   fw.reason, u.full_name AS approver
            FROM fee_waivers fw
            JOIN students s ON s.id=fw.student_id
            LEFT JOIN student_bills sb ON sb.id=fw.bill_id
            LEFT JOIN academic_years ay ON ay.id=fw.academic_year_id
            LEFT JOIN users u ON u.id=fw.approved_by
            ORDER BY fw.created_at DESC
        """)
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, v in enumerate([
                row["student"], row["admission_no"],
                row["waiver_type"].replace("_", " ").title(),
                f"{row['discount_percent']:.0f}%",
                row["control_number"] or "All outstanding",
                row["year"] or "—",
                row["reason"] or "—",
                row["approver"] or "—",
            ]):
                item = QTableWidgetItem(v)
                if row["discount_percent"] == 100:
                    item.setForeground(QColor("#4C1D95"))
                self.table.setItem(r, c, item)

    def _add(self):
        if WaiverDialog(self).exec(): self.load_table()
