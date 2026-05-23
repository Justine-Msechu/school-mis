"""Grades module — tabbed container for entry, approval, results, and exam management."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTabWidget, QFrame
)
from PyQt6.QtCore import Qt
from auth.session import session
from modules.grades.entry    import GradeEntryTab
from modules.grades.approval import ApprovalTab
from modules.grades.results  import ResultsTab
from modules.grades.exams    import ExamManagementTab


class GradesWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 20, 28, 20)
        lay.setSpacing(0)

        # ── Header ────────────────────────────────────────────────────────────
        hdr = QHBoxLayout()
        title = QLabel("Grades & Examinations")
        title.setStyleSheet("font-size:22px;font-weight:700;color:#111827;")
        hdr.addWidget(title); hdr.addStretch()
        lay.addLayout(hdr)
        lay.addSpacing(14)

        # ── Tabs ──────────────────────────────────────────────────────────────
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane{
                border:1px solid #E5E7EB;border-radius:8px;
                background:white;padding:16px;
            }
            QTabBar::tab{
                background:#F3F4F6;color:#374151;
                padding:9px 20px;margin-right:3px;border-radius:6px 6px 0 0;
                font-size:13px;
            }
            QTabBar::tab:selected{background:white;color:#111827;font-weight:600;
                border:1px solid #E5E7EB;border-bottom:none;}
            QTabBar::tab:hover{background:#E5E7EB;}
        """)

        role = session.role

        # Grade Entry — teachers and above (anyone with grades.enter or grades.view)
        if session.can("grades.enter") or session.can("grades.view"):
            self._entry_tab = GradeEntryTab()
            self.tabs.addTab(self._entry_tab, "Grade Entry")
        else:
            self._entry_tab = None

        # Approval — academic, head_teacher, admin
        if session.can("grades.approve"):
            self._approval_tab = ApprovalTab()
            self.tabs.addTab(self._approval_tab, "Approvals")
        else:
            self._approval_tab = None

        # Results & Reports — anyone with grades.view
        if session.can("grades.view"):
            self._results_tab = ResultsTab()
            self.tabs.addTab(self._results_tab, "Results & Reports")
        else:
            self._results_tab = None

        # Exam Management — approvers and above
        if session.can("grades.approve"):
            self._exams_tab = ExamManagementTab()
            self.tabs.addTab(self._exams_tab, "Exam Management")
        else:
            self._exams_tab = None

        lay.addWidget(self.tabs)

    def refresh(self):
        for tab in [self._entry_tab, self._approval_tab,
                    self._results_tab, self._exams_tab]:
            if tab is not None and hasattr(tab, "refresh"):
                tab.refresh()
