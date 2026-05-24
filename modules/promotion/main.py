"""Year-End Student Promotion module."""
import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QLineEdit, QMessageBox, QAbstractItemView, QTabWidget, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from database.db import fetch_all
from services.promotion_service import promotion_service
from services.base import ServiceError, PolicyViolation

BTN_PRIMARY = """QPushButton{background:#059669;color:white;border:none;border-radius:7px;
    padding:8px 20px;font-size:13px;font-weight:600;}QPushButton:hover{background:#047857;}
    QPushButton:disabled{background:#CBD5E1;color:#94A3B8;}"""
BTN_OUTLINE = """QPushButton{background:white;color:#374151;border:1px solid #D1D5DB;
    border-radius:7px;padding:8px 14px;font-size:13px;}QPushButton:hover{background:#F9FAFB;}"""
COMBO = """QComboBox{border:1px solid #D1D5DB;border-radius:6px;padding:6px 10px;
    font-size:13px;background:white;min-width:160px;}"""

ACTION_OPTS   = [("Promote",   "promote"),
                 ("Hold Back", "hold_back"),
                 ("Graduate",  "graduate")]
ACTION_COLORS = {"promote": "#059669", "hold_back": "#F59E0B", "graduate": "#6B7280"}


class PromoteTab(QWidget):
    COLS = ["Student", "Adm No", "Avg %", "Decision", "Notes", "Done?"]

    def __init__(self):
        super().__init__()
        self._students: list[dict] = []
        self._decision_cbs: dict[int, QComboBox] = {}
        self._note_edits:   dict[int, QLineEdit]  = {}
        self._build()
        self._load_meta()

    def _load_meta(self):
        self._years   = fetch_all("SELECT id, label FROM academic_years ORDER BY id DESC")
        self._classes = fetch_all("SELECT id, name, grade_level FROM classes ORDER BY grade_level, name")

        self.year_cb.clear()
        for y in self._years:
            self.year_cb.addItem(y["label"], y["id"])

        self.from_cb.clear()
        self.to_cb.clear()
        self.from_cb.addItem("-- From Class --", None)
        self.to_cb.addItem("-- To Class (promoted) --", None)
        for c in self._classes:
            self.from_cb.addItem(c["name"], c["id"])
            self.to_cb.addItem(c["name"], c["id"])

    def _build(self):
        lay = QVBoxLayout(self); lay.setContentsMargins(0, 16, 0, 0); lay.setSpacing(12)

        # ── Warning banner ────────────────────────────────────────────────────
        warn = QFrame()
        warn.setStyleSheet("QFrame{background:#FEF3C7;border:1px solid #FDE68A;border-radius:8px;}")
        wl = QHBoxLayout(warn); wl.setContentsMargins(14, 8, 14, 8)
        wl.addWidget(QLabel("⚠  This action modifies student class assignments and is irreversible. "
                            "Review all decisions carefully before executing.").also(
            lambda l: l.setStyleSheet("color:#92400E;font-size:12px;background:transparent;")))
        lay.addWidget(warn)

        # ── Selectors ─────────────────────────────────────────────────────────
        sel = QHBoxLayout(); sel.setSpacing(10)
        self.year_cb = QComboBox(); self.year_cb.setStyleSheet(COMBO)
        self.from_cb = QComboBox(); self.from_cb.setStyleSheet(COMBO); self.from_cb.setMinimumWidth(180)
        self.to_cb   = QComboBox(); self.to_cb.setStyleSheet(COMBO);   self.to_cb.setMinimumWidth(180)
        load_btn = QPushButton("Load Students"); load_btn.setStyleSheet(BTN_OUTLINE)
        load_btn.clicked.connect(self._load_students)
        for lbl, w in [("Academic Year:", self.year_cb), ("From Class:", self.from_cb),
                        ("Promote To:", self.to_cb)]:
            sel.addWidget(QLabel(lbl).also(lambda l: l.setStyleSheet("font-size:13px;font-weight:600;color:#374151;")))
            sel.addWidget(w)
        sel.addWidget(load_btn); sel.addStretch()
        lay.addLayout(sel)

        # ── Info bar ──────────────────────────────────────────────────────────
        self.info_lbl = QLabel("")
        self.info_lbl.setVisible(False)
        self.info_lbl.setStyleSheet(
            "background:#F0FDF4;color:#166534;border-radius:6px;padding:8px 12px;font-size:12px;"
        )
        lay.addWidget(self.info_lbl)

        # ── Table ─────────────────────────────────────────────────────────────
        self.table = QTableWidget()
        self.table.setColumnCount(len(self.COLS))
        self.table.setHorizontalHeaderLabels(self.COLS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setStyleSheet("""
            QTableWidget{border:1px solid #E5E7EB;border-radius:8px;
                gridline-color:#F3F4F6;font-size:12px;}
            QHeaderView::section{background:#F0FDF4;font-weight:600;
                padding:7px;border:none;border-bottom:1px solid #BBF7D0;color:#166534;}
            QTableWidget::item{padding:5px 7px;}
        """)
        lay.addWidget(self.table)

        # ── Bulk actions + execute ────────────────────────────────────────────
        bot = QHBoxLayout(); bot.setSpacing(8)
        mark_all_promote = QPushButton("Mark All → Promote"); mark_all_promote.setStyleSheet(BTN_OUTLINE)
        mark_all_promote.clicked.connect(lambda: self._set_all("promote"))
        mark_all_hold    = QPushButton("Mark All → Hold Back"); mark_all_hold.setStyleSheet(BTN_OUTLINE)
        mark_all_hold.clicked.connect(lambda: self._set_all("hold_back"))
        bot.addWidget(mark_all_promote); bot.addWidget(mark_all_hold); bot.addStretch()
        self.exec_btn = QPushButton("Execute Promotion"); self.exec_btn.setStyleSheet(BTN_PRIMARY)
        self.exec_btn.setEnabled(False); self.exec_btn.clicked.connect(self._execute)
        bot.addWidget(self.exec_btn)
        lay.addLayout(bot)

    def _load_students(self):
        year_id      = self.year_cb.currentData()
        from_class_id = self.from_cb.currentData()
        if not from_class_id:
            QMessageBox.warning(self, "Required", "Select the class to promote from."); return
        try:
            self._students = promotion_service.get_class_students_with_status(from_class_id, year_id)
        except (ServiceError, PolicyViolation) as e:
            QMessageBox.warning(self, "Error", str(e)); return

        already = sum(1 for s in self._students if s.get("promotion_id"))
        pending = len(self._students) - already
        self.info_lbl.setText(
            f"{len(self._students)} students — {already} already processed, {pending} pending"
        )
        self.info_lbl.setVisible(True)
        self._fill_table()
        self.exec_btn.setEnabled(pending > 0)

    def _fill_table(self):
        self._decision_cbs.clear()
        self._note_edits.clear()
        self.table.setRowCount(len(self._students))

        for r, s in enumerate(self._students):
            done = bool(s.get("promotion_id"))

            def cell(v, align=Qt.AlignmentFlag.AlignLeft, fg=None):
                it = QTableWidgetItem(str(v) if v is not None else "—")
                it.setFlags(Qt.ItemFlag.ItemIsEnabled)
                it.setTextAlignment(align | Qt.AlignmentFlag.AlignVCenter)
                if fg: it.setForeground(QColor(fg))
                return it
            ctr = Qt.AlignmentFlag.AlignCenter

            self.table.setItem(r, 0, cell(s["name"]))
            self.table.setItem(r, 1, cell(s.get("admission_no") or "—", ctr))
            avg = s.get("avg_pct")
            self.table.setItem(r, 2, cell(
                f"{avg:.1f}%" if avg is not None else "—", ctr,
                "#059669" if avg and avg >= 50 else ("#DC2626" if avg is not None else None)
            ))

            if done:
                action = s.get("promotion_action") or "—"
                self.table.setItem(r, 3, cell(action.replace("_", " ").title(), ctr,
                                              ACTION_COLORS.get(action)))
                self.table.setItem(r, 4, cell(""))
                self.table.setItem(r, 5, cell("✓ Done", ctr, "#059669"))
            else:
                cb = QComboBox(); cb.setStyleSheet(COMBO)
                for lbl, val in ACTION_OPTS:
                    cb.addItem(lbl, val)
                self.table.setCellWidget(r, 3, cb)
                self._decision_cbs[r] = cb

                ne = QLineEdit()
                ne.setStyleSheet("border:1px solid #D1D5DB;border-radius:4px;padding:4px 6px;font-size:12px;")
                ne.setPlaceholderText("Notes…")
                self.table.setCellWidget(r, 4, ne)
                self._note_edits[r] = ne

                self.table.setItem(r, 5, cell("Pending", ctr, "#6B7280"))

    def _set_all(self, action: str):
        for cb in self._decision_cbs.values():
            for i in range(cb.count()):
                if cb.itemData(i) == action:
                    cb.setCurrentIndex(i)
                    break

    def _execute(self):
        year_id       = self.year_cb.currentData()
        from_class_id = self.from_cb.currentData()
        to_class_id   = self.to_cb.currentData()

        entries = []
        for r, s in enumerate(self._students):
            if s.get("promotion_id"):
                continue
            cb = self._decision_cbs.get(r)
            ne = self._note_edits.get(r)
            if cb is None:
                continue
            action = cb.currentData()
            if action == "promote" and not to_class_id:
                QMessageBox.warning(self, "Required",
                                    "Select a target class for promoted students."); return
            entries.append({
                "student_id": s["id"],
                "action":     action,
                "notes":      ne.text().strip() if ne else "",
            })

        if not entries:
            QMessageBox.information(self, "Nothing to Do",
                                    "All students in this class have already been processed.")
            return

        promoted  = sum(1 for e in entries if e["action"] == "promote")
        held      = sum(1 for e in entries if e["action"] == "hold_back")
        graduated = sum(1 for e in entries if e["action"] == "graduate")
        msg = (f"You are about to process {len(entries)} students:\n\n"
               f"  • Promote: {promoted}\n"
               f"  • Hold Back: {held}\n"
               f"  • Graduate (deactivate): {graduated}\n\n"
               f"This cannot be undone. Continue?")
        if QMessageBox.question(
            self, "Confirm Promotion", msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) != QMessageBox.StandardButton.Yes:
            return

        try:
            counts = promotion_service.promote_batch(year_id, from_class_id, to_class_id, entries)
        except (ServiceError, PolicyViolation) as e:
            QMessageBox.warning(self, "Error", str(e)); return

        QMessageBox.information(
            self, "Promotion Complete",
            f"Done!\n\n"
            f"Promoted: {counts['promoted']}\n"
            f"Held Back: {counts['held_back']}\n"
            f"Graduated: {counts['graduated']}\n"
            f"Already done (skipped): {counts['skipped']}"
        )
        self._load_students()

    def refresh(self):
        self._load_meta()


class HistoryTab(QWidget):
    COLS = ["Student", "Adm No", "From Class", "To Class", "Decision", "Year", "Date", "By"]

    def __init__(self):
        super().__init__()
        self._build()
        self._load_meta()

    def _load_meta(self):
        years   = fetch_all("SELECT id, label FROM academic_years ORDER BY id DESC")
        classes = fetch_all("SELECT id, name FROM classes ORDER BY grade_level, name")
        self.year_cb.clear(); self.year_cb.addItem("All Years", None)
        for y in years:  self.year_cb.addItem(y["label"], y["id"])
        self.class_cb.clear(); self.class_cb.addItem("All Classes", None)
        for c in classes: self.class_cb.addItem(c["name"], c["id"])

    def _build(self):
        lay = QVBoxLayout(self); lay.setContentsMargins(0, 12, 0, 0); lay.setSpacing(10)

        bar = QHBoxLayout(); bar.setSpacing(8)
        self.year_cb  = QComboBox(); self.year_cb.setStyleSheet(COMBO)
        self.class_cb = QComboBox(); self.class_cb.setStyleSheet(COMBO)
        ref_btn = QPushButton("Load"); ref_btn.setStyleSheet(BTN_OUTLINE)
        ref_btn.clicked.connect(self._load)
        for lbl, w in [("Year:", self.year_cb), ("From Class:", self.class_cb)]:
            bar.addWidget(QLabel(lbl).also(lambda l: l.setStyleSheet("font-size:13px;font-weight:600;color:#374151;")))
            bar.addWidget(w)
        bar.addWidget(ref_btn); bar.addStretch()
        lay.addLayout(bar)

        self.table = QTableWidget()
        self.table.setColumnCount(len(self.COLS))
        self.table.setHorizontalHeaderLabels(self.COLS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setStyleSheet("""
            QTableWidget{border:1px solid #E5E7EB;border-radius:8px;font-size:12px;}
            QHeaderView::section{background:#F0FDF4;font-weight:600;
                padding:7px;border:none;border-bottom:1px solid #BBF7D0;color:#166534;}
            QTableWidget::item{padding:5px 7px;}
        """)
        lay.addWidget(self.table)

    def _load(self):
        try:
            rows = promotion_service.get_history(
                self.year_cb.currentData(), self.class_cb.currentData()
            )
        except (ServiceError, PolicyViolation) as e:
            QMessageBox.warning(self, "Error", str(e)); return
        self.table.setRowCount(len(rows))
        for r, h in enumerate(rows):
            action = h.get("action", "—")
            def cell(v, align=Qt.AlignmentFlag.AlignLeft, fg=None):
                it = QTableWidgetItem(str(v) if v is not None else "—")
                it.setFlags(Qt.ItemFlag.ItemIsEnabled)
                it.setTextAlignment(align | Qt.AlignmentFlag.AlignVCenter)
                if fg: it.setForeground(QColor(fg))
                return it
            ctr = Qt.AlignmentFlag.AlignCenter
            self.table.setItem(r, 0, cell(h["student_name"]))
            self.table.setItem(r, 1, cell(h.get("admission_no") or "—", ctr))
            self.table.setItem(r, 2, cell(h.get("from_class") or "—", ctr))
            self.table.setItem(r, 3, cell(h.get("to_class") or "—", ctr))
            self.table.setItem(r, 4, cell(
                action.replace("_", " ").title(), ctr, ACTION_COLORS.get(action)
            ))
            self.table.setItem(r, 5, cell(h.get("year_label") or "—", ctr))
            self.table.setItem(r, 6, cell((h.get("created_at") or "")[:10], ctr))
            self.table.setItem(r, 7, cell(h.get("promoted_by_name") or "—"))

    def refresh(self):
        self._load_meta()
        self._load()


class PromotionWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 16, 24, 16)
        lay.setSpacing(0)

        hdr = QLabel("Year-End Student Promotion")
        hdr.setStyleSheet("font-size:16px;font-weight:700;color:#1F2937;margin-bottom:8px;")
        lay.addWidget(hdr)

        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane{border:none;background:transparent;}
            QTabBar::tab{padding:10px 22px;font-size:13px;color:#6B7280;
                border:none;border-bottom:2px solid transparent;background:transparent;}
            QTabBar::tab:selected{color:#059669;border-bottom:2px solid #059669;font-weight:600;}
        """)
        self._promote_tab = PromoteTab()
        self._history_tab = HistoryTab()
        tabs.addTab(self._promote_tab, "Promote Students")
        tabs.addTab(self._history_tab, "History")
        tabs.currentChanged.connect(lambda i: [self._promote_tab, self._history_tab][i].refresh())
        lay.addWidget(tabs)

    def refresh(self):
        self._promote_tab.refresh()


# ── QLabel.also() helper ──────────────────────────────────────────────────────
from PyQt6.QtWidgets import QLabel as _QL
if not hasattr(_QL, "also"):
    def _also(self, fn): fn(self); return self
    _QL.also = _also
