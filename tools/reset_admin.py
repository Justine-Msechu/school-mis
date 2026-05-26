#!/usr/bin/env python3
"""Reset the admin password. Run from the project root: python tools/reset_admin.py"""

import sys, os, getpass
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database.db import DB_PATH, initialize_database, fetch_one, execute, fetch_all

print(f"Database: {DB_PATH}")

# Create tables and run schema migrations if not yet done
initialize_database()

# Show all active users so we know what's in the DB
print("\nActive users in database:")
users = fetch_all("SELECT id, username, role, pw_scheme FROM users WHERE is_active=1")
if not users:
    print("  No active users found. The database may be empty.")
    sys.exit(1)

for u in users:
    scheme = u["pw_scheme"] if "pw_scheme" in u.keys() else "sha256"
    print(f"  [{u['id']}] {u['username']}  (role: {u['role']}, scheme: {scheme})")

# Pick the user to reset
print()
choice = input("Enter username to reset (or press Enter to reset first admin): ").strip()

if choice:
    row = fetch_one("SELECT id, username FROM users WHERE username=? AND is_active=1", (choice,))
else:
    row = fetch_one("SELECT id, username FROM users WHERE role='admin' AND is_active=1 LIMIT 1")

if not row:
    print("ERROR: User not found.")
    sys.exit(1)

print(f"\nResetting password for: {row['username']}")

# Get new password
while True:
    pw = getpass.getpass("New password (min 8 chars): ")
    if len(pw) < 8:
        print("Password must be at least 8 characters. Try again.")
        continue
    pw2 = getpass.getpass("Confirm password: ")
    if pw != pw2:
        print("Passwords do not match. Try again.")
        continue
    break

# Hash with bcrypt
try:
    import bcrypt
    pw_hash = bcrypt.hashpw(pw.encode(), bcrypt.gensalt(rounds=12)).decode()
    # Try to update with pw_scheme column (migration 018)
    try:
        execute(
            "UPDATE users SET password_hash=?, pw_scheme='bcrypt', salt='' WHERE id=?",
            (pw_hash, row["id"])
        )
    except Exception:
        # pw_scheme column may not exist yet — update without it
        execute(
            "UPDATE users SET password_hash=?, salt='' WHERE id=?",
            (pw_hash, row["id"])
        )
    print(f"\nDone. Password reset for '{row['username']}'. You can now log in.")
except ImportError:
    # Fallback to SHA-256 if bcrypt not installed
    import hashlib, secrets
    salt = secrets.token_hex(16)
    pw_hash = hashlib.sha256((salt + pw).encode()).hexdigest()
    execute(
        "UPDATE users SET password_hash=?, salt=? WHERE id=?",
        (pw_hash, salt, row["id"])
    )
    print(f"\nDone (SHA-256). Password reset for '{row['username']}'. You can now log in.")
