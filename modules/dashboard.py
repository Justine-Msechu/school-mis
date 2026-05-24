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

def _stat_icon(n: int, color: str, size: int = 28) -> QPixmap:
    src = QPixmap(str(_ICON_DIR / f"Icon {n}.png"))
    if src.isNull():
        return QPixmap()
    src = src.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio,
                     Qt.TransformationMode.SmoothTransformation)
    img = src.toImage().convertToFormat(QImage.Format.Format_ARGB32)
    c = QColor(color)
    r, g, b = c.red(), c.green(), c.blue()
    for y in range(img.height()):
        for x in range(img.width()):
            lum = (QColor(img.pixel(x, y)).red() + QColor(img.pixel(x, y)).green()
                   + QColor(img.pixel(x, y)).blue()) // 3
            img.setPixelColor(x, y, QColor(r, g, b, 255 - lum))
    return QPixmap.fromImage(img)


def _n(row, key="n"):
    return row[key] if row else 0


# ── Reusable widgets ──────────────────────────────────────────────────────────

class StatCard(QFrame):
    def __init__(self, title: str, value, color="#2563EB", icon_num=0, subtitle=""):
        super().__init__()
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(f"""
            QFrame {{
                background: white; border-radius: 12px;
                border-left: 4px solid {color};
                border-top: 1px solid #E5E7EB;
                border-right: 1px solid #E5E7EB;
                border-bottom: 1px solid #E5E7EB;
            }}
        """)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(100)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(4)

        top = QHBoxLayout()
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size:12px;color:#6B7280;font-weight:600;")
        top.addWidget(title_lbl); top.addStretch()
        if icon_num:
            ico = QLabel()
            pix = _stat_icon(icon_num, color, 22)
            ico.setPixmap(pix)
            top.addWidget(ico)
        lay.addLayout(top)

        self.value_lbl = QLabel(str(value))
        self.value_lbl.setStyleSheet(f"font-size:26px;font-weight:700;color:{color};")
        lay.addWidget(self.value_lbl)

        if subtitle:
            self.sub_lbl = QLabel(subtitle)
            self.sub_lbl.setStyleSheet("font-size:11px;color:#9CA3AF;")
            lay.addWidget(self.sub_lbl)
        else:
            self.sub_lbl = None

    def set_value(self, v, subtitle=""):
        self.value_lbl.setText(str(v))
        if self.sub_lbl and subtitle:
            self.sub_lbl.setText(subtitle)


class SectionHeader(QLabel):
    def __init__(self, text: str):
        super().__init__(text)
        self.setStyleSheet(
            "font-size:13px;font-weight:700;color:#374151;"
            "border-bottom:1px solid #E5E7EB;padding-bottom:4px;margin-top:8px;"
        )


class RecentList(QFrame):
    """A compact list of recent activity rows."""
    def __init__(self, rows: list[tuple], empty_text="Nothing to show."):
        super().__init__()
        self.setStyleSheet(
            "QFrame{background:white;border:1px solid #E5E7EB;border-radius:10px;}"
        )
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(8)
        if not rows:
            lbl = QLabel(empty_text)
            lbl.setStyleSheet("font-size:12px;color:#9CA3AF;")
            lay.addWidget(lbl)
            return
        for i, (left, right, colour) in enumerate(rows):
            row = QHBoxLayout()
            dot = QLabel("●")
            dot.setStyleSheet(f"color:{colour};font-size:10px;")
            dot.setFixedWidth(14)
            l = QLabel(left)
            l.setStyleSheet("font-size:12px;color:#374151;")
            l.setWordWrap(True)
            r = QLabel(right)
            r.setStyleSheet(f"font-size:11px;color:{colour};font-weight:600;")
            r.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            r.setMinimumWidth(70)
            row.addWidget(dot); row.addWidget(l, 1); row.addWidget(r)
            lay.addLayout(row)
            if i < len(rows) - 1:
                sep = QFrame()
                sep.setFrameShape(QFrame.Shape.HLine)
                sep.setStyleSheet("color:#F3F4F6;")
                lay.addWidget(sep)


