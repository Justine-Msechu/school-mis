"""Teachers & Staff module."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QDialog, QFormLayout, QComboBox, QTextEdit, QDateEdit,
    QMessageBox, QAbstractItemView
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QColor
from database.db import fetch_all, fetch_one, execute

BTN_PRIMARY = """
    QPushButton {
        background: #059669; color: white; border: none;
        border-radius: 7px; padding: 8px 18px; font-size: 13px; font-weight: 600;
    }
    QPushButton:hover { background: #047857; }
"""
BTN_DANGER = """
    QPushButton {
        background: #EF4444; color: white; border: none;
        border-radius: 7px; padding: 8px 18px; font-size: 13px; font-weight: 600;
    }
    QPushButton:hover { background: #DC2626; }
"""
BTN_OUTLINE = """
    QPushButton {
        background: white; color: #374151; border: 1px solid #D1D5DB;
        border-radius: 7px; padding: 8px 18px; font-size: 13px;
    }
    QPushButton:hover { background: #F9FAFB; }
"""
INPUT_STYLE = """
    QLineEdit, QComboBox, QTextEdit, QDateEdit {
        border: 1px solid #D1D5DB; border-radius: 6px;
        padding: 6px 10px; font-size: 13px; background: white;
    }
"""


class TeacherDialog(QDialog):
    def __init__(self, parent=None, teacher_id=None):
        super().__init__(parent)
        self.teacher_id = teacher_id
        self.setWindowTitle("Edit Staff" if teacher_id else "Add Staff Member")
        self.setMinimumWidth(460)
        self.setStyleSheet(INPUT_STYLE + "QDialog { background: #F9FAFB; }")
        self._build()
        if teacher_id:
            self._load()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        title = QLabel("Staff Information")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #111827;")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(9)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.first  = QLineEdit(); self.first.setPlaceholderText("First name")
        self.last   = QLineEdit(); self.last.setPlaceholderText("Last name")
        self.gender = QComboBox(); self.gender.addItems(["Male", "Female", "Other"])
        self.role   = QComboBox()
        self.role.addItems(["Teacher", "Head Teacher", "Deputy Head", "Admin", "Support Staff"])
        self.phone  = QLineEdit(); self.phone.setPlaceholderText("+255 7xx xxx xxx")
        self.email  = QLineEdit(); self.email.setPlaceholderText("email@school.tz")
        self.qual   = QLineEdit(); self.qual.setPlaceholderText("e.g. Diploma in Education")
        self.hire   = QDateEdit(); self.hire.setCalendarPopup(True)
        self.hire.setDate(QDate.currentDate()); self.hire.setDisplayFormat("dd/MM/yyyy")
        self.notes  = QTextEdit(); self.notes.setFixedHeight(55)

        for lbl, wgt in [
            ("First name *", self.first), ("Last name *", self.last),
            ("Gender", self.gender), ("Role", self.role),
            ("Phone", self.phone), ("Email", self.email),
            ("Qualification", self.qual), ("Hire date", self.hire),
            ("Notes", self.notes),
        ]:
            l = QLabel(lbl); l.setStyleSheet("font-size: 13px; color: #374151;")
            form.addRow(l, wgt)

        layout.addLayout(form)

        row = QHBoxLayout(); row.addStretch()
        c = QPushButton("Cancel"); c.setStyleSheet(BTN_OUTLINE)
        s = QPushButton("Save");   s.setStyleSheet(BTN_PRIMARY)
        c.clicked.connect(self.reject); s.clicked.connect(self._save)
        row.addWidget(c); row.addWidget(s)
        layout.addLayout(row)

    def _load(self):
        t = fetch_one("SELECT * FROM teachers WHERE id=?", (self.teacher_id,))
        if not t: return
        self.first.setText(t["first_name"]); self.last.setText(t["last_name"])
        for cb, val in [(self.gender, t["gender"]), (self.role, t["role"])]:
            idx = cb.findText(val or ""); 
            if idx >= 0: cb.setCurrentIndex(idx)
        self.phone.setText(t["phone"] or ""); self.email.setText(t["email"] or "")
        self.qual.setText(t["qualification"] or "")
        if t["hire_date"]:
            self.hire.setDate(QDate.fromString(t["hire_date"], "yyyy-MM-dd"))
        self.notes.setPlainText(t["notes"] or "")

    def _save(self):
        if not self.first.text().strip() or not self.last.text().strip():
            QMessageBox.warning(self, "Validation", "First and Last name are required.")
            return
        data = (
            self.first.text().strip(), self.last.text().strip(),
            self.gender.currentText(), self.role.currentText(),
            self.phone.text().strip(), self.email.text().strip(),
            self.qual.text().strip(),
            self.hire.date().toString("yyyy-MM-dd"),
            self.notes.toPlainText().strip(),
        )
        if self.teacher_id:
            execute("""
                UPDATE teachers SET first_name=?,last_name=?,gender=?,role=?,
                    phone=?,email=?,qualification=?,hire_date=?,notes=?
                WHERE id=?
            """, data + (self.teacher_id,))
        else:
            execute("""
                INSERT INTO teachers
                    (first_name,last_name,gender,role,phone,email,qualification,hire_date,notes)
                VALUES (?,?,?,?,?,?,?,?,?)
            """, data)
        self.accept()


class TeachersWidget(QWidget):
    COLS = ["Name", "Role", "Gender", "Phone", "Email", "Hire date", "Status"]

    def __init__(self):
        super().__init__()
        self._build()
        self.load_table()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        row0 = QHBoxLayout()
        t = QLabel("Teachers & Staff")
        t.setStyleSheet("font-size: 22px; font-weight: 700; color: #111827;")
        row0.addWidget(t); row0.addStretch()
        add = QPushButton("+ Add staff member"); add.setStyleSheet(BTN_PRIMARY)
        add.clicked.connect(self.add_teacher)
        row0.addWidget(add)
        layout.addLayout(row0)

        bar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search by name…")
        self.search.setStyleSheet(INPUT_STYLE + "QLineEdit{min-width:240px;}")
        self.search.textChanged.connect(self.load_table)
        bar.addWidget(self.search); bar.addStretch()
        layout.addLayout(bar)

        self.table = QTableWidget()
        self.table.setColumnCount(len(self.COLS))
        self.table.setHorizontalHeaderLabels(self.COLS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet("""
            QTableWidget { border: 1px solid #E5E7EB; border-radius: 8px;
                gridline-color: #F3F4F6; font-size: 13px; }
            QHeaderView::section { background: #F9FAFB; font-weight: 600;
                padding: 8px; border: none; border-bottom: 1px solid #E5E7EB; color: #374151; }
            QTableWidget::item { padding: 6px 8px; }
            QTableWidget::item:selected { background: #ECFDF5; color: #065F46; }
        """)
        self.table.doubleClicked.connect(self.edit_selected)
        layout.addWidget(self.table)

        act = QHBoxLayout()
        self.lbl = QLabel(""); self.lbl.setStyleSheet("font-size:12px;color:#9CA3AF;")
        act.addWidget(self.lbl); act.addStretch()
        eb = QPushButton("Edit selected"); eb.setStyleSheet(BTN_OUTLINE)
        db = QPushButton("Deactivate");    db.setStyleSheet(BTN_DANGER)
        eb.clicked.connect(self.edit_selected); db.clicked.connect(self.deactivate)
        act.addWidget(eb); act.addWidget(db)
        layout.addLayout(act)

    def load_table(self):
        q = self.search.text().strip()
        sql = """SELECT * FROM teachers WHERE 1=1"""
        params = []
        if q:
            sql += " AND (first_name LIKE ? OR last_name LIKE ?)"
            params += [f"%{q}%", f"%{q}%"]
        sql += " ORDER BY last_name, first_name"
        rows = fetch_all(sql, params)
        self.table.setRowCount(len(rows))
        self._ids = []
        for r, row in enumerate(rows):
            self._ids.append(row["id"])
            vals = [
                f"{row['first_name']} {row['last_name']}",
                row["role"] or "Teacher",
                row["gender"] or "",
                row["phone"] or "",
                row["email"] or "",
                row["hire_date"] or "",
                "Active" if row["is_active"] else "Inactive",
            ]
            for c, v in enumerate(vals):
                item = QTableWidgetItem(v)
                if v == "Inactive": item.setForeground(QColor("#9CA3AF"))
                self.table.setItem(r, c, item)
        self.lbl.setText(f"{len(rows)} staff member(s)")

    def _sel_id(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self._ids):
            QMessageBox.information(self, "Select", "Please select a staff member first.")
            return None
        return self._ids[row]

    def add_teacher(self):
        if TeacherDialog(self).exec(): self.load_table()

    def edit_selected(self):
        tid = self._sel_id()
        if tid and TeacherDialog(self, teacher_id=tid).exec(): self.load_table()

    def deactivate(self):
        tid = self._sel_id()
        if not tid: return
        t = fetch_one("SELECT first_name, last_name FROM teachers WHERE id=?", (tid,))
        r = QMessageBox.question(self, "Confirm",
            f"Deactivate {t['first_name']} {t['last_name']}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if r == QMessageBox.StandardButton.Yes:
            execute("UPDATE teachers SET is_active=0 WHERE id=?", (tid,))
            self.load_table()
