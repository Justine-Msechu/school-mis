"""modules/settings.py — School settings, user management, academic years, themes."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTabWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QDialog, QFormLayout, QComboBox, QMessageBox,
    QAbstractItemView, QFrame, QApplication
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from database.db import (
    fetch_all, fetch_one, execute,
    get_config, set_config, ROLES, hash_password
)
from auth.session import session
from services.auth_service import auth_service
from services.base import ServiceError

BTN_PRIMARY = """QPushButton{background:#374151;color:#fff;border:none;border-radius:7px;
    padding:8px 18px;font-size:13px;font-weight:600;}QPushButton:hover{background:#1F2937;}"""
BTN_DANGER  = """QPushButton{background:#EF4444;color:#fff;border:none;border-radius:7px;
    padding:8px 14px;font-size:13px;}QPushButton:hover{background:#DC2626;}"""
BTN_OUTLINE = """QPushButton{background:#fff;color:#374151;border:1px solid #D1D5DB;
    border-radius:7px;padding:8px 16px;font-size:13px;}QPushButton:hover{background:#F9FAFB;}"""
COMBO = """QComboBox{border:1px solid #D1D5DB;border-radius:6px;padding:6px 10px;
    font-size:13px;background:white;}"""


# ── Add/Edit User dialog ───────────────────────────────────────────────────────

# Roles a head teacher is allowed to create/assign
_HEAD_TEACHER_ALLOWED_ROLES = {"class_teacher", "subject_teacher", "academic"}


class UserDialog(QDialog):
    def __init__(self, parent=None, user_id=None, editor_role="admin"):
        super().__init__(parent)
        self.user_id     = user_id
        self.editor_role = editor_role
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

        self.f_role = QComboBox()
        # Head teacher can only assign teacher-level roles
        allowed = (
            _HEAD_TEACHER_ALLOWED_ROLES
            if self.editor_role == "head_teacher"
            else set(ROLES.keys())
        )
        for key, info in ROLES.items():
            if key in allowed:
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
                h, salt = hash_password(self.f_pw.text())
                execute("UPDATE users SET password_hash=?,salt=?,must_change_pw=0 WHERE id=?",
                        (h, salt, self.user_id))
        else:
            if not self.f_pw.text():
                QMessageBox.warning(self, "Required", "Password is required for new users."); return
            try:
                auth_service.create_user_account(
                    username=self.f_user.text().strip(),
                    password=self.f_pw.text(),
                    role=self.f_role.currentData(),
                    full_name=self.f_name.text().strip(),
                    teacher_id=self.f_teacher.currentData(),
                    must_change=True,
                )
            except ServiceError as e:
                QMessageBox.warning(self, "Cannot Create User", str(e)); return
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
        tabs.addTab(self._tab_school(),      "School")
        tabs.addTab(self._tab_users(),       "Users & Access")
        tabs.addTab(self._tab_portal_accounts(), "Portal Accounts")
        tabs.addTab(self._tab_years(),       "Academic Years")
        tabs.addTab(self._tab_appearance(),  "Appearance")
        tabs.addTab(self._tab_update(),      "Updates")
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

        # School type selector
        self._school_type_cb = QComboBox()
        self._school_type_cb.setStyleSheet(
            "QComboBox{border:1px solid #D1D5DB;border-radius:6px;"
            "padding:6px 10px;font-size:13px;background:white;}"
        )
        self._school_type_cb.addItem("Primary School", "primary")
        self._school_type_cb.addItem("Secondary School", "secondary")
        current_type = get_config("school_type", "primary")
        idx = self._school_type_cb.findData(current_type)
        if idx >= 0:
            self._school_type_cb.setCurrentIndex(idx)

        type_note = QLabel("Affects grade display (GPA for secondary) and attendance mode.")
        type_note.setStyleSheet("color:#6B7280;font-size:11px;")
        form.addRow(QLabel("School type:"), self._school_type_cb)
        form.addRow("", type_note)

        lay.addLayout(form)

        save = QPushButton("Save school settings"); save.setStyleSheet(BTN_PRIMARY)
        save.clicked.connect(self._save_school)
        lay.addWidget(save, alignment=Qt.AlignmentFlag.AlignLeft)
        lay.addStretch()
        return w

    def _save_school(self):
        for key, e in self._school_fields.items():
            set_config(key, e.text().strip())
        set_config("school_type", self._school_type_cb.currentData())
        QMessageBox.information(self, "Saved", "School settings saved.")

    # ── Users tab ─────────────────────────────────────────────────
    def _tab_users(self):
        w = QWidget(); lay = QVBoxLayout(w); lay.setContentsMargins(20,16,20,16); lay.setSpacing(10)

        if not session.is_admin and not session.is_head_teacher:
            lay.addWidget(QLabel("Only administrators and the head teacher can manage users."))
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
        # Head teacher must not see admin accounts
        if session.is_admin:
            rows = fetch_all("SELECT * FROM users ORDER BY full_name")
        else:
            rows = fetch_all(
                "SELECT * FROM users WHERE role != 'admin' ORDER BY full_name"
            )
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
                tbl.setItem(r, c, item)

    def _add_user(self, tbl):
        if UserDialog(self, editor_role=session.role).exec():
            self._load_users(tbl)

    def _edit_user(self, tbl):
        row = tbl.currentRow()
        if row < 0:
            QMessageBox.information(self, "Select", "Select a user first."); return
        uid = self._user_ids[row]
        target = fetch_one("SELECT role FROM users WHERE id=?", (uid,))
        if target and target["role"] == "admin" and not session.is_admin:
            QMessageBox.warning(self, "Access denied",
                                "Only an administrator can edit admin accounts."); return
        if UserDialog(self, user_id=uid, editor_role=session.role).exec():
            self._load_users(tbl)

    def _deactivate_user(self, tbl):
        row = tbl.currentRow()
        if row < 0: return
        uid = self._user_ids[row]
        target = fetch_one("SELECT role, full_name FROM users WHERE id=?", (uid,))
        r = QMessageBox.question(self, "Confirm",
            f"Deactivate account for {target['full_name'] if target else 'this user'}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if r == QMessageBox.StandardButton.Yes:
            try:
                auth_service.deactivate_user(uid)
            except ServiceError as e:
                QMessageBox.warning(self, "Cannot Deactivate", str(e)); return
            self._load_users(tbl)

    # ── Portal accounts tab ────────────────────────────────────────
    def _tab_portal_accounts(self):
        from PyQt6.QtWidgets import QScrollArea, QGroupBox, QRadioButton, QButtonGroup
        w = QWidget(); lay = QVBoxLayout(w); lay.setContentsMargins(20,16,20,16); lay.setSpacing(14)

        if not (session.is_admin or session.is_head_teacher):
            lay.addWidget(QLabel("Only administrators can manage portal accounts."))
            return w

        lay.addWidget(QLabel(
            "Link student and parent user accounts to their records. "
            "Portal accounts use the same login as staff, but have restricted access."
        ).setWordWrap(True) or QLabel(""))

        info = QLabel(
            "To create a portal account:\n"
            "1. Create the user in 'Users & Access' with role 'Student' or 'Parent / Guardian'.\n"
            "2. Return here to link that user to the appropriate student record.\n"
            "3. For parents, you can link one parent account to multiple children."
        )
        info.setWordWrap(True)
        info.setStyleSheet(
            "background:#F0F9FF;color:#0369A1;border-radius:6px;"
            "padding:10px 14px;font-size:12px;"
        )
        lay.addWidget(info)

        # ── Student accounts ──────────────────────────────────────
        grp_s = QLabel("Student Portal Accounts"); grp_s.setStyleSheet(
            "font-size:13px;font-weight:700;color:#374151;border-bottom:1px solid #E5E7EB;padding-bottom:4px;"
        )
        lay.addWidget(grp_s)

        self._stbl = QTableWidget(); self._stbl.setColumnCount(4)
        self._stbl.setHorizontalHeaderLabels(["Username", "Student Name", "Adm No", "Actions"])
        self._stbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self._stbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._stbl.setAlternatingRowColors(True)
        self._stbl.verticalHeader().setVisible(False)
        self._stbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._stbl.setMaximumHeight(180)
        lay.addWidget(self._stbl)

        link_s_row = QHBoxLayout()
        lbl_u = QLabel("User:")
        self._s_user_cb = QComboBox(); self._s_user_cb.setStyleSheet(COMBO)
        self._s_user_cb.setMinimumWidth(160)
        lbl_st = QLabel("Student:")
        self._s_student_cb = QComboBox(); self._s_student_cb.setStyleSheet(COMBO)
        self._s_student_cb.setMinimumWidth(200)
        link_s_btn = QPushButton("Link"); link_s_btn.setStyleSheet(BTN_PRIMARY)
        link_s_btn.clicked.connect(self._link_student_portal)
        unlink_s_btn = QPushButton("Unlink Selected"); unlink_s_btn.setStyleSheet(BTN_DANGER)
        unlink_s_btn.clicked.connect(self._unlink_student_portal)
        for w2 in [lbl_u, self._s_user_cb, lbl_st, self._s_student_cb, link_s_btn, unlink_s_btn]:
            link_s_row.addWidget(w2)
        link_s_row.addStretch()
        lay.addLayout(link_s_row)

        # ── Parent accounts ───────────────────────────────────────
        grp_p = QLabel("Parent Portal Accounts"); grp_p.setStyleSheet(
            "font-size:13px;font-weight:700;color:#374151;border-bottom:1px solid #E5E7EB;padding-bottom:4px;margin-top:8px;"
        )
        lay.addWidget(grp_p)

        self._ptbl = QTableWidget(); self._ptbl.setColumnCount(4)
        self._ptbl.setHorizontalHeaderLabels(["Username", "Student Name", "Relation", "Actions"])
        self._ptbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self._ptbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._ptbl.setAlternatingRowColors(True)
        self._ptbl.verticalHeader().setVisible(False)
        self._ptbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._ptbl.setMaximumHeight(180)
        lay.addWidget(self._ptbl)

        link_p_row = QHBoxLayout()
        lbl_pu = QLabel("Parent user:")
        self._p_user_cb = QComboBox(); self._p_user_cb.setStyleSheet(COMBO)
        self._p_user_cb.setMinimumWidth(160)
        lbl_ps = QLabel("Student:")
        self._p_student_cb = QComboBox(); self._p_student_cb.setStyleSheet(COMBO)
        self._p_student_cb.setMinimumWidth(200)
        lbl_rel = QLabel("Relation:")
        self._p_rel_cb = QComboBox(); self._p_rel_cb.setStyleSheet(COMBO)
        self._p_rel_cb.addItems(["Parent", "Mother", "Father", "Guardian", "Other"])
        link_p_btn = QPushButton("Link"); link_p_btn.setStyleSheet(BTN_PRIMARY)
        link_p_btn.clicked.connect(self._link_parent_portal)
        unlink_p_btn = QPushButton("Unlink Selected"); unlink_p_btn.setStyleSheet(BTN_DANGER)
        unlink_p_btn.clicked.connect(self._unlink_parent_portal)
        for w2 in [lbl_pu, self._p_user_cb, lbl_ps, self._p_student_cb,
                   lbl_rel, self._p_rel_cb, link_p_btn, unlink_p_btn]:
            link_p_row.addWidget(w2)
        link_p_row.addStretch()
        lay.addLayout(link_p_row)

        lay.addStretch()
        self._load_portal_combos()
        self._load_student_links()
        self._load_parent_links()
        return w

    def _load_portal_combos(self):
        students = fetch_all(
            "SELECT id, first_name||' '||last_name AS name, admission_no "
            "FROM students WHERE is_active=1 ORDER BY last_name, first_name"
        )
        for cb in [self._s_student_cb, self._p_student_cb]:
            cb.clear()
            cb.addItem("-- Select student --", None)
            for s in students:
                cb.addItem(f"{s['name']} ({s['admission_no']})", s["id"])

        s_users = fetch_all(
            "SELECT id, username, full_name FROM users WHERE role='student_portal' AND is_active=1"
        )
        self._s_user_cb.clear()
        self._s_user_cb.addItem("-- Select user --", None)
        for u in s_users:
            self._s_user_cb.addItem(f"{u['username']} ({u['full_name']})", u["id"])

        p_users = fetch_all(
            "SELECT id, username, full_name FROM users WHERE role='parent_portal' AND is_active=1"
        )
        self._p_user_cb.clear()
        self._p_user_cb.addItem("-- Select user --", None)
        for u in p_users:
            self._p_user_cb.addItem(f"{u['username']} ({u['full_name']})", u["id"])

    def _load_student_links(self):
        rows = fetch_all(
            """SELECT u.username, s.first_name||' '||s.last_name AS sname,
                      s.admission_no, spa.user_id, spa.student_id
               FROM student_portal_accounts spa
               JOIN users u ON u.id = spa.user_id
               JOIN students s ON s.id = spa.student_id
               ORDER BY u.username"""
        )
        self._stbl.setRowCount(len(rows))
        self._student_link_ids = []
        for r, row in enumerate(rows):
            self._student_link_ids.append((row["user_id"], row["student_id"]))
            for c, v in enumerate([row["username"], row["sname"], row["admission_no"]]):
                it = QTableWidgetItem(str(v or "—"))
                it.setFlags(Qt.ItemFlag.ItemIsEnabled)
                self._stbl.setItem(r, c, it)
            unlink = QPushButton("Remove"); unlink.setStyleSheet(BTN_DANGER)
            uid, sid = row["user_id"], row["student_id"]
            unlink.clicked.connect(lambda _, u=uid, s=sid: self._remove_student_link(u, s))
            self._stbl.setCellWidget(r, 3, unlink)

    def _load_parent_links(self):
        rows = fetch_all(
            """SELECT u.username, s.first_name||' '||s.last_name AS sname,
                      ppa.relation, ppa.id AS link_id
               FROM parent_portal_accounts ppa
               JOIN users u ON u.id = ppa.user_id
               JOIN students s ON s.id = ppa.student_id
               ORDER BY u.username"""
        )
        self._ptbl.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, v in enumerate([row["username"], row["sname"], row["relation"] or "Parent"]):
                it = QTableWidgetItem(str(v or "—"))
                it.setFlags(Qt.ItemFlag.ItemIsEnabled)
                self._ptbl.setItem(r, c, it)
            unlink = QPushButton("Remove"); unlink.setStyleSheet(BTN_DANGER)
            lid = row["link_id"]
            unlink.clicked.connect(lambda _, i=lid: self._remove_parent_link(i))
            self._ptbl.setCellWidget(r, 3, unlink)

    def _link_student_portal(self):
        user_id    = self._s_user_cb.currentData()
        student_id = self._s_student_cb.currentData()
        if not user_id or not student_id:
            QMessageBox.warning(self, "Required", "Select both a user and a student."); return
        try:
            execute(
                "INSERT OR REPLACE INTO student_portal_accounts(user_id,student_id) VALUES(?,?)",
                (user_id, student_id)
            )
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e)); return
        self._load_student_links()

    def _unlink_student_portal(self):
        row = self._stbl.currentRow()
        if row < 0: return
        uid, sid = self._student_link_ids[row]
        self._remove_student_link(uid, sid)

    def _remove_student_link(self, user_id, student_id):
        execute(
            "DELETE FROM student_portal_accounts WHERE user_id=? AND student_id=?",
            (user_id, student_id)
        )
        self._load_student_links()

    def _link_parent_portal(self):
        user_id    = self._p_user_cb.currentData()
        student_id = self._p_student_cb.currentData()
        relation   = self._p_rel_cb.currentText()
        if not user_id or not student_id:
            QMessageBox.warning(self, "Required", "Select both a parent user and a student."); return
        try:
            execute(
                """INSERT OR IGNORE INTO parent_portal_accounts(user_id,student_id,relation)
                   VALUES(?,?,?)""",
                (user_id, student_id, relation)
            )
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e)); return
        self._load_parent_links()

    def _unlink_parent_portal(self):
        row = self._ptbl.currentRow()
        if row < 0: return
        lid = self._ptbl.item(row, 0)  # placeholder — handled by per-row buttons

    def _remove_parent_link(self, link_id: int):
        execute("DELETE FROM parent_portal_accounts WHERE id=?", (link_id,))
        self._load_parent_links()

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
                                        row["end_date"], "Current" if row["is_current"] else ""]):
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

    # ── Appearance tab ────────────────────────────────────────────
    def _tab_appearance(self):
        w = QWidget(); lay = QVBoxLayout(w); lay.setContentsMargins(20, 20, 20, 20); lay.setSpacing(16)

        title = QLabel("Theme")
        title.setStyleSheet("font-size:15px;font-weight:700;color:#111827;")
        lay.addWidget(title)

        hint = QLabel("Choose a theme that is comfortable for your eyes. Changes apply immediately.")
        hint.setWordWrap(True)
        hint.setStyleSheet("font-size:12px;color:#6B7280;")
        lay.addWidget(hint)

        from ui.theme import THEMES
        current_key = get_config(f"theme_user_{session.user_id}", "light")

        cards_row = QHBoxLayout(); cards_row.setSpacing(16)
        self._theme_cards = {}
        for key, info in THEMES.items():
            card = self._build_theme_card(key, info, active=(key == current_key))
            self._theme_cards[key] = card
            cards_row.addWidget(card)
        cards_row.addStretch()
        lay.addLayout(cards_row)
        lay.addStretch()
        return w

    def _build_theme_card(self, key, info, active):
        bg, panel, accent = info["preview"]
        card = QFrame()
        card.setFixedSize(140, 120)
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        self._style_theme_card(card, bg, accent, active)

        cl = QVBoxLayout(card); cl.setContentsMargins(10, 10, 10, 10); cl.setSpacing(6)

        # Mini preview pane
        preview = QFrame()
        preview.setFixedHeight(52)
        border_c = "#334155" if key == "dark" else "#E5E7EB"
        preview.setStyleSheet(
            f"QFrame{{background:{panel};border:1px solid {border_c};border-radius:5px;}}"
        )
        pl = QVBoxLayout(preview); pl.setContentsMargins(7, 5, 7, 5); pl.setSpacing(4)
        bar_colors = (
            [accent, "#475569", "#334155"] if key == "dark"
            else [accent, "#D1D5DB", "#E5E7EB"] if key == "light"
            else [accent, "#BFDBFE", "#DBEAFE"]
        )
        for color in bar_colors:
            bar = QFrame()
            bar.setFixedHeight(4)
            bar.setStyleSheet(f"background:{color};border-radius:2px;border:none;")
            pl.addWidget(bar)
        cl.addWidget(preview)

        name_lbl = QLabel(info["name"])
        name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text_color = "#F1F5F9" if key == "dark" else "#374151"
        name_lbl.setStyleSheet(
            f"font-size:12px;font-weight:600;color:{text_color};background:transparent;"
        )
        cl.addWidget(name_lbl)

        if active:
            active_lbl = QLabel("Active")
            active_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            active_lbl.setObjectName("active_lbl")
            active_lbl.setStyleSheet(f"font-size:10px;color:{accent};background:transparent;")
            cl.addWidget(active_lbl)

        card.mousePressEvent = lambda e, k=key: self._set_theme(k)
        return card

    @staticmethod
    def _style_theme_card(card, bg, accent, active):
        border = accent if active else "#D1D5DB"
        width  = "2px" if active else "1px"
        card.setStyleSheet(
            f"QFrame{{background:{bg};border:{width} solid {border};border-radius:10px;}}"
        )

    def _set_theme(self, key):
        from ui.theme import THEMES
        theme = THEMES.get(key, THEMES["light"])

        # Apply stylesheet + content-area background via MainWindow
        for widget in QApplication.instance().topLevelWidgets():
            from ui.main_window import MainWindow
            if isinstance(widget, MainWindow):
                widget.apply_theme(key, save=True)
                break

        # Update card borders to reflect new selection
        for k, card in self._theme_cards.items():
            _, _, accent = THEMES[k]["preview"]
            bg = THEMES[k]["preview"][0]
            self._style_theme_card(card, bg, accent, active=(k == key))
            # update/hide the "✓ Active" label
            for child in card.findChildren(QLabel):
                if child.objectName() == "active_lbl":
                    child.setVisible(k == key)

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

        btn = QPushButton("Check for updates now"); btn.setStyleSheet(BTN_PRIMARY)
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
                self._update_status.setText(f"Note: {info['note']}")
            else:
                self._update_status.setText(f"You are on the latest version (v{info['local']}).")
        except Exception as e:
            self._update_status.setText(f"Could not check for updates: {e}")
