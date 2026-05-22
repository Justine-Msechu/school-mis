"""Main window — role-aware sidebar navigation."""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QStackedWidget, QFrame, QMessageBox
)
from PyQt6.QtCore import Qt, QMetaObject, Q_ARG
from auth.session import session
from database.db import get_config

# All module imports
from modules.dashboard  import DashboardWidget
from modules.students   import StudentsWidget
from modules.teachers   import TeachersWidget
from modules.classes    import ClassesWidget
from modules.attendance import AttendanceWidget
from modules.fees       import FeesWidget
from modules.settings   import SettingsWidget

SIDEBAR_W = 216

# (icon, label, key, required_permission)
ALL_NAV = [
    ("🏠", "Dashboard",   "home",       None),
    ("🎓", "Students",    "students",   "students.view"),
    ("👩‍🏫","Teachers",   "teachers",   "teachers.view"),
    ("🏫", "Classes",     "classes",    "classes.view"),
    ("✅", "Attendance",  "attendance", "attendance.view"),
    ("💰", "Fees",        "fees",       "fees.view"),
    ("⚙",  "Settings",   "settings",   "settings.view"),
]


class NavButton(QPushButton):
    def __init__(self, icon, label, key):
        super().__init__(f"  {icon}  {label}")
        self.key = key
        self.setCheckable(True)
        self.setFixedHeight(44)
        self.setStyleSheet("""
            QPushButton {
                text-align: left; padding-left: 18px;
                font-size: 13px; border: none; border-radius: 8px;
                color: #94A3B8; background: transparent; font-weight: 400;
            }
            QPushButton:hover  { background: rgba(255,255,255,0.08); color: #F1F5F9; }
            QPushButton:checked { background: rgba(255,255,255,0.14); color: #FFFFFF; font-weight: 600; }
        """)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        school = get_config("school_name", "School MIS")
        self.setWindowTitle(f"{school} — Management System")
        self.setMinimumSize(1050, 680)
        self.resize(1240, 760)
        self._build()
        self._load_saved_theme()
        self._start_update_check()

    def _build(self):
        root = QWidget()
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Sidebar ──────────────────────────────────────────────
        sidebar = QFrame()
        sidebar.setFixedWidth(SIDEBAR_W)
        sidebar.setStyleSheet("QFrame { background: #0F172A; }")
        sb = QVBoxLayout(sidebar)
        sb.setContentsMargins(10, 0, 10, 16)
        sb.setSpacing(2)

        # School name header
        header = QFrame()
        header.setStyleSheet("background: #1E293B; border-bottom: 1px solid #334155;")
        header.setFixedHeight(64)
        hl = QVBoxLayout(header); hl.setContentsMargins(16, 0, 16, 0)
        school = get_config("school_name", "School MIS")
        sn = QLabel(school[:22] + "…" if len(school) > 22 else school)
        sn.setStyleSheet("color:#F8FAFC;font-size:13px;font-weight:700;background:transparent;")
        hl.addWidget(sn)
        sub = QLabel("Management System")
        sub.setStyleSheet("color:#64748B;font-size:11px;background:transparent;")
        hl.addWidget(sub)
        sb.addWidget(header)
        sb.addSpacing(10)

        # Nav items (filtered by permission)
        self._stack  = QStackedWidget()
        self._pages  = {}
        self.nav_btns = {}

        module_map = {
            "home":       DashboardWidget,
            "students":   StudentsWidget,
            "teachers":   TeachersWidget,
            "classes":    ClassesWidget,
            "attendance": AttendanceWidget,
            "fees":       FeesWidget,
            "settings":   SettingsWidget,
        }

        for icon, label, key, perm in ALL_NAV:
            if perm and not session.can(perm):
                continue
            btn = NavButton(icon, label, key)
            btn.clicked.connect(lambda _, k=key: self._nav(k))
            sb.addWidget(btn)
            self.nav_btns[key] = btn
            page = module_map[key]()
            self._stack.addWidget(page)
            self._pages[key] = page

        sb.addStretch()

        # ── User info strip at bottom of sidebar ─────────────────
        user_strip = QFrame()
        user_strip.setStyleSheet(
            "QFrame{background:#1E293B;border-radius:8px;border:1px solid #334155;}"
        )
        ul = QVBoxLayout(user_strip); ul.setContentsMargins(12, 8, 12, 8); ul.setSpacing(2)

        uname = QLabel(session.full_name)
        uname.setStyleSheet("color:#F1F5F9;font-size:12px;font-weight:600;background:transparent;")
        role_color = session.role_color
        role_lbl = QLabel(session.role_label)
        role_lbl.setStyleSheet(f"color:{role_color};font-size:11px;background:transparent;")

        logout_btn = QPushButton("Sign out")
        logout_btn.setStyleSheet(
            "QPushButton{color:#94A3B8;background:transparent;border:none;"
            "font-size:11px;text-align:left;padding:0;}QPushButton:hover{color:#F87171;}"
        )
        logout_btn.clicked.connect(self._logout)

        ul.addWidget(uname); ul.addWidget(role_lbl); ul.addWidget(logout_btn)
        sb.addWidget(user_strip)

        # ── Content area ─────────────────────────────────────────
        content = QFrame()
        self._content_frame = content          # saved so apply_theme can update it
        content.setStyleSheet("QFrame { background: #F3F4F6; }")
        cl = QVBoxLayout(content)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)

        # Update banner (hidden until an update is found)
        self._banner = self._build_banner()
        self._banner.setVisible(False)
        cl.addWidget(self._banner)
        cl.addWidget(self._stack)

        layout.addWidget(sidebar)
        layout.addWidget(content)

        self._nav("home")

    def _nav(self, key):
        if key not in self._pages:
            return
        for k, btn in self.nav_btns.items():
            btn.setChecked(k == key)
        self._stack.setCurrentWidget(self._pages[key])
        if key == "home":
            self._pages["home"].refresh()

    def _logout(self):
        session.logout()
        self.close()
        # Restart login flow
        from main import run_app
        run_app()

    def _load_saved_theme(self):
        from database.db import get_config as gc
        key = gc(f"theme_user_{session.user_id}", "light")
        self.apply_theme(key, save=False)

    def apply_theme(self, key: str, save: bool = True):
        from ui.theme import THEMES
        from PyQt6.QtWidgets import QApplication
        theme = THEMES.get(key, THEMES["light"])
        QApplication.instance().setStyleSheet(theme["style"])
        self._content_frame.setStyleSheet(
            f"QFrame {{ background: {theme['content_bg']}; }}"
        )
        if save:
            from database.db import set_config
            set_config(f"theme_user_{session.user_id}", key)

    def _build_banner(self):
        banner = QFrame()
        banner.setStyleSheet(
            "QFrame { background: #DBEAFE; border-bottom: 1px solid #93C5FD; }"
        )
        banner.setFixedHeight(46)
        row = QHBoxLayout(banner)
        row.setContentsMargins(20, 0, 12, 0)

        self._banner_label = QLabel()
        self._banner_label.setStyleSheet(
            "color: #1E40AF; font-size: 13px; font-weight: 600; background: transparent;"
        )

        install_btn = QPushButton("Install now")
        install_btn.setFixedHeight(28)
        install_btn.setStyleSheet(
            "QPushButton { background: #2563EB; color: #fff; border: none; border-radius: 5px;"
            " padding: 0 14px; font-size: 12px; font-weight: 600; }"
            "QPushButton:hover { background: #1D4ED8; }"
        )
        install_btn.clicked.connect(self._open_update_dialog)

        dismiss_btn = QPushButton("✕")
        dismiss_btn.setFixedSize(26, 26)
        dismiss_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #60A5FA; border: none; font-size: 14px; }"
            "QPushButton:hover { color: #1E40AF; }"
        )
        dismiss_btn.clicked.connect(lambda: self._banner.setVisible(False))

        icon = QLabel("🔄")
        icon.setStyleSheet("background: transparent;")
        row.addWidget(icon)
        row.addSpacing(6)
        row.addWidget(self._banner_label)
        row.addStretch()
        row.addWidget(install_btn)
        row.addSpacing(6)
        row.addWidget(dismiss_btn)
        return banner

    def _start_update_check(self):
        from modules.updater import StartupUpdateChecker, ConnectivityWatcher

        self._update_info   = None
        self._check_running = False

        # Immediate check on startup
        self._checker = StartupUpdateChecker()
        self._checker.update_available.connect(self._show_update_banner)
        self._checker.start()

        # Connectivity watcher — re-checks whenever internet comes back
        self._conn_watcher = ConnectivityWatcher()
        self._conn_watcher.came_online.connect(self._on_came_online)
        self._conn_watcher.start()

    def _on_came_online(self):
        """Triggered when internet becomes available. Run a fresh update check."""
        if self._check_running or (self._update_info and self._banner.isVisible()):
            return  # already checking or banner already showing
        from modules.updater import StartupUpdateChecker
        self._check_running = True
        checker = StartupUpdateChecker()
        checker.update_available.connect(self._show_update_banner)
        checker.finished.connect(lambda: setattr(self, "_check_running", False))
        checker.start()
        self._checker = checker  # keep reference

    def _show_update_banner(self, info: dict):
        self._update_info = info
        self._banner_label.setText(
            f"Update available — v{info['local']}  →  v{info['remote']}"
        )
        self._banner.setVisible(True)

    def _open_update_dialog(self):
        if not self._update_info:
            return
        from modules.updater import UpdateDialog
        dlg = UpdateDialog(self._update_info, self)
        dlg.exec()
        self._banner.setVisible(False)

    def closeEvent(self, event):
        if hasattr(self, "_conn_watcher"):
            self._conn_watcher.requestInterruption()
            self._conn_watcher.wait(2000)
        super().closeEvent(event)
