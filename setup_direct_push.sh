#!/usr/bin/env bash
# Option B — Push directly from your laptop to the Pi (no GitHub needed).
# Run on the Pi: bash setup_direct_push.sh

set -e
cd "$(dirname "$0")"

PROJECT_DIR="$(pwd)"
BARE_REPO="/opt/school_mis_repo.git"
BRANCH="main"

echo "=== Direct Push Deploy Setup ==="
echo "    Project: $PROJECT_DIR"
echo "    Bare repo: $BARE_REPO"

# 1. Create bare repo
echo ""
echo "[1/4] Creating bare git repository..."
if [ -d "$BARE_REPO" ]; then
  echo "      Bare repo already exists — skipping."
else
  sudo git init --bare "$BARE_REPO"
  sudo chown -R "$USER":"$USER" "$BARE_REPO"
  echo "      Done."
fi

# 2. Create post-receive hook
echo ""
echo "[2/4] Installing deploy hook..."
HOOK="$BARE_REPO/hooks/post-receive"
sudo tee "$HOOK" > /dev/null << HOOK_SCRIPT
#!/bin/bash
echo ""
echo "=== School MIS Deploy ==="
export HOME=/home/$USER

cd $PROJECT_DIR

# Pull latest code from the bare repo
git --git-dir=$BARE_REPO --work-tree=$PROJECT_DIR checkout -f $BRANCH

# Python deps
source $PROJECT_DIR/venv/bin/activate
pip install -q -r $PROJECT_DIR/backend/requirements.txt

# Frontend build
cd $PROJECT_DIR/school-mis-app
npm ci --silent
npm run build --silent
cd $PROJECT_DIR

# Restart service
sudo systemctl restart school-mis

echo "=== Deploy complete ==="
HOOK_SCRIPT

sudo chmod +x "$HOOK"
sudo chown "$USER":"$USER" "$HOOK"
echo "      Hook installed."

# 3. Push current code into the bare repo so it's in sync
echo ""
echo "[3/4] Syncing current code into bare repo..."
if ! git remote get-url bare &>/dev/null; then
  git remote add bare "$BARE_REPO"
fi
git push bare "$BRANCH" --force
echo "      Done."

# 4. Print laptop instructions
PI_IP=$(tailscale ip -4 2>/dev/null || hostname -I | awk '{print $1}')

echo ""
echo "=== Setup complete ==="
echo ""
echo "┌─────────────────────────────────────────────────────────────────┐"
echo "│  On your LAPTOP, run these commands once:                       │"
echo "│                                                                  │"
echo "│  cd ~/Desktop/codeDevelopment/school_mis                        │"
echo "│  git remote add pi ssh://$USER@$PI_IP/opt/school_mis_repo.git   │"
echo "│                                                                  │"
echo "│  To deploy any update:                                          │"
echo "│    git push pi main                                             │"
echo "│                                                                  │"
echo "│  The Pi will build and restart automatically.                   │"
echo "└─────────────────────────────────────────────────────────────────┘"
