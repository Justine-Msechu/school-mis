"""
School MIS — Smart Installer  (v3 — GitHub edition)
=====================================================
Two modes:
  A) FRESH INSTALL from GitHub
     The .bat/.sh scripts call this after downloading it alone.
     It downloads the full repo, then sets up the environment.

  B) LOCAL SETUP
     Run directly from inside an already-downloaded repo folder.
     Skips the download step and goes straight to venv + packages.

Usage:
    python install.py                     # local setup (mode B)
    python install.py --from-github       # download repo first (mode A)
    python install.py --repo USER/REPO    # override repo (mode A)
"""

import sys, os, platform, subprocess, shutil, urllib.request
import zipfile, argparse, json, hashlib
from pathlib import Path

# ── Colours ───────────────────────────────────────────────────────────────────
RESET="\033[0m"; BOLD="\033[1m"; RED="\033[91m"; GREEN="\033[92m"
YELLOW="\033[93m"; BLUE="\033[94m"; CYAN="\033[96m"

def _win_ansi():
    if platform.system()=="Windows":
        try:
            import ctypes; ctypes.windll.kernel32.SetConsoleMode(
                ctypes.windll.kernel32.GetStdHandle(-11), 7)
        except: pass
_win_ansi()

def c(t,col=RESET): return f"{col}{t}{RESET}"
def ok(t):   print(c(f"  ✓  {t}", GREEN))
def warn(t): print(c(f"  ⚠  {t}", YELLOW))
def fail(t): print(c(f"  ✗  {t}", RED))
def info(t): print(c(f"  →  {t}", BLUE))
def header(t):
    print(); print(c("─"*58, CYAN)); print(c(f"  {t}", BOLD+CYAN)); print(c("─"*58, CYAN))

OS       = platform.system()
MIN_PY   = (3, 10)
APP_NAME = "School MIS"


# ─────────────────────────────────────────────────────────────────────────────
#  Parse args
# ─────────────────────────────────────────────────────────────────────────────
def parse_args():
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--from-github", action="store_true")
    ap.add_argument("--repo",   default=None, help="USER/REPO")
    ap.add_argument("--branch", default="main")
    ap.add_argument("--dest",   default=None, help="Install folder")
    return ap.parse_args()


