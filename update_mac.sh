#!/usr/bin/env bash
# ============================================================
# School MIS — Update on Ubuntu server
# Run after pushing code changes: bash update_mac.sh
# ============================================================
set -euo pipefail
cd "$(dirname "$0")"

echo "=== School MIS — Updating ==="
echo

echo "[1/3] Pulling latest code..."
git pull --ff-only

echo
echo "[2/3] Rebuilding and restarting containers..."
# Only rebuild backend and frontend — postgres and nginx don't need rebuilding
docker compose up -d --build --no-deps backend frontend

echo
echo "[3/3] Health check..."
sleep 6
if curl -sf http://localhost/api/health &>/dev/null; then
  echo "[✓] App is healthy."
else
  echo "[!] Still starting — check: docker compose logs -f backend"
fi

echo
echo "Done. App: https://maarifahub.co.tz"
