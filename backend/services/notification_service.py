"""
NotificationService — event-driven in-app notifications.

Subscribes to domain events and writes notification rows to the DB.
Portal users (parents, students) see these in their dashboards.
Staff see them via the notification bell.
"""

from __future__ import annotations
import sqlite3
import logging
from datetime import datetime, timezone

from backend.core.events import event_bus, Event, Events

log = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def _notify(self, user_ids: list[int], type_: str, title: str, body: str, data: dict | None = None) -> None:
        if not user_ids:
            return
        now = datetime.now(timezone.utc).isoformat()
        import json
        try:
            cur = self.conn.execute(
                "INSERT INTO notifications (type, title, body, data_json, created_at) VALUES (?,?,?,?,?)",
                (type_, title, body, json.dumps(data or {}), now),
            )
            notif_id = cur.lastrowid
            self.conn.executemany(
                "INSERT OR IGNORE INTO notification_recipients (notification_id, user_id) VALUES (?,?)",
                [(notif_id, uid) for uid in user_ids],
            )
            self.conn.commit()
        except Exception:
            log.exception("NotificationService._notify failed")

    def _get_staff_ids(self, roles: list[str]) -> list[int]:
        placeholders = ",".join("?" * len(roles))
        rows = self.conn.execute(
            f"SELECT id FROM users WHERE role IN ({placeholders}) AND is_active=1",
            roles,
        ).fetchall()
        return [r[0] for r in rows]

    def _get_student_portal_user_id(self, student_id: int) -> int | None:
        row = self.conn.execute(
            "SELECT user_id FROM student_portal_accounts WHERE student_id=?",
            (student_id,),
        ).fetchone()
        return row[0] if row else None

    def _get_parent_portal_user_ids(self, student_id: int) -> list[int]:
        rows = self.conn.execute(
            "SELECT user_id FROM parent_portal_accounts WHERE student_id=?",
            (student_id,),
        ).fetchall()
        return [r[0] for r in rows]

    def _get_class_student_portal_ids(self, class_id: int) -> list[int]:
        """Return portal user_ids for all students in a class."""
        rows = self.conn.execute(
            """SELECT spa.user_id FROM student_portal_accounts spa
               JOIN students s ON s.id = spa.student_id
               WHERE s.class_id = ?""",
            (class_id,),
        ).fetchall()
        return [r[0] for r in rows]

    def _get_class_parent_portal_ids(self, class_id: int) -> list[int]:
        """Return portal user_ids for all parents of students in a class."""
        rows = self.conn.execute(
            """SELECT DISTINCT ppa.user_id FROM parent_portal_accounts ppa
               JOIN students s ON s.id = ppa.student_id
               WHERE s.class_id = ?""",
            (class_id,),
        ).fetchall()
        return [r[0] for r in rows]

    # ── Event handlers ────────────────────────────────────────────────────────

    def on_payment_received(self, event: Event) -> None:
        p = event.payload
        staff_ids = self._get_staff_ids(["admin", "accountant", "head_teacher"])
        self._notify(
            staff_ids,
            "payment.received",
            "Payment Received",
            f"{p.get('student_name','A student')} paid TZS {p.get('amount',0):,.0f} (Rcpt: {p.get('receipt_no','')})",
            data={"payment_id": p.get("payment_id"), "student_id": p.get("student_id")},
        )

    def on_grades_submitted(self, event: Event) -> None:
        p = event.payload
        reviewer_ids = self._get_staff_ids(["academic", "head_teacher", "admin"])
        self._notify(
            reviewer_ids,
            "grades.submitted",
            "Grades Ready for Review",
            f"{p.get('count', 0)} grade entries submitted for review (Exam #{p.get('exam_id')})",
            data={"exam_id": p.get("exam_id"), "class_id": p.get("class_id"), "subject_id": p.get("subject_id")},
        )

    def on_grades_published(self, event: Event) -> None:
        p = event.payload
        exam_id  = p.get("exam_id")
        class_id = p.get("class_id")
        data     = {"exam_id": exam_id, "class_id": class_id}

        # Staff
        staff_ids = self._get_staff_ids(["admin", "head_teacher", "academic", "class_teacher", "subject_teacher"])
        self._notify(staff_ids, "grades.published", "Grades Published",
                     f"Results for Exam #{exam_id} have been published", data=data)

        # Portal users in the affected class
        if class_id:
            student_ids = self._get_class_student_portal_ids(class_id)
            parent_ids  = self._get_class_parent_portal_ids(class_id)
            self._notify(student_ids, "grades.published", "Your Results Are Out",
                         f"Your exam results have been published. Check your Grades tab.", data=data)
            self._notify(parent_ids, "grades.published", "Results Published",
                         f"Your child's exam results are now available.", data=data)

    def on_grades_approved(self, event: Event) -> None:
        p = event.payload
        # Notify the teacher(s) who submitted the batch
        rows = self.conn.execute(
            """SELECT DISTINCT u.id FROM users u
               JOIN grades g ON g.entered_by = u.id
               WHERE g.exam_id = ? AND g.subject_id = ?""",
            (p.get("exam_id"), p.get("subject_id")),
        ).fetchall()
        teacher_ids = [r[0] for r in rows]
        self._notify(
            teacher_ids,
            "grades.approved",
            "Grades Approved",
            f"Your grade submission for Exam #{p.get('exam_id')} has been approved.",
            data={"exam_id": p.get("exam_id"), "subject_id": p.get("subject_id")},
        )

    def on_grades_returned(self, event: Event) -> None:
        p = event.payload
        # Notify teachers who entered grades for this batch
        rows = self.conn.execute(
            """SELECT DISTINCT u.id FROM users u
               JOIN grades g ON g.entered_by = u.id
               WHERE g.exam_id = ? AND g.subject_id = ?""",
            (p.get("exam_id"), p.get("subject_id")),
        ).fetchall()
        teacher_ids = [r[0] for r in rows]
        self._notify(
            teacher_ids,
            "grades.returned",
            "Grades Returned for Correction",
            f"Your grade submission for Exam #{p.get('exam_id')} was returned: {p.get('reason','')}",
            data={"exam_id": p.get("exam_id"), "class_id": p.get("class_id"), "subject_id": p.get("subject_id")},
        )

    def on_change_request(self, event: Event) -> None:
        p = event.payload
        reviewer_ids = self._get_staff_ids(["academic", "head_teacher", "admin"])
        self._notify(
            reviewer_ids,
            "grade_change.requested",
            "Grade Change Request",
            f"A grade change request has been submitted (Grade #{p.get('grade_id')})",
            data={"cr_id": p.get("cr_id"), "grade_id": p.get("grade_id")},
        )

    def on_leave_reviewed(self, event: Event) -> None:
        p = event.payload
        student_id  = p.get("student_id")
        submitted_by = p.get("submitted_by")  # user_id of parent who submitted
        approved    = p.get("approved", False)
        status      = "approved" if approved else "rejected"

        recipients = []
        if submitted_by:
            recipients.append(submitted_by)

        # Also notify the student's portal account if one exists
        if student_id:
            uid = self._get_student_portal_user_id(student_id)
            if uid and uid not in recipients:
                recipients.append(uid)

        self._notify(
            recipients,
            "leave.reviewed",
            f"Leave Request {status.title()}",
            f"The leave request for {p.get('date_from','')} – {p.get('date_to','')} has been {status}."
            + (f" Note: {p.get('review_note','')}" if p.get("review_note") else ""),
            data={"student_id": student_id, "status": status},
        )

    def on_report_card_published(self, event: Event) -> None:
        p = event.payload
        student_id = p.get("student_id")
        if not student_id:
            return
        data = {"card_id": p.get("card_id"), "student_id": student_id}

        student_uid = self._get_student_portal_user_id(student_id)
        parent_uids = self._get_parent_portal_user_ids(student_id)
        all_ids     = ([student_uid] if student_uid else []) + parent_uids

        self._notify(all_ids, "report_card.published", "Report Card Available",
                     "Your report card has been published. You can view it in the portal.",
                     data=data)

    # ── Registration ─────────────────────────────────────────────────────────

    def register(self) -> None:
        """Subscribe all handlers to the event bus. Call once at startup."""
        event_bus.subscribe(Events.PAYMENT_RECORDED,        self.on_payment_received)
        event_bus.subscribe(Events.GRADES_SUBMITTED,         self.on_grades_submitted)
        event_bus.subscribe(Events.GRADES_APPROVED,          self.on_grades_approved)
        event_bus.subscribe(Events.GRADES_PUBLISHED,         self.on_grades_published)
        event_bus.subscribe(Events.GRADES_RETURNED,          self.on_grades_returned)
        event_bus.subscribe(Events.CHANGE_REQUEST_CREATED,   self.on_change_request)
        event_bus.subscribe(Events.LEAVE_REVIEWED,           self.on_leave_reviewed)
        event_bus.subscribe("report_card.published",         self.on_report_card_published)
        log.info("NotificationService registered %d event handlers", 8)
