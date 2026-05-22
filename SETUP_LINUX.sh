#!/bin/bash
# School MIS — Installer for Linux
# ─────────────────────────────────────────────────────────────────────────────
# Works in TWO modes automatically:
#
#   MODE A — You already have the code (running from inside the repo folder)
#            Detected when install.py exists next to this script.
#            → Skips GitHub download, sets up the environment directly.
#
#   MODE B — Fresh install on a new PC (only this .sh file was downloaded)
#            → Downloads the full repo from GitHub, then sets up.
#
# Developer: set GITHUB_USER and GITHUB_REPO below before sharing.

GITHUB_USER="Justine-Msechu"
GITHUB_REPO="school-mis"
GITHUB_BRANCH="main"
INSTALL_DIR="$HOME/school_mis"

# ── Colours ───────────────────────────────────────────────────────────────────
RED='\033[91m'; GREEN='\033[92m'; YELLOW='\033[93m'
BLUE='\033[94m'; CYAN='\033[96m'; BOLD='\033[1m'; RESET='\033[0m'
ok()   { echo -e "${GREEN}  ✓  $1${RESET}"; }
warn() { echo -e "${YELLOW}  ⚠  $1${RESET}"; }
fail() { echo -e "${RED}  ✗  $1${RESET}"; }
info() { echo -e "${BLUE}  →  $1${RESET}"; }

clear
echo ""
echo -e "${CYAN}${BOLD}╔══════════════════════════════════════════════════════╗${RESET}"
echo -e "${CYAN}${BOLD}║   School Management Information System              ║${RESET}"
echo -e "${CYAN}${BOLD}║   Installer for Linux                                ║${RESET}"
echo -e "${CYAN}${BOLD}╚══════════════════════════════════════════════════════╝${RESET}"
echo ""

# ── Locate install.py ─────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCAL_INSTALLER="$SCRIPT_DIR/install.py"

if [ -f "$LOCAL_INSTALLER" ]; then
    # ── MODE A: Already have the code ────────────────────────────────────────
    info "Code found locally — skipping GitHub download."
    info "Working directory: $SCRIPT_DIR"
    INSTALLER="$LOCAL_INSTALLER"
    INSTALL_DIR="$SCRIPT_DIR"
    DOWNLOAD_NEEDED=false
else
    # ── MODE B: Need to download from GitHub ─────────────────────────────────
    info "install.py not found here — will download from GitHub."
    info "Repository: https://github.com/$GITHUB_USER/$GITHUB_REPO"
    info "Destination: $INSTALL_DIR"
    DOWNLOAD_NEEDED=true
fi

echo ""

# ── 1. Detect package manager ──────────────────────────────────────────────────
echo -e "${BOLD}  [1/4]  Detecting system...${RESET}"
PKG_MGR=""
command -v apt-get &>/dev/null && PKG_MGR="apt"
command -v dnf     &>/dev/null && PKG_MGR="${PKG_MGR:-dnf}"
command -v pacman  &>/dev/null && PKG_MGR="${PKG_MGR:-pacman}"
DISTRO=$(grep -oP '(?<=^NAME=).+' /etc/os-release 2>/dev/null | tr -d '"' || echo "Linux")
ok "Distro: $DISTRO  |  Package manager: ${PKG_MGR:-unknown}"

# ── 2. Find or install Python 3.10+ ───────────────────────────────────────────
echo ""
echo -e "${BOLD}  [2/4]  Checking Python...${RESET}"
PYTHON_CMD=""
for cmd in python3.12 python3.11 python3.10 python3 python; do
    if command -v "$cmd" &>/dev/null; then
        VER=$("$cmd" --version 2>&1 | awk '{print $2}')
        MAJ=$(echo "$VER" | cut -d. -f1)
        MIN=$(echo "$VER" | cut -d. -f2)
        if [ "$MAJ" -ge 3 ] && [ "$MIN" -ge 10 ]; then
            PYTHON_CMD="$cmd"
            ok "Python $VER  ($cmd)"
            break
        else
            warn "$cmd v$VER is too old (need ≥ 3.10), skipping."
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    warn "Python 3.10+ not found — trying to install..."
    SUDO=""; [ "$EUID" -ne 0 ] && SUDO="sudo"
    case "$PKG_MGR" in
        apt)
            $SUDO apt-get update -qq
            $SUDO apt-get install -y python3.12 python3.12-venv python3-pip 2>/dev/null \
                || $SUDO apt-get install -y python3 python3-venv python3-pip
            ;;
        dnf)    $SUDO dnf install -y python3 python3-pip ;;
        pacman) $SUDO pacman -Sy --noconfirm python python-pip ;;
        *)
            fail "Cannot auto-install Python. Please install Python 3.10+ manually."
            echo "    Ubuntu/Debian:  sudo apt install python3.12 python3-venv python3-pip"
            exit 1
            ;;
    esac
    PYTHON_CMD="python3"
    ok "Python installed"
