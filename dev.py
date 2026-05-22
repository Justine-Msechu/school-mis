"""
dev.py — Auto-restart launcher for development.

Usage:
    python dev.py

Watches all .py files in the project. When any file is saved,
the app restarts automatically. Press Ctrl+C to quit.
"""

import subprocess
import sys
import time
import os
from pathlib import Path

ROOT = Path(__file__).parent

IGNORE = {"venv", "__pycache__", ".update_backup", ".git"}


def _py_mtimes() -> dict:
    result = {}
    for path in ROOT.rglob("*.py"):
        if any(part in IGNORE for part in path.parts):
            continue
        try:
            result[str(path)] = path.stat().st_mtime
        except OSError:
            pass
    return result


def _changed_files(old: dict, new: dict) -> list:
    return [
        f for f, t in new.items()
        if old.get(f) != t
    ]


def _start() -> subprocess.Popen:
    return subprocess.Popen(
        [sys.executable, "main.py"],
        cwd=ROOT,
    )


def main():
    print("=" * 52)
    print("  School MIS — Dev mode (auto-restart on save)")
    print("  Press Ctrl+C to stop.")
    print("=" * 52)
    print()

    proc   = _start()
    mtimes = _py_mtimes()
    print(f"  App started (PID {proc.pid}). Watching for changes...\n")

    try:
        while True:
            time.sleep(0.8)

            # App crashed or was closed manually — restart it
            if proc.poll() is not None:
                print("\n  App exited. Restarting...\n")
                proc   = _start()
                mtimes = _py_mtimes()
                print(f"  App started (PID {proc.pid}). Watching...\n")
                continue

            new_mtimes = _py_mtimes()
            changed    = _changed_files(mtimes, new_mtimes)

            if changed:
                names = [os.path.relpath(f, ROOT) for f in changed]
                print(f"  Changed: {', '.join(names)}")
                print("  Restarting app...\n")
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
                mtimes = new_mtimes
                proc   = _start()
                print(f"  App started (PID {proc.pid}). Watching...\n")

    except KeyboardInterrupt:
        print("\n  Stopping...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        print("  Done.")


if __name__ == "__main__":
    main()
