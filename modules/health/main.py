"""Health / Infirmary module — student visit records, symptoms, treatment."""
import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QLineEdit, QMessageBox, QAbstractItemView, QDialog,
    QFormLayout, QTextEdit, QDialogButtonBox, QCheckBox,
    QDateEdit, QTabWidget, QFrame
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QColor
from database.db import fetch_all, fetch_one
from services.health_service import health_service, ACTION_LABELS
from services.base import ServiceError, PolicyViolation
from auth.session import session

BTN_PRIMARY = """QPushButton{background:#EC4899;color:white;border:none;border-radius:7px;
    padding:8px 18px;font-size:13px;font-weight:600;}QPushButton:hover{background:#DB2777;}
    QPushButton:disabled{background:#CBD5E1;color:#94A3B8;}"""
BTN_OUTLINE = """QPushButton{background:white;color:#374151;border:1px solid #D1D5DB;
    border-radius:7px;padding:8px 14px;font-size:13px;}QPushButton:hover{background:#F9FAFB;}"""
COMBO = """QComboBox{border:1px solid #D1D5DB;border-radius:6px;padding:6px 10px;
    font-size:13px;background:white;min-width:160px;}"""
FIELD = "border:1px solid #D1D5DB;border-radius:6px;padding:7px 10px;font-size:13px;"

ACTION_COLORS = {
    "treated":   "#059669",
    "referred":  "#DC2626",
    "sent_home": "#F59E0B",
    "rest":      "#2563EB",
    "other":     "#6B7280",
}

COLS = ["Date", "Time", "Student", "Class", "Symptoms", "Action Taken",
        "Parent Notified", "Nurse", ""]


