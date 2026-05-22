"""modules/settings.py — School settings, user management, academic years."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTabWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QDialog, QFormLayout, QComboBox, QMessageBox,
    QAbstractItemView, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from database.db import (
    fetch_all, fetch_one, execute, create_user,
    get_config, set_config, ROLES
)
from auth.session import session

BTN_PRIMARY = """QPushButton{background:#374151;color:#fff;border:none;border-radius:7px;
    padding:8px 18px;font-size:13px;font-weight:600;}QPushButton:hover{background:#1F2937;}"""
BTN_DANGER  = """QPushButton{background:#EF4444;color:#fff;border:none;border-radius:7px;
    padding:8px 14px;font-size:13px;}QPushButton:hover{background:#DC2626;}"""
BTN_OUTLINE = """QPushButton{background:#fff;color:#374151;border:1px solid #D1D5DB;
    border-radius:7px;padding:8px 16px;font-size:13px;}QPushButton:hover{background:#F9FAFB;}"""


# ── Add/Edit User dialog ───────────────────────────────────────────────────────
class UserDialog(QDialog):
    def __init__(self, parent=None, user_id=None):
        super().__init__(parent)
        self.user_id = user_id
        self.setWindowTitle("Edit User" if user_id else "Add User")
        self.setMinimumWidth(420)
        self._build()
        if user_id: self._load()

    def _build(self):
        lay = QVBoxLayout(self); lay.setContentsMargins(24,20,24,20); lay.setSpacing(12)
        title = QLabel("User Account")
        title.setStyleSheet("font-size:16px;font-weight:700;color:#111827;")
        lay.addWidget(title)

        form = QFormLayout(); form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.f_name  = QLineEdit(); self.f_name.setPlaceholderText("Full name")
        self.f_user  = QLineEdit(); self.f_user.setPlaceholderText("username (no spaces)")
        self.f_pw    = QLineEdit(); self.f_pw.setEchoMode(QLineEdit.EchoMode.Password)
        self.f_pw.setPlaceholderText("Leave blank to keep existing password")
        self.f_role  = QComboBox()
        for key, info in ROLES.items():
            self.f_role.addItem(info["label"], key)
        self.f_teacher = QComboBox()
        self.f_teacher.addItem("— Not linked to a teacher —", None)
        for t in fetch_all("SELECT id,first_name,last_name FROM teachers WHERE is_active=1"):
            self.f_teacher.addItem(f"{t['first_name']} {t['last_name']}", t["id"])

        for lbl, wgt in [
            ("Full name *", self.f_name), ("Username *", self.f_user),
            ("Password",    self.f_pw),   ("Role *", self.f_role),
            ("Linked teacher", self.f_teacher),
        ]:
            l = QLabel(lbl); l.setStyleSheet("font-size:13px;color:#374151;")
            form.addRow(l, wgt)
        lay.addLayout(form)

        row = QHBoxLayout(); row.addStretch()
        c = QPushButton("Cancel"); c.setStyleSheet(BTN_OUTLINE)
        s = QPushButton("Save");   s.setStyleSheet(BTN_PRIMARY)
        c.clicked.connect(self.reject); s.clicked.connect(self._save)
        row.addWidget(c); row.addWidget(s)
        lay.addLayout(row)

    def _load(self):
        u = fetch_one("SELECT * FROM users WHERE id=?", (self.user_id,))
        if not u: return
        self.f_name.setText(u["full_name"]); self.f_user.setText(u["username"])
        for i in range(self.f_role.count()):
            if self.f_role.itemData(i) == u["role"]:
                self.f_role.setCurrentIndex(i); break
        for i in range(self.f_teacher.count()):
            if self.f_teacher.itemData(i) == u["teacher_id"]:
                self.f_teacher.setCurrentIndex(i); break

    def _save(self):
        if not self.f_name.text().strip() or not self.f_user.text().strip():
            QMessageBox.warning(self, "Required", "Name and username are required."); return

        if self.user_id:
            execute("UPDATE users SET full_name=?,username=?,role=?,teacher_id=? WHERE id=?",
                    (self.f_name.text().strip(), self.f_user.text().strip(),
                     self.f_role.currentData(), self.f_teacher.currentData(), self.user_id))
            if self.f_pw.text():
                from database.db import hash_password
                h, salt = hash_password(self.f_pw.text())
                execute("UPDATE users SET password_hash=?,salt=?,must_change_pw=0 WHERE id=?",
                        (h, salt, self.user_id))
        else:
            if not self.f_pw.text():
                QMessageBox.warning(self, "Required", "Password is required for new users."); return
            create_user(self.f_user.text().strip(), self.f_pw.text(),
                        self.f_role.currentData(), self.f_name.text().strip(),
                        self.f_teacher.currentData(), must_change=True)
        self.accept()


# ── Main Settings Widget ───────────────────────────────────────────────────────
class SettingsWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._build()

    def _build(self):
        lay = QVBoxLayout(self); lay.setContentsMargins(28,24,28,24); lay.setSpacing(16)

        title = QLabel("Settings")
        title.setStyleSheet("font-size:22px;font-weight:700;color:#111827;")
        lay.addWidget(title)

        tabs = QTabWidget()
        tabs.addTab(self._tab_school(),  "🏫  School")
        tabs.addTab(self._tab_users(),   "👤  Users & Access")
        tabs.addTab(self._tab_years(),   "📅  Academic Years")
        tabs.addTab(self._tab_update(),  "🔄  Updates")
        lay.addWidget(tabs)

    # ── School info tab ───────────────────────────────────────────
    def _tab_school(self):
        w = QWidget(); lay = QVBoxLayout(w); lay.setContentsMargins(20,16,20,16); lay.setSpacing(10)
        form = QFormLayout(); form.setSpacing(10); form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        fields = [
            ("school_name",    "School name",    ""),
            ("school_address", "Address",        ""),
            ("school_phone",   "Phone",          ""),
            ("school_email",   "Email",          ""),
            ("school_motto",   "Motto",          ""),
        ]
        self._school_fields = {}
        for key, lbl, ph in fields:
            e = QLineEdit(); e.setPlaceholderText(ph)
            e.setText(get_config(key, ""))
            form.addRow(QLabel(lbl), e)
            self._school_fields[key] = e

        lay.addLayout(form)

        save = QPushButton("Save school settings"); save.setStyleSheet(BTN_PRIMARY)
        save.clicked.connect(self._save_school)
        lay.addWidget(save, alignment=Qt.AlignmentFlag.AlignLeft)
        lay.addStretch()
        return w

    def _save_school(self):
        for key, e in self._school_fields.items():
            set_config(key, e.text().strip())
        QMessageBox.information(self, "Saved", "School settings saved.")

    # ── Users tab ─────────────────────────────────────────────────
    def _tab_users(self):
        w = QWidget(); lay = QVBoxLayout(w); lay.setContentsMargins(20,16,20,16); lay.setSpacing(10)

        if not session.is_admin and not session.is_head_teacher:
            lay.addWidget(QLabel("⚠  Only administrators and the head teacher can manage users."))
            return w

        row0 = QHBoxLayout()
        row0.addWidget(QLabel("User accounts")); row0.addStretch()
        add = QPushButton("+ Add user"); add.setStyleSheet(BTN_PRIMARY)
        add.clicked.connect(lambda: self._add_user(tbl))
        row0.addWidget(add)
        lay.addLayout(row0)

        tbl = QTableWidget()
        tbl.setColumnCount(5)
        tbl.setHorizontalHeaderLabels(["Username","Full name","Role","Last login","Status"])
        tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tbl.verticalHeader().setVisible(False)
        tbl.setAlternatingRowColors(True)
        lay.addWidget(tbl)

        act = QHBoxLayout(); act.addStretch()
        eb = QPushButton("Edit");       eb.setStyleSheet(BTN_OUTLINE)
        db = QPushButton("Deactivate"); db.setStyleSheet(BTN_DANGER)
        eb.clicked.connect(lambda: self._edit_user(tbl))
        db.clicked.connect(lambda: self._deactivate_user(tbl))
        act.addWidget(eb); act.addWidget(db)
        lay.addLayout(act)

        self._users_table = tbl
        self._load_users(tbl)
        return w

    def _load_users(self, tbl):
        rows = fetch_all("SELECT * FROM users ORDER BY full_name")
        tbl.setRowCount(len(rows))
        self._user_ids = []
        for r, u in enumerate(rows):
            self._user_ids.append(u["id"])
            role_info  = ROLES.get(u["role"], {})
            role_label = role_info.get("label", u["role"])
            role_color = role_info.get("color", "#6B7280")
            vals = [u["username"], u["full_name"], role_label,
                    u["last_login"] or "Never", "Active" if u["is_active"] else "Inactive"]
            for c, v in enumerate(vals):
                item = QTableWidgetItem(v)
                if c == 2:
                    item.setForeground(QColor(role_color))
                    item.setFont(item.font())
                tbl.setItem(r, c, item)

    def _add_user(self, tbl):
        if UserDialog(self).exec(): self._load_users(tbl)

    def _edit_user(self, tbl):
        row = tbl.currentRow()
        if row < 0: QMessageBox.information(self,"Select","Select a user first."); return
        if UserDialog(self, user_id=self._user_ids[row]).exec():
            self._load_users(tbl)

    def _deactivate_user(self, tbl):
        row = tbl.currentRow()
        if row < 0: return
        uid = self._user_ids[row]
        if uid == session.user_id:
            QMessageBox.warning(self, "Cannot", "You cannot deactivate your own account."); return
        r = QMessageBox.question(self, "Confirm", "Deactivate this user account?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if r == QMessageBox.StandardButton.Yes:
            execute("UPDATE users SET is_active=0 WHERE id=?", (uid,))
            self._load_users(tbl)

    # ── Academic years tab ────────────────────────────────────────
    def _tab_years(self):
        from PyQt6.QtWidgets import QDateEdit
        from PyQt6.QtCore import QDate
        w = QWidget(); lay = QVBoxLayout(w); lay.setContentsMargins(20,16,20,16); lay.setSpacing(10)
        lay.addWidget(QLabel("Manage academic years:").setObjectName("") or QLabel("Academic Years"))

        tbl = QTableWidget(); tbl.setColumnCount(4)
        tbl.setHorizontalHeaderLabels(["Label","Start","End","Current"])
        tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tbl.verticalHeader().setVisible(False)
        lay.addWidget(tbl)

        def reload():
            rows = fetch_all("SELECT * FROM academic_years ORDER BY id DESC")
            tbl.setRowCount(len(rows))
            for r, row in enumerate(rows):
                for c, v in enumerate([row["label"], row["start_date"],
                                        row["end_date"], "✓" if row["is_current"] else ""]):
                    tbl.setItem(r, c, QTableWidgetItem(v))

        act = QHBoxLayout()
        add = QPushButton("+ Add year"); add.setStyleSheet(BTN_PRIMARY)
        set_cur = QPushButton("Set as current"); set_cur.setStyleSheet(BTN_OUTLINE)

        def add_year():
            lay2 = QDialog(self); lay2.setWindowTitle("Add Academic Year"); lay2.setFixedWidth(320)
            vl = QVBoxLayout(lay2)
            label_e = QLineEdit(); label_e.setPlaceholderText("e.g. 2025/2026")
            start_e = QLineEdit(); start_e.setPlaceholderText("YYYY-MM-DD")
            end_e   = QLineEdit(); end_e.setPlaceholderText("YYYY-MM-DD")
            vl.addWidget(QLabel("Label:")); vl.addWidget(label_e)
            vl.addWidget(QLabel("Start:")); vl.addWidget(start_e)
            vl.addWidget(QLabel("End:"));   vl.addWidget(end_e)
            save = QPushButton("Save"); save.setStyleSheet(BTN_PRIMARY)
            vl.addWidget(save)
            def do_save():
                execute("INSERT OR IGNORE INTO academic_years(label,start_date,end_date) VALUES(?,?,?)",
                        (label_e.text().strip(), start_e.text().strip(), end_e.text().strip()))
                lay2.accept(); reload()
            save.clicked.connect(do_save)
            lay2.exec()

        def set_current():
            row = tbl.currentRow()
            if row < 0: return
            yr = fetch_all("SELECT id FROM academic_years ORDER BY id DESC")[row]["id"]
            execute("UPDATE academic_years SET is_current=0")
            execute("UPDATE academic_years SET is_current=1 WHERE id=?", (yr,))
            reload()

        add.clicked.connect(add_year); set_cur.clicked.connect(set_current)
        act.addWidget(add); act.addWidget(set_cur); act.addStretch()
        lay.addLayout(act)
        reload()
        return w

    # ── Updates tab ───────────────────────────────────────────────
    def _tab_update(self):
        w = QWidget(); lay = QVBoxLayout(w); lay.setContentsMargins(20,20,20,20); lay.setSpacing(12)

        from version_info import get_local_version
        ver = get_local_version()
        lay.addWidget(QLabel(f"Current version: {ver}").setObjectName("") or
                      QLabel(f"Installed version:  v{ver}"))

        vl = QLabel(f"Installed version:  v{ver}")
        vl.setStyleSheet("font-size:14px;font-weight:600;color:#111827;")
        lay.addWidget(vl)

        self._update_status = QLabel("Click 'Check for updates' to see if a newer version is available.")
        self._update_status.setStyleSheet("font-size:13px;color:#6B7280;background:#F9FAFB;"
                                          "border-radius:6px;padding:10px;")
        self._update_status.setWordWrap(True)
        lay.addWidget(self._update_status)

        btn = QPushButton("🔄  Check for updates now"); btn.setStyleSheet(BTN_PRIMARY)
        btn.clicked.connect(self._check_update)
        lay.addWidget(btn, alignment=Qt.AlignmentFlag.AlignLeft)

        info = QLabel(
            "Updates are delivered from GitHub. When an update is found, only changed files "
            "are downloaded — your database and student data are never affected."
        )
        info.setStyleSheet("font-size:12px;color:#6B7280;background:#EFF6FF;border-radius:6px;padding:10px;")
        info.setWordWrap(True)
        lay.addWidget(info)
        lay.addStretch()
        return w

    def _check_update(self):
        from modules.updater import check_for_update, UpdateDialog
        self._update_status.setText("Checking…")
        try:
            info = check_for_update()
            if info.get("available"):
                self._update_status.setText(f"Update available: v{info['remote']}")
                UpdateDialog(info, self).exec()
            elif info.get("note"):
                self._update_status.setText(f"ℹ  {info['note']}")
            else:
                self._update_status.setText(f"✓  You are on the latest version (v{info['local']}).")
        except Exception as e:
            self._update_status.setText(f"⚠  Could not check for updates: {e}")
