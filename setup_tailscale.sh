#!/usr/bin/env bash
# Install and configure Tailscale on the Pi.
# Run from anywhere: bash setup_tailscale.sh

set -e

echo "=== Tailscale Setup ==="

# 1. Install Tailscale
echo ""
echo "[1/3] Installing Tailscale..."
curl -fsSL https://tailscale.com/install.sh | sh

# 2. Enable IP forwarding (needed for subnet routing)
echo ""
echo "[2/3] Enabling IP forwarding..."
echo 'net.ipv4.ip_forward = 1' | sudo tee -a /etc/sysctl.d/99-tailscale.conf
echo 'net.ipv6.conf.all.forwarding = 1' | sudo tee -a /etc/sysctl.d/99-tailscale.conf
sudo sysctl -p /etc/sysctl.d/99-tailscale.conf

# 3. Start Tailscale and authenticate
echo ""
echo "[3/3] Starting Tailscale..."
echo ""
echo "┌─────────────────────────────────────────────────────────┐"
echo "│  A link will appear below.                              │"
echo "│  Open it on your phone or computer to authenticate.     │"
echo "│  You need a free Tailscale account (tailscale.com).     │"
echo "└─────────────────────────────────────────────────────────┘"
echo ""
sudo tailscale up --advertise-tags=tag:server

echo ""
echo "=== Done ==="
echo ""
echo "Your Pi's Tailscale IP:"
tailscale ip -4
echo ""
echo "Access the school system from anywhere using:"
TSIP=$(tailscale ip -4 2>/dev/null || echo "<tailscale-ip>")
echo "  http://$TSIP:8765"
echo ""
echo "Next steps:"
echo "  1. Install the Tailscale app on every staff phone/device"
echo "  2. Log in with the same Tailscale account"
echo "  3. Open http://$TSIP:8765 in the browser"