class VisitDialog(QDialog):
    def __init__(self, parent, visit: dict | None = None):
        super().__init__(parent)
        self.setWindowTitle("Record Visit" if visit is None else "Edit Visit")
        self.setMinimumWidth(520)
        self._visit = visit
        self._students = fetch_all(
            "SELECT id, first_name||' '||last_name AS name, admission_no "
            "FROM students WHERE is_active=1 ORDER BY last_name, first_name"
        )
        self._build()
        if visit:
            self._fill(visit)

    def _build(self):
        lay = QVBoxLayout(self)
        form = QFormLayout(); form.setLabelAlignment(Qt.AlignmentFlag.AlignRight); form.setSpacing(10)

        def field(ph=""):
            e = QLineEdit(); e.setPlaceholderText(ph); e.setStyleSheet(FIELD); return e

        # Student
        self.stu_search = QLineEdit(); self.stu_search.setPlaceholderText("Type to filter student…")
        self.stu_search.setStyleSheet(FIELD)
        self.stu_cb = QComboBox(); self.stu_cb.setStyleSheet(COMBO); self.stu_cb.setMinimumWidth(280)
        self._fill_students(self._students)
        self.stu_search.textChanged.connect(self._filter_stu)
        stu_row = QHBoxLayout(); stu_row.addWidget(self.stu_search); stu_row.addWidget(self.stu_cb, 1)
        form.addRow("Student *:", _wrap(stu_row))

        # Date / time
        self.date_e = QDateEdit(); self.date_e.setDate(QDate.currentDate())
        self.date_e.setCalendarPopup(True); self.date_e.setStyleSheet(FIELD)
        self.time_e = field(datetime.datetime.now().strftime("%H:%M"))
        dt_row = QHBoxLayout()
        dt_row.addWidget(self.date_e); dt_row.addWidget(QLabel("Time:")); dt_row.addWidget(self.time_e)
        form.addRow("Date:", _wrap(dt_row))

        # Clinical fields
        self.symptoms_e  = QTextEdit(); self.symptoms_e.setMaximumHeight(60)
        self.symptoms_e.setStyleSheet("border:1px solid #D1D5DB;border-radius:5px;padding:5px;font-size:12px;")
        self.diagnosis_e = QTextEdit(); self.diagnosis_e.setMaximumHeight(60)
        self.diagnosis_e.setStyleSheet("border:1px solid #D1D5DB;border-radius:5px;padding:5px;font-size:12px;")
        self.treatment_e = QTextEdit(); self.treatment_e.setMaximumHeight(60)
        self.treatment_e.setStyleSheet("border:1px solid #D1D5DB;border-radius:5px;padding:5px;font-size:12px;")

        # Action taken
        self.action_cb = QComboBox(); self.action_cb.setStyleSheet(COMBO)
        for key, lbl in ACTION_LABELS.items():
            self.action_cb.addItem(lbl, key)
        self.action_cb.currentIndexChanged.connect(self._on_action)

        self.referred_e = field("Hospital / clinic name")
        self.referred_e.setVisible(False)
        self.referred_lbl = QLabel("Referred To:")

        # Parent notification
        self.parent_cb = QCheckBox("Parent / guardian was notified")
        self.parent_note_e = QTextEdit(); self.parent_note_e.setMaximumHeight(50)
        self.parent_note_e.setStyleSheet("border:1px solid #D1D5DB;border-radius:5px;padding:5px;font-size:12px;")
        self.parent_note_e.setPlaceholderText("Message sent / notes on notification…")

        self.nurse_e = field("Name of nurse / attending staff")

        for lbl, w in [("Symptoms", self.symptoms_e), ("Diagnosis", self.diagnosis_e),
                        ("Treatment", self.treatment_e), ("Action Taken", self.action_cb),
                        ("Referred To", self.referred_e),
                        ("", self.parent_cb), ("Parent Note", self.parent_note_e),
                        ("Staff Name", self.nurse_e)]:
            form.addRow(lbl, w)

        lay.addLayout(form)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self._save); bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def _on_action(self):
        is_ref = self.action_cb.currentData() == "referred"
        self.referred_e.setVisible(is_ref)

    def _fill_students(self, students):
        self.stu_cb.clear()
        self.stu_cb.addItem("-- Select student --", None)
        for s in students:
            self.stu_cb.addItem(f"{s['name']} ({s['admission_no']})", s["id"])

    def _filter_stu(self, text: str):
        text = text.lower()
        filtered = [s for s in self._students
                    if text in (s["name"] or "").lower()
                    or text in (s["admission_no"] or "").lower()]
        self._fill_students(filtered)

    def _fill(self, v: dict):
        idx = self.stu_cb.findData(v["student_id"])
        if idx >= 0: self.stu_cb.setCurrentIndex(idx)
        self.date_e.setDate(QDate.fromString(v.get("visit_date") or "", "yyyy-MM-dd"))
        self.time_e.setText(v.get("visit_time") or "")
        self.symptoms_e.setPlainText(v.get("symptoms") or "")
        self.diagnosis_e.setPlainText(v.get("diagnosis") or "")
        self.treatment_e.setPlainText(v.get("treatment") or "")
        idx = self.action_cb.findData(v.get("action_taken") or "other")
        if idx >= 0: self.action_cb.setCurrentIndex(idx)
        self.referred_e.setText(v.get("referred_to") or "")
        self.parent_cb.setChecked(bool(v.get("parent_notified")))
        self.parent_note_e.setPlainText(v.get("parent_notification_note") or "")
        self.nurse_e.setText(v.get("nurse_name") or "")

    def _save(self):
        student_id = self.stu_cb.currentData()
        if not student_id:
            QMessageBox.warning(self, "Required", "Select a student."); return
        data = {
            "student_id":               student_id,
            "visit_date":               self.date_e.date().toString("yyyy-MM-dd"),
            "visit_time":               self.time_e.text().strip() or datetime.datetime.now().strftime("%H:%M"),
            "symptoms":                 self.symptoms_e.toPlainText().strip(),
            "diagnosis":                self.diagnosis_e.toPlainText().strip(),
            "treatment":                self.treatment_e.toPlainText().strip(),
            "action_taken":             self.action_cb.currentData(),
            "referred_to":              self.referred_e.text().strip(),
            "parent_notified":          self.parent_cb.isChecked(),
            "parent_notification_note": self.parent_note_e.toPlainText().strip(),
            "nurse_name":               self.nurse_e.text().strip(),
        }
        try:
            if self._visit:
                health_service.update_visit(self._visit["id"], data)
            else:
                health_service.record_visit(data)
            self.accept()
        except (ServiceError, PolicyViolation) as e:
            QMessageBox.warning(self, "Error", str(e))


