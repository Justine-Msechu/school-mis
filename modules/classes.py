"""Classes module — manage class groups."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QDialog,
    QFormLayout, QComboBox, QLineEdit, QSpinBox, QMessageBox,
    QAbstractItemView
)
from PyQt6.QtCore import Qt
from database.db import fetch_all, fetch_one, execute

BTN_PRIMARY = """QPushButton{background:#7C3AED;color:white;border:none;border-radius:7px;
    padding:8px 18px;font-size:13px;font-weight:600;}QPushButton:hover{background:#6D28D9;}"""
BTN_OUTLINE = """QPushButton{background:white;color:#374151;border:1px solid #D1D5DB;
    border-radius:7px;padding:8px 18px;font-size:13px;}QPushButton:hover{background:#F9FAFB;}"""
BTN_DANGER = """QPushButton{background:#EF4444;color:white;border:none;border-radius:7px;
    padding:8px 18px;font-size:13px;font-weight:600;}QPushButton:hover{background:#DC2626;}"""
INPUT = "QLineEdit,QComboBox,QSpinBox{border:1px solid #D1D5DB;border-radius:6px;padding:6px 10px;font-size:13px;background:white;}"


class ClassDialog(QDialog):
    def __init__(self, parent=None, class_id=None):
        super().__init__(parent)
        self.class_id = class_id
        self.setWindowTitle("Edit Class" if class_id else "Add New Class")
        self.setMinimumWidth(400)
        self.setStyleSheet(INPUT + "QDialog{background:#F9FAFB;}")
        self._build()
        if class_id: self._load()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        title = QLabel("Class Details")
        title.setStyleSheet("font-size:16px;font-weight:700;color:#111827;")
        layout.addWidget(title)

        form = QFormLayout(); form.setSpacing(9)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.name  = QLineEdit(); self.name.setPlaceholderText("e.g. Grade 1A")
        self.grade = QSpinBox(); self.grade.setRange(1, 7); self.grade.setValue(1)
        self.cap   = QSpinBox(); self.cap.setRange(10, 100); self.cap.setValue(40)
        self.room  = QLineEdit(); self.room.setPlaceholderText("e.g. Room 3")

        self.teacher_cb = QComboBox()
        self.teacher_cb.addItem("— No class teacher —", None)
        for t in fetch_all("SELECT id, first_name, last_name FROM teachers WHERE is_active=1"):
            self.teacher_cb.addItem(f"{t['first_name']} {t['last_name']}", t["id"])

        self.year_cb = QComboBox()
        for y in fetch_all("SELECT id, label FROM academic_years ORDER BY id DESC"):
            self.year_cb.addItem(y["label"], y["id"])

        for lbl, wgt in [
            ("Class name *", self.name), ("Grade level", self.grade),
            ("Capacity", self.cap), ("Room", self.room),
            ("Class teacher", self.teacher_cb), ("Academic year", self.year_cb),
        ]:
            l = QLabel(lbl); l.setStyleSheet("font-size:13px;color:#374151;")
            form.addRow(l, wgt)

        layout.addLayout(form)

        row = QHBoxLayout(); row.addStretch()
        c = QPushButton("Cancel"); c.setStyleSheet(BTN_OUTLINE)
        s = QPushButton("Save class"); s.setStyleSheet(BTN_PRIMARY)
        c.clicked.connect(self.reject); s.clicked.connect(self._save)
        row.addWidget(c); row.addWidget(s)
        layout.addLayout(row)

    def _load(self):
        cl = fetch_one("SELECT * FROM classes WHERE id=?", (self.class_id,))
        if not cl: return
        self.name.setText(cl["name"]); self.grade.setValue(cl["grade_level"])
        self.cap.setValue(cl["capacity"] or 40)
        self.room.setText(cl["room"] or "")
        for i in range(self.teacher_cb.count()):
            if self.teacher_cb.itemData(i) == cl["teacher_id"]:
                self.teacher_cb.setCurrentIndex(i); break
        for i in range(self.year_cb.count()):
            if self.year_cb.itemData(i) == cl["academic_year_id"]:
                self.year_cb.setCurrentIndex(i); break

    def _save(self):
        if not self.name.text().strip():
            QMessageBox.warning(self, "Validation", "Class name is required."); return
        data = (
            self.name.text().strip(), self.grade.value(),
            self.cap.value(), self.room.text().strip(),
            self.teacher_cb.currentData(), self.year_cb.currentData(),
        )
        if self.class_id:
            execute("UPDATE classes SET name=?,grade_level=?,capacity=?,room=?,teacher_id=?,academic_year_id=? WHERE id=?",
                    data + (self.class_id,))
        else:
            execute("INSERT INTO classes(name,grade_level,capacity,room,teacher_id,academic_year_id) VALUES(?,?,?,?,?,?)", data)
        self.accept()


class ClassesWidget(QWidget):
    COLS = ["Class", "Grade", "Teacher", "Room", "Capacity", "Students"]

    def __init__(self):
        super().__init__()
        self._build()
        self.load_table()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        row0 = QHBoxLayout()
        t = QLabel("Classes & Timetable")
        t.setStyleSheet("font-size:22px;font-weight:700;color:#111827;")
        row0.addWidget(t); row0.addStretch()
        add = QPushButton("+ Add class"); add.setStyleSheet(BTN_PRIMARY)
        add.clicked.connect(self.add_class)
        row0.addWidget(add)
        layout.addLayout(row0)

        self.table = QTableWidget()
        self.table.setColumnCount(len(self.COLS))
        self.table.setHorizontalHeaderLabels(self.COLS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet("""
            QTableWidget{border:1px solid #E5E7EB;border-radius:8px;
                gridline-color:#F3F4F6;font-size:13px;}
            QHeaderView::section{background:#F9FAFB;font-weight:600;
                padding:8px;border:none;border-bottom:1px solid #E5E7EB;color:#374151;}
            QTableWidget::item{padding:6px 8px;}
            QTableWidget::item:selected{background:#F5F3FF;color:#4C1D95;}
        """)
        self.table.doubleClicked.connect(self.edit_selected)
        layout.addWidget(self.table)

        act = QHBoxLayout()
        self.lbl = QLabel(""); self.lbl.setStyleSheet("font-size:12px;color:#9CA3AF;")
        act.addWidget(self.lbl); act.addStretch()
        eb = QPushButton("Edit selected"); eb.setStyleSheet(BTN_OUTLINE)
        db = QPushButton("Delete");        db.setStyleSheet(BTN_DANGER)
        eb.clicked.connect(self.edit_selected); db.clicked.connect(self.delete_selected)
        act.addWidget(eb); act.addWidget(db)
        layout.addLayout(act)

    def load_table(self):
        rows = fetch_all("""
            SELECT c.id, c.name, c.grade_level, c.room, c.capacity,
                   t.first_name||' '||t.last_name AS teacher,
                   (SELECT COUNT(*) FROM students s WHERE s.class_id=c.id AND s.is_active=1) AS students
            FROM classes c LEFT JOIN teachers t ON t.id=c.teacher_id
            ORDER BY c.grade_level, c.name
        """)
        self.table.setRowCount(len(rows))
        self._ids = []
        for r, row in enumerate(rows):
            self._ids.append(row["id"])
            for c, v in enumerate([
                row["name"], str(row["grade_level"]),
                row["teacher"] or "—", row["room"] or "—",
                str(row["capacity"] or 40), str(row["students"])
            ]):
                self.table.setItem(r, c, QTableWidgetItem(v))
        self.lbl.setText(f"{len(rows)} class(es)")

    def _sel_id(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self._ids):
            QMessageBox.information(self, "Select", "Please select a class."); return None
        return self._ids[row]

    def add_class(self):
        if ClassDialog(self).exec(): self.load_table()

    def edit_selected(self):
        cid = self._sel_id()
        if cid and ClassDialog(self, class_id=cid).exec(): self.load_table()

    def delete_selected(self):
        cid = self._sel_id()
        if not cid: return
        cl = fetch_one("SELECT name FROM classes WHERE id=?", (cid,))
        r = QMessageBox.question(self, "Confirm", f"Delete class '{cl['name']}'?\nAll attendance/grade links will also be removed.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if r == QMessageBox.StandardButton.Yes:
            execute("DELETE FROM classes WHERE id=?", (cid,))
            self.load_table()
