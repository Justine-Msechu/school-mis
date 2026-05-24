from typing import Annotated
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from backend.deps import require_auth, hydrate_session
from services.library_service import library_service
from services.base import ServiceError, PolicyViolation
from database.db import fetch_all, fetch_one, execute

router = APIRouter(tags=["library"])
Usr = Annotated[dict, Depends(require_auth)]


@router.get("/books")
def list_books(user: Usr, search: str = Query(""), category: str = Query(""), available_only: bool = Query(False)):
    hydrate_session(user)
    try:
        books = library_service.search_books(search, category, available_only)
        return [dict(b) for b in books]
    except (ServiceError, PolicyViolation) as e:
        from fastapi import HTTPException
        raise HTTPException(400, str(e))


@router.get("/books/categories")
def get_categories(user: Usr):
    rows = fetch_all("SELECT DISTINCT category FROM library_books WHERE category IS NOT NULL ORDER BY category")
    return [r["category"] for r in rows]


@router.get("/books/{book_id}")
def get_book(book_id: int, user: Usr):
    row = fetch_one("SELECT * FROM library_books WHERE id=?", (book_id,))
    if not row:
        from fastapi import HTTPException
        raise HTTPException(404, "Book not found")
    return dict(row)


class BookPayload(BaseModel):
    title:      str
    author:     str = ""
    isbn:       str = ""
    category:   str = ""
    copies:     int = 1
    shelf_loc:  str = ""
    publisher:  str = ""
    year:       int | None = None


@router.post("/books")
def add_book(body: BookPayload, user: Usr):
    hydrate_session(user)
    try:
        book_id = library_service.add_book(body.model_dump())
        return dict(fetch_one("SELECT * FROM library_books WHERE id=?", (book_id,)))
    except (ServiceError, PolicyViolation) as e:
        from fastapi import HTTPException
        raise HTTPException(400, str(e))


@router.get("/loans")
def get_loans(user: Usr, status: str = Query(None)):
    hydrate_session(user)
    try:
        loans = library_service.get_loans(status=status)
        return [dict(l) for l in loans]
    except (ServiceError, PolicyViolation):
        return []


class CheckoutBody(BaseModel):
    book_id:       int
    borrower_type: str = "student"  # student | staff
    borrower_id:   int
    due_date:      str


@router.post("/checkout")
def checkout(body: CheckoutBody, user: Usr):
    hydrate_session(user)
    try:
        loan_id = library_service.checkout_book(
            body.book_id, body.borrower_type, body.borrower_id, body.due_date
        )
        return {"loan_id": loan_id, "ok": True}
    except (ServiceError, PolicyViolation) as e:
        from fastapi import HTTPException
        raise HTTPException(400, str(e))


@router.post("/return/{loan_id}")
def return_book(loan_id: int, user: Usr):
    hydrate_session(user)
    try:
        result = library_service.return_book(loan_id)
        return result if isinstance(result, dict) else {"ok": True}
    except (ServiceError, PolicyViolation) as e:
        from fastapi import HTTPException
        raise HTTPException(400, str(e))


@router.get("/stats")
def get_stats(user: Usr):
    hydrate_session(user)
    try:
        return library_service.get_stats()
    except Exception:
        return {}
