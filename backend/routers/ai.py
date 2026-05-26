"""
AI chat assistant — natural language access to school data via Claude tool use.

Requires ANTHROPIC_API_KEY environment variable.
Model: claude-haiku-4-5-20251001 (fast, cost-effective).
"""

import json
import os
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.deps import rate_limit
from database.db import fetch_all, fetch_one

router = APIRouter(tags=["ai"])
Usr = Annotated[dict, Depends(rate_limit(max_calls=60, window_secs=3600, scope="ai"))]

MODEL = "claude-haiku-4-5-20251001"

# ── Tool definitions ────────────────────────────────────────────────────────────

TOOLS = [
    {
        "name": "get_school_summary",
        "description": "Get overall school statistics: total active students, teachers, classes, and today's attendance rate.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "search_students",
        "description": "Search for students by name or class. Returns names, admission numbers, class, and status.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name":       {"type": "string",  "description": "Part of student name to search"},
                "class_name": {"type": "string",  "description": "Class name, e.g. 'Class 4A'"},
                "inactive":   {"type": "boolean", "description": "Include inactive students"},
                "limit":      {"type": "integer", "description": "Max results (default 20)"},
            },
        },
    },
    {
        "name": "get_attendance_report",
        "description": "Get attendance statistics by class and date range. Returns present/absent counts and percentage.",
        "input_schema": {
            "type": "object",
            "properties": {
                "class_name": {"type": "string", "description": "Filter by class name"},
                "date_from":  {"type": "string", "description": "Start date YYYY-MM-DD (default today)"},
                "date_to":    {"type": "string", "description": "End date YYYY-MM-DD (default today)"},
            },
        },
    },
    {
        "name": "get_fee_summary",
        "description": "Get fee collection summary: total collected per class or overall.",
        "input_schema": {
            "type": "object",
            "properties": {
                "class_name": {"type": "string", "description": "Filter by class"},
            },
        },
    },
    {
        "name": "get_fee_arrears",
        "description": "List students with the lowest fee payments (likely in arrears). Returns student name, class, total paid, and last payment date.",
        "input_schema": {
            "type": "object",
            "properties": {
                "class_name": {"type": "string",  "description": "Filter by class"},
                "limit":      {"type": "integer", "description": "Max results (default 20)"},
            },
        },
    },
    {
        "name": "get_grade_results",
        "description": "Get student exam/grade results. Filter by class or subject.",
        "input_schema": {
            "type": "object",
            "properties": {
                "class_name":   {"type": "string",  "description": "Filter by class name"},
                "subject_name": {"type": "string",  "description": "Filter by subject name"},
                "limit":        {"type": "integer", "description": "Max results (default 30)"},
            },
        },
    },
    {
        "name": "get_welfare_cases",
        "description": "Get active student welfare cases (orphans, disabilities, financial hardship, etc.).",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {"type": "string",  "description": "Welfare category to filter by"},
                "limit":    {"type": "integer", "description": "Max results (default 20)"},
            },
        },
    },
    {
        "name": "get_inventory_status",
        "description": "Get inventory items. Use low_stock_only=true to find items that need restocking.",
        "input_schema": {
            "type": "object",
            "properties": {
                "low_stock_only": {"type": "boolean", "description": "Only return items at or below reorder level"},
                "category":       {"type": "string",  "description": "Filter by category"},
            },
        },
    },
    {
        "name": "get_staff_list",
        "description": "Get list of staff (teachers, admin, etc.) with roles and specializations.",
        "input_schema": {
            "type": "object",
            "properties": {
                "role": {"type": "string", "description": "Filter by role, e.g. 'teacher', 'admin'"},
            },
        },
    },
]


# ── Tool implementations ────────────────────────────────────────────────────────

