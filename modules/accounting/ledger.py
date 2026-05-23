"""Ledger — income vs expenses summary and audit trail."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QAbstractItemView
)
from PyQt6.QtGui import QColor
from database.db import fetch_all, fetch_one

INPUT = "QComboBox{border:1px solid #D1D5DB;border-radius:6px;padding:6px 10px;font-size:13px;background:white;}"


def _card(label, value, bg, fg):
    f = QFrame()
    f.setStyleSheet(f"QFrame{{background:{bg};border-radius:10px;border:1px solid {fg}22;}}")
    f.setMinimumHeight(80)
    lay = QVBoxLayout(f); lay.setContentsMargins(16, 12, 16, 12)
    v = QLabel(value); v.setStyleSheet(f"font-size:22px;font-weight:700;color:{fg};")
    l = QLabel(label); l.setStyleSheet(f"font-size:12px;color:{fg};opacity:0.8;")
    lay.addWidget(v); lay.addWidget(l)
    return f, v


class LedgerWidget(QWidget):
    AUDIT_COLS = ["Timestamp", "User", "Action", "Table", "Detail"]

    def __init__(self):
        super().__init__()
        self._cards = {}
        self._build()
        self.load_table()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 20, 28, 20); layout.setSpacing(16)

        t = QLabel("Financial Ledger")
        t.setStyleSheet("font-size:20px;font-weight:700;color:#111827;")
        layout.addWidget(t)

        # Year filter
        bar = QHBoxLayout()
        self.year_cb = QComboBox(); self.year_cb.setStyleSheet(INPUT)
        self.year_cb.addItem("Current month", "month")
        self.year_cb.addItem("Current year", "year")
        self.year_cb.addItem("All time", "all")
        self.year_cb.currentIndexChanged.connect(self.load_table)
        bar.addWidget(QLabel("Period:")); bar.addWidget(self.year_cb); bar.addStretch()
        layout.addLayout(bar)

        # Summary cards
        cards_row = QHBoxLayout(); cards_row.setSpacing(14)
        for key, label, bg, fg in [
            ("income",  "Total Income",  "#D1FAE5", "#065F46"),
            ("expense", "Total Expenses","#FEE2E2", "#991B1B"),
            ("surplus", "Net Surplus",   "#DBEAFE", "#1E40AF"),
            ("waivers", "Fees Waived",   "#EDE9FE", "#4C1D95"),
        ]:
            f, v = _card(label, "TZS 0", bg, fg)
            self._cards[key] = v
            cards_row.addWidget(f)
        layout.addLayout(cards_row)

        # Audit trail table
        audit_lbl = QLabel("Audit Trail (recent 300 actions)")
        audit_lbl.setStyleSheet("font-size:14px;font-weight:600;color:#374151;margin-top:8px;")
        layout.addWidget(audit_lbl)

        self.table = QTableWidget()
        self.table.setColumnCount(len(self.AUDIT_COLS))
        self.table.setHorizontalHeaderLabels(self.AUDIT_COLS)
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
        period = self.year_cb.currentData()
        if period == "month":
            date_filter = "AND strftime('%Y-%m',payment_date)=strftime('%Y-%m','now')"
            exp_filter  = "AND strftime('%Y-%m',expense_date)=strftime('%Y-%m','now')"
            waiv_filter = "AND strftime('%Y-%m',fw.created_at)=strftime('%Y-%m','now')"
        elif period == "year":
            date_filter = "AND strftime('%Y',payment_date)=strftime('%Y','now')"
            exp_filter  = "AND strftime('%Y',expense_date)=strftime('%Y','now')"
            waiv_filter = "AND strftime('%Y',fw.created_at)=strftime('%Y','now')"
        else:
            date_filter = exp_filter = waiv_filter = ""

        income = fetch_one(
            f"SELECT COALESCE(SUM(amount_paid),0) AS t FROM fee_payments WHERE 1=1 {date_filter}"
        )
        expense = fetch_one(
            f"SELECT COALESCE(SUM(amount),0) AS t FROM expenses WHERE 1=1 {exp_filter}"
        )
        waivers = fetch_one(
            f"""SELECT COALESCE(SUM(sb.amount_due * fw.discount_percent/100),0) AS t
                FROM fee_waivers fw
                JOIN student_bills sb ON sb.id=fw.bill_id
                WHERE 1=1 {waiv_filter}"""
        )

        inc  = income["t"]  if income  else 0
        exp  = expense["t"] if expense else 0
        waiv = waivers["t"] if waivers else 0
        surp = inc - exp

        self._cards["income"].setText(f"TZS {inc:,.0f}")
        self._cards["expense"].setText(f"TZS {exp:,.0f}")
        self._cards["surplus"].setText(f"TZS {surp:,.0f}")
        self._cards["surplus"].setStyleSheet(
            f"font-size:22px;font-weight:700;color:{'#065F46' if surp>=0 else '#991B1B'};"
        )
        self._cards["waivers"].setText(f"TZS {waiv:,.0f}")

        # Audit log
        rows = fetch_all("""
            SELECT al.ts, u.full_name AS username, al.action, al.table_name, al.detail
            FROM audit_log al LEFT JOIN users u ON u.id=al.user_id
            ORDER BY al.ts DESC LIMIT 300
        """)
        self.table.setRowCount(len(rows))
        ACTION_COLORS = {
            "payment_recorded": "#065F46",
            "expense_recorded": "#991B1B",
            "item_issued":      "#92400E",
            "welfare_classified": "#4C1D95",
        }
        for r, row in enumerate(rows):
            color = ACTION_COLORS.get(row["action"], "#374151")
            for c, v in enumerate([
                (row["ts"] or "")[:19],
                row["username"] or "—",
                row["action"] or "—",
                row["table_name"] or "—",
                row["detail"] or "—",
            ]):
                item = QTableWidgetItem(v)
                item.setForeground(QColor(color))
                self.table.setItem(r, c, item)
