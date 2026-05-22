"""
modules/setup_wizard.py
First-run wizard: school info → admin account → head teacher → done.
Only shows once. After completion, sets school_config.setup_complete = 1.
"""

import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QStackedWidget, QWidget, QFormLayout,
    QFileDialog, QMessageBox, QFrame, QComboBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QFont
from database.db import set_config, get_config, create_user, execute, fetch_one


# ── Shared button styles ──────────────────────────────────────────────────────
BTN_NEXT = """QPushButton{background:#2563EB;color:#fff;border:none;border-radius:8px;
    padding:10px 28px;font-size:14px;font-weight:600;}
    QPushButton:hover{background:#1D4ED8;}QPushButton:disabled{background:#93C5FD;}"""
BTN_BACK = """QPushButton{background:#F3F4F6;color:#374151;border:1px solid #D1D5DB;
    border-radius:8px;padding:10px 24px;font-size:14px;}
    QPushButton:hover{background:#E5E7EB;}"""
CARD = """QFrame{background:#fff;border-radius:12px;border:1px solid #E5E7EB;}"""


def _label(text, size=13, bold=False, color="#374151"):
    l = QLabel(text)
    l.setStyleSheet(f"font-size:{size}px;{'font-weight:600;' if bold else ''}color:{color};background:transparent;")
    l.setWordWrap(True)
    return l

def _input(placeholder="", password=False):
    e = QLineEdit()
    e.setPlaceholderText(placeholder)
    if password:
        e.setEchoMode(QLineEdit.EchoMode.Password)
    return e

def _card_frame():
    f = QFrame()
    f.setStyleSheet(CARD)
    return f


