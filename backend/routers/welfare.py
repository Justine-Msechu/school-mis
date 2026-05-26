from typing import Annotated
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from backend.deps import require_auth
from database.db import fetch_all, fetch_one, execute

router = APIRouter(tags=["welfare"])
Usr = Annotated[dict, Depends(require_auth)]

_CATEGORIES = ("orphan", "half_orphan", "sponsored", "vulnerable")
_SUPPORT_TYPES = ("full_fees", "partial", "non_financial")
_REASONS = ("grief", "abuse", "dropout_risk", "behaviour", "family_issues", "other")
_INCIDENT_TYPES = ("absence_risk", "suspected_abuse", "behaviour_change", "hunger", "loss_of_parent", "other")
_ITEM_TYPES = ("uniform", "meals", "stationery", "sanitary", "books", "shoes", "other")


# ── Welfare Records (background categories) ───────────────────────────────────

@router.get("/records")
def get_records(
    user: Usr,
    student_id: int  = Query(None),
    category:   str  = Query(None),
    verified:   bool = Query(None),
    limit:      int  = Query(50),
):
    where = ["1=1"]
    params: list = []
    if student_id:
        where.append("wr.student_id=?"); params.append(student_id)
    if category:
        where.append("wr.category=?"); params.append(category)
    if verified is not None:
        where.append("wr.verified=?"); params.append(1 if verified else 0)
    params.append(limit)
    rows = fetch_all(
        f"""SELECT wr.*, (s.first_name || ' ' || s.last_name) AS student_name, s.admission_no
            FROM welfare_records wr
            JOIN students s ON s.id = wr.student_id
            WHERE {' AND '.join(where)}
            ORDER BY wr.created_at DESC LIMIT ?""",
        params,
    )
    return [dict(r) for r in rows]


class WelfarePayload(BaseModel):
    student_id:   int
    category:     str
    support_type: str = "non_financial"
    sponsor_name: str = ""
    sponsor_org:  str = ""
    notes:        str = ""


def _sync_student_category(student_id: int, welfare_category: str):
    mapped = "orphan" if welfare_category in ("orphan", "half_orphan") else \
             "sponsored" if welfare_category == "sponsored" else "regular"
    execute("UPDATE students SET student_category=? WHERE id=?", (mapped, student_id))


@router.post("/records")
def register_record(body: WelfarePayload, user: Usr):
    if body.category not in _CATEGORIES:
        raise HTTPException(400, f"category must be one of {_CATEGORIES}")
    student = fetch_one("SELECT id FROM students WHERE id=? AND deleted_at IS NULL", (body.student_id,))
    if not student:
        raise HTTPException(404, "Student not found")
    existing = fetch_one(
        "SELECT id FROM welfare_records WHERE student_id=? AND is_current=1",
        (body.student_id,),
    )
    if existing:
        execute(
            "UPDATE welfare_records SET is_current=0, superseded_at=datetime('now') WHERE id=?",
            (existing["id"],),
        )
    wr_id = execute(
        """INSERT INTO welfare_records
           (student_id, category, is_current, support_type, sponsor_name, sponsor_org, notes)
           VALUES (?,?,1,?,?,?,?)""",
        (body.student_id, body.category, body.support_type,
         body.sponsor_name, body.sponsor_org, body.notes),
    )
    _sync_student_category(body.student_id, body.category)
    return {"id": wr_id, "ok": True}


@router.post("/records/{wr_id}/verify")
def verify_record(wr_id: int, user: Usr):
    row = fetch_one("SELECT id FROM welfare_records WHERE id=?", (wr_id,))
    if not row:
        raise HTTPException(404, "Welfare record not found")
    execute(
        "UPDATE welfare_records SET verified=1, verified_by=?, verified_date=date('now') WHERE id=?",
        (user.get("id"), wr_id),
    )
    return {"ok": True}


@router.get("/categories")
def get_categories(user: Usr):
    return list(_CATEGORIES)


# ── Counseling Sessions ───────────────────────────────────────────────────────

