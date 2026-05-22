"""
github_config.py
================
Edit this file once with your GitHub details.
Every other part of the app (installer, updater) reads from here.

Instructions:
  1. Create a GitHub account at https://github.com if you don't have one.
  2. Create a new repository (e.g. "school-mis").
  3. Fill in GITHUB_USERNAME and GITHUB_REPO below.
  4. Push the code (see README.md → "Pushing to GitHub").
  5. Done — the installer and auto-updater will use these values.
"""

# ── EDIT THESE TWO LINES ──────────────────────────────────────────
GITHUB_USERNAME = "Justine-Msechu"   # e.g. "johnmwangi"
GITHUB_REPO     = "school-mis"         # e.g. "school-mis"
GITHUB_BRANCH   = "main"                   # usually "main" or "master"
# ──────────────────────────────────────────────────────────────────

# Derived URLs (do not edit below)
GITHUB_BASE      = f"https://github.com/{GITHUB_USERNAME}/{GITHUB_REPO}"
GITHUB_RAW_BASE  = f"https://raw.githubusercontent.com/{GITHUB_USERNAME}/{GITHUB_REPO}/{GITHUB_BRANCH}"
GITHUB_ZIP_URL   = f"{GITHUB_BASE}/archive/refs/heads/{GITHUB_BRANCH}.zip"
GITHUB_API_REPO  = f"https://api.github.com/repos/{GITHUB_USERNAME}/{GITHUB_REPO}"


def is_configured() -> bool:
    """Returns True if the developer has filled in the repo details."""
    return (
        GITHUB_USERNAME != "YOUR_GITHUB_USERNAME"
        and GITHUB_REPO != "YOUR_REPO_NAME"
    )
