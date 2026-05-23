"""Welfare module — student welfare classification and exemption overview."""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTabWidget


class WelfareWidget(QWidget):
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
            QTabBar::tab:selected { background: #7C3AED; color: white; font-weight: 600; }
            QTabBar::tab:hover:!selected { background: #D1D5DB; }
        """)

        from modules.welfare.classification import ClassificationWidget
        from modules.welfare.exemptions     import ExemptionsWidget

        self.tabs.addTab(ClassificationWidget(), "Student Classification")
        self.tabs.addTab(ExemptionsWidget(),     "Exemptions Overview")

        layout.addWidget(self.tabs)

    def refresh(self):
        for i in range(self.tabs.count()):
            w = self.tabs.widget(i)
            if hasattr(w, "load_table"):
                w.load_table()
