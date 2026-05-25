from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from backend.deps import require_auth
from database.db import fetch_all, fetch_one, execute

router = APIRouter(tags=["library"])
Usr = Annotated[dict, Depends(require_auth)]


@router.get("/books")
def list_books(
    user: Usr,
    search: str = Query(""),
    category: str = Query(""),
    available_only: bool = Query(False),
):
    where = ["is_active=1"]
    params: list = []
    if search:
        where.append("(title LIKE ? OR author LIKE ? OR isbn LIKE ?)")
        params += [f"%{search}%", f"%{search}%", f"%{search}%"]
    if category:
        where.append("category=?")
        params.append(category)
    if available_only:
        where.append("available_copies > 0")
    clause = " AND ".join(where)
    rows = fetch_all(f"SELECT * FROM library_books WHERE {clause} ORDER BY title", params)
    return [dict(r) for r in rows]


@router.get("/books/categories")
def get_categories(user: Usr):
    rows = fetch_all("SELECT DISTINCT category FROM library_books WHERE category IS NOT NULL ORDER BY category")
    return [r["category"] for r in rows]


@router.get("/books/{book_id}")
def get_book(book_id: int, user: Usr):
    row = fetch_one("SELECT * FROM library_books WHERE id=?", (book_id,))
    if not row:
        raise HTTPException(404, "Book not found")
    return dict(row)


class BookPayload(BaseModel):
    title:           str
    author:          str | None = None
    isbn:            str | None = None
    category:        str = "other"
    total_copies:    int = 1
    shelf_location:  str | None = None
    publisher:       str | None = None
    year:            str | None = None
    notes:           str | None = None


@router.post("/books")
def add_book(body: BookPayload, user: Usr):
    book_id = execute(
        """INSERT INTO library_books
           (title, author, isbn, category, total_copies, available_copies, shelf_location, publisher, year, notes, is_active)
           VALUES (?,?,?,?,?,?,?,?,?,?,1)""",
        (body.title, body.author, body.isbn, body.category,
         body.total_copies, body.total_copies,
         body.shelf_location, body.publisher, body.year, body.notes),
    )
    return dict(fetch_one("SELECT * FROM library_books WHERE id=?", (book_id,)))


@router.put("/books/{book_id}")
def update_book(book_id: int, body: BookPayload, user: Usr):
    row = fetch_one("SELECT * FROM library_books WHERE id=? AND is_active=1", (book_id,))
    if not row:
        raise HTTPException(404, "Book not found")
    extra_copies = body.total_copies - row["total_copies"]
    new_available = max(0, row["available_copies"] + extra_copies)
    execute(
        """UPDATE library_books SET title=?, author=?, isbn=?, category=?,
           total_copies=?, available_copies=?, shelf_location=?, publisher=?, year=?, notes=?
           WHERE id=?""",
        (body.title, body.author, body.isbn, body.category,
         body.total_copies, new_available,
         body.shelf_location, body.publisher, body.year, body.notes, book_id),
    )
    return dict(fetch_one("SELECT * FROM library_books WHERE id=?", (book_id,)))


@router.get("/loans")
def get_loans(user: Usr, status: str = Query(None), limit: int = Query(100)):
    where = ["1=1"]
    params: list = []
    if status:
        where.append("ll.status=?")
        params.append(status)
    clause = " AND ".join(where)
    rows = fetch_all(
        f"""SELECT ll.*,
               lb.title as book_title,
               CASE WHEN ll.borrower_type='student'
                    THEN (SELECT s.first_name||' '||s.last_name FROM students s WHERE s.id=ll.borrower_id)
                    ELSE (SELECT t.first_name||' '||t.last_name FROM teachers t WHERE t.id=ll.borrower_id)
               END as borrower_name
            FROM library_loans ll
            JOIN library_books lb ON lb.id=ll.book_id
            WHERE {clause}
            ORDER BY ll.issue_date DESC
            LIMIT ?""",
        params + [limit],
    )
    return [dict(r) for r in rows]


class CheckoutBody(BaseModel):
    book_id:       int
    borrower_type: str = "student"
    borrower_id:   int
    due_date:      str
    notes:         str | None = None


@router.post("/checkout")
def checkout(body: CheckoutBody, user: Usr):
    book = fetch_one("SELECT * FROM library_books WHERE id=? AND is_active=1", (body.book_id,))
    if not book:
        raise HTTPException(404, "Book not found")
    if book["available_copies"] <= 0:
        raise HTTPException(400, "No copies available for checkout")
    if body.borrower_type not in ("student", "teacher"):
        raise HTTPException(400, "borrower_type must be 'student' or 'teacher'")

    if body.borrower_type == "student":
        borrower = fetch_one(
            "SELECT first_name||' '||last_name AS name FROM students WHERE id=? AND deleted_at IS NULL",
            (body.borrower_id,),
        )
    else:
        borrower = fetch_one(
            "SELECT first_name||' '||last_name AS name FROM teachers WHERE id=?",
            (body.borrower_id,),
        )
    if not borrower:
        raise HTTPException(404, f"{body.borrower_type.title()} not found")

    loan_id = execute(
        """INSERT INTO library_loans
           (book_id, borrower_type, borrower_id, borrower_name, issue_date, due_date, status, notes, issued_by)
           VALUES (?,?,?,?,date('now'),?,'active',?,?)""",
        (body.book_id, body.borrower_type, body.borrower_id, borrower["name"],
         body.due_date, body.notes, user.get("id")),
    )
    execute(
        "UPDATE library_books SET available_copies = available_copies - 1 WHERE id=?",
        (body.book_id,),
    )
    return {"loan_id": loan_id, "ok": True}


@router.post("/return/{loan_id}")
def return_book(loan_id: int, user: Usr):
    loan = fetch_one("SELECT * FROM library_loans WHERE id=?", (loan_id,))
    if not loan:
        raise HTTPException(404, "Loan not found")
    if loan["status"] == "returned":
        raise HTTPException(400, "Book already returned")
    execute(
        "UPDATE library_loans SET status='returned', return_date=date('now'), returned_to=? WHERE id=?",
        (user.get("id"), loan_id),
    )
    execute(
        "UPDATE library_books SET available_copies = available_copies + 1 WHERE id=?",
        (loan["book_id"],),
    )
    return {"ok": True}


@router.get("/stats")
def get_stats(user: Usr):
    total   = fetch_one("SELECT COUNT(*) as n FROM library_books WHERE is_active=1")
    active  = fetch_one("SELECT COUNT(*) as n FROM library_loans WHERE status='active'")
    overdue = fetch_one(
        "SELECT COUNT(*) as n FROM library_loans WHERE status='active' AND due_date < date('now')"
    )
    return {
        "total_books":   dict(total  or {}).get("n", 0),
        "active_loans":  dict(active or {}).get("n", 0),
        "overdue_loans": dict(overdue or {}).get("n", 0),
    }
