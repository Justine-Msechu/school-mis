"""modules/login.py — Login dialog shown on every app start."""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QMessageBox, QFrame, QWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from database.db import authenticate, get_config, hash_password, execute, ROLES
from auth.session import session


BTN_LOGIN = """QPushButton{background:#2563EB;color:#fff;border:none;border-radius:8px;
    padding:11px;font-size:14px;font-weight:700;}
    QPushButton:hover{background:#1D4ED8;}"""


class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("School MIS — Login")
        self.setFixedSize(420, 520)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header banner ─────────────────────────────────────────
        header = QFrame()
        header.setStyleSheet("background:#1E293B;")
        header.setFixedHeight(140)
        hl = QVBoxLayout(header); hl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # School name from config
        sn = get_config("school_name", "School MIS")
        school_lbl = QLabel(sn)
        school_lbl.setStyleSheet("color:#FFFFFF;font-size:18px;font-weight:700;background:transparent;")
        school_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        sub = QLabel("Management Information System")
        sub.setStyleSheet("color:#94A3B8;font-size:12px;background:transparent;")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)

        hl.addWidget(school_lbl)
        hl.addWidget(sub)

        # ── Login form ────────────────────────────────────────────
        body = QWidget(); body.setStyleSheet("background:#FFFFFF;")
        bl = QVBoxLayout(body); bl.setContentsMargins(40, 32, 40, 32); bl.setSpacing(14)

        title = QLabel("Sign in to your account")
        title.setStyleSheet("font-size:16px;font-weight:700;color:#111827;")
        bl.addWidget(title)

        bl.addWidget(self._field_label("Username"))
        self.f_user = QLineEdit()
        self.f_user.setPlaceholderText("Enter your username")
        self.f_user.setFixedHeight(42)
        bl.addWidget(self.f_user)

        bl.addWidget(self._field_label("Password"))
        self.f_pw = QLineEdit()
        self.f_pw.setEchoMode(QLineEdit.EchoMode.Password)
        self.f_pw.setPlaceholderText("Enter your password")
        self.f_pw.setFixedHeight(42)
        self.f_pw.returnPressed.connect(self._attempt_login)
        bl.addWidget(self.f_pw)

        bl.addSpacing(4)
        self._err_lbl = QLabel("")
        self._err_lbl.setStyleSheet("color:#DC2626;font-size:12px;background:transparent;")
        self._err_lbl.setWordWrap(True)
        bl.addWidget(self._err_lbl)

        btn = QPushButton("Sign In"); btn.setStyleSheet(BTN_LOGIN)
        btn.clicked.connect(self._attempt_login)
        btn.setFixedHeight(44)
        bl.addWidget(btn)

        bl.addStretch()

        # ── Footer ────────────────────────────────────────────────
        footer = QLabel("Contact your system administrator if you cannot log in.")
        footer.setStyleSheet("color:#9CA3AF;font-size:11px;background:#F9FAFB;"
                             "padding:10px;border-top:1px solid #F3F4F6;")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setWordWrap(True)

        root.addWidget(header)
        root.addWidget(body, 1)
        root.addWidget(footer)

    def _field_label(self, text):
        l = QLabel(text)
        l.setStyleSheet("font-size:13px;font-weight:600;color:#374151;background:transparent;")
        return l

    def _attempt_login(self):
        username = self.f_user.text().strip()
        password = self.f_pw.text()

        if not username or not password:
            self._err_lbl.setText("Please enter your username and password.")
            return

        user = authenticate(username, password)
        if not user:
            self._err_lbl.setText("Incorrect username or password. Please try again.")
            self.f_pw.clear()
            self.f_pw.setFocus()
            return

        session.login(user)

        # Must change password?
        if user.get("must_change_pw"):
            dlg = ChangePasswordDialog(self)
            if dlg.exec() != QDialog.DialogCode.Accepted:
                session.logout()
                return

        self.accept()


# ── Change password dialog ────────────────────────────────────────────────────
class ChangePasswordDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Change Password")
        self.setFixedSize(380, 320)
        self._build()

    def _build(self):
        lay = QVBoxLayout(self); lay.setContentsMargins(32, 28, 32, 28); lay.setSpacing(12)

        title = QLabel("Set a new password")
        title.setStyleSheet("font-size:16px;font-weight:700;color:#111827;")
        lay.addWidget(title)

        info = QLabel("Your account requires a password change before continuing.")
        info.setStyleSheet("font-size:12px;color:#6B7280;background:#FEF3C7;"
                           "border-radius:6px;padding:8px 10px;")
        info.setWordWrap(True)
        lay.addWidget(info)

        self.f_new  = QLineEdit(); self.f_new.setEchoMode(QLineEdit.EchoMode.Password)
        self.f_new.setPlaceholderText("New password (min 6 chars)")
        self.f_new.setFixedHeight(40)

        self.f_conf = QLineEdit(); self.f_conf.setEchoMode(QLineEdit.EchoMode.Password)
        self.f_conf.setPlaceholderText("Confirm new password")
        self.f_conf.setFixedHeight(40)

        lay.addWidget(QLabel("New password"))
        lay.addWidget(self.f_new)
        lay.addWidget(QLabel("Confirm"))
        lay.addWidget(self.f_conf)

        self._err = QLabel(""); self._err.setStyleSheet("color:#DC2626;font-size:12px;")
        lay.addWidget(self._err)

        btn = QPushButton("Update password")
        btn.setStyleSheet("QPushButton{background:#2563EB;color:#fff;border:none;border-radius:7px;"
                          "padding:10px;font-size:14px;font-weight:600;}QPushButton:hover{background:#1D4ED8;}")
        btn.clicked.connect(self._save)
        lay.addWidget(btn)

    def _save(self):
        pw = self.f_new.text()
        if len(pw) < 6:
            self._err.setText("Password must be at least 6 characters."); return
        if pw != self.f_conf.text():
            self._err.setText("Passwords do not match."); return
        h, salt = hash_password(pw)
        execute("UPDATE users SET password_hash=?,salt=?,must_change_pw=0 WHERE id=?",
                (h, salt, session.user_id))
        self.accept()
