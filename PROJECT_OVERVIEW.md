# School Management Information System (School MIS) v2.0

## Project Summary

A cross-platform desktop application for managing primary school operations. Built with Python and PyQt6, it runs fully offline with a local SQLite database and includes a GitHub-based auto-updater for seamless distribution.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.10+ |
| GUI Framework | PyQt6 (v6.6.0+) |
| Database | SQLite3 (local, per-school) |
| Distribution | GitHub + smart installer |
| Platforms | Windows, Linux |

**Key libraries:** `PyQt6`, `sqlite3`, `hashlib`, `secrets`, `urllib`, `json`, `pathlib`

---

## Project Structure

```
school_mis/
├── main.py                   # Entry point: DB init → setup wizard → login → main window
├── github_config.py          # GitHub repo config (auto-updater/installer)
├── version.json              # Version manifest with SHA-256 file hashes
├── version_info.py           # Version reader utility
├── requirements.txt          # PyQt6>=6.6.0
├── install.py                # Smart cross-platform installer
│
├── auth/
│   └── session.py            # Global session: current user, role, permissions
│
├── database/
│   └── db.py                 # SQLite schema + auth helpers + config storage
│
├── modules/
│   ├── setup_wizard.py       # First-run 4-step configuration wizard
│   ├── login.py              # Login dialog with role validation
│   ├── dashboard.py          # Home page with stats cards
│   ├── students.py           # Student enrollment CRUD
│   ├── teachers.py           # Staff management
│   ├── classes.py            # Class groups & assignments
│   ├── attendance.py         # Daily attendance marking
│   ├── fees.py               # Fee types, payments, receipts
│   ├── settings.py           # Admin: users, roles, school info, academic years
│   └── updater.py            # GitHub-based auto-update system
│
├── ui/
│   ├── main_window.py        # Sidebar + role-aware navigation
│   └── theme.py              # Global Qt stylesheet
│
├── tools/
│   └── build_manifest.py     # Pre-release: scans files, generates version.json
│
├── assets/                   # School logos (git-ignored)
├── exports/                  # PDFs/Excel (git-ignored)
├── SETUP_WINDOWS.bat         # Automated Windows installer
└── SETUP_LINUX.sh            # Automated Linux installer
```

---

## Application Flow

```
Start App
   └── Check setup_complete flag
         ├── First run → SetupWizard (4 steps) → Save school config
         └── Already set up → LoginDialog → Authenticate
                                   └── Create session
                                         └── MainWindow
                                               └── Load modules by role
                                                     └── Logout → Close
```

---

## Database Schema (SQLite — 13+ tables)

| Table | Purpose |
|-------|---------|
| `school_config` | Key-value store (school name, logo, setup status) |
| `academic_years` | School terms/years (start_date, end_date, is_current) |
| `teachers` | Staff records (name, qualification, hire_date, contact) |
| `users` | Login accounts (username, password_hash, salt, role) |
| `classes` | Class groups (name, grade_level, capacity, room, teacher) |
| `students` | Enrollment (admission_no, name, DOB, class, parents, address) |
| `subjects` | Curriculum (name, code, grade_level) |
| `teacher_subjects` | Many-to-many: teacher ↔ subject ↔ class |
| `timetable` | Weekly schedule (class, subject, teacher, day, time) |
| `attendance` | Daily roll call (student, date, status) |
| `exams` | Assessment events (name, term, dates, status) |
| `grades` | Exam scores (student, exam, subject, score, approval) |
| `fee_types` | School charges (name, amount, term) |
| `fee_payments` | Payment records (student, amount, date, receipt_no, method) |
| `audit_log` | Activity tracking (user, action, table, timestamp) |

---

## Core Features

### 1. First-Run Setup Wizard
4-step wizard on first launch:
- **Step 1:** School information (name, address, logo)
- **Step 2:** Create administrator account
- **Step 3:** Optional head teacher setup
- **Step 4:** Confirmation & finish

### 2. Authentication & Role-Based Access Control

5 roles with progressive permissions:

