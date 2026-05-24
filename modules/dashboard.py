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


# ── Icon loader (alpha-preserving recolor) ────────────────────────────────────

def _tinted_icon(n: int, hex_color: str, size: int = 26) -> QPixmap:
    """Load a PNG icon and recolor it to hex_color, preserving transparency."""
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
            alpha = QColor(img.pixel(x, y)).alpha()
            img.setPixelColor(x, y, QColor(r, g, b, alpha))
    return QPixmap.fromImage(img)


def _n(row, key="n"):
    return row[key] if row else 0


# ── Reusable widgets ──────────────────────────────────────────────────────────

class StatCard(QFrame):
    """A KPI card with icon badge, big number, and title."""

    def __init__(self, title: str, value, color: str = "#2563EB",
                 icon_num: int = 0, subtitle: str = ""):
        super().__init__()
        self._color = color
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(108)
        self.setStyleSheet(f"""
            QFrame {{
                background: white;
                border-radius: 12px;
                border: 1px solid #E5E7EB;
            }}
            QFrame:hover {{
                border: 1px solid {color};
            }}
        """)

        root = QHBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(14)

        # Colored icon badge on the left
        if icon_num:
            badge = QFrame()
            badge.setFixedSize(52, 52)
            # light-tinted background derived from the color
            badge.setStyleSheet(f"""
                QFrame {{
                    background: {color}18;
                    border-radius: 12px;
                    border: none;
                }}
            """)
            badge_lay = QVBoxLayout(badge)
            badge_lay.setContentsMargins(0, 0, 0, 0)
            badge_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
            ico_lbl = QLabel()
            ico_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            pix = _tinted_icon(icon_num, color, 28)
            ico_lbl.setPixmap(pix)
            badge_lay.addWidget(ico_lbl)
            root.addWidget(badge)

        # Text block
        text = QVBoxLayout()
        text.setSpacing(3)

        self.value_lbl = QLabel(str(value))
        self.value_lbl.setStyleSheet(
            f"font-size:24px;font-weight:700;color:{color};letter-spacing:-0.5px;"
        )
        text.addWidget(self.value_lbl)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size:12px;color:#6B7280;font-weight:500;")
        text.addWidget(title_lbl)

        if subtitle:
            self.sub_lbl = QLabel(subtitle)
            self.sub_lbl.setStyleSheet("font-size:11px;color:#9CA3AF;")
            text.addWidget(self.sub_lbl)
        else:
            self.sub_lbl = None

        root.addLayout(text)
        root.addStretch()

    def set_value(self, v, subtitle: str = ""):
        self.value_lbl.setText(str(v))
        if self.sub_lbl and subtitle:
            self.sub_lbl.setText(subtitle)


class SectionHeader(QLabel):
    def __init__(self, text: str):
        super().__init__(text)
        self.setStyleSheet(
            "font-size:13px;font-weight:700;color:#374151;"
            "padding-bottom:6px;margin-top:10px;"
        )


class Divider(QFrame):
    def __init__(self):
        super().__init__()
        self.setFrameShape(QFrame.Shape.HLine)
        self.setStyleSheet("color:#F3F4F6;background:#F3F4F6;border:none;max-height:1px;")


