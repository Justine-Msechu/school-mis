#!/usr/bin/env bash
# Docker-based deployment and update setup.
# Run on the Pi: bash setup_docker_deploy.sh
#
# This script:
#   - Installs Docker if not present
#   - Builds and starts the app in Docker
#   - Sets up a nightly auto-update cron job (git pull + docker rebuild)
#   - Data (database) is stored in a Docker volume — never lost on update

set -e
cd "$(dirname "$0")"

echo "=== School MIS — Docker Deploy Setup ==="

# 1. Install Docker if not present
if ! command -v docker &>/dev/null; then
  echo ""
  echo "[1/5] Installing Docker..."
  curl -fsSL https://get.docker.com | sh
  sudo usermod -aG docker "$USER"
  echo "      Docker installed. NOTE: You may need to log out and back in"
  echo "      for group changes to take effect. If docker commands fail,"
  echo "      run: newgrp docker"
else
  echo "[1/5] Docker already installed: $(docker --version)"
fi

# 2. Install Docker Compose plugin if not present
if ! docker compose version &>/dev/null 2>&1; then
  echo ""
  echo "[2/5] Installing Docker Compose plugin..."
  sudo apt-get install -y docker-compose-plugin
else
  echo "[2/5] Docker Compose already installed."
fi

# 3. Build and start the app
echo ""
echo "[3/5] Building and starting School MIS..."
docker compose up -d --build
echo "      Done."

# 4. Set up nightly auto-update cron (2am every night)
echo ""
echo "[4/5] Setting up nightly auto-update..."
PROJECT_DIR="$(pwd)"
CRON_CMD="0 2 * * * cd $PROJECT_DIR && git pull --ff-only && docker compose up -d --build >> /var/log/school-mis-update.log 2>&1"

# Add only if not already present
( crontab -l 2>/dev/null | grep -v "school-mis-update" ; echo "$CRON_CMD" ) | crontab -
echo "      Nightly update scheduled at 2:00 AM."

# 5. Done
echo ""
echo "[5/5] Checking status..."
docker compose ps

PI_IP=$(tailscale ip -4 2>/dev/null || hostname -I | awk '{print $1}')

echo ""
echo "=== Setup complete ==="
echo ""
echo "School MIS is running at: http://$PI_IP:8765"
echo ""
echo "┌─────────────────────────────────────────────────────────────┐"
echo "│  How updates work with Docker:                              │"
echo "│                                                             │"
echo "│  Automatic: Every night at 2am the Pi pulls your latest    │"
echo "│  code and rebuilds the container.                          │"
echo "│                                                             │"
echo "│  Manual (instant): SSH into the Pi and run:                │"
echo "│    cd $PROJECT_DIR                     │"
echo "│    git pull && docker compose up -d --build                │"
echo "│                                                             │"
echo "│  Database is safe: stored in a Docker volume (db_data).    │"
echo "│  It is NEVER touched during updates.                       │"
echo "└─────────────────────────────────────────────────────────────┘"
echo ""
echo "Useful commands:"
echo "  View logs:    docker compose logs -f"
echo "  Stop app:     docker compose down"
echo "  Start app:    docker compose up -d"
echo "  Backup DB:    docker run --rm -v school_mis_db_data:/data -v \$(pwd):/backup alpine cp /data/school_mis.db /backup/backup_\$(date +%Y%m%d).db"
