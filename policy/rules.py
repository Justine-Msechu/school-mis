"""
policy/rules.py — All business rules registered with the policy engine.

Import this module once at startup (in main.py) to activate every rule.
Rules are grouped by domain. Each rule is a plain function decorated with
@policy_engine.register("action.code").

Rule contract:
  - Receives a PolicyContext
  - Returns PolicyResult.allow() or PolicyResult.deny(reason, rule_name=...)
  - Must NEVER raise — return deny with an error message instead
  - Must be side-effect-free (read-only DB queries are fine, no writes)
"""

from policy.engine import policy_engine
from policy.result import PolicyContext, PolicyResult


# ═══════════════════════════════════════════════════════════════════════════════
# FINANCE — payment rules
# ═══════════════════════════════════════════════════════════════════════════════

@policy_engine.register("payment.record")
def require_valid_control_number(ctx: PolicyContext) -> PolicyResult:
    if not ctx.subject.get("control_number"):
        return PolicyResult.deny(
            "Invalid or missing control number — cannot record payment.",
            rule_name="require_valid_control_number",
        )
    return PolicyResult.allow()


@policy_engine.register("payment.record")
def deny_payment_on_waived_bill(ctx: PolicyContext) -> PolicyResult:
    if ctx.subject.get("status") == "waived":
        return PolicyResult.deny(
            "This bill has been waived — the student is exempt and no payment is required.",
            rule_name="deny_payment_on_waived_bill",
        )
    return PolicyResult.allow()


@policy_engine.register("payment.record")
def deny_payment_on_paid_bill(ctx: PolicyContext) -> PolicyResult:
    if ctx.subject.get("status") == "paid":
        return PolicyResult.deny(
            "This bill is already fully paid. No further payment is accepted.",
            rule_name="deny_payment_on_paid_bill",
        )
    return PolicyResult.allow()


@policy_engine.register("payment.record")
def deny_zero_or_negative_payment(ctx: PolicyContext) -> PolicyResult:
    amount = ctx.data.get("amount", 0)
    if amount <= 0:
        return PolicyResult.deny(
            "Payment amount must be greater than zero.",
            rule_name="deny_zero_or_negative_payment",
        )
    return PolicyResult.allow()


@policy_engine.register("payment.record")
def deny_overpayment(ctx: PolicyContext) -> PolicyResult:
    bill = ctx.subject
    balance = (
        bill.get("amount_due", 0)
        - bill.get("amount_paid", 0)
        - bill.get("discount_amount", 0)
    )
    amount = ctx.data.get("amount", 0)
    if amount > balance + 0.01:      # 0.01 tolerance for float rounding
        return PolicyResult.deny(
            f"Payment TZS {amount:,.0f} exceeds outstanding balance "
            f"TZS {max(balance, 0):,.0f}.",
            rule_name="deny_overpayment",
        )
    return PolicyResult.allow()


# ── Finance — fee structure rules ─────────────────────────────────────────────

@policy_engine.register("fee.structure.delete", "fee.structure.edit")
def protect_paid_fee_structure(ctx: PolicyContext) -> PolicyResult:
    """Block changes to a fee structure that already has payments recorded."""
    if ctx.subject.get("has_payments"):
        return PolicyResult.deny(
            "Cannot modify a fee structure that already has payments recorded against it.",
            rule_name="protect_paid_fee_structure",
        )
    return PolicyResult.allow()


# ── Finance — billing rules ───────────────────────────────────────────────────

@policy_engine.register("fee.bill_student")
def orphan_must_use_waiver(ctx: PolicyContext) -> PolicyResult:
    """
    Orphan students get 100% fee waiver, not a regular bill.
    The billing engine should detect this and call WelfareService to apply waiver.
    """
    if ctx.subject.get("student_category") == "orphan":
        return PolicyResult.deny(
            "Orphan students are automatically exempt — a full waiver is applied instead of billing.",
            rule_name="orphan_must_use_waiver",
        )
    return PolicyResult.allow()