class VisitsTab(QWidget):
    def __init__(self):
        super().__init__()
        self._visits: list[dict] = []
        self._build()
        self.refresh()

    def _build(self):
        lay = QVBoxLayout(self); lay.setContentsMargins(0, 12, 0, 0); lay.setSpacing(10)

        # Stats cards
        self.stats_bar = QFrame()
        self.stats_bar.setStyleSheet(
            "QFrame{background:white;border:1px solid #E5E7EB;border-radius:8px;}"
        )
        sl = QHBoxLayout(self.stats_bar); sl.setContentsMargins(16, 10, 16, 10); sl.setSpacing(30)
        self.stat_total   = _stat_card("Total Visits", "—", "#EC4899")
        self.stat_today   = _stat_card("Today", "—", "#2563EB")
        self.stat_referred = _stat_card("Referred", "—", "#DC2626")
        for s in [self.stat_total, self.stat_today, self.stat_referred]:
            sl.addWidget(s)
        sl.addStretch()
        lay.addWidget(self.stats_bar)

        # Toolbar
        bar = QHBoxLayout(); bar.setSpacing(8)
        self.search_e = QLineEdit(); self.search_e.setPlaceholderText("Search student name…")
        self.search_e.setStyleSheet(FIELD); self.search_e.setMinimumWidth(200)
        self.search_e.returnPressed.connect(self._load)
        self.date_from = QDateEdit(); self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addDays(-30))
        self.date_from.setStyleSheet(FIELD)
        self.date_to = QDateEdit(); self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate()); self.date_to.setStyleSheet(FIELD)
        srch_btn = QPushButton("Search"); srch_btn.setStyleSheet(BTN_OUTLINE)
        srch_btn.clicked.connect(self._load)
        bar.addWidget(QLabel("Student:")); bar.addWidget(self.search_e)
        bar.addWidget(QLabel("From:")); bar.addWidget(self.date_from)
        bar.addWidget(QLabel("To:")); bar.addWidget(self.date_to)
        bar.addWidget(srch_btn); bar.addStretch()
        if session.can("health.record"):
            add_btn = QPushButton("+ Record Visit"); add_btn.setStyleSheet(BTN_PRIMARY)
            add_btn.clicked.connect(self._add); bar.addWidget(add_btn)
        lay.addLayout(bar)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(len(COLS))
        self.table.setHorizontalHeaderLabels(COLS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setStyleSheet("""
            QTableWidget{border:1px solid #E5E7EB;border-radius:8px;
                gridline-color:#F3F4F6;font-size:12px;}
            QHeaderView::section{background:#FDF2F8;font-weight:600;
                padding:7px;border:none;border-bottom:1px solid #FBCFE8;color:#9D174D;}
            QTableWidget::item{padding:5px 7px;}
        """)
        lay.addWidget(self.table)

    def _load(self):
        try:
            visits = health_service.get_visits(
                date_from=self.date_from.date().toString("yyyy-MM-dd"),
                date_to=self.date_to.date().toString("yyyy-MM-dd"),
            )
        except (ServiceError, PolicyViolation) as e:
            QMessageBox.warning(self, "Error", str(e)); return

        q = self.search_e.text().strip().lower()
        if q:
            visits = [v for v in visits if q in (v.get("student_name") or "").lower()]
        self._visits = visits
        self._fill_table(visits)

        # Update stats
        try:
            stats = health_service.get_stats()
            self.stat_total.findChild(QLabel, "val").setText(str(stats["total"]))
            self.stat_today.findChild(QLabel, "val").setText(str(stats["today"]))
            self.stat_referred.findChild(QLabel, "val").setText(str(stats["referred"]))
        except Exception:
            pass

    def _fill_table(self, visits: list[dict]):
        can_record = session.can("health.record")
        self.table.setRowCount(len(visits))
        for r, v in enumerate(visits):
            def cell(val, align=Qt.AlignmentFlag.AlignLeft, fg=None):
                it = QTableWidgetItem(str(val) if val is not None else "—")
                it.setFlags(Qt.ItemFlag.ItemIsEnabled)
                it.setTextAlignment(align | Qt.AlignmentFlag.AlignVCenter)
                if fg: it.setForeground(QColor(fg))
                return it
            ctr = Qt.AlignmentFlag.AlignCenter
            action = v.get("action_taken") or "other"
            self.table.setItem(r, 0, cell(v.get("visit_date") or "—", ctr))
            self.table.setItem(r, 1, cell(v.get("visit_time") or "—", ctr))
            self.table.setItem(r, 2, cell(v.get("student_name") or "—"))
            self.table.setItem(r, 3, cell(v.get("class_name") or "—", ctr))
            symp = (v.get("symptoms") or "—")
            if len(symp) > 50: symp = symp[:47] + "…"
            self.table.setItem(r, 4, cell(symp))
            self.table.setItem(r, 5, cell(
                ACTION_LABELS.get(action, action), ctr, ACTION_COLORS.get(action)
            ))
            notified = bool(v.get("parent_notified"))
            self.table.setItem(r, 6, cell(
                "Yes" if notified else "No", ctr, "#059669" if notified else "#9CA3AF"
            ))
            self.table.setItem(r, 7, cell(v.get("nurse_name") or "—"))
            if can_record:
                edit_btn = QPushButton("Edit"); edit_btn.setStyleSheet(BTN_OUTLINE)
                edit_btn.clicked.connect(lambda _, vid=v["id"]: self._edit(vid))
                self.table.setCellWidget(r, 8, edit_btn)
            else:
                self.table.setItem(r, 8, cell(""))

    def _add(self):
        dlg = VisitDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._load()

    def _edit(self, visit_id: int):
        try:
            v = health_service.get_visit(visit_id)
        except (ServiceError, PolicyViolation) as e:
            QMessageBox.warning(self, "Error", str(e)); return
        dlg = VisitDialog(self, v)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._load()

    def refresh(self):
        self._load()


class HealthWidget(QWidget):
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
            QTabBar::tab:selected{color:#EC4899;border-bottom:2px solid #EC4899;font-weight:600;}
        """)
        self._visits_tab = VisitsTab()
        tabs.addTab(self._visits_tab, "Visit Records")
        lay.addWidget(tabs)

    def refresh(self):
        self._visits_tab.refresh()


# ── Helpers ───────────────────────────────────────────────────────────────────
def _wrap(layout):
    w = QWidget(); w.setLayout(layout); return w


def _stat_card(title: str, value: str, color: str) -> QFrame:
    f = QFrame()
    f.setStyleSheet("QFrame{background:transparent;}")
    fl = QVBoxLayout(f); fl.setSpacing(2); fl.setContentsMargins(0, 0, 0, 0)
    tl = QLabel(title); tl.setStyleSheet(f"color:#6B7280;font-size:11px;background:transparent;")
    vl = QLabel(value); vl.setObjectName("val")
    vl.setStyleSheet(f"color:{color};font-size:22px;font-weight:700;background:transparent;")
    fl.addWidget(tl); fl.addWidget(vl)
    return f
