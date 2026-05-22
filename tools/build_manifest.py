#!/usr/bin/env python3
"""
tools/build_manifest.py
Run this locally before pushing a new release to GitHub.

Usage:
    python tools/build_manifest.py --version 2.1.0 --notes "Fixed attendance bug"

It scans all app source files, computes their SHA-256 hashes,
and writes version.json. Commit and push that file — clients will
detect the change and download only what changed.
"""

import argparse, hashlib, json, os, sys
from pathlib import Path

BASE    = Path(__file__).parent.parent.resolve()
OUT     = BASE / "version.json"

# These are never included in the update manifest
SKIP = {
    # never-update system files
    "school_mis.db", "version.json", ".update_backup", "venv", "__pycache__",
    "assets", "exports", ".git", "tools",
    # installer / setup scripts (not delivered via auto-update)
    "SETUP_WINDOWS.bat", "SETUP_LINUX.sh", "install.py", "get-pip.py",
    # machine-specific launcher files created by the installer
    "run_school_mis.sh", "run_school_mis.bat",
    "SchoolMIS.desktop", "School MIS.lnk",
}
SKIP_EXT = {".pyc", ".pyo", ".db", ".db-shm", ".db-wal", ".tmp", ".log", ".lnk"}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def scan_files():
    files = {}
    for root, dirs, fnames in os.walk(BASE):
        dirs[:] = [d for d in dirs if d not in SKIP and not d.startswith(".")]
        for fname in fnames:
            p = Path(root) / fname
            rel = str(p.relative_to(BASE))
            # normalise to forward slashes
            rel = rel.replace("\\", "/")
            if any(s in rel for s in SKIP):
                continue
            if p.suffix in SKIP_EXT:
                continue
            if fname.startswith("."):
                continue
            files[rel] = sha256(p)
    return files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default=None, help="New version string e.g. 2.1.0")
    ap.add_argument("--notes",   default="",   help="Release notes")
    args = ap.parse_args()

    existing = {}
    if OUT.exists():
        try: existing = json.loads(OUT.read_text())
        except: pass

    version = args.version or existing.get("version", "1.0.0")

    files = scan_files()
    manifest = {
        "version":       version,
        "release_date":  __import__("datetime").date.today().isoformat(),
        "release_notes": args.notes or existing.get("release_notes", ""),
        "min_python":    "3.10",
        "files":         files,
    }

    OUT.write_text(json.dumps(manifest, indent=2))
    print(f"✓ version.json written — v{version} — {len(files)} files")
    print(f"  Commit and push version.json to trigger updates on clients.")


if __name__ == "__main__":
    main()
