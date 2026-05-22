"""
School MIS — Entry point (v2)
Flow: DB init → setup wizard (first run) → login → main window
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from PyQt6.QtWidgets import QApplication, QDialog
from PyQt6.QtGui import QFont
from database.db import initialize_database, is_setup_complete
from ui.theme import GLOBAL_STYLE


def run_app():
    """Full app flow — can be called again after logout."""
    # 1. Setup wizard on first run
    if not is_setup_complete():
        from modules.setup_wizard import SetupWizard
        wiz = SetupWizard()
        if wiz.exec() != QDialog.DialogCode.Accepted:
            sys.exit(0)

    # 2. Login
    from modules.login import LoginDialog
    login = LoginDialog()
    if login.exec() != QDialog.DialogCode.Accepted:
        sys.exit(0)

    # 3. Main window
    from ui.main_window import MainWindow
    win = MainWindow()
    win.show()


def main():
    initialize_database()

    app = QApplication(sys.argv)
    app.setApplicationName("School MIS")

    font = QFont("Segoe UI", 10) if sys.platform == "win32" else QFont("Ubuntu", 10)
    app.setFont(font)
    app.setStyleSheet(GLOBAL_STYLE)

    run_app()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
