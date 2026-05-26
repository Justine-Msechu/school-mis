#!/usr/bin/env bash
# Pull latest code and restart the service.
# Run from the project root: bash update_pi.sh

set -e
cd "$(dirname "$0")"

echo "=== School MIS — Update ==="

echo ""
echo "[1/4] Pulling latest code..."
git pull

echo ""
echo "[2/4] Installing Python dependencies..."
source venv/bin/activate
pip install --quiet -r backend/requirements.txt

echo ""
echo "[3/4] Rebuilding frontend..."
cd school-mis-app
npm ci --silent
npm run build --silent
cd ..

echo ""
echo "[4/4] Restarting service..."
sudo systemctl restart school-mis
sleep 2
sudo systemctl status school-mis --no-pager

echo ""
echo "=== Update complete ==="
