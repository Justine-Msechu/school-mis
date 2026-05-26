#!/usr/bin/env bash
# Full setup script for Raspberry Pi (or any Debian/Ubuntu server).
# Run once after cloning: bash setup_pi.sh
# Safe to re-run — it skips steps already done.

set -e
cd "$(dirname "$0")"

echo "=== School MIS — Pi Setup ==="

# 1. System packages
echo ""
echo "[1/6] Installing system dependencies..."
sudo apt-get update -qq
sudo apt-get install -y python3 python3-pip python3-venv curl

# Install Node 20 if not present or version is wrong
NODE_VER=$(node --version 2>/dev/null | cut -c2- | cut -d. -f1 || echo "0")
if [ "$NODE_VER" -lt 18 ]; then
  echo "      Installing Node.js 20..."
  curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
  sudo apt-get install -y nodejs
else
  echo "      Node.js $NODE_VER already installed."
fi

# 2. Python venv
echo ""
echo "[2/6] Setting up Python virtual environment..."
if [ ! -d venv ]; then
  python3 -m venv venv
fi
source venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r backend/requirements.txt
echo "      Done."

# 3. Frontend build
echo ""
echo "[3/6] Building frontend..."
cd school-mis-app
npm ci --silent
npm run build --silent
cd ..
echo "      Done."

# 4. Fix ownership
echo ""
echo "[4/6] Fixing file ownership..."
sudo chown -R "$USER":"$USER" .
echo "      Done."

# 5. Systemd service
echo ""
echo "[5/6] Installing systemd service..."
PROJECT_DIR="$(pwd)"
VENV_UVICORN="$PROJECT_DIR/venv/bin/uvicorn"
CURRENT_USER="$USER"

sudo tee /etc/systemd/system/school-mis.service > /dev/null << UNIT
[Unit]
Description=School MIS
After=network.target

[Service]
User=$CURRENT_USER
WorkingDirectory=$PROJECT_DIR
ExecStart=$VENV_UVICORN backend.main:app --host 0.0.0.0 --port 8765
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT

sudo systemctl daemon-reload
sudo systemctl enable school-mis
echo "      Service installed and enabled."

# 6. Start service
echo ""
echo "[6/6] Starting service..."
sudo systemctl restart school-mis
sleep 2
sudo systemctl status school-mis --no-pager

echo ""
echo "=== Setup complete ==="
echo "Open http://$(hostname -I | awk '{print $1}'):8765 in your browser."
echo "If this is a fresh install, the setup wizard will guide you."
echo "To reset the admin password later, run: bash reset_admin.sh"
