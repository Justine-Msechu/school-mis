from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from backend.deps import require_auth
from database.db import fetch_all, fetch_one, execute

router = APIRouter(tags=["ngo"])
Usr = Annotated[dict, Depends(require_auth)]


# ── NGO CRUD ──────────────────────────────────────────────────────────────────

class NgoPayload(BaseModel):
    name:           str
    contact_person: str = ""
    phone:          str = ""
    email:          str = ""
    address:        str = ""
    website:        str = ""
    notes:          str = ""


@router.get("/ngos")
def list_ngos(user: Usr):
    rows = fetch_all("""
        SELECT n.*,
               COUNT(CASE WHEN sp.is_active=1 THEN 1 END) AS student_count
        FROM ngos n
        LEFT JOIN student_sponsorships sp ON sp.ngo_id = n.id
        WHERE n.is_active = 1
        GROUP BY n.id
        ORDER BY n.name
    """)
    return [dict(r) for r in rows]


@router.post("/ngos")
def create_ngo(body: NgoPayload, user: Usr):
    existing = fetch_one("SELECT id FROM ngos WHERE name=?", (body.name,))
    if existing:
        raise HTTPException(400, f"NGO '{body.name}' already exists")
    ngo_id = execute(
        """INSERT INTO ngos (name, contact_person, phone, email, address, website, notes)
           VALUES (?,?,?,?,?,?,?)""",
        (body.name, body.contact_person or None, body.phone or None,
         body.email or None, body.address or None, body.website or None,
         body.notes or None),
    )
    return dict(fetch_one("SELECT * FROM ngos WHERE id=?", (ngo_id,)))


@router.put("/ngos/{ngo_id}")
def update_ngo(ngo_id: int, body: NgoPayload, user: Usr):
    row = fetch_one("SELECT id FROM ngos WHERE id=? AND is_active=1", (ngo_id,))
    if not row:
        raise HTTPException(404, "NGO not found")
    execute(
        """UPDATE ngos SET name=?, contact_person=?, phone=?, email=?,
           address=?, website=?, notes=? WHERE id=?""",
        (body.name, body.contact_person or None, body.phone or None,
         body.email or None, body.address or None, body.website or None,
         body.notes or None, ngo_id),
    )
    return dict(fetch_one("SELECT * FROM ngos WHERE id=?", (ngo_id,)))


@router.delete("/ngos/{ngo_id}")
def deactivate_ngo(ngo_id: int, user: Usr):
    row = fetch_one("SELECT id FROM ngos WHERE id=? AND is_active=1", (ngo_id,))
    if not row:
        raise HTTPException(404, "NGO not found")
    execute("UPDATE ngos SET is_active=0 WHERE id=?", (ngo_id,))
    return {"ok": True}


# ── Sponsorships ──────────────────────────────────────────────────────────────

class SponsorshipPayload(BaseModel):
    student_id:    int
    support_types: str = ""   # comma-separated: fees,uniform,meals,medical,stationery,transport
    fee_amount:    float = 0
    start_date:    str = ""
    end_date:      str = ""
    notes:         str = ""


STUDENT_SPONSORSHIP_SELECT = """
    SELECT sp.id AS sponsorship_id, sp.support_types, sp.fee_amount,
           sp.start_date, sp.end_date, sp.notes AS sponsorship_notes,
           sp.is_active, sp.created_at,
           s.id AS student_id, s.full_name, s.student_id AS admission_no,
           s.gender, s.date_of_birth,
           c.name AS class_name,
           n.id AS ngo_id, n.name AS ngo_name
    FROM student_sponsorships sp
    JOIN students s ON s.id = sp.student_id
    LEFT JOIN classes c ON c.id = s.class_id
    JOIN ngos n ON n.id = sp.ngo_id
"""


@router.get("/ngos/{ngo_id}/students")
def get_ngo_students(ngo_id: int, user: Usr):
    row = fetch_one("SELECT id FROM ngos WHERE id=? AND is_active=1", (ngo_id,))
    if not row:
        raise HTTPException(404, "NGO not found")
    rows = fetch_all(
        f"{STUDENT_SPONSORSHIP_SELECT} WHERE sp.ngo_id=? AND sp.is_active=1 AND s.is_active=1 ORDER BY s.full_name",
        (ngo_id,),
    )
    return [dict(r) for r in rows]


@router.get("/sponsorships")
def list_sponsorships(user: Usr, ngo_id: Optional[int] = Query(None)):
    where = "sp.is_active=1 AND s.is_active=1"
    params: list = []
    if ngo_id:
        where += " AND sp.ngo_id=?"
        params.append(ngo_id)
    rows = fetch_all(
        f"{STUDENT_SPONSORSHIP_SELECT} WHERE {where} ORDER BY s.full_name",
        params,
    )
    return [dict(r) for r in rows]


