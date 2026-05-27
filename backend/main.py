"""FastAPI backend — enterprise-grade, clean architecture."""

import sys
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from contextlib import asynccontextmanager

# Make the parent directory importable so existing services/db/auth work
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.routers import (
    auth, grades, students, dashboard, classes,
    teachers, attendance, finance, library, transport,
    inventory, health, welfare, promotion, accounting,
    reports, settings, rbac, invoices, payroll, subjects, ai,
)
from backend.routers import notifications, audit
from backend.routers import enrollments, guardians, timetable, report_cards
from backend.routers import ngo
from backend.routers import setup as setup_router
from backend.routers import subscription as subscription_router
from backend.routers import schools as schools_router
from backend.subscriptions.router import router as new_subscription_router
from backend.subscriptions.webhooks.router import router as webhooks_router

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: run migrations, configure DB, register event handlers."""
    # 1. Run all migrations — each is isolated so one failure never blocks the rest
    import importlib.util, os as _os
    _mig_dir = _os.path.join(_os.path.dirname(__file__), "migrations")
    _migrations = sorted([
        "001_architecture_v2", "002_phase2", "003_structural_fixes",
        "004_id_generation", "005_rbac_tables", "006_secure_finance",
        "007_fee_structure_student_columns", "008_fee_structure_grade_level",
        "009_payroll", "010_payroll_prorate", "011_payroll_permissions",
        "012_inventory_upgrade", "013_inventory_classification",
        "015_ngo", "016_student_sponsorship", "017_welfare_extended",
        "018_security", "019_subscription_v2", "020_superadmin",
    ])
    for _mig_name in _migrations:
        _path = _os.path.join(_mig_dir, f"{_mig_name}.py")
        if not _os.path.exists(_path):
            continue
        try:
            _spec = importlib.util.spec_from_file_location(_mig_name, _path)
            _mod  = importlib.util.module_from_spec(_spec)
            _spec.loader.exec_module(_mod)
            _mod.run()
        except Exception as _e:
            log.warning("Migration %s skipped/warned: %s", _mig_name, _e)

    # Init payment providers from env vars
    try:
        from backend.subscriptions.providers.registry import init_providers
        init_providers()
    except Exception as e:
        log.warning("Payment provider init warning: %s", e)

    # 2. Configure SQLite pragmas on the thread-local connection
    from backend.core.db import _get_conn
    conn = _get_conn()
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")

    # 3. Register notification service event handlers
    try:
        from backend.services.notification_service import NotificationService
        notif_svc = NotificationService(conn)
        notif_svc.register()
        log.info("NotificationService event handlers registered")
    except Exception as e:
        log.warning("NotificationService registration failed: %s", e)

    log.info("School MIS API v5.1 started")
    yield
    log.info("School MIS API shutting down")


app = FastAPI(title="School MIS API", version="5.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", "http://127.0.0.1:3000",
        "http://localhost:1420", "http://127.0.0.1:1420",
        "tauri://localhost",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Subscription enforcement middleware ────────────────────────────────────────
_SUBSCRIPTION_EXEMPT = (
    "/api/auth/",
    "/api/setup/",
    "/api/schools/register",
    "/api/subscription/",
    "/api/subscriptions/",
    "/api/superadmin/",
    "/api/webhooks/",
    "/api/ai/",
    "/api/health",
    "/assets/",
    "/favicon",
    "/manifest",
    "/robots",
)

@app.middleware("http")
async def subscription_middleware(request: Request, call_next):
    path = request.url.path
    if any(path.startswith(p) for p in _SUBSCRIPTION_EXEMPT) or not path.startswith("/api/"):
        return await call_next(request)

    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        return await call_next(request)

    token = auth_header[7:]
    try:
        from backend.deps import get_user_from_token
        from backend.routers.subscription import get_subscription_info
        from backend.subscriptions.plan_config import plan_allows_path, min_plan_for_path
        user = await asyncio.to_thread(get_user_from_token, token)
        if user and user.get("role") not in ("admin", "superadmin"):
            sub = await asyncio.to_thread(get_subscription_info, user.get("school_id"))

            # 1. Check subscription is active
            if not sub.get("is_active", True):
                return JSONResponse(
                    status_code=402,
                    content={
                        "detail": {
                            "code": "subscription_expired",
                            "message": sub.get("warning") or "Subscription expired. Contact your administrator.",
                            "plan": sub.get("plan"),
                            "status": sub.get("status"),
                        }
                    },
                )

            # 2. Check plan allows this path
            plan_name = sub.get("plan", "trial")
            if not plan_allows_path(plan_name, path):
                required = min_plan_for_path(path)
                return JSONResponse(
                    status_code=402,
                    content={
                        "detail": {
                            "code": "plan_restricted",
                            "message": f"This feature requires the {required.title()} plan or higher.",
                            "current_plan": plan_name,
                            "required_plan": required,
                        }
                    },
                )
    except Exception:
        pass  # never block a request due to middleware errors

    return await call_next(request)


# ── Domain exception → HTTP response ──────────────────────────────────────────
from backend.core.exceptions import AppError

@app.exception_handler(AppError)
async def app_error_handler(request, exc: AppError):
    return JSONResponse(
        status_code=exc.http_status,
        content={"detail": exc.message, "code": exc.code},
    )


# ── Routes ─────────────────────────────────────────────────────────────────────
app.include_router(auth.router,          prefix="/api/auth")
app.include_router(grades.router,        prefix="/api/grades")
app.include_router(students.router,      prefix="/api/students")
app.include_router(dashboard.router,     prefix="/api/dashboard")
app.include_router(classes.router,       prefix="/api/classes")
app.include_router(teachers.router,      prefix="/api/teachers")
app.include_router(attendance.router,    prefix="/api/attendance")
app.include_router(finance.router,       prefix="/api/finance")
app.include_router(library.router,       prefix="/api/library")
app.include_router(transport.router,     prefix="/api/transport")
app.include_router(inventory.router,     prefix="/api/inventory")
app.include_router(health.router,        prefix="/api/health")
app.include_router(welfare.router,       prefix="/api/welfare")
app.include_router(promotion.router,     prefix="/api/promotion")
app.include_router(accounting.router,    prefix="/api/accounting")
app.include_router(reports.router,       prefix="/api/reports")
app.include_router(settings.router,      prefix="/api/settings")
app.include_router(notifications.router, prefix="/api/notifications")
app.include_router(audit.router,         prefix="/api/audit")
app.include_router(enrollments.router,   prefix="/api/enrollments")
app.include_router(guardians.router,     prefix="/api/guardians")
app.include_router(timetable.router,     prefix="/api/timetable")
app.include_router(report_cards.router,  prefix="/api/report-cards")
app.include_router(rbac.router,          prefix="/api/rbac")
app.include_router(subjects.router,      prefix="/api/subjects")
app.include_router(invoices.router,      prefix="/api/invoices")
app.include_router(payroll.router,       prefix="/api/payroll")
app.include_router(ngo.router,           prefix="/api")
app.include_router(schools_router.router,        prefix="/api")
app.include_router(setup_router.router,         prefix="/api/setup")
app.include_router(subscription_router.router,  prefix="/api/subscription")
app.include_router(new_subscription_router,     prefix="/api/subscriptions")
app.include_router(webhooks_router,             prefix="/api/webhooks")
app.include_router(ai.router,                   prefix="/api/ai")


@app.get("/api/health")
def health_check():
    return {"status": "ok", "version": "5.1.0", "timestamp": datetime.utcnow().isoformat()}


# ── Static file serving (Pi / Docker / production) ────────────────────────────
# When SCHOOL_MIS_STATIC_DIR is set, serve the built React app on all non-API
# routes so the whole system is accessible via a single port.
import os as _os
from fastapi.responses import FileResponse as _FileResponse

_static_dir = _os.environ.get("SCHOOL_MIS_STATIC_DIR", "").strip()

# Also auto-detect: if dist/ sits next to the project root, use it
if not _static_dir:
    _auto = Path(__file__).parent.parent / "school-mis-app" / "dist"
    if _auto.is_dir():
        _static_dir = str(_auto)

if _static_dir and Path(_static_dir).is_dir():
    from fastapi.staticfiles import StaticFiles

    _assets = Path(_static_dir) / "assets"
    if _assets.is_dir():
        app.mount("/assets", StaticFiles(directory=str(_assets)), name="assets")

    # Serve any other static files that Vite emits at the root (favicon, manifest, etc.)
    @app.get("/favicon.ico", include_in_schema=False)
    @app.get("/manifest.json", include_in_schema=False)
    @app.get("/robots.txt", include_in_schema=False)
    def _static_root_files(request: Request):
        p = Path(_static_dir) / request.url.path.lstrip("/")
        if p.is_file():
            return _FileResponse(str(p))
        return _FileResponse(str(Path(_static_dir) / "index.html"))

    # Root path — must be explicit because /{path} doesn't match empty ""
    @app.get("/", include_in_schema=False)
    def _spa_root():
        return _FileResponse(str(Path(_static_dir) / "index.html"))

    # All other non-API paths → React Router handles them client-side
    @app.get("/{full_path:path}", include_in_schema=False)
    def _spa_fallback(full_path: str):
        # Don't intercept /api/* (already handled above, but just in case)
        if full_path.startswith("api/"):
            from fastapi import HTTPException
            raise HTTPException(404)
        return _FileResponse(str(Path(_static_dir) / "index.html"))

    log.info("Serving frontend from %s", _static_dir)
else:
    log.info("SCHOOL_MIS_STATIC_DIR not set or dist/ not found — frontend not served (API-only mode)")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8765, reload=True)
