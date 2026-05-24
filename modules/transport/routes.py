"""Routes tab — manage transport routes and view per-route passenger list."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QLineEdit, QMessageBox, QAbstractItemView, QDialog,
    QFormLayout, QDoubleSpinBox, QDialogButtonBox, QSplitter,
    QTextEdit, QFrame
)
from PyQt6.QtCore import Qt
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
    border-radius:7px;padding:8px 14px;font-size:12px;}QPushButton:hover{background:#FEE2E2;}"""
FIELD = "border:1px solid #D1D5DB;border-radius:6px;padding:7px 10px;font-size:13px;"
COMBO = """QComboBox{border:1px solid #D1D5DB;border-radius:6px;padding:6px 10px;
    font-size:13px;background:white;min-width:130px;}"""


class RouteDialog(QDialog):
    def __init__(self, parent, route: dict | None = None):
        super().__init__(parent)
        self.setWindowTitle("Add Route" if route is None else "Edit Route")
        self.setMinimumWidth(440)
        self._route = route
        self._build()
        if route:
            self._fill(route)

    def _build(self):
        lay = QVBoxLayout(self)
        form = QFormLayout(); form.setLabelAlignment(Qt.AlignmentFlag.AlignRight); form.setSpacing(10)

        def f(ph=""):
            e = QLineEdit(); e.setPlaceholderText(ph); e.setStyleSheet(FIELD); return e

        def fare_spin():
            s = QDoubleSpinBox(); s.setRange(0, 9_999_999); s.setDecimals(0)
            s.setPrefix("TZS "); s.setSingleStep(1000)
            s.setStyleSheet("border:1px solid #D1D5DB;border-radius:5px;padding:5px;font-size:13px;")
            return s

        self.name_e    = f("e.g. Kariakoo – Mikocheni")
        self.desc_e    = QTextEdit(); self.desc_e.setMaximumHeight(60)
        self.desc_e.setStyleSheet("border:1px solid #D1D5DB;border-radius:5px;padding:5px;font-size:12px;")
        self.vehicle_e = f("Bus reg. no.")
        self.driver_e  = f("Driver full name")
        self.phone_e   = f("+255…")
        self.fare1_sb  = fare_spin()
        self.fare2_sb  = fare_spin()
        self.fare3_sb  = fare_spin()

        for lbl, w in [("Route Name *", self.name_e), ("Pickup Points", self.desc_e),
                        ("Vehicle No.", self.vehicle_e), ("Driver Name", self.driver_e),
                        ("Driver Phone", self.phone_e),
                        ("Fare Term 1", self.fare1_sb), ("Fare Term 2", self.fare2_sb),
                        ("Fare Term 3", self.fare3_sb)]:
            form.addRow(QLabel(lbl), w)
        lay.addLayout(form)

        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self._save); bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def _fill(self, r: dict):
        self.name_e.setText(r.get("name") or "")
        self.desc_e.setPlainText(r.get("description") or "")
        self.vehicle_e.setText(r.get("vehicle_no") or "")
        self.driver_e.setText(r.get("driver_name") or "")
        self.phone_e.setText(r.get("driver_phone") or "")
        self.fare1_sb.setValue(r.get("fare_term1") or 0)
        self.fare2_sb.setValue(r.get("fare_term2") or 0)
        self.fare3_sb.setValue(r.get("fare_term3") or 0)

    def _save(self):
        if not self.name_e.text().strip():
            QMessageBox.warning(self, "Required", "Route name is required."); return
        data = {
            "name":         self.name_e.text().strip(),
            "description":  self.desc_e.toPlainText().strip(),
            "vehicle_no":   self.vehicle_e.text().strip(),
            "driver_name":  self.driver_e.text().strip(),
            "driver_phone": self.phone_e.text().strip(),
            "fare_term1":   self.fare1_sb.value(),
            "fare_term2":   self.fare2_sb.value(),
            "fare_term3":   self.fare3_sb.value(),
        }
        try:
            if self._route:
                transport_service.update_route(self._route["id"], data)
            else:
                transport_service.add_route(data)
            self.accept()
        except (ServiceError, PolicyViolation) as e:
            QMessageBox.warning(self, "Error", str(e))