# ─────────────────────────────────────────────────────────────────────────────
#  Step A: Download repo from GitHub
# ─────────────────────────────────────────────────────────────────────────────
def download_from_github(repo: str, branch: str, dest: Path):
    header("Downloading School MIS from GitHub")

    zip_url = f"https://github.com/{repo}/archive/refs/heads/{branch}.zip"
    info(f"Repository : https://github.com/{repo}")
    info(f"Branch     : {branch}")
    info(f"Destination: {dest}")

    zip_path = dest.parent / "_school_mis_download.zip"

    # Download with progress
    print(c(f"\n  Downloading… ", BLUE), end="", flush=True)
    try:
        def _progress(block, block_size, total):
            if total > 0:
                pct = min(block * block_size * 100 // total, 100)
                print(f"\r{c(f'  Downloading… {pct}%', BLUE)}", end="", flush=True)
        urllib.request.urlretrieve(zip_url, zip_path, reporthook=_progress)
        print()
        ok(f"Downloaded ({zip_path.stat().st_size // 1024} KB)")
    except Exception as e:
        print()
        fail(f"Download failed: {e}")
        info("Check your internet connection and that the repository is public.")
        info(f"URL tried: {zip_url}")
        sys.exit(1)

    # Extract
    info("Extracting…")
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(dest.parent)
        # GitHub zips extract to REPO-BRANCH/
        repo_name = repo.split("/")[1]
        extracted = dest.parent / f"{repo_name}-{branch}"
        if not extracted.exists():
            # try other common patterns
            candidates = list(dest.parent.glob(f"{repo_name}*"))
            if candidates:
                extracted = candidates[0]
            else:
                fail("Could not find extracted folder."); sys.exit(1)

        if dest.exists():
            warn(f"Folder {dest} already exists — updating files.")
            # Copy new files over existing (preserves school_mis.db etc.)
            for item in extracted.iterdir():
                target = dest / item.name
                if item.is_dir():
                    shutil.copytree(item, target, dirs_exist_ok=True)
                else:
                    shutil.copy2(item, target)
        else:
            shutil.move(str(extracted), str(dest))

        zip_path.unlink(missing_ok=True)
        ok(f"Extracted to: {dest}")
    except Exception as e:
        fail(f"Extraction failed: {e}"); sys.exit(1)

    return dest


# ─────────────────────────────────────────────────────────────────────────────
#  Steps B1–B5: Local environment setup
# ─────────────────────────────────────────────────────────────────────────────
def check_python():
    header("Python version check")
    ver = sys.version_info
    info(f"Python {ver.major}.{ver.minor}.{ver.micro}  ({sys.executable})")
    if (ver.major, ver.minor) < MIN_PY:
        fail(f"Need Python {MIN_PY[0]}.{MIN_PY[1]}+  —  found {ver.major}.{ver.minor}")
        if OS == "Windows":
            warn("Download: https://www.python.org/downloads/")
            warn("Tick '✓ Add Python to PATH' during install")
        else:
            warn("Run: sudo apt install python3.12 python3-venv python3-pip")
        sys.exit(1)
    ok(f"Python {ver.major}.{ver.minor}.{ver.micro} — OK")


def setup_venv(base: Path):
    header("Virtual environment & packages")
    venv = base / "venv"
    py   = str(venv/"Scripts"/"python.exe") if OS=="Windows" else str(venv/"bin"/"python3")
    pip  = str(venv/"Scripts"/"pip.exe")    if OS=="Windows" else str(venv/"bin"/"pip")

    if not venv.exists():
        info("Creating virtual environment…")
        try:
            subprocess.check_call([sys.executable,"-m","venv",str(venv)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            ok(f"Created: {venv}")
        except Exception as e:
            fail(f"venv creation failed: {e}"); sys.exit(1)
    else:
        warn("Virtual environment already exists — updating packages.")

    _quiet([py,"-m","pip","install","--upgrade","pip"])
    ok("pip upgraded")

    req = base / "requirements.txt"
    if not req.exists():
        fail("requirements.txt not found"); sys.exit(1)

    packages = [l.strip() for l in req.read_text().splitlines() if l.strip() and not l.startswith("#")]
    info(f"Installing: {', '.join(packages)}")
    for pkg in packages:
        info(f"  {pkg}…")
        try:
            _quiet([pip,"install",pkg])
            ok(f"  {pkg}")
        except Exception:
            fail(f"  Failed to install {pkg}")
            warn("  Check your internet connection."); sys.exit(1)

    return py


def init_db(base: Path, python_exe: str):
    header("Database initialisation")
    db = base / "school_mis.db"
    if db.exists():
        warn("Database already exists — skipping (your data is safe).")
        return
    result = subprocess.run(
        [python_exe, "-c",
         f"import sys; sys.path.insert(0,r'{base}');"
         "from database.db import initialize_database; initialize_database(); print('OK')"],
        capture_output=True, text=True
    )
    if "OK" in result.stdout:
        ok(f"Database created: {db}")
    else:
        fail("Database init failed:"); print(result.stderr); sys.exit(1)


def create_launcher(base: Path, python_exe: str):
    header("Creating launcher")
    pythonw = python_exe.replace("python3","pythonw").replace("/python3","/pythonw")
    # On Linux pythonw doesn't exist — just use python3
    if OS != "Windows": pythonw = python_exe

    if OS == "Windows":
        bat = base / "Run School MIS.bat"
        bat.write_text(f'@echo off\ncd /d "{base}"\n"{pythonw}" main.py\n')
        ok(f"Launcher: {bat.name}")

        # Desktop shortcut
        desktop = Path.home() / "Desktop"
        if desktop.exists():
            sc = desktop / "School MIS.lnk"
            ps = (f'$ws=New-Object -ComObject WScript.Shell;'
                  f'$s=$ws.CreateShortcut("{sc}");'
                  f'$s.TargetPath="{pythonw}";'
                  f'$s.Arguments=\'"{base}\\main.py"\';'
                  f'$s.WorkingDirectory="{base}";$s.Save()')
            r = subprocess.run(["powershell","-NoProfile","-Command",ps],
                               capture_output=True)
            if r.returncode == 0:
                ok(f"Desktop shortcut created")
            else:
                warn("Desktop shortcut failed (use the .bat file)")

    elif OS == "Linux":
        sh = base / "run_school_mis.sh"
        sh.write_text(f'#!/bin/bash\ncd "{base}"\n"{python_exe}" main.py\n')
        sh.chmod(0o755)
        ok(f"Shell launcher: {sh.name}")

        desktop_entry = (
            f"[Desktop Entry]\nVersion=1.0\nName=School MIS\n"
            f"Exec={python_exe} {base}/main.py\nPath={base}\n"
            f"Icon=applications-education\nTerminal=false\nType=Application\n"
            f"Categories=Education;Office;\n"
        )
        df = base / "SchoolMIS.desktop"
        df.write_text(desktop_entry)
        apps = Path.home() / ".local" / "share" / "applications"
        apps.mkdir(parents=True, exist_ok=True)
        shutil.copy2(df, apps / "SchoolMIS.desktop")
        (apps / "SchoolMIS.desktop").chmod(0o644)
        ok("Application menu entry installed")

        desk = Path.home() / "Desktop"
        if desk.exists():
            d = desk / "SchoolMIS.desktop"
            shutil.copy2(df, d); d.chmod(0o755)
            ok("Desktop icon created")


def print_summary(base: Path):
    w = 58
    print(); print(c("═"*w, GREEN+BOLD))
    print(c(f"  ✓  {APP_NAME} is ready!", GREEN+BOLD))
    print(c("═"*w, GREEN+BOLD)); print()
    if OS == "Windows":
        print(c("  To launch:", BOLD))
        print(f"    • Double-click 'School MIS' on your Desktop")
        print(f"    • Or double-click 'Run School MIS.bat'")
    else:
        print(c("  To launch:", BOLD))
        print(f"    • Open 'School MIS' from the applications menu")
        print(f"    • Or run: ./run_school_mis.sh")
    print()
    print(c("  Your data:", BOLD))
    print(f"    • Database : {base / 'school_mis.db'}")
    print(f"    • Exports  : {base / 'exports'}")
    print(c("─"*w, CYAN)); print()


def _quiet(cmd):
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if r.returncode != 0:
        raise subprocess.CalledProcessError(r.returncode, cmd)


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    args = parse_args()

    print()
    print(c("╔══════════════════════════════════════════════════════╗", CYAN+BOLD))
    print(c("║   School Management Information System  — Installer ║", CYAN+BOLD))
    print(c("╚══════════════════════════════════════════════════════╝", CYAN+BOLD))
    print(c(f"  Platform: {OS} {platform.release()}", BLUE))

    try:
        # Determine base directory
        if args.from_github:
            # ── Mode A: download then install ────────────────────
            repo   = args.repo
            branch = args.branch

            # Try reading from github_config.py if no --repo given
            if not repo:
                cfg_path = Path(__file__).parent / "github_config.py"
                if cfg_path.exists():
                    import importlib.util
                    spec = importlib.util.spec_from_file_location("gc", cfg_path)
                    gc   = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(gc)
                    if gc.is_configured():
                        repo   = f"{gc.GITHUB_USERNAME}/{gc.GITHUB_REPO}"
                        branch = gc.GITHUB_BRANCH

            if not repo or repo.startswith("YOUR_"):
                fail("GitHub repository not configured.")
                info("Edit github_config.py and set GITHUB_USERNAME and GITHUB_REPO.")
                sys.exit(1)

            dest = Path(args.dest) if args.dest else (
                Path.home() / "school_mis"
                if OS == "Windows"
                else Path.home() / "school_mis"
            )
            BASE = download_from_github(repo, branch, dest)
            # Re-run ourselves from inside the downloaded folder
            new_installer = BASE / "install.py"
            print()
            info("Running installer from downloaded folder…")
            subprocess.check_call([sys.executable, str(new_installer),
                                   "--dest", str(BASE)])
            sys.exit(0)
        else:
            # ── Mode B: already in the repo folder ───────────────
            BASE = Path(args.dest) if args.dest else Path(__file__).parent.resolve()

        check_python()
        py = setup_venv(BASE)
        init_db(BASE, py)
        create_launcher(BASE, py)
        print_summary(BASE)

    except KeyboardInterrupt:
        print(); warn("Cancelled."); sys.exit(0)
    except SystemExit:
        print(); fail("Installation stopped — see messages above.")
        if OS == "Windows": input("\nPress Enter to close…")
        sys.exit(1)
