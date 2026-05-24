"""Attendance module — mark daily attendance and review leave requests."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QDateEdit, QMessageBox, QAbstractItemView, QTabWidget
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QColor, QBrush
from database.db import fetch_all, fetch_one
from auth.session import session
from auth.rbac import get_class_scope
from services.student_service import student_service
from services.portal_service import portal_service
from services.base import ServiceError, PolicyViolation

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
BTN_SUCCESS = """QPushButton{background:#059669;color:white;border:none;border-radius:6px;
    padding:5px 12px;font-size:12px;font-weight:600;}QPushButton:hover{background:#047857;}"""
BTN_DANGER = """QPushButton{background:#FEF2F2;color:#DC2626;border:1px solid #FECACA;
    border-radius:6px;padding:5px 12px;font-size:12px;}QPushButton:hover{background:#FEE2E2;}"""
INPUT_STYLE = ("QComboBox,QDateEdit{border:1px solid #D1D5DB;border-radius:6px;"
               "padding:6px 10px;font-size:13px;background:white;}")

STATUS_COLORS = {
    "Present": ("#D1FAE5", "#065F46"),
    "Absent":  ("#FEE2E2", "#991B1B"),
    "Late":    ("#FEF3C7", "#92400E"),
    "Excused": ("#EDE9FE", "#4C1D95"),
}


def _scoped_classes():
    """Return classes the current user may access, respecting teacher scope."""
    scope = get_class_scope()
    if scope is None:
        return fetch_all("SELECT id, name FROM classes ORDER BY name")
    if scope:
        ph = ",".join("?" * len(scope))
        return fetch_all(
            f"SELECT id, name FROM classes WHERE id IN ({ph}) ORDER BY name", scope
        )
    return []


# ── Daily marking tab ─────────────────────────────────────────────────────────

class _MarkingTab(QWidget):
    def __init__(self):
        super().__init__()
        self._students = []
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 12, 0, 0)
        layout.setSpacing(12)

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
        for row in _scoped_classes():
            self.cls_cb.addItem(row["name"], row["id"])
        self.cls_cb.currentIndexChanged.connect(self._load_attendance)

        mark_all = QPushButton("Mark all present"); mark_all.setStyleSheet(BTN_OUTLINE)
        mark_all.clicked.connect(self._mark_all_present)
        save_btn = QPushButton("Save attendance"); save_btn.setStyleSheet(BTN_PRIMARY)
        save_btn.clicked.connect(self._save)

        bar.addWidget(lbl_d); bar.addWidget(self.date_pick)
        bar.addWidget(lbl_c); bar.addWidget(self.cls_cb)
        bar.addStretch()
        bar.addWidget(mark_all); bar.addWidget(save_btn)
        layout.addLayout(bar)

        sum_row = QHBoxLayout()
        self.lbl_present = self._badge("Present: 0", "#D1FAE5", "#065F46")
        self.lbl_absent  = self._badge("Absent: 0",  "#FEE2E2", "#991B1B")
        self.lbl_late    = self._badge("Late: 0",    "#FEF3C7", "#92400E")
        for w in [self.lbl_present, self.lbl_absent, self.lbl_late]:
            sum_row.addWidget(w)
        sum_row.addStretch()
        layout.addLayout(sum_row)

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

    @staticmethod
    def _badge(text, bg, fg):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"background:{bg};color:{fg};border-radius:6px;"
                          f"padding:4px 12px;font-size:12px;font-weight:600;")
        return lbl

    def _load_attendance(self):
        cls_id = self.cls_cb.currentData()
        if not cls_id:
            self.table.setRowCount(0); self._students = []; return

        date_str = self.date_pick.date().toString("yyyy-MM-dd")
        students = fetch_all(
            "SELECT id, admission_no, first_name, last_name FROM students "
            "WHERE class_id=? AND is_active=1 ORDER BY last_name, first_name",
            (cls_id,)
        )
        existing = {
            row["student_id"]: row
            for row in fetch_all(
                "SELECT student_id, status, notes FROM attendance WHERE class_id=? AND date=?",
                (cls_id, date_str)
            )
        }

        self.table.setRowCount(len(students))
        self._students = []
        for r, s in enumerate(students):
            self._students.append(s["id"])
            att = existing.get(s["id"])

            adm  = QTableWidgetItem(s["admission_no"])
            adm.setFlags(adm.flags() & ~Qt.ItemFlag.ItemIsEditable)
            name = QTableWidgetItem(f"{s['first_name']} {s['last_name']}")
            name.setFlags(name.flags() & ~Qt.ItemFlag.ItemIsEditable)

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
            if cb:
                counts[cb.currentText()] = counts.get(cb.currentText(), 0) + 1
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
        records = []
        for r, sid in enumerate(self._students):
            cb = self.table.cellWidget(r, 2)
            status = cb.currentText() if cb else "Present"
            notes_item = self.table.item(r, 3)
            notes = notes_item.text() if notes_item else ""
            records.append({"student_id": sid, "status": status, "notes": notes})
        try:
            saved = student_service.mark_attendance(cls_id, date_str, records)
        except (ServiceError, PolicyViolation) as e:
            QMessageBox.warning(self, "Cannot Save Attendance", str(e)); return
        QMessageBox.information(
            self, "Saved", f"Attendance saved for {saved} student(s) on {date_str}."
        )

    def refresh(self):
        # Reload the class list in case scope changed, then reload attendance
        current_id = self.cls_cb.currentData()
        self.cls_cb.blockSignals(True)
        self.cls_cb.clear()
        self.cls_cb.addItem("— Select class —", None)
        for row in _scoped_classes():
            self.cls_cb.addItem(row["name"], row["id"])
        idx = self.cls_cb.findData(current_id)
        if idx >= 0:
            self.cls_cb.setCurrentIndex(idx)
        self.cls_cb.blockSignals(False)
        self._load_attendance()