class RoutesTab(QWidget):
    ROUTE_COLS = ["Route Name", "Vehicle", "Driver", "Phone", "T1 Fare", "T2 Fare", "T3 Fare", "Students"]
    PASS_COLS  = ["Name", "Adm No", "Class", "Year", "Term", "Fare (TZS)"]

    def __init__(self):
        super().__init__()
        self._routes: list[dict] = []
        self._build()
        self.refresh()

    def _build(self):
        lay = QVBoxLayout(self); lay.setContentsMargins(0, 12, 0, 0); lay.setSpacing(10)

        # ── Toolbar ──────────────────────────────────────────────────────────
        bar = QHBoxLayout(); bar.setSpacing(8)
        bar.addStretch()
        can_manage = session.can("transport.manage")
        if can_manage:
            add_btn = QPushButton("+ Add Route"); add_btn.setStyleSheet(BTN_PRIMARY)
            add_btn.clicked.connect(self._add); bar.addWidget(add_btn)
        lay.addLayout(bar)

        # ── Splitter: routes left, passenger list right ───────────────────────
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Routes table
        left = QWidget()
        ll = QVBoxLayout(left); ll.setContentsMargins(0, 0, 4, 0); ll.setSpacing(6)
        routes_lbl = QLabel("Routes")
        routes_lbl.setStyleSheet("font-size:13px;font-weight:700;color:#374151;")
        ll.addWidget(routes_lbl)
        self.route_table = QTableWidget()
        self.route_table.setColumnCount(len(self.ROUTE_COLS))
        self.route_table.setHorizontalHeaderLabels(self.ROUTE_COLS)
        self.route_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.route_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.route_table.setAlternatingRowColors(True)
        self.route_table.verticalHeader().setVisible(False)
        self.route_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.route_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.route_table.setStyleSheet("""
            QTableWidget{border:1px solid #E5E7EB;border-radius:8px;
                gridline-color:#F3F4F6;font-size:12px;}
            QHeaderView::section{background:#E0F2FE;font-weight:600;
                padding:7px;border:none;border-bottom:1px solid #BAE6FD;color:#0369A1;}
            QTableWidget::item{padding:5px 6px;}
        """)
        self.route_table.itemSelectionChanged.connect(self._on_route_selected)
        ll.addWidget(self.route_table)

        if can_manage:
            act = QHBoxLayout(); act.addStretch()
            self.edit_btn = QPushButton("Edit"); self.edit_btn.setStyleSheet(BTN_OUTLINE)
            self.edit_btn.setEnabled(False); self.edit_btn.clicked.connect(self._edit)
            self.deact_btn = QPushButton("Deactivate"); self.deact_btn.setStyleSheet(BTN_DANGER)
            self.deact_btn.setEnabled(False); self.deact_btn.clicked.connect(self._deactivate)
            act.addWidget(self.edit_btn); act.addWidget(self.deact_btn)
            ll.addLayout(act)

        splitter.addWidget(left)

        # Passenger list
        right = QWidget()
        rl = QVBoxLayout(right); rl.setContentsMargins(4, 0, 0, 0); rl.setSpacing(6)
        self.pass_lbl = QLabel("Select a route to see passengers")
        self.pass_lbl.setStyleSheet("font-size:13px;font-weight:700;color:#374151;")
        rl.addWidget(self.pass_lbl)
        self.pass_table = QTableWidget()
        self.pass_table.setColumnCount(len(self.PASS_COLS))
        self.pass_table.setHorizontalHeaderLabels(self.PASS_COLS)
        self.pass_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.pass_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.pass_table.setAlternatingRowColors(True)
        self.pass_table.verticalHeader().setVisible(False)
        self.pass_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.pass_table.setStyleSheet("""
            QTableWidget{border:1px solid #E5E7EB;border-radius:8px;
                gridline-color:#F3F4F6;font-size:12px;}
            QHeaderView::section{background:#E0F2FE;font-weight:600;
                padding:7px;border:none;border-bottom:1px solid #BAE6FD;color:#0369A1;}
            QTableWidget::item{padding:5px 6px;}
        """)
        rl.addWidget(self.pass_table)
        splitter.addWidget(right)
        splitter.setSizes([480, 360])
        lay.addWidget(splitter)

    def _fill_routes(self, routes: list[dict]):
        self.route_table.setRowCount(len(routes))
        for r, rt in enumerate(routes):
            def cell(v, align=Qt.AlignmentFlag.AlignLeft):
                it = QTableWidgetItem(str(v) if v is not None else "—")
                it.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                it.setTextAlignment(align | Qt.AlignmentFlag.AlignVCenter)
                return it
            ctr = Qt.AlignmentFlag.AlignCenter
            self.route_table.setItem(r, 0, cell(rt["name"]))
            self.route_table.setItem(r, 1, cell(rt.get("vehicle_no") or "—", ctr))
            self.route_table.setItem(r, 2, cell(rt.get("driver_name") or "—"))
            self.route_table.setItem(r, 3, cell(rt.get("driver_phone") or "—", ctr))
            self.route_table.setItem(r, 4, cell(f"{rt.get('fare_term1',0):,.0f}", ctr))
            self.route_table.setItem(r, 5, cell(f"{rt.get('fare_term2',0):,.0f}", ctr))
            self.route_table.setItem(r, 6, cell(f"{rt.get('fare_term3',0):,.0f}", ctr))
            self.route_table.setItem(r, 7, cell(rt.get("student_count", 0), ctr))

    def _on_route_selected(self):
        sel = self.route_table.selectedItems()
        if session.can("transport.manage"):
            self.edit_btn.setEnabled(bool(sel))
            self.deact_btn.setEnabled(bool(sel))
        if not sel:
            self.pass_lbl.setText("Select a route to see passengers")
            self.pass_table.setRowCount(0)
            return
        r = self.route_table.currentRow()
        if r >= len(self._routes): return
        rt = self._routes[r]
        self.pass_lbl.setText(f"Passengers — {rt['name']}")
        try:
            students = transport_service.get_route_students(rt["id"])
        except (ServiceError, PolicyViolation):
            students = []
        self.pass_table.setRowCount(len(students))
        for i, s in enumerate(students):
            def cell(v, align=Qt.AlignmentFlag.AlignLeft):
                it = QTableWidgetItem(str(v) if v is not None else "—")
                it.setFlags(Qt.ItemFlag.ItemIsEnabled)
                it.setTextAlignment(align | Qt.AlignmentFlag.AlignVCenter)
                return it
            ctr = Qt.AlignmentFlag.AlignCenter
            self.pass_table.setItem(i, 0, cell(s["student_name"]))
            self.pass_table.setItem(i, 1, cell(s.get("admission_no") or "—", ctr))
            self.pass_table.setItem(i, 2, cell(s.get("class_name") or "—", ctr))
            self.pass_table.setItem(i, 3, cell(s.get("year_label") or "—", ctr))
            self.pass_table.setItem(i, 4, cell(f"T{s['term']}", ctr))
            # Fare based on term
            fare_key = f"fare_term{s['term']}"
            fare = rt.get(fare_key, 0)
            self.pass_table.setItem(i, 5, cell(f"{fare:,.0f}", ctr))

    def _selected_route(self):
        r = self.route_table.currentRow()
        return self._routes[r] if 0 <= r < len(self._routes) else None

    def _add(self):
        dlg = RouteDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def _edit(self):
        rt = self._selected_route()
        if not rt: return
        dlg = RouteDialog(self, rt)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def _deactivate(self):
        rt = self._selected_route()
        if not rt: return
        if rt.get("student_count", 0) > 0:
            QMessageBox.warning(self, "Cannot Deactivate",
                                "Remove all student subscriptions from this route first.")
            return
        if QMessageBox.question(
            self, "Deactivate Route", f"Deactivate route '{rt['name']}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) != QMessageBox.StandardButton.Yes:
            return
        try:
            transport_service.deactivate_route(rt["id"])
        except (ServiceError, PolicyViolation) as e:
            QMessageBox.warning(self, "Error", str(e)); return
        self.refresh()

    def refresh(self):
        try:
            self._routes = transport_service.get_routes()
        except (ServiceError, PolicyViolation) as e:
            QMessageBox.warning(self, "Error", str(e)); return
        self._fill_routes(self._routes)
        self.pass_table.setRowCount(0)
        self.pass_lbl.setText("Select a route to see passengers")

