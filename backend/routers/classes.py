from typing import Annotated
from fastapi import APIRouter
from backend.deps import require_auth
from database.db import fetch_all

router = APIRouter(tags=["classes"])

Usr = Annotated[dict, require_auth]


@router.get("")
def list_classes(user: Usr):
    rows = fetch_all("SELECT id, name, level, stream FROM classes ORDER BY name")
    return [dict(r) for r in rows]
