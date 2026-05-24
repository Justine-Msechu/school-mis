"""Homework tab — teachers post assignments and grade submissions."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QMessageBox, QAbstractItemView, QDialog, QFormLayout,
    QTextEdit, QDialogButtonBox, QDoubleSpinBox, QLineEdit,
    QDateTimeEdit, QSplitter, QFrame
)
from PyQt6.QtCore import Qt, QDateTime
from PyQt6.QtGui import QColor
from database.db import fetch_all
from auth.session import session
from auth.rbac import get_class_scope, check_subject_access
from services.homework_service import homework_service
from services.base import ServiceError, PolicyViolation

BTN_PRIMARY = """QPushButton{background:#7C3AED;color:white;border:none;border-radius:7px;
    padding:7px 16px;font-size:13px;font-weight:600;}QPushButton:hover{background:#6D28D9;}"""
BTN_OUTLINE = """QPushButton{background:white;color:#374151;border:1px solid #D1D5DB;
    border-radius:7px;padding:7px 16px;font-size:13px;}QPushButton:hover{background:#F9FAFB;}"""
BTN_DANGER = """QPushButton{background:#FEF2F2;color:#DC2626;border:1px solid #FECACA;
    border-radius:6px;padding:5px 12px;font-size:12px;}QPushButton:hover{background:#FEE2E2;}"""
BTN_SUCCESS = """QPushButton{background:#059669;color:white;border:none;border-radius:6px;
    padding:5px 12px;font-size:12px;font-weight:600;}QPushButton:hover{background:#047857;}"""
COMBO = """QComboBox{border:1px solid #D1D5DB;border-radius:6px;padding:6px 10px;
    font-size:13px;background:white;min-width:140px;}"""


class _NewAssignmentDialog(QDialog):
    def __init__(self, class_id: int, subject_id: int,
                 class_name: str, subject_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Homework Assignment")
        self.setMinimumWidth(460)
        lay = QVBoxLayout(self); lay.setSpacing(12)

        ctx = QLabel(f"<b>Class:</b> {class_name}  ·  <b>Subject:</b> {subject_name}")
        ctx.setStyleSheet("font-size:13px;padding:4px 0;")
        lay.addWidget(ctx)

        form = QFormLayout(); form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("e.g. Chapter 5 Exercise")
        self.title_edit.setStyleSheet(
            "QLineEdit{border:1px solid #D1D5DB;border-radius:5px;"
            "padding:5px 8px;font-size:13px;background:white;}"
        )

        self.desc_edit = QTextEdit()
        self.desc_edit.setMaximumHeight(90)
        self.desc_edit.setPlaceholderText("Instructions (optional)…")
        self.desc_edit.setStyleSheet(
            "QTextEdit{border:1px solid #D1D5DB;border-radius:5px;"
            "padding:5px;font-size:13px;background:white;}"
        )

        self.deadline_edit = QDateTimeEdit(QDateTime.currentDateTime().addDays(7))
        self.deadline_edit.setCalendarPopup(True)
        self.deadline_edit.setDisplayFormat("dd/MM/yyyy HH:mm")
        self.deadline_edit.setStyleSheet(
            "QDateTimeEdit{border:1px solid #D1D5DB;border-radius:5px;"
            "padding:5px 8px;font-size:13px;background:white;}"
        )

        self.max_pts = QDoubleSpinBox()
        self.max_pts.setRange(1, 100); self.max_pts.setDecimals(0)
        self.max_pts.setValue(10)
        self.max_pts.setStyleSheet(
            "QDoubleSpinBox{border:1px solid #D1D5DB;border-radius:5px;"
            "padding:5px 8px;font-size:13px;background:white;}"
        )

        form.addRow("Title *:", self.title_edit)
        form.addRow("Instructions:", self.desc_edit)
        form.addRow("Deadline *:", self.deadline_edit)
        form.addRow("Max Points:", self.max_pts)
        lay.addLayout(form)

        bb = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        bb.accepted.connect(self._validate)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def _validate(self):
        if not self.title_edit.text().strip():
            QMessageBox.warning(self, "Required", "Please enter a title.")
            return
        self.accept()

    @property
    def title(self):    return self.title_edit.text().strip()
    @property
    def description(self): return self.desc_edit.toPlainText().strip()
    @property
    def deadline(self):
        return self.deadline_edit.dateTime().toString("yyyy-MM-dd HH:mm:ss")
    @property
    def max_points(self): return self.max_pts.value()


class _GradeDialog(QDialog):
    def __init__(self, student_name: str, max_points: float, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Grade: {student_name}")
        self.setMinimumWidth(360)
        lay = QVBoxLayout(self); lay.setSpacing(10)
        form = QFormLayout(); form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.pts_spin = QDoubleSpinBox()
        self.pts_spin.setRange(0, max_points); self.pts_spin.setDecimals(1)
        self.pts_spin.setStyleSheet(
            "QDoubleSpinBox{border:1px solid #D1D5DB;border-radius:5px;"
            "padding:5px 8px;font-size:13px;background:white;}"
        )
        self.fb_edit = QTextEdit()
        self.fb_edit.setMaximumHeight(80)
        self.fb_edit.setPlaceholderText("Feedback for student (optional)…")
        self.fb_edit.setStyleSheet(
            "QTextEdit{border:1px solid #D1D5DB;border-radius:5px;"
            "padding:5px;font-size:13px;background:white;}"
        )

        form.addRow(f"Points (/{max_points:.0f}):", self.pts_spin)
        form.addRow("Feedback:", self.fb_edit)
        lay.addLayout(form)

        bb = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    @property
    def points(self): return self.pts_spin.value()
    @property
    def feedback(self): return self.fb_edit.toPlainText().strip()


class _SubmissionsDialog(QDialog):
    COLS = ["Student", "Adm No", "Submitted At", "Status", "Points", "Actions"]

    def __init__(self, assignment: dict, parent=None):
        super().__init__(parent)
        self._assignment = assignment
        self.setWindowTitle(f"Submissions — {assignment['title']}")
        self.setMinimumSize(700, 420)
        lay = QVBoxLayout(self)

        info = QLabel(
            f"<b>{assignment['title']}</b>  ·  "
            f"Deadline: {assignment.get('deadline','—')}  ·  "
            f"Max: {assignment.get('max_points',10):.0f} pts  ·  "
            f"{assignment.get('submission_count',0)} submission(s)"
        )
        info.setStyleSheet("font-size:12px;color:#374151;padding:4px 0;")
        lay.addWidget(info)

        self.table = QTableWidget()
        self.table.setColumnCount(len(self.COLS))
        self.table.setHorizontalHeaderLabels(self.COLS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet("""
            QTableWidget{border:1px solid #E5E7EB;border-radius:8px;
                gridline-color:#F3F4F6;font-size:12px;}
            QHeaderView::section{background:#F5F3FF;font-weight:600;
                padding:7px;border:none;border-bottom:1px solid #DDD6FE;color:#5B21B6;}
            QTableWidget::item{padding:5px 7px;}
        """)
        lay.addWidget(self.table)
        self._load()

    def _load(self):
        try:
            subs = homework_service.get_submissions(self._assignment["id"])
        except (ServiceError, PolicyViolation) as e:
            QMessageBox.warning(self, "Error", str(e)); return

        self.table.setRowCount(len(subs))
        ctr = Qt.AlignmentFlag.AlignCenter
        for r, sub in enumerate(subs):
            def cell(v, align=Qt.AlignmentFlag.AlignLeft, fg=None):
                it = QTableWidgetItem(str(v) if v is not None else "—")
                it.setFlags(Qt.ItemFlag.ItemIsEnabled)
                it.setTextAlignment(align | Qt.AlignmentFlag.AlignVCenter)
                if fg: it.setForeground(QColor(fg))
                return it

            st = sub.get("status") or "not submitted"
            st_colors = {"submitted": "#0891B2", "late": "#DC2626", "graded": "#059669"}
            self.table.setItem(r, 0, cell(sub.get("student_name") or "—"))
            self.table.setItem(r, 1, cell(sub.get("admission_no") or "—", ctr))
            self.table.setItem(r, 2, cell(
                (sub.get("submitted_at") or "—")[:16], ctr
            ))
            self.table.setItem(r, 3, cell(st.title(), ctr, st_colors.get(st, "#9CA3AF")))
            pts = sub.get("points_earned")
            self.table.setItem(r, 4, cell(
                f"{pts:.1f}/{self._assignment.get('max_points',10):.0f}"
                if pts is not None else "—", ctr
            ))

            btn_w = QWidget()
            bl = QHBoxLayout(btn_w); bl.setContentsMargins(4,2,4,2); bl.setSpacing(4)
            if sub.get("file_path"):
                op_btn = QPushButton("Open File"); op_btn.setStyleSheet(BTN_OUTLINE)
                fp = sub.get("file_path", "")
                op_btn.clicked.connect(
                    lambda _, f=fp: self._open_file(f)
                )
                bl.addWidget(op_btn)
            grade_btn = QPushButton("Grade"); grade_btn.setStyleSheet(BTN_SUCCESS)
            grade_btn.clicked.connect(
                lambda _, sid=sub["id"], sn=sub.get("student_name",""):
                self._grade(sid, sn)
            )
            bl.addWidget(grade_btn)
            self.table.setCellWidget(r, 5, btn_w)

    def _open_file(self, file_path: str):
        import subprocess, os
        try:
            if os.path.exists(file_path):
                subprocess.Popen(["xdg-open", file_path])
            else:
                QMessageBox.warning(self, "File Not Found",
                                    f"The file could not be found:\n{file_path}")
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

    def _grade(self, submission_id: int, student_name: str):
        dlg = _GradeDialog(student_name,
                           self._assignment.get("max_points", 10), self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            homework_service.grade_submission(submission_id, dlg.points, dlg.feedback)
        except (ServiceError, PolicyViolation) as e:
            QMessageBox.warning(self, "Error", str(e)); return
        self._load()


class HomeworkTab(QWidget):
    COLS = ["Subject", "Title", "Deadline", "Max Pts", "Submissions", "Actions"]

    def __init__(self):
        super().__init__()
        self._assignments: list[dict] = []
        self._build()
        self._load_selectors()

    def _build(self):
        lay = QVBoxLayout(self); lay.setContentsMargins(0, 12, 0, 0); lay.setSpacing(10)

        # Selector row
        sel = QHBoxLayout(); sel.setSpacing(8)
        lc = QLabel("Class:"); lc.setStyleSheet("font-size:13px;font-weight:600;color:#374151;")
        self.cls_cb = QComboBox(); self.cls_cb.setStyleSheet(COMBO)
        self.cls_cb.currentIndexChanged.connect(self._on_class_changed)
        ls = QLabel("Subject:"); ls.setStyleSheet("font-size:13px;font-weight:600;color:#374151;")
        self.subj_cb = QComboBox(); self.subj_cb.setStyleSheet(COMBO)
        self.subj_cb.setMinimumWidth(160)

        load_btn = QPushButton("Load"); load_btn.setStyleSheet(BTN_OUTLINE)
        load_btn.clicked.connect(self._load_assignments)

        new_btn = QPushButton("+ New Assignment"); new_btn.setStyleSheet(BTN_PRIMARY)
        new_btn.clicked.connect(self._new_assignment)

        for w in [lc, self.cls_cb, ls, self.subj_cb, load_btn]:
            sel.addWidget(w)
        sel.addStretch(); sel.addWidget(new_btn)
        lay.addLayout(sel)

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
            QHeaderView::section{background:#F5F3FF;font-weight:600;
                padding:7px;border:none;border-bottom:1px solid #DDD6FE;color:#5B21B6;}
            QTableWidget::item{padding:5px 7px;}
        """)
        lay.addWidget(self.table)

    def _load_selectors(self):
        scope = get_class_scope()  # None = all, [] = none, [ids] = scoped
        if scope is None:
            classes = fetch_all("SELECT id, name FROM classes ORDER BY name")
        elif scope:
            placeholders = ",".join("?" * len(scope))
            classes = fetch_all(
                f"SELECT id, name FROM classes WHERE id IN ({placeholders}) ORDER BY name",
                scope
            )
        else:
            classes = []

        self.cls_cb.clear()
        self.cls_cb.addItem("-- Select class --", None)
        for c in classes:
            self.cls_cb.addItem(c["name"], c["id"])

    def _on_class_changed(self):
        class_id = self.cls_cb.currentData()
        self.subj_cb.clear()
        self.subj_cb.addItem("-- All subjects --", None)
        if not class_id:
            return
        if session.is_teacher:
            try:
                from services.grades_service import grades_service
                subjects = grades_service.get_subjects_for_teacher(class_id)
            except (ServiceError, PolicyViolation):
                subjects = []
        else:
            subjects = fetch_all("SELECT id, name FROM subjects ORDER BY name")
        for s in subjects:
            self.subj_cb.addItem(s["name"], s["id"])

    def _load_assignments(self):
        class_id = self.cls_cb.currentData()
        if not class_id:
            QMessageBox.warning(self, "Required", "Select a class first.")
            return
        subject_id = self.subj_cb.currentData()
        try:
            self._assignments = homework_service.get_assignments(class_id, subject_id)
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

            dl_str = hw.get("deadline") or ""
            try:
                dl = datetime.datetime.fromisoformat(dl_str)
                dl_label = dl.strftime("%d %b %Y %H:%M")
                dl_color = "#DC2626" if now > dl else "#374151"
            except (ValueError, TypeError):
                dl_label = dl_str; dl_color = "#374151"

            self.table.setItem(r, 0, cell(hw.get("subject_name") or "—"))
            self.table.setItem(r, 1, cell(hw.get("title") or "—"))
            self.table.setItem(r, 2, cell(dl_label, ctr, dl_color))
            self.table.setItem(r, 3, cell(f"{hw.get('max_points',10):.0f}", ctr))
            self.table.setItem(r, 4, cell(str(hw.get("submission_count", 0)), ctr))

            btn_w = QWidget()
            bl = QHBoxLayout(btn_w); bl.setContentsMargins(4,2,4,2); bl.setSpacing(4)
            view_btn = QPushButton("Submissions"); view_btn.setStyleSheet(BTN_PRIMARY)
            view_btn.clicked.connect(lambda _, h=hw: self._view_submissions(h))
            bl.addWidget(view_btn)
            if session.can("homework.assign"):
                del_btn = QPushButton("Delete"); del_btn.setStyleSheet(BTN_DANGER)
                del_btn.clicked.connect(lambda _, hid=hw["id"]: self._delete(hid))
                bl.addWidget(del_btn)
            self.table.setCellWidget(r, 5, btn_w)

    def _new_assignment(self):
        class_id   = self.cls_cb.currentData()
        subject_id = self.subj_cb.currentData()
        if not class_id:
            QMessageBox.warning(self, "Required", "Select a class first."); return
        if not subject_id:
            QMessageBox.warning(self, "Required", "Select a subject first."); return

        class_name = self.cls_cb.currentText()
        subj_name  = self.subj_cb.currentText()
        dlg = _NewAssignmentDialog(class_id, subject_id, class_name, subj_name, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            homework_service.create_assignment(
                class_id, subject_id, dlg.title,
                dlg.description, dlg.deadline, dlg.max_points
            )
        except (ServiceError, PolicyViolation) as e:
            QMessageBox.warning(self, "Error", str(e)); return
        QMessageBox.information(self, "Created", "Assignment posted successfully.")
        self._load_assignments()

    def _view_submissions(self, hw: dict):
        _SubmissionsDialog(hw, self).exec()
        self._load_assignments()  # refresh submission count

    def _delete(self, assignment_id: int):
        if QMessageBox.question(
            self, "Delete Assignment",
            "Delete this assignment? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) != QMessageBox.StandardButton.Yes:
            return
        try:
            homework_service.delete_assignment(assignment_id)
        except (ServiceError, PolicyViolation) as e:
            QMessageBox.warning(self, "Cannot Delete", str(e)); return
        self._load_assignments()

    def refresh(self):
        self._load_selectors()
