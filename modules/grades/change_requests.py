"""Grade Change Requests tab — review and act on locked/approved grade amendments."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QMessageBox, QAbstractItemView, QDialog, QFormLayout,
    QTextEdit, QDialogButtonBox, QTabWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from services.grades_service import grades_service
from services.base import ServiceError, PolicyViolation
from auth.session import session

BTN_SUCCESS = """QPushButton{background:#059669;color:white;border:none;border-radius:6px;
    padding:5px 14px;font-size:12px;font-weight:600;}QPushButton:hover{background:#047857;}"""
BTN_DANGER  = """QPushButton{background:#FEF2F2;color:#DC2626;border:1px solid #FECACA;
    border-radius:6px;padding:5px 12px;font-size:12px;}QPushButton:hover{background:#FEE2E2;}"""
BTN_OUTLINE = """QPushButton{background:white;color:#374151;border:1px solid #D1D5DB;
    border-radius:7px;padding:8px 14px;font-size:13px;}QPushButton:hover{background:#F9FAFB;}"""
COMBO = """QComboBox{border:1px solid #D1D5DB;border-radius:6px;padding:6px 10px;
    font-size:13px;background:white;min-width:130px;}"""

STATUS_COLORS = {"pending": "#F59E0B", "approved": "#059669", "rejected": "#DC2626"}

COLS = ["#", "Student", "Class", "Exam", "Subject",
        "Current", "Proposed", "Reason", "Requested By", "Status", "Actions"]


class RejectDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Reject Change Request")
        self.setMinimumWidth(380)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("Reason for rejection (optional):"))
        self.note = QTextEdit()
        self.note.setMaximumHeight(100)
        self.note.setStyleSheet("border:1px solid #D1D5DB;border-radius:5px;padding:5px;font-size:13px;")
        lay.addWidget(self.note)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    @property
    def rejection_note(self) -> str:
        return self.note.toPlainText().strip()