@router.get("/counseling")
def get_counseling(
    user: Usr,
    student_id: int = Query(None),
    limit:      int = Query(100),
):
    where = ["1=1"]
    params: list = []
    if student_id:
        where.append("wc.student_id=?"); params.append(student_id)
    params.append(limit)
    rows = fetch_all(
        f"""SELECT wc.*, (s.first_name||' '||s.last_name) AS student_name, s.admission_no,
                   (u.first_name||' '||u.last_name) AS counselor_name
            FROM welfare_counseling wc
            JOIN students s ON s.id = wc.student_id
            LEFT JOIN users u ON u.id = wc.counselor_id
            WHERE {' AND '.join(where)}
            ORDER BY wc.session_date DESC LIMIT ?""",
        params,
    )
    return [dict(r) for r in rows]


class CounselingPayload(BaseModel):
    student_id:     int
    session_date:   str
    reason:         str
    notes:          str = ""
    follow_up_date: str | None = None


@router.post("/counseling")
def add_counseling(body: CounselingPayload, user: Usr):
    if body.reason not in _REASONS:
        raise HTTPException(400, f"reason must be one of {_REASONS}")
    student = fetch_one("SELECT id FROM students WHERE id=? AND deleted_at IS NULL", (body.student_id,))
    if not student:
        raise HTTPException(404, "Student not found")
    rec_id = execute(
        """INSERT INTO welfare_counseling
           (student_id, session_date, reason, notes, counselor_id, follow_up_date)
           VALUES (?,?,?,?,?,?)""",
        (body.student_id, body.session_date, body.reason,
         body.notes, user.get("id"), body.follow_up_date),
    )
    return {"id": rec_id, "ok": True}


@router.post("/counseling/{rec_id}/follow-up-done")
def mark_followup_done(rec_id: int, user: Usr):
    row = fetch_one("SELECT id FROM welfare_counseling WHERE id=?", (rec_id,))
    if not row:
        raise HTTPException(404, "Counseling record not found")
    execute("UPDATE welfare_counseling SET follow_up_done=1 WHERE id=?", (rec_id,))
    return {"ok": True}


# ── Home Visits ───────────────────────────────────────────────────────────────

@router.get("/visits")
def get_visits(
    user: Usr,
    student_id: int = Query(None),
    limit:      int = Query(100),
):
    where = ["1=1"]
    params: list = []
    if student_id:
        where.append("wv.student_id=?"); params.append(student_id)
    params.append(limit)
    rows = fetch_all(
        f"""SELECT wv.*, (s.first_name||' '||s.last_name) AS student_name, s.admission_no,
                   (u.first_name||' '||u.last_name) AS officer_name
            FROM welfare_visits wv
            JOIN students s ON s.id = wv.student_id
            LEFT JOIN users u ON u.id = wv.officer_id
            WHERE {' AND '.join(where)}
            ORDER BY wv.visit_date DESC LIMIT ?""",
        params,
    )
    return [dict(r) for r in rows]


class VisitPayload(BaseModel):
    student_id:      int
    visit_date:      str
    address_visited: str = ""
    findings:        str
    action_taken:    str = ""
    next_visit_date: str | None = None


@router.post("/visits")
def add_visit(body: VisitPayload, user: Usr):
    student = fetch_one("SELECT id FROM students WHERE id=? AND deleted_at IS NULL", (body.student_id,))
    if not student:
        raise HTTPException(404, "Student not found")
    rec_id = execute(
        """INSERT INTO welfare_visits
           (student_id, visit_date, address_visited, findings, action_taken, next_visit_date, officer_id)
           VALUES (?,?,?,?,?,?,?)""",
        (body.student_id, body.visit_date, body.address_visited,
         body.findings, body.action_taken, body.next_visit_date, user.get("id")),
    )
    return {"id": rec_id, "ok": True}


# ── In-Kind Distributions ─────────────────────────────────────────────────────

