"""FastAPI backend — enterprise-grade, clean architecture."""

import sys
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
    reports, settings, rbac, invoices, payroll,
)
from backend.routers import notifications, audit
from backend.routers import enrollments, guardians, timetable, report_cards
from backend.routers import ngo
from backend.routers import setup as setup_router
from backend.routers import subscription as subscription_router

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: run migrations, configure DB, register event handlers."""
    # 1. Ensure all new tables exist
    try:
        import importlib.util, os
        _mig_path = os.path.join(os.path.dirname(__file__), "migrations", "001_architecture_v2.py")
        _spec = importlib.util.spec_from_file_location("migration_001", _mig_path)
        _mod = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_mod)
        _mod.run()
        _mig2_path = os.path.join(os.path.dirname(__file__), "migrations", "002_phase2.py")
        _spec2 = importlib.util.spec_from_file_location("migration_002", _mig2_path)
        _mod2 = importlib.util.module_from_spec(_spec2)
        _spec2.loader.exec_module(_mod2)
        _mod2.run()
        _mig3_path = os.path.join(os.path.dirname(__file__), "migrations", "003_structural_fixes.py")
        _spec3 = importlib.util.spec_from_file_location("migration_003", _mig3_path)
        _mod3 = importlib.util.module_from_spec(_spec3)
        _spec3.loader.exec_module(_mod3)
        _mod3.run()
        _mig4_path = os.path.join(os.path.dirname(__file__), "migrations", "004_id_generation.py")
        _spec4 = importlib.util.spec_from_file_location("migration_004", _mig4_path)
        _mod4 = importlib.util.module_from_spec(_spec4)
        _spec4.loader.exec_module(_mod4)
        _mod4.run()
        _mig5_path = os.path.join(os.path.dirname(__file__), "migrations", "005_rbac_tables.py")
        _spec5 = importlib.util.spec_from_file_location("migration_005", _mig5_path)
        _mod5 = importlib.util.module_from_spec(_spec5)
        _spec5.loader.exec_module(_mod5)
        _mod5.run()
        _mig6_path = os.path.join(os.path.dirname(__file__), "migrations", "006_secure_finance.py")
        _spec6 = importlib.util.spec_from_file_location("migration_006", _mig6_path)
        _mod6 = importlib.util.module_from_spec(_spec6)
        _spec6.loader.exec_module(_mod6)
        _mod6.run()
        _mig7_path = os.path.join(os.path.dirname(__file__), "migrations", "007_fee_structure_student_columns.py")
        _spec7 = importlib.util.spec_from_file_location("migration_007", _mig7_path)
        _mod7 = importlib.util.module_from_spec(_spec7)
        _spec7.loader.exec_module(_mod7)
        _mod7.run()
        _mig8_path = os.path.join(os.path.dirname(__file__), "migrations", "008_fee_structure_grade_level.py")
        _spec8 = importlib.util.spec_from_file_location("migration_008", _mig8_path)
        _mod8 = importlib.util.module_from_spec(_spec8)
        _spec8.loader.exec_module(_mod8)
        _mod8.run()
        _mig9_path = os.path.join(os.path.dirname(__file__), "migrations", "009_payroll.py")
        _spec9 = importlib.util.spec_from_file_location("migration_009", _mig9_path)
        _mod9 = importlib.util.module_from_spec(_spec9)
        _spec9.loader.exec_module(_mod9)
        _mod9.run()
        _mig10_path = os.path.join(os.path.dirname(__file__), "migrations", "010_payroll_prorate.py")
        _spec10 = importlib.util.spec_from_file_location("migration_010", _mig10_path)
        _mod10 = importlib.util.module_from_spec(_spec10)
        _spec10.loader.exec_module(_mod10)
        _mod10.run()
        _mig11_path = os.path.join(os.path.dirname(__file__), "migrations", "011_payroll_permissions.py")
        _spec11 = importlib.util.spec_from_file_location("migration_011", _mig11_path)
        _mod11 = importlib.util.module_from_spec(_spec11)
        _spec11.loader.exec_module(_mod11)
        _mod11.run()
        _mig12_path = os.path.join(os.path.dirname(__file__), "migrations", "012_inventory_upgrade.py")
        _spec12 = importlib.util.spec_from_file_location("migration_012", _mig12_path)
        _mod12 = importlib.util.module_from_spec(_spec12)
        _spec12.loader.exec_module(_mod12)
        _mod12.run()
        _mig13_path = os.path.join(os.path.dirname(__file__), "migrations", "013_inventory_classification.py")
        _spec13 = importlib.util.spec_from_file_location("migration_013", _mig13_path)
        _mod13 = importlib.util.module_from_spec(_spec13)
        _spec13.loader.exec_module(_mod13)
        _mod13.run()
        _mig15_path = os.path.join(os.path.dirname(__file__), "migrations", "015_ngo.py")
        _spec15 = importlib.util.spec_from_file_location("migration_015", _mig15_path)
        _mod15 = importlib.util.module_from_spec(_spec15)
        _spec15.loader.exec_module(_mod15)
        _mod15.run()
        _mig16_path = os.path.join(os.path.dirname(__file__), "migrations", "016_student_sponsorship.py")
        _spec16 = importlib.util.spec_from_file_location("migration_016", _mig16_path)
        _mod16 = importlib.util.module_from_spec(_spec16)
        _spec16.loader.exec_module(_mod16)
        _mod16.run()
        _mig17_path = os.path.join(os.path.dirname(__file__), "migrations", "017_welfare_extended.py")
        _spec17 = importlib.util.spec_from_file_location("migration_017", _mig17_path)
        _mod17 = importlib.util.module_from_spec(_spec17)
        _spec17.loader.exec_module(_mod17)
        _mod17.run()
        _mig18_path = os.path.join(os.path.dirname(__file__), "migrations", "018_security.py")
        _spec18 = importlib.util.spec_from_file_location("migration_018", _mig18_path)
        _mod18 = importlib.util.module_from_spec(_spec18)
        _spec18.loader.exec_module(_mod18)
        _mod18.run()
    except Exception as e:
        log.warning("Migration warning (may already be applied): %s", e)

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
app.include_router(invoices.router,      prefix="/api/invoices")
app.include_router(payroll.router,       prefix="/api/payroll")
app.include_router(ngo.router,           prefix="/api")
app.include_router(setup_router.router,         prefix="/api/setup")
app.include_router(subscription_router.router,  prefix="/api/subscription")


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