@router.post("/ngos/{ngo_id}/students")
def add_sponsorship(ngo_id: int, body: SponsorshipPayload, user: Usr):
    ngo = fetch_one("SELECT id FROM ngos WHERE id=? AND is_active=1", (ngo_id,))
    if not ngo:
        raise HTTPException(404, "NGO not found")
    student = fetch_one("SELECT id FROM students WHERE id=? AND is_active=1", (body.student_id,))
    if not student:
        raise HTTPException(404, "Student not found")
    existing = fetch_one(
        "SELECT id FROM student_sponsorships WHERE student_id=? AND ngo_id=? AND is_active=1",
        (body.student_id, ngo_id),
    )
    if existing:
        raise HTTPException(400, "Student is already sponsored by this NGO")
    sp_id = execute(
        """INSERT INTO student_sponsorships
           (student_id, ngo_id, support_types, fee_amount, start_date, end_date, notes)
           VALUES (?,?,?,?,?,?,?)""",
        (body.student_id, ngo_id, body.support_types or None,
         body.fee_amount or 0,
         body.start_date or None, body.end_date or None, body.notes or None),
    )
    row = fetch_all(
        f"{STUDENT_SPONSORSHIP_SELECT} WHERE sp.id=?", (sp_id,)
    )
    return dict(row[0]) if row else {"ok": True}


@router.put("/sponsorships/{sp_id}")
def update_sponsorship(sp_id: int, body: SponsorshipPayload, user: Usr):
    row = fetch_one("SELECT id FROM student_sponsorships WHERE id=? AND is_active=1", (sp_id,))
    if not row:
        raise HTTPException(404, "Sponsorship not found")
    execute(
        """UPDATE student_sponsorships
           SET support_types=?, fee_amount=?, start_date=?, end_date=?, notes=?
           WHERE id=?""",
        (body.support_types or None, body.fee_amount or 0,
         body.start_date or None, body.end_date or None, body.notes or None,
         sp_id),
    )
    return {"ok": True}


@router.delete("/sponsorships/{sp_id}")
def remove_sponsorship(sp_id: int, user: Usr):
    row = fetch_one("SELECT id FROM student_sponsorships WHERE id=? AND is_active=1", (sp_id,))
    if not row:
        raise HTTPException(404, "Sponsorship not found")
    execute("UPDATE student_sponsorships SET is_active=0 WHERE id=?", (sp_id,))
    return {"ok": True}


# ── NGO Report ────────────────────────────────────────────────────────────────

@router.get("/ngos/{ngo_id}/report")
def ngo_report(ngo_id: int, user: Usr):
    ngo = fetch_one("SELECT * FROM ngos WHERE id=? AND is_active=1", (ngo_id,))
    if not ngo:
        raise HTTPException(404, "NGO not found")

    rows = fetch_all("""
        SELECT
            s.id          AS student_id,
            s.full_name,
            s.student_id  AS admission_no,
            c.name        AS class_name,
            sp.support_types,
            sp.fee_amount,
            sp.start_date,
            COALESCE(
                (SELECT ROUND(100.0 * SUM(CASE WHEN a.status='present' THEN 1 ELSE 0 END)
                              / NULLIF(COUNT(*), 0), 1)
                 FROM attendance a WHERE a.student_id = s.id),
                0
            ) AS attendance_pct,
            COALESCE(
                (SELECT SUM(sb.amount_due)
                 FROM student_bills sb WHERE sb.student_id = s.id),
                0
            ) AS total_billed,
            COALESCE(
                (SELECT SUM(sb.amount_paid)
                 FROM student_bills sb WHERE sb.student_id = s.id),
                0
            ) AS total_paid
        FROM student_sponsorships sp
        JOIN students s ON s.id = sp.student_id AND s.is_active = 1
        LEFT JOIN classes c ON c.id = s.class_id
        WHERE sp.ngo_id = ? AND sp.is_active = 1
        ORDER BY s.full_name
    """, (ngo_id,))

    students = [dict(r) for r in rows]
    for st in students:
        st["balance"] = round(st["total_billed"] - st["total_paid"], 2)

    return {
        "ngo": dict(ngo),
        "students": students,
        "summary": {
            "total_beneficiaries": len(students),
            "avg_attendance_pct":  round(
                sum(s["attendance_pct"] for s in students) / len(students), 1
            ) if students else 0,
            "total_billed":  sum(s["total_billed"]  for s in students),
            "total_paid":    sum(s["total_paid"]    for s in students),
            "total_balance": sum(s["balance"]       for s in students),
        },
    }
