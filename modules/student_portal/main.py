"""Student Portal — read-only view of own approved grades + homework submissions."""

import os
import shutil
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget,
    QComboBox, QMessageBox, QAbstractItemView, QFileDialog,
    QDialog, QFormLayout, QTextEdit, QDialogButtonBox, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from auth.session import session
from auth.rbac import get_portal_student_id
from services.portal_service import portal_service
from services.homework_service import homework_service
from services.base import ServiceError, PolicyViolation
from database.db import fetch_one, fetch_all

BTN_PRIMARY = """QPushButton{background:#6366F1;color:white;border:none;border-radius:7px;
    padding:8px 18px;font-size:13px;font-weight:600;}QPushButton:hover{background:#4F46E5;}
    QPushButton:disabled{background:#CBD5E1;color:#94A3B8;}"""
BTN_OUTLINE = """QPushButton{background:white;color:#374151;border:1px solid #D1D5DB;
    border-radius:7px;padding:8px 18px;font-size:13px;}QPushButton:hover{background:#F9FAFB;}"""
COMBO = """QComboBox{border:1px solid #D1D5DB;border-radius:6px;padding:6px 10px;
    font-size:13px;background:white;min-width:160px;}"""

GRADE_COLOURS = {"A": "#059669", "B": "#0891B2", "C": "#D97706", "D": "#EA580C", "F": "#DC2626"}
UPLOADS_DIR   = Path("homework_uploads")


def _ensure_uploads():
    UPLOADS_DIR.mkdir(exist_ok=True)


