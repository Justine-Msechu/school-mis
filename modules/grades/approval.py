"""Approval tab — academic officer / head teacher reviews and approves submitted grades."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QAbstractItemView
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from services.grades_service import grades_service
from services.base import ServiceError, PolicyViolation

BTN_PRIMARY = """QPushButton{background:#059669;color:white;border:none;border-radius:7px;
    padding:7px 16px;font-size:13px;font-weight:600;}QPushButton:hover{background:#047857;}"""
BTN_DANGER  = """QPushButton{background:white;color:#DC2626;border:1px solid #FECACA;
    border-radius:7px;padding:7px 16px;font-size:13px;}QPushButton:hover{background:#FEF2F2;}"""
BTN_OUTLINE = """QPushButton{background:white;color:#374151;border:1px solid #D1D5DB;
    border-radius:7px;padding:7px 16px;font-size:13px;}QPushButton:hover{background:#F9FAFB;}"""


class ApprovalTab(QWidget):
    COLS = ["Exam", "Class", "Subject", "Grades", "Action"]

    def __init__(self):
        super().__init__()
        self._pending = []
        self._build()
        self.load()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 16, 0, 0)
        lay.setSpacing(12)

        hdr = QHBoxLayout()
        t = QLabel("Pending Grade Submissions")
        t.setStyleSheet("font-size:15px;font-weight:700;color:#111827;")
        hdr.addWidget(t); hdr.addStretch()
        ref = QPushButton("Refresh"); ref.setStyleSheet(BTN_OUTLINE)
        ref.clicked.connect(self.load)
        hdr.addWidget(ref)
        lay.addLayout(hdr)

        info = QLabel(
            "Review submitted grade batches and approve or reject them. "
            "All batches must be approved before an exam can be published."
        )
        info.setWordWrap(True)
        info.setStyleSheet(
            "background:#F0FDF4;color:#166534;border-radius:6px;padding:8px 12px;font-size:12px;"
        )
        lay.addWidget(info)

        self.table = QTableWidget()
        self.table.setColumnCount(len(self.COLS))
        self.table.setHorizontalHeaderLabels(self.COLS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(4, 230)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet("""
            QTableWidget{border:1px solid #E5E7EB;border-radius:8px;
                gridline-color:#F3F4F6;font-size:13px;}
            QHeaderView::section{background:#F0FDF4;font-weight:600;
                padding:8px;border:none;border-bottom:1px solid #BBF7D0;color:#166534;}
            QTableWidget::item{padding:6px 8px;}
        """)
        lay.addWidget(self.table)

    def load(self):
        try:
            self._pending = grades_service.get_pending_submissions()
        except (ServiceError, PolicyViolation) as e:
            self._pending = []
            self.table.setRowCount(0)
            return

        self.table.setRowCount(len(self._pending))
        for r, row in enumerate(self._pending):
            for c, v in enumerate([
                row["exam_name"],
                row["class_name"],
                row["subject_name"],
                str(row["grade_count"]),
            ]):
                item = QTableWidgetItem(v)
                item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                self.table.setItem(r, c, item)

            # Action cell — Approve + Reject buttons
            cell = QWidget()
            cell_lay = QHBoxLayout(cell)
            cell_lay.setContentsMargins(4, 2, 4, 2); cell_lay.setSpacing(6)

            approve_btn = QPushButton("Approve"); approve_btn.setStyleSheet(BTN_PRIMARY)
            approve_btn.clicked.connect(
                lambda _, rr=r: self._approve(rr)
            )
            reject_btn = QPushButton("Return"); reject_btn.setStyleSheet(BTN_DANGER)
            reject_btn.clicked.connect(
                lambda _, rr=r: self._reject(rr)
            )
            cell_lay.addWidget(approve_btn); cell_lay.addWidget(reject_btn)
            cell_lay.addStretch()
            self.table.setCellWidget(r, 4, cell)

        if not self._pending:
            self.table.setRowCount(1)
            item = QTableWidgetItem("No pending submissions — all batches are up to date.")
            item.setForeground(QColor("#9CA3AF"))
            item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.table.setItem(0, 0, item)
            self.table.setSpan(0, 0, 1, len(self.COLS))

    def _approve(self, row_idx: int):
        row = self._pending[row_idx]
        try:
            n = grades_service.approve_grades(row["exam_id"], row["class_id"], row["subject_id"])
        except (ServiceError, PolicyViolation) as e:
            QMessageBox.warning(self, "Cannot Approve", str(e)); return
        QMessageBox.information(self, "Approved", f"{n} grade(s) approved.")
        self.load()

    def _reject(self, row_idx: int):
        row = self._pending[row_idx]
        if QMessageBox.question(
            self, "Return Grades",
            f"Return {row['subject_name']} grades for {row['class_name']} to draft?\n"
            "The teacher will need to re-submit them.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) != QMessageBox.StandardButton.Yes:
            return
        try:
            grades_service.reject_grades(row["exam_id"], row["class_id"], row["subject_id"])
        except (ServiceError, PolicyViolation) as e:
            QMessageBox.warning(self, "Error", str(e)); return
        QMessageBox.information(self, "Returned", "Grades returned to draft.")
        self.load()

    def refresh(self):
        self.load()
