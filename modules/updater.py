"""
modules/updater.py
GitHub-based auto-updater.

How it works:
  1. On startup (or "Check for updates"), fetch version.json from GitHub raw URL.
  2. Compare remote version with local version.json.
  3. Build a manifest of all app files with their SHA-256 hashes.
  4. Download only files that differ (or are new).
  5. Show a progress dialog while downloading.
  6. Ask user to restart the app.

Developer instructions:
  - Set GITHUB_RAW_URL below to your repo's raw content base URL.
  - After pushing changes to GitHub, run tools/build_manifest.py (included)
    to regenerate version.json with updated file hashes.
  - Commit and push version.json. Users get the update on next startup.
"""

import os
import json
import hashlib
import shutil
import urllib.request
import urllib.error
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QTextEdit, QMessageBox, QFrame
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

# ── Read GitHub URL from github_config.py ────────────────────────────────────
def _get_raw_url() -> str:
    try:
        import importlib.util, sys
        cfg_path = Path(__file__).parent.parent / "github_config.py"
        spec = importlib.util.spec_from_file_location("github_config", cfg_path)
        gc   = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gc)
        if gc.is_configured():
            return gc.GITHUB_RAW_BASE
    except Exception:
        pass
    return "https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main"

GITHUB_RAW_URL = _get_raw_url()
# ─────────────────────────────────────────────────────────────────────────────

BASE_DIR         = Path(__file__).parent.parent.resolve()
LOCAL_VERSION_F  = BASE_DIR / "version.json"
BACKUP_DIR       = BASE_DIR / ".update_backup"

# Files/dirs never touched by the updater
SKIP_PATHS = {
    "school_mis.db", "version.json", "config.json",
    "assets", "exports", "venv", ".update_backup",
    "SETUP_WINDOWS.bat", "SETUP_LINUX.sh", "install.py",
}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return ""


def _fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"Cache-Control": "no-cache",
                                                "User-Agent": "SchoolMIS-Updater/2.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode())


def _load_local_version() -> dict:
    try:
        return json.loads(LOCAL_VERSION_F.read_text())
    except Exception:
        return {"version": "0.0.0", "files": {}}


def check_for_update() -> dict:
    """
    Returns dict:
      { "available": bool, "local": "1.0.0", "remote": "2.0.0",
        "release_notes": "…", "files_to_update": ["path/file.py", …] }
    Raises ConnectionError if GitHub is unreachable.
    """
    if GITHUB_RAW_URL.startswith("https://raw.githubusercontent.com/YOUR_USERNAME"):
        return {"available": False, "local": "dev", "remote": "dev",
                "note": "GitHub URL not configured."}

    local  = _load_local_version()
    remote = _fetch_json(f"{GITHUB_RAW_URL}/version.json")

    local_v  = tuple(int(x) for x in local.get("version","0.0.0").split("."))
    remote_v = tuple(int(x) for x in remote.get("version","0.0.0").split("."))

    if remote_v <= local_v:
        return {"available": False,
                "local":  local.get("version"),
                "remote": remote.get("version")}

    # Find which files have changed (by hash or are new)
    remote_files = remote.get("files", {})
    local_files  = local.get("files", {})
    to_update = []
    for rel_path, remote_hash in remote_files.items():
        local_hash = local_files.get(rel_path, "")
        disk_hash  = _sha256(BASE_DIR / rel_path)
        if remote_hash != disk_hash:
            to_update.append(rel_path)

    return {
        "available":      True,
        "local":          local.get("version"),
        "remote":         remote.get("version"),
        "release_notes":  remote.get("release_notes", ""),
        "files_to_update": to_update,
        "remote_manifest": remote,
    }


# ── Background download thread ─────────────────────────────────────────────────
class _DownloadThread(QThread):
    progress     = pyqtSignal(int, int, str)   # current, total, filename
    file_done    = pyqtSignal(str)
    all_done     = pyqtSignal()
    error        = pyqtSignal(str)

    def __init__(self, files: list, remote_manifest: dict):
        super().__init__()
        self._files    = files
        self._manifest = remote_manifest

    def run(self):
        total = len(self._files)
        BACKUP_DIR.mkdir(exist_ok=True)

        for i, rel_path in enumerate(self._files):
            try:
                self.progress.emit(i, total, rel_path)
                url  = f"{GITHUB_RAW_URL}/{rel_path.replace(os.sep, '/')}"
                dest = BASE_DIR / rel_path

                # Back up existing file
                if dest.exists():
                    backup = BACKUP_DIR / rel_path
                    backup.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(dest, backup)

                # Download to temp, then move atomically
                dest.parent.mkdir(parents=True, exist_ok=True)
                tmp = dest.with_suffix(dest.suffix + ".tmp")
                urllib.request.urlretrieve(url, tmp)

                # Verify hash
                expected = self._manifest.get("files", {}).get(rel_path, "")
                if expected and _sha256(tmp) != expected:
                    tmp.unlink(missing_ok=True)
                    self.error.emit(f"Hash mismatch for {rel_path} — download aborted.")
                    return

                shutil.move(str(tmp), str(dest))
                self.file_done.emit(rel_path)

            except Exception as e:
                self.error.emit(f"Error updating {rel_path}: {e}")
                return

        # Write new version.json
        try:
            LOCAL_VERSION_F.write_text(json.dumps(self._manifest, indent=2))
        except Exception:
            pass

        self.all_done.emit()


