#!/usr/bin/env bash
# Sets up a Cloudflare Tunnel on this Ubuntu machine so that
# maarifahub.co.tz → nginx (localhost:80) via Cloudflare.
#
# Run once on the Mac Mini (Ubuntu):
#   bash tools/setup_cloudflare_tunnel.sh

set -e

TUNNEL_NAME="school-mis"
DOMAIN="maarifahub.co.tz"
WWW_DOMAIN="www.maarifahub.co.tz"
NGINX_PORT=80
CONFIG_DIR="/etc/cloudflared"
CONFIG_FILE="$CONFIG_DIR/config.yml"

# ── colours ───────────────────────────────────────────────────────
bold=$(tput bold 2>/dev/null || true)
green=$(tput setaf 2 2>/dev/null || true)
yellow=$(tput setaf 3 2>/dev/null || true)
reset=$(tput sgr0 2>/dev/null || true)

step() { echo; echo "${bold}${green}▶ $*${reset}"; }
info() { echo "  ${yellow}→${reset} $*"; }

# ── 1. Install cloudflared ────────────────────────────────────────
step "1/6  Installing cloudflared"
if command -v cloudflared &>/dev/null; then
    info "Already installed: $(cloudflared --version)"
else
    # Official Cloudflare apt repo
    sudo mkdir -p /usr/share/keyrings
    curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg \
        | sudo tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null
    echo "deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] \
https://pkg.cloudflare.com/cloudflared $(lsb_release -cs) main" \
        | sudo tee /etc/apt/sources.list.d/cloudflared.list
    sudo apt-get update -qq
    sudo apt-get install -y cloudflared
    info "Installed: $(cloudflared --version)"
fi

# ── 2. Authenticate ───────────────────────────────────────────────
step "2/6  Logging in to Cloudflare"
info "cloudflared will print a URL — open it in any browser on any device."
info "Select the maarifahub.co.tz zone and authorise."
cloudflared tunnel login

# ── 3. Create tunnel ─────────────────────────────────────────────
step "3/6  Creating tunnel '$TUNNEL_NAME'"
if cloudflared tunnel list 2>/dev/null | grep -q "$TUNNEL_NAME"; then
    info "Tunnel '$TUNNEL_NAME' already exists — skipping creation."
    TUNNEL_ID=$(cloudflared tunnel list | awk "/$TUNNEL_NAME/ {print \$1}")
else
    cloudflared tunnel create "$TUNNEL_NAME"
    TUNNEL_ID=$(cloudflared tunnel list | awk "/$TUNNEL_NAME/ {print \$1}")
fi
info "Tunnel ID: $TUNNEL_ID"

# ── 4. Write config ───────────────────────────────────────────────
step "4/6  Writing $CONFIG_FILE"
CRED_FILE="$HOME/.cloudflared/$TUNNEL_ID.json"

sudo mkdir -p "$CONFIG_DIR"
sudo tee "$CONFIG_FILE" > /dev/null <<EOF
tunnel: $TUNNEL_ID
credentials-file: $CRED_FILE

ingress:
  - hostname: $DOMAIN
    service: http://localhost:$NGINX_PORT
  - hostname: $WWW_DOMAIN
    service: http://localhost:$NGINX_PORT
  # catch-all — required by cloudflared
  - service: http_status:404
EOF

info "Written to $CONFIG_FILE"

# ── 5. Route DNS ─────────────────────────────────────────────────
step "5/6  Routing DNS ($DOMAIN and $WWW_DOMAIN → tunnel)"
cloudflared tunnel route dns "$TUNNEL_NAME" "$DOMAIN"
cloudflared tunnel route dns "$TUNNEL_NAME" "$WWW_DOMAIN"
info "CNAME records created in Cloudflare (proxied)."

# ── 6. Install as a systemd service ──────────────────────────────
step "6/6  Installing cloudflared as a systemd service (auto-starts on boot)"
sudo cloudflared service install
sudo systemctl enable cloudflared
sudo systemctl start cloudflared

sleep 2
if systemctl is-active --quiet cloudflared; then
    info "Service is running."
else
    info "Service did not start cleanly — check: sudo journalctl -u cloudflared -n 50"
fi

echo
echo "${bold}${green}Done!${reset}"
echo "  Test:   open https://$DOMAIN in a browser"
echo "  Logs:   sudo journalctl -u cloudflared -f"
echo "  Stop:   sudo systemctl stop cloudflared"
echo "  Start:  sudo systemctl start cloudflared"
echo "  Status: sudo systemctl status cloudflared"
