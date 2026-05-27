# ── Stage 1: build the React frontend ────────────────────────────────────────
FROM node:20-alpine AS frontend-build
WORKDIR /app/school-mis-app
COPY school-mis-app/package*.json ./
RUN npm ci --silent
COPY school-mis-app/ ./
RUN npm run build

# ── Stage 2: Python runtime + backend + built frontend ────────────────────────
FROM python:3.11-slim
WORKDIR /app

# System deps needed by bcrypt
RUN apt-get update && apt-get install -y --no-install-recommends \
    libffi-dev curl \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies (backend only — no PyQt6)
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Backend source
COPY backend/ ./backend/

# Root-level database module (used by backend + services)
COPY database/ ./database/

# Only services/ and policy/ from desktop_app are needed
# (transport_service and accounting_service live in services/;
#  policy/ is the dependency of BaseService used by both)
COPY desktop_app/services/ ./desktop_app/services/
COPY desktop_app/policy/   ./desktop_app/policy/
COPY desktop_app/auth/     ./desktop_app/auth/

# Built React frontend → served by FastAPI
COPY --from=frontend-build /app/school-mis-app/dist /app/static

# ── Configuration ─────────────────────────────────────────────────────────────
ENV SCHOOL_MIS_STATIC_DIR=/app/static
ENV SCHOOL_MIS_DB_PATH=/data/school_mis.db

# Database lives in a named volume so it survives container rebuilds/updates
VOLUME ["/data"]

EXPOSE 8765

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -sf http://localhost:8765/api/setup/status || exit 1

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8765", "--workers", "2"]
