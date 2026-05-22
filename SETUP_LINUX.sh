#!/bin/bash
# School MIS — GitHub Installer for Linux
# ─────────────────────────────────────────────────────────────────────────────
# The developer sets GITHUB_USER and GITHUB_REPO below before sharing.
# Users just run:  chmod +x SETUP_LINUX.sh && ./SETUP_LINUX.sh

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

echo ""
echo -e "${CYAN}${BOLD}╔══════════════════════════════════════════════════════╗${RESET}"
echo -e "${CYAN}${BOLD}║   School Management Information System              ║${RESET}"
echo -e "${CYAN}${BOLD}║   GitHub Installer for Linux                         ║${RESET}"
echo -e "${CYAN}${BOLD}╚══════════════════════════════════════════════════════╝${RESET}"
echo ""

# ── Validate configured ───────────────────────────────────────────────────────
if [ "$GITHUB_USER" = "YOUR_GITHUB_USERNAME" ]; then
    fail "This installer has not been configured."
    warn "The developer must set GITHUB_USER and GITHUB_REPO in this file."
    exit 1
fi

info "Repository : https://github.com/$GITHUB_USER/$GITHUB_REPO"
info "Installing to: $INSTALL_DIR"

# ── 1. Detect package manager ──────────────────────────────────────────────────
echo ""
echo -e "${BOLD}  [1/5]  Detecting system...${RESET}"
PKG_MGR=""
command -v apt-get &>/dev/null && PKG_MGR="apt"
command -v dnf     &>/dev/null && PKG_MGR="${PKG_MGR:-dnf}"
command -v pacman  &>/dev/null && PKG_MGR="${PKG_MGR:-pacman}"
DISTRO=$(grep -oP '(?<=^NAME=).+' /etc/os-release 2>/dev/null | tr -d '"' || echo "Linux")
ok "Distro: $DISTRO  |  Package manager: ${PKG_MGR:-unknown}"

# ── 2. Find or install Python 3.10+ ───────────────────────────────────────────
echo ""
echo -e "${BOLD}  [2/5]  Checking Python...${RESET}"
PYTHON_CMD=""
for cmd in python3.12 python3.11 python3.10 python3 python; do
    if command -v "$cmd" &>/dev/null; then
        VER=$("$cmd" --version 2>&1 | awk '{print $2}')
        MAJ=$(echo "$VER" | cut -d. -f1)
        MIN=$(echo "$VER" | cut -d. -f2)
        if [ "$MAJ" -ge 3 ] && [ "$MIN" -ge 10 ]; then
            PYTHON_CMD="$cmd"; ok "Python $VER ($cmd)"; break
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    warn "Python 3.10+ not found — installing..."
    SUDO=""; [ "$EUID" -ne 0 ] && SUDO="sudo"
    case "$PKG_MGR" in
        apt)    $SUDO apt-get update -qq && $SUDO apt-get install -y python3.12 python3.12-venv python3-pip 2>/dev/null \
                    || $SUDO apt-get install -y python3 python3-venv python3-pip ;;
        dnf)    $SUDO dnf install -y python3.12 python3-pip 2>/dev/null || $SUDO dnf install -y python3 python3-pip ;;
        pacman) $SUDO pacman -Sy --noconfirm python python-pip ;;
        *)      fail "Cannot auto-install Python. Please install Python 3.10+ manually."; exit 1 ;;
    esac
    PYTHON_CMD="python3"
    ok "Python installed"
fi

# ── 3. Ensure venv + pip ──────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}  [3/5]  Checking dependencies...${RESET}"
SUDO=""; [ "$EUID" -ne 0 ] && SUDO="sudo"

if ! "$PYTHON_CMD" -c "import venv" &>/dev/null; then
    warn "python3-venv not found — installing..."
    PY_SHORT=$("$PYTHON_CMD" -c "import sys;print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    case "$PKG_MGR" in
        apt)    $SUDO apt-get install -y "python${PY_SHORT}-venv" python3-venv 2>/dev/null || true ;;
        dnf)    $SUDO dnf install -y python3-virtualenv ;;
    esac
fi
ok "venv available"

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

# ── 4. Download install.py from GitHub ────────────────────────────────────────
echo ""
echo -e "${BOLD}  [4/5]  Downloading installer from GitHub...${RESET}"
RAW_URL="https://raw.githubusercontent.com/$GITHUB_USER/$GITHUB_REPO/$GITHUB_BRANCH/install.py"
TEMP_INSTALLER="/tmp/school_mis_install.py"

if command -v curl &>/dev/null; then
    curl -fsSL "$RAW_URL" -o "$TEMP_INSTALLER"
elif command -v wget &>/dev/null; then
    wget -q "$RAW_URL" -O "$TEMP_INSTALLER"
else
    # Fall back to Python urllib
    "$PYTHON_CMD" -c "import urllib.request; urllib.request.urlretrieve('$RAW_URL','$TEMP_INSTALLER')"
fi

if [ ! -f "$TEMP_INSTALLER" ]; then
    fail "Failed to download installer from GitHub."
    warn "Check your internet and that the repo is public."
    warn "URL: $RAW_URL"
    exit 1
fi
ok "Installer downloaded"

# ── 5. Run the installer ───────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}  [5/5]  Installing School MIS...${RESET}"
echo ""
echo -e "${CYAN}  ────────────────────────────────────────────────────────${RESET}"
echo ""

"$PYTHON_CMD" "$TEMP_INSTALLER" \
    --from-github \
    --repo "$GITHUB_USER/$GITHUB_REPO" \
    --branch "$GITHUB_BRANCH" \
    --dest "$INSTALL_DIR"
EXIT_CODE=$?

echo ""
echo -e "${CYAN}  ────────────────────────────────────────────────────────${RESET}"
echo ""

rm -f "$TEMP_INSTALLER"

if [ $EXIT_CODE -eq 0 ]; then
    ok "School MIS installed at: $INSTALL_DIR"
    ok "Launch it from your applications menu or run: ~/school_mis/run_school_mis.sh"
else
    fail "Installation failed — see messages above."
fi
echo ""
exit $EXIT_CODE
