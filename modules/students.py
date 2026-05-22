"""Students module — enrol, view, edit, deactivate students."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QDialog, QFormLayout, QComboBox, QTextEdit, QDateEdit,
    QMessageBox, QFrame, QSizePolicy, QAbstractItemView
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QColor
from database.db import fetch_all, fetch_one, execute


# ── Styles ────────────────────────────────────────────────────────────────────
BTN_PRIMARY = """
    QPushButton {
        background: #2563EB; color: white; border: none;
        border-radius: 7px; padding: 8px 18px; font-size: 13px; font-weight: 600;
    }
    QPushButton:hover { background: #1D4ED8; }
    QPushButton:pressed { background: #1E40AF; }
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
    QLineEdit:focus, QComboBox:focus, QDateEdit:focus {
        border-color: #2563EB;
    }
"""


def next_admission_no():
    row = fetch_one("SELECT MAX(CAST(SUBSTR(admission_no,3) AS INTEGER)) AS n FROM students")
    n = (row["n"] or 0) + 1 if row and row["n"] else 1
    return f"ST{n:04d}"


def get_classes():
    return fetch_all(
        "SELECT id, name FROM classes ORDER BY grade_level, name"
    )


# ── Dialog: Add / Edit Student ─────────────────────────────────────────────────
class StudentDialog(QDialog):
    def __init__(self, parent=None, student_id=None):
        super().__init__(parent)
        self.student_id = student_id
        self.setWindowTitle("Edit Student" if student_id else "Enrol New Student")
        self.setMinimumWidth(480)
        self.setStyleSheet(INPUT_STYLE + "QDialog { background: #F9FAFB; }")
        self._build()
        if student_id:
            self._load()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        title = QLabel("Student Information")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #111827;")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.adm = QLineEdit()
        self.adm.setText(next_admission_no())
        self.adm.setPlaceholderText("e.g. ST0001")

        self.first  = QLineEdit(); self.first.setPlaceholderText("First name")
        self.last   = QLineEdit(); self.last.setPlaceholderText("Last name")

        self.gender = QComboBox()
        self.gender.addItems(["Male", "Female", "Other"])

        self.dob = QDateEdit()
        self.dob.setCalendarPopup(True)
        self.dob.setDate(QDate(2015, 1, 1))
        self.dob.setDisplayFormat("dd/MM/yyyy")

        self.cls = QComboBox()
        self._fill_classes()

        self.parent_name  = QLineEdit(); self.parent_name.setPlaceholderText("Parent / Guardian name")
        self.parent_phone = QLineEdit(); self.parent_phone.setPlaceholderText("e.g. +255 712 345 678")
        self.parent_email = QLineEdit(); self.parent_email.setPlaceholderText("parent@email.com")
        self.address      = QLineEdit(); self.address.setPlaceholderText("Home address")
        self.notes        = QTextEdit(); self.notes.setFixedHeight(60)
        self.notes.setPlaceholderText("Any additional notes…")

        for lbl, wgt in [
            ("Admission no *", self.adm),
            ("First name *", self.first),
            ("Last name *", self.last),
            ("Gender", self.gender),
            ("Date of birth", self.dob),
            ("Class", self.cls),
            ("Parent name", self.parent_name),
            ("Parent phone", self.parent_phone),
            ("Parent email", self.parent_email),
            ("Address", self.address),
            ("Notes", self.notes),
        ]:
            lbl_w = QLabel(lbl)
            lbl_w.setStyleSheet("font-size: 13px; color: #374151;")
            form.addRow(lbl_w, wgt)

        layout.addLayout(form)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel = QPushButton("Cancel"); cancel.setStyleSheet(BTN_OUTLINE)
        save   = QPushButton("Save student"); save.setStyleSheet(BTN_PRIMARY)
        cancel.clicked.connect(self.reject)
        save.clicked.connect(self._save)
        btn_row.addWidget(cancel)
        btn_row.addWidget(save)
        layout.addLayout(btn_row)

    def _fill_classes(self):
        self.cls.clear()
        self.cls.addItem("— No class assigned —", None)
        for row in get_classes():
            self.cls.addItem(row["name"], row["id"])

    def _load(self):
        s = fetch_one("SELECT * FROM students WHERE id=?", (self.student_id,))
        if not s:
            return
        self.adm.setText(s["admission_no"])
        self.first.setText(s["first_name"])
        self.last.setText(s["last_name"])
        idx = self.gender.findText(s["gender"] or "Male")
        if idx >= 0: self.gender.setCurrentIndex(idx)
        if s["date_of_birth"]:
            self.dob.setDate(QDate.fromString(s["date_of_birth"], "yyyy-MM-dd"))
        # class combo
        for i in range(self.cls.count()):
            if self.cls.itemData(i) == s["class_id"]:
                self.cls.setCurrentIndex(i); break
        self.parent_name.setText(s["parent_name"] or "")
        self.parent_phone.setText(s["parent_phone"] or "")
        self.parent_email.setText(s["parent_email"] or "")
        self.address.setText(s["address"] or "")
        self.notes.setPlainText(s["notes"] or "")

    def _save(self):
        if not self.first.text().strip() or not self.last.text().strip():
            QMessageBox.warning(self, "Validation", "First name and Last name are required.")
            return
        if not self.adm.text().strip():
            QMessageBox.warning(self, "Validation", "Admission number is required.")
            return

        data = (
            self.adm.text().strip(),
            self.first.text().strip(),
            self.last.text().strip(),
            self.gender.currentText(),
            self.dob.date().toString("yyyy-MM-dd"),
            self.cls.currentData(),
            self.parent_name.text().strip(),
            self.parent_phone.text().strip(),
            self.parent_email.text().strip(),
            self.address.text().strip(),
            self.notes.toPlainText().strip(),
        )

        if self.student_id:
            execute("""
                UPDATE students SET
                    admission_no=?, first_name=?, last_name=?, gender=?,
                    date_of_birth=?, class_id=?, parent_name=?, parent_phone=?,
                    parent_email=?, address=?, notes=?
                WHERE id=?
            """, data + (self.student_id,))
        else:
            execute("""
                INSERT INTO students
                    (admission_no, first_name, last_name, gender, date_of_birth,
                     class_id, parent_name, parent_phone, parent_email, address, notes)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """, data)

        self.accept()


# ── Main Students Widget ───────────────────────────────────────────────────────
class StudentsWidget(QWidget):
    COLS = ["Adm No", "Full Name", "Gender", "Class", "Parent", "Phone", "Status"]

    def __init__(self):
        super().__init__()
        self._build()
        self.load_table()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        # Title row
        title_row = QHBoxLayout()
        title = QLabel("Students")
        title.setStyleSheet("font-size: 22px; font-weight: 700; color: #111827;")
        title_row.addWidget(title)
        title_row.addStretch()
        add_btn = QPushButton("+ Enrol student")
        add_btn.setStyleSheet(BTN_PRIMARY)
        add_btn.clicked.connect(self.add_student)
        title_row.addWidget(add_btn)
        layout.addLayout(title_row)

        # Search / filter bar
        bar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍  Search by name or admission number…")
        self.search.setStyleSheet(INPUT_STYLE + "QLineEdit { min-width: 260px; }")
        self.search.textChanged.connect(self.load_table)

        self.filter_cls = QComboBox()
        self.filter_cls.setStyleSheet(INPUT_STYLE)
        self.filter_cls.addItem("All classes", None)
        for row in get_classes():
            self.filter_cls.addItem(row["name"], row["id"])
        self.filter_cls.currentIndexChanged.connect(self.load_table)

        self.filter_status = QComboBox()
        self.filter_status.setStyleSheet(INPUT_STYLE)
        self.filter_status.addItems(["Active", "Inactive", "All"])
        self.filter_status.currentIndexChanged.connect(self.load_table)

        bar.addWidget(self.search)
        bar.addWidget(QLabel("Class:"))
        bar.addWidget(self.filter_cls)
        bar.addWidget(QLabel("Status:"))
        bar.addWidget(self.filter_status)
        bar.addStretch()
        layout.addLayout(bar)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(len(self.COLS))
        self.table.setHorizontalHeaderLabels(self.COLS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #E5E7EB; border-radius: 8px;
                gridline-color: #F3F4F6; font-size: 13px;
            }
            QHeaderView::section {
                background: #F9FAFB; font-weight: 600;
                padding: 8px; border: none; border-bottom: 1px solid #E5E7EB;
                color: #374151;
            }
            QTableWidget::item { padding: 6px 8px; }
            QTableWidget::item:selected { background: #EFF6FF; color: #1E40AF; }
        """)
        self.table.doubleClicked.connect(self.edit_selected)
        layout.addWidget(self.table)

        # Action row (below table)
        act = QHBoxLayout()
        self.lbl_count = QLabel("")
        self.lbl_count.setStyleSheet("font-size: 12px; color: #9CA3AF;")
        act.addWidget(self.lbl_count)
        act.addStretch()
        edit_btn = QPushButton("Edit selected")
        edit_btn.setStyleSheet(BTN_OUTLINE)
        edit_btn.clicked.connect(self.edit_selected)
        deact_btn = QPushButton("Deactivate")
        deact_btn.setStyleSheet(BTN_DANGER)
        deact_btn.clicked.connect(self.deactivate_selected)
        act.addWidget(edit_btn)
        act.addWidget(deact_btn)
        layout.addLayout(act)

    def load_table(self):
        q = self.search.text().strip()
        cls_id = self.filter_cls.currentData()
        status_txt = self.filter_status.currentText()
        status_map = {"Active": 1, "Inactive": 0, "All": None}
        status = status_map[status_txt]

        sql = """
            SELECT s.id, s.admission_no, s.first_name, s.last_name,
                   s.gender, c.name AS class_name,
                   s.parent_name, s.parent_phone, s.is_active
            FROM students s
            LEFT JOIN classes c ON c.id = s.class_id
            WHERE 1=1
        """
        params = []
        if q:
            sql += " AND (s.first_name LIKE ? OR s.last_name LIKE ? OR s.admission_no LIKE ?)"
            params += [f"%{q}%", f"%{q}%", f"%{q}%"]
        if cls_id:
            sql += " AND s.class_id = ?"
            params.append(cls_id)
        if status is not None:
            sql += " AND s.is_active = ?"
            params.append(status)
        sql += " ORDER BY s.last_name, s.first_name"

        rows = fetch_all(sql, params)
        self.table.setRowCount(len(rows))
        self._row_ids = []

        for r, row in enumerate(rows):
            self._row_ids.append(row["id"])
            vals = [
                row["admission_no"],
                f"{row['first_name']} {row['last_name']}",
                row["gender"] or "",
                row["class_name"] or "—",
                row["parent_name"] or "—",
                row["parent_phone"] or "—",
                "Active" if row["is_active"] else "Inactive",
            ]
            for c, v in enumerate(vals):
                item = QTableWidgetItem(v)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if v == "Inactive":
                    item.setForeground(QColor("#9CA3AF"))
                self.table.setItem(r, c, item)

        self.lbl_count.setText(f"{len(rows)} student(s) found")

    def _selected_id(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self._row_ids):
            QMessageBox.information(self, "No selection", "Please select a student first.")
            return None
        return self._row_ids[row]

    def add_student(self):
        dlg = StudentDialog(self)
        if dlg.exec():
            self.load_table()

    def edit_selected(self):
        sid = self._selected_id()
        if sid is None: return
        dlg = StudentDialog(self, student_id=sid)
        if dlg.exec():
            self.load_table()

    def deactivate_selected(self):
        sid = self._selected_id()
        if sid is None: return
        s = fetch_one("SELECT first_name, last_name FROM students WHERE id=?", (sid,))
        reply = QMessageBox.question(
            self, "Confirm",
            f"Deactivate {s['first_name']} {s['last_name']}?\nThey will be hidden from active lists.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            execute("UPDATE students SET is_active=0 WHERE id=?", (sid,))
            self.load_table()