def _card_grid(cards: list, cols=3) -> QGridLayout:
    grid = QGridLayout(); grid.setSpacing(14)
    for i, card in enumerate(cards):
        grid.addWidget(card, i // cols, i % cols)
    return grid


# ── Role dashboards ───────────────────────────────────────────────────────────

class _FullDashboard(QWidget):
    """Admin / Head Teacher — complete school overview."""

    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self); lay.setSpacing(16); lay.setContentsMargins(0,0,0,0)

        lay.addWidget(SectionHeader("School Overview"))
        self.c_students  = StatCard("Active Students",       "—", "#2563EB", 10)
        self.c_teachers  = StatCard("Teachers & Staff",      "—", "#059669", 41)
        self.c_classes   = StatCard("Classes",               "—", "#7C3AED", 38)
        self.c_present   = StatCard("Present Today",         "—", "#D97706",  2)
        self.c_absent    = StatCard("Absent Today",          "—", "#6B7280",  2)
        self.c_late      = StatCard("Late / Excused Today",  "—", "#9CA3AF",  2)
        lay.addLayout(_card_grid([
            self.c_students, self.c_teachers, self.c_classes,
            self.c_present,  self.c_absent,   self.c_late,
        ]))

        lay.addWidget(SectionHeader("Finance & Welfare"))
        self.c_fees     = StatCard("Fees Collected (month)", "—", "#059669",  3)
        self.c_unpaid   = StatCard("Unpaid Bills",           "—", "#DC2626",  3)
        self.c_welfare  = StatCard("Welfare Students",       "—", "#9333EA",  5)
        self.c_stock    = StatCard("Low Stock Items",        "—", "#B45309",  6)
        self.c_expenses = StatCard("Expenses (month)",       "—", "#EA580C",  7)
        self.c_grades   = StatCard("Grades Pending Approval","—", "#0891B2",  4)
        lay.addLayout(_card_grid([
            self.c_fees, self.c_unpaid, self.c_welfare,
            self.c_stock, self.c_expenses, self.c_grades,
        ]))

        lay.addWidget(SectionHeader("Recent Payments"))
        self.recent_payments = RecentList([])
        lay.addWidget(self.recent_payments)
        lay.addStretch()

    def refresh(self):
        today = date.today().isoformat()

        self.c_students.set_value(_n(fetch_one("SELECT COUNT(*) AS n FROM students WHERE is_active=1")))
        self.c_teachers.set_value(_n(fetch_one("SELECT COUNT(*) AS n FROM teachers WHERE is_active=1")))
        self.c_classes.set_value(_n(fetch_one("SELECT COUNT(*) AS n FROM classes")))

        self.c_present.set_value(_n(fetch_one(
            "SELECT COUNT(*) AS n FROM attendance WHERE date=? AND status='Present'", (today,))))
        self.c_absent.set_value(_n(fetch_one(
            "SELECT COUNT(*) AS n FROM attendance WHERE date=? AND status='Absent'", (today,))))
        self.c_late.set_value(_n(fetch_one(
            "SELECT COUNT(*) AS n FROM attendance WHERE date=? AND status IN ('Late','Excused')", (today,))))

        r = fetch_one("SELECT COALESCE(SUM(amount_paid),0) AS t FROM fee_payments "
                      "WHERE strftime('%Y-%m',payment_date)=strftime('%Y-%m','now')")
        self.c_fees.set_value(f"TZS {_n(r,'t'):,.0f}")

        self.c_unpaid.set_value(_n(fetch_one(
            "SELECT COUNT(*) AS n FROM student_bills WHERE status IN ('unpaid','partial')")))
        self.c_welfare.set_value(_n(fetch_one("SELECT COUNT(*) AS n FROM welfare_records")))
        self.c_stock.set_value(_n(fetch_one(
            "SELECT COUNT(*) AS n FROM inventory_items WHERE is_active=1 AND stock_qty<=reorder_qty")))

        r = fetch_one("SELECT COALESCE(SUM(amount),0) AS t FROM expenses "
                      "WHERE strftime('%Y-%m',expense_date)=strftime('%Y-%m','now')")
        self.c_expenses.set_value(f"TZS {_n(r,'t'):,.0f}")

        self.c_grades.set_value(_n(fetch_one(
            "SELECT COUNT(*) AS n FROM grades WHERE status='submitted'")))

        payments = fetch_all("""
            SELECT s.first_name||' '||s.last_name AS student,
                   fp.amount_paid, fp.payment_method, fp.payment_date
            FROM fee_payments fp
            JOIN students s ON s.id=fp.student_id
            ORDER BY fp.id DESC LIMIT 6
        """)
        rows = [(f"{p['student']} — {p['payment_method']}",
                 f"TZS {p['amount_paid']:,.0f}", "#059669")
                for p in payments]
        self.recent_payments.setParent(None)
        self.recent_payments = RecentList(rows, "No payments recorded yet.")
        self.layout().insertWidget(self.layout().count() - 1, self.recent_payments)


