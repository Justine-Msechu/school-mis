"""Inventory items — manage stock, add stock, view levels."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QDialog,
    QFormLayout, QComboBox, QLineEdit, QDoubleSpinBox, QSpinBox,
    QMessageBox, QAbstractItemView
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from database.db import fetch_all, fetch_one, execute, db_write
from auth.session import session

BTN_PRIMARY = """QPushButton{background:#D97706;color:white;border:none;border-radius:7px;
    padding:8px 18px;font-size:13px;font-weight:600;}QPushButton:hover{background:#B45309;}"""
BTN_OUTLINE = """QPushButton{background:white;color:#374151;border:1px solid #D1D5DB;
    border-radius:7px;padding:8px 18px;font-size:13px;}QPushButton:hover{background:#F9FAFB;}"""
BTN_DANGER = """QPushButton{background:#EF4444;color:white;border:none;border-radius:7px;
    padding:8px 18px;font-size:13px;font-weight:600;}QPushButton:hover{background:#DC2626;}"""
INPUT = """QLineEdit,QComboBox,QDoubleSpinBox,QSpinBox{
    border:1px solid #D1D5DB;border-radius:6px;padding:6px 10px;font-size:13px;background:white;}"""

CATEGORIES = ["uniform", "book", "stationery", "equipment", "other"]


class ItemDialog(QDialog):
    def __init__(self, parent=None, item_id=None):
        super().__init__(parent)
        self.item_id = item_id
        self.setWindowTitle("Edit Item" if item_id else "Add Stock Item")
        self.setMinimumWidth(420)
        self.setStyleSheet(INPUT + "QDialog{background:#F9FAFB;}")
        self._build()
        if item_id: self._load()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20); layout.setSpacing(14)
        title = QLabel("Stock Item")
        title.setStyleSheet("font-size:16px;font-weight:700;color:#111827;")
        layout.addWidget(title)

        form = QFormLayout(); form.setSpacing(9)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.name = QLineEdit(); self.name.setPlaceholderText("Item name")
        self.cat_cb = QComboBox(); self.cat_cb.addItems(CATEGORIES)
        self.unit = QLineEdit(); self.unit.setPlaceholderText("pcs / pairs / sets")
        self.unit.setText("pcs")
        self.price = QDoubleSpinBox()
        self.price.setRange(0, 999_999); self.price.setPrefix("TZS ")
        self.price.setSingleStep(500); self.price.setDecimals(0)
        self.stock = QSpinBox(); self.stock.setRange(0, 99999)
        self.reorder = QSpinBox(); self.reorder.setRange(0, 9999); self.reorder.setValue(5)

        for lbl, wgt in [
            ("Item name *", self.name), ("Category", self.cat_cb),
            ("Unit", self.unit), ("Unit price (TZS)", self.price),
            ("Opening stock", self.stock), ("Reorder level", self.reorder),
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

    def _load(self):
        it = fetch_one("SELECT * FROM inventory_items WHERE id=?", (self.item_id,))
        if not it: return
        self.name.setText(it["name"])
        idx = self.cat_cb.findText(it["category"] or "other")
        if idx >= 0: self.cat_cb.setCurrentIndex(idx)
        self.unit.setText(it["unit"] or "pcs")
        self.price.setValue(it["unit_price"] or 0)
        self.stock.setValue(it["stock_qty"] or 0)
        self.reorder.setValue(it["reorder_qty"] or 5)

    def _save(self):
        if not self.name.text().strip():
            QMessageBox.warning(self, "Required", "Item name is required."); return
        data = (
            self.name.text().strip(), self.cat_cb.currentText(),
            self.unit.text().strip() or "pcs",
            self.price.value(), self.stock.value(), self.reorder.value(),
        )
        if self.item_id:
            execute(
                "UPDATE inventory_items SET name=?,category=?,unit=?,unit_price=?,"
                "stock_qty=?,reorder_qty=? WHERE id=?",
                data + (self.item_id,)
            )
        else:
            execute(
                "INSERT INTO inventory_items(name,category,unit,unit_price,stock_qty,reorder_qty)"
                " VALUES(?,?,?,?,?,?)", data
            )
        self.accept()


class StockInDialog(QDialog):
    """Add incoming stock for an existing item."""
    def __init__(self, item_id, parent=None):
        super().__init__(parent)
        self.item_id = item_id
        self.setWindowTitle("Add Stock")
        self.setMinimumWidth(360)
        self.setStyleSheet(INPUT + "QDialog{background:#F9FAFB;}")
        self._build()

    def _build(self):
        it = fetch_one("SELECT name,stock_qty FROM inventory_items WHERE id=?", (self.item_id,))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20); layout.setSpacing(14)
        title = QLabel(f"Add Stock: {it['name'] if it else ''}")
        title.setStyleSheet("font-size:15px;font-weight:700;color:#111827;")
        layout.addWidget(title)

        form = QFormLayout(); form.setSpacing(9)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.qty = QSpinBox(); self.qty.setRange(1, 99999)
        self.ref = QLineEdit(); self.ref.setPlaceholderText("Delivery note / PO number")
        self.notes = QLineEdit(); self.notes.setPlaceholderText("Optional notes")
        for lbl, wgt in [("Qty received *", self.qty), ("Reference", self.ref), ("Notes", self.notes)]:
            l = QLabel(lbl); l.setStyleSheet("font-size:13px;color:#374151;")
            form.addRow(l, wgt)
        layout.addLayout(form)

        row = QHBoxLayout(); row.addStretch()
        c = QPushButton("Cancel"); c.setStyleSheet(BTN_OUTLINE)
        s = QPushButton("Add Stock"); s.setStyleSheet(BTN_PRIMARY)
        c.clicked.connect(self.reject); s.clicked.connect(self._save)
        row.addWidget(c); row.addWidget(s)
        layout.addLayout(row)

    def _save(self):
        qty = self.qty.value()
        db_write(
            "INSERT INTO inventory_transactions(item_id,type,qty,reference,notes,recorded_by)"
            " VALUES(?,?,?,?,?,?)",
            (self.item_id, "stock_in", qty,
             self.ref.text().strip(), self.notes.text().strip(), session.user_id),
            action="stock_in", table="inventory_transactions",
            detail=f"Item {self.item_id} +{qty}", user_id=session.user_id
        )
        execute(
            "UPDATE inventory_items SET stock_qty=stock_qty+? WHERE id=?",
            (qty, self.item_id)
        )
        self.accept()


