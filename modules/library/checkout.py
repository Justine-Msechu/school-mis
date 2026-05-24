"""Checkout tab — issue books to students or teachers."""
import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QLineEdit, QMessageBox, QAbstractItemView, QFrame,
    QButtonGroup, QRadioButton, QDateEdit
)
from PyQt6.QtCore import Qt, QDate
from database.db import fetch_all, get_config
from services.library_service import library_service
from services.base import ServiceError, PolicyViolation

BTN_PRIMARY = """QPushButton{background:#F59E0B;color:white;border:none;border-radius:7px;
    padding:8px 22px;font-size:13px;font-weight:600;}QPushButton:hover{background:#D97706;}
    QPushButton:disabled{background:#CBD5E1;color:#94A3B8;}"""
BTN_OUTLINE = """QPushButton{background:white;color:#374151;border:1px solid #D1D5DB;
    border-radius:7px;padding:8px 14px;font-size:13px;}QPushButton:hover{background:#F9FAFB;}"""
COMBO = """QComboBox{border:1px solid #D1D5DB;border-radius:6px;padding:6px 10px;
    font-size:13px;background:white;}"""
FIELD = "border:1px solid #D1D5DB;border-radius:6px;padding:7px 10px;font-size:13px;"


def _default_loan_days() -> int:
    return int(get_config("library_loan_days") or 14)