class RecentList(QFrame):
    """A compact list of recent activity rows."""

    def __init__(self, rows: list[tuple], empty_text="Nothing to show yet."):
        super().__init__()
        self.setStyleSheet("""
            QFrame {
                background: white;
                border: 1px solid #E5E7EB;
                border-radius: 12px;
            }
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(0)

        if not rows:
            lbl = QLabel(empty_text)
            lbl.setStyleSheet("font-size:12px;color:#9CA3AF;padding:4px 0;")
            lay.addWidget(lbl)
            return

        for i, (left, right, colour) in enumerate(rows):
            row_w = QWidget()
            row_w.setStyleSheet("background:transparent;")
            row_lay = QHBoxLayout(row_w)
            row_lay.setContentsMargins(0, 7, 0, 7)
            row_lay.setSpacing(10)

            dot = QLabel()
            dot.setFixedSize(8, 8)
            dot.setStyleSheet(
                f"background:{colour};border-radius:4px;min-width:8px;max-width:8px;"
            )

            l = QLabel(left)
            l.setStyleSheet("font-size:12px;color:#374151;")
            l.setWordWrap(True)

            r_lbl = QLabel(right)
            r_lbl.setStyleSheet(
                f"font-size:11px;color:{colour};font-weight:600;"
                "background:transparent;"
            )
            r_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            r_lbl.setMinimumWidth(80)

            row_lay.addWidget(dot)
            row_lay.addWidget(l, 1)
            row_lay.addWidget(r_lbl)
            lay.addWidget(row_w)

            if i < len(rows) - 1:
                sep = QFrame()
                sep.setFrameShape(QFrame.Shape.HLine)
                sep.setStyleSheet(
                    "color:#F3F4F6;background:#F3F4F6;"
                    "border:none;max-height:1px;margin:0;"
                )
                lay.addWidget(sep)


def _card_grid(cards: list, cols: int = 3) -> QGridLayout:
    grid = QGridLayout()
    grid.setSpacing(14)
    for i, card in enumerate(cards):
        grid.addWidget(card, i // cols, i % cols)
    return grid


# ── Role-specific dashboard panels ───────────────────────────────────────────

class _FullDashboard(QWidget):
    """Admin / Head Teacher — complete school overview."""

    def __init__(self):
        super().__init__()
        self.setStyleSheet("background:transparent;")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

        lay.addWidget(SectionHeader("School Overview"))
        self.c_students = StatCard("Active Students",       "—", "#2563EB", 10)
        self.c_teachers = StatCard("Teachers & Staff",      "—", "#059669", 41)
        self.c_classes  = StatCard("Classes",               "—", "#7C3AED", 38)
        lay.addLayout(_card_grid([self.c_students, self.c_teachers, self.c_classes]))

        lay.addWidget(SectionHeader("Attendance Today"))
        self.c_present = StatCard("Present",           "—", "#059669",  2)
        self.c_absent  = StatCard("Absent",            "—", "#DC2626",  2)
        self.c_late    = StatCard("Late / Excused",    "—", "#D97706",  2)
        lay.addLayout(_card_grid([self.c_present, self.c_absent, self.c_late]))

        lay.addWidget(SectionHeader("Finance, Welfare & Inventory"))
        self.c_fees     = StatCard("Fees Collected (Month)", "—", "#059669",  3)
        self.c_unpaid   = StatCard("Unpaid Bills",           "—", "#DC2626",  3)
        self.c_welfare  = StatCard("Welfare Students",       "—", "#9333EA",  5)
        self.c_stock    = StatCard("Low Stock Items",        "—", "#B45309",  6)
        self.c_expenses = StatCard("Expenses (Month)",       "—", "#EA580C",  7)
        self.c_grades   = StatCard("Grades Awaiting Approval","—","#0891B2",  4)
        lay.addLayout(_card_grid([
            self.c_fees, self.c_unpaid, self.c_welfare,
            self.c_stock, self.c_expenses, self.c_grades,
        ]))

        lay.addWidget(SectionHeader("Recent Payments"))
        self.recent_frame = RecentList([])
        lay.addWidget(self.recent_frame)
        lay.addStretch()

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
                 f"TZS {p['amount_paid']:,.0f}", "#059669")
                for p in payments]
        self._replace(self.recent_frame, RecentList(rows, "No payments recorded yet."))

    def _replace(self, old, new):
        lay = self.layout()
        idx = lay.indexOf(old)
        old.setParent(None)
        lay.insertWidget(idx, new)
        self.recent_frame = new


class _AccountantDashboard(QWidget):
    """Accountant — finance view."""

    def __init__(self):
        super().__init__()
        self.setStyleSheet("background:transparent;")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(10)

        lay.addWidget(SectionHeader("Collections"))
        self.c_today   = StatCard("Collected Today",      "—", "#059669", 3)
        self.c_month   = StatCard("Collected This Month", "—", "#2563EB", 3)
        self.c_expense = StatCard("Expenses This Month",  "—", "#EA580C", 7)
        lay.addLayout(_card_grid([self.c_today, self.c_month, self.c_expense]))

        lay.addWidget(SectionHeader("Outstanding Bills"))
        self.c_unpaid  = StatCard("Unpaid Bills",   "—", "#DC2626", 3)
        self.c_partial = StatCard("Partial Bills",  "—", "#D97706", 3)
        self.c_waived  = StatCard("Waived Bills",   "—", "#9333EA", 5)
        lay.addLayout(_card_grid([self.c_unpaid, self.c_partial, self.c_waived]))

        lay.addWidget(SectionHeader("Recent Payments"))
        self.recent_frame = RecentList([])
        lay.addWidget(self.recent_frame)
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
                   fp.amount_paid, fp.payment_method, fp.receipt_no, fp.payment_date
            FROM fee_payments fp JOIN students s ON s.id=fp.student_id
            ORDER BY fp.id DESC LIMIT 8
        """)
        rows = [(f"{p['student']}  ·  {p['payment_method']}  ·  {p['payment_date']}",
                 f"TZS {p['amount_paid']:,.0f}", "#059669") for p in rows_db]
        new = RecentList(rows, "No payments recorded yet.")
        lay = self.layout()
        idx = lay.indexOf(self.recent_frame)
        self.recent_frame.setParent(None)
        lay.insertWidget(idx, new)
        self.recent_frame = new


