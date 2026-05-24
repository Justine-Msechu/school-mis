"""Grade entry tab — teachers enter scores for their class/subject/exam."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QDoubleSpinBox, QLineEdit, QMessageBox, QAbstractItemView,
    QDialog, QFormLayout, QDialogButtonBox, QTextEdit
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from database.db import fetch_all
from auth.session import session
from services.grades_service import grades_service
from services.base import ServiceError, PolicyViolation

BTN_PRIMARY = """QPushButton{background:#0891B2;color:white;border:none;border-radius:7px;
    padding:8px 18px;font-size:13px;font-weight:600;}QPushButton:hover{background:#0E7490;}
    QPushButton:disabled{background:#CBD5E1;color:#94A3B8;}"""
BTN_OUTLINE = """QPushButton{background:white;color:#374151;border:1px solid #D1D5DB;
    border-radius:7px;padding:8px 18px;font-size:13px;}QPushButton:hover{background:#F9FAFB;}
    QPushButton:disabled{background:#F3F4F6;color:#9CA3AF;}"""
BTN_SUCCESS = """QPushButton{background:#059669;color:white;border:none;border-radius:7px;
    padding:8px 18px;font-size:13px;font-weight:600;}QPushButton:hover{background:#047857;}
    QPushButton:disabled{background:#CBD5E1;color:#94A3B8;}"""
BTN_WARN = """QPushButton{background:#FEF3C7;color:#92400E;border:1px solid #FDE68A;
    border-radius:6px;padding:4px 10px;font-size:11px;font-weight:600;}
    QPushButton:hover{background:#FDE68A;}"""
COMBO = """QComboBox{border:1px solid #D1D5DB;border-radius:6px;padding:6px 10px;
    font-size:13px;background:white;}"""

_STATUS_LABEL = {
    "draft":            "Draft",
    "submitted_locked": "Submitted (Locked)",
    "approved":         "Approved",
}
_STATUS_COLOR = {
    "Draft":              "#F59E0B",
    "Submitted (Locked)": "#3B82F6",
    "Approved":           "#059669",
    "Not Entered":        "#9CA3AF",
}


class ChangeRequestDialog(QDialog):
    """Collect a proposed score + reason when requesting a change on a locked grade."""

    def __init__(self, student_name: str, current_score, current_max, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Request Grade Change")
        self.setMinimumWidth(420)
        lay = QVBoxLayout(self)
        lay.setSpacing(12)

        info = QLabel(f"<b>Student:</b> {student_name}")
        info.setStyleSheet("font-size:13px;padding:4px 0;")
        lay.addWidget(info)

        note = QLabel(
            "This grade is locked. Submitting a change request will send it to "
            "an academic officer for review."
        )
        note.setWordWrap(True)
        note.setStyleSheet(
            "background:#FEF3C7;color:#92400E;border-radius:5px;"
            "padding:8px 10px;font-size:12px;"
        )
        lay.addWidget(note)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        spin_style = (
            "QDoubleSpinBox{border:1px solid #D1D5DB;border-radius:4px;"
            "padding:4px 8px;font-size:13px;background:white;}"
        )

        self.score_spin = QDoubleSpinBox()
        self.score_spin.setRange(0, 9999)
        self.score_spin.setDecimals(1)
        self.score_spin.setStyleSheet(spin_style)
        if current_score is not None:
            self.score_spin.setValue(float(current_score))

        self.max_spin = QDoubleSpinBox()
        self.max_spin.setRange(1, 9999)
        self.max_spin.setDecimals(0)
        self.max_spin.setStyleSheet(spin_style)
        self.max_spin.setValue(float(current_max or 100))

        self.reason_edit = QTextEdit()
        self.reason_edit.setMaximumHeight(90)
        self.reason_edit.setPlaceholderText("Reason for the change (required)…")
        self.reason_edit.setStyleSheet(
            "QTextEdit{border:1px solid #D1D5DB;border-radius:5px;"
            "padding:5px;font-size:13px;background:white;}"
        )

        form.addRow("Proposed Score:", self.score_spin)
        form.addRow("Out of (Max):", self.max_spin)
        form.addRow("Reason:", self.reason_edit)
        lay.addLayout(form)

        bb = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        bb.accepted.connect(self._validate)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def _validate(self):
        if not self.reason_edit.toPlainText().strip():
            QMessageBox.warning(self, "Required", "Please provide a reason for the change.")
            return
        self.accept()

    @property
    def proposed_score(self) -> float:
        return self.score_spin.value()

    @property
    def proposed_max(self) -> float:
        return self.max_spin.value()

    @property
    def reason_text(self) -> str:
        return self.reason_edit.toPlainText().strip()


class GradeEntryTab(QWidget):
    COLS = ["Student", "Adm No", "Score", "/ Max", "Grade", "Remarks", "Status", "Actions"]

    def __init__(self):
        super().__init__()
        self._exam_id = None
        self._class_id = None
        self._subject_id = None
        self._sheet = []
        self._build()
        self._load_selectors()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 16, 0, 0)
        lay.setSpacing(12)

        # ── Selector row ──────────────────────────────────────────────────────
        sel = QHBoxLayout(); sel.setSpacing(10)

        self.exam_cb = QComboBox(); self.exam_cb.setStyleSheet(COMBO)
        self.exam_cb.setMinimumWidth(200)
        self.class_cb = QComboBox(); self.class_cb.setStyleSheet(COMBO)
        self.class_cb.setMinimumWidth(140)
        self.subj_cb = QComboBox(); self.subj_cb.setStyleSheet(COMBO)
        self.subj_cb.setMinimumWidth(160)

        self.load_btn = QPushButton("Load Sheet"); self.load_btn.setStyleSheet(BTN_OUTLINE)
        self.load_btn.clicked.connect(self._load_sheet)

        for lbl, wgt in [("Exam:", self.exam_cb), ("Class:", self.class_cb),
                          ("Subject:", self.subj_cb)]:
            l = QLabel(lbl); l.setStyleSheet("font-size:13px;color:#374151;font-weight:600;")
            sel.addWidget(l); sel.addWidget(wgt)
        sel.addWidget(self.load_btn)
        sel.addStretch()
        lay.addLayout(sel)

        # ── Status info bar ───────────────────────────────────────────────────
        self.info_bar = QLabel("")
        self.info_bar.setVisible(False)
        self.info_bar.setStyleSheet(
            "background:#EFF6FF;color:#1D4ED8;border-radius:6px;"
            "padding:8px 12px;font-size:12px;"
        )
        lay.addWidget(self.info_bar)

        # ── Lock warning bar (shown when batch has locked grades) ─────────────
        self.lock_bar = QLabel(
            "Some grades in this batch are locked (submitted or approved). "
            "Use 'Request Change' on individual rows to propose corrections."
        )
        self.lock_bar.setWordWrap(True)
        self.lock_bar.setVisible(False)
        self.lock_bar.setStyleSheet(
            "background:#FEF3C7;color:#92400E;border-radius:6px;"
            "padding:8px 12px;font-size:12px;"
        )
        lay.addWidget(self.lock_bar)

        # ── Grade table ───────────────────────────────────────────────────────
        self.table = QTableWidget()
        self.table.setColumnCount(len(self.COLS))
        self.table.setHorizontalHeaderLabels(self.COLS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setStyleSheet("""
            QTableWidget{border:1px solid #E5E7EB;border-radius:8px;
                gridline-color:#F3F4F6;font-size:13px;}
            QHeaderView::section{background:#F0F9FF;font-weight:600;
                padding:8px;border:none;border-bottom:1px solid #BAE6FD;color:#0369A1;}
            QTableWidget::item{padding:4px 8px;}
        """)
        lay.addWidget(self.table)

        # ── Action buttons ────────────────────────────────────────────────────
        btn_row = QHBoxLayout(); btn_row.addStretch()
        self.save_btn = QPushButton("Save as Draft")
        self.save_btn.setStyleSheet(BTN_OUTLINE)
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self._save_draft)

        self.submit_btn = QPushButton("Finalize & Submit")
        self.submit_btn.setStyleSheet(BTN_SUCCESS)
        self.submit_btn.setEnabled(False)
        self.submit_btn.clicked.connect(self._submit)

        btn_row.addWidget(self.save_btn); btn_row.addWidget(self.submit_btn)
        lay.addLayout(btn_row)

    # ── Populate selectors ────────────────────────────────────────────────────

    def _load_selectors(self):
        try:
            exams = grades_service.get_exams()
        except (ServiceError, PolicyViolation):
            exams = []

        self.exam_cb.clear()
        self.exam_cb.addItem("-- Select exam --", None)
        for e in exams:
            label = f"{e['name']} (T{e['term']}) [{e['status']}]"
            self.exam_cb.addItem(label, e["id"])

        classes = fetch_all("SELECT id, name FROM classes ORDER BY name")
        self.class_cb.clear()
        self.class_cb.addItem("-- Select class --", None)
        for c in classes:
            self.class_cb.addItem(c["name"], c["id"])

        self.class_cb.currentIndexChanged.connect(self._on_class_changed)
        self._on_class_changed()

    def _on_class_changed(self):
        class_id = self.class_cb.currentData()
        self.subj_cb.clear()
        self.subj_cb.addItem("-- Select subject --", None)
        if not class_id:
            return
        if session.role in ("subject_teacher", "class_teacher"):
            try:
                subjects = grades_service.get_subjects_for_teacher(class_id)
            except (ServiceError, PolicyViolation):
                subjects = []
        else:
            subjects = fetch_all("SELECT * FROM subjects ORDER BY name")
        for s in subjects:
            self.subj_cb.addItem(s["name"], s["id"])

    def _load_sheet(self):
        exam_id    = self.exam_cb.currentData()
        class_id   = self.class_cb.currentData()
        subject_id = self.subj_cb.currentData()
        if not all([exam_id, class_id, subject_id]):
            QMessageBox.warning(self, "Required", "Select an exam, class, and subject first.")
            return
        try:
            sheet = grades_service.get_grade_sheet(exam_id, class_id, subject_id)
        except (ServiceError, PolicyViolation) as e:
            QMessageBox.warning(self, "Error", str(e)); return

        self._exam_id    = exam_id
        self._class_id   = class_id
        self._subject_id = subject_id
        self._sheet      = sheet
        self._fill_table(sheet)

        has_editable = any(
            (r.get("status") or "not_entered") not in ("submitted_locked", "approved")
            for r in sheet
        )
        self.save_btn.setEnabled(has_editable)
        self.submit_btn.setEnabled(has_editable)

    def _fill_table(self, sheet: list[dict]):
        self.table.setRowCount(len(sheet))
        self._score_widgets  = {}
        self._max_widgets    = {}
        self._remark_widgets = {}

        can_request = session.can("grades.change_request")
        has_locked  = False

        for r, row in enumerate(sheet):
            status      = row.get("status") or "not_entered"
            is_locked   = status in ("submitted_locked", "approved")
            grade_id    = row.get("grade_id")
            if is_locked:
                has_locked = True

            # Name / Adm No (always read-only)
            for c, v in enumerate([row["student_name"], row["admission_no"]]):
                it = QTableWidgetItem(v)
                it.setFlags(Qt.ItemFlag.ItemIsEnabled)
                self.table.setItem(r, c, it)

            # Score spinner
            score_spin = QDoubleSpinBox()
            score_spin.setRange(0, 9999); score_spin.setDecimals(1)
            if row.get("score") is not None:
                score_spin.setValue(float(row["score"]))
            score_spin.setEnabled(not is_locked)
            score_spin.setStyleSheet(
                "QDoubleSpinBox{border:1px solid #D1D5DB;border-radius:4px;"
                "padding:3px 6px;font-size:13px;background:white;}"
                "QDoubleSpinBox:disabled{background:#F3F4F6;color:#9CA3AF;}"
            )
            self.table.setCellWidget(r, 2, score_spin)
            self._score_widgets[r] = score_spin

            # Max score spinner
            max_spin = QDoubleSpinBox()
            max_spin.setRange(1, 9999); max_spin.setDecimals(0)
            max_spin.setValue(float(row.get("max_score") or 100))
            max_spin.setEnabled(not is_locked)
            max_spin.setStyleSheet(
                "QDoubleSpinBox{border:1px solid #D1D5DB;border-radius:4px;"
                "padding:3px 6px;font-size:13px;background:white;}"
                "QDoubleSpinBox:disabled{background:#F3F4F6;color:#9CA3AF;}"
            )
            self.table.setCellWidget(r, 3, max_spin)
            self._max_widgets[r] = max_spin

            # Grade letter (computed — read-only display)
            grade_item = QTableWidgetItem(row.get("grade_letter") or "—")
            grade_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            grade_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._colour_grade(grade_item, row.get("grade_letter"))
            self.table.setItem(r, 4, grade_item)

            # Remarks
            rem = QLineEdit(row.get("remarks") or "")
            rem.setEnabled(not is_locked)
            rem.setStyleSheet(
                "QLineEdit{border:1px solid #D1D5DB;border-radius:4px;"
                "padding:3px 6px;font-size:12px;background:white;}"
                "QLineEdit:disabled{background:#F3F4F6;color:#9CA3AF;}"
            )
            self.table.setCellWidget(r, 5, rem)
            self._remark_widgets[r] = rem

            # Status badge
            st_label = _STATUS_LABEL.get(status, "Not Entered")
            st_item  = QTableWidgetItem(st_label)
            st_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            st_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            st_item.setForeground(QColor(_STATUS_COLOR.get(st_label, "#9CA3AF")))
            self.table.setItem(r, 6, st_item)

            # Actions column — "Request Change" button for locked grades
            if is_locked and grade_id and can_request:
                btn_w = QWidget()
                bl = QHBoxLayout(btn_w)
                bl.setContentsMargins(4, 2, 4, 2); bl.setSpacing(0)
                req_btn = QPushButton("Request Change")
                req_btn.setStyleSheet(BTN_WARN)
                req_btn.clicked.connect(
                    lambda _, gid=grade_id, sn=row["student_name"],
                           sc=row.get("score"), mx=row.get("max_score"):
                    self._request_change(gid, sn, sc, mx)
                )
                bl.addWidget(req_btn)
                self.table.setCellWidget(r, 7, btn_w)
            else:
                self.table.setItem(r, 7, QTableWidgetItem(""))

            # Live grade letter update (only for editable rows)
            if not is_locked:
                score_spin.valueChanged.connect(
                    lambda val, gi=grade_item, ms=max_spin:
                    self._update_letter(val, ms, gi)
                )

        # Info bars
        draft     = sum(1 for s in sheet if s.get("status") == "draft")
        locked_ct = sum(1 for s in sheet if s.get("status") == "submitted_locked")
        approved  = sum(1 for s in sheet if s.get("status") == "approved")
        total     = len(sheet)
        self.info_bar.setText(
            f"{total} students — {draft} draft, {locked_ct} submitted (locked), {approved} approved"
        )
        self.info_bar.setVisible(True)
        self.lock_bar.setVisible(has_locked)

    @staticmethod
    def _colour_grade(item: QTableWidgetItem, letter: str | None):
        colours = {"A": "#059669", "B": "#0891B2", "C": "#D97706",
                   "D": "#EA580C", "F": "#DC2626"}
        item.setForeground(QColor(colours.get(letter, "#9CA3AF")))

    @staticmethod
    def _update_letter(score: float, max_spin: QDoubleSpinBox, grade_item: QTableWidgetItem):
        from services.grades_service import _letter_grade
        letter = _letter_grade(score, max_spin.value() or 100)
        grade_item.setText(letter)
        GradeEntryTab._colour_grade(grade_item, letter)

    def _collect_entries(self) -> list[dict]:
        """Collect only editable (non-locked) rows."""
        entries = []
        for r, row in enumerate(self._sheet):
            status = row.get("status") or "not_entered"
            if status in ("submitted_locked", "approved"):
                continue
            score_w = self._score_widgets.get(r)
            max_w   = self._max_widgets.get(r)
            rem_w   = self._remark_widgets.get(r)
            if score_w is None:
                continue
            entries.append({
                "student_id": row["student_id"],
                "score":      score_w.value(),
                "max_score":  max_w.value() if max_w else 100,
                "remarks":    rem_w.text().strip() if rem_w else "",
            })
        return entries

    def _save_draft(self):
        if self._exam_id is None:
            return
        try:
            n = grades_service.save_grades(
                self._exam_id, self._class_id, self._subject_id,
                self._collect_entries()
            )
        except (ServiceError, PolicyViolation) as e:
            QMessageBox.warning(self, "Cannot Save", str(e)); return
        QMessageBox.information(self, "Saved", f"{n} grade(s) saved as draft.")
        self._load_sheet()

    def _submit(self):
        if self._exam_id is None:
            return
        if QMessageBox.question(
            self, "Finalize & Submit",
            "Submit these grades for approval?\n\n"
            "Once submitted, grades will be locked and can only be changed "
            "via a formal change request.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) != QMessageBox.StandardButton.Yes:
            return
        try:
            grades_service.save_grades(
                self._exam_id, self._class_id, self._subject_id,
                self._collect_entries()
            )
            n = grades_service.submit_grades(
                self._exam_id, self._class_id, self._subject_id
            )
        except (ServiceError, PolicyViolation) as e:
            QMessageBox.warning(self, "Cannot Submit", str(e)); return
        QMessageBox.information(self, "Submitted", f"{n} grade(s) submitted for approval and locked.")
        self._load_sheet()

    def _request_change(self, grade_id: int, student_name: str,
                        current_score, current_max):
        dlg = ChangeRequestDialog(student_name, current_score, current_max, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            grades_service.request_grade_change(
                grade_id, dlg.proposed_score, dlg.proposed_max, dlg.reason_text
            )
        except (ServiceError, PolicyViolation) as e:
            QMessageBox.warning(self, "Error", str(e)); return
        QMessageBox.information(
            self, "Request Submitted",
            "Your change request has been submitted for review by an academic officer."
        )

    def refresh(self):
        self._load_selectors()
