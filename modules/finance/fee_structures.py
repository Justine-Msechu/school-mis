"""Fee Structures — define what each class owes per term per year."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QDialog,
    QFormLayout, QComboBox, QDoubleSpinBox, QDateEdit, QMessageBox,
    QAbstractItemView
)
from PyQt6.QtCore import Qt, QDate
from database.db import fetch_all, fetch_one, execute

BTN_PRIMARY = """QPushButton{background:#DC2626;color:white;border:none;border-radius:7px;
    padding:8px 18px;font-size:13px;font-weight:600;}QPushButton:hover{background:#B91C1C;}"""
BTN_DANGER = """QPushButton{background:#EF4444;color:white;border:none;border-radius:7px;
    padding:8px 18px;font-size:13px;font-weight:600;}QPushButton:hover{background:#DC2626;}"""
BTN_OUTLINE = """QPushButton{background:white;color:#374151;border:1px solid #D1D5DB;
    border-radius:7px;padding:8px 18px;font-size:13px;}QPushButton:hover{background:#F9FAFB;}"""
INPUT = """QLineEdit,QComboBox,QDoubleSpinBox,QDateEdit{
    border:1px solid #D1D5DB;border-radius:6px;padding:6px 10px;font-size:13px;background:white;}"""


class FeeStructureDialog(QDialog):
    def __init__(self, parent=None, struct_id=None):
        super().__init__(parent)
        self.struct_id = struct_id
        self.setWindowTitle("Edit Fee Structure" if struct_id else "Add Fee Structure")
        self.setMinimumWidth(440)
        self.setStyleSheet(INPUT + "QDialog{background:#F9FAFB;}")
        self._build()
        if struct_id:
            self._load()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20); layout.setSpacing(14)
        title = QLabel("Fee Structure")
        title.setStyleSheet("font-size:16px;font-weight:700;color:#111827;")
        layout.addWidget(title)

        form = QFormLayout(); form.setSpacing(9)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.year_cb = QComboBox()
        for y in fetch_all("SELECT id,label FROM academic_years ORDER BY id DESC"):
            self.year_cb.addItem(y["label"], y["id"])

        self.class_cb = QComboBox()
        self.class_cb.addItem("All classes", None)
        for c in fetch_all("SELECT id,name FROM classes ORDER BY grade_level,name"):
            self.class_cb.addItem(c["name"], c["id"])

        self.fee_type_cb = QComboBox()
        self.fee_type_cb.addItem("-- Select fee type --", None)
        for f in fetch_all("SELECT id,name FROM fee_types ORDER BY name"):
            self.fee_type_cb.addItem(f["name"], f["id"])
        self.fee_type_cb.currentIndexChanged.connect(self._auto_amount)

        self.term_cb = QComboBox()
        self.term_cb.addItems(["Full Year", "Term 1", "Term 2", "Term 3"])

        self.amount = QDoubleSpinBox()
        self.amount.setRange(0, 9_999_999); self.amount.setPrefix("TZS ")
        self.amount.setSingleStep(1000); self.amount.setDecimals(0)

        self.due_date = QDateEdit(); self.due_date.setCalendarPopup(True)
        self.due_date.setDate(QDate.currentDate()); self.due_date.setDisplayFormat("dd/MM/yyyy")

        for lbl, wgt in [
            ("Academic year *", self.year_cb), ("Class", self.class_cb),
            ("Fee type *", self.fee_type_cb), ("Term", self.term_cb),
            ("Amount (TZS) *", self.amount), ("Due date", self.due_date),
        ]:
            l = QLabel(lbl); l.setStyleSheet("font-size:13px;color:#374151;")
            form.addRow(l, wgt)
        layout.addLayout(form)

        row = QHBoxLayout(); row.addStretch()
        c = QPushButton("Cancel"); c.setStyleSheet(BTN_OUTLINE)
        s = QPushButton("Save"); s.setStyleSheet(BTN_PRIMARY)
        c.clicked.connect(self.reject); s.clicked.connect(self._save)
        row.addWidget(c); row.addWidget(s)
        layout.addLayout(row)

    def _auto_amount(self):
        fid = self.fee_type_cb.currentData()
        if fid:
            f = fetch_one("SELECT amount FROM fee_types WHERE id=?", (fid,))
            if f: self.amount.setValue(f["amount"])

    def _load(self):
        row = fetch_one("SELECT * FROM fee_structures WHERE id=?", (self.struct_id,))
        if not row: return
        for i in range(self.year_cb.count()):
            if self.year_cb.itemData(i) == row["academic_year_id"]:
                self.year_cb.setCurrentIndex(i); break
        for i in range(self.class_cb.count()):
            if self.class_cb.itemData(i) == row["class_id"]:
                self.class_cb.setCurrentIndex(i); break
        for i in range(self.fee_type_cb.count()):
            if self.fee_type_cb.itemData(i) == row["fee_type_id"]:
                self.fee_type_cb.setCurrentIndex(i); break
        term_map = {None: 0, 1: 1, 2: 2, 3: 3}
        self.term_cb.setCurrentIndex(term_map.get(row["term"], 0))
        self.amount.setValue(row["amount"])
        if row["due_date"]:
            self.due_date.setDate(QDate.fromString(row["due_date"], "yyyy-MM-dd"))

    def _save(self):
        if not self.fee_type_cb.currentData():
            QMessageBox.warning(self, "Validation", "Please select a fee type."); return
        if self.amount.value() <= 0:
            QMessageBox.warning(self, "Validation", "Amount must be greater than zero."); return
        term_map = {0: None, 1: 1, 2: 2, 3: 3}
        term = term_map[self.term_cb.currentIndex()]
        data = (
            self.year_cb.currentData(), self.class_cb.currentData(),
            self.fee_type_cb.currentData(), self.amount.value(),
            term, self.due_date.date().toString("yyyy-MM-dd"),
        )
        if self.struct_id:
            execute("""UPDATE fee_structures SET academic_year_id=?,class_id=?,
                fee_type_id=?,amount=?,term=?,due_date=? WHERE id=?""",
                data + (self.struct_id,))
        else:
            execute("""INSERT INTO fee_structures
                (academic_year_id,class_id,fee_type_id,amount,term,due_date)
                VALUES (?,?,?,?,?,?)""", data)
        self.accept()