# ── Leave request review tab ──────────────────────────────────────────────────

class _LeaveReviewTab(QWidget):
    COLS = ["Student", "Class", "From", "To", "Reason", "Submitted By", "Date", "Status", "Actions"]

    def __init__(self):
        super().__init__()
        self._requests: list[dict] = []
        self._build()
        self._load("pending")

    def _build(self):
        lay = QVBoxLayout(self); lay.setContentsMargins(0, 12, 0, 0); lay.setSpacing(10)

        hdr = QHBoxLayout()
        t = QLabel("Leave Requests")
        t.setStyleSheet("font-size:15px;font-weight:700;color:#111827;")
        hdr.addWidget(t); hdr.addStretch()

        self.filter_cb = QComboBox()
        self.filter_cb.setStyleSheet(INPUT_STYLE)
        self.filter_cb.addItems(["Pending", "Approved", "Rejected"])
        self.filter_cb.currentTextChanged.connect(
            lambda t: self._load(t.lower())
        )
        ref = QPushButton("Refresh"); ref.setStyleSheet(BTN_OUTLINE)
        ref.clicked.connect(lambda: self._load(self.filter_cb.currentText().lower()))
        hdr.addWidget(self.filter_cb); hdr.addWidget(ref)
        lay.addLayout(hdr)

        self.table = QTableWidget()
        self.table.setColumnCount(len(self.COLS))
        self.table.setHorizontalHeaderLabels(self.COLS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet("""
            QTableWidget{border:1px solid #E5E7EB;border-radius:8px;
                gridline-color:#F3F4F6;font-size:12px;}
            QHeaderView::section{background:#FFF7ED;font-weight:600;
                padding:7px;border:none;border-bottom:1px solid #FED7AA;color:#9A3412;}
            QTableWidget::item{padding:5px 7px;}
        """)
        lay.addWidget(self.table)

    def _load(self, status: str = "pending"):
        try:
            self._requests = portal_service.get_all_leave_requests(status)
        except (ServiceError, PolicyViolation) as e:
            QMessageBox.warning(self, "Error", str(e)); return
        self._fill()

    def _fill(self):
        STATUS_FG = {"pending": "#F59E0B", "approved": "#059669", "rejected": "#DC2626"}
        self.table.setRowCount(len(self._requests))
        ctr = Qt.AlignmentFlag.AlignCenter

        for r, req in enumerate(self._requests):
            def cell(v, align=Qt.AlignmentFlag.AlignLeft, fg=None):
                it = QTableWidgetItem(str(v) if v is not None else "—")
                it.setFlags(Qt.ItemFlag.ItemIsEnabled)
                it.setTextAlignment(align | Qt.AlignmentFlag.AlignVCenter)
                if fg: it.setForeground(QColor(fg))
                return it

            reason = req.get("reason") or ""
            if len(reason) > 45: reason = reason[:42] + "…"

            self.table.setItem(r, 0, cell(req.get("student_name") or "—"))
            self.table.setItem(r, 1, cell(req.get("class_name") or "—", ctr))
            self.table.setItem(r, 2, cell(req.get("date_from") or "—", ctr))
            self.table.setItem(r, 3, cell(req.get("date_to") or "—", ctr))
            self.table.setItem(r, 4, cell(reason))
            self.table.setItem(r, 5, cell(req.get("submitted_by_name") or "—"))
            self.table.setItem(r, 6, cell((req.get("created_at") or "")[:10], ctr))
            st = req.get("status", "pending")
            self.table.setItem(r, 7, cell(st.title(), ctr, STATUS_FG.get(st, "#9CA3AF")))

            btn_w = QWidget()
            bl = QHBoxLayout(btn_w); bl.setContentsMargins(4, 2, 4, 2); bl.setSpacing(4)
            if st == "pending":
                ap = QPushButton("Approve"); ap.setStyleSheet(BTN_SUCCESS)
                ap.clicked.connect(lambda _, rid=req["id"]: self._review(rid, True))
                rj = QPushButton("Reject"); rj.setStyleSheet(BTN_DANGER)
                rj.clicked.connect(lambda _, rid=req["id"]: self._review(rid, False))
                bl.addWidget(ap); bl.addWidget(rj)
            self.table.setCellWidget(r, 8, btn_w)

    def _review(self, request_id: int, approved: bool):
        action = "approve" if approved else "reject"
        note = ""
        if not approved:
            from PyQt6.QtWidgets import QInputDialog
            note, ok = QInputDialog.getText(
                self, "Rejection Note",
                "Optional note for the parent:"
            )
            if not ok: return
        if QMessageBox.question(
            self, f"Confirm {action.title()}",
            f"{'Approve' if approved else 'Reject'} this leave request?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) != QMessageBox.StandardButton.Yes:
            return
        try:
            portal_service.review_leave_request(request_id, approved, note)
        except (ServiceError, PolicyViolation) as e:
            QMessageBox.warning(self, "Error", str(e)); return
        self._load(self.filter_cb.currentText().lower())

    def refresh(self):
        self._load(self.filter_cb.currentText().lower())


# ── Top-level attendance widget ───────────────────────────────────────────────

class AttendanceWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(12)

        title = QLabel("Attendance")
        title.setStyleSheet("font-size:22px;font-weight:700;color:#111827;")
        layout.addWidget(title)

        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane{border:1px solid #E5E7EB;border-radius:8px;
                background:white;padding:16px;}
            QTabBar::tab{background:#F3F4F6;color:#374151;padding:9px 20px;
                margin-right:3px;border-radius:6px 6px 0 0;font-size:13px;}
            QTabBar::tab:selected{background:white;color:#D97706;font-weight:600;
                border:1px solid #E5E7EB;border-bottom:none;}
            QTabBar::tab:hover{background:#E5E7EB;}
        """)

        self._marking_tab = _MarkingTab()
        tabs.addTab(self._marking_tab, "Daily Marking")

        self._leave_tab = None
        if session.can("leave.review"):
            self._leave_tab = _LeaveReviewTab()
            tabs.addTab(self._leave_tab, "Leave Requests")

        tabs.currentChanged.connect(lambda i: self._on_tab(i, tabs))
        layout.addWidget(tabs)

    def _on_tab(self, index: int, tabs: QTabWidget):
        w = tabs.widget(index)
        if w and hasattr(w, "refresh"):
            w.refresh()

    def refresh(self):
        self._marking_tab.refresh()