# ═══════════════════════════════════════════════════════════════════════════════
# INVENTORY — issuance rules
# ═══════════════════════════════════════════════════════════════════════════════

@policy_engine.register("inventory.issue")
def block_issuance_if_unpaid(ctx: PolicyContext) -> PolicyResult:
    student = ctx.subject
    # Orphans are always exempt from this requirement
    if student.get("student_category") == "orphan":
        return PolicyResult.allow(reason="Orphan — exempt from payment requirement.")

    # Full-fee waiver via welfare record also bypasses the block
    if ctx.extra.get("has_full_waiver"):
        return PolicyResult.allow(reason="Student holds a full fee waiver.")

    unpaid = ctx.extra.get("unpaid_bills", 0)
    if unpaid > 0:
        return PolicyResult.deny(
            f"Student has {unpaid} unpaid or partial bill(s). "
            f"Outstanding balance must be cleared before items can be issued.",
            rule_name="block_issuance_if_unpaid",
        )
    return PolicyResult.allow()


@policy_engine.register("inventory.issue")
def check_stock_availability(ctx: PolicyContext) -> PolicyResult:
    item = ctx.extra.get("item", {})
    qty  = ctx.data.get("qty", 1)
    stock = item.get("stock_qty", 0)
    if qty < 1:
        return PolicyResult.deny("Quantity must be at least 1.",
                                  rule_name="check_stock_availability")
    if stock < qty:
        return PolicyResult.deny(
            f"Insufficient stock: {stock} unit(s) available, {qty} requested.",
            rule_name="check_stock_availability",
        )
    return PolicyResult.allow()


@policy_engine.register("inventory.issue")
def deny_inactive_item(ctx: PolicyContext) -> PolicyResult:
    item = ctx.extra.get("item", {})
    if not item.get("is_active", 1):
        return PolicyResult.deny(
            "This inventory item is inactive and cannot be issued.",
            rule_name="deny_inactive_item",
        )
    return PolicyResult.allow()


# ── Inventory — stock adjustment rules ───────────────────────────────────────

@policy_engine.register("inventory.adjust")
def deny_negative_stock_result(ctx: PolicyContext) -> PolicyResult:
    item  = ctx.extra.get("item", {})
    delta = ctx.data.get("qty_delta", 0)
    if item.get("stock_qty", 0) + delta < 0:
        return PolicyResult.deny(
            "Adjustment would result in negative stock.",
            rule_name="deny_negative_stock_result",
        )
    return PolicyResult.allow()


# ═══════════════════════════════════════════════════════════════════════════════
# WELFARE — registration and verification rules
# ═══════════════════════════════════════════════════════════════════════════════

@policy_engine.register("welfare.register")
def deny_duplicate_welfare_record(ctx: PolicyContext) -> PolicyResult:
    if ctx.extra.get("existing_record"):
        return PolicyResult.deny(
            "This student already has a welfare record. Edit the existing one instead.",
            rule_name="deny_duplicate_welfare_record",
        )
    return PolicyResult.allow()


@policy_engine.register("welfare.verify")
def require_welfare_verifier_role(ctx: PolicyContext) -> PolicyResult:
    allowed_roles = {"welfare_officer", "head_teacher", "admin"}
    if ctx.actor_role not in allowed_roles:
        return PolicyResult.deny(
            "Only Welfare Officers, Head Teachers, or Admins may verify welfare records.",
            rule_name="require_welfare_verifier_role",
        )
    return PolicyResult.allow()


@policy_engine.register("welfare.register", "welfare.edit")
def require_orphan_category_for_exemption(ctx: PolicyContext) -> PolicyResult:
    """Full-fee exemptions only apply to orphan/half_orphan categories."""
    support = ctx.data.get("support_type", "")
    category = ctx.data.get("category", "")
    if support == "full_fees" and category not in ("orphan", "half_orphan"):
        return PolicyResult.deny(
            "Full fee exemption (support_type=full_fees) is only valid for "
            "orphan or half_orphan categories.",
            rule_name="require_orphan_category_for_exemption",
        )
    return PolicyResult.allow()