class _AccountantDashboard(QWidget):
    """Accountant — finance-focused view."""

    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self); lay.setSpacing(16); lay.setContentsMargins(0,0,0,0)

        lay.addWidget(SectionHeader("Finance Overview"))
        self.c_today   = StatCard("Collected Today",     "—", "#059669", 3)
        self.c_month   = StatCard("Collected This Month","—", "#2563EB", 3)
        self.c_unpaid  = StatCard("Unpaid Bills",        "—", "#DC2626", 3)
        self.c_partial = StatCard("Partial Payments",    "—", "#D97706", 3)
        self.c_waived  = StatCard("Waived Bills",        "—", "#9333EA", 5)
        self.c_expense = StatCard("Expenses This Month", "—", "#EA580C", 7)
        lay.addLayout(_card_grid([
            self.c_today, self.c_month, self.c_unpaid,
            self.c_partial, self.c_waived, self.c_expense,
        ]))

        lay.addWidget(SectionHeader("Recent Payments"))
        self.recent = RecentList([])
        lay.addWidget(self.recent)
        lay.addStretch()

    def refresh(self):
        today = date.today().isoformat()

        r = fetch_one("SELECT COALESCE(SUM(amount_paid),0) AS t FROM fee_payments WHERE payment_date=?", (today,))
        self.c_today.set_value(f"TZS {_n(r,'t'):,.0f}")

        r = fetch_one("SELECT COALESCE(SUM(amount_paid),0) AS t FROM fee_payments "
                      "WHERE strftime('%Y-%m',payment_date)=strftime('%Y-%m','now')")
        self.c_month.set_value(f"TZS {_n(r,'t'):,.0f}")

        self.c_unpaid.set_value(_n(fetch_one(
            "SELECT COUNT(*) AS n FROM student_bills WHERE status='unpaid'")))
        self.c_partial.set_value(_n(fetch_one(
            "SELECT COUNT(*) AS n FROM student_bills WHERE status='partial'")))
        self.c_waived.set_value(_n(fetch_one(
            "SELECT COUNT(*) AS n FROM student_bills WHERE status='waived'")))

        r = fetch_one("SELECT COALESCE(SUM(amount),0) AS t FROM expenses "
                      "WHERE strftime('%Y-%m',expense_date)=strftime('%Y-%m','now')")
        self.c_expense.set_value(f"TZS {_n(r,'t'):,.0f}")

        payments = fetch_all("""
            SELECT s.first_name||' '||s.last_name AS student,
                   fp.amount_paid, fp.payment_method, fp.receipt_no, fp.payment_date
            FROM fee_payments fp
            JOIN students s ON s.id=fp.student_id
            ORDER BY fp.id DESC LIMIT 8
        """)
        rows = [(f"{p['student']} — {p['payment_method']} ({p['receipt_no'] or '—'})",
                 f"TZS {p['amount_paid']:,.0f}", "#059669")
                for p in payments]
        self.recent.setParent(None)
        self.recent = RecentList(rows, "No payments yet.")
        self.layout().insertWidget(self.layout().count() - 1, self.recent)