# ── Update dialog UI ───────────────────────────────────────────────────────────
class UpdateDialog(QDialog):
    def __init__(self, update_info: dict, parent=None):
        super().__init__(parent)
        self._info   = update_info
        self._thread = None
        self.setWindowTitle("Software Update")
        self.setFixedSize(520, 420)
        self._build()

    def _build(self):
        lay = QVBoxLayout(self); lay.setContentsMargins(28, 24, 28, 24); lay.setSpacing(14)

        title = QLabel("Update available")
        title.setStyleSheet("font-size:18px;font-weight:700;color:#111827;")
        lay.addWidget(title)

        ver_row = QHBoxLayout()
        ver_row.addWidget(self._badge(f"Current: v{self._info['local']}", "#F3F4F6", "#6B7280"))
        ver_row.addWidget(QLabel("→"))
        ver_row.addWidget(self._badge(f"New: v{self._info['remote']}", "#DBEAFE", "#1E40AF"))
        ver_row.addStretch()
        lay.addLayout(ver_row)

        # Release notes
        notes_lbl = QLabel("What's new:")
        notes_lbl.setStyleSheet("font-size:13px;font-weight:600;color:#374151;")
        lay.addWidget(notes_lbl)
        notes = QTextEdit()
        notes.setPlainText(self._info.get("release_notes", "No notes provided."))
        notes.setReadOnly(True); notes.setFixedHeight(90)
        notes.setStyleSheet("background:#F9FAFB;border:1px solid #E5E7EB;border-radius:6px;font-size:13px;color:#374151;")
        lay.addWidget(notes)

        n = len(self._info.get("files_to_update", []))
        files_lbl = QLabel(f"{n} file(s) will be updated. Your data will not be affected.")
        files_lbl.setStyleSheet("font-size:12px;color:#6B7280;background:#F0FDF4;border-radius:6px;padding:8px 10px;")
        lay.addWidget(files_lbl)

        # Progress
        self._prog = QProgressBar()
        self._prog.setRange(0, max(n, 1))
        self._prog.setValue(0)
        self._prog.setStyleSheet("""QProgressBar{border:1px solid #E5E7EB;border-radius:6px;
            background:#F9FAFB;height:16px;text-align:center;color:#374151;font-size:11px;}
            QProgressBar::chunk{background:#2563EB;border-radius:5px;}""")
        self._prog.setVisible(False)
        lay.addWidget(self._prog)

        self._status = QLabel("")
        self._status.setStyleSheet("font-size:12px;color:#6B7280;")
        self._status.setVisible(False)
        lay.addWidget(self._status)

        lay.addStretch()

        # Buttons
        btn_row = QHBoxLayout()
        self._btn_later  = QPushButton("Remind me later")
        self._btn_later.setStyleSheet("QPushButton{background:#F3F4F6;color:#374151;border:1px solid #D1D5DB;border-radius:7px;padding:9px 20px;}")
        self._btn_later.clicked.connect(self.reject)

        self._btn_update = QPushButton("⬇  Install update")
        self._btn_update.setStyleSheet("QPushButton{background:#2563EB;color:#fff;border:none;border-radius:7px;padding:9px 20px;font-weight:600;}")
        self._btn_update.clicked.connect(self._start_update)

        btn_row.addWidget(self._btn_later); btn_row.addStretch(); btn_row.addWidget(self._btn_update)
        lay.addLayout(btn_row)

    def _badge(self, text, bg, fg):
        l = QLabel(text)
        l.setStyleSheet(f"background:{bg};color:{fg};border-radius:5px;padding:4px 10px;font-size:12px;font-weight:600;")
        return l

    def _start_update(self):
        self._btn_update.setEnabled(False)
        self._btn_later.setEnabled(False)
        self._prog.setVisible(True)
        self._status.setVisible(True)
        self._prog.setMaximum(len(self._info.get("files_to_update", [])))

        self._thread = _DownloadThread(
            self._info.get("files_to_update", []),
            self._info.get("remote_manifest", {})
        )
        self._thread.progress.connect(self._on_progress)
        self._thread.all_done.connect(self._on_done)
        self._thread.error.connect(self._on_error)
        self._thread.start()

    def _on_progress(self, current, total, filename):
        self._prog.setValue(current)
        self._status.setText(f"Updating: {filename}")

    def _on_done(self):
        self._prog.setValue(self._prog.maximum())
        self._status.setText("✓ Update complete!")
        QMessageBox.information(
            self, "Update installed",
            "The update was installed successfully.\n\nPlease close and reopen the app to use the new version."
        )
        self.accept()

    def _on_error(self, msg):
        self._btn_later.setEnabled(True)
        self._status.setText(f"✗ {msg}")
        QMessageBox.critical(self, "Update failed", msg)


# ── Silent startup check (non-blocking) ────────────────────────────────────────
class StartupUpdateChecker(QThread):
    """Run in background on startup — emits update_available if found."""
    update_available = pyqtSignal(dict)

    def run(self):
        try:
            info = check_for_update()
            if info.get("available"):
                self.update_available.emit(info)
        except Exception:
            pass  # Silent fail on no internet / unconfigured URL
