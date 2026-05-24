"""Library module — tabbed container."""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTabWidget
from PyQt6.QtCore import Qt
from auth.session import session
from modules.library.catalogue import CatalogueTab
from modules.library.checkout import CheckoutTab
from modules.library.loans import LoansTab


class LibraryWidget(QWidget):
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
            QTabBar::tab:selected{color:#F59E0B;border-bottom:2px solid #F59E0B;font-weight:600;}
            QTabBar::tab:hover{color:#D97706;}
        """)

        self._cat_tab  = CatalogueTab()
        tabs.addTab(self._cat_tab, "Catalogue")

        if session.can("library.checkout"):
            self._chk_tab = CheckoutTab()
            tabs.addTab(self._chk_tab, "Issue / Return")
        else:
            self._chk_tab = None

        if session.can("library.view"):
            self._loans_tab = LoansTab()
            tabs.addTab(self._loans_tab, "Loan Records")
        else:
            self._loans_tab = None

        lay.addWidget(tabs)

    def refresh(self):
        self._cat_tab.refresh()
        if self._chk_tab:
            self._chk_tab.refresh()
        if self._loans_tab:
            self._loans_tab.refresh()
