"""Dashboard — role-aware summary shown on startup."""

from pathlib import Path
from datetime import date

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QGridLayout, QSizePolicy, QScrollArea
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QImage, QPixmap

from database.db import fetch_one, fetch_all, get_config
from auth.session import session

_ICON_DIR = Path(__file__).parent.parent / "assets" / "Icons" / "PNG"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _hex_to_rgba(hex_color: str, alpha_0_255: int) -> str:
    """Convert #RRGGBB + integer alpha (0–255) to Qt rgba() string."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha_0_255})"


def _tinted_icon(n: int, hex_color: str, size: int = 20) -> QPixmap:
    """
    Load a white-background PNG icon and recolor it to hex_color.
    White pixels become transparent; black lines become the target color.
    """
    src = QPixmap(str(_ICON_DIR / f"Icon {n}.png"))
    if src.isNull():
        return QPixmap()
    src = src.scaled(size, size,
                     Qt.AspectRatioMode.KeepAspectRatio,
                     Qt.TransformationMode.SmoothTransformation)
    img = src.toImage().convertToFormat(QImage.Format.Format_ARGB32)
    c = QColor(hex_color)
    r, g, b = c.red(), c.green(), c.blue()
    for y in range(img.height()):
        for x in range(img.width()):
            px = QColor(img.pixel(x, y))
            lum = (px.red() + px.green() + px.blue()) // 3
            img.setPixelColor(x, y, QColor(r, g, b, 255 - lum))
    return QPixmap.fromImage(img)


def _n(row, key="n"):
    return row[key] if row else 0


# ── Reusable widgets ──────────────────────────────────────────────────────────

class StatCard(QFrame):
    """Clean KPI card: large colored number + title + icon in top-right corner."""

    def __init__(self, title: str, value, color: str = "#2563EB",
                 icon_num: int = 0, subtitle: str = ""):
        super().__init__()
        self._color = color
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(100)
        self.setStyleSheet(
            "QFrame { background: white; border-radius: 10px; border: 1px solid #E5E7EB; }"
        )

        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(4)

        # Top row: title left, icon right
        top = QHBoxLayout(); top.setSpacing(8)
        t_lbl = QLabel(title)
        t_lbl.setStyleSheet("font-size:12px;color:#6B7280;font-weight:500;background:transparent;")
        top.addWidget(t_lbl, 1)

        if icon_num:
            ico = QLabel()
            ico.setFixedSize(32, 32)
            ico.setAlignment(Qt.AlignmentFlag.AlignCenter)
            ico.setStyleSheet(
                f"background:{_hex_to_rgba(color, 28)};"  # ~11% opacity
                f"border-radius:8px;"
            )
            pix = _tinted_icon(icon_num, color, 20)
            ico.setPixmap(pix)
            top.addWidget(ico)

        lay.addLayout(top)

        # Big value
        self.value_lbl = QLabel(str(value))
        self.value_lbl.setStyleSheet(
            f"font-size:26px;font-weight:700;color:{color};background:transparent;"
        )
        lay.addWidget(self.value_lbl)

        if subtitle:
            self.sub_lbl = QLabel(subtitle)
            self.sub_lbl.setStyleSheet("font-size:11px;color:#9CA3AF;background:transparent;")
            lay.addWidget(self.sub_lbl)
        else:
            self.sub_lbl = None

    def set_value(self, v, subtitle: str = ""):
        self.value_lbl.setText(str(v))
        if self.sub_lbl and subtitle:
            self.sub_lbl.setText(subtitle)


class SectionLabel(QLabel):
    def __init__(self, text: str):
        super().__init__(text)
        self.setStyleSheet(
            "font-size:12px;font-weight:700;color:#6B7280;"
            "letter-spacing:0.5px;margin-top:8px;background:transparent;"
        )


class RecentList(QFrame):
    """Compact list of recent activity rows."""

    def __init__(self, rows: list[tuple], empty_text: str = "Nothing to show yet."):
        super().__init__()
        self.setStyleSheet(
            "QFrame { background: white; border: 1px solid #E5E7EB; border-radius: 10px; }"
        )
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(0)

        if not rows:
            lbl = QLabel(empty_text)
            lbl.setStyleSheet("font-size:12px;color:#9CA3AF;background:transparent;")
            lay.addWidget(lbl)
            return

        for i, (left, right, colour) in enumerate(rows):
            if i > 0:
                sep = QFrame()
                sep.setFixedHeight(1)
                sep.setStyleSheet("background:#F3F4F6;border:none;")
                lay.addWidget(sep)

            row_lay = QHBoxLayout()
            row_lay.setContentsMargins(0, 8, 0, 8)
            row_lay.setSpacing(10)

            dot = QLabel("●")
            dot.setFixedWidth(12)
            dot.setStyleSheet(f"color:{colour};font-size:8px;background:transparent;")

            l = QLabel(left)
            l.setStyleSheet("font-size:12px;color:#374151;background:transparent;")
            l.setWordWrap(True)

            r_lbl = QLabel(right)
            r_lbl.setStyleSheet(
                f"font-size:11px;color:{colour};font-weight:600;background:transparent;"
            )
            r_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            r_lbl.setMinimumWidth(90)

            row_lay.addWidget(dot)
            row_lay.addWidget(l, 1)
            row_lay.addWidget(r_lbl)
            lay.addLayout(row_lay)


def _grid(cards: list, cols: int = 3) -> QGridLayout:
    g = QGridLayout(); g.setSpacing(12)
    for i, c in enumerate(cards):
        g.addWidget(c, i // cols, i % cols)
    return g


def _section(lay: QVBoxLayout, title: str, cards: list, cols: int = 3):
    lay.addWidget(SectionLabel(title.upper()))
    lay.addLayout(_grid(cards, cols))


# ═══════════════════════════════════════════════════════════════════════════════
# Role-specific dashboard panels
# ═══════════════════════════════════════════════════════════════════════════════

class _FullDashboard(QWidget):
    """Admin / Head Teacher — complete school overview."""

    def __init__(self):
        super().__init__()
        self.setStyleSheet("background:transparent;")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 4, 0, 16)
        lay.setSpacing(8)

        _section(lay, "Students & Staff", [
            StatCard("Active Students",   "—", "#2563EB", 10),
            StatCard("Teachers & Staff",  "—", "#059669", 41),
            StatCard("Classes",           "—", "#7C3AED", 38),
        ])
        self.c_students, self.c_teachers, self.c_classes = self._last3(lay)

        _section(lay, "Attendance Today", [
            StatCard("Present",        "—", "#059669",  2),
            StatCard("Absent",         "—", "#DC2626",  2),
            StatCard("Late / Excused", "—", "#D97706",  2),
        ])
        self.c_present, self.c_absent, self.c_late = self._last3(lay)

        _section(lay, "Finance & Operations", [
            StatCard("Fees Collected (Month)", "—", "#059669",  3),
            StatCard("Unpaid Bills",           "—", "#DC2626",  3),
            StatCard("Welfare Students",       "—", "#9333EA",  5),
            StatCard("Low Stock Items",        "—", "#B45309",  6),
            StatCard("Expenses (Month)",       "—", "#EA580C",  7),
            StatCard("Grades Pending Approval","—", "#0891B2",  4),
        ], cols=3)
        cards = self._last_n(lay, 6)
        self.c_fees, self.c_unpaid, self.c_welfare, \
            self.c_stock, self.c_expenses, self.c_grades = cards

        lay.addWidget(SectionLabel("RECENT PAYMENTS"))
        self.recent = RecentList([])
        lay.addWidget(self.recent)
        lay.addStretch()

    @staticmethod
    def _last3(lay):
        grid = lay.itemAt(lay.count() - 1).layout()
        return grid.itemAtPosition(0,0).widget(), \
               grid.itemAtPosition(0,1).widget(), \
               grid.itemAtPosition(0,2).widget()

    @staticmethod
    def _last_n(lay, n):
        grid = lay.itemAt(lay.count() - 1).layout()
        result = []
        cols = 3
        for i in range(n):
            result.append(grid.itemAtPosition(i // cols, i % cols).widget())
        return result

    def refresh(self):
        today = date.today().isoformat()
        self.c_students.set_value(_n(fetch_one(
            "SELECT COUNT(*) AS n FROM students WHERE is_active=1")))
        self.c_teachers.set_value(_n(fetch_one(
            "SELECT COUNT(*) AS n FROM teachers WHERE is_active=1")))
        self.c_classes.set_value(_n(fetch_one(
            "SELECT COUNT(*) AS n FROM classes")))
        self.c_present.set_value(_n(fetch_one(
            "SELECT COUNT(*) AS n FROM attendance WHERE date=? AND status='Present'", (today,))))
        self.c_absent.set_value(_n(fetch_one(
            "SELECT COUNT(*) AS n FROM attendance WHERE date=? AND status='Absent'", (today,))))
        self.c_late.set_value(_n(fetch_one(
            "SELECT COUNT(*) AS n FROM attendance "
            "WHERE date=? AND status IN ('Late','Excused')", (today,))))
        r = fetch_one("SELECT COALESCE(SUM(amount_paid),0) AS t FROM fee_payments "
                      "WHERE strftime('%Y-%m',payment_date)=strftime('%Y-%m','now')")
        self.c_fees.set_value(f"TZS {_n(r,'t'):,.0f}")
        self.c_unpaid.set_value(_n(fetch_one(
            "SELECT COUNT(*) AS n FROM student_bills WHERE status IN ('unpaid','partial')")))
        self.c_welfare.set_value(_n(fetch_one(
            "SELECT COUNT(*) AS n FROM welfare_records")))
        self.c_stock.set_value(_n(fetch_one(
            "SELECT COUNT(*) AS n FROM inventory_items "
            "WHERE is_active=1 AND stock_qty<=reorder_qty")))
        r = fetch_one("SELECT COALESCE(SUM(amount),0) AS t FROM expenses "
                      "WHERE strftime('%Y-%m',expense_date)=strftime('%Y-%m','now')")
        self.c_expenses.set_value(f"TZS {_n(r,'t'):,.0f}")
        self.c_grades.set_value(_n(fetch_one(
            "SELECT COUNT(*) AS n FROM grades WHERE status='submitted'")))

        payments = fetch_all("""
            SELECT s.first_name||' '||s.last_name AS student,
                   fp.amount_paid, fp.payment_method, fp.payment_date
            FROM fee_payments fp JOIN students s ON s.id=fp.student_id
            ORDER BY fp.id DESC LIMIT 7
        """)
        rows = [(f"{p['student']}  ·  {p['payment_method']}  ·  {p['payment_date']}",
                 f"TZS {p['amount_paid']:,.0f}", "#059669") for p in payments]
        self._swap_list("recent", rows, "No payments recorded yet.")

    def _swap_list(self, attr: str, rows: list, empty: str):
        lay = self.layout()
        old = getattr(self, attr)
        new = RecentList(rows, empty)
        lay.replaceWidget(old, new)
        old.deleteLater()
        setattr(self, attr, new)


class _AccountantDashboard(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("background:transparent;")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 4, 0, 16); lay.setSpacing(8)

        _section(lay, "Collections", [
            StatCard("Collected Today",      "—", "#059669", 3),
            StatCard("Collected This Month", "—", "#2563EB", 3),
            StatCard("Expenses This Month",  "—", "#EA580C", 7),
        ])
        self.c_today, self.c_month, self.c_expense = _FullDashboard._last3(lay)

        _section(lay, "Bill Status", [
            StatCard("Unpaid",  "—", "#DC2626", 3),
            StatCard("Partial", "—", "#D97706", 3),
            StatCard("Waived",  "—", "#9333EA", 5),
        ])
        self.c_unpaid, self.c_partial, self.c_waived = _FullDashboard._last3(lay)

        lay.addWidget(SectionLabel("RECENT PAYMENTS"))
        self.recent = RecentList([])
        lay.addWidget(self.recent)
        lay.addStretch()

    def refresh(self):
        today = date.today().isoformat()
        r = fetch_one("SELECT COALESCE(SUM(amount_paid),0) AS t "
                      "FROM fee_payments WHERE payment_date=?", (today,))
        self.c_today.set_value(f"TZS {_n(r,'t'):,.0f}")
        r = fetch_one("SELECT COALESCE(SUM(amount_paid),0) AS t FROM fee_payments "
                      "WHERE strftime('%Y-%m',payment_date)=strftime('%Y-%m','now')")
        self.c_month.set_value(f"TZS {_n(r,'t'):,.0f}")
        r = fetch_one("SELECT COALESCE(SUM(amount),0) AS t FROM expenses "
                      "WHERE strftime('%Y-%m',expense_date)=strftime('%Y-%m','now')")
        self.c_expense.set_value(f"TZS {_n(r,'t'):,.0f}")
        self.c_unpaid.set_value(_n(fetch_one(
            "SELECT COUNT(*) AS n FROM student_bills WHERE status='unpaid'")))
        self.c_partial.set_value(_n(fetch_one(
            "SELECT COUNT(*) AS n FROM student_bills WHERE status='partial'")))
        self.c_waived.set_value(_n(fetch_one(
            "SELECT COUNT(*) AS n FROM student_bills WHERE status='waived'")))
        rows_db = fetch_all("""
            SELECT s.first_name||' '||s.last_name AS student,
                   fp.amount_paid, fp.payment_method, fp.payment_date
            FROM fee_payments fp JOIN students s ON s.id=fp.student_id
            ORDER BY fp.id DESC LIMIT 8
        """)
        rows = [(f"{p['student']}  ·  {p['payment_method']}  ·  {p['payment_date']}",
                 f"TZS {p['amount_paid']:,.0f}", "#059669") for p in rows_db]
        old = self.recent
        self.recent = RecentList(rows, "No payments yet.")
        self.layout().replaceWidget(old, self.recent); old.deleteLater()


class _AcademicDashboard(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("background:transparent;")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 4, 0, 16); lay.setSpacing(8)

        _section(lay, "School Overview", [
            StatCard("Active Students",          "—", "#2563EB", 10),
            StatCard("Classes",                  "—", "#7C3AED", 38),
            StatCard("Open Exams",               "—", "#0891B2",  4),
        ])
        self.c_students, self.c_classes, self.c_exams = _FullDashboard._last3(lay)

        _section(lay, "Attendance Today", [
            StatCard("Present",                      "—", "#059669",  2),
            StatCard("Absent",                       "—", "#DC2626",  2),
            StatCard("Grade Batches Pending Approval","—", "#D97706",  4),
        ])
        self.c_present, self.c_absent, self.c_pending = _FullDashboard._last3(lay)

        lay.addWidget(SectionLabel("GRADE BATCHES AWAITING APPROVAL"))
        self.pending_list = RecentList([])
        lay.addWidget(self.pending_list)
        lay.addStretch()

    def refresh(self):
        today = date.today().isoformat()
        self.c_students.set_value(_n(fetch_one(
            "SELECT COUNT(*) AS n FROM students WHERE is_active=1")))
        self.c_classes.set_value(_n(fetch_one("SELECT COUNT(*) AS n FROM classes")))
        self.c_exams.set_value(_n(fetch_one(
            "SELECT COUNT(*) AS n FROM exams WHERE status='open'")))
        self.c_present.set_value(_n(fetch_one(
            "SELECT COUNT(*) AS n FROM attendance WHERE date=? AND status='Present'", (today,))))
        self.c_absent.set_value(_n(fetch_one(
            "SELECT COUNT(*) AS n FROM attendance WHERE date=? AND status='Absent'", (today,))))
        pc = fetch_one("""
            SELECT COUNT(DISTINCT (g.exam_id||'-'||st.class_id||'-'||g.subject_id)) AS n
            FROM grades g JOIN students st ON st.id=g.student_id WHERE g.status='submitted'
        """)
        self.c_pending.set_value(_n(pc))
        batches = fetch_all("""
            SELECT e.name AS exam_name, c.name AS class_name, s.name AS subj_name,
                   COUNT(g.id) AS cnt
            FROM grades g
            JOIN exams e ON e.id=g.exam_id
            JOIN students st ON st.id=g.student_id
            JOIN classes c ON c.id=st.class_id
            JOIN subjects s ON s.id=g.subject_id
            WHERE g.status='submitted'
            GROUP BY g.exam_id, c.id, g.subject_id
            ORDER BY e.id DESC LIMIT 8
        """)
        rows = [(f"{b['exam_name']}  ·  {b['class_name']} / {b['subj_name']}",
                 f"{b['cnt']} grades", "#D97706") for b in batches]
        old = self.pending_list
        self.pending_list = RecentList(rows, "No pending grade submissions.")
        self.layout().replaceWidget(old, self.pending_list); old.deleteLater()


class _WelfareDashboard(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("background:transparent;")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 4, 0, 16); lay.setSpacing(8)

        _section(lay, "Welfare Records", [
            StatCard("Total Records",       "—", "#9333EA", 5),
            StatCard("Verified",            "—", "#059669", 5),
            StatCard("Awaiting Verification","—","#D97706", 5),
            StatCard("Orphan Students",     "—", "#7C3AED", 10),
            StatCard("Half-Orphan",         "—", "#6B7280", 10),
            StatCard("Full Fee Exemptions", "—", "#0891B2",  5),
        ])
        cards = _FullDashboard._last_n(lay, 6)
        self.c_total, self.c_verified, self.c_pending, \
            self.c_orphan, self.c_half, self.c_exempt = cards

        lay.addWidget(SectionLabel("RECENT REGISTRATIONS"))
        self.recent = RecentList([])
        lay.addWidget(self.recent)
        lay.addStretch()

    def refresh(self):
        self.c_total.set_value(_n(fetch_one("SELECT COUNT(*) AS n FROM welfare_records")))
        self.c_verified.set_value(_n(fetch_one(
            "SELECT COUNT(*) AS n FROM welfare_records WHERE verified=1")))
        self.c_pending.set_value(_n(fetch_one(
            "SELECT COUNT(*) AS n FROM welfare_records WHERE verified=0")))
        self.c_orphan.set_value(_n(fetch_one(
            "SELECT COUNT(*) AS n FROM welfare_records WHERE category='orphan'")))
        self.c_half.set_value(_n(fetch_one(
            "SELECT COUNT(*) AS n FROM welfare_records WHERE category='half_orphan'")))
        self.c_exempt.set_value(_n(fetch_one(
            "SELECT COUNT(*) AS n FROM welfare_records WHERE support_type='full_fees'")))
        recent = fetch_all("""
            SELECT s.first_name||' '||s.last_name AS student, wr.category, wr.verified
            FROM welfare_records wr JOIN students s ON s.id=wr.student_id
            ORDER BY wr.id DESC LIMIT 8
        """)
        rows = [(f"{r['student']}  ·  {r['category'].replace('_',' ').title()}",
                 "Verified" if r["verified"] else "Pending",
                 "#059669" if r["verified"] else "#D97706") for r in recent]
        old = self.recent
        self.recent = RecentList(rows, "No welfare records yet.")
        self.layout().replaceWidget(old, self.recent); old.deleteLater()


class _ClassTeacherDashboard(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("background:transparent;")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 4, 0, 16); lay.setSpacing(8)

        self.class_banner = QLabel("Loading class info…")
        self.class_banner.setStyleSheet(
            "background:#EFF6FF;color:#1D4ED8;border-radius:8px;"
            "padding:10px 14px;font-size:13px;font-weight:600;"
        )
        lay.addWidget(self.class_banner)

        _section(lay, "My Class — Today", [
            StatCard("Students",         "—", "#2563EB", 10),
            StatCard("Present Today",    "—", "#059669",  2),
            StatCard("Absent Today",     "—", "#DC2626",  2),
            StatCard("Late / Excused",   "—", "#D97706",  2),
            StatCard("Grade Drafts",     "—", "#0891B2",  4),
            StatCard("Grades Submitted", "—", "#7C3AED",  4),
        ])
        cards = _FullDashboard._last_n(lay, 6)
        self.c_students, self.c_present, self.c_absent, \
            self.c_late, self.c_drafts, self.c_submit = cards

        lay.addWidget(SectionLabel("ABSENT STUDENTS TODAY"))
        self.absent_list = RecentList([])
        lay.addWidget(self.absent_list)
        lay.addStretch()

    def _get_class(self):
        user = session.user or {}
        tid = user.get("teacher_id")
        if not tid:
            return None, None
        row = fetch_one("SELECT id, name FROM classes WHERE teacher_id=?", (tid,))
        return (row["id"], row["name"]) if row else (None, None)

    def refresh(self):
        today = date.today().isoformat()
        class_id, class_name = self._get_class()
        if not class_id:
            self.class_banner.setText("No class assigned — contact admin.")
            return
        self.class_banner.setText(f"Showing data for:  {class_name}")
        self.c_students.set_value(_n(fetch_one(
            "SELECT COUNT(*) AS n FROM students WHERE class_id=? AND is_active=1", (class_id,))))
        self.c_present.set_value(_n(fetch_one(
            "SELECT COUNT(*) AS n FROM attendance a JOIN students s ON s.id=a.student_id "
            "WHERE s.class_id=? AND a.date=? AND a.status='Present'", (class_id, today))))
        self.c_absent.set_value(_n(fetch_one(
            "SELECT COUNT(*) AS n FROM attendance a JOIN students s ON s.id=a.student_id "
            "WHERE s.class_id=? AND a.date=? AND a.status='Absent'", (class_id, today))))
        self.c_late.set_value(_n(fetch_one(
            "SELECT COUNT(*) AS n FROM attendance a JOIN students s ON s.id=a.student_id "
            "WHERE s.class_id=? AND a.date=? AND a.status IN ('Late','Excused')", (class_id, today))))
        self.c_drafts.set_value(_n(fetch_one(
            "SELECT COUNT(*) AS n FROM grades g JOIN students s ON s.id=g.student_id "
            "WHERE s.class_id=? AND g.status='draft'", (class_id,))))
        self.c_submit.set_value(_n(fetch_one(
            "SELECT COUNT(*) AS n FROM grades g JOIN students s ON s.id=g.student_id "
            "WHERE s.class_id=? AND g.status='submitted'", (class_id,))))
        absent = fetch_all("""
            SELECT s.first_name||' '||s.last_name AS student, a.notes
            FROM attendance a JOIN students s ON s.id=a.student_id
            WHERE s.class_id=? AND a.date=? AND a.status='Absent' ORDER BY s.last_name
        """, (class_id, today))
        rows = [(r["student"], r["notes"] or "No reason", "#DC2626") for r in absent]
        old = self.absent_list
        self.absent_list = RecentList(rows, "No absences recorded today.")
        self.layout().replaceWidget(old, self.absent_list); old.deleteLater()


class _SubjectTeacherDashboard(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("background:transparent;")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 4, 0, 16); lay.setSpacing(8)

        _section(lay, "My Grade Status", [
            StatCard("Draft Grades",        "—", "#D97706", 4),
            StatCard("Submitted for Review","—", "#0891B2", 4),
            StatCard("Approved Grades",     "—", "#059669", 4),
            StatCard("Open Exams",          "—", "#7C3AED", 4),
        ], cols=4)
        cards = _FullDashboard._last_n(lay, 4)
        self.c_drafts, self.c_submitted, self.c_approved, self.c_exams = cards

        lay.addWidget(SectionLabel("OPEN EXAMS"))
        self.exam_list = RecentList([])
        lay.addWidget(self.exam_list)

        lay.addWidget(SectionLabel("MY PENDING SUBMISSIONS"))
        self.draft_list = RecentList([])
        lay.addWidget(self.draft_list)
        lay.addStretch()

    def refresh(self):
        user = session.user or {}
        tid  = user.get("teacher_id")
        if tid:
            self.c_drafts.set_value(_n(fetch_one(
                "SELECT COUNT(*) AS n FROM grades g "
                "JOIN teacher_subjects ts ON ts.subject_id=g.subject_id "
                "WHERE ts.teacher_id=? AND g.status='draft'", (tid,))))
            self.c_submitted.set_value(_n(fetch_one(
                "SELECT COUNT(*) AS n FROM grades g "
                "JOIN teacher_subjects ts ON ts.subject_id=g.subject_id "
                "WHERE ts.teacher_id=? AND g.status='submitted'", (tid,))))
            self.c_approved.set_value(_n(fetch_one(
                "SELECT COUNT(*) AS n FROM grades g "
                "JOIN teacher_subjects ts ON ts.subject_id=g.subject_id "
                "WHERE ts.teacher_id=? AND g.status='approved'", (tid,))))
        self.c_exams.set_value(_n(fetch_one(
            "SELECT COUNT(*) AS n FROM exams WHERE status='open'")))

        exams = fetch_all("""
            SELECT e.name, e.term, ay.label AS year FROM exams e
            LEFT JOIN academic_years ay ON ay.id=e.academic_year_id
            WHERE e.status='open' ORDER BY e.id DESC LIMIT 5
        """)
        erows = [(f"{e['name']}  ·  Term {e['term']}", e["year"] or "—", "#7C3AED")
                 for e in exams]
        old = self.exam_list
        self.exam_list = RecentList(erows, "No open exams.")
        self.layout().replaceWidget(old, self.exam_list); old.deleteLater()

        drows = []
        if tid:
            drafts = fetch_all("""
                SELECT e.name AS exam_name, s.name AS subj_name,
                       c.name AS class_name, COUNT(g.id) AS cnt, g.status
                FROM grades g
                JOIN exams e ON e.id=g.exam_id
                JOIN subjects s ON s.id=g.subject_id
                JOIN students st ON st.id=g.student_id
                JOIN classes c ON c.id=st.class_id
                JOIN teacher_subjects ts ON ts.subject_id=g.subject_id AND ts.teacher_id=?
                WHERE g.status IN ('draft','submitted')
                GROUP BY g.exam_id, g.subject_id, st.class_id, g.status
                ORDER BY g.status, e.id DESC LIMIT 8
            """, (tid,))
            colour_map = {"draft": "#D97706", "submitted": "#0891B2"}
            drows = [(f"{d['exam_name']}  ·  {d['subj_name']} ({d['class_name']})",
                      d["status"].title(), colour_map.get(d["status"], "#374151"))
                     for d in drafts]
        old = self.draft_list
        self.draft_list = RecentList(drows, "No pending grade work.")
        self.layout().replaceWidget(old, self.draft_list); old.deleteLater()


class _StorekeeperDashboard(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("background:transparent;")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 4, 0, 16); lay.setSpacing(8)

        _section(lay, "Inventory Overview", [
            StatCard("Active Items",       "—", "#2563EB", 6),
            StatCard("Low Stock Alerts",   "—", "#DC2626", 6),
            StatCard("Units Issued Today", "—", "#D97706", 6),
        ])
        self.c_items, self.c_low, self.c_today = _FullDashboard._last3(lay)

        lay.addWidget(SectionLabel("LOW STOCK ITEMS"))
        self.low_list = RecentList([])
        lay.addWidget(self.low_list)

        lay.addWidget(SectionLabel("ISSUED TODAY"))
        self.issue_list = RecentList([])
        lay.addWidget(self.issue_list)
        lay.addStretch()

    def refresh(self):
        today = date.today().isoformat()
        self.c_items.set_value(_n(fetch_one(
            "SELECT COUNT(*) AS n FROM inventory_items WHERE is_active=1")))
        self.c_low.set_value(_n(fetch_one(
            "SELECT COUNT(*) AS n FROM inventory_items "
            "WHERE is_active=1 AND stock_qty<=reorder_qty")))
        r = fetch_one("SELECT COALESCE(SUM(qty),0) AS n FROM inventory_transactions "
                      "WHERE type='issued' AND date(created_at)=?", (today,))
        self.c_today.set_value(_n(r))

        low = fetch_all("""
            SELECT name, stock_qty, unit FROM inventory_items
            WHERE is_active=1 AND stock_qty<=reorder_qty ORDER BY stock_qty LIMIT 8
        """)
        lrows = [(r["name"], f"{r['stock_qty']} {r['unit']} left",
                  "#DC2626" if r["stock_qty"] == 0 else "#D97706") for r in low]

        issues = fetch_all("""
            SELECT s.first_name||' '||s.last_name AS student,
                   ii.name AS item, it.qty
            FROM inventory_transactions it
            JOIN inventory_items ii ON ii.id=it.item_id
            LEFT JOIN students s ON s.id=it.student_id
            WHERE it.type='issued' AND date(it.created_at)=?
            ORDER BY it.id DESC LIMIT 8
        """, (today,))
        irows = [(f"{r['student'] or '—'}  ·  {r['item']}", f"×{r['qty']}", "#059669")
                 for r in issues]

        for old_attr, new_widget, attr in [
            ("low_list",   RecentList(lrows, "All items adequately stocked."), "low_list"),
            ("issue_list", RecentList(irows, "No issuances today."),           "issue_list"),
        ]:
            old = getattr(self, old_attr)
            self.layout().replaceWidget(old, new_widget)
            old.deleteLater()
            setattr(self, attr, new_widget)


# ═══════════════════════════════════════════════════════════════════════════════
# Main dashboard widget
# ═══════════════════════════════════════════════════════════════════════════════

_ROLE_MAP = {
    "admin":           _FullDashboard,
    "head_teacher":    _FullDashboard,
    "accountant":      _AccountantDashboard,
    "academic":        _AcademicDashboard,
    "welfare_officer": _WelfareDashboard,
    "class_teacher":   _ClassTeacherDashboard,
    "subject_teacher": _SubjectTeacherDashboard,
    "storekeeper":     _StorekeeperDashboard,
}


class DashboardWidget(QWidget):

    def __init__(self):
        super().__init__()
        self.setStyleSheet("background:#F1F5F9;")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(14)

        # ── Greeting bar ──────────────────────────────────────────────────────
        school     = get_config("school_name", "School MIS")
        today_str  = date.today().strftime("%A, %d %B %Y")
        name       = (session.full_name or session.username or "User").split()[0]
        role_label = (session.user or {}).get(
            "role_label", session.role.replace("_", " ").title()
        )

        bar = QFrame()
        bar.setStyleSheet(
            "QFrame { background: #0F172A; border-radius: 10px; }"
        )
        bar_lay = QHBoxLayout(bar)
        bar_lay.setContentsMargins(20, 14, 20, 14)

        left_v = QVBoxLayout(); left_v.setSpacing(2)
        hi = QLabel(f"Welcome back, {name}")
        hi.setStyleSheet("font-size:18px;font-weight:700;color:#F8FAFC;background:transparent;")
        sub = QLabel(f"{role_label}  ·  {today_str}")
        sub.setStyleSheet("font-size:12px;color:#94A3B8;background:transparent;")
        left_v.addWidget(hi); left_v.addWidget(sub)

        badge = QLabel(school)
        badge.setStyleSheet(
            "font-size:11px;font-weight:600;color:#94A3B8;"
            "background:#1E293B;border-radius:6px;padding:5px 12px;"
        )

        bar_lay.addLayout(left_v); bar_lay.addStretch(); bar_lay.addWidget(badge)
        outer.addWidget(bar)

        # ── Scrollable role content ───────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        DashClass = _ROLE_MAP.get(session.role, _FullDashboard)
        self._inner = DashClass()
        scroll.setWidget(self._inner)
        outer.addWidget(scroll)

        self._inner.refresh()

    def refresh(self):
        self._inner.refresh()
