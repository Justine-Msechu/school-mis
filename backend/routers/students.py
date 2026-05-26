from typing import Annotated
import math
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from backend.deps import require_auth
from backend.core.id_generator import next_admission_no
from database.db import fetch_all, fetch_one, execute

from backend.deps import rate_limit
from fastapi import Depends
router = APIRouter(tags=["students"], dependencies=[Depends(rate_limit(max_calls=200, window_secs=60, scope="students"))])
Usr = Annotated[dict, Depends(require_auth)]


@router.get("/next-admission-no")
def preview_admission_no(user: Usr):
    """Return what the next auto-generated admission number will look like."""
    from database.db import fetch_one as _fo
    row = _fo("SELECT value FROM school_config WHERE key='student_adm_seq'")
    import datetime
    seq = (int(row["value"]) if row else 0) + 1
    year = datetime.date.today().year
    return {"admission_no": f"ADM/{year}/{seq:04d}"}


def _audit(user_id: int, action: str, record_id: int, detail: str):
    try:
        execute(
            "INSERT INTO audit_log (user_id, action, table_name, record_id, detail) VALUES (?,?,?,?,?)",
            (user_id, action, "students", record_id, detail),
        )
    except Exception:
        pass


def _sync_guardian(student_id: int, parent_name: str, parent_phone: str | None, parent_email: str | None):
    """When parent contact data is present, keep the guardians table in sync."""
    if not parent_name:
        return
    existing_link = fetch_one(
        "SELECT gs.guardian_id FROM guardian_students gs WHERE gs.student_id=? AND gs.is_primary=1",
        (student_id,),
    )
    if existing_link:
        execute(
            "UPDATE guardians SET full_name=?, phone=?, email=? WHERE id=?",
            (parent_name, parent_phone, parent_email, existing_link["guardian_id"]),
        )
    else:
        gid = execute(
            """INSERT INTO guardians (full_name, phone, email, relationship, is_emergency_contact)
               VALUES (?, ?, ?, 'guardian', 1)""",
            (parent_name, parent_phone, parent_email),
        )
        execute(
            "INSERT OR IGNORE INTO guardian_students (guardian_id, student_id, is_primary) VALUES (?,?,1)",
            (gid, student_id),
        )


@router.get("")
def list_students(
    user:      Usr,
    search:    str  = Query(""),
    class_id:  int  = Query(None),
    is_active: bool = Query(True),
    page:      int  = Query(1, ge=1),
    per_page:  int  = Query(30, ge=1, le=100),
):
    where  = ["s.deleted_at IS NULL", "s.is_active = ?"]
    params: list = [1 if is_active else 0]

    if search:
        where.append("(s.first_name || ' ' || s.last_name LIKE ? OR s.admission_no LIKE ?)")
        params += [f"%{search}%", f"%{search}%"]
    if class_id:
        where.append("s.class_id = ?")
        params.append(class_id)

    where_clause = " AND ".join(where)
    total_row = fetch_one(f"SELECT COUNT(*) as n FROM students s WHERE {where_clause}", params)
    total = dict(total_row).get("n", 0) if total_row else 0

    offset = (page - 1) * per_page
    rows = fetch_all(
        f"""SELECT s.*, c.name as class_name
            FROM students s
            LEFT JOIN classes c ON c.id = s.class_id
            WHERE {where_clause}
            ORDER BY s.last_name, s.first_name
            LIMIT ? OFFSET ?""",
        params + [per_page, offset],
    )
    return {
        "items":    [dict(r) for r in rows],
        "total":    total,
        "page":     page,
        "per_page": per_page,
        "pages":    math.ceil(total / per_page) if total else 1,
    }


class StudentPayload(BaseModel):
    first_name:     str
    last_name:      str
    admission_no:   str | None = None   # auto-generated if omitted
    gender:         str = "Male"
    class_id:       int | None = None
    date_of_birth:  str | None = None
    parent_name:    str | None = None
    parent_phone:   str | None = None
    parent_email:   str | None = None
    address:        str | None = None
    notes:          str | None = None
    student_category:    str = "regular"  # background: regular|orphan|vulnerable|staff_child
    student_type:        str = "Day"      # Day | Boarding
    sponsorship_type:    str = "none"     # none | ngo | individual
    sponsor_ngo_id:      int | None = None
    sponsor_name:        str | None = None
    sponsor_phone:       str | None = None
    sponsor_relationship: str | None = None


