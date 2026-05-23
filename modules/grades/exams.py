"""Exam management tab — create exams and manage their status."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QDialog,
    QFormLayout, QLineEdit, QComboBox, QSpinBox, QDateEdit,
    QMessageBox, QAbstractItemView
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QColor
from database.db import fetch_all
from services.grades_service import grades_service
from services.base import ServiceError, PolicyViolation

BTN_PRIMARY = """QPushButton{background:#0891B2;color:white;border:none;border-radius:7px;
    padding:8px 18px;font-size:13px;font-weight:600;}QPushButton:hover{background:#0E7490;}"""
BTN_OUTLINE = """QPushButton{background:white;color:#374151;border:1px solid #D1D5DB;
    border-radius:7px;padding:8px 18px;font-size:13px;}QPushButton:hover{background:#F9FAFB;}"""
BTN_DANGER  = """QPushButton{background:white;color:#DC2626;border:1px solid #FECACA;
    border-radius:7px;padding:7px 14px;font-size:12px;}QPushButton:hover{background:#FEF2F2;}"""
BTN_SUCCESS = """QPushButton{background:#059669;color:white;border:none;border-radius:7px;
    padding:7px 14px;font-size:12px;font-weight:600;}QPushButton:hover{background:#047857;}"""
COMBO = """QComboBox{border:1px solid #D1D5DB;border-radius:6px;padding:6px 10px;font-size:13px;background:white;}"""
INPUT = """QLineEdit,QComboBox{border:1px solid #D1D5DB;border-radius:6px;padding:6px 10px;font-size:13px;background:white;}"""

STATUS_COLOURS = {
    "open":      "#059669",
    "locked":    "#D97706",
    "published": "#7C3AED",
}


class CreateExamDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create New Exam")
        self.setMinimumWidth(420)
        self.setStyleSheet(INPUT + "QDialog{background:#F9FAFB;}")
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 20); lay.setSpacing(14)

        title = QLabel("Create New Exam")
        title.setStyleSheet("font-size:16px;font-weight:700;color:#111827;")
        lay.addWidget(title)

        form = QFormLayout(); form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.name_in = QLineEdit(); self.name_in.setPlaceholderText("e.g. Mid-Term Examination")
        self.year_cb = QComboBox(); self.year_cb.setStyleSheet(COMBO)
        for yr in fetch_all("SELECT * FROM academic_years ORDER BY id DESC"):
            self.year_cb.addItem(yr["label"], yr["id"])

        self.term_cb = QComboBox(); self.term_cb.setStyleSheet(COMBO)
        for t in ["1", "2", "3"]:
            self.term_cb.addItem(f"Term {t}", int(t))

        self.start_de = QDateEdit(QDate.currentDate()); self.start_de.setCalendarPopup(True)
        self.end_de   = QDateEdit(QDate.currentDate().addDays(7)); self.end_de.setCalendarPopup(True)

        for lbl, wgt in [
            ("Exam Name *", self.name_in),
            ("Academic Year *", self.year_cb),
            ("Term *", self.term_cb),
            ("Start Date", self.start_de),
            ("End Date", self.end_de),
        ]:
            l = QLabel(lbl); l.setStyleSheet("font-size:13px;color:#374151;")
            form.addRow(l, wgt)
        lay.addLayout(form)

        row = QHBoxLayout(); row.addStretch()
        c = QPushButton("Cancel"); c.setStyleSheet(BTN_OUTLINE)
        s = QPushButton("Create Exam"); s.setStyleSheet(BTN_PRIMARY)
        c.clicked.connect(self.reject); s.clicked.connect(self._save)
        row.addWidget(c); row.addWidget(s)
        lay.addLayout(row)

    def _save(self):
        name = self.name_in.text().strip()
        if not name:
            QMessageBox.warning(self, "Required", "Exam name is required."); return
        try:
            grades_service.create_exam(
                name=name,
                academic_year_id=self.year_cb.currentData(),
                term=self.term_cb.currentData(),
                start_date=self.start_de.date().toString("yyyy-MM-dd"),
                end_date=self.end_de.date().toString("yyyy-MM-dd"),
            )
        except (ServiceError, PolicyViolation) as e:
            QMessageBox.warning(self, "Error", str(e)); return
        self.accept()


