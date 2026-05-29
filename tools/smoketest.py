#!/usr/bin/env python3
"""
Smoke test runner for the auto-fix Docker sandbox.
Runs against the test backend on port 18765.

Creates a fresh school + admin, logs in, then hits the key endpoints.
Exit 0 = all tests passed.  Exit 1 = one or more failed.

No third-party dependencies — stdlib only.
"""

import json
import sys
import time
import urllib.error
import urllib.request

BASE  = "http://localhost:18765"
TOKEN = None
PASS  = []
FAIL  = []


def api(method: str, path: str, body: dict | None = None,
        token: str | None = None) -> tuple[int, dict]:
    url  = BASE + "/api" + path
    data = json.dumps(body).encode() if body else None
    hdrs: dict = {"Content-Type": "application/json"}
    if token:
        hdrs["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=12) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"{}")
        except Exception:
            return e.code, {}
    except Exception as e:
        return 0, {"error": str(e)}


def check(name: str, status: int, ok_range: tuple[int, int] = (200, 299)) -> bool:
    passed = ok_range[0] <= status <= ok_range[1]
    symbol = "✓" if passed else "✗"
    print(f"  {symbol}  {name:<40} HTTP {status}")
    (PASS if passed else FAIL).append(name)
    return passed


# ── 1. Wait for backend health ────────────────────────────────────────────────

print("Waiting for test backend to become healthy…")
for attempt in range(45):
    try:
        s, _ = api("GET", "/health")
        if s == 200:
            print(f"  Backend ready (attempt {attempt + 1})\n")
            break
    except Exception:
        pass
    time.sleep(2)
else:
    print("  FATAL: Backend did not respond within 90s")
    sys.exit(1)


# ── 2. First-time setup ───────────────────────────────────────────────────────

print("Setting up test school…")
s, _ = api("POST", "/setup/initialize", {
    "school_name":    "Smoke Test School",
    "admin_username": "smokeadmin",
    "admin_fullname": "Smoke Admin",
    "admin_password": "Smoke@1234",
    "plan_name":      "premium",
})
# 200 = fresh setup, 400 = already done — both are fine
print(f"  Setup response: HTTP {s}\n")


# ── 3. Login ──────────────────────────────────────────────────────────────────

print("Logging in…")
s, data = api("POST", "/auth/login", {
    "username": "smokeadmin",
    "password": "Smoke@1234",
})
TOKEN = data.get("token")
if s != 200 or not TOKEN:
    print(f"  FATAL: Login failed HTTP {s}: {data}")
    sys.exit(1)
print(f"  Token obtained\n")


# ── 4. Core endpoint checks ───────────────────────────────────────────────────

print("Running endpoint smoke tests…")

s, _ = api("GET", "/health")
check("Health check", s)

s, _ = api("GET", "/auth/me", token=TOKEN)
check("Auth /me", s)

s, _ = api("GET", "/setup/status")
check("Setup status", s)

s, _ = api("GET", "/notifications/unread-count", token=TOKEN)
check("Notifications unread-count", s)

s, _ = api("GET", "/audit", token=TOKEN)
check("Audit log (requires roles)", s)

s, _ = api("GET", "/subscriptions/status", token=TOKEN)
check("Subscription status", s)

s, _ = api("GET", "/superadmin/stats", token=TOKEN)
check("Superadmin stats", s)

s, _ = api("GET", "/rbac/roles", token=TOKEN)
check("RBAC roles list", s)

s, _ = api("GET", "/students?page=1", token=TOKEN)
check("Students list", s)

s, _ = api("GET", "/teachers", token=TOKEN)
check("Teachers list", s)

# Verify the response body makes sense for a couple of key endpoints
s, body = api("GET", "/auth/me", token=TOKEN)
if s == 200 and body.get("role") != "admin":
    print(f"  ✗  /auth/me returned unexpected role: {body.get('role')}")
    FAIL.append("Auth /me role check")
else:
    print(f"  ✓  Auth role check                       OK (admin)")
    PASS.append("Auth /me role check")


# ── 5. Summary ────────────────────────────────────────────────────────────────

print(f"\n{'─' * 48}")
print(f"  Passed: {len(PASS)}   Failed: {len(FAIL)}")
if FAIL:
    print("\n  Failed tests:")
    for f in FAIL:
        print(f"    ✗  {f}")
    print()
    sys.exit(1)

print("  All smoke tests passed!")
sys.exit(0)