# ══════════════════════════════════════════════════════════════════════════════
class SetupWizard(QDialog):
    """
    4-step first-run wizard.
    On accept() the caller should create a session and proceed to main window.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("School MIS — First-time Setup")
        self.setFixedSize(600, 560)
        self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)
        self._logo_path = ""
        self._admin_id  = None
        self._build()

    # ── UI ────────────────────────────────────────────────────────
    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Progress bar (step indicator)
        self._step_bar = _StepBar(["School info", "Admin account", "Head teacher", "Done"])
        root.addWidget(self._step_bar)

        # Stacked pages
        self._stack = QStackedWidget()
        self._stack.addWidget(self._page_school())
        self._stack.addWidget(self._page_admin())
        self._stack.addWidget(self._page_headteacher())
        self._stack.addWidget(self._page_done())
        root.addWidget(self._stack, 1)

        # Navigation buttons
        nav = QHBoxLayout()
        nav.setContentsMargins(32, 16, 32, 24)
        self._btn_back = QPushButton("← Back"); self._btn_back.setStyleSheet(BTN_BACK)
        self._btn_next = QPushButton("Next →");  self._btn_next.setStyleSheet(BTN_NEXT)
        self._btn_back.clicked.connect(self._go_back)
        self._btn_next.clicked.connect(self._go_next)
        nav.addWidget(self._btn_back)
        nav.addStretch()
        nav.addWidget(self._btn_next)
        root.addLayout(nav)

        self._update_nav(0)

    # ── Page 1: School information ────────────────────────────────
    def _page_school(self):
        w = QWidget(); lay = QVBoxLayout(w); lay.setContentsMargins(32,24,32,8)
        lay.addWidget(_label("School Information", 18, True, "#111827"))
        lay.addWidget(_label("Enter the details of your school. These will appear on reports and print-outs.", 13, color="#6B7280"))
        lay.addSpacing(16)

        card = _card_frame()
        form = QFormLayout(card); form.setContentsMargins(20,16,20,16); form.setSpacing(12)

        self.f_school_name    = _input("e.g. Arusha Primary School")
        self.f_school_address = _input("Physical address")
        self.f_school_phone   = _input("+255 …")
        self.f_school_email   = _input("school@example.tz")
        self.f_school_motto   = _input("Optional school motto")

        # Logo picker
        logo_row = QHBoxLayout()
        self._logo_preview = QLabel("No logo selected")
        self._logo_preview.setStyleSheet("color:#9CA3AF;font-size:12px;")
        logo_btn = QPushButton("Choose logo…")
        logo_btn.setStyleSheet("QPushButton{background:#F9FAFB;border:1px solid #D1D5DB;border-radius:6px;padding:6px 14px;font-size:12px;}")
        logo_btn.clicked.connect(self._pick_logo)
        logo_row.addWidget(self._logo_preview, 1)
        logo_row.addWidget(logo_btn)
        logo_w = QWidget(); logo_w.setLayout(logo_row)

        for lbl, wgt in [
            ("School name *", self.f_school_name),
            ("Address", self.f_school_address),
            ("Phone", self.f_school_phone),
            ("Email", self.f_school_email),
            ("Motto", self.f_school_motto),
            ("Logo", logo_w),
        ]:
            form.addRow(_label(lbl), wgt)

        lay.addWidget(card); lay.addStretch()
        return w

    # ── Page 2: Admin account ─────────────────────────────────────
    def _page_admin(self):
        w = QWidget(); lay = QVBoxLayout(w); lay.setContentsMargins(32,24,32,8)
        lay.addWidget(_label("Create Administrator Account", 18, True, "#111827"))
        lay.addWidget(_label("This account has full access to all settings. Keep the password safe.", 13, color="#6B7280"))
        lay.addSpacing(16)

        card = _card_frame()
        form = QFormLayout(card); form.setContentsMargins(20,16,20,16); form.setSpacing(12)

        self.f_admin_name     = _input("Full name")
        self.f_admin_username = _input("Username (no spaces)")
        self.f_admin_pw       = _input("Password (min 6 characters)", password=True)
        self.f_admin_pw2      = _input("Repeat password", password=True)

        for lbl, wgt in [
            ("Full name *", self.f_admin_name),
            ("Username *",  self.f_admin_username),
            ("Password *",  self.f_admin_pw),
            ("Confirm *",   self.f_admin_pw2),
        ]:
            form.addRow(_label(lbl), wgt)

        info = QLabel("ℹ  You can create more user accounts from Settings → Users after setup.")
        info.setStyleSheet("color:#2563EB;font-size:12px;background:#EFF6FF;border-radius:6px;padding:8px 12px;")
        info.setWordWrap(True)

        lay.addWidget(card); lay.addSpacing(12); lay.addWidget(info); lay.addStretch()
        return w

    # ── Page 3: Head teacher ──────────────────────────────────────
    def _page_headteacher(self):
        w = QWidget(); lay = QVBoxLayout(w); lay.setContentsMargins(32,24,32,8)
        lay.addWidget(_label("Assign Head Teacher", 18, True, "#111827"))
        lay.addWidget(_label("The head teacher can approve grades and manage staff. You can skip this and assign later.", 13, color="#6B7280"))
        lay.addSpacing(16)

        card = _card_frame()
        form = QFormLayout(card); form.setContentsMargins(20,16,20,16); form.setSpacing(12)

        self.f_ht_first = _input("First name")
        self.f_ht_last  = _input("Last name")
        self.f_ht_phone = _input("+255 …")
        self.f_ht_user  = _input("Login username")
        self.f_ht_pw    = _input("Temporary password", password=True)

        for lbl, wgt in [
            ("First name", self.f_ht_first),
            ("Last name",  self.f_ht_last),
            ("Phone",      self.f_ht_phone),
            ("Username",   self.f_ht_user),
            ("Temp. password", self.f_ht_pw),
        ]:
            form.addRow(_label(lbl), wgt)

        skip = QLabel("Leave fields blank to skip this step.")
        skip.setStyleSheet("color:#6B7280;font-size:12px;background:transparent;")
        lay.addWidget(card); lay.addSpacing(8); lay.addWidget(skip); lay.addStretch()
        return w

    # ── Page 4: Done ──────────────────────────────────────────────
    def _page_done(self):
        w = QWidget(); lay = QVBoxLayout(w); lay.setContentsMargins(32,24,32,8)
        lay.addStretch()
        icon = QLabel("🎉"); icon.setStyleSheet("font-size:52px;background:transparent;")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(icon)
        lay.addWidget(_label("Setup Complete!", 22, True, "#111827"))
        self._done_lbl = _label("", 13, color="#6B7280")
        self._done_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._done_lbl)
        lay.addSpacing(24)

        summary = _card_frame()
        sl = QVBoxLayout(summary); sl.setContentsMargins(20,16,20,16); sl.setSpacing(6)
        self._summary_labels = []
        for _ in range(5):
            lbl = QLabel(""); lbl.setStyleSheet("font-size:13px;color:#374151;")
            sl.addWidget(lbl); self._summary_labels.append(lbl)
        lay.addWidget(summary)
        lay.addStretch()
        return w

    # ── Navigation logic ──────────────────────────────────────────
    def _update_nav(self, step):
        self._step_bar.set_step(step)
        self._stack.setCurrentIndex(step)
        self._btn_back.setVisible(step > 0)
        if step == 3:
            self._btn_next.setText("Open School MIS →")
        elif step == 2:
            self._btn_next.setText("Finish setup →")
        else:
            self._btn_next.setText("Next →")
        self._current_step = step

    def _go_back(self):
        if self._current_step > 0:
            self._update_nav(self._current_step - 1)

    def _go_next(self):
        step = self._current_step
        if   step == 0 and not self._validate_school(): return
        elif step == 1 and not self._validate_admin():  return
        elif step == 2: self._save_headteacher()
        elif step == 3: self.accept(); return
        if step == 2:
            self._fill_done_page()
        self._update_nav(step + 1)

    # ── Validators & savers ───────────────────────────────────────
    def _validate_school(self):
        if not self.f_school_name.text().strip():
            QMessageBox.warning(self, "Required", "School name is required."); return False
        return True

    def _save_school(self):
        set_config("school_name",    self.f_school_name.text().strip())
        set_config("school_address", self.f_school_address.text().strip())
        set_config("school_phone",   self.f_school_phone.text().strip())
        set_config("school_email",   self.f_school_email.text().strip())
        set_config("school_motto",   self.f_school_motto.text().strip())
        set_config("school_logo",    self._logo_path)

    def _validate_admin(self):
        self._save_school()
        if not self.f_admin_name.text().strip():
            QMessageBox.warning(self, "Required", "Admin full name is required."); return False
        if not self.f_admin_username.text().strip():
            QMessageBox.warning(self, "Required", "Admin username is required."); return False
        if len(self.f_admin_pw.text()) < 6:
            QMessageBox.warning(self, "Password", "Password must be at least 6 characters."); return False
        if self.f_admin_pw.text() != self.f_admin_pw2.text():
            QMessageBox.warning(self, "Password", "Passwords do not match."); return False
        self._admin_id = create_user(
            self.f_admin_username.text().strip(),
            self.f_admin_pw.text(),
            "admin",
            self.f_admin_name.text().strip(),
        )
        return True

    def _save_headteacher(self):
        fn = self.f_ht_first.text().strip()
        ln = self.f_ht_last.text().strip()
        if not fn or not ln:
            return   # skip
        from database.db import execute
        tid = execute(
            "INSERT INTO teachers(first_name,last_name,role) VALUES(?,?,'Head Teacher')",
            (fn, ln)
        )
        set_config("head_teacher_id", str(tid))
        if self.f_ht_user.text().strip() and self.f_ht_pw.text():
            create_user(
                self.f_ht_user.text().strip(),
                self.f_ht_pw.text(),
                "head_teacher",
                f"{fn} {ln}",
                teacher_id=tid,
                must_change=True,
            )
        if self.f_ht_phone.text().strip():
            execute("UPDATE teachers SET phone=? WHERE id=?",
                    (self.f_ht_phone.text().strip(), tid))

    def _fill_done_page(self):
        sn = get_config("school_name", "—")
        self._done_lbl.setText(f"Your school '{sn}' is ready.")
        infos = [
            f"🏫  School: {sn}",
            f"👤  Admin: {self.f_admin_name.text().strip()} ({self.f_admin_username.text().strip()})",
            f"👩‍🏫  Head teacher: {self.f_ht_first.text().strip() or '(not set)'}",
            "📋  You can add more teachers and classes from the main app.",
            "⚙   Settings are under the Settings menu.",
        ]
        for i, lbl in enumerate(self._summary_labels):
            lbl.setText(infos[i] if i < len(infos) else "")
        set_config("setup_complete", "1")

    def _pick_logo(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select logo", "", "Images (*.png *.jpg *.jpeg *.svg)"
        )
        if path:
            self._logo_path = path
            self._logo_preview.setText(os.path.basename(path))
            self._logo_preview.setStyleSheet("color:#2563EB;font-size:12px;")


# ── Step progress bar ─────────────────────────────────────────────────────────
class _StepBar(QWidget):
    def __init__(self, steps):
        super().__init__()
        self._steps = steps
        self._current = 0
        self.setFixedHeight(72)
        self.setStyleSheet("background:#F9FAFB;border-bottom:1px solid #E5E7EB;")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(32, 0, 32, 0)
        self._labels = []
        for i, s in enumerate(steps):
            lbl = QLabel(f"{'✓' if i==0 else str(i+1)}  {s}")
            lbl.setStyleSheet("font-size:13px;color:#9CA3AF;background:transparent;")
            lay.addWidget(lbl)
            self._labels.append(lbl)
            if i < len(steps) - 1:
                sep = QLabel("──")
                sep.setStyleSheet("color:#E5E7EB;background:transparent;")
                lay.addWidget(sep)
        lay.addStretch()

    def set_step(self, step):
        self._current = step
        for i, lbl in enumerate(self._labels):
            if i < step:
                lbl.setStyleSheet("font-size:13px;color:#059669;font-weight:600;background:transparent;")
                lbl.setText(f"✓  {self._steps[i]}")
            elif i == step:
                lbl.setStyleSheet("font-size:13px;color:#2563EB;font-weight:700;background:transparent;")
                lbl.setText(f"● {self._steps[i]}")
            else:
                lbl.setStyleSheet("font-size:13px;color:#9CA3AF;background:transparent;")
                lbl.setText(f"{i+1}  {self._steps[i]}")
