@echo off
setlocal EnableDelayedExpansion
title School MIS — Installer
color 0B
cls

echo.
echo  ╔══════════════════════════════════════════════════════╗
echo  ║   School Management Information System              ║
echo  ║   Installer for Windows                              ║
echo  ╚══════════════════════════════════════════════════════╝
echo.

REM ── GitHub settings (developer fills these in) ─────────────────────────────
set GITHUB_USER=Justine-Msechu
set GITHUB_REPO=school-mis
set GITHUB_BRANCH=main
set INSTALL_DIR=%USERPROFILE%\school_mis

REM ── Move to the folder containing this .bat ────────────────────────────────
cd /d "%~dp0"

REM ══════════════════════════════════════════════════════════════════════════
REM  Detect mode: do we already have install.py here?
REM ══════════════════════════════════════════════════════════════════════════
set DOWNLOAD_NEEDED=true
set LOCAL_INSTALLER=%~dp0install.py

if exist "%LOCAL_INSTALLER%" (
    echo  Mode: CODE ALREADY HERE — skipping GitHub download.
    echo  Working directory: %~dp0
    set DOWNLOAD_NEEDED=false
    set INSTALL_DIR=%~dp0
) else (
    echo  Mode: FRESH INSTALL — will download from GitHub.
    echo  Repository: https://github.com/%GITHUB_USER%/%GITHUB_REPO%
    echo  Destination: %INSTALL_DIR%
)
echo.

REM ══════════════════════════════════════════════════════════════════════════
REM  1. Find Python
REM ══════════════════════════════════════════════════════════════════════════
echo  [1/3]  Looking for Python...

set PYTHON_CMD=
python --version >nul 2>&1  && set PYTHON_CMD=python
if not defined PYTHON_CMD (
    python3 --version >nul 2>&1 && set PYTHON_CMD=python3
)
for %%P in (
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
    "C:\Python312\python.exe" "C:\Python311\python.exe"
) do (
    if not defined PYTHON_CMD (
        if exist %%P ( set PYTHON_CMD=%%P )
    )
)

if not defined PYTHON_CMD (
    echo.
    echo  [!] Python not found.
    echo      1. Go to https://www.python.org/downloads/
    echo      2. Download Python 3.12
    echo      3. IMPORTANT: Tick "Add Python to PATH"
    echo      4. Re-run this file.
    start https://www.python.org/downloads/
    pause & exit /b 1
)
echo         Python: !PYTHON_CMD!

REM ══════════════════════════════════════════════════════════════════════════
REM  2. Check pip
REM ══════════════════════════════════════════════════════════════════════════
echo  [2/3]  Checking pip...
!PYTHON_CMD! -m pip --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    !PYTHON_CMD! -m ensurepip --upgrade >nul 2>&1
)
echo         pip OK.

REM ══════════════════════════════════════════════════════════════════════════
REM  3. Run installer
REM ══════════════════════════════════════════════════════════════════════════
echo  [3/3]  Running School MIS installer...
echo.
echo  ────────────────────────────────────────────────────────
echo.

if "!DOWNLOAD_NEEDED!"=="false" (
    REM ── Already have the code — run locally ──────────────────────────────
    !PYTHON_CMD! "%LOCAL_INSTALLER%"
    set EXIT_CODE=!ERRORLEVEL!
) else (
    REM ── Download install.py from GitHub first ─────────────────────────────
    set RAW_URL=https://raw.githubusercontent.com/%GITHUB_USER%/%GITHUB_REPO%/%GITHUB_BRANCH%/install.py
    set TEMP_INSTALLER=%TEMP%\school_mis_install_%RANDOM%.py

    echo  Downloading installer from GitHub...
    powershell -NoProfile -Command ^
      "try { Invoke-WebRequest -Uri '!RAW_URL!' -OutFile '!TEMP_INSTALLER!' -UseBasicParsing } catch { exit 1 }" >nul 2>&1

    if not exist "!TEMP_INSTALLER!" (
        echo.
        echo  [!] Could not download from GitHub.
        echo.
        echo  Possible reasons:
        echo    1. The repository is PRIVATE
        echo       Go to: github.com/%GITHUB_USER%/%GITHUB_REPO% / Settings / Change visibility
        echo    2. The code has not been pushed yet
        echo       Run: git push  from inside the project folder
        echo    3. No internet connection
        echo.
        echo  If you already have the code on this computer:
        echo    Run SETUP_WINDOWS.bat from INSIDE the school_mis folder.
        echo.
        pause & exit /b 1
    )

    echo  Installer downloaded.
    !PYTHON_CMD! "!TEMP_INSTALLER!" --from-github --repo %GITHUB_USER%/%GITHUB_REPO% --branch %GITHUB_BRANCH% --dest "!INSTALL_DIR!"
    set EXIT_CODE=!ERRORLEVEL!
    del "!TEMP_INSTALLER!" >nul 2>&1
)

echo.
echo  ────────────────────────────────────────────────────────

if !EXIT_CODE! EQU 0 (
    echo.
    echo  Setup complete!
    if "!DOWNLOAD_NEEDED!"=="false" (
        echo  Run the app with:  python main.py
        echo  Or use the desktop shortcut / Start menu entry.
    ) else (
        echo  Use the desktop shortcut "School MIS" to launch the app.
    )
    echo.
) else (
    echo.
    echo  [!] Setup failed — see messages above.
    echo.
)
pause
exit /b !EXIT_CODE!
