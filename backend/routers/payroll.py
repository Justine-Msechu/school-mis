from backend.deps import rate_limit
from fastapi import Depends
"""Payroll router — salary configuration, payroll runs, payslips, reports."""

from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from backend.deps import require_auth
from backend.core.db import _get_conn
from backend.core.security import require_permission
from backend.services.payroll_service import PayrollService
from database.db import fetch_all, fetch_one

router = APIRouter(tags=["payroll"], dependencies=[Depends(rate_limit(max_calls=60, window_secs=60, scope="payroll"))])
Usr = Annotated[dict, Depends(require_auth)]


def _svc() -> PayrollService:
    return PayrollService(_get_conn())


# ── Staff / salary list ────────────────────────────────────────────────────────

@router.get("/staff")
def list_staff(user: Usr, search: str = Query("")):
    require_permission(user, "payroll.view")
    params: list = []
    where = ["t.deleted_at IS NULL", "t.is_active = 1"]
    if search:
        where.append("(t.first_name || ' ' || t.last_name LIKE ? OR t.employee_no LIKE ?)")
        params += [f"%{search}%", f"%{search}%"]
    rows = fetch_all(
        f"""SELECT t.id, t.first_name, t.last_name, t.employee_no, t.subject_specialization,
                   psc.basic_salary, psc.housing_allow, psc.transport_allow, psc.other_allow,
                   psc.loan_deduction, psc.loan_board, psc.notes
            FROM teachers t
            LEFT JOIN payroll_salary_config psc ON psc.teacher_id = t.id
            WHERE {' AND '.join(where)}
            ORDER BY t.last_name, t.first_name""",
        params,
    )
    return [dict(r) for r in rows]


@router.get("/staff/{teacher_id}/history")
def staff_history(teacher_id: int, user: Usr):
    """All payslips for one employee across all runs."""
    require_permission(user, "payroll.view")
    t = fetch_one("SELECT id FROM teachers WHERE id=? AND deleted_at IS NULL", (teacher_id,))
    if not t:
        raise HTTPException(404, "Teacher not found")
    rows = fetch_all(
        """SELECT pi.*, pr.label AS run_label, pr.status AS run_status,
                  pr.month, pr.year
           FROM payroll_items pi
           JOIN payroll_runs pr ON pr.id = pi.run_id
           WHERE pi.teacher_id=?
           ORDER BY pr.year DESC, pr.month DESC""",
        (teacher_id,),
    )
    return [dict(r) for r in rows]


# ── Salary config ─────────────────────────────────────────────────────────────

class SalaryConfigBody(BaseModel):
    basic_salary:    float = 0
    housing_allow:   float = 0
    transport_allow: float = 0
    other_allow:     float = 0
    loan_deduction:  float = 0
    loan_board:      bool  = False
    notes:           str   = ""


@router.put("/staff/{teacher_id}/salary")
def set_salary(teacher_id: int, body: SalaryConfigBody, user: Usr):
    require_permission(user, "payroll.manage")
    t = fetch_one("SELECT id FROM teachers WHERE id=? AND deleted_at IS NULL", (teacher_id,))
    if not t:
        raise HTTPException(404, "Teacher not found")
    cfg = _svc().upsert_salary_config(teacher_id, body.model_dump(), actor_id=user["id"])
    return cfg


# ── Payroll runs ──────────────────────────────────────────────────────────────

@router.get("/runs")
def list_runs(user: Usr):
    require_permission(user, "payroll.view")
    rows = fetch_all(
        """SELECT pr.*,
                  (SELECT COUNT(*) FROM payroll_items pi WHERE pi.run_id = pr.id) AS employee_count,
                  (SELECT SUM(net_pay) FROM payroll_items pi WHERE pi.run_id = pr.id) AS total_net,
                  (SELECT SUM(gross_pay) FROM payroll_items pi WHERE pi.run_id = pr.id) AS total_gross
           FROM payroll_runs pr
           ORDER BY pr.year DESC, pr.month DESC"""
    )
    return [dict(r) for r in rows]


class CreateRunBody(BaseModel):
    month: int
    year:  int


@router.post("/runs")
def create_run(body: CreateRunBody, user: Usr):
    require_permission(user, "payroll.manage")
    if not (1 <= body.month <= 12):
        raise HTTPException(400, "Month must be 1–12")
    try:
        run = _svc().create_run(body.month, body.year, actor_id=user["id"])
        return run
    except Exception as e:
        raise HTTPException(400, str(e))


@router.delete("/runs/{run_id}")
def delete_run(run_id: int, user: Usr):
    require_permission(user, "payroll.manage")
    try:
        _svc().delete_run(run_id, actor_id=user["id"])
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/runs/{run_id}/reopen")
def reopen_run(run_id: int, user: Usr):
    require_permission(user, "payroll.manage")
    try:
        _svc().reopen_run(run_id, actor_id=user["id"])
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/runs/{run_id}/compute")
def compute_run(run_id: int, user: Usr):
    require_permission(user, "payroll.manage")
    try:
        n = _svc().compute_run(run_id, actor_id=user["id"])
        return {"computed": n}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/runs/{run_id}/finalize")
