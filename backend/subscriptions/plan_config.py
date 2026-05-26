"""
Plan feature matrix — single source of truth for what each plan allows.
"""

from dataclasses import dataclass, field

PLAN_COLORS = {
    "basic":    "#0891B2",
    "standard": "#7C3AED",
    "premium":  "#059669",
}

PLAN_DESCRIPTIONS = {
    "basic":    "Perfect for small schools just getting started",
    "standard": "Everything you need to run a full school",
    "premium":  "Unlimited power for large schools and networks",
}

# Modules blocked per plan — everything not listed here is allowed
PLAN_RESTRICTED_MODULES = {
    "basic": {
        "/api/payroll",
        "/api/welfare",
        "/api/transport",
        "/api/inventory",
        "/api/library",
        "/api/ai",
        "/api/ngo",
        "/api/accounting",
    },
    "standard": {
        "/api/ai",
    },
    "premium": set(),  # no restrictions
}

PLAN_FEATURES = {
    "basic": [
        "Up to 25 staff accounts",
        "Up to 300 students",
        "Students, Classes, Attendance",
        "Grades & Report Cards",
        "Basic Finance & Fees",
        "Email support",
    ],
    "standard": [
        "Up to 100 staff accounts",
        "Up to 1,000 students",
        "Everything in Basic",
        "Payroll Management",
        "Transport & Inventory",
        "Library & Welfare",
        "NGO Partners",
        "Advanced Reports",
        "Priority support",
    ],
    "premium": [
        "Up to 500 staff accounts",
        "Up to 5,000 students",
        "Everything in Standard",
        "AI Chat Assistant",
        "Multi-school network",
        "API access",
        "Dedicated support",
    ],
}

# Maps plan name → included module paths (for UI display)
PLAN_INCLUDED_PATHS: dict[str, set] = {
    "basic":    {"/api/students", "/api/classes", "/api/attendance", "/api/grades", "/api/finance"},
    "standard": {"*"} - {"/api/ai"},
    "premium":  {"*"},
}


def plan_allows_path(plan_name: str, path: str) -> bool:
    restricted = PLAN_RESTRICTED_MODULES.get(plan_name, set())
    for prefix in restricted:
        if path.startswith(prefix):
            return False
    return True


def min_plan_for_path(path: str) -> str | None:
    for plan in ["basic", "standard", "premium"]:
        if plan_allows_path(plan, path):
            return plan
    return "premium"