@router.post("")
def create_student(body: StudentPayload, user: Usr):
    adm_no = (body.admission_no or "").strip() or next_admission_no()
    existing = fetch_one("SELECT id FROM students WHERE admission_no=?", (adm_no,))
    if existing:
        raise HTTPException(400, f"Admission number '{adm_no}' already exists")
    row_id = execute(
        """INSERT INTO students
           (first_name, last_name, admission_no, gender, class_id, date_of_birth,
            parent_name, parent_phone, parent_email, address, notes,
            student_category, student_type,
            sponsorship_type, sponsor_ngo_id, sponsor_name, sponsor_phone, sponsor_relationship,
            is_active)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1)""",
        (body.first_name, body.last_name, adm_no, body.gender, body.class_id,
         body.date_of_birth, body.parent_name, body.parent_phone, body.parent_email,
         body.address, body.notes, body.student_category, body.student_type,
         body.sponsorship_type,
         body.sponsor_ngo_id if body.sponsorship_type == "ngo" else None,
         body.sponsor_name if body.sponsorship_type == "individual" else None,
         body.sponsor_phone if body.sponsorship_type == "individual" else None,
         body.sponsor_relationship if body.sponsorship_type == "individual" else None),
    )
    _sync_guardian(row_id, body.parent_name, body.parent_phone, body.parent_email)
    _audit(user["id"], "student_create", row_id, f"Created student {body.first_name} {body.last_name} ({adm_no})")
    row = fetch_one("SELECT * FROM students WHERE id=?", (row_id,))
    return dict(row)


@router.put("/{student_id}")
def update_student(student_id: int, body: StudentPayload, user: Usr):
    before = fetch_one("SELECT * FROM students WHERE id=? AND deleted_at IS NULL", (student_id,))
    if not before:
        raise HTTPException(404, "Student not found")
    adm_no = (body.admission_no or "").strip() or before["admission_no"]
    dup = fetch_one(
        "SELECT id FROM students WHERE admission_no=? AND id != ?",
        (adm_no, student_id),
    )
    if dup:
        raise HTTPException(400, f"Admission number '{adm_no}' already used by another student")
    execute(
        """UPDATE students SET first_name=?, last_name=?, admission_no=?, gender=?,
           class_id=?, date_of_birth=?, parent_name=?, parent_phone=?, parent_email=?,
           address=?, notes=?, student_category=?, student_type=?,
           sponsorship_type=?, sponsor_ngo_id=?, sponsor_name=?, sponsor_phone=?, sponsor_relationship=?
           WHERE id=?""",
        (body.first_name, body.last_name, adm_no, body.gender, body.class_id,
         body.date_of_birth, body.parent_name, body.parent_phone, body.parent_email,
         body.address, body.notes, body.student_category, body.student_type,
         body.sponsorship_type,
         body.sponsor_ngo_id if body.sponsorship_type == "ngo" else None,
         body.sponsor_name if body.sponsorship_type == "individual" else None,
         body.sponsor_phone if body.sponsorship_type == "individual" else None,
         body.sponsor_relationship if body.sponsorship_type == "individual" else None,
         student_id),
    )
    _sync_guardian(student_id, body.parent_name, body.parent_phone, body.parent_email)
    _audit(user["id"], "student_update", student_id, f"Updated student {body.first_name} {body.last_name}")
    row = fetch_one("SELECT * FROM students WHERE id=?", (student_id,))
    return dict(row)


@router.delete("/{student_id}")
def deactivate_student(student_id: int, user: Usr):
    row = fetch_one("SELECT id, first_name, last_name FROM students WHERE id=? AND deleted_at IS NULL", (student_id,))
    if not row:
        raise HTTPException(404, "Student not found")
    execute(
        "UPDATE students SET is_active=0, deleted_at=datetime('now') WHERE id=?",
        (student_id,),
    )
    _audit(user["id"], "student_delete", student_id,
           f"Deactivated {row['first_name']} {row['last_name']}")
    return {"ok": True}
