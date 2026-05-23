"""Attendance module — mark and view daily attendance."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QDateEdit, QMessageBox, QAbstractItemView, QCheckBox
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QColor, QBrush
from database.db import fetch_all, fetch_one, execute, execute_many, get_connection

BTN_PRIMARY = """
    QPushButton { background:#D97706;color:white;border:none;
        border-radius:7px;padding:8px 18px;font-size:13px;font-weight:600;}
    QPushButton:hover{background:#B45309;}
"""
BTN_OUTLINE = """
    QPushButton { background:white;color:#374151;border:1px solid #D1D5DB;
        border-radius:7px;padding:8px 18px;font-size:13px;}
    QPushButton:hover{background:#F9FAFB;}
"""
INPUT_STYLE = "QComboBox,QDateEdit{border:1px solid #D1D5DB;border-radius:6px;padding:6px 10px;font-size:13px;background:white;}"

STATUS_COLORS = {
    "Present": ("#D1FAE5", "#065F46"),
    "Absent":  ("#FEE2E2", "#991B1B"),
    "Late":    ("#FEF3C7", "#92400E"),
    "Excused": ("#EDE9FE", "#4C1D95"),
}


class AttendanceWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._students = []
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        title = QLabel("Attendance")
        title.setStyleSheet("font-size:22px;font-weight:700;color:#111827;")
        layout.addWidget(title)

        # Controls row
        bar = QHBoxLayout(); bar.setSpacing(12)

        lbl_d = QLabel("Date:")
        self.date_pick = QDateEdit()
        self.date_pick.setCalendarPopup(True)
        self.date_pick.setDate(QDate.currentDate())
        self.date_pick.setDisplayFormat("dd/MM/yyyy")
        self.date_pick.setStyleSheet(INPUT_STYLE)
        self.date_pick.dateChanged.connect(self._load_attendance)

        lbl_c = QLabel("Class:")
        self.cls_cb = QComboBox()
        self.cls_cb.setStyleSheet(INPUT_STYLE)
        self.cls_cb.addItem("— Select class —", None)
        for row in fetch_all("SELECT id, name FROM classes ORDER BY grade_level, name"):
            self.cls_cb.addItem(row["name"], row["id"])
        self.cls_cb.currentIndexChanged.connect(self._load_attendance)

        mark_all_present = QPushButton("Mark all present")
        mark_all_present.setStyleSheet(BTN_OUTLINE)
        mark_all_present.clicked.connect(self._mark_all_present)

        save_btn = QPushButton("Save attendance")
        save_btn.setStyleSheet(BTN_PRIMARY)
        save_btn.clicked.connect(self._save)

        bar.addWidget(lbl_d); bar.addWidget(self.date_pick)
        bar.addWidget(lbl_c); bar.addWidget(self.cls_cb)
        bar.addStretch()
        bar.addWidget(mark_all_present); bar.addWidget(save_btn)
        layout.addLayout(bar)

        # Summary labels
        sum_row = QHBoxLayout()
        self.lbl_present = self._badge("Present: 0", "#D1FAE5", "#065F46")
        self.lbl_absent  = self._badge("Absent: 0",  "#FEE2E2", "#991B1B")
        self.lbl_late    = self._badge("Late: 0",    "#FEF3C7", "#92400E")
        for w in [self.lbl_present, self.lbl_absent, self.lbl_late]:
            sum_row.addWidget(w)
        sum_row.addStretch()
        layout.addLayout(sum_row)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Adm No", "Student Name", "Status", "Notes"])
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setStyleSheet("""
            QTableWidget{border:1px solid #E5E7EB;border-radius:8px;
                gridline-color:#F3F4F6;font-size:13px;}
            QHeaderView::section{background:#F9FAFB;font-weight:600;
                padding:8px;border:none;border-bottom:1px solid #E5E7EB;color:#374151;}
            QTableWidget::item{padding:4px 8px;}
        """)
        layout.addWidget(self.table)

    def _badge(self, text, bg, fg):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"background:{bg};color:{fg};border-radius:6px;"
                          f"padding:4px 12px;font-size:12px;font-weight:600;")
        return lbl

    def _load_attendance(self):
        cls_id = self.cls_cb.currentData()
        if not cls_id:
            self.table.setRowCount(0)
            self._students = []
            return

        date_str = self.date_pick.date().toString("yyyy-MM-dd")

        students = fetch_all(
            "SELECT id, admission_no, first_name, last_name FROM students "
            "WHERE class_id=? AND is_active=1 ORDER BY last_name, first_name",
            (cls_id,)
        )

        # Existing attendance for this date/class
        existing = {}
        for row in fetch_all(
            "SELECT student_id, status, notes FROM attendance WHERE class_id=? AND date=?",
            (cls_id, date_str)
        ):
            existing[row["student_id"]] = row

        self.table.setRowCount(len(students))
        self._students = []

        for r, s in enumerate(students):
            self._students.append(s["id"])
            att = existing.get(s["id"])

            adm = QTableWidgetItem(s["admission_no"])
            adm.setFlags(adm.flags() & ~Qt.ItemFlag.ItemIsEditable)
            name = QTableWidgetItem(f"{s['first_name']} {s['last_name']}")
            name.setFlags(name.flags() & ~Qt.ItemFlag.ItemIsEditable)

            # Status dropdown embedded in table
            status_cb = QComboBox()
            status_cb.addItems(["Present", "Absent", "Late", "Excused"])
            status_cb.setStyleSheet("QComboBox{border:none;padding:4px;font-size:13px;}")
            current = att["status"] if att else "Present"
            idx = status_cb.findText(current)
            if idx >= 0: status_cb.setCurrentIndex(idx)
            status_cb.currentTextChanged.connect(lambda t, row=r: self._color_row(row, t))

            notes = QTableWidgetItem(att["notes"] if att and att["notes"] else "")

            self.table.setItem(r, 0, adm)
            self.table.setItem(r, 1, name)
            self.table.setCellWidget(r, 2, status_cb)
            self.table.setItem(r, 3, notes)
            self.table.setRowHeight(r, 36)

            self._color_row(r, current)

        self._update_summary()

    def _color_row(self, row, status):
        bg, fg = STATUS_COLORS.get(status, ("#FFFFFF", "#111827"))
        for col in [0, 1, 3]:
            item = self.table.item(row, col)
            if item:
                item.setBackground(QColor(bg))
                item.setForeground(QColor(fg))
        self._update_summary()

    def _update_summary(self):
        counts = {"Present": 0, "Absent": 0, "Late": 0, "Excused": 0}
        for r in range(self.table.rowCount()):
            cb = self.table.cellWidget(r, 2)
            if cb: counts[cb.currentText()] = counts.get(cb.currentText(), 0) + 1
        self.lbl_present.setText(f"Present: {counts['Present']}")
        self.lbl_absent.setText(f"Absent: {counts['Absent']}")
        self.lbl_late.setText(f"Late: {counts['Late']}")

    def _mark_all_present(self):
        for r in range(self.table.rowCount()):
            cb = self.table.cellWidget(r, 2)
            if cb: cb.setCurrentText("Present")

    def _save(self):
        cls_id = self.cls_cb.currentData()
        if not cls_id:
            QMessageBox.information(self, "No class", "Please select a class first.")
            return
        date_str = self.date_pick.date().toString("yyyy-MM-dd")

        conn = get_connection()
        for r, sid in enumerate(self._students):
            cb = self.table.cellWidget(r, 2)
            status = cb.currentText() if cb else "Present"
            notes_item = self.table.item(r, 3)
            notes = notes_item.text() if notes_item else ""
            conn.execute("""
                INSERT INTO attendance (student_id, class_id, date, status, notes)
                VALUES (?,?,?,?,?)
                ON CONFLICT(student_id, date) DO UPDATE SET
                    status=excluded.status, notes=excluded.notes
            """, (sid, cls_id, date_str, status, notes))
        conn.commit()
        conn.close()

        QMessageBox.information(
            self, "Saved",
            f"Attendance saved for {self.table.rowCount()} student(s) on {date_str}."
        )