def _execute_tool(name: str, inputs: dict) -> str:
    try:
        if name == "get_school_summary":
            students = fetch_one("SELECT COUNT(*) as n FROM students WHERE is_active=1 AND deleted_at IS NULL")
            teachers = fetch_one("SELECT COUNT(*) as n FROM teachers WHERE is_active=1 AND deleted_at IS NULL")
            classes  = fetch_one("SELECT COUNT(*) as n FROM classes WHERE deleted_at IS NULL")
            today    = date.today().isoformat()
            att = fetch_one(
                "SELECT COUNT(*) as total, SUM(CASE WHEN status='present' THEN 1 ELSE 0 END) as present FROM attendance WHERE date=?",
                (today,),
            )
            pct = round((att["present"] or 0) / att["total"] * 100, 1) if att and att["total"] else None
            return json.dumps({
                "total_students":       students["n"] if students else 0,
                "total_teachers":       teachers["n"] if teachers else 0,
                "total_classes":        classes["n"] if classes else 0,
                "attendance_today_pct": pct,
                "date": today,
            })

        elif name == "search_students":
            nm    = inputs.get("name", "")
            cls   = inputs.get("class_name", "")
            limit = min(int(inputs.get("limit", 20)), 50)
            active_clause = "" if inputs.get("inactive") else "AND s.is_active=1 AND s.deleted_at IS NULL"
            wheres, params = [], []
            if nm:
                wheres.append("(s.first_name || ' ' || s.last_name) LIKE ?")
                params.append(f"%{nm}%")
            if cls:
                wheres.append("c.name LIKE ?")
                params.append(f"%{cls}%")
            where = ("WHERE " + " AND ".join(wheres) + " " + active_clause) if wheres else f"WHERE 1=1 {active_clause}"
            rows = fetch_all(
                f"""SELECT s.first_name||' '||s.last_name as name, s.admission_no,
                           c.name as class_name, s.is_active
                    FROM students s LEFT JOIN classes c ON s.class_id=c.id
                    {where} ORDER BY c.name, s.first_name LIMIT ?""",
                params + [limit],
            )
            return json.dumps([dict(r) for r in rows])

        elif name == "get_attendance_report":
            today     = date.today().isoformat()
            d_from    = inputs.get("date_from", today)
            d_to      = inputs.get("date_to", today)
            cls       = inputs.get("class_name", "")
            cf        = "AND c.name LIKE ?" if cls else ""
            params    = [d_from, d_to] + ([f"%{cls}%"] if cls else [])
            rows = fetch_all(
                f"""SELECT c.name as class_name,
                           COUNT(*) as total,
                           SUM(CASE WHEN a.status='present' THEN 1 ELSE 0 END) as present,
                           SUM(CASE WHEN a.status='absent'  THEN 1 ELSE 0 END) as absent
                    FROM attendance a
                    JOIN students s ON a.student_id=s.id
                    JOIN classes c ON s.class_id=c.id
                    WHERE a.date BETWEEN ? AND ? {cf}
                    GROUP BY c.id ORDER BY c.name""",
                params,
            )
            result = []
            for r in rows:
                r = dict(r)
                r["attendance_pct"] = round(r["present"] / r["total"] * 100, 1) if r["total"] else 0
                result.append(r)
            return json.dumps({"date_from": d_from, "date_to": d_to, "classes": result})

        elif name == "get_fee_summary":
            cls = inputs.get("class_name", "")
            cf  = "AND c.name LIKE ?" if cls else ""
            p   = [f"%{cls}%"] if cls else []
            row = fetch_one(
                f"""SELECT COUNT(DISTINCT fp.student_id) as payers,
                           SUM(fp.amount_paid) as total_collected
                    FROM fee_payments fp
                    JOIN students s ON fp.student_id=s.id
                    JOIN classes c ON s.class_id=c.id
                    WHERE 1=1 {cf}""",
                p,
            )
            return json.dumps({
                "unique_payers":   row["payers"]          if row else 0,
                "total_collected": row["total_collected"] if row else 0,
                "currency": "TZS",
            })

        elif name == "get_fee_arrears":
            cls   = inputs.get("class_name", "")
            limit = min(int(inputs.get("limit", 20)), 50)
            cf    = "AND c.name LIKE ?" if cls else ""
            p     = ([f"%{cls}%"] if cls else []) + [limit]
            rows  = fetch_all(
                f"""SELECT s.first_name||' '||s.last_name as name, s.admission_no,
                           c.name as class_name,
                           COALESCE(SUM(fp.amount_paid), 0) as total_paid,
                           MAX(fp.payment_date) as last_payment_date
                    FROM students s
                    LEFT JOIN classes c ON s.class_id=c.id
                    LEFT JOIN fee_payments fp ON fp.student_id=s.id
                    WHERE s.is_active=1 AND s.deleted_at IS NULL {cf}
                    GROUP BY s.id
                    ORDER BY total_paid ASC
                    LIMIT ?""",
                p,
            )
            return json.dumps([dict(r) for r in rows])

        elif name == "get_grade_results":
            cls   = inputs.get("class_name", "")
            subj  = inputs.get("subject_name", "")
            limit = min(int(inputs.get("limit", 30)), 100)
            wheres, params = [], []
            if cls:
                wheres.append("c.name LIKE ?")
                params.append(f"%{cls}%")
            if subj:
                wheres.append("su.name LIKE ?")
                params.append(f"%{subj}%")
            where = ("WHERE " + " AND ".join(wheres)) if wheres else ""
            rows = fetch_all(
                f"""SELECT s.first_name||' '||s.last_name as student, s.admission_no,
                           c.name as class_name, su.name as subject, e.name as exam,
                           g.score, g.max_score, g.grade_letter
                    FROM grades g
                    JOIN students s  ON g.student_id=s.id
                    LEFT JOIN classes c  ON s.class_id=c.id
                    LEFT JOIN subjects su ON g.subject_id=su.id
                    LEFT JOIN exams e    ON g.exam_id=e.id
                    {where}
                    ORDER BY c.name, su.name, s.first_name LIMIT ?""",
                params + [limit],
            )
            return json.dumps([dict(r) for r in rows])

        elif name == "get_welfare_cases":
            cat   = inputs.get("category", "")
            limit = min(int(inputs.get("limit", 20)), 50)
            cf    = "AND wr.category LIKE ?" if cat else ""
            p     = ([f"%{cat}%"] if cat else []) + [limit]
            rows  = fetch_all(
                f"""SELECT s.first_name||' '||s.last_name as student, s.admission_no,
                           c.name as class_name, wr.category, wr.support_type, wr.sponsor_name, wr.notes
                    FROM welfare_records wr
                    JOIN students s ON wr.student_id=s.id
                    LEFT JOIN classes c ON s.class_id=c.id
                    WHERE wr.is_current=1 {cf}
                    ORDER BY wr.category, s.first_name LIMIT ?""",
                p,
            )
            return json.dumps([dict(r) for r in rows])

        elif name == "get_inventory_status":
            low  = inputs.get("low_stock_only", False)
            cat  = inputs.get("category", "")
            wheres, params = [], []
            if low:
                wheres.append("i.stock_qty <= i.reorder_qty")
            if cat:
                wheres.append("i.category LIKE ?")
                params.append(f"%{cat}%")
            where = ("WHERE " + " AND ".join(wheres)) if wheres else ""
            rows = fetch_all(
                f"""SELECT i.name, i.category, i.unit, i.stock_qty, i.reorder_qty,
                           CASE WHEN i.stock_qty <= i.reorder_qty THEN 'LOW' ELSE 'OK' END as status
                    FROM inventory_items_v2 i {where}
                    ORDER BY (i.stock_qty - i.reorder_qty) ASC""",
                params,
            )
            return json.dumps([dict(r) for r in rows])

        elif name == "get_staff_list":
            role = inputs.get("role", "")
            rf   = "AND u.role LIKE ?" if role else ""
            p    = [f"%{role}%"] if role else []
            rows = fetch_all(
                f"""SELECT u.full_name, u.role, u.username,
                           t.subject_specialization, t.employee_no,
                           t.first_name||' '||t.last_name as teacher_name
                    FROM users u
                    LEFT JOIN teachers t ON u.teacher_id=t.id
                    WHERE u.is_active=1 {rf}
                    ORDER BY u.role, u.full_name""",
                p,
            )
            return json.dumps([dict(r) for r in rows])

        return json.dumps({"error": f"Unknown tool: {name}"})

    except Exception as ex:
        return json.dumps({"error": str(ex)})