class _GradesTab(QWidget):
    COLS = ["Exam", "Term", "Year", "Subject", "Score", "Grade", "Remarks"]

    def __init__(self):
        super().__init__()
        self._build()
        self._load()

    def _build(self):
        lay = QVBoxLayout(self); lay.setContentsMargins(0, 12, 0, 0); lay.setSpacing(10)

        hdr = QHBoxLayout()
        t = QLabel("My Approved Grades")
        t.setStyleSheet("font-size:15px;font-weight:700;color:#111827;")
        hdr.addWidget(t); hdr.addStretch()
        ref = QPushButton("Refresh"); ref.setStyleSheet(BTN_OUTLINE)
        ref.clicked.connect(self._load)
        hdr.addWidget(ref)
        lay.addLayout(hdr)

        note = QLabel(
            "Only grades that have been approved by the academic officer are shown here. "
            "Grades in draft or pending review are not visible."
        )
        note.setWordWrap(True)
        note.setStyleSheet(
            "background:#EEF2FF;color:#3730A3;border-radius:6px;"
            "padding:8px 12px;font-size:12px;"
        )
        lay.addWidget(note)

        self.table = QTableWidget()
        self.table.setColumnCount(len(self.COLS))
        self.table.setHorizontalHeaderLabels(self.COLS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet("""
            QTableWidget{border:1px solid #E5E7EB;border-radius:8px;
                gridline-color:#F3F4F6;font-size:12px;}
            QHeaderView::section{background:#EEF2FF;font-weight:600;
                padding:7px;border:none;border-bottom:1px solid #C7D2FE;color:#3730A3;}
            QTableWidget::item{padding:5px 7px;}
        """)
        lay.addWidget(self.table)

    def _load(self):
        try:
            rows = portal_service.get_my_grades()
        except (ServiceError, PolicyViolation) as e:
            QMessageBox.warning(self, "Error", str(e)); return

        self.table.setRowCount(len(rows))
        ctr = Qt.AlignmentFlag.AlignCenter
        for r, row in enumerate(rows):
            def cell(v, align=Qt.AlignmentFlag.AlignLeft, fg=None):
                it = QTableWidgetItem(str(v) if v is not None else "—")
                it.setFlags(Qt.ItemFlag.ItemIsEnabled)
                it.setTextAlignment(align | Qt.AlignmentFlag.AlignVCenter)
                if fg: it.setForeground(QColor(fg))
                return it
            self.table.setItem(r, 0, cell(row.get("exam_name") or "—"))
            self.table.setItem(r, 1, cell(f"Term {row.get('term','?')}", ctr))
            self.table.setItem(r, 2, cell(row.get("year_label") or "—", ctr))
            self.table.setItem(r, 3, cell(row.get("subject_name") or "—"))
            sc = row.get("score"); mx = row.get("max_score") or 100
            self.table.setItem(r, 4, cell(
                f"{sc:.0f}/{mx:.0f}" if sc is not None else "—", ctr
            ))
            letter = row.get("grade_letter") or "—"
            self.table.setItem(r, 5, cell(letter, ctr, GRADE_COLOURS.get(letter, "#9CA3AF")))
            self.table.setItem(r, 6, cell(row.get("remarks") or ""))

    def refresh(self): self._load()


class _HomeworkTab(QWidget):
    COLS = ["Subject", "Title", "Deadline", "Max Pts", "Status", "My Points", "Actions"]

    def __init__(self):
        super().__init__()
        self._assignments: list[dict] = []
        self._build()
        self._load()

    def _build(self):
        lay = QVBoxLayout(self); lay.setContentsMargins(0, 12, 0, 0); lay.setSpacing(10)

        hdr = QHBoxLayout()
        t = QLabel("Homework Assignments")
        t.setStyleSheet("font-size:15px;font-weight:700;color:#111827;")
        hdr.addWidget(t); hdr.addStretch()
        ref = QPushButton("Refresh"); ref.setStyleSheet(BTN_OUTLINE)
        ref.clicked.connect(self._load)
        hdr.addWidget(ref)
        lay.addLayout(hdr)

        self.table = QTableWidget()
        self.table.setColumnCount(len(self.COLS))
        self.table.setHorizontalHeaderLabels(self.COLS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet("""
            QTableWidget{border:1px solid #E5E7EB;border-radius:8px;
                gridline-color:#F3F4F6;font-size:12px;}
            QHeaderView::section{background:#EEF2FF;font-weight:600;
                padding:7px;border:none;border-bottom:1px solid #C7D2FE;color:#3730A3;}
            QTableWidget::item{padding:5px 7px;}
        """)
        lay.addWidget(self.table)

    def _load(self):
        try:
            self._assignments = portal_service.get_my_homework()
        except (ServiceError, PolicyViolation) as e:
            QMessageBox.warning(self, "Error", str(e)); return
        self._fill()

    def _fill(self):
        import datetime
        now = datetime.datetime.now()
        self.table.setRowCount(len(self._assignments))
        ctr = Qt.AlignmentFlag.AlignCenter

        for r, hw in enumerate(self._assignments):
            def cell(v, align=Qt.AlignmentFlag.AlignLeft, fg=None):
                it = QTableWidgetItem(str(v) if v is not None else "—")
                it.setFlags(Qt.ItemFlag.ItemIsEnabled)
                it.setTextAlignment(align | Qt.AlignmentFlag.AlignVCenter)
                if fg: it.setForeground(QColor(fg))
                return it

            deadline_str = hw.get("deadline") or ""
            try:
                dl = datetime.datetime.fromisoformat(deadline_str)
                past_deadline = now > dl
                dl_label = dl.strftime("%d %b %Y %H:%M")
            except (ValueError, TypeError):
                past_deadline = False
                dl_label = deadline_str

            self.table.setItem(r, 0, cell(hw.get("subject_name") or "—"))
            self.table.setItem(r, 1, cell(hw.get("title") or "—"))
            self.table.setItem(r, 2, cell(dl_label, ctr,
                                          "#DC2626" if past_deadline else "#059669"))
            self.table.setItem(r, 3, cell(
                f"{hw.get('max_points', 10):.0f}", ctr
            ))

            sub_status = hw.get("sub_status")
            if sub_status == "graded":
                st_label = "Graded"; st_fg = "#059669"
            elif sub_status == "submitted":
                st_label = "Submitted"; st_fg = "#0891B2"
            elif sub_status == "late":
                st_label = "Late"; st_fg = "#DC2626"
            else:
                st_label = "Not Submitted"
                st_fg = "#DC2626" if past_deadline else "#F59E0B"

            self.table.setItem(r, 4, cell(st_label, ctr, st_fg))
            pts = hw.get("points_earned")
            self.table.setItem(r, 5, cell(
                f"{pts:.1f}" if pts is not None else "—", ctr
            ))

            # Actions
            btn_w = QWidget()
            bl = QHBoxLayout(btn_w); bl.setContentsMargins(4, 2, 4, 2); bl.setSpacing(4)
            if not past_deadline or not sub_status:
                up_btn = QPushButton("Upload"); up_btn.setStyleSheet(BTN_PRIMARY)
                up_btn.clicked.connect(
                    lambda _, aid=hw["assignment_id"]: self._upload(aid)
                )
                bl.addWidget(up_btn)
            if hw.get("feedback"):
                fb_btn = QPushButton("Feedback"); fb_btn.setStyleSheet(BTN_OUTLINE)
                fb_btn.clicked.connect(
                    lambda _, fb=hw.get("feedback"): QMessageBox.information(
                        self, "Teacher Feedback", fb or "No feedback yet."
                    )
                )
                bl.addWidget(fb_btn)
            self.table.setCellWidget(r, 6, btn_w)

    def _upload(self, assignment_id: int):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select your homework file", "",
            "All Files (*);;PDF (*.pdf);;Word (*.docx);;Images (*.png *.jpg)"
        )
        if not path:
            return

        # Copy file to uploads folder
        _ensure_uploads()
        src  = Path(path)
        sid  = get_portal_student_id() or "unknown"
        dest = UPLOADS_DIR / f"student{sid}_hw{assignment_id}_{src.name}"
        try:
            shutil.copy2(str(src), str(dest))
        except OSError as e:
            QMessageBox.warning(self, "File Error", f"Could not copy file: {e}")
            return

        try:
            portal_service.submit_homework(assignment_id, str(dest), "")
        except (ServiceError, PolicyViolation) as e:
            QMessageBox.warning(self, "Error", str(e)); return

        QMessageBox.information(self, "Submitted", "Homework submitted successfully.")
        self._load()

    def refresh(self): self._load()


class StudentPortalWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 20, 28, 20); lay.setSpacing(0)

        # Header
        hdr = QHBoxLayout()
        title = QLabel("Student Portal")
        title.setStyleSheet("font-size:22px;font-weight:700;color:#111827;")
        hdr.addWidget(title); hdr.addStretch()

        student_id = get_portal_student_id()
        if student_id:
            st = fetch_one(
                "SELECT first_name||' '||last_name AS name, admission_no FROM students WHERE id=?",
                (student_id,)
            )
            if st:
                sub = QLabel(f"{st['name']}  ·  Adm: {st['admission_no']}")
                sub.setStyleSheet("font-size:13px;color:#6B7280;")
                hdr.addWidget(sub)
        lay.addLayout(hdr)
        lay.addSpacing(14)

        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane{border:1px solid #E5E7EB;border-radius:8px;
                background:white;padding:16px;}
            QTabBar::tab{background:#F3F4F6;color:#374151;padding:9px 20px;
                margin-right:3px;border-radius:6px 6px 0 0;font-size:13px;}
            QTabBar::tab:selected{background:white;color:#4F46E5;font-weight:600;
                border:1px solid #E5E7EB;border-bottom:none;}
        """)

        self._grades_tab   = _GradesTab()
        self._homework_tab = _HomeworkTab()
        tabs.addTab(self._grades_tab,   "My Grades")
        tabs.addTab(self._homework_tab, "Homework")
        tabs.currentChanged.connect(
            lambda i: [self._grades_tab, self._homework_tab][i].refresh()
        )
        lay.addWidget(tabs)

    def refresh(self):
        self._grades_tab.refresh()