class FeeStructuresWidget(QWidget):
    COLS = ["Academic Year", "Class", "Fee Type", "Term", "Amount (TZS)", "Due Date"]

    def __init__(self):
        super().__init__()
        self._build()
        self.load_table()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 20, 28, 20); layout.setSpacing(14)

        row0 = QHBoxLayout()
        t = QLabel("Fee Structures")
        t.setStyleSheet("font-size:20px;font-weight:700;color:#111827;")
        row0.addWidget(t); row0.addStretch()

        add_ft = QPushButton("+ Fee Type"); add_ft.setStyleSheet(BTN_OUTLINE)
        add_ft.clicked.connect(self._add_fee_type)
        add = QPushButton("+ Add Structure"); add.setStyleSheet(BTN_PRIMARY)
        add.clicked.connect(self._add)
        row0.addWidget(add_ft); row0.addWidget(add)
        layout.addLayout(row0)

        info = QLabel("Define fee structures per academic year and class. Run Billing to generate student bills from these structures.")
        info.setWordWrap(True)
        info.setStyleSheet("background:#FEF2F2;color:#991B1B;border-radius:8px;padding:10px 14px;font-size:12px;")
        layout.addWidget(info)

        self.table = QTableWidget()
        self.table.setColumnCount(len(self.COLS))
        self.table.setHorizontalHeaderLabels(self.COLS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet("""
            QTableWidget{border:1px solid #E5E7EB;border-radius:8px;
                gridline-color:#F3F4F6;font-size:13px;}
            QHeaderView::section{background:#F9FAFB;font-weight:600;
                padding:8px;border:none;border-bottom:1px solid #E5E7EB;color:#374151;}
            QTableWidget::item{padding:6px 8px;}
            QTableWidget::item:selected{background:#FEF2F2;color:#991B1B;}
        """)
        layout.addWidget(self.table)

        act = QHBoxLayout(); act.addStretch()
        eb = QPushButton("Edit"); eb.setStyleSheet(BTN_OUTLINE)
        db = QPushButton("Delete"); db.setStyleSheet(BTN_DANGER)
        eb.clicked.connect(self._edit); db.clicked.connect(self._delete)
        act.addWidget(eb); act.addWidget(db)
        layout.addLayout(act)

    def load_table(self):
        rows = fetch_all("""
            SELECT fs.id, ay.label AS year, c.name AS class_name,
                   ft.name AS fee_name, fs.term, fs.amount, fs.due_date
            FROM fee_structures fs
            JOIN academic_years ay ON ay.id=fs.academic_year_id
            JOIN fee_types ft ON ft.id=fs.fee_type_id
            LEFT JOIN classes c ON c.id=fs.class_id
            ORDER BY ay.id DESC, c.grade_level, ft.name
        """)
        self.table.setRowCount(len(rows))
        self._ids = []
        term_map = {None: "Full Year", 1: "Term 1", 2: "Term 2", 3: "Term 3"}
        for r, row in enumerate(rows):
            self._ids.append(row["id"])
            for c, v in enumerate([
                row["year"], row["class_name"] or "All Classes",
                row["fee_name"], term_map.get(row["term"], "Full Year"),
                f"{row['amount']:,.0f}", row["due_date"] or "—",
            ]):
                self.table.setItem(r, c, QTableWidgetItem(v))

    def _sel_id(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self._ids):
            QMessageBox.information(self, "Select", "Please select a row first."); return None
        return self._ids[row]

    def _add(self):
        if FeeStructureDialog(self).exec(): self.load_table()

    def _edit(self):
        sid = self._sel_id()
        if sid and FeeStructureDialog(self, struct_id=sid).exec(): self.load_table()

    def _delete(self):
        sid = self._sel_id()
        if not sid: return
        r = QMessageBox.question(self, "Confirm", "Delete this fee structure?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if r == QMessageBox.StandardButton.Yes:
            execute("DELETE FROM fee_structures WHERE id=?", (sid,))
            self.load_table()

    def _add_fee_type(self):
        from modules.fees import FeeTypeDialog
        FeeTypeDialog(self).exec()
