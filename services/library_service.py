"""Library management service — books, checkout, returns, fines."""
from __future__ import annotations
import datetime
from services.base import BaseService, ServiceError
from database.db import fetch_one, fetch_all, execute, get_config


def _days_overdue(due_date: str) -> int:
    try:
        due = datetime.date.fromisoformat(due_date)
        return max(0, (datetime.date.today() - due).days)
    except Exception:
        return 0


def _calc_fine(due_date: str) -> float:
    days = _days_overdue(due_date)
    if days == 0:
        return 0.0
    rate = float(get_config("library_fine_per_day") or 100)
    return days * rate


class LibraryService(BaseService):

    # ── Catalogue ─────────────────────────────────────────────────────────────

    def add_book(self, data: dict) -> int:
        self._require_permission("library.manage")
        title = (data.get("title") or "").strip()
        if not title:
            raise ServiceError("Book title is required.")
        copies = max(1, int(data.get("total_copies") or 1))
        eid = execute(
            """INSERT INTO library_books
               (title, author, isbn, category, shelf_location,
                publisher, year, total_copies, available_copies, notes)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (title,
             (data.get("author") or "").strip() or None,
             (data.get("isbn") or "").strip() or None,
             data.get("category") or "other",
             (data.get("shelf_location") or "").strip() or None,
             (data.get("publisher") or "").strip() or None,
             (data.get("year") or "").strip() or None,
             copies, copies,
             (data.get("notes") or "").strip() or None),
        )
        self._audit("book_added", "library_books", eid, detail=title)
        return eid

    def update_book(self, book_id: int, data: dict) -> None:
        self._require_permission("library.manage")
        book = fetch_one("SELECT * FROM library_books WHERE id=?", (book_id,))
        if not book:
            raise ServiceError("Book not found.")
        title = (data.get("title") or "").strip()
        if not title:
            raise ServiceError("Book title is required.")
        new_total = max(1, int(data.get("total_copies") or book["total_copies"]))
        delta = new_total - book["total_copies"]
        new_available = max(0, book["available_copies"] + delta)
        execute(
            """UPDATE library_books SET
               title=?, author=?, isbn=?, category=?, shelf_location=?,
               publisher=?, year=?, total_copies=?, available_copies=?, notes=?
               WHERE id=?""",
            (title,
             (data.get("author") or "").strip() or None,
             (data.get("isbn") or "").strip() or None,
             data.get("category") or book["category"],
             (data.get("shelf_location") or "").strip() or None,
             (data.get("publisher") or "").strip() or None,
             (data.get("year") or "").strip() or None,
             new_total, new_available,
             (data.get("notes") or "").strip() or None,
             book_id),
        )
        self._audit("book_updated", "library_books", book_id, detail=title,
                    before=dict(book), after={"title": title, "total_copies": new_total})

    def search_books(self, query: str = "", category: str = "",
                     active_only: bool = True) -> list[dict]:
        self._require_permission("library.view")
        where, params = [], []
        if active_only:
            where.append("b.is_active=1")
        if query:
            where.append("(b.title LIKE ? OR b.author LIKE ? OR b.isbn LIKE ?)")
            q = f"%{query}%"
            params += [q, q, q]
        if category:
            where.append("b.category=?")
            params.append(category)
        clause = ("WHERE " + " AND ".join(where)) if where else ""
        rows = fetch_all(
            f"""SELECT b.*,
                       (SELECT COUNT(*) FROM library_loans l
                        WHERE l.book_id=b.id AND l.status IN ('active','overdue')) AS on_loan
                FROM library_books b {clause} ORDER BY b.title""",
            tuple(params),
        )
        return [dict(r) for r in rows]

    def get_book(self, book_id: int) -> dict:
        self._require_permission("library.view")
        row = fetch_one("SELECT * FROM library_books WHERE id=?", (book_id,))
        if not row:
            raise ServiceError("Book not found.")
        return dict(row)

    def deactivate_book(self, book_id: int) -> None:
        self._require_permission("library.manage")
        execute("UPDATE library_books SET is_active=0 WHERE id=?", (book_id,))
        self._audit("book_deactivated", "library_books", book_id)

    # ── Checkout / Return ────────────────────────────────────────────────────

    def checkout_book(self, book_id: int, borrower_type: str,
                      borrower_id: int, due_date: str, notes: str = "") -> int:
        self._require_permission("library.checkout")
        book = fetch_one("SELECT * FROM library_books WHERE id=?", (book_id,))
        if not book:
            raise ServiceError("Book not found.")
        if not book["is_active"]:
            raise ServiceError("This book is no longer in the catalogue.")
        if book["available_copies"] < 1:
            raise ServiceError(
                f"No copies available — all {book['total_copies']} "
                f"copy/copies are currently on loan."
            )
        if borrower_type == "student":
            br = fetch_one(
                "SELECT first_name||' '||last_name AS name FROM students WHERE id=? AND is_active=1",
                (borrower_id,)
            )
        elif borrower_type == "teacher":
            br = fetch_one(
                "SELECT first_name||' '||last_name AS name FROM teachers WHERE id=? AND is_active=1",
                (borrower_id,)
            )
        else:
            raise ServiceError("Invalid borrower type.")
        if not br:
            raise ServiceError("Borrower not found.")

        issue_date = datetime.date.today().isoformat()
        loan_id = execute(
            """INSERT INTO library_loans
               (book_id, borrower_type, borrower_id, borrower_name,
                issue_date, due_date, status, notes, issued_by)
               VALUES (?,?,?,?,?,?,'active',?,?)""",
            (book_id, borrower_type, borrower_id, br["name"],
             issue_date, due_date, notes or None, self._session.user_id),
        )
        execute(
            "UPDATE library_books SET available_copies=available_copies-1 WHERE id=?",
            (book_id,)
        )
        self._audit("book_checked_out", "library_loans", loan_id,
                    detail=f"'{book['title']}' → {br['name']} (due {due_date})")
        return loan_id

    def return_book(self, loan_id: int, notes: str = "") -> dict:
        """Mark loan returned; compute overdue fine. Returns {fine, overdue_days}."""
        self._require_permission("library.checkout")
        loan = fetch_one("SELECT * FROM library_loans WHERE id=?", (loan_id,))
        if not loan:
            raise ServiceError("Loan record not found.")
        if loan["status"] not in ("active", "overdue"):
            raise ServiceError("This book has already been returned or marked lost.")

        return_date = datetime.date.today().isoformat()
        fine = _calc_fine(loan["due_date"])
        execute(
            """UPDATE library_loans
               SET return_date=?, fine_amount=?, status='returned',
                   returned_to=?, notes=COALESCE(NULLIF(?,''), notes)
               WHERE id=?""",
            (return_date, fine, self._session.user_id, notes or "", loan_id),
        )
        execute(
            "UPDATE library_books SET available_copies=available_copies+1 WHERE id=?",
            (loan["book_id"],)
        )
        self._audit("book_returned", "library_loans", loan_id,
                    detail=f"Fine: TZS {fine:.0f}")
        return {"fine": fine, "overdue_days": _days_overdue(loan["due_date"])}

    def mark_lost(self, loan_id: int) -> None:
        self._require_permission("library.manage")
        loan = fetch_one("SELECT * FROM library_loans WHERE id=?", (loan_id,))
        if not loan:
            raise ServiceError("Loan not found.")
        if loan["status"] == "returned":
            raise ServiceError("Cannot mark a returned book as lost.")
        execute("UPDATE library_loans SET status='lost' WHERE id=?", (loan_id,))
        self._audit("book_marked_lost", "library_loans", loan_id)

    # ── Loan queries ──────────────────────────────────────────────────────────

    def get_loans(self, status: str | None = None,
                  borrower_type: str | None = None) -> list[dict]:
        self._require_permission("library.view")
        where, params = [], []
        if status:
            where.append("l.status=?"); params.append(status)
        if borrower_type:
            where.append("l.borrower_type=?"); params.append(borrower_type)
        clause = ("WHERE " + " AND ".join(where)) if where else ""
        rows = fetch_all(
            f"""SELECT l.*, b.title AS book_title, b.isbn AS book_isbn
                FROM library_loans l
                JOIN library_books b ON b.id=l.book_id
                {clause} ORDER BY l.id DESC""",
            tuple(params),
        )
        today = datetime.date.today().isoformat()
        result = []
        for r in rows:
            d = dict(r)
            if d["status"] in ("active", "overdue"):
                d["overdue_days"] = _days_overdue(d["due_date"])
                d["current_fine"] = _calc_fine(d["due_date"])
                if d["overdue_days"] > 0 and d["status"] == "active":
                    execute(
                        "UPDATE library_loans SET status='overdue' WHERE id=?",
                        (d["id"],)
                    )
                    d["status"] = "overdue"
            else:
                d["overdue_days"] = 0
                d["current_fine"] = d.get("fine_amount") or 0
            result.append(d)
        return result

    def get_overdue_loans(self) -> list[dict]:
        return self.get_loans(status="overdue")

    def get_stats(self) -> dict:
        """Quick summary counts for the dashboard."""
        self._require_permission("library.view")
        total    = fetch_one("SELECT COUNT(*) AS n FROM library_books WHERE is_active=1")
        on_loan  = fetch_one(
            "SELECT COUNT(*) AS n FROM library_loans WHERE status IN ('active','overdue')"
        )
        overdue  = fetch_one(
            "SELECT COUNT(*) AS n FROM library_loans WHERE status='overdue'"
        )
        return {
            "total_books": total["n"] if total else 0,
            "on_loan":     on_loan["n"] if on_loan else 0,
            "overdue":     overdue["n"] if overdue else 0,
        }


library_service = LibraryService()
