"""Welfare Classification — mark students as orphan, sponsored, or vulnerable."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QDialog,
    QFormLayout, QComboBox, QLineEdit, QTextEdit, QCheckBox,
    QMessageBox, QAbstractItemView
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from database.db import fetch_all, fetch_one, execute, db_write
from auth.session import session

BTN_PRIMARY = """QPushButton{background:#7C3AED;color:white;border:none;border-radius:7px;
    padding:8px 18px;font-size:13px;font-weight:600;}QPushButton:hover{background:#6D28D9;}"""
BTN_OUTLINE = """QPushButton{background:white;color:#374151;border:1px solid #D1D5DB;
    border-radius:7px;padding:8px 18px;font-size:13px;}QPushButton:hover{background:#F9FAFB;}"""
INPUT = """QLineEdit,QComboBox,QTextEdit{
    border:1px solid #D1D5DB;border-radius:6px;padding:6px 10px;font-size:13px;background:white;}"""

CATEGORIES = ["orphan", "half_orphan", "sponsored", "vulnerable"]
SUPPORT_TYPES = ["full_fees", "partial", "non_financial"]
CAT_COLORS = {
    "orphan":      ("#FEE2E2", "#991B1B"),
    "half_orphan": ("#FEF3C7", "#92400E"),
    "sponsored":   ("#D1FAE5", "#065F46"),
    "vulnerable":  ("#EDE9FE", "#4C1D95"),
}


class WelfareRecordDialog(QDialog):
    def __init__(self, parent=None, student_id=None):
        super().__init__(parent)
        self.student_id = student_id
        self.setWindowTitle("Welfare Record")
        self.setMinimumWidth(480)
        self.setStyleSheet(INPUT + "QDialog{background:#F9FAFB;}")
        self._build()
        if student_id:
            self._load_existing()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20); layout.setSpacing(14)
        title = QLabel("Student Welfare Classification")
        title.setStyleSheet("font-size:16px;font-weight:700;color:#111827;")
        layout.addWidget(title)

        form = QFormLayout(); form.setSpacing(9)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        if not self.student_id:
            self.student_cb = QComboBox()
            for s in fetch_all(
                "SELECT id,admission_no,first_name,last_name FROM students "
                "WHERE is_active=1 ORDER BY last_name"
            ):
                self.student_cb.addItem(
                    f"{s['admission_no']} — {s['first_name']} {s['last_name']}", s["id"]
                )
            l = QLabel("Student *"); l.setStyleSheet("font-size:13px;color:#374151;")
            form.addRow(l, self.student_cb)

        self.cat_cb = QComboBox(); self.cat_cb.addItems(CATEGORIES)
        self.support_cb = QComboBox(); self.support_cb.addItems(SUPPORT_TYPES)
        self.sponsor_name = QLineEdit(); self.sponsor_name.setPlaceholderText("Sponsor name (if any)")
        self.sponsor_org  = QLineEdit(); self.sponsor_org.setPlaceholderText("Sponsoring organisation")
        self.verified_cb  = QCheckBox("Mark as verified")
        self.notes = QTextEdit(); self.notes.setFixedHeight(60)
        self.notes.setPlaceholderText("Additional notes...")

        for lbl, wgt in [
            ("Category *", self.cat_cb),
            ("Support type", self.support_cb),
            ("Sponsor name", self.sponsor_name),
            ("Sponsor org", self.sponsor_org),
            ("Verified", self.verified_cb),
            ("Notes", self.notes),
        ]:
            l = QLabel(lbl); l.setStyleSheet("font-size:13px;color:#374151;")
            form.addRow(l, wgt)
        layout.addLayout(form)

        row = QHBoxLayout(); row.addStretch()
        c = QPushButton("Cancel"); c.setStyleSheet(BTN_OUTLINE)
        s = QPushButton("Save Record"); s.setStyleSheet(BTN_PRIMARY)
        c.clicked.connect(self.reject); s.clicked.connect(self._save)
        row.addWidget(c); row.addWidget(s)
        layout.addLayout(row)

    def _load_existing(self):
        wr = fetch_one("SELECT * FROM welfare_records WHERE student_id=?", (self.student_id,))
        if not wr: return
        idx = self.cat_cb.findText(wr["category"] or "orphan")
        if idx >= 0: self.cat_cb.setCurrentIndex(idx)
        idx2 = self.support_cb.findText(wr["support_type"] or "full_fees")
        if idx2 >= 0: self.support_cb.setCurrentIndex(idx2)
        self.sponsor_name.setText(wr["sponsor_name"] or "")
        self.sponsor_org.setText(wr["sponsor_org"] or "")
        self.verified_cb.setChecked(bool(wr["verified"]))
        self.notes.setPlainText(wr["notes"] or "")

    def _save(self):
        sid = self.student_id or (self.student_cb.currentData() if hasattr(self, "student_cb") else None)
        if not sid:
            QMessageBox.warning(self, "Required", "Select a student."); return

        cat = self.cat_cb.currentText()
        support = self.support_cb.currentText()
        verified = 1 if self.verified_cb.isChecked() else 0
        verified_by = session.user_id if verified else None
        from datetime import date
        verified_date = date.today().isoformat() if verified else None

        existing = fetch_one("SELECT id FROM welfare_records WHERE student_id=?", (sid,))
        if existing:
            execute(
                """UPDATE welfare_records SET category=?,support_type=?,
                   sponsor_name=?,sponsor_org=?,verified=?,verified_by=?,
                   verified_date=?,notes=? WHERE student_id=?""",
                (cat, support,
                 self.sponsor_name.text().strip(), self.sponsor_org.text().strip(),
                 verified, verified_by, verified_date,
                 self.notes.toPlainText().strip(), sid)
            )
        else:
            execute(
                """INSERT INTO welfare_records
                   (student_id,category,support_type,sponsor_name,sponsor_org,
                    verified,verified_by,verified_date,notes)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (sid, cat, support,
                 self.sponsor_name.text().strip(), self.sponsor_org.text().strip(),
                 verified, verified_by, verified_date,
                 self.notes.toPlainText().strip())
            )

        # Sync student_category field
        execute(
            "UPDATE students SET student_category=? WHERE id=?",
            (cat if cat in ["orphan", "sponsored"] else "regular", sid)
        )

        db_write(
            "UPDATE audit_log SET detail=detail WHERE 1=0",  # no-op write for audit
            action="welfare_classified", table="welfare_records",
            detail=f"Student {sid} classified as {cat}", user_id=session.user_id
        )
        self.accept()


class ClassificationWidget(QWidget):
    COLS = ["Student", "Adm No", "Category", "Support Type", "Sponsor", "Verified", "Notes"]

    def __init__(self):
        super().__init__()
        self._build()
        self.load_table()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 20, 28, 20); layout.setSpacing(14)

        row0 = QHBoxLayout()
        t = QLabel("Student Welfare Classification")
        t.setStyleSheet("font-size:20px;font-weight:700;color:#111827;")
        row0.addWidget(t); row0.addStretch()
        add = QPushButton("+ Add / Update Record"); add.setStyleSheet(BTN_PRIMARY)
        add.clicked.connect(self._add)
        row0.addWidget(add)
        layout.addLayout(row0)

        info = QLabel(
            "Classify students as orphan, half-orphan, sponsored, or vulnerable. "
            "Students with 'full_fees' support type are automatically exempt from all fees when billing runs."
        )
        info.setWordWrap(True)
        info.setStyleSheet("background:#EDE9FE;color:#4C1D95;border-radius:8px;"
                           "padding:10px 14px;font-size:12px;")
        layout.addWidget(info)

        self.table = QTableWidget()
        self.table.setColumnCount(len(self.COLS))
        self.table.setHorizontalHeaderLabels(self.COLS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet("""
            QTableWidget{border:1px solid #E5E7EB;border-radius:8px;
                gridline-color:#F3F4F6;font-size:13px;}
            QHeaderView::section{background:#F9FAFB;font-weight:600;
                padding:8px;border:none;border-bottom:1px solid #E5E7EB;color:#374151;}
            QTableWidget::item{padding:6px 8px;}
        """)
        self.table.doubleClicked.connect(self._edit_selected)
        layout.addWidget(self.table)

        act = QHBoxLayout(); act.addStretch()
        self.count_lbl = QLabel("")
        self.count_lbl.setStyleSheet("font-size:12px;color:#9CA3AF;")
        act.addWidget(self.count_lbl); act.addStretch()
        eb = QPushButton("Edit selected"); eb.setStyleSheet(BTN_OUTLINE)
        eb.clicked.connect(self._edit_selected)
        act.addWidget(eb)
        layout.addLayout(act)

    def load_table(self):
        rows = fetch_all("""
            SELECT wr.student_id, s.first_name||' '||s.last_name AS student,
                   s.admission_no, wr.category, wr.support_type,
                   wr.sponsor_name, wr.sponsor_org, wr.verified, wr.notes
            FROM welfare_records wr
            JOIN students s ON s.id=wr.student_id
            ORDER BY wr.category, s.last_name
        """)
        self.table.setRowCount(len(rows))
        self._ids = []
        for r, row in enumerate(rows):
            self._ids.append(row["student_id"])
            bg, fg = CAT_COLORS.get(row["category"], ("#FFFFFF", "#111827"))
            sponsor = row["sponsor_name"] or row["sponsor_org"] or "—"
            for c, v in enumerate([
                row["student"], row["admission_no"],
                row["category"].replace("_", " ").title(),
                row["support_type"].replace("_", " ").title(),
                sponsor,
                "Yes" if row["verified"] else "No",
                row["notes"] or "—",
            ]):
                item = QTableWidgetItem(v)
                item.setBackground(QColor(bg)); item.setForeground(QColor(fg))
                self.table.setItem(r, c, item)
        self.count_lbl.setText(f"{len(rows)} welfare record(s)")

    def _add(self):
        if WelfareRecordDialog(self).exec(): self.load_table()

    def _edit_selected(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self._ids):
            QMessageBox.information(self, "Select", "Select a student first."); return
        sid = self._ids[row]
        if WelfareRecordDialog(self, student_id=sid).exec(): self.load_table()
