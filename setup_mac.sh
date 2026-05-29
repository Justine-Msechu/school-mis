#!/usr/bin/env bash
# ============================================================
# School MIS — Ubuntu Server Setup
# Run ONCE on the Mac Mini:  bash setup_mac.sh
#
# What this does:
#   1. Verifies Docker + Docker Compose are installed
#   2. Creates stub dirs so Docker build never fails
#   3. Issues a free SSL cert from Let's Encrypt
#   4. Builds and starts all 4 containers
#   5. Registers a systemd service for auto-start on boot
#   6. Sets up a cron for automatic cert renewal
# ============================================================
set -euo pipefail
cd "$(dirname "$0")"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; BOLD='\033[1m'; NC='\033[0m'
ok()   { echo -e "${GREEN}[✓]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
err()  { echo -e "${RED}[✗]${NC} $*"; exit 1; }
step() { echo; echo -e "${BOLD}──────────────────────────────────────────────${NC}"; echo -e "${BOLD} $*${NC}"; echo -e "${BOLD}──────────────────────────────────────────────${NC}"; }

DOMAIN="maarifahub.co.tz"
EMAIL="admin@${DOMAIN}"
PROJECT_DIR="$(pwd)"
USER_NAME="${USER:-young}"

echo
echo -e "${BOLD}  School MIS — Server Setup${NC}"
echo -e "  Domain: ${GREEN}https://${DOMAIN}${NC}"
echo -e "  User:   ${USER_NAME}"
echo

[[ "$EUID" -eq 0 ]] && err "Run as your normal user (not root): bash setup_mac.sh"

# ── 1. Docker check ──────────────────────────────────────────
step "1/6  Docker"
command -v docker &>/dev/null  || err "Docker is not installed. Install it first: https://docs.docker.com/engine/install/ubuntu/"
docker info &>/dev/null 2>&1   || err "Docker daemon is not running. Start it: sudo systemctl start docker"
ok "Docker: $(docker --version)"

# ── 2. Docker Compose check ──────────────────────────────────
step "2/6  Docker Compose"
if ! docker compose version &>/dev/null 2>&1; then
  warn "Installing Docker Compose plugin..."
  sudo apt-get update -qq
  sudo apt-get install -y docker-compose-plugin
fi
ok "Docker Compose: $(docker compose version --short 2>/dev/null || docker compose version)"

# ── 3. Prep: stub dirs + certbot dirs ────────────────────────
step "3/6  Preparing directories"

# Create empty desktop_app stubs so Docker build never fails
# (needed when the repo was git-cloned and desktop_app wasn't included)
for d in desktop_app/services desktop_app/policy desktop_app/auth; do
  if [[ ! -d "$d" ]]; then
    mkdir -p "$d"
    touch "$d/__init__.py"
    warn "Created stub: $d/"
  fi
done

# Certbot directories (bind mounts for nginx)
mkdir -p certbot/conf certbot/www
ok "Directories ready."

# Dummy SSL certs so nginx can start before the real cert is issued.
# certbot will overwrite these.
LIVE_DIR="certbot/conf/live/${DOMAIN}"
if [[ ! -f "${LIVE_DIR}/fullchain.pem" ]]; then
  warn "Creating temporary self-signed certificate (will be replaced by Let's Encrypt)..."
  mkdir -p "$LIVE_DIR"
  openssl req -x509 -nodes -newkey rsa:2048 \
    -keyout "${LIVE_DIR}/privkey.pem" \
    -out    "${LIVE_DIR}/fullchain.pem" \
    -days 1 -subj "/CN=${DOMAIN}" 2>/dev/null
  cp "${LIVE_DIR}/fullchain.pem" "${LIVE_DIR}/chain.pem"
  ok "Temporary certificate created."
fi

# ── 4. Build + start all containers ─────────────────────────
step "4/6  Building and starting containers (first run ~5 min)"
docker compose down --remove-orphans 2>/dev/null || true
docker compose up -d --build

# Wait for nginx (it starts last, after backend + frontend health checks)
echo "  Waiting for all services (up to 120 s)..."
READY=0
for i in $(seq 1 60); do
  if curl -sf http://localhost/api/health &>/dev/null; then
    READY=1; break
  fi
  printf "."
  sleep 2
done
echo

[[ $READY -eq 1 ]] && ok "All containers are running." || warn "Containers may still be starting. Check: docker compose logs -f"

# ── 5. Let's Encrypt SSL certificate ─────────────────────────
step "5/6  SSL certificate (Let's Encrypt)"
echo "  Requesting certificate for ${DOMAIN} and www.${DOMAIN}..."
echo "  NOTE: Your domain DNS must already point to this server's public IP."
echo

docker run --rm \
  -v "$(pwd)/certbot/conf:/etc/letsencrypt" \
  -v "$(pwd)/certbot/www:/var/www/certbot" \
  certbot/certbot certonly \
    --webroot \
    --webroot-path /var/www/certbot \
    --email "${EMAIL}" \
    --agree-tos \
    --no-eff-email \
    -d "${DOMAIN}" \
    -d "www.${DOMAIN}" && {
      ok "SSL certificate issued for ${DOMAIN}."
      docker compose exec nginx nginx -s reload
      ok "Nginx reloaded with the real certificate."
    } || {
      warn "SSL certificate could not be issued (DNS not pointing here yet?)."
      warn "The app is running on HTTP for now. To add SSL later, run:"
      echo "    bash ssl_renew.sh"
    }

# ── 6. Auto-start + renewal cron ────────────────────────────
step "6/6  Auto-start on boot + SSL renewal"

# Systemd service
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
User=${USER_NAME}

[Install]
WantedBy=multi-user.target
SERVICE
sudo systemctl daemon-reload
sudo systemctl enable school-mis
ok "Systemd service registered — app auto-starts on boot."

# Cron: renew cert every 12 hours, reload nginx if renewed
CRON_LINE="0 */12 * * * cd ${PROJECT_DIR} && docker run --rm -v \$(pwd)/certbot/conf:/etc/letsencrypt -v \$(pwd)/certbot/www:/var/www/certbot certbot/certbot renew --quiet && docker compose exec nginx nginx -s reload >> /var/log/school-mis-ssl-renew.log 2>&1"
( crontab -l 2>/dev/null | grep -v "school-mis-ssl-renew"; echo "$CRON_LINE" ) | crontab -
ok "SSL auto-renewal cron registered (runs every 12 hours)."

# ── Summary ──────────────────────────────────────────────────
LOCAL_IP=$(hostname -I | awk '{print $1}')
echo
echo -e "${BOLD}┌──────────────────────────────────────────────────────────────┐${NC}"
echo -e "${BOLD}│          School MIS is live!                                 │${NC}"
echo       "│                                                              │"
printf     "│  Public URL:          https://%-32s│\n" "${DOMAIN}"
printf     "│  Local network:       http://%-33s│\n" "${LOCAL_IP}"
echo       "│                                                              │"
echo       "│  First time? Go to https://${DOMAIN}/setup               │"
echo       "│  to create the first superadmin account.                     │"
echo       "│                                                              │"
echo       "│  From your dev machine (Parrot Linux):                       │"
echo       "│    Access app:   https://${DOMAIN}                       │"
echo       "│    Dev with live reload against this backend:                │"
echo       "│    VITE_API_HOST=https://${DOMAIN} npm run dev          │"
echo       "│                                                              │"
echo       "│  Useful commands:                                            │"
echo       "│    Logs:     docker compose logs -f                          │"
echo       "│    Stop:     docker compose down                             │"
echo       "│    Update:   bash update_mac.sh                              │"
echo       "│    SSH in:   ssh ${USER_NAME}@${LOCAL_IP}                            │"
echo -e "${BOLD}└──────────────────────────────────────────────────────────────┘${NC}"
echo