class _RequestsTable(QWidget):
    def __init__(self, status_filter: str | None, parent=None):
        super().__init__(parent)
        self._status = status_filter
        self._requests: list[dict] = []
        self._build()

    def _build(self):
        lay = QVBoxLayout(self); lay.setContentsMargins(0, 8, 0, 0); lay.setSpacing(8)

        bar = QHBoxLayout(); bar.setSpacing(8)
        ref_btn = QPushButton("Refresh"); ref_btn.setStyleSheet(BTN_OUTLINE)
        ref_btn.clicked.connect(self._load)
        bar.addWidget(ref_btn); bar.addStretch()
        lay.addLayout(bar)

        self.table = QTableWidget()
        self.table.setColumnCount(len(COLS))
        self.table.setHorizontalHeaderLabels(COLS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setStyleSheet("""
            QTableWidget{border:1px solid #E5E7EB;border-radius:8px;
                gridline-color:#F3F4F6;font-size:12px;}
            QHeaderView::section{background:#FFF7ED;font-weight:600;
                padding:7px;border:none;border-bottom:1px solid #FED7AA;color:#9A3412;}
            QTableWidget::item{padding:5px 7px;}
        """)
        lay.addWidget(self.table)

    def _load(self):
        try:
            self._requests = grades_service.get_change_requests(status=self._status)
        except (ServiceError, PolicyViolation) as e:
            QMessageBox.warning(self, "Error", str(e)); return
        self._fill()

    def _fill(self):
        can_review = session.can("grades.change_request.review")
        self.table.setRowCount(len(self._requests))
        for r, req in enumerate(self._requests):
            def cell(v, align=Qt.AlignmentFlag.AlignLeft, fg=None):
                it = QTableWidgetItem(str(v) if v is not None else "—")
                it.setFlags(Qt.ItemFlag.ItemIsEnabled)
                it.setTextAlignment(align | Qt.AlignmentFlag.AlignVCenter)
                if fg: it.setForeground(QColor(fg))
                return it
            ctr = Qt.AlignmentFlag.AlignCenter
            st  = req.get("status", "pending")

            self.table.setItem(r, 0,  cell(f"#{req['id']}", ctr))
            self.table.setItem(r, 1,  cell(req.get("student_name") or "—"))
            self.table.setItem(r, 2,  cell(req.get("class_name") or "—", ctr))
            self.table.setItem(r, 3,  cell(req.get("exam_name") or "—"))
            self.table.setItem(r, 4,  cell(req.get("subject_name") or "—"))
            cur_s  = req.get("current_score")
            cur_m  = req.get("current_max") or 100
            pro_s  = req.get("proposed_score")
            pro_m  = req.get("proposed_max") or 100
            self.table.setItem(r, 5,  cell(
                f"{cur_s:.0f}/{cur_m:.0f} ({req.get('grade_letter','?')})" if cur_s is not None else "—", ctr
            ))
            self.table.setItem(r, 6,  cell(
                f"{pro_s:.0f}/{pro_m:.0f}" if pro_s is not None else "—", ctr
            ))
            reason = req.get("reason") or "—"
            if len(reason) > 50: reason = reason[:47] + "…"
            self.table.setItem(r, 7,  cell(reason))
            self.table.setItem(r, 8,  cell(req.get("requested_by_name") or "—"))
            self.table.setItem(r, 9,  cell(st.title(), ctr, STATUS_COLORS.get(st)))

            if can_review and st == "pending":
                btn_w = QWidget()
                bl = QHBoxLayout(btn_w); bl.setContentsMargins(4, 2, 4, 2); bl.setSpacing(4)
                ok_btn = QPushButton("Approve"); ok_btn.setStyleSheet(BTN_SUCCESS)
                ok_btn.clicked.connect(lambda _, rid=req["id"]: self._approve(rid))
                rej_btn = QPushButton("Reject"); rej_btn.setStyleSheet(BTN_DANGER)
                rej_btn.clicked.connect(lambda _, rid=req["id"]: self._reject(rid))
                bl.addWidget(ok_btn); bl.addWidget(rej_btn)
                self.table.setCellWidget(r, 10, btn_w)
            else:
                rv = req.get("review_note") or ""
                self.table.setItem(r, 10, cell(rv if rv else st.title(), ctr, "#9CA3AF"))

    def _approve(self, request_id: int):
        req = next((r for r in self._requests if r["id"] == request_id), None)
        if not req: return
        msg = (f"Approve change request #{request_id}?\n\n"
               f"Student: {req.get('student_name','')}\n"
               f"Current: {req.get('current_score','?')}/{req.get('current_max','?')}\n"
               f"Proposed: {req.get('proposed_score','?')}/{req.get('proposed_max','?')}\n\n"
               f"This will update the grade and create an audit record.")
        if QMessageBox.question(
            self, "Confirm Approval", msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) != QMessageBox.StandardButton.Yes:
            return
        try:
            grades_service.approve_change_request(request_id)
        except (ServiceError, PolicyViolation) as e:
            QMessageBox.warning(self, "Error", str(e)); return
        QMessageBox.information(self, "Approved", "Grade change approved and applied.")
        self._load()

    def _reject(self, request_id: int):
        dlg = RejectDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            grades_service.reject_change_request(request_id, dlg.rejection_note)
        except (ServiceError, PolicyViolation) as e:
            QMessageBox.warning(self, "Error", str(e)); return
        self._load()

    def refresh(self):
        self._load()


class ChangeRequestsTab(QWidget):
    def __init__(self):
        super().__init__()
        self._build()

    def _build(self):
        lay = QVBoxLayout(self); lay.setContentsMargins(0, 8, 0, 0); lay.setSpacing(0)

        info = QLabel(
            "Grade Change Requests allow teachers to propose corrections to locked or approved grades. "
            "All changes are audited and require Academic Officer / Head Teacher approval."
        )
        info.setWordWrap(True)
        info.setStyleSheet(
            "background:#FFF7ED;color:#9A3412;border-radius:6px;padding:10px 14px;"
            "font-size:12px;margin-bottom:8px;"
        )
        lay.addWidget(info)

        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane{border:none;}
            QTabBar::tab{padding:7px 18px;font-size:12px;color:#6B7280;
                border:none;border-bottom:2px solid transparent;}
            QTabBar::tab:selected{color:#EA580C;border-bottom:2px solid #EA580C;font-weight:600;}
        """)
        self._pending  = _RequestsTable("pending")
        self._approved = _RequestsTable("approved")
        self._rejected = _RequestsTable("rejected")
        tabs.addTab(self._pending,  "Pending")
        tabs.addTab(self._approved, "Approved")
        tabs.addTab(self._rejected, "Rejected")
        tabs.currentChanged.connect(
            lambda i: [self._pending, self._approved, self._rejected][i].refresh()
        )
        lay.addWidget(tabs)
        self._pending.refresh()

    def refresh(self):
        self._pending.refresh()
