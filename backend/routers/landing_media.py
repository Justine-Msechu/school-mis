"""
Landing page media — upload, list, update, delete.

Files are saved to backend/uploads/landing/ and served at /uploads/landing/<filename>.
Public GET endpoints have no auth — anyone viewing the landing page can fetch them.
Write endpoints (POST/PUT/DELETE) require superadmin.
"""

import os
import uuid
import logging
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from backend.deps import require_auth
from backend.core.db import execute, fetch_all, fetch_one

router = APIRouter(tags=["landing-media"])
log    = logging.getLogger(__name__)

UPLOADS_DIR  = Path(__file__).parent.parent / "uploads" / "landing"
ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_BYTES    = 5 * 1024 * 1024  # 5 MB

Usr = Annotated[dict, Depends(require_auth)]


def _super(user: dict):
    if user.get("role") != "superadmin":
        raise HTTPException(403, "Superadmin only")


def _ensure_dir():
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


# ── Public endpoints ──────────────────────────────────────────────────────────

@router.get("")
def list_media(active_only: bool = True):
    """Public — returns media for the landing page."""
    where = "WHERE is_active=1" if active_only else ""
    rows = fetch_all(
        f"SELECT * FROM landing_media {where} ORDER BY sort_order ASC, id ASC"
    )
    return {"items": rows}


# ── Superadmin endpoints ──────────────────────────────────────────────────────

@router.post("", status_code=201)
async def upload_media(
    user:        Usr,
    file:        UploadFile = File(...),
    title:       str        = Form(""),
    description: str        = Form(""),
    media_type:  str        = Form("poster"),   # poster | banner | screenshot
):
    _super(user)
    _ensure_dir()

    if file.content_type not in ALLOWED_MIME:
        raise HTTPException(400, f"Unsupported file type: {file.content_type}. Allowed: JPEG, PNG, WebP, GIF.")

    contents = await file.read()
    if len(contents) > MAX_BYTES:
        raise HTTPException(400, "File too large. Maximum size is 5 MB.")

    ext      = Path(file.filename or "img").suffix.lower() or ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"
    dest     = UPLOADS_DIR / filename

    dest.write_bytes(contents)
    log.info("Uploaded landing media: %s (%s bytes)", filename, len(contents))

    media_id = execute(
        """INSERT INTO landing_media (filename, title, description, media_type, uploaded_by)
           VALUES (%s,%s,%s,%s,%s)""",
        (filename, title.strip() or None, description.strip() or None, media_type, user["id"]),
    )
    row = fetch_one("SELECT * FROM landing_media WHERE id=%s", (media_id,))
    return row


class MediaUpdate(BaseModel):
    title:       str | None = None
    description: str | None = None
    media_type:  str | None = None
    sort_order:  int | None = None
    is_active:   int | None = None


@router.put("/{media_id}")
def update_media(media_id: int, body: MediaUpdate, user: Usr):
    _super(user)
    row = fetch_one("SELECT id FROM landing_media WHERE id=%s", (media_id,))
    if not row:
        raise HTTPException(404, "Not found")

    fields, vals = [], []
    if body.title       is not None: fields.append("title=%s");       vals.append(body.title)
    if body.description is not None: fields.append("description=%s"); vals.append(body.description)
    if body.media_type  is not None: fields.append("media_type=%s");  vals.append(body.media_type)
    if body.sort_order  is not None: fields.append("sort_order=%s");  vals.append(body.sort_order)
    if body.is_active   is not None: fields.append("is_active=%s");   vals.append(body.is_active)

    if fields:
        vals.append(media_id)
        execute(f"UPDATE landing_media SET {', '.join(fields)} WHERE id=%s", vals)

    return fetch_one("SELECT * FROM landing_media WHERE id=%s", (media_id,))


@router.delete("/{media_id}")
def delete_media(media_id: int, user: Usr):
    _super(user)
    row = fetch_one("SELECT filename FROM landing_media WHERE id=%s", (media_id,))
    if not row:
        raise HTTPException(404, "Not found")

    # Delete file from disk
    try:
        (UPLOADS_DIR / row["filename"]).unlink(missing_ok=True)
    except Exception as exc:
        log.warning("Could not delete file %s: %s", row["filename"], exc)

    execute("DELETE FROM landing_media WHERE id=%s", (media_id,))
    return {"ok": True}


# ── Contact form ──────────────────────────────────────────────────────────────

class ContactPayload(BaseModel):
    name:    str
    email:   str
    phone:   str = ""
    school:  str = ""
    message: str

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @staticmethod
    def _check(v: str, field: str, max_len: int = 500) -> str:
        v = v.strip()
        if not v:
            raise ValueError(f"{field} is required")
        if len(v) > max_len:
            raise ValueError(f"{field} is too long")
        return v


@router.post("/contact", status_code=201)
def submit_contact(body: ContactPayload):
    name    = body.name.strip()
    email   = body.email.strip()
    message = body.message.strip()

    if not name or not email or not message:
        raise HTTPException(400, "Name, email, and message are required")
    if "@" not in email:
        raise HTTPException(400, "Invalid email address")

    execute(
        """INSERT INTO contact_inquiries (name, email, phone, school, message)
           VALUES (?,?,?,?,?)""",
        (name, email, body.phone.strip(), body.school.strip(), message),
    )
    log.info("Contact inquiry from %s <%s> — %s", name, email, body.school.strip())
    return {"ok": True}


@router.get("/contact/inquiries")
def list_inquiries(user: Usr):
    from backend.core.security import require_permission
    require_permission(user, "superadmin")
    rows = fetch_all(
        "SELECT * FROM contact_inquiries ORDER BY created_at DESC LIMIT 200",
        (),
    )
    return [dict(r) for r in rows]