class ItemsWidget(QWidget):
    COLS = ["Name", "Category", "Unit", "Price (TZS)", "In Stock", "Reorder Level", "Status"]

    def __init__(self):
        super().__init__()
        self._build()
        self.load_table()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 20, 28, 20); layout.setSpacing(14)

        row0 = QHBoxLayout()
        t = QLabel("Stock Items")
        t.setStyleSheet("font-size:20px;font-weight:700;color:#111827;")
        row0.addWidget(t); row0.addStretch()
        add_stock = QPushButton("+ Add Stock"); add_stock.setStyleSheet(BTN_OUTLINE)
        add_stock.clicked.connect(self._add_stock)
        add = QPushButton("+ New Item"); add.setStyleSheet(BTN_PRIMARY)
        add.clicked.connect(self._add)
        row0.addWidget(add_stock); row0.addWidget(add)
        layout.addLayout(row0)

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
            QTableWidget::item:selected{background:#FEF3C7;color:#92400E;}
        """)
        self.table.doubleClicked.connect(self._edit)
        layout.addWidget(self.table)

        act = QHBoxLayout()
        self.count_lbl = QLabel("")
        self.count_lbl.setStyleSheet("font-size:12px;color:#9CA3AF;")
        act.addWidget(self.count_lbl); act.addStretch()
        eb = QPushButton("Edit"); eb.setStyleSheet(BTN_OUTLINE)
        eb.clicked.connect(self._edit)
        act.addWidget(eb)
        layout.addLayout(act)

    def load_table(self):
        rows = fetch_all(
            "SELECT * FROM inventory_items WHERE is_active=1 ORDER BY category, name"
        )
        self.table.setRowCount(len(rows))
        self._ids = []
        for r, row in enumerate(rows):
            self._ids.append(row["id"])
            low = row["stock_qty"] <= row["reorder_qty"]
            status = "LOW STOCK" if row["stock_qty"] <= row["reorder_qty"] else "OK"
            for c, v in enumerate([
                row["name"], row["category"].title(),
                row["unit"], f"{row['unit_price']:,.0f}",
                str(row["stock_qty"]), str(row["reorder_qty"]), status,
            ]):
                item = QTableWidgetItem(v)
                if low:
                    item.setForeground(QColor("#991B1B"))
                    item.setBackground(QColor("#FEE2E2"))
                self.table.setItem(r, c, item)
        self.count_lbl.setText(f"{len(rows)} item(s)")

    def _sel_id(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self._ids):
            QMessageBox.information(self, "Select", "Select an item first."); return None
        return self._ids[row]

    def _add(self):
        if ItemDialog(self).exec(): self.load_table()

    def _edit(self):
        iid = self._sel_id()
        if iid and ItemDialog(self, item_id=iid).exec(): self.load_table()

    def _add_stock(self):
        iid = self._sel_id()
        if iid and StockInDialog(iid, self).exec(): self.load_table()
