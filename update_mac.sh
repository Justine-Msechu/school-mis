#!/usr/bin/env bash
# ============================================================
# School MIS — Update on Mac Mini
# Run after pulling latest code:  bash update_mac.sh
# ============================================================
set -euo pipefail
cd "$(dirname "$0")"

echo "=== School MIS — Updating ==="
echo

echo "[1/3] Pulling latest code..."
git pull --ff-only

echo
echo "[2/3] Rebuilding and restarting containers..."
docker compose up -d --build

echo
echo "[3/3] Checking health..."
sleep 5
if curl -sf http://localhost:8765/api/health &>/dev/null; then
  echo "[✓] App is running."
else
  echo "[!] App may still be starting. Check: docker compose logs -f"
fi

echo
LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "192.168.1.8")
echo "Access: http://$LOCAL_IP"
