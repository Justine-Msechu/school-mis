"""Finance module — tabbed container for all finance sub-pages."""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTabWidget
from auth.session import session


class FinanceWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: none; background: #F3F4F6; }
            QTabBar::tab {
                background: #E5E7EB; color: #374151;
                padding: 8px 20px; font-size: 13px;
                border-top-left-radius: 6px; border-top-right-radius: 6px;
                margin-right: 2px;
            }
            QTabBar::tab:selected { background: #DC2626; color: white; font-weight: 600; }
            QTabBar::tab:hover:!selected { background: #D1D5DB; }
        """)

        from modules.finance.fee_structures import FeeStructuresWidget
        from modules.finance.billing        import BillingWidget
        from modules.finance.payments       import PaymentsWidget
        from modules.finance.waivers        import WaiversWidget

        self.tabs.addTab(FeeStructuresWidget(), "Fee Structures")
        self.tabs.addTab(BillingWidget(),       "Billing")
        self.tabs.addTab(PaymentsWidget(),      "Record Payment")
        self.tabs.addTab(WaiversWidget(),       "Waivers")

        layout.addWidget(self.tabs)

    def refresh(self):
        for i in range(self.tabs.count()):
            w = self.tabs.widget(i)
            if hasattr(w, "load_table"):
                w.load_table()
