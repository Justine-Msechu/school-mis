"""Library catalogue tab — browse, add and edit books."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QLineEdit, QMessageBox, QAbstractItemView, QDialog,
    QFormLayout, QSpinBox, QTextEdit, QDialogButtonBox, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from services.library_service import library_service
from services.base import ServiceError, PolicyViolation
from auth.session import session

BTN_PRIMARY = """QPushButton{background:#F59E0B;color:white;border:none;border-radius:7px;
    padding:8px 18px;font-size:13px;font-weight:600;}QPushButton:hover{background:#D97706;}
    QPushButton:disabled{background:#CBD5E1;color:#94A3B8;}"""
BTN_OUTLINE = """QPushButton{background:white;color:#374151;border:1px solid #D1D5DB;
    border-radius:7px;padding:8px 18px;font-size:13px;}QPushButton:hover{background:#F9FAFB;}"""
BTN_DANGER = """QPushButton{background:#FEF2F2;color:#DC2626;border:1px solid #FECACA;
    border-radius:7px;padding:8px 14px;font-size:12px;}QPushButton:hover{background:#FEE2E2;}"""
COMBO = """QComboBox{border:1px solid #D1D5DB;border-radius:6px;padding:6px 10px;
    font-size:13px;background:white;min-width:140px;}"""

CATEGORIES = ["", "textbook", "fiction", "reference", "non_fiction", "other"]
CAT_LABELS  = {"textbook": "Textbook", "fiction": "Fiction",
               "reference": "Reference", "non_fiction": "Non-Fiction", "other": "Other"}


class BookDialog(QDialog):
    def __init__(self, parent, book: dict | None = None):
        super().__init__(parent)
        self.setWindowTitle("Add Book" if book is None else "Edit Book")
        self.setMinimumWidth(440)
        self._book = book
        self._build()
        if book:
            self._fill(book)

    def _build(self):
        lay = QVBoxLayout(self)
        form = QFormLayout(); form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setSpacing(10)

        def field(ph=""):
            e = QLineEdit(); e.setPlaceholderText(ph)
            e.setStyleSheet("border:1px solid #D1D5DB;border-radius:5px;padding:6px;font-size:13px;")
            return e

        self.title_e    = field("Book title (required)")
        self.author_e   = field("Author name")
        self.isbn_e     = field("ISBN / barcode")
        self.cat_cb     = QComboBox()
        self.cat_cb.setStyleSheet(COMBO)
        for c in CATEGORIES:
            self.cat_cb.addItem(CAT_LABELS.get(c, "-- Category --") if c else "-- Category --", c)
        self.shelf_e    = field("e.g. A-12")
        self.publisher_e = field("Publisher")
        self.year_e     = field("e.g. 2022")
        self.copies_sb  = QSpinBox(); self.copies_sb.setRange(1, 9999); self.copies_sb.setValue(1)
        self.copies_sb.setStyleSheet("border:1px solid #D1D5DB;border-radius:5px;padding:5px;font-size:13px;")
        self.notes_e    = QTextEdit(); self.notes_e.setMaximumHeight(70)
        self.notes_e.setStyleSheet("border:1px solid #D1D5DB;border-radius:5px;padding:5px;font-size:12px;")

        for lbl, w in [("Title *", self.title_e), ("Author", self.author_e),
                        ("ISBN", self.isbn_e), ("Category", self.cat_cb),
                        ("Shelf", self.shelf_e), ("Publisher", self.publisher_e),
                        ("Year", self.year_e), ("Total Copies", self.copies_sb),
                        ("Notes", self.notes_e)]:
            form.addRow(QLabel(lbl), w)
        lay.addLayout(form)

        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self._save); bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def _fill(self, b: dict):
        self.title_e.setText(b.get("title") or "")
        self.author_e.setText(b.get("author") or "")
        self.isbn_e.setText(b.get("isbn") or "")
        idx = self.cat_cb.findData(b.get("category") or "other")
        if idx >= 0: self.cat_cb.setCurrentIndex(idx)
        self.shelf_e.setText(b.get("shelf_location") or "")
        self.publisher_e.setText(b.get("publisher") or "")
        self.year_e.setText(b.get("year") or "")
        self.copies_sb.setValue(b.get("total_copies") or 1)
        self.notes_e.setPlainText(b.get("notes") or "")

    def _save(self):
        if not self.title_e.text().strip():
            QMessageBox.warning(self, "Required", "Book title is required."); return
        data = {
            "title":         self.title_e.text().strip(),
            "author":        self.author_e.text().strip(),
            "isbn":          self.isbn_e.text().strip(),
            "category":      self.cat_cb.currentData() or "other",
            "shelf_location": self.shelf_e.text().strip(),
            "publisher":     self.publisher_e.text().strip(),
            "year":          self.year_e.text().strip(),
            "total_copies":  self.copies_sb.value(),
            "notes":         self.notes_e.toPlainText().strip(),
        }
        try:
            if self._book:
                library_service.update_book(self._book["id"], data)
            else:
                library_service.add_book(data)
            self.accept()
        except (ServiceError, PolicyViolation) as e:
            QMessageBox.warning(self, "Error", str(e))


class CatalogueTab(QWidget):
    COLS = ["Title", "Author", "ISBN", "Category", "Shelf", "Copies", "Available", "On Loan"]

    def __init__(self):
        super().__init__()
        self._books = []
        self._build()
        self.refresh()

    def _build(self):
        lay = QVBoxLayout(self); lay.setContentsMargins(0, 16, 0, 0); lay.setSpacing(10)

        # ── Toolbar ──────────────────────────────────────────────────────────
        bar = QHBoxLayout(); bar.setSpacing(8)
        self.search_e = QLineEdit(); self.search_e.setPlaceholderText("Search title, author, ISBN…")
        self.search_e.setStyleSheet(
            "border:1px solid #D1D5DB;border-radius:6px;padding:7px 10px;font-size:13px;"
        )
        self.search_e.setMinimumWidth(220)
        self.search_e.returnPressed.connect(self._load)

        self.cat_cb = QComboBox(); self.cat_cb.setStyleSheet(COMBO)
        self.cat_cb.addItem("All Categories", "")
        for c in CATEGORIES[1:]:
            self.cat_cb.addItem(CAT_LABELS[c], c)
        self.cat_cb.currentIndexChanged.connect(self._load)

        srch_btn = QPushButton("Search"); srch_btn.setStyleSheet(BTN_OUTLINE)
        srch_btn.clicked.connect(self._load)

        bar.addWidget(self.search_e); bar.addWidget(self.cat_cb); bar.addWidget(srch_btn)
        bar.addStretch()

        can_manage = session.can("library.manage")
        if can_manage:
            add_btn = QPushButton("+ Add Book"); add_btn.setStyleSheet(BTN_PRIMARY)
            add_btn.clicked.connect(self._add)
            bar.addWidget(add_btn)

        lay.addLayout(bar)

        # ── Table ─────────────────────────────────────────────────────────────
        self.table = QTableWidget()
        self.table.setColumnCount(len(self.COLS))
        self.table.setHorizontalHeaderLabels(self.COLS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setStyleSheet("""
            QTableWidget{border:1px solid #E5E7EB;border-radius:8px;
                gridline-color:#F3F4F6;font-size:13px;}
            QHeaderView::section{background:#FEF3C7;font-weight:600;
                padding:7px;border:none;border-bottom:1px solid #FDE68A;color:#92400E;}
            QTableWidget::item{padding:5px 7px;}
        """)
        lay.addWidget(self.table)

        # ── Action row ────────────────────────────────────────────────────────
        if can_manage:
            act = QHBoxLayout(); act.addStretch()
            self.edit_btn = QPushButton("Edit Selected"); self.edit_btn.setStyleSheet(BTN_OUTLINE)
            self.edit_btn.setEnabled(False); self.edit_btn.clicked.connect(self._edit)
            self.deact_btn = QPushButton("Deactivate"); self.deact_btn.setStyleSheet(BTN_DANGER)
            self.deact_btn.setEnabled(False); self.deact_btn.clicked.connect(self._deactivate)
            act.addWidget(self.edit_btn); act.addWidget(self.deact_btn)
            lay.addLayout(act)
            self.table.itemSelectionChanged.connect(self._on_select)

    def _on_select(self):
        sel = bool(self.table.selectedItems())
        self.edit_btn.setEnabled(sel)
        self.deact_btn.setEnabled(sel)

    def _load(self):
        q   = self.search_e.text().strip()
        cat = self.cat_cb.currentData()
        try:
            self._books = library_service.search_books(q, cat)
        except (ServiceError, PolicyViolation) as e:
            QMessageBox.warning(self, "Error", str(e)); return
        self._fill(self._books)

    def _fill(self, books: list[dict]):
        self.table.setRowCount(len(books))
        for r, b in enumerate(books):
            avail = b["available_copies"]
            def cell(v, align=Qt.AlignmentFlag.AlignLeft, fg=None):
                it = QTableWidgetItem(str(v))
                it.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                it.setTextAlignment(align | Qt.AlignmentFlag.AlignVCenter)
                if fg: it.setForeground(QColor(fg))
                return it

            ctr = Qt.AlignmentFlag.AlignCenter
            self.table.setItem(r, 0, cell(b["title"]))
            self.table.setItem(r, 1, cell(b.get("author") or "—"))
            self.table.setItem(r, 2, cell(b.get("isbn") or "—", ctr))
            self.table.setItem(r, 3, cell(CAT_LABELS.get(b.get("category",""), "—"), ctr))
            self.table.setItem(r, 4, cell(b.get("shelf_location") or "—", ctr))
            self.table.setItem(r, 5, cell(b["total_copies"], ctr))
            colour = "#059669" if avail > 0 else "#DC2626"
            self.table.setItem(r, 6, cell(avail, ctr, colour))
            self.table.setItem(r, 7, cell(b.get("on_loan") or 0, ctr))

    def _selected_book(self):
        rows = self.table.selectedItems()
        if not rows: return None
        r = self.table.currentRow()
        return self._books[r] if r < len(self._books) else None

    def _add(self):
        dlg = BookDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._load()

    def _edit(self):
        b = self._selected_book()
        if not b: return
        dlg = BookDialog(self, b)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._load()

    def _deactivate(self):
        b = self._selected_book()
        if not b: return
        if b.get("on_loan", 0) > 0:
            QMessageBox.warning(self, "Cannot Deactivate",
                                "This book has active loans. Return all copies first.")
            return
        if QMessageBox.question(
            self, "Deactivate Book",
            f"Remove '{b['title']}' from the catalogue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) != QMessageBox.StandardButton.Yes:
            return
        try:
            library_service.deactivate_book(b["id"])
        except (ServiceError, PolicyViolation) as e:
            QMessageBox.warning(self, "Error", str(e)); return
        self._load()

    def refresh(self):
        self._load()
