#!/usr/bin/env bash
# Sets up a Cloudflare Tunnel on this Mac Mini so that
# maarifahub.co.tz → nginx (localhost:80) via Cloudflare.
#
# Run once on the Mac Mini:
#   bash tools/setup_cloudflare_tunnel.sh

set -e

TUNNEL_NAME="school-mis"
DOMAIN="maarifahub.co.tz"
WWW_DOMAIN="www.maarifahub.co.tz"
NGINX_PORT=80
CONFIG_DIR="$HOME/.cloudflared"
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
    if ! command -v brew &>/dev/null; then
        echo "Homebrew not found. Install it first: https://brew.sh"
        exit 1
    fi
    brew install cloudflared
    info "Installed: $(cloudflared --version)"
fi

# ── 2. Authenticate ───────────────────────────────────────────────
step "2/6  Logging in to Cloudflare"
info "A browser window will open — pick the maarifahub.co.tz zone and authorise."
info "If you are on an SSH session without a browser, copy the URL it prints and open it on another device."
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
CRED_FILE="$CONFIG_DIR/$TUNNEL_ID.json"

mkdir -p "$CONFIG_DIR"
cat > "$CONFIG_FILE" <<EOF
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

info "Written."

# ── 5. Route DNS ─────────────────────────────────────────────────
step "5/6  Routing DNS ($DOMAIN and $WWW_DOMAIN → tunnel)"
cloudflared tunnel route dns "$TUNNEL_NAME" "$DOMAIN"
cloudflared tunnel route dns "$TUNNEL_NAME" "$WWW_DOMAIN"
info "CNAME records created in Cloudflare (proxied)."

# ── 6. Install as a launchd service ──────────────────────────────
step "6/6  Installing cloudflared as a system service (auto-starts on boot)"
sudo cloudflared service install
sudo launchctl load /Library/LaunchDaemons/com.cloudflare.cloudflared.plist 2>/dev/null || true

# verify
sleep 2
if sudo launchctl list | grep -q cloudflared; then
    info "Service running."
else
    info "Service may need a moment — check with: sudo launchctl list | grep cloudflared"
fi

echo
echo "${bold}${green}Done!${reset}"
echo "  Test: open https://$DOMAIN in a browser."
echo "  Logs: sudo tail -f /Library/Logs/com.cloudflare.cloudflared.log"
echo "  Stop: sudo launchctl unload /Library/LaunchDaemons/com.cloudflare.cloudflared.plist"
echo "  Start: sudo launchctl load /Library/LaunchDaemons/com.cloudflare.cloudflared.plist"