class _AcademicDashboard(QWidget):
    """Academic Officer — attendance, grades, exams."""

    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self); lay.setSpacing(16); lay.setContentsMargins(0,0,0,0)

        lay.addWidget(SectionHeader("Academic Overview"))
        self.c_students = StatCard("Active Students",         "—", "#2563EB", 10)
        self.c_classes  = StatCard("Classes",                 "—", "#7C3AED", 38)
        self.c_present  = StatCard("Present Today",           "—", "#059669",  2)
        self.c_absent   = StatCard("Absent Today",            "—", "#DC2626",  2)
        self.c_pending  = StatCard("Grade Batches Pending",   "—", "#D97706",  4)
        self.c_exams    = StatCard("Open Exams",              "—", "#0891B2",  4)
        lay.addLayout(_card_grid([
            self.c_students, self.c_classes, self.c_present,
            self.c_absent, self.c_pending, self.c_exams,
        ]))

        lay.addWidget(SectionHeader("Grade Batches Awaiting Approval"))
        self.pending_list = RecentList([])
        lay.addWidget(self.pending_list)
        lay.addStretch()

    def refresh(self):
        today = date.today().isoformat()
        self.c_students.set_value(_n(fetch_one("SELECT COUNT(*) AS n FROM students WHERE is_active=1")))
        self.c_classes.set_value(_n(fetch_one("SELECT COUNT(*) AS n FROM classes")))
        self.c_present.set_value(_n(fetch_one(
            "SELECT COUNT(*) AS n FROM attendance WHERE date=? AND status='Present'", (today,))))
        self.c_absent.set_value(_n(fetch_one(
            "SELECT COUNT(*) AS n FROM attendance WHERE date=? AND status='Absent'", (today,))))

        pending_count = fetch_one("""
            SELECT COUNT(DISTINCT (g.exam_id||'-'||st.class_id||'-'||g.subject_id)) AS n
            FROM grades g JOIN students st ON st.id=g.student_id WHERE g.status='submitted'
        """)
        self.c_pending.set_value(_n(pending_count))

        self.c_exams.set_value(_n(fetch_one(
            "SELECT COUNT(*) AS n FROM exams WHERE status='open'")))

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
        rows = [(f"{b['exam_name']} — {b['class_name']} / {b['subj_name']}",
                 f"{b['cnt']} grades", "#D97706")
                for b in batches]
        self.pending_list.setParent(None)
        self.pending_list = RecentList(rows, "No pending grade submissions.")
        self.layout().insertWidget(self.layout().count() - 1, self.pending_list)


class _WelfareDashboard(QWidget):
    """Welfare Officer — welfare records and exemptions."""

    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self); lay.setSpacing(16); lay.setContentsMargins(0,0,0,0)

        lay.addWidget(SectionHeader("Welfare Overview"))
        self.c_total    = StatCard("Total Welfare Records", "—", "#9333EA", 5)
        self.c_verified = StatCard("Verified Records",      "—", "#059669", 5)
        self.c_pending  = StatCard("Awaiting Verification", "—", "#D97706", 5)
        self.c_orphan   = StatCard("Orphan Students",       "—", "#7C3AED", 10)
        self.c_exempt   = StatCard("Full Fee Exemptions",   "—", "#0891B2", 5)
        self.c_half     = StatCard("Half-Orphan Students",  "—", "#6B7280", 10)
        lay.addLayout(_card_grid([
            self.c_total, self.c_verified, self.c_pending,
            self.c_orphan, self.c_exempt, self.c_half,
        ]))

        lay.addWidget(SectionHeader("Recent Welfare Registrations"))
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
        self.c_exempt.set_value(_n(fetch_one(
            "SELECT COUNT(*) AS n FROM welfare_records WHERE support_type='full_fees'")))
        self.c_half.set_value(_n(fetch_one(
            "SELECT COUNT(*) AS n FROM welfare_records WHERE category='half_orphan'")))

        recent = fetch_all("""
            SELECT s.first_name||' '||s.last_name AS student,
                   wr.category, wr.support_type, wr.verified
            FROM welfare_records wr JOIN students s ON s.id=wr.student_id
            ORDER BY wr.id DESC LIMIT 8
        """)
        rows = [(f"{r['student']} — {r['category'].replace('_',' ').title()}",
                 "Verified" if r["verified"] else "Pending",
                 "#059669" if r["verified"] else "#D97706")
                for r in recent]
        self.recent.setParent(None)
        self.recent = RecentList(rows, "No welfare records yet.")
        self.layout().insertWidget(self.layout().count() - 1, self.recent)


