#!/bin/bash
# Sets up a cron job to run the auto-fix agent every 30 minutes.
# Run once on the Mac Mini:  bash tools/setup_cron.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PYTHON="$(which python3)"
LOG="$SCRIPT_DIR/autofix.log"
ENV_FILE="$SCRIPT_DIR/.env"

if [ ! -f "$ENV_FILE" ]; then
  echo "ERROR: $ENV_FILE not found."
  echo "Copy tools/.env.example → tools/.env and fill in your credentials."
  exit 1
fi

# Install Python dependency
echo "Installing anthropic package…"
pip3 install -q anthropic

# Build the cron line
CRON_LINE="*/30 * * * * source $ENV_FILE && cd $PROJECT_DIR && $PYTHON tools/auto_fix_agent.py >> $LOG 2>&1"

# Add to crontab if not already present
( crontab -l 2>/dev/null | grep -v "auto_fix_agent.py" ; echo "$CRON_LINE" ) | crontab -

echo ""
echo "✓ Cron job installed — runs every 30 minutes."
echo "  Logs: $LOG"
echo "  Remove: crontab -e  (delete the auto_fix_agent line)"
