#!/usr/bin/env bash
# Reset the admin password.
# Run from the project root: bash reset_admin.sh

set -e
cd "$(dirname "$0")"

if [ ! -f venv/bin/activate ]; then
  echo "ERROR: venv not found. Run setup_pi.sh first."
  exit 1
fi

source venv/bin/activate
python tools/reset_admin.py
