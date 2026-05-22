# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the app

```bash
# Normal run
python main.py

# Development mode — auto-restarts on any .py file save
python dev.py
```

The app requires Python 3.10+ and PyQt6:
```bash
pip install -r requirements.txt   # PyQt6>=6.6.0
```

## Releasing an update

After making code changes, always run this before pushing:
```bash
python tools/build_manifest.py --version X.Y.Z --notes "What changed"
git add version.json
git commit -m "Release vX.Y.Z"
git push
```

`version.json` must be committed for installed apps to detect the new version. The GitHub repo must be **public** — the auto-updater fetches `version.json` unauthenticated from `raw.githubusercontent.com`.

## Architecture

### Startup flow

`main.py` → `initialize_database()` → setup wizard (first run only) → `LoginDialog` → `MainWindow`

All three steps live in `run_app()` which is also called again after logout to restart the login flow without restarting the process.

### Data layer — `database/db.py`

Single SQLite file (`school_mis.db`, gitignored). All queries go through three helpers:
- `fetch_one(sql, params)` / `fetch_all(sql, params)` — reads
- `execute(sql, params)` — writes, returns `lastrowid`

`ROLES` dict in `db.py` is the single source of truth for role labels, colours, and permission lists. Every permission check in the app calls `session.can("module.action")` which reads from this dict.

### Session — `auth/session.py`

`session` is a module-level singleton imported everywhere. After `session.login(user_dict)` succeeds, `session.can()`, `session.is_admin`, `session.is_head_teacher` etc. are available app-wide. `session.logout()` clears state.

### UI structure — `ui/main_window.py`

`MainWindow` builds a dark sidebar (`#0F172A`) + a light content `QFrame`. Each module is instantiated once as a `QWidget` page inside a `QStackedWidget`. Navigation just calls `setCurrentWidget`.

The sidebar nav list is filtered at build time by `session.can(perm)` — modules the user lacks permission for are never instantiated.

### Themes — `ui/theme.py`

Three full Qt stylesheets: `LIGHT_STYLE`, `DARK_STYLE`, `OCEAN_STYLE`. The `THEMES` dict maps keys (`"light"`, `"dark"`, `"ocean"`) to stylesheet + `content_bg` colour. `GLOBAL_STYLE` is an alias for `LIGHT_STYLE` (used in `main.py`).

Theme preference is stored per-user in `school_config` as `theme_user_{user_id}`. `MainWindow.apply_theme(key)` calls `QApplication.setStyleSheet()` and updates the content frame background.

### Module pattern

Every feature module (`students`, `teachers`, `fees`, etc.) is a `QWidget` subclass with:
- A table (`QTableWidget`) for the list view
- Dialog subclasses (`QDialog`) for add/edit forms
- `_load_*()` method that re-queries the DB and repopulates the table

Inline button styles (`BTN_PRIMARY`, `BTN_OUTLINE`, `BTN_DANGER`) are defined as string constants at the top of each module file. These are not theme-aware — they stay consistent across themes.

### Access control rules

- **Admin** — full access, sees all users
- **Head Teacher** — cannot see, edit, deactivate, or assign admin-level accounts; can only assign `class_teacher` / `subject_teacher` roles
- Role filtering happens in `settings.py` (`_load_users`, `_edit_user`, `_deactivate_user`) and in `UserDialog` (role combo filtered by `editor_role` param)

### Auto-updater — `modules/updater.py`

`ConnectivityWatcher` (QThread) probes `8.8.8.8:53` every 30 s. On internet reconnect it triggers `StartupUpdateChecker`, which compares `version.json` versions. If a newer version is found, `MainWindow._show_update_banner()` shows a non-modal blue banner. Clicking **Install now** opens `UpdateDialog`, which runs `_DownloadThread` to fetch only changed files. On completion, `_restart_app()` spawns a fresh process and quits the current one.

Files excluded from the manifest and never downloaded: `run_school_mis.sh`, `SchoolMIS.desktop`, `venv/`, `school_mis.db`, installer scripts. These are controlled by `SKIP` in `tools/build_manifest.py` and `SKIP_PATHS` / `_should_skip()` in `updater.py`.

## Key conventions

- **No HTML/web tech** — 100% PyQt6. All UI is `QWidget`/`QDialog` subclasses with Qt stylesheets.
- **Inline styles over global classes** — widgets use `setStyleSheet(...)` directly. Only the global theme stylesheet (set via `QApplication`) and the three `BTN_*` constants are shared.
- **Passwords** — SHA-256 + random 16-byte hex salt. `hash_password()` and `verify_password()` in `db.py`.
- **Currency** — TZS (Tanzanian shilling). No conversion logic; amounts are stored as `REAL` in SQLite.
- **`github_config.py`** — single place to set `GITHUB_USERNAME` / `GITHUB_REPO`. Both the installer scripts and the updater derive all GitHub URLs from this file.
