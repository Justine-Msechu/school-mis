"""Loans tab — view all loans, return books, mark lost, track overdue fines."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QMessageBox, QAbstractItemView, QTabWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from services.library_service import library_service
from services.base import ServiceError, PolicyViolation
from auth.session import session

BTN_SUCCESS = """QPushButton{background:#059669;color:white;border:none;border-radius:6px;
    padding:5px 14px;font-size:12px;font-weight:600;}QPushButton:hover{background:#047857;}"""
BTN_DANGER = """QPushButton{background:#FEF2F2;color:#DC2626;border:1px solid #FECACA;
    border-radius:6px;padding:5px 12px;font-size:12px;}QPushButton:hover{background:#FEE2E2;}"""
BTN_OUTLINE = """QPushButton{background:white;color:#374151;border:1px solid #D1D5DB;
    border-radius:7px;padding:8px 14px;font-size:13px;}QPushButton:hover{background:#F9FAFB;}"""

STATUS_COLORS = {
    "active":   "#2563EB",
    "overdue":  "#DC2626",
    "returned": "#059669",
    "lost":     "#9CA3AF",
}

COLS = ["Loan #", "Book", "Borrower", "Type", "Issued", "Due", "Days OD",
        "Fine (TZS)", "Status", "Actions"]


class _LoansTable(QWidget):
    """Reusable loans table filtered by status (None = all)."""

    def __init__(self, status_filter: str | None, parent=None):
        super().__init__(parent)
        self._status = status_filter
        self._loans: list[dict] = []
        self._build()

    def _build(self):
        lay = QVBoxLayout(self); lay.setContentsMargins(0, 8, 0, 0); lay.setSpacing(8)

        # Refresh + type filter
        bar = QHBoxLayout(); bar.setSpacing(8)
        self.type_cb = QComboBox()
        self.type_cb.setStyleSheet(
            "QComboBox{border:1px solid #D1D5DB;border-radius:6px;padding:6px 10px;"
            "font-size:13px;background:white;min-width:130px;}"
        )
        self.type_cb.addItem("All borrowers", "")
        self.type_cb.addItem("Students", "student")
        self.type_cb.addItem("Teachers", "teacher")
        self.type_cb.currentIndexChanged.connect(self._load)
        ref_btn = QPushButton("Refresh"); ref_btn.setStyleSheet(BTN_OUTLINE)
        ref_btn.clicked.connect(self._load)
        bar.addWidget(QLabel("Show:")); bar.addWidget(self.type_cb)
        bar.addWidget(ref_btn); bar.addStretch()
        lay.addLayout(bar)

        self.table = QTableWidget()
        self.table.setColumnCount(len(COLS))
        self.table.setHorizontalHeaderLabels(COLS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setStyleSheet("""
            QTableWidget{border:1px solid #E5E7EB;border-radius:8px;
                gridline-color:#F3F4F6;font-size:12px;}
            QHeaderView::section{background:#FEF3C7;font-weight:600;
                padding:7px;border:none;border-bottom:1px solid #FDE68A;color:#92400E;}
            QTableWidget::item{padding:5px 7px;}
        """)
        lay.addWidget(self.table)

    def _load(self):
        btype = self.type_cb.currentData() or None
        try:
            self._loans = library_service.get_loans(status=self._status, borrower_type=btype)
        except (ServiceError, PolicyViolation) as e:
            QMessageBox.warning(self, "Error", str(e)); return
        self._fill()

    def _fill(self):
        can_checkout = session.can("library.checkout")
        can_manage   = session.can("library.manage")

        self.table.setRowCount(len(self._loans))
        for r, loan in enumerate(self._loans):
            def cell(v, align=Qt.AlignmentFlag.AlignLeft, fg=None):
                it = QTableWidgetItem(str(v) if v is not None else "—")
                it.setFlags(Qt.ItemFlag.ItemIsEnabled)
                it.setTextAlignment(align | Qt.AlignmentFlag.AlignVCenter)
                if fg: it.setForeground(QColor(fg))
                return it

            ctr = Qt.AlignmentFlag.AlignCenter
            st  = loan["status"]
            od  = loan.get("overdue_days", 0)
            fine = loan.get("current_fine", 0)

            self.table.setItem(r, 0, cell(f"#{loan['id']}", ctr))
            self.table.setItem(r, 1, cell(loan["book_title"]))
            self.table.setItem(r, 2, cell(loan.get("borrower_name") or "—"))
            self.table.setItem(r, 3, cell(loan["borrower_type"].title(), ctr))
            self.table.setItem(r, 4, cell(loan["issue_date"], ctr))
            self.table.setItem(r, 5, cell(loan["due_date"], ctr))
            self.table.setItem(r, 6, cell(
                od if od > 0 else "—", ctr,
                "#DC2626" if od > 0 else None
            ))
            self.table.setItem(r, 7, cell(
                f"{fine:,.0f}" if fine > 0 else "—", ctr,
                "#DC2626" if fine > 0 else None
            ))
            self.table.setItem(r, 8, cell(st.title(), ctr, STATUS_COLORS.get(st)))

            # Action buttons
            if st in ("active", "overdue") and (can_checkout or can_manage):
                btn_w = QWidget()
                btn_lay = QHBoxLayout(btn_w); btn_lay.setContentsMargins(4, 2, 4, 2); btn_lay.setSpacing(4)
                if can_checkout:
                    ret_btn = QPushButton("Return"); ret_btn.setStyleSheet(BTN_SUCCESS)
                    ret_btn.clicked.connect(lambda _, lid=loan["id"]: self._return(lid))
                    btn_lay.addWidget(ret_btn)
                if can_manage:
                    lost_btn = QPushButton("Lost"); lost_btn.setStyleSheet(BTN_DANGER)
                    lost_btn.clicked.connect(lambda _, lid=loan["id"]: self._mark_lost(lid))
                    btn_lay.addWidget(lost_btn)
                self.table.setCellWidget(r, 9, btn_w)
            else:
                ret_lbl = loan.get("return_date") or ""
                self.table.setItem(r, 9, cell(
                    f"Returned {ret_lbl}" if ret_lbl else st.title(), ctr, "#9CA3AF"
                ))

    def _return(self, loan_id: int):
        if QMessageBox.question(
            self, "Return Book", "Confirm book return?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) != QMessageBox.StandardButton.Yes:
            return
        try:
            result = library_service.return_book(loan_id)
        except (ServiceError, PolicyViolation) as e:
            QMessageBox.warning(self, "Error", str(e)); return

        if result["fine"] > 0:
            QMessageBox.information(
                self, "Book Returned",
                f"Book returned successfully.\n\n"
                f"Overdue by {result['overdue_days']} day(s).\n"
                f"Fine: TZS {result['fine']:,.0f}"
            )
        else:
            QMessageBox.information(self, "Book Returned", "Book returned successfully. No fine.")
        self._load()

    def _mark_lost(self, loan_id: int):
        if QMessageBox.question(
            self, "Mark as Lost",
            "Mark this book as lost? The copy will not be returned to available stock.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) != QMessageBox.StandardButton.Yes:
            return
        try:
            library_service.mark_lost(loan_id)
        except (ServiceError, PolicyViolation) as e:
            QMessageBox.warning(self, "Error", str(e)); return
        self._load()

    def refresh(self):
        self._load()


class LoansTab(QWidget):
    def __init__(self):
        super().__init__()
        self._build()

    def _build(self):
        lay = QVBoxLayout(self); lay.setContentsMargins(0, 12, 0, 0); lay.setSpacing(0)

        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane{border:none;}
            QTabBar::tab{padding:8px 18px;font-size:13px;color:#6B7280;
                border:none;border-bottom:2px solid transparent;}
            QTabBar::tab:selected{color:#F59E0B;border-bottom:2px solid #F59E0B;font-weight:600;}
        """)

        self._all_tab      = _LoansTable(None)
        self._active_tab   = _LoansTable("active")
        self._overdue_tab  = _LoansTable("overdue")
        self._returned_tab = _LoansTable("returned")

        tabs.addTab(self._all_tab,      "All Loans")
        tabs.addTab(self._active_tab,   "Active")
        tabs.addTab(self._overdue_tab,  "Overdue")
        tabs.addTab(self._returned_tab, "Returned / Lost")

        tabs.currentChanged.connect(self._on_tab)
        lay.addWidget(tabs)
        self._tabs = [self._all_tab, self._active_tab, self._overdue_tab, self._returned_tab]
        self._all_tab.refresh()

    def _on_tab(self, idx: int):
        self._tabs[idx].refresh()

    def refresh(self):
        for t in self._tabs:
            t.refresh()