def finalize_run(run_id: int, user: Usr):
    require_permission(user, "payroll.manage")
    try:
        _svc().finalize_run(run_id, actor_id=user["id"])
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/runs/{run_id}/approve")
def approve_run(run_id: int, user: Usr):
    require_permission(user, "payroll.approve")
    try:
        _svc().approve_run(run_id, actor_id=user["id"])
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(400, str(e))


# ── Pro-rating ────────────────────────────────────────────────────────────────

class ProrateBody(BaseModel):
    prorate_pct: float


@router.patch("/runs/{run_id}/items/{teacher_id}")
def update_prorate(run_id: int, teacher_id: int, body: ProrateBody, user: Usr):
    require_permission(user, "payroll.manage")
    if not (0 < body.prorate_pct <= 100):
        raise HTTPException(400, "prorate_pct must be between 1 and 100")
    try:
        _svc().update_prorate(run_id, teacher_id, body.prorate_pct, actor_id=user["id"])
        row = fetch_one(
            """SELECT pi.*, t.first_name, t.last_name, t.employee_no
               FROM payroll_items pi JOIN teachers t ON t.id=pi.teacher_id
               WHERE pi.run_id=? AND pi.teacher_id=?""",
            (run_id, teacher_id),
        )
        return dict(row)
    except ValueError as e:
        raise HTTPException(400, str(e))


# ── Payroll items (payslips) ───────────────────────────────────────────────────

@router.get("/runs/{run_id}/items")
def get_run_items(run_id: int, user: Usr):
    require_permission(user, "payroll.view")
    run = fetch_one("SELECT * FROM payroll_runs WHERE id=?", (run_id,))
    if not run:
        raise HTTPException(404, "Payroll run not found")
    rows = fetch_all(
        """SELECT pi.*,
                  t.first_name, t.last_name, t.employee_no, t.subject_specialization
           FROM payroll_items pi
           JOIN teachers t ON t.id = pi.teacher_id
           WHERE pi.run_id=?
           ORDER BY t.last_name, t.first_name""",
        (run_id,),
    )
    return {
        "run": dict(run),
        "items": [dict(r) for r in rows],
    }


@router.get("/runs/{run_id}/items/{teacher_id}")
def get_payslip(run_id: int, teacher_id: int, user: Usr):
    require_permission(user, "payroll.view")
    run = fetch_one("SELECT * FROM payroll_runs WHERE id=?", (run_id,))
    item = fetch_one(
        """SELECT pi.*, t.first_name, t.last_name, t.employee_no, t.subject_specialization
           FROM payroll_items pi
           JOIN teachers t ON t.id = pi.teacher_id
           WHERE pi.run_id=? AND pi.teacher_id=?""",
        (run_id, teacher_id),
    )
    if not item:
        raise HTTPException(404, "Payslip not found")
    return {"run": dict(run), "item": dict(item)}


# ── Year-to-Date ──────────────────────────────────────────────────────────────

@router.get("/ytd")
def ytd_summary(user: Usr, year: int = Query(...)):
    """Year-to-date totals per employee for finalized/approved runs in the given year."""
    require_permission(user, "payroll.view")
    rows = fetch_all(
        """SELECT t.id AS teacher_id, t.first_name, t.last_name, t.employee_no,
                  COUNT(pi.id) AS months_paid,
                  SUM(pi.gross_pay) AS ytd_gross,
                  SUM(pi.nssf_employee) AS ytd_nssf_employee,
                  SUM(pi.nssf_employer) AS ytd_nssf_employer,
                  SUM(pi.paye) AS ytd_paye,
                  SUM(pi.loan_deduction) AS ytd_loan,
                  SUM(pi.loan_board) AS ytd_loan_board,
                  SUM(pi.total_deductions) AS ytd_deductions,
                  SUM(pi.net_pay) AS ytd_net
           FROM payroll_items pi
           JOIN payroll_runs pr ON pr.id = pi.run_id
           JOIN teachers t ON t.id = pi.teacher_id
           WHERE pr.year=? AND pr.status IN ('finalized','approved')
           GROUP BY pi.teacher_id
           ORDER BY t.last_name, t.first_name""",
        (year,),
    )
    return [dict(r) for r in rows]


# ── Audit log ─────────────────────────────────────────────────────────────────

@router.get("/runs/{run_id}/log")
def run_audit_log(run_id: int, user: Usr):
    require_permission(user, "payroll.view")
    rows = fetch_all(
        """SELECT pal.*, u.full_name AS actor_name
           FROM payroll_audit_log pal
           LEFT JOIN users u ON u.id = pal.actor_id
           WHERE pal.run_id=?
           ORDER BY pal.created_at""",
        (run_id,),
    )
    return [dict(r) for r in rows]
