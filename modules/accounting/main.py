"""Accounting module — expenses and ledger."""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTabWidget


class AccountingWidget(QWidget):
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
            QTabBar::tab:selected { background: #059669; color: white; font-weight: 600; }
            QTabBar::tab:hover:!selected { background: #D1D5DB; }
        """)

        from modules.accounting.expenses import ExpensesWidget
        from modules.accounting.ledger   import LedgerWidget

        self.tabs.addTab(ExpensesWidget(), "Expenses")
        self.tabs.addTab(LedgerWidget(),   "Ledger")

        layout.addWidget(self.tabs)

    def refresh(self):
        for i in range(self.tabs.count()):
            w = self.tabs.widget(i)
            if hasattr(w, "load_table"):
                w.load_table()
