"""Assignments tab — assign students to routes and cancel subscriptions."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QLineEdit, QMessageBox, QAbstractItemView, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from database.db import fetch_all, fetch_one
from services.transport_service import transport_service
from services.base import ServiceError, PolicyViolation
from auth.session import session

BTN_PRIMARY = """QPushButton{background:#0891B2;color:white;border:none;border-radius:7px;
    padding:8px 18px;font-size:13px;font-weight:600;}QPushButton:hover{background:#0E7490;}
    QPushButton:disabled{background:#CBD5E1;color:#94A3B8;}"""
BTN_OUTLINE = """QPushButton{background:white;color:#374151;border:1px solid #D1D5DB;
    border-radius:7px;padding:8px 14px;font-size:13px;}QPushButton:hover{background:#F9FAFB;}"""
BTN_DANGER = """QPushButton{background:#FEF2F2;color:#DC2626;border:1px solid #FECACA;
    border-radius:6px;padding:5px 12px;font-size:12px;}QPushButton:hover{background:#FEE2E2;}"""
COMBO = """QComboBox{border:1px solid #D1D5DB;border-radius:6px;padding:6px 10px;
    font-size:13px;background:white;min-width:160px;}"""
FIELD = "border:1px solid #D1D5DB;border-radius:6px;padding:7px 10px;font-size:13px;"

COLS = ["Student", "Adm No", "Class", "Route", "Term", "Year", "Status", ""]


class AssignmentsTab(QWidget):
    def __init__(self):
        super().__init__()
        self._subs: list[dict] = []
        self._routes: list[dict] = []
        self._students: list[dict] = []
        self._years: list[dict] = []
        self._build()
        self._load_meta()
        self.refresh()

    def _load_meta(self):
        try:
            self._routes = transport_service.get_routes()
        except (ServiceError, PolicyViolation):
            self._routes = []
        self._years = fetch_all(
            "SELECT id, label FROM academic_years ORDER BY id DESC"
        )
        self._students = fetch_all(
            "SELECT id, first_name||' '||last_name AS name, admission_no "
            "FROM students WHERE is_active=1 ORDER BY last_name, first_name"
        )

        # Populate route combo in assign panel
        self.route_cb.clear()
        self.route_cb.addItem("-- Select route --", None)
        for r in self._routes:
            self.route_cb.addItem(r["name"], r["id"])

        # Populate year combo in filter
        self.year_cb.clear()
        self.year_cb.addItem("All Years", None)
        for y in self._years:
            self.year_cb.addItem(y["label"], y["id"])

        # Populate assign year combo
        self.assign_year_cb.clear()
        for y in self._years:
            self.assign_year_cb.addItem(y["label"], y["id"])

        # Populate student filter combo
        self._fill_student_cb(self._students)

    def _fill_student_cb(self, students):
        self.student_cb.clear()
        self.student_cb.addItem("-- Select student --", None)
        for s in students:
            self.student_cb.addItem(f"{s['name']} ({s['admission_no']})", s["id"])

    def _build(self):
        lay = QVBoxLayout(self); lay.setContentsMargins(0, 12, 0, 0); lay.setSpacing(14)

        # ── Assign card (only for users with assign permission) ───────────────
        can_assign = session.can("transport.assign")
        if can_assign:
            card = QFrame()
            card.setStyleSheet("QFrame{background:white;border:1px solid #E5E7EB;border-radius:10px;}")
            cl = QVBoxLayout(card); cl.setContentsMargins(18, 14, 18, 14); cl.setSpacing(10)
            hdr = QLabel("Assign Student to Route")
            hdr.setStyleSheet("font-size:14px;font-weight:700;color:#1F2937;background:transparent;")
            cl.addWidget(hdr)

            r1 = QHBoxLayout(); r1.setSpacing(8)

            # Student search filter
            self.stu_search = QLineEdit(); self.stu_search.setPlaceholderText("Filter student…")
            self.stu_search.setStyleSheet(FIELD); self.stu_search.setMaximumWidth(160)
            self.stu_search.textChanged.connect(self._filter_students)
            self.student_cb = QComboBox(); self.student_cb.setStyleSheet(COMBO); self.student_cb.setMinimumWidth(240)
            self.route_cb   = QComboBox(); self.route_cb.setStyleSheet(COMBO)

            self.term_cb = QComboBox(); self.term_cb.setStyleSheet(COMBO)
            for t in [("Term 1", 1), ("Term 2", 2), ("Term 3", 3)]:
                self.term_cb.addItem(t[0], t[1])

            self.assign_year_cb = QComboBox(); self.assign_year_cb.setStyleSheet(COMBO)

            self.notes_e = QLineEdit(); self.notes_e.setPlaceholderText("Notes (optional)")
            self.notes_e.setStyleSheet(FIELD)

            assign_btn = QPushButton("Assign"); assign_btn.setStyleSheet(BTN_PRIMARY)
            assign_btn.clicked.connect(self._assign)

            for lbl, w in [("Student:", self.stu_search), ("→", self.student_cb),
                            ("Route:", self.route_cb), ("Term:", self.term_cb),
                            ("Year:", self.assign_year_cb)]:
                r1.addWidget(QLabel(lbl)); r1.addWidget(w)
            cl.addLayout(r1)
            r2 = QHBoxLayout(); r2.setSpacing(8)
            r2.addWidget(QLabel("Notes:")); r2.addWidget(self.notes_e, 1)
            r2.addWidget(assign_btn)
            cl.addLayout(r2)
            lay.addWidget(card)
        else:
            # Still need to initialise combos so _load_meta doesn't crash
            self.student_cb     = QComboBox()
            self.route_cb       = QComboBox()
            self.term_cb        = QComboBox()
            self.assign_year_cb = QComboBox()
            self.stu_search     = QLineEdit()

        # ── Filter row ────────────────────────────────────────────────────────
        fbar = QHBoxLayout(); fbar.setSpacing(8)
        self.year_cb = QComboBox(); self.year_cb.setStyleSheet(COMBO)
        self.year_cb.currentIndexChanged.connect(self.refresh)
        self.filter_term_cb = QComboBox(); self.filter_term_cb.setStyleSheet(COMBO)
        self.filter_term_cb.addItem("All Terms", None)
        for t in [("Term 1", 1), ("Term 2", 2), ("Term 3", 3)]:
            self.filter_term_cb.addItem(t[0], t[1])
        self.filter_term_cb.currentIndexChanged.connect(self.refresh)
        self.filter_route_cb = QComboBox(); self.filter_route_cb.setStyleSheet(COMBO)
        self.filter_route_cb.addItem("All Routes", None)
        ref_btn = QPushButton("Refresh"); ref_btn.setStyleSheet(BTN_OUTLINE)
        ref_btn.clicked.connect(self.refresh)

        fbar.addWidget(QLabel("Year:")); fbar.addWidget(self.year_cb)
        fbar.addWidget(QLabel("Term:")); fbar.addWidget(self.filter_term_cb)
        fbar.addWidget(QLabel("Route:")); fbar.addWidget(self.filter_route_cb)
        fbar.addWidget(ref_btn); fbar.addStretch()
        lay.addLayout(fbar)

        # ── Subscriptions table ───────────────────────────────────────────────
        self.table = QTableWidget()
        self.table.setColumnCount(len(COLS))
        self.table.setHorizontalHeaderLabels(COLS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setStyleSheet("""
            QTableWidget{border:1px solid #E5E7EB;border-radius:8px;
                gridline-color:#F3F4F6;font-size:12px;}
            QHeaderView::section{background:#E0F2FE;font-weight:600;
                padding:7px;border:none;border-bottom:1px solid #BAE6FD;color:#0369A1;}
            QTableWidget::item{padding:5px 7px;}
        """)
        lay.addWidget(self.table)

    def _filter_students(self, text: str):
        text = text.lower()
        filtered = [s for s in self._students
                    if text in (s["name"] or "").lower()
                    or text in (s["admission_no"] or "").lower()]
        self._fill_student_cb(filtered)

    def _assign(self):
        student_id       = self.student_cb.currentData()
        route_id         = self.route_cb.currentData()
        term             = self.term_cb.currentData()
        academic_year_id = self.assign_year_cb.currentData()
        if not all([student_id, route_id, term, academic_year_id]):
            QMessageBox.warning(self, "Required", "Select student, route, term and year."); return
        try:
            transport_service.assign_student(student_id, route_id, academic_year_id, term,
                                             self.notes_e.text().strip())
        except (ServiceError, PolicyViolation) as e:
            QMessageBox.warning(self, "Cannot Assign", str(e)); return
        self.notes_e.clear()
        self.refresh()

    def _cancel(self, sub_id: int):
        if QMessageBox.question(
            self, "Cancel Subscription", "Remove this student from the route?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) != QMessageBox.StandardButton.Yes:
            return
        try:
            transport_service.cancel_subscription(sub_id)
        except (ServiceError, PolicyViolation) as e:
            QMessageBox.warning(self, "Error", str(e)); return
        self.refresh()

    def refresh(self):
        # Rebuild filter route combo if needed
        if self.filter_route_cb.count() <= 1:
            self.filter_route_cb.clear()
            self.filter_route_cb.addItem("All Routes", None)
            for r in self._routes:
                self.filter_route_cb.addItem(r["name"], r["id"])

        year_id = self.year_cb.currentData()
        term    = self.filter_term_cb.currentData()
        try:
            subs = transport_service.get_all_subscriptions(year_id, term)
        except (ServiceError, PolicyViolation) as e:
            QMessageBox.warning(self, "Error", str(e)); return

        # Apply route filter
        route_id = self.filter_route_cb.currentData()
        if route_id:
            subs = [s for s in subs if s["route_id"] == route_id]
        self._subs = subs

        can_assign = session.can("transport.assign")
        self.table.setRowCount(len(subs))
        for r, s in enumerate(subs):
            def cell(v, align=Qt.AlignmentFlag.AlignLeft, fg=None):
                it = QTableWidgetItem(str(v) if v is not None else "—")
                it.setFlags(Qt.ItemFlag.ItemIsEnabled)
                it.setTextAlignment(align | Qt.AlignmentFlag.AlignVCenter)
                if fg: it.setForeground(QColor(fg))
                return it
            ctr = Qt.AlignmentFlag.AlignCenter
            self.table.setItem(r, 0, cell(s["student_name"]))
            self.table.setItem(r, 1, cell(s.get("admission_no") or "—", ctr))
            self.table.setItem(r, 2, cell(s.get("class_name") or "—", ctr))
            self.table.setItem(r, 3, cell(s["route_name"]))
            self.table.setItem(r, 4, cell(f"T{s['term']}", ctr))
            self.table.setItem(r, 5, cell(s.get("year_label") or "—", ctr))
            st = s["status"]
            self.table.setItem(r, 6, cell(
                st.title(), ctr, "#059669" if st == "active" else "#9CA3AF"
            ))
            if can_assign and st == "active":
                btn = QPushButton("Remove"); btn.setStyleSheet(BTN_DANGER)
                btn.clicked.connect(lambda _, sid=s["id"]: self._cancel(sid))
                self.table.setCellWidget(r, 7, btn)
            else:
                self.table.setItem(r, 7, cell(""))