class ExamManagementTab(QWidget):
    COLS = ["Exam Name", "Year", "Term", "Start", "End", "Status", "Actions"]

    def __init__(self):
        super().__init__()
        self._exams = []
        self._build()
        self.load()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 16, 0, 0)
        lay.setSpacing(12)

        hdr = QHBoxLayout()
        t = QLabel("Exam Management")
        t.setStyleSheet("font-size:15px;font-weight:700;color:#111827;")
        hdr.addWidget(t); hdr.addStretch()
        add_btn = QPushButton("+ New Exam"); add_btn.setStyleSheet(BTN_PRIMARY)
        add_btn.clicked.connect(self._create)
        hdr.addWidget(add_btn)
        lay.addLayout(hdr)

        info = QLabel(
            "Create exams here. Once teachers have submitted and grades are approved, "
            "lock the exam to prevent further changes, then publish to make results visible."
        )
        info.setWordWrap(True)
        info.setStyleSheet(
            "background:#EFF6FF;color:#1D4ED8;border-radius:6px;padding:8px 12px;font-size:12px;"
        )
        lay.addWidget(info)

        self.table = QTableWidget()
        self.table.setColumnCount(len(self.COLS))
        self.table.setHorizontalHeaderLabels(self.COLS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(6, 240)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet("""
            QTableWidget{border:1px solid #E5E7EB;border-radius:8px;
                gridline-color:#F3F4F6;font-size:13px;}
            QHeaderView::section{background:#F0F9FF;font-weight:600;
                padding:8px;border:none;border-bottom:1px solid #BAE6FD;color:#0369A1;}
            QTableWidget::item{padding:6px 8px;}
        """)
        lay.addWidget(self.table)

    def load(self):
        try:
            self._exams = grades_service.get_exams()
        except (ServiceError, PolicyViolation):
            self._exams = []
        self.table.setRowCount(len(self._exams))
        for r, exam in enumerate(self._exams):
            status = exam["status"]
            for c, v in enumerate([
                exam["name"],
                exam.get("year_label") or "—",
                f"Term {exam['term']}",
                (exam.get("start_date") or "—")[:10],
                (exam.get("end_date") or "—")[:10],
            ]):
                it = QTableWidgetItem(v)
                it.setFlags(Qt.ItemFlag.ItemIsEnabled)
                self.table.setItem(r, c, it)

            st_item = QTableWidgetItem(status.title())
            st_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            st_item.setForeground(QColor(STATUS_COLOURS.get(status, "#374151")))
            self.table.setItem(r, 5, st_item)

            # Status action buttons
            cell = QWidget()
            cl   = QHBoxLayout(cell); cl.setContentsMargins(4, 2, 4, 2); cl.setSpacing(6)
            if status == "open":
                b = QPushButton("Lock"); b.setStyleSheet(BTN_OUTLINE)
                b.clicked.connect(lambda _, i=r: self._set_status(i, "locked"))
                cl.addWidget(b)
            elif status == "locked":
                b1 = QPushButton("Re-open"); b1.setStyleSheet(BTN_DANGER)
                b1.clicked.connect(lambda _, i=r: self._set_status(i, "open"))
                b2 = QPushButton("Publish"); b2.setStyleSheet(BTN_SUCCESS)
                b2.clicked.connect(lambda _, i=r: self._set_status(i, "published"))
                cl.addWidget(b1); cl.addWidget(b2)
            else:
                lbl = QLabel("Published"); lbl.setStyleSheet("color:#7C3AED;font-size:12px;")
                cl.addWidget(lbl)
            cl.addStretch()
            self.table.setCellWidget(r, 6, cell)

    def _create(self):
        if CreateExamDialog(self).exec():
            self.load()

    def _set_status(self, row_idx: int, status: str):
        exam = self._exams[row_idx]
        msg = {
            "locked":    "Lock this exam? Teachers will no longer be able to enter grades.",
            "open":      "Re-open this exam for grade entry?",
            "published": "Publish results? All grades must be approved first.",
        }.get(status, f"Set exam status to '{status}'?")
        if QMessageBox.question(self, "Confirm", msg,
                                QMessageBox.StandardButton.Yes |
                                QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return
        try:
            grades_service.update_exam_status(exam["id"], status)
        except (ServiceError, PolicyViolation) as e:
            QMessageBox.warning(self, "Cannot Change Status", str(e)); return
        self.load()

    def refresh(self):
        self.load()
