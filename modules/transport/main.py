"""Transport module — routes, student assignments and subscription overview."""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTabWidget
from auth.session import session
from modules.transport.routes import RoutesTab
from modules.transport.assignments import AssignmentsTab


class TransportWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 16, 24, 16)
        lay.setSpacing(0)

        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane{border:none;background:transparent;}
            QTabBar::tab{padding:10px 22px;font-size:13px;color:#6B7280;
                border:none;border-bottom:2px solid transparent;background:transparent;}
            QTabBar::tab:selected{color:#0891B2;border-bottom:2px solid #0891B2;font-weight:600;}
            QTabBar::tab:hover{color:#0E7490;}
        """)

        self._routes_tab = RoutesTab()
        tabs.addTab(self._routes_tab, "Routes")

        self._assign_tab = AssignmentsTab()
        tabs.addTab(self._assign_tab, "Student Assignments")

        tabs.currentChanged.connect(self._on_tab)
        lay.addWidget(tabs)
        self._tabs = [self._routes_tab, self._assign_tab]

    def _on_tab(self, idx: int):
        self._tabs[idx].refresh()

    def refresh(self):
        self._routes_tab.refresh()
