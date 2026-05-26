# School MIS — multi-stage Docker build
# Stage 1: build the React frontend
FROM node:20-alpine AS frontend-build
WORKDIR /app/school-mis-app
COPY school-mis-app/package*.json ./
RUN npm ci
COPY school-mis-app/ ./
RUN npm run build

# Stage 2: Python runtime + backend + built frontend
FROM python:3.11-slim
WORKDIR /app

# System deps (bcrypt needs libffi)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy entire project
COPY . .

# Copy built frontend into a static dir the backend can serve
COPY --from=frontend-build /app/school-mis-app/dist /app/static

# Add static file serving to the backend (done via startup env var)
ENV SCHOOL_MIS_STATIC_DIR=/app/static
ENV SCHOOL_MIS_DB_PATH=/data/school_mis.db

# Data volume — database lives here so it persists across container updates
VOLUME ["/data"]

EXPOSE 8765

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8765"]