class CheckoutTab(QWidget):
    def __init__(self):
        super().__init__()
        self._books = []
        self._borrowers: list[dict] = []
        self._build()
        self._load_books()
        self._load_borrowers()

    def _build(self):
        lay = QVBoxLayout(self); lay.setContentsMargins(0, 16, 0, 0); lay.setSpacing(14)

        # ── Issue form card ───────────────────────────────────────────────────
        card = QFrame()
        card.setStyleSheet(
            "QFrame{background:white;border:1px solid #E5E7EB;border-radius:10px;}"
        )
        card_lay = QVBoxLayout(card); card_lay.setContentsMargins(20, 16, 20, 16); card_lay.setSpacing(12)

        hdr = QLabel("Issue a Book")
        hdr.setStyleSheet("font-size:14px;font-weight:700;color:#1F2937;background:transparent;")
        card_lay.addWidget(hdr)

        # Row 1: Book selection + search
        r1 = QHBoxLayout(); r1.setSpacing(8)
        r1.addWidget(QLabel("Book:"));
        self.book_search = QLineEdit(); self.book_search.setPlaceholderText("Type title or ISBN to filter…")
        self.book_search.setStyleSheet(FIELD)
        self.book_search.textChanged.connect(self._filter_books)
        self.book_cb = QComboBox(); self.book_cb.setStyleSheet(COMBO); self.book_cb.setMinimumWidth(300)
        r1.addWidget(self.book_search, 1); r1.addWidget(QLabel("→")); r1.addWidget(self.book_cb, 2)
        card_lay.addLayout(r1)

        # Row 2: Borrower type + borrower
        r2 = QHBoxLayout(); r2.setSpacing(10)
        r2.addWidget(QLabel("Borrower:"))
        self.type_grp = QButtonGroup(self)
        self.student_rb = QRadioButton("Student"); self.student_rb.setChecked(True)
        self.teacher_rb = QRadioButton("Teacher")
        self.type_grp.addButton(self.student_rb, 0)
        self.type_grp.addButton(self.teacher_rb, 1)
        self.student_rb.toggled.connect(self._load_borrowers)
        r2.addWidget(self.student_rb); r2.addWidget(self.teacher_rb)
        r2.addSpacing(8)
        self.borrower_cb = QComboBox(); self.borrower_cb.setStyleSheet(COMBO); self.borrower_cb.setMinimumWidth(260)
        self.borrower_search = QLineEdit(); self.borrower_search.setPlaceholderText("Filter borrower…")
        self.borrower_search.setStyleSheet(FIELD); self.borrower_search.setMaximumWidth(180)
        self.borrower_search.textChanged.connect(self._filter_borrowers)
        r2.addWidget(self.borrower_search); r2.addWidget(self.borrower_cb, 1)
        card_lay.addLayout(r2)

        # Row 3: Due date + notes + issue button
        r3 = QHBoxLayout(); r3.setSpacing(10)
        r3.addWidget(QLabel("Due Date:"))
        self.due_date = QDateEdit()
        self.due_date.setCalendarPopup(True)
        due = QDate.currentDate().addDays(_default_loan_days())
        self.due_date.setDate(due)
        self.due_date.setStyleSheet(FIELD)
        self.notes_e = QLineEdit(); self.notes_e.setPlaceholderText("Notes (optional)")
        self.notes_e.setStyleSheet(FIELD)
        issue_btn = QPushButton("Issue Book"); issue_btn.setStyleSheet(BTN_PRIMARY)
        issue_btn.clicked.connect(self._issue)
        r3.addWidget(self.due_date); r3.addWidget(self.notes_e, 1); r3.addWidget(issue_btn)
        card_lay.addLayout(r3)

        lay.addWidget(card)

        # ── Today's checkouts table ───────────────────────────────────────────
        lbl = QLabel("Today's Checkouts")
        lbl.setStyleSheet("font-size:13px;font-weight:700;color:#374151;margin-top:4px;")
        lay.addWidget(lbl)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Book", "Borrower", "Type", "Due Date", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setStyleSheet("""
            QTableWidget{border:1px solid #E5E7EB;border-radius:8px;
                gridline-color:#F3F4F6;font-size:12px;}
            QHeaderView::section{background:#FEF3C7;font-weight:600;
                padding:7px;border:none;border-bottom:1px solid #FDE68A;color:#92400E;}
            QTableWidget::item{padding:5px 7px;}
        """)
        lay.addWidget(self.table)
        self._load_today()

    def _load_books(self):
        try:
            self._books = library_service.search_books(active_only=True)
        except (ServiceError, PolicyViolation):
            self._books = []
        self._fill_books(self._books)

    def _fill_books(self, books: list[dict]):
        self.book_cb.clear()
        self.book_cb.addItem("-- Select book --", None)
        for b in books:
            avail = b.get("available_copies", 0)
            label = f"{b['title']}"
            if b.get("isbn"):
                label += f" [{b['isbn']}]"
            label += f" — {avail} avail."
            self.book_cb.addItem(label, b["id"])

    def _filter_books(self, text: str):
        text = text.lower()
        filtered = [b for b in self._books
                    if text in (b.get("title") or "").lower()
                    or text in (b.get("isbn") or "").lower()]
        self._fill_books(filtered)

    def _load_borrowers(self):
        btype = "student" if self.student_rb.isChecked() else "teacher"
        if btype == "student":
            rows = fetch_all(
                "SELECT id, first_name||' '||last_name AS name, admission_no FROM students "
                "WHERE is_active=1 ORDER BY last_name, first_name"
            )
            self._borrowers = [{"id": r["id"], "name": r["name"],
                                 "label": f"{r['name']} ({r['admission_no']})",
                                 "type": "student"} for r in rows]
        else:
            rows = fetch_all(
                "SELECT id, first_name||' '||last_name AS name FROM teachers "
                "WHERE is_active=1 ORDER BY last_name, first_name"
            )
            self._borrowers = [{"id": r["id"], "name": r["name"],
                                 "label": r["name"], "type": "teacher"} for r in rows]
        self._fill_borrowers(self._borrowers)

    def _fill_borrowers(self, borrowers: list[dict]):
        self.borrower_cb.clear()
        self.borrower_cb.addItem("-- Select borrower --", None)
        for b in borrowers:
            self.borrower_cb.addItem(b["label"], b["id"])

    def _filter_borrowers(self, text: str):
        text = text.lower()
        filtered = [b for b in self._borrowers if text in b["label"].lower()]
        self._fill_borrowers(filtered)

    def _issue(self):
        book_id     = self.book_cb.currentData()
        borrower_id = self.borrower_cb.currentData()
        if not book_id:
            QMessageBox.warning(self, "Required", "Please select a book."); return
        if not borrower_id:
            QMessageBox.warning(self, "Required", "Please select a borrower."); return

        btype   = "student" if self.student_rb.isChecked() else "teacher"
        due     = self.due_date.date().toString("yyyy-MM-dd")
        notes   = self.notes_e.text().strip()

        if self.due_date.date() <= QDate.currentDate():
            QMessageBox.warning(self, "Invalid Date", "Due date must be in the future."); return

        try:
            library_service.checkout_book(book_id, btype, borrower_id, due, notes)
        except (ServiceError, PolicyViolation) as e:
            QMessageBox.warning(self, "Cannot Issue", str(e)); return

        QMessageBox.information(self, "Issued", "Book issued successfully.")
        self.notes_e.clear()
        self.due_date.setDate(QDate.currentDate().addDays(_default_loan_days()))
        self._load_books()
        self._load_today()

    def _load_today(self):
        today = datetime.date.today().isoformat()
        rows = fetch_all(
            """SELECT l.*, b.title AS book_title
               FROM library_loans l
               JOIN library_books b ON b.id=l.book_id
               WHERE l.issue_date=? ORDER BY l.id DESC""",
            (today,)
        )
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            def cell(v, align=Qt.AlignmentFlag.AlignLeft):
                it = QTableWidgetItem(str(v))
                it.setFlags(Qt.ItemFlag.ItemIsEnabled)
                it.setTextAlignment(align | Qt.AlignmentFlag.AlignVCenter)
                return it
            ctr = Qt.AlignmentFlag.AlignCenter
            self.table.setItem(r, 0, cell(row["book_title"]))
            self.table.setItem(r, 1, cell(row["borrower_name"] or "—"))
            self.table.setItem(r, 2, cell(row["borrower_type"].title(), ctr))
            self.table.setItem(r, 3, cell(row["due_date"], ctr))
            self.table.setItem(r, 4, cell(row["status"].title(), ctr))

    def refresh(self):
        self._load_books()
        self._load_borrowers()
        self._load_today()
