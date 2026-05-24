"""FastAPI backend — wraps existing Python service layer for the React frontend."""

import sys
import os
import secrets
from datetime import datetime
from pathlib import Path

# Make the parent directory importable so existing services/db/auth work
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import auth, grades, students, dashboard, classes

app = FastAPI(title="School MIS API", version="5.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:1420", "tauri://localhost", "http://127.0.0.1:1420"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,      prefix="/api/auth")
app.include_router(grades.router,    prefix="/api/grades")
app.include_router(students.router,  prefix="/api/students")
app.include_router(dashboard.router, prefix="/api/dashboard")
app.include_router(classes.router,   prefix="/api/classes")


@app.get("/api/health")
def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8765, reload=True)
