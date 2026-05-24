#!/usr/bin/env bash
# Start both the FastAPI backend and the React dev server in parallel.
# Usage: ./dev_ui.sh

set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"

# Activate venv if present
if [ -f "$ROOT/venv/bin/activate" ]; then
  source "$ROOT/venv/bin/activate"
fi

echo "Starting FastAPI backend on http://127.0.0.1:8765 ..."
cd "$ROOT"
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8765 --reload &
BACKEND_PID=$!

echo "Starting React frontend on http://localhost:1420 ..."
cd "$ROOT/school-mis-app"
npm run dev &
FRONTEND_PID=$!

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM

wait