| Role | Access |
|------|--------|
| **Admin** | Full system access (`*`) |
| **Head Teacher** | Students, teachers, grades, fees, reports |
| **Academic Officer** | Grades, exams, results publishing |
| **Class Teacher** | Attendance for their class, view students & grades |
| **Subject Teacher** | Enter grades for assigned subjects only |

- Passwords: SHA-256 + random salt (no plaintext stored)
- Session singleton: `session.can("module.action")` checks throughout app

### 3. Dashboard
Live stat cards on the home page:
- Total active students
- Active teachers
- Class count
- Today's attendance (present / absent)
- Fees collected this month (TZS currency)

### 4. Students Module
- Enrol new students (auto-generated admission numbers: ST0001, ST0002…)
- Edit student info (name, DOB, class, parents, address)
- Search & filter by admission no, name, class
- Soft-deactivate students

### 5. Teachers Module
- Add/manage staff records (name, gender, qualification, phone, email)
- Active/inactive status
- Link teachers to classes & subjects

### 6. Classes Module
- Create class groups (e.g., Grade 1A, Grade 5B)
- Assign class teacher, capacity, and room
- View enrolled students

### 7. Attendance System
- Mark daily roll call by class & date
- Statuses: Present, Absent, Late, Excused
- Quick "Mark all present" button
- One record per student per date (enforced by unique constraint)

### 8. Grades & Exams
- Create exam events (name, term, date range)
- Enter scores per student/subject/exam
- Score → letter grade conversion
- Approval workflow: draft → submitted → approved
- Remarks per student

### 9. Fees Module
- Define fee types (tuition, uniform, lunch, etc.) by term
- Record payments (amount, date, method)
- Auto-generate receipt numbers (RCP + 6 digits)
- Monthly fee totals on dashboard (TZS)

### 10. Settings & Administration
- User account management (add, edit, delete)
- Role assignment
- Link user accounts to teacher records
- Edit school info & logo
- Manage academic years
- Admin-only access

### 11. Auto-Updater
- Checks GitHub on startup for new version
- Downloads only changed files (delta updates via SHA-256 manifest)
- Backs up existing files before update
- Restarts app after successful update

---

## UI Architecture

Built entirely in **PyQt6** (no HTML/CSS):

- **MainWindow:** Dark sidebar (#0F172A) + light content area (#F3F4F6)
- **Sidebar navigation:** Role-aware — only shows permitted modules
- **Pages:** Each module is a `QWidget` in a `QStackedWidget`
- **Dialogs:** Modal `QDialog` forms for all CRUD operations
- **Tables:** `QTableWidget` with search, double-click edit, right-click context menus
- **Styling:** Centralized in `theme.py` (primary buttons, outline buttons, danger buttons)

---

## Distribution & Installation

### For End Users

**Windows:**
1. Download `SETUP_WINDOWS.bat`
2. Double-click → auto-detects Python, downloads repo, sets up venv, creates shortcut

**Linux:**
1. Download `SETUP_LINUX.sh`
2. Run: `chmod +x SETUP_LINUX.sh && ./SETUP_LINUX.sh`

### For Developers
```bash
git clone <repo>
python install.py      # set up local dev environment
python main.py         # run the app
```

### Release Workflow
```bash
# 1. Make changes, commit & push
# 2. Generate new version manifest
python tools/build_manifest.py --version 2.1.0 --notes "What changed"
# 3. Commit version.json → push to GitHub
# 4. Installed apps auto-detect & apply the update on next launch
```

---

## Security

| Concern | Implementation |
|---------|---------------|
| Passwords | SHA-256 + random salt |
| SQL injection | Parameterized queries throughout |
| Authorization | RBAC — checked on every action |
| Audit trail | `audit_log` table (in progress) |
| Update integrity | SHA-256 hash verification before applying updates |

---

## Current Status

- **Version:** 2.0 (initial release)
- **Branch:** `main`
- **Last commit:** `dc3f49c — Initial release v2.0`
- **Known in-progress:** Audit log (partially implemented), PDF/Excel exports (folder scaffolded)
