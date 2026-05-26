#!/usr/bin/env bash
# Reset the admin password to a value you choose.
# Run from the project root: bash reset_admin.sh

set -e

cd "$(dirname "$0")"

# Activate venv
if [ ! -f venv/bin/activate ]; then
  echo "ERROR: venv not found. Run setup_pi.sh first."
  exit 1
fi
source venv/bin/activate

# Ask for new password
read -s -p "Enter new admin password (min 8 chars): " NEW_PW
echo
if [ ${#NEW_PW} -lt 8 ]; then
  echo "ERROR: Password must be at least 8 characters."
  exit 1
fi
read -s -p "Confirm password: " CONFIRM_PW
echo
if [ "$NEW_PW" != "$CONFIRM_PW" ]; then
  echo "ERROR: Passwords do not match."
  exit 1
fi

python3 - "$NEW_PW" << 'EOF'
import sys
sys.path.insert(0, '.')
import bcrypt
from database.db import execute, fetch_one

new_password = sys.argv[1]
row = fetch_one("SELECT id, username FROM users WHERE role='admin' AND is_active=1 LIMIT 1")
if not row:
    print("ERROR: No active admin user found in the database.")
    sys.exit(1)

pw_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt(rounds=12)).decode()
execute(
    "UPDATE users SET password_hash=?, pw_scheme='bcrypt', salt='' WHERE id=?",
    (pw_hash, row['id'])
)
print(f"Password reset for user '{row['username']}'. You can now log in.")
EOF