class _AcademicDashboard(QWidget):
    """Academic Officer — attendance, grades, exams."""

    def __init__(self):
        super().__init__()
        self.setStyleSheet("background:transparent;")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(10)

        lay.addWidget(SectionHeader("School — Academic Overview"))
        self.c_students = StatCard("Active Students",          "—", "#2563EB", 10)
        self.c_classes  = StatCard("Classes",                  "—", "#7C3AED", 38)
        self.c_exams    = StatCard("Open Exams",               "—", "#0891B2",  4)
        lay.addLayout(_card_grid([self.c_students, self.c_classes, self.c_exams]))

        lay.addWidget(SectionHeader("Attendance Today"))
        self.c_present = StatCard("Present", "—", "#059669", 2)
        self.c_absent  = StatCard("Absent",  "—", "#DC2626", 2)
        self.c_pending = StatCard("Grade Batches Pending Approval", "—", "#D97706", 4)
        lay.addLayout(_card_grid([self.c_present, self.c_absent, self.c_pending]))

        lay.addWidget(SectionHeader("Grade Batches Awaiting Approval"))
        self.pending_frame = RecentList([])
        lay.addWidget(self.pending_frame)
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
        rows = [(f"{b['exam_name']}  ·  {b['class_name']}  /  {b['subj_name']}",
                 f"{b['cnt']} grades", "#D97706") for b in batches]
        new = RecentList(rows, "No pending grade submissions.")
        lay = self.layout()
        idx = lay.indexOf(self.pending_frame)
        self.pending_frame.setParent(None)
        lay.insertWidget(idx, new)
        self.pending_frame = new


class _WelfareDashboard(QWidget):
    """Welfare Officer — welfare records and exemptions."""

    def __init__(self):
        super().__init__()
        self.setStyleSheet("background:transparent;")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(10)

        lay.addWidget(SectionHeader("Welfare Records"))
        self.c_total    = StatCard("Total Welfare Records", "—", "#9333EA", 5)
        self.c_verified = StatCard("Verified",              "—", "#059669", 5)
        self.c_pending  = StatCard("Awaiting Verification", "—", "#D97706", 5)
        lay.addLayout(_card_grid([self.c_total, self.c_verified, self.c_pending]))

        lay.addWidget(SectionHeader("Categories"))
        self.c_orphan = StatCard("Orphan Students",       "—", "#7C3AED", 10)
        self.c_half   = StatCard("Half-Orphan Students",  "—", "#6B7280", 10)
        self.c_exempt = StatCard("Full Fee Exemptions",   "—", "#0891B2",  5)
        lay.addLayout(_card_grid([self.c_orphan, self.c_half, self.c_exempt]))

        lay.addWidget(SectionHeader("Recent Welfare Registrations"))
        self.recent_frame = RecentList([])
        lay.addWidget(self.recent_frame)
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
            SELECT s.first_name||' '||s.last_name AS student,
                   wr.category, wr.support_type, wr.verified
            FROM welfare_records wr JOIN students s ON s.id=wr.student_id
            ORDER BY wr.id DESC LIMIT 8
        """)
        rows = [(f"{r['student']}  ·  {r['category'].replace('_',' ').title()}",
                 "Verified" if r["verified"] else "Pending",
                 "#059669" if r["verified"] else "#D97706") for r in recent]
        new = RecentList(rows, "No welfare records yet.")
        lay = self.layout()
        idx = lay.indexOf(self.recent_frame)
        self.recent_frame.setParent(None)
        lay.insertWidget(idx, new)
        self.recent_frame = new


class _ClassTeacherDashboard(QWidget):
    """Class Teacher — their class only."""

    def __init__(self):
        super().__init__()
        self.setStyleSheet("background:transparent;")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(10)

        self.class_banner = QLabel("")
        self.class_banner.setStyleSheet(
            "background:#EFF6FF;color:#1D4ED8;border-radius:10px;"
            "padding:12px 16px;font-size:13px;font-weight:600;"
        )
        self.class_banner.setWordWrap(True)
        lay.addWidget(self.class_banner)

        lay.addWidget(SectionHeader("My Class — Today"))
        self.c_students = StatCard("Students",           "—", "#2563EB", 10)
        self.c_present  = StatCard("Present Today",      "—", "#059669",  2)
        self.c_absent   = StatCard("Absent Today",       "—", "#DC2626",  2)
        self.c_late     = StatCard("Late / Excused",     "—", "#D97706",  2)
        self.c_drafts   = StatCard("My Grade Drafts",    "—", "#0891B2",  4)
        self.c_submit   = StatCard("Grades Submitted",   "—", "#7C3AED",  4)
        lay.addLayout(_card_grid([
            self.c_students, self.c_present, self.c_absent,
            self.c_late, self.c_drafts, self.c_submit,
        ]))

        lay.addWidget(SectionHeader("Absent Students Today"))
        self.absent_frame = RecentList([])
        lay.addWidget(self.absent_frame)
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
            self.class_banner.setText(
                "No class assigned yet — contact admin to assign you a class."
            )
            return
        self.class_banner.setText(f"Showing data for: {class_name}")

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
            WHERE s.class_id=? AND a.date=? AND a.status='Absent'
            ORDER BY s.last_name
        """, (class_id, today))
        rows = [(r["student"], r["notes"] or "No reason given", "#DC2626") for r in absent]
        new = RecentList(rows, "No absences recorded today.")
        lay = self.layout()
        idx = lay.indexOf(self.absent_frame)
        self.absent_frame.setParent(None)
        lay.insertWidget(idx, new)
        self.absent_frame = new