class _ClassTeacherDashboard(QWidget):
    """Class Teacher — their class only."""

    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self); lay.setSpacing(16); lay.setContentsMargins(0,0,0,0)
        self._class_id = None

        lay.addWidget(SectionHeader("My Class"))
        self.c_students = StatCard("Students in My Class", "—", "#2563EB", 10)
        self.c_present  = StatCard("Present Today",        "—", "#059669",  2)
        self.c_absent   = StatCard("Absent Today",         "—", "#DC2626",  2)
        self.c_late     = StatCard("Late / Excused",       "—", "#D97706",  2)
        self.c_drafts   = StatCard("Grade Drafts",         "—", "#0891B2",  4)
        self.c_submit   = StatCard("Grades Submitted",     "—", "#7C3AED",  4)
        lay.addLayout(_card_grid([
            self.c_students, self.c_present, self.c_absent,
            self.c_late, self.c_drafts, self.c_submit,
        ]))

        self.class_label = QLabel("")
        self.class_label.setStyleSheet(
            "background:#EFF6FF;color:#1D4ED8;border-radius:8px;"
            "padding:10px 14px;font-size:13px;"
        )
        self.class_label.setWordWrap(True)
        lay.addWidget(self.class_label)

        lay.addWidget(SectionHeader("Today's Absent Students"))
        self.absent_list = RecentList([])
        lay.addWidget(self.absent_list)
        lay.addStretch()

    def _get_class_id(self):
        user = session.user or {}
        tid = user.get("teacher_id")
        if not tid:
            return None
        row = fetch_one("SELECT id, name FROM classes WHERE teacher_id=?", (tid,))
        return (row["id"], row["name"]) if row else None

    def refresh(self):
        today = date.today().isoformat()
        result = self._get_class_id()
        if not result:
            self.class_label.setText(
                "No class assigned to your account yet. Ask an admin to assign you a class."
            )
            return
        class_id, class_name = result
        self.class_label.setText(f"Showing data for: {class_name}")

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
        rows = [(r["student"], r["notes"] or "No notes", "#DC2626") for r in absent]
        self.absent_list.setParent(None)
        self.absent_list = RecentList(rows, "No absences recorded today.")
        self.layout().insertWidget(self.layout().count() - 1, self.absent_list)


class _SubjectTeacherDashboard(QWidget):
    """Subject Teacher — grade entry status and active exams."""

    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self); lay.setSpacing(16); lay.setContentsMargins(0,0,0,0)

        lay.addWidget(SectionHeader("My Grade Entry Status"))
        self.c_drafts   = StatCard("My Draft Grades",     "—", "#D97706", 4)
        self.c_submitted= StatCard("Submitted for Review","—", "#0891B2", 4)
        self.c_approved = StatCard("Approved Grades",     "—", "#059669", 4)
        self.c_exams    = StatCard("Open Exams",          "—", "#7C3AED", 4)
        lay.addLayout(_card_grid([
            self.c_drafts, self.c_submitted, self.c_approved, self.c_exams,
        ], cols=4))

        lay.addWidget(SectionHeader("Open Exams"))
        self.exam_list = RecentList([])
        lay.addWidget(self.exam_list)

        lay.addWidget(SectionHeader("My Pending Submissions"))
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
        else:
            for c in [self.c_drafts, self.c_submitted, self.c_approved]:
                c.set_value("—")

        self.c_exams.set_value(_n(fetch_one(
            "SELECT COUNT(*) AS n FROM exams WHERE status='open'")))

        exams = fetch_all("""
            SELECT e.name, e.term, ay.label AS year
            FROM exams e LEFT JOIN academic_years ay ON ay.id=e.academic_year_id
            WHERE e.status='open' ORDER BY e.id DESC LIMIT 5
        """)
        erows = [(f"{e['name']} — Term {e['term']}", e["year"] or "", "#7C3AED")
                 for e in exams]
        self.exam_list.setParent(None)
        self.exam_list = RecentList(erows, "No open exams.")
        self.layout().insertWidget(self.layout().count() - 2, self.exam_list)

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
            drows = [(f"{d['exam_name']} — {d['subj_name']} ({d['class_name']})",
                      d["status"].title(), colour_map.get(d["status"], "#374151"))
                     for d in drafts]
        else:
            drows = []
        self.draft_list.setParent(None)
        self.draft_list = RecentList(drows, "No pending grade work.")
        self.layout().insertWidget(self.layout().count() - 1, self.draft_list)


