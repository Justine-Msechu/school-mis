#!/usr/bin/env bash
# Option A — Private GitHub repo + SSH deploy key.
# Run on the Pi: bash setup_private_github.sh

set -e
cd "$(dirname "$0")"

echo "=== Private GitHub Deploy Key Setup ==="

# 1. Generate SSH key
echo ""
echo "[1/4] Generating SSH deploy key..."
if [ -f ~/.ssh/deploy_key ]; then
  echo "      Key already exists at ~/.ssh/deploy_key — skipping generation."
else
  ssh-keygen -t ed25519 -C "pi-deploy-$(hostname)" -f ~/.ssh/deploy_key -N ""
  echo "      Key generated."
fi

# 2. Configure SSH to use this key for GitHub
echo ""
echo "[2/4] Configuring SSH..."
grep -q "deploy_key" ~/.ssh/config 2>/dev/null || cat >> ~/.ssh/config << 'EOF'

Host github.com
  IdentityFile ~/.ssh/deploy_key
  StrictHostKeyChecking no
EOF

# 3. Switch remote to SSH (if currently HTTPS)
echo ""
echo "[3/4] Switching git remote to SSH..."
CURRENT=$(git remote get-url origin 2>/dev/null || echo "")
if echo "$CURRENT" | grep -q "https://"; then
  REPO=$(echo "$CURRENT" | sed 's|https://github.com/||')
  git remote set-url origin "git@github.com:$REPO"
  echo "      Remote updated to: git@github.com:$REPO"
else
  echo "      Remote is already SSH: $CURRENT"
fi

# 4. Print the public key for GitHub
echo ""
echo "[4/4] Almost done!"
echo ""
echo "┌─────────────────────────────────────────────────────────────┐"
echo "│  Add this key to GitHub as a Deploy Key:                    │"
echo "│  Repo → Settings → Deploy keys → Add deploy key            │"
echo "│  Title: Pi Deploy Key                                       │"
echo "│  Tick: Allow read access                                    │"
echo "└─────────────────────────────────────────────────────────────┘"
echo ""
cat ~/.ssh/deploy_key.pub
echo ""
echo "After adding the key to GitHub, test with:"
echo "  git pull"
echo ""
echo "Then make your repo private:"
echo "  GitHub → Repo → Settings → Danger Zone → Change visibility → Private"
