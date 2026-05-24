"""Parent Portal — children's grades, fee balances, and leave requests."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget,
    QComboBox, QMessageBox, QAbstractItemView, QDialog,
    QFormLayout, QTextEdit, QDialogButtonBox, QDateEdit,
    QFrame, QSplitter
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QColor

from auth.session import session
from auth.rbac import get_portal_children_ids
from services.portal_service import portal_service
from services.base import ServiceError, PolicyViolation
from database.db import fetch_one

BTN_PRIMARY = """QPushButton{background:#10B981;color:white;border:none;border-radius:7px;
    padding:8px 18px;font-size:13px;font-weight:600;}QPushButton:hover{background:#059669;}
    QPushButton:disabled{background:#CBD5E1;color:#94A3B8;}"""
BTN_OUTLINE = """QPushButton{background:white;color:#374151;border:1px solid #D1D5DB;
    border-radius:7px;padding:8px 18px;font-size:13px;}QPushButton:hover{background:#F9FAFB;}"""
COMBO = """QComboBox{border:1px solid #D1D5DB;border-radius:6px;padding:6px 10px;
    font-size:13px;background:white;min-width:160px;}"""

GRADE_COLOURS = {"A": "#059669", "B": "#0891B2", "C": "#D97706", "D": "#EA580C", "F": "#DC2626"}


class LeaveRequestDialog(QDialog):
    def __init__(self, student_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Submit Leave Request")
        self.setMinimumWidth(420)
        lay = QVBoxLayout(self); lay.setSpacing(12)

        lay.addWidget(QLabel(f"<b>Student:</b> {student_name}"))

        form = QFormLayout(); form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.date_from = QDateEdit(QDate.currentDate())
        self.date_from.setCalendarPopup(True)
        self.date_from.setStyleSheet(
            "QDateEdit{border:1px solid #D1D5DB;border-radius:5px;"
            "padding:5px 8px;font-size:13px;background:white;}"
        )

        self.date_to = QDateEdit(QDate.currentDate())
        self.date_to.setCalendarPopup(True)
        self.date_to.setStyleSheet(self.date_from.styleSheet())

        self.reason_edit = QTextEdit()
        self.reason_edit.setMaximumHeight(100)
        self.reason_edit.setPlaceholderText("Reason for absence (required)…")
        self.reason_edit.setStyleSheet(
            "QTextEdit{border:1px solid #D1D5DB;border-radius:5px;"
            "padding:5px;font-size:13px;background:white;}"
        )

        form.addRow("From:", self.date_from)
        form.addRow("To:", self.date_to)
        form.addRow("Reason:", self.reason_edit)
        lay.addLayout(form)

        bb = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        bb.accepted.connect(self._validate)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def _validate(self):
        if self.date_to.date() < self.date_from.date():
            QMessageBox.warning(self, "Invalid", "End date must be after start date.")
            return
        if not self.reason_edit.toPlainText().strip():
            QMessageBox.warning(self, "Required", "Please provide a reason.")
            return
        self.accept()

    @property
    def date_from_str(self): return self.date_from.date().toString("yyyy-MM-dd")
    @property
    def date_to_str(self):   return self.date_to.date().toString("yyyy-MM-dd")
    @property
    def reason(self):        return self.reason_edit.toPlainText().strip()


class _ChildrenSelector(QComboBox):
    """Combo that lists linked children; emits child_changed when selection changes."""
    def __init__(self, children: list[dict], parent=None):
        super().__init__(parent)
        self.setStyleSheet(COMBO)
        self.setMinimumWidth(220)
        for ch in children:
            self.addItem(f"{ch['name']} ({ch['class_name'] or '—'})", ch["id"])


class _GradesTab(QWidget):
    COLS = ["Exam", "Term", "Year", "Subject", "Score", "Grade"]

    def __init__(self, children: list[dict]):
        super().__init__()
        self._children = children
        self._build()
        if children:
            self._load()

    def _build(self):
        lay = QVBoxLayout(self); lay.setContentsMargins(0, 12, 0, 0); lay.setSpacing(10)

        sel_row = QHBoxLayout(); sel_row.setSpacing(8)
        l = QLabel("Child:"); l.setStyleSheet("font-size:13px;color:#374151;font-weight:600;")
        self.child_cb = _ChildrenSelector(self._children)
        self.child_cb.currentIndexChanged.connect(self._load)
        sel_row.addWidget(l); sel_row.addWidget(self.child_cb); sel_row.addStretch()
        ref = QPushButton("Refresh"); ref.setStyleSheet(BTN_OUTLINE)
        ref.clicked.connect(self._load)
        sel_row.addWidget(ref)
        lay.addLayout(sel_row)

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
            QHeaderView::section{background:#ECFDF5;font-weight:600;
                padding:7px;border:none;border-bottom:1px solid #A7F3D0;color:#065F46;}
            QTableWidget::item{padding:5px 7px;}
        """)
        lay.addWidget(self.table)

    def _load(self):
        student_id = self.child_cb.currentData()
        if not student_id:
            return
        try:
            rows = portal_service.get_child_grades(student_id)
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

    def refresh(self): self._load()


class _FeesTab(QWidget):
    def __init__(self, children: list[dict]):
        super().__init__()
        self._children = children
        self._build()
        if children:
            self._load()

    def _build(self):
        lay = QVBoxLayout(self); lay.setContentsMargins(0, 12, 0, 0); lay.setSpacing(10)

        sel_row = QHBoxLayout(); sel_row.setSpacing(8)
        l = QLabel("Child:"); l.setStyleSheet("font-size:13px;color:#374151;font-weight:600;")
        self.child_cb = _ChildrenSelector(self._children)
        self.child_cb.currentIndexChanged.connect(self._load)
        sel_row.addWidget(l); sel_row.addWidget(self.child_cb); sel_row.addStretch()
        lay.addLayout(sel_row)

        # Summary cards
        cards = QHBoxLayout(); cards.setSpacing(12)
        self._card_due  = self._make_card("Total Due",  "#FEF2F2", "#DC2626")
        self._card_paid = self._make_card("Total Paid", "#F0FDF4", "#059669")
        self._card_bal  = self._make_card("Balance",    "#FEF3C7", "#D97706")
        for c in [self._card_due, self._card_paid, self._card_bal]:
            cards.addWidget(c)
        lay.addLayout(cards)

        # Allocation table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Fee Item", "Year", "Term", "Due", "Paid"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet("""
            QTableWidget{border:1px solid #E5E7EB;border-radius:8px;
                gridline-color:#F3F4F6;font-size:12px;}
            QHeaderView::section{background:#ECFDF5;font-weight:600;
                padding:7px;border:none;border-bottom:1px solid #A7F3D0;color:#065F46;}
        """)
        lay.addWidget(self.table)

    @staticmethod
    def _make_card(label: str, bg: str, fg: str) -> QFrame:
        f = QFrame()
        f.setStyleSheet(
            f"QFrame{{background:{bg};border-radius:8px;border:1px solid {fg}33;}}"
        )
        v = QVBoxLayout(f); v.setContentsMargins(14, 10, 14, 10); v.setSpacing(2)
        lbl = QLabel(label); lbl.setStyleSheet(f"color:{fg};font-size:11px;font-weight:600;")
        val = QLabel("—"); val.setStyleSheet(f"color:{fg};font-size:18px;font-weight:700;")
        val.setObjectName("val")
        v.addWidget(lbl); v.addWidget(val)
        return f

    def _set_card(self, card: QFrame, value: float):
        val = card.findChild(QLabel, "val")
        if val:
            val.setText(f"TZS {value:,.0f}")

    def _load(self):
        student_id = self.child_cb.currentData()
        if not student_id:
            return
        try:
            summary = portal_service.get_child_fee_summary(student_id)
        except (ServiceError, PolicyViolation) as e:
            QMessageBox.warning(self, "Error", str(e)); return

        self._set_card(self._card_due,  summary["total_due"])
        self._set_card(self._card_paid, summary["total_paid"])
        self._set_card(self._card_bal,  summary["balance"])

        allocs = summary["allocations"]
        self.table.setRowCount(len(allocs))
        ctr = Qt.AlignmentFlag.AlignCenter
        for r, row in enumerate(allocs):
            def cell(v, align=Qt.AlignmentFlag.AlignLeft, fg=None):
                it = QTableWidgetItem(str(v) if v is not None else "—")
                it.setFlags(Qt.ItemFlag.ItemIsEnabled)
                it.setTextAlignment(align | Qt.AlignmentFlag.AlignVCenter)
                if fg: it.setForeground(QColor(fg))
                return it
            self.table.setItem(r, 0, cell(row.get("fee_name") or "—"))
            self.table.setItem(r, 1, cell(row.get("year_label") or "—", ctr))
            self.table.setItem(r, 2, cell(f"T{row.get('term','?')}", ctr))
            self.table.setItem(r, 3, cell(
                f"TZS {row.get('amount_due',0):,.0f}", ctr, "#DC2626"
            ))
            self.table.setItem(r, 4, cell(
                f"TZS {row.get('amount_paid',0):,.0f}", ctr, "#059669"
            ))

    def refresh(self): self._load()


class _LeaveTab(QWidget):
    COLS = ["Student", "From", "To", "Reason", "Submitted", "Status"]

    def __init__(self, children: list[dict]):
        super().__init__()
        self._children = children
        self._build()
        if children:
            self._load()

    def _build(self):
        lay = QVBoxLayout(self); lay.setContentsMargins(0, 12, 0, 0); lay.setSpacing(10)

        hdr = QHBoxLayout()
        t = QLabel("Leave Requests")
        t.setStyleSheet("font-size:15px;font-weight:700;color:#111827;")
        hdr.addWidget(t); hdr.addStretch()

        sel_row = QHBoxLayout(); sel_row.setSpacing(8)
        l = QLabel("Child:"); l.setStyleSheet("font-size:13px;color:#374151;font-weight:600;")
        self.child_cb = _ChildrenSelector(self._children)
        self.child_cb.currentIndexChanged.connect(self._load)

        new_btn = QPushButton("+ New Request"); new_btn.setStyleSheet(BTN_PRIMARY)
        new_btn.clicked.connect(self._new_request)

        sel_row.addWidget(l); sel_row.addWidget(self.child_cb)
        sel_row.addStretch(); sel_row.addWidget(new_btn)
        lay.addLayout(hdr)
        lay.addLayout(sel_row)

        STATUS_COLORS = {"pending": "#F59E0B", "approved": "#059669", "rejected": "#DC2626"}

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
            QHeaderView::section{background:#ECFDF5;font-weight:600;
                padding:7px;border:none;border-bottom:1px solid #A7F3D0;color:#065F46;}
            QTableWidget::item{padding:5px 7px;}
        """)
        lay.addWidget(self.table)
        self._STATUS_COLORS = STATUS_COLORS

    def _load(self):
        student_id = self.child_cb.currentData()
        if not student_id:
            return
        try:
            rows = portal_service.get_my_leave_requests(student_id)
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
            self.table.setItem(r, 0, cell(row.get("student_name") or "—"))
            self.table.setItem(r, 1, cell(row.get("date_from") or "—", ctr))
            self.table.setItem(r, 2, cell(row.get("date_to") or "—", ctr))
            reason = row.get("reason") or ""
            if len(reason) > 50: reason = reason[:47] + "…"
            self.table.setItem(r, 3, cell(reason))
            self.table.setItem(r, 4, cell((row.get("created_at") or "")[:10], ctr))
            st = row.get("status", "pending")
            self.table.setItem(r, 5, cell(
                st.title(), ctr, self._STATUS_COLORS.get(st, "#9CA3AF")
            ))

    def _new_request(self):
        student_id = self.child_cb.currentData()
        if not student_id:
            return
        student = fetch_one(
            "SELECT first_name||' '||last_name AS name FROM students WHERE id=?",
            (student_id,)
        )
        name = student["name"] if student else "—"
        dlg = LeaveRequestDialog(name, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            portal_service.submit_leave_request(
                student_id, dlg.date_from_str, dlg.date_to_str, dlg.reason
            )
        except (ServiceError, PolicyViolation) as e:
            QMessageBox.warning(self, "Error", str(e)); return
        QMessageBox.information(
            self, "Submitted",
            "Your leave request has been submitted. "
            "The school will review it and notify you."
        )
        self._load()

    def refresh(self): self._load()


class ParentPortalWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 20, 28, 20); lay.setSpacing(0)

        # Header
        hdr = QHBoxLayout()
        title = QLabel("Parent Portal")
        title.setStyleSheet("font-size:22px;font-weight:700;color:#111827;")
        hdr.addWidget(title); hdr.addStretch()
        lay.addLayout(hdr)
        lay.addSpacing(14)

        # Load linked children
        try:
            children = portal_service.get_children()
        except (ServiceError, PolicyViolation):
            children = []

        if not children:
            no_link = QLabel(
                "Your account is not linked to any student records. "
                "Please contact the school administrator."
            )
            no_link.setWordWrap(True)
            no_link.setStyleSheet(
                "background:#FEF2F2;color:#DC2626;border-radius:6px;"
                "padding:14px;font-size:13px;"
            )
            lay.addWidget(no_link)
            return

        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane{border:1px solid #E5E7EB;border-radius:8px;
                background:white;padding:16px;}
            QTabBar::tab{background:#F3F4F6;color:#374151;padding:9px 20px;
                margin-right:3px;border-radius:6px 6px 0 0;font-size:13px;}
            QTabBar::tab:selected{background:white;color:#059669;font-weight:600;
                border:1px solid #E5E7EB;border-bottom:none;}
        """)

        self._grades_tab = _GradesTab(children)
        self._fees_tab   = _FeesTab(children)
        self._leave_tab  = _LeaveTab(children)
        tabs.addTab(self._grades_tab, "Academic Progress")
        tabs.addTab(self._fees_tab,   "Fee Account")
        tabs.addTab(self._leave_tab,  "Leave Requests")
        tabs.currentChanged.connect(
            lambda i: [self._grades_tab, self._fees_tab, self._leave_tab][i].refresh()
        )
        lay.addWidget(tabs)

    def refresh(self):
        pass  # children list is static per session; individual tabs auto-refresh