class _StorekeeperDashboard(QWidget):
    """Storekeeper — inventory levels and recent issuances."""

    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self); lay.setSpacing(16); lay.setContentsMargins(0,0,0,0)

        lay.addWidget(SectionHeader("Inventory Overview"))
        self.c_items    = StatCard("Total Active Items", "—", "#2563EB", 6)
        self.c_lowstock = StatCard("Low Stock Alerts",   "—", "#DC2626", 6)
        self.c_today    = StatCard("Items Issued Today", "—", "#D97706", 6)
        lay.addLayout(_card_grid([self.c_items, self.c_lowstock, self.c_today], cols=3))

        lay.addWidget(SectionHeader("Low Stock Items"))
        self.low_list = RecentList([])
        lay.addWidget(self.low_list)

        lay.addWidget(SectionHeader("Recent Issuances Today"))
        self.issue_list = RecentList([])
        lay.addWidget(self.issue_list)
        lay.addStretch()

    def refresh(self):
        today = date.today().isoformat()
        self.c_items.set_value(_n(fetch_one(
            "SELECT COUNT(*) AS n FROM inventory_items WHERE is_active=1")))
        self.c_lowstock.set_value(_n(fetch_one(
            "SELECT COUNT(*) AS n FROM inventory_items WHERE is_active=1 AND stock_qty<=reorder_qty")))
        self.c_today.set_value(_n(fetch_one(
            "SELECT COALESCE(SUM(qty),0) AS n FROM inventory_transactions "
            "WHERE type='issued' AND date(created_at)=?", (today,))))

        low = fetch_all("""
            SELECT name, stock_qty, reorder_qty, unit FROM inventory_items
            WHERE is_active=1 AND stock_qty<=reorder_qty ORDER BY stock_qty LIMIT 8
        """)
        lrows = [(f"{r['name']}", f"{r['stock_qty']} {r['unit']} left",
                  "#DC2626" if r["stock_qty"] == 0 else "#D97706")
                 for r in low]
        self.low_list.setParent(None)
        self.low_list = RecentList(lrows, "All items adequately stocked.")
        self.layout().insertWidget(self.layout().count() - 2, self.low_list)

        issues = fetch_all("""
            SELECT s.first_name||' '||s.last_name AS student,
                   ii.name AS item, it.qty
            FROM inventory_transactions it
            JOIN inventory_items ii ON ii.id=it.item_id
            LEFT JOIN students s ON s.id=it.student_id
            WHERE it.type='issued' AND date(it.created_at)=?
            ORDER BY it.id DESC LIMIT 8
        """, (today,))
        irows = [(f"{r['student'] or '—'} — {r['item']}", f"×{r['qty']}", "#059669")
                 for r in issues]
        self.issue_list.setParent(None)
        self.issue_list = RecentList(irows, "No issuances today.")
        self.layout().insertWidget(self.layout().count() - 1, self.issue_list)


# ── Main dashboard widget (role router) ───────────────────────────────────────

class DashboardWidget(QWidget):

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

    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(14)

        # ── Greeting header ───────────────────────────────────────────────────
        school = get_config("school_name", "School MIS")
        today  = date.today().strftime("%A, %d %B %Y")
        name   = session.full_name or session.username or "User"
        role_label = (session.user or {}).get("role_label", session.role.replace("_", " ").title())

        greet = "Good morning" if date.today().weekday() < 5 else "Welcome back"

        top = QHBoxLayout()
        left = QVBoxLayout()
        hi = QLabel(f"{greet}, {name.split()[0]}")
        hi.setStyleSheet("font-size:22px;font-weight:700;color:#111827;")
        sub = QLabel(f"{role_label}  ·  {today}")
        sub.setStyleSheet("font-size:13px;color:#6B7280;")
        left.addWidget(hi); left.addWidget(sub)
        top.addLayout(left); top.addStretch()

        school_lbl = QLabel(school)
        school_lbl.setStyleSheet("font-size:13px;font-weight:600;color:#374151;"
                                 "background:#F3F4F6;border-radius:8px;padding:6px 14px;")
        school_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        top.addWidget(school_lbl)
        lay.addLayout(top)

        # ── Role-specific dashboard inside a scroll area ──────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")

        DashClass = self._ROLE_MAP.get(session.role, _FullDashboard)
        self._inner = DashClass()
        scroll.setWidget(self._inner)
        lay.addWidget(scroll)

    def refresh(self):
        self._inner.refresh()