fi

# ── 3. Ensure venv + pip ──────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}  [3/4]  Checking dependencies...${RESET}"
SUDO=""; [ "$EUID" -ne 0 ] && SUDO="sudo"

if ! "$PYTHON_CMD" -c "import venv" &>/dev/null; then
    warn "python3-venv not found — installing..."
    PY_SHORT=$("$PYTHON_CMD" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    case "$PKG_MGR" in
        apt)
            $SUDO apt-get install -y "python${PY_SHORT}-venv" python3-venv 2>/dev/null || \
            $SUDO apt-get install -y python3-venv
            ;;
        dnf)    $SUDO dnf install -y python3-virtualenv ;;
        pacman) : ;;  # venv bundled on Arch
    esac
fi

if "$PYTHON_CMD" -c "import venv" &>/dev/null; then
    ok "venv available"
else
    fail "venv module still missing."
    warn "Run:  sudo apt install python3-venv   then re-run this script."
    exit 1
fi

if ! "$PYTHON_CMD" -m pip --version &>/dev/null; then
    warn "pip not found — installing..."
    case "$PKG_MGR" in
        apt)    $SUDO apt-get install -y python3-pip ;;
        dnf)    $SUDO dnf install -y python3-pip ;;
        pacman) $SUDO pacman -Sy --noconfirm python-pip ;;
        *)      "$PYTHON_CMD" -m ensurepip --upgrade ;;
    esac
fi
ok "pip available"

# ── 4. Get install.py and run it ──────────────────────────────────────────────
echo ""
echo -e "${BOLD}  [4/4]  Running School MIS installer...${RESET}"
echo ""
echo -e "${CYAN}  ────────────────────────────────────────────────────────${RESET}"
echo ""

if [ "$DOWNLOAD_NEEDED" = true ]; then
    # Download install.py from GitHub into /tmp
    RAW_URL="https://raw.githubusercontent.com/$GITHUB_USER/$GITHUB_REPO/$GITHUB_BRANCH/install.py"
    TEMP_INSTALLER="/tmp/school_mis_install_$$.py"
    info "Downloading installer from GitHub..."

    DOWNLOAD_OK=false
    if   command -v curl &>/dev/null; then
        curl -fsSL "$RAW_URL" -o "$TEMP_INSTALLER" && DOWNLOAD_OK=true
    elif command -v wget &>/dev/null; then
        wget -q "$RAW_URL" -O "$TEMP_INSTALLER" && DOWNLOAD_OK=true
    else
        "$PYTHON_CMD" -c \
          "import urllib.request; urllib.request.urlretrieve('$RAW_URL','$TEMP_INSTALLER')" \
          && DOWNLOAD_OK=true
    fi

    if [ "$DOWNLOAD_OK" = false ] || [ ! -s "$TEMP_INSTALLER" ]; then
        fail "Could not download install.py from GitHub."
        echo ""
        warn "Possible reasons:"
        warn "  1. The repository is PRIVATE — make it Public in GitHub Settings"
        warn "     → github.com/$GITHUB_USER/$GITHUB_REPO → Settings → Danger Zone → Change visibility"
        warn "  2. The code has not been pushed yet"
        warn "     → Run:  git push  from inside the project folder"
        warn "  3. No internet connection"
        echo ""
        info "If you already have the code on this computer:"
        info "  cd /path/to/school_mis"
        info "  ./SETUP_LINUX.sh          (run from inside the folder)"
        rm -f "$TEMP_INSTALLER"
        exit 1
    fi

    ok "install.py downloaded"
    INSTALLER="$TEMP_INSTALLER"
    CLEANUP_INSTALLER=true

    "$PYTHON_CMD" "$INSTALLER" \
        --from-github \
        --repo "$GITHUB_USER/$GITHUB_REPO" \
        --branch "$GITHUB_BRANCH" \
        --dest "$INSTALL_DIR"
    EXIT_CODE=$?
else
    # Already in the repo — just run local install.py
    cd "$INSTALL_DIR"
    "$PYTHON_CMD" "$INSTALLER"
    EXIT_CODE=$?
fi

echo ""
echo -e "${CYAN}  ────────────────────────────────────────────────────────${RESET}"
echo ""

[ "${CLEANUP_INSTALLER:-false}" = true ] && rm -f "$INSTALLER"

if [ $EXIT_CODE -eq 0 ]; then
    ok "Installation complete!"
    if [ "$DOWNLOAD_NEEDED" = true ]; then
        ok "Installed to: $INSTALL_DIR"
        ok "Launch: School MIS in your applications menu"
        ok "Or run: ~/school_mis/run_school_mis.sh"
    else
        ok "Environment set up in: $INSTALL_DIR"
        ok "Run the app:  python main.py"
        ok "Or use the desktop shortcut / app menu entry"
    fi
else
    fail "Installation failed — see messages above."
fi
echo ""
exit $EXIT_CODE
