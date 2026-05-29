#!/usr/bin/env bash
# ============================================================
# School MIS — Linux MX Setup Script
# Run once on the Mac Mini:  bash setup_mac.sh
# ============================================================
set -euo pipefail
cd "$(dirname "$0")"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; BOLD='\033[1m'; NC='\033[0m'
ok()   { echo -e "${GREEN}[✓]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
err()  { echo -e "${RED}[✗]${NC} $*"; exit 1; }
step() { echo; echo -e "${BOLD}── $* ──${NC}"; }

echo
echo -e "${BOLD}================================================${NC}"
echo -e "${BOLD}   School MIS — Server Setup (Linux MX)         ${NC}"
echo -e "${BOLD}================================================${NC}"
echo

# Must not run as root (Docker Desktop for Linux needs the real user)
if [[ "$EUID" -eq 0 ]]; then
  err "Do not run as root. Run as your normal user: bash setup_mac.sh"
fi

PROJECT_DIR="$(pwd)"

# ── 1. System packages ───────────────────────────────────────
step "1/5  System packages"
sudo apt-get update -qq
sudo apt-get install -y curl git ca-certificates gnupg lsb-release
ok "System packages ready."

# ── 2. Docker ───────────────────────────────────────────────
step "2/5  Docker"
if ! command -v docker &>/dev/null; then
  warn "Installing Docker..."
  curl -fsSL https://get.docker.com | sh
  sudo usermod -aG docker "$USER"
  ok "Docker installed."
  echo
  warn "You have been added to the 'docker' group."
  warn "To apply without logging out, this script will continue using 'sg docker'."
  # Re-exec the rest of this script under the docker group
  exec sg docker -c "bash '$0'"
fi
ok "Docker: $(docker --version)"

# ── 3. Docker Compose plugin ────────────────────────────────
step "3/5  Docker Compose"
if ! docker compose version &>/dev/null 2>&1; then
  warn "Installing Docker Compose plugin..."
  sudo apt-get install -y docker-compose-plugin
fi
ok "Docker Compose: $(docker compose version --short 2>/dev/null || docker compose version)"

# ── 4. Build & start ────────────────────────────────────────
step "4/5  Build & start (first run ~4 min — builds Node + Python layers)"
docker compose down --remove-orphans 2>/dev/null || true
docker compose up -d --build

# Health check
echo "  Waiting for app to be ready (up to 90 s)..."
READY=0
for i in $(seq 1 45); do
  if curl -sf http://localhost:8765/api/health &>/dev/null; then
    READY=1; break
  fi
  printf "."
  sleep 2
done
echo

if [[ $READY -eq 1 ]]; then
  ok "App is healthy."
else
  warn "App may still be starting. Check: docker compose logs -f school-mis"
fi

# ── 5. Auto-start on boot ───────────────────────────────────
step "5/5  Auto-start on boot"

SERVICE_FILE="/etc/systemd/system/school-mis.service"

sudo tee "$SERVICE_FILE" > /dev/null <<SERVICE
[Unit]
Description=School MIS Application
After=docker.service network-online.target
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=${PROJECT_DIR}
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
User=${USER}

[Install]
WantedBy=multi-user.target
SERVICE

sudo systemctl daemon-reload
sudo systemctl enable school-mis
ok "Systemd service installed — app will start automatically on boot."

# ── SSH access from dev machine ─────────────────────────────
step "SSH setup"
# Enable SSH server so you can connect / deploy from Parrot Linux
if ! systemctl is-active --quiet ssh 2>/dev/null && ! systemctl is-active --quiet sshd 2>/dev/null; then
  warn "Installing OpenSSH server..."
  sudo apt-get install -y openssh-server
  sudo systemctl enable --now ssh
fi
ok "SSH server is running."
echo "  From your Parrot Linux machine you can now run:"
echo "    ssh ${USER}@192.168.1.8"

# ── Summary ─────────────────────────────────────────────────
LOCAL_IP=$(hostname -I | awk '{print $1}')

echo
echo -e "${BOLD}┌──────────────────────────────────────────────────────────┐${NC}"
echo -e "${BOLD}│          School MIS is running!                          │${NC}"
echo       "│                                                          │"
printf     "│  From this machine:   http://localhost                   │\n"
printf     "│  From your dev PC:    http://%-30s│\n" "$LOCAL_IP"
echo       "│                                                          │"
echo       "│  First time? Open the URL above → go to /setup           │"
echo       "│  to create the first superadmin account.                 │"
echo       "│                                                          │"
echo       "│  Commands:                                               │"
echo       "│    See logs:    docker compose logs -f                   │"
echo       "│    Stop:        docker compose down                      │"
echo       "│    Update:      bash update_mac.sh                       │"
echo       "│    SSH in:      ssh ${USER}@$LOCAL_IP                   │"
echo -e "${BOLD}└──────────────────────────────────────────────────────────┘${NC}"
echo