@router.get("/distributions")
def get_distributions(
    user: Usr,
    student_id: int = Query(None),
    item_type:  str = Query(None),
    limit:      int = Query(100),
):
    where = ["1=1"]
    params: list = []
    if student_id:
        where.append("wd.student_id=?"); params.append(student_id)
    if item_type:
        where.append("wd.item_type=?"); params.append(item_type)
    params.append(limit)
    rows = fetch_all(
        f"""SELECT wd.*, (s.first_name||' '||s.last_name) AS student_name, s.admission_no,
                   (u.first_name||' '||u.last_name) AS distributed_by_name
            FROM welfare_distributions wd
            JOIN students s ON s.id = wd.student_id
            LEFT JOIN users u ON u.id = wd.distributed_by
            WHERE {' AND '.join(where)}
            ORDER BY wd.distribution_date DESC LIMIT ?""",
        params,
    )
    return [dict(r) for r in rows]


@router.get("/distributions/summary")
def distributions_summary(user: Usr):
    rows = fetch_all(
        """SELECT item_type, COUNT(*) as count, SUM(quantity) as total_qty
           FROM welfare_distributions
           GROUP BY item_type ORDER BY count DESC""",
        [],
    )
    return [dict(r) for r in rows]


class DistributionPayload(BaseModel):
    student_id:        int
    item_type:         str
    quantity:          float = 1
    unit:              str   = "pcs"
    distribution_date: str
    notes:             str   = ""


@router.post("/distributions")
def add_distribution(body: DistributionPayload, user: Usr):
    if body.item_type not in _ITEM_TYPES:
        raise HTTPException(400, f"item_type must be one of {_ITEM_TYPES}")
    student = fetch_one("SELECT id FROM students WHERE id=? AND deleted_at IS NULL", (body.student_id,))
    if not student:
        raise HTTPException(404, "Student not found")
    rec_id = execute(
        """INSERT INTO welfare_distributions
           (student_id, item_type, quantity, unit, distribution_date, notes, distributed_by)
           VALUES (?,?,?,?,?,?,?)""",
        (body.student_id, body.item_type, body.quantity,
         body.unit, body.distribution_date, body.notes, user.get("id")),
    )
    return {"id": rec_id, "ok": True}


# ── Incidents & At-Risk Flags ─────────────────────────────────────────────────

@router.get("/incidents")
def get_incidents(
    user: Usr,
    student_id: int  = Query(None),
    resolved:   bool = Query(None),
    limit:      int  = Query(100),
):
    where = ["1=1"]
    params: list = []
    if student_id:
        where.append("wi.student_id=?"); params.append(student_id)
    if resolved is not None:
        where.append("wi.resolved=?"); params.append(1 if resolved else 0)
    params.append(limit)
    rows = fetch_all(
        f"""SELECT wi.*, (s.first_name||' '||s.last_name) AS student_name, s.admission_no,
                   (u.first_name||' '||u.last_name) AS reporter_name
            FROM welfare_incidents wi
            JOIN students s ON s.id = wi.student_id
            LEFT JOIN users u ON u.id = wi.reported_by
            WHERE {' AND '.join(where)}
            ORDER BY wi.reported_date DESC LIMIT ?""",
        params,
    )
    return [dict(r) for r in rows]


class IncidentPayload(BaseModel):
    student_id:    int
    incident_type: str
    reported_date: str
    description:   str
    action_taken:  str = ""


@router.post("/incidents")
def add_incident(body: IncidentPayload, user: Usr):
    if body.incident_type not in _INCIDENT_TYPES:
        raise HTTPException(400, f"incident_type must be one of {_INCIDENT_TYPES}")
    student = fetch_one("SELECT id FROM students WHERE id=? AND deleted_at IS NULL", (body.student_id,))
    if not student:
        raise HTTPException(404, "Student not found")
    rec_id = execute(
        """INSERT INTO welfare_incidents
           (student_id, incident_type, reported_date, description, action_taken, reported_by)
           VALUES (?,?,?,?,?,?)""",
        (body.student_id, body.incident_type, body.reported_date,
         body.description, body.action_taken, user.get("id")),
    )
    return {"id": rec_id, "ok": True}


@router.post("/incidents/{inc_id}/resolve")
def resolve_incident(inc_id: int, user: Usr):
    row = fetch_one("SELECT id FROM welfare_incidents WHERE id=?", (inc_id,))
    if not row:
        raise HTTPException(404, "Incident not found")
    execute(
        "UPDATE welfare_incidents SET resolved=1, resolved_date=date('now') WHERE id=?",
        (inc_id,),
    )
    return {"ok": True}
