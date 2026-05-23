"""Inventory Report — stock levels, issuance summary, low-stock alerts."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QGridLayout,
    QAbstractItemView, QSizePolicy
)
from PyQt6.QtGui import QColor
from database.db import fetch_all, fetch_one


def _stat(label, value, color):
    f = QFrame()
    f.setStyleSheet("QFrame{background:white;border:1px solid #E5E7EB;border-radius:10px;}")
    f.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    f.setMinimumHeight(90)
    lay = QVBoxLayout(f); lay.setContentsMargins(16, 12, 16, 12)
    v = QLabel(value); v.setStyleSheet(f"font-size:20px;font-weight:700;color:{color};")
    l = QLabel(label); l.setStyleSheet("font-size:12px;color:#6B7280;")
    lay.addWidget(v); lay.addWidget(l)
    return f, v


class InventoryReportWidget(QWidget):
    COLS = ["Item", "Category", "Unit Price (TZS)", "In Stock", "Reorder Level",
            "Total Issued", "Total Returned", "Stock Value (TZS)", "Status"]

    def __init__(self):
        super().__init__()
        self._stats = {}
        self._build()
        self.load_table()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 20, 28, 20); layout.setSpacing(14)

        t = QLabel("Inventory Report")
        t.setStyleSheet("font-size:20px;font-weight:700;color:#111827;")
        layout.addWidget(t)

        grid = QGridLayout(); grid.setSpacing(12)
        for i, (key, lbl, color) in enumerate([
            ("items",    "Total Items",    "#D97706"),
            ("low",      "Low Stock",      "#DC2626"),
            ("issued",   "Total Issued",   "#2563EB"),
            ("value",    "Stock Value",    "#059669"),
        ]):
            f, v = _stat(lbl, "—", color)
            self._stats[key] = v
            grid.addWidget(f, 0, i)
        layout.addLayout(grid)

        lbl = QLabel("Stock Level by Item")
        lbl.setStyleSheet("font-size:14px;font-weight:600;color:#374151;margin-top:4px;")
        layout.addWidget(lbl)

        self.table = QTableWidget()
        self.table.setColumnCount(len(self.COLS))
        self.table.setHorizontalHeaderLabels(self.COLS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet("""
            QTableWidget{border:1px solid #E5E7EB;border-radius:8px;
                gridline-color:#F3F4F6;font-size:13px;}
            QHeaderView::section{background:#F9FAFB;font-weight:600;
                padding:8px;border:none;border-bottom:1px solid #E5E7EB;color:#374151;}
            QTableWidget::item{padding:6px 8px;}
        """)
        layout.addWidget(self.table)

    def load_table(self):
        items = fetch_all("""
            SELECT ii.id, ii.name, ii.category, ii.unit_price, ii.stock_qty,
                   ii.reorder_qty,
                   COALESCE(SUM(CASE WHEN it.type='issued' THEN it.qty ELSE 0 END),0)   AS issued,
                   COALESCE(SUM(CASE WHEN it.type='returned' THEN it.qty ELSE 0 END),0) AS returned
            FROM inventory_items ii
            LEFT JOIN inventory_transactions it ON it.item_id=ii.id
            WHERE ii.is_active=1
            GROUP BY ii.id ORDER BY ii.category, ii.name
        """)

        low_count = issued_total = total_value = 0
        self.table.setRowCount(len(items))

        for r, row in enumerate(items):
            low = row["stock_qty"] <= row["reorder_qty"]
            if low: low_count += 1
            issued_total += row["issued"]
            val = row["stock_qty"] * row["unit_price"]
            total_value += val
            status = "LOW STOCK" if low else "OK"

            for c, v in enumerate([
                row["name"], row["category"].title(),
                f"{row['unit_price']:,.0f}",
                str(row["stock_qty"]),
                str(row["reorder_qty"]),
                str(row["issued"]),
                str(row["returned"]),
                f"{val:,.0f}",
                status,
            ]):
                item = QTableWidgetItem(v)
                if low:
                    item.setBackground(QColor("#FEE2E2"))
                    item.setForeground(QColor("#991B1B"))
                self.table.setItem(r, c, item)

        self._stats["items"].setText(str(len(items)))
        self._stats["low"].setText(str(low_count))
        self._stats["issued"].setText(str(issued_total))
        self._stats["value"].setText(f"TZS {total_value:,.0f}")