# ── Request / Response models ───────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role:    str
    content: str

class ChatRequest(BaseModel):
    messages: list[ChatMessage]


# ── Endpoint ────────────────────────────────────────────────────────────────────

@router.post("/chat")
async def chat(body: ChatRequest, user: Usr):
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(
            503,
            "AI assistant is not configured. "
            "Set ANTHROPIC_API_KEY in the server environment and restart.",
        )

    try:
        import anthropic
    except ImportError:
        raise HTTPException(
            503,
            "Python 'anthropic' package is not installed. "
            "Run: pip install anthropic",
        )

    school_name = ""
    try:
        cfg = fetch_one("SELECT value FROM school_config WHERE key='school_name'")
        school_name = cfg["value"] if cfg else ""
    except Exception:
        pass

    system = (
        f"You are an AI assistant for {school_name or 'the school'}'s management system. "
        "You help staff quickly get answers about students, attendance, fees, grades, welfare, and inventory. "
        "Always use the tools to look up live data before answering — never guess numbers. "
        "Be concise. When there are many results, summarise rather than listing all of them. "
        "Use bullet points for lists. Bold important numbers with **number**. "
        f"Today's date is {date.today().isoformat()}. Currency is TZS (Tanzanian Shillings)."
    )

    messages = [{"role": m.role, "content": m.content} for m in body.messages]

    client = anthropic.Anthropic(api_key=api_key)

    for _ in range(6):
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=system,
            tools=TOOLS,
            messages=messages,
        )

        tool_uses = [b for b in response.content if b.type == "tool_use"]
        if not tool_uses:
            text = next((b.text for b in response.content if b.type == "text"), "")
            return {"message": text}

        # Append assistant turn with tool calls
        assistant_blocks = []
        for b in response.content:
            if b.type == "text":
                assistant_blocks.append({"type": "text", "text": b.text})
            elif b.type == "tool_use":
                assistant_blocks.append({"type": "tool_use", "id": b.id, "name": b.name, "input": b.input})
        messages.append({"role": "assistant", "content": assistant_blocks})

        # Execute tools and append results
        results = []
        for tu in tool_uses:
            results.append({
                "type": "tool_result",
                "tool_use_id": tu.id,
                "content": _execute_tool(tu.name, tu.input),
            })
        messages.append({"role": "user", "content": results})

    return {"message": "I reached the maximum number of steps. Please try a more specific question."}