class _SubjectTeacherDashboard(QWidget):
    """Subject Teacher — grade entry status."""

    def __init__(self):
        super().__init__()
        self.setStyleSheet("background:transparent;")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(10)

        lay.addWidget(SectionHeader("My Grade Entry Status"))
        self.c_drafts    = StatCard("My Draft Grades",      "—", "#D97706", 4)
        self.c_submitted = StatCard("Submitted for Review", "—", "#0891B2", 4)
        self.c_approved  = StatCard("Approved Grades",      "—", "#059669", 4)
        self.c_exams     = StatCard("Open Exams",           "—", "#7C3AED", 4)
        lay.addLayout(_card_grid([
            self.c_drafts, self.c_submitted, self.c_approved, self.c_exams,
        ], cols=4))

        lay.addWidget(SectionHeader("Open Exams"))
        self.exam_frame = RecentList([])
        lay.addWidget(self.exam_frame)

        lay.addWidget(SectionHeader("My Pending Submissions"))
        self.draft_frame = RecentList([])
        lay.addWidget(self.draft_frame)
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
            SELECT e.name, e.term, ay.label AS year
            FROM exams e LEFT JOIN academic_years ay ON ay.id=e.academic_year_id
            WHERE e.status='open' ORDER BY e.id DESC LIMIT 5
        """)
        erows = [(f"{e['name']}  ·  Term {e['term']}", e["year"] or "—", "#7C3AED")
                 for e in exams]

        lay = self.layout()
        new_e = RecentList(erows, "No open exams.")
        idx_e = lay.indexOf(self.exam_frame)
        self.exam_frame.setParent(None)
        lay.insertWidget(idx_e, new_e)
        self.exam_frame = new_e

        if tid:
            drafts = fetch_all("""
                SELECT e.name AS exam_name, s.name AS subj_name,
                       c.name AS class_name, COUNT(g.id) AS cnt, g.status
                FROM grades g
                JOIN exams e ON e.id=g.exam_id
                JOIN subjects s ON s.id=g.subject_id
                JOIN students st ON st.id=g.student_id
                JOIN classes c ON c.id=st.class_id
                JOIN teacher_subjects ts
                  ON ts.subject_id=g.subject_id AND ts.teacher_id=?
                WHERE g.status IN ('draft','submitted')
                GROUP BY g.exam_id, g.subject_id, st.class_id, g.status
                ORDER BY g.status, e.id DESC LIMIT 8
            """, (tid,))
            colour_map = {"draft": "#D97706", "submitted": "#0891B2"}
            drows = [(f"{d['exam_name']}  ·  {d['subj_name']} ({d['class_name']})",
                      d["status"].title(), colour_map.get(d["status"], "#374151"))
                     for d in drafts]
        else:
            drows = []

        new_d = RecentList(drows, "No pending grade work.")
        idx_d = lay.indexOf(self.draft_frame)
        self.draft_frame.setParent(None)
        lay.insertWidget(idx_d, new_d)
        self.draft_frame = new_d


class _StorekeeperDashboard(QWidget):
    """Storekeeper — inventory levels and issuances."""

    def __init__(self):
        super().__init__()
        self.setStyleSheet("background:transparent;")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(10)

        lay.addWidget(SectionHeader("Inventory Overview"))
        self.c_items    = StatCard("Active Items",       "—", "#2563EB", 6)
        self.c_lowstock = StatCard("Low Stock Alerts",   "—", "#DC2626", 6)
        self.c_today    = StatCard("Units Issued Today", "—", "#D97706", 6)
        lay.addLayout(_card_grid([self.c_items, self.c_lowstock, self.c_today]))

        lay.addWidget(SectionHeader("Low Stock Items"))
        self.low_frame = RecentList([])
        lay.addWidget(self.low_frame)

        lay.addWidget(SectionHeader("Issued Today"))
        self.issue_frame = RecentList([])
        lay.addWidget(self.issue_frame)
        lay.addStretch()

    def refresh(self):
        today = date.today().isoformat()
        self.c_items.set_value(_n(fetch_one(
            "SELECT COUNT(*) AS n FROM inventory_items WHERE is_active=1")))
        self.c_lowstock.set_value(_n(fetch_one(
            "SELECT COUNT(*) AS n FROM inventory_items "
            "WHERE is_active=1 AND stock_qty<=reorder_qty")))
        r = fetch_one("SELECT COALESCE(SUM(qty),0) AS n FROM inventory_transactions "
                      "WHERE type='issued' AND date(created_at)=?", (today,))
        self.c_today.set_value(_n(r))

        low = fetch_all("""
            SELECT name, stock_qty, reorder_qty, unit FROM inventory_items
            WHERE is_active=1 AND stock_qty<=reorder_qty ORDER BY stock_qty LIMIT 8
        """)
        lrows = [(r["name"],
                  f"{r['stock_qty']} {r['unit']} remaining",
                  "#DC2626" if r["stock_qty"] == 0 else "#D97706")
                 for r in low]

        issues = fetch_all("""
            SELECT s.first_name||' '||s.last_name AS student,
                   ii.name AS item, it.qty
            FROM inventory_transactions it
            JOIN inventory_items ii ON ii.id=it.item_id
            LEFT JOIN students s ON s.id=it.student_id
            WHERE it.type='issued' AND date(it.created_at)=?
            ORDER BY it.id DESC LIMIT 8
        """, (today,))
        irows = [(f"{r['student'] or '—'}  ·  {r['item']}",
                  f"×{r['qty']}", "#059669") for r in issues]

        lay = self.layout()
        for old, new, attr in [
            (self.low_frame,   RecentList(lrows, "All items adequately stocked."), "low_frame"),
            (self.issue_frame, RecentList(irows, "No issuances today."),           "issue_frame"),
        ]:
            idx = lay.indexOf(old)
            old.setParent(None)
            lay.insertWidget(idx, new)
            setattr(self, attr, new)


# ── Main dashboard widget (role router) ───────────────────────────────────────

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
        self.setStyleSheet("background:#F8FAFC;")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 24, 28, 24)
        outer.setSpacing(16)

        # ── Greeting strip ────────────────────────────────────────────────────
        school  = get_config("school_name", "School MIS")
        today   = date.today().strftime("%A, %d %B %Y")
        name    = (session.full_name or session.username or "User").split()[0]
        role_label = (session.user or {}).get(
            "role_label", session.role.replace("_", " ").title()
        )

        greet_frame = QFrame()
        greet_frame.setStyleSheet(
            "QFrame{background:white;border-radius:12px;border:1px solid #E5E7EB;}"
        )
        gf = QHBoxLayout(greet_frame)
        gf.setContentsMargins(20, 14, 20, 14)

        left = QVBoxLayout(); left.setSpacing(2)
        hi = QLabel(f"Welcome, {name}")
        hi.setStyleSheet("font-size:20px;font-weight:700;color:#111827;")
        sub = QLabel(f"{role_label}  ·  {today}")
        sub.setStyleSheet("font-size:12px;color:#6B7280;")
        left.addWidget(hi); left.addWidget(sub)
        gf.addLayout(left); gf.addStretch()

        school_badge = QLabel(school)
        school_badge.setStyleSheet(
            "font-size:12px;font-weight:600;color:#374151;"
            "background:#F3F4F6;border-radius:8px;padding:6px 14px;"
        )
        gf.addWidget(school_badge)
        outer.addWidget(greet_frame)

        # ── Role-specific content in a scroll area ────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")

        DashClass = _ROLE_MAP.get(session.role, _FullDashboard)
        self._inner = DashClass()
        scroll.setWidget(self._inner)
        outer.addWidget(scroll)

        self._inner.refresh()

    def refresh(self):
        self._inner.refresh()