# ═══════════════════════════════════════════════════════════════════════════════
# ATTENDANCE rules
# ═══════════════════════════════════════════════════════════════════════════════

@policy_engine.register("attendance.mark")
def deny_future_attendance(ctx: PolicyContext) -> PolicyResult:
    import datetime
    date_str = ctx.data.get("date", "")
    try:
        mark_date = datetime.date.fromisoformat(date_str)
        if mark_date > datetime.date.today():
            return PolicyResult.deny(
                "Attendance cannot be marked for a future date.",
                rule_name="deny_future_attendance",
            )
    except ValueError:
        return PolicyResult.deny(
            "Invalid attendance date format.",
            rule_name="deny_future_attendance",
        )
    return PolicyResult.allow()


@policy_engine.register("attendance.mark")
def class_teacher_own_class_only(ctx: PolicyContext) -> PolicyResult:
    """Class teachers may only mark attendance for their own assigned class."""
    if ctx.actor_role != "class_teacher":
        return PolicyResult.allow()
    actor_class = ctx.extra.get("actor_class_id")
    target_class = ctx.data.get("class_id")
    if actor_class and target_class and int(actor_class) != int(target_class):
        return PolicyResult.deny(
            "Class teachers can only mark attendance for their own assigned class.",
            rule_name="class_teacher_own_class_only",
        )
    return PolicyResult.allow()


# ═══════════════════════════════════════════════════════════════════════════════
# GRADES rules
# ═══════════════════════════════════════════════════════════════════════════════

@policy_engine.register("grade.enter", "grade.edit")
def deny_grade_on_locked_exam(ctx: PolicyContext) -> PolicyResult:
    status = ctx.extra.get("exam_status", "open")
    if status in ("locked", "published"):
        return PolicyResult.deny(
            f"The exam is '{status}' — grades can no longer be entered or modified.",
            rule_name="deny_grade_on_locked_exam",
        )
    return PolicyResult.allow()


@policy_engine.register("grade.approve")
def require_grade_approver_role(ctx: PolicyContext) -> PolicyResult:
    allowed_roles = {"head_teacher", "academic", "admin"}
    if ctx.actor_role not in allowed_roles:
        return PolicyResult.deny(
            "Only Academic Officers or Head Teachers may approve grades.",
            rule_name="require_grade_approver_role",
        )
    return PolicyResult.allow()


@policy_engine.register("grade.publish")
def require_all_grades_approved_before_publish(ctx: PolicyContext) -> PolicyResult:
    unapproved = ctx.extra.get("unapproved_count", 0)
    if unapproved > 0:
        return PolicyResult.deny(
            f"{unapproved} grade(s) are still in 'draft' or 'submitted' state. "
            f"Approve all grades before publishing.",
            rule_name="require_all_grades_approved_before_publish",
        )
    return PolicyResult.allow()


# ═══════════════════════════════════════════════════════════════════════════════
# ACCOUNTING rules
# ═══════════════════════════════════════════════════════════════════════════════

@policy_engine.register("accounting.expense.record")
def deny_negative_expense(ctx: PolicyContext) -> PolicyResult:
    if ctx.data.get("amount", 0) <= 0:
        return PolicyResult.deny(
            "Expense amount must be greater than zero.",
            rule_name="deny_negative_expense",
        )
    return PolicyResult.allow()


@policy_engine.register("accounting.expense.record")
def require_expense_category(ctx: PolicyContext) -> PolicyResult:
    if not ctx.data.get("category"):
        return PolicyResult.deny(
            "Expense category is required.",
            rule_name="require_expense_category",
        )
    return PolicyResult.allow()
