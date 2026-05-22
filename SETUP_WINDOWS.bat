@echo off
setlocal EnableDelayedExpansion
title School MIS — Install from GitHub
color 0B
cls

echo.
echo  ╔══════════════════════════════════════════════════════╗
echo  ║   School Management Information System              ║
echo  ║   GitHub Installer for Windows                       ║
echo  ╚══════════════════════════════════════════════════════╝
echo.

REM ── Read GitHub repo from this file ───────────────────────────────────────
REM    The developer sets these two values before sharing this script.
set GITHUB_USER=Justine-Msechu
set GITHUB_REPO=school-mis
set GITHUB_BRANCH=main
set INSTALL_DIR=%USERPROFILE%\school_mis

REM ══════════════════════════════════════════════════════════════════════════
REM  Validate repo is configured
REM ══════════════════════════════════════════════════════════════════════════
if "%GITHUB_USER%"=="YOUR_GITHUB_USERNAME" (
    echo  [!] This installer has not been configured yet.
    echo      The developer needs to edit SETUP_WINDOWS.bat
    echo      and set GITHUB_USER and GITHUB_REPO.
    pause
    exit /b 1
)

echo  Repository : https://github.com/%GITHUB_USER%/%GITHUB_REPO%
echo  Installing to: %INSTALL_DIR%
echo.

REM ══════════════════════════════════════════════════════════════════════════
REM  1. Find Python
REM ══════════════════════════════════════════════════════════════════════════
echo  [1/4]  Checking Python...

set PYTHON_CMD=
python --version >nul 2>&1 && set PYTHON_CMD=python
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
    echo      3. Tick "Add Python to PATH"
    echo      4. Re-run this file.
    start https://www.python.org/downloads/
    pause
    exit /b 1
)
echo         Python found: !PYTHON_CMD!

REM ══════════════════════════════════════════════════════════════════════════
REM  2. Check / install pip
REM ══════════════════════════════════════════════════════════════════════════
echo  [2/4]  Checking pip...
!PYTHON_CMD! -m pip --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo         Installing pip...
    !PYTHON_CMD! -m ensurepip --upgrade >nul 2>&1
)
echo         pip OK.

REM ══════════════════════════════════════════════════════════════════════════
REM  3. Download install.py from GitHub (just this one file first)
REM ══════════════════════════════════════════════════════════════════════════
echo  [3/4]  Downloading installer from GitHub...
set RAW_URL=https://raw.githubusercontent.com/%GITHUB_USER%/%GITHUB_REPO%/%GITHUB_BRANCH%/install.py
set TEMP_INSTALLER=%TEMP%\school_mis_install.py

REM Use PowerShell to download
powershell -NoProfile -Command ^
  "Invoke-WebRequest -Uri '%RAW_URL%' -OutFile '%TEMP_INSTALLER%' -UseBasicParsing" >nul 2>&1

if not exist "%TEMP_INSTALLER%" (
    echo  [!] Failed to download installer from GitHub.
    echo      Check your internet connection and that the repo is public.
    echo      URL: %RAW_URL%
    pause
    exit /b 1
)
echo         Installer downloaded.

REM ══════════════════════════════════════════════════════════════════════════
REM  4. Run the installer (it will download the full repo)
REM ══════════════════════════════════════════════════════════════════════════
echo  [4/4]  Running School MIS installer...
echo.
echo  ────────────────────────────────────────────────────────
echo.

!PYTHON_CMD! "%TEMP_INSTALLER%" --from-github --repo %GITHUB_USER%/%GITHUB_REPO% --branch %GITHUB_BRANCH% --dest "%INSTALL_DIR%"
set EXIT_CODE=%ERRORLEVEL%

echo.
echo  ────────────────────────────────────────────────────────

if !EXIT_CODE! EQU 0 (
    echo.
    echo  Setup complete! Use the desktop shortcut to open the app.
    echo.
) else (
    echo.
    echo  [!] Setup encountered an error. See messages above.
    echo.
)

del "%TEMP_INSTALLER%" >nul 2>&1
pause
exit /b !EXIT_CODE!
