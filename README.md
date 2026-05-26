# School Management Information System
**Web Edition — v2.2**

A browser-based school MIS designed for primary schools. Runs on a Raspberry Pi (or any Linux server) and is accessed by staff from any phone, tablet, or PC on the same network — no installation required on client devices.

---

## Architecture

| Layer | Technology |
|---|---|
| Backend API | Python / FastAPI |
| Frontend | React + TypeScript (Vite) |
| Database | SQLite |
| Server | Uvicorn (via systemd or Docker) |

---

## Deployment

See **[DEPLOY.md](DEPLOY.md)** for full instructions. Summary:

### Raspberry Pi (no Docker)

```bash
# 1. Clone the repo
git clone https://github.com/Justine-Msechu/school-mis.git /opt/school_mis
cd /opt/school_mis

# 2. Build the frontend
cd school-mis-app && npm ci && npm run build && cd ..

# 3. Create Python environment and install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt

# 4. Start the server
uvicorn backend.main:app --host 0.0.0.0 --port 8765
```

Open `http://<pi-ip>:8765` on any device on the same network.

### Docker (recommended for any server)

```bash
git clone https://github.com/Justine-Msechu/school-mis.git
cd school-mis
docker compose up -d --build
```

Access at `http://<server-ip>:8765`.

---

## Updating the server

### Raspberry Pi (systemd)

```bash
cd /opt/school_mis
git pull
cd school-mis-app && npm ci && npm run build && cd ..
sudo systemctl restart school-mis
sudo systemctl status school-mis
```

### Docker

```bash
cd /opt/school_mis
git pull
docker compose up -d --build
```

---

## Run as a systemd service (auto-start on boot)

```bash
sudo tee /etc/systemd/system/school-mis.service << 'EOF'
[Unit]
Description=School MIS
After=network.target

[Service]
User=pi
WorkingDirectory=/opt/school_mis
ExecStart=/opt/school_mis/venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8765
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable school-mis
sudo systemctl start school-mis
```

---

## First-run setup

On first launch the app shows a **Setup Wizard**:
1. Enter school name, address, and logo
2. Create the administrator account
3. Click **Finish** — the login page appears

---

## Roles & access control

| Role | Access |
|---|---|
| **Administrator** | Full access — settings, users, all modules |
| **Head Teacher** | All school operations, approve grades |
| **Academic Officer** | Enter/approve/publish exam results and reports |
| **Class Teacher** | Attendance for their class, view students |
| **Subject Teacher** | Enter grades for their subjects only |
| **Accountant** | Finance, payroll, and fee collection |
| **Librarian** | Library module only |
| **Transport Officer** | Transport routes and student assignments |

User accounts are managed under **Settings → Users & Access**.

---

## Project structure

```
school_mis/
├── backend/
│   ├── main.py              ← FastAPI app entry point
│   ├── deps.py              ← Auth dependencies & permission checks
│   ├── core/
│   │   └── db.py            ← Database connection helpers
│   ├── routers/             ← One file per module (students, finance, …)
│   ├── migrations/          ← Numbered DB migration scripts
│   └── requirements.txt
├── school-mis-app/          ← React/TypeScript frontend
│   ├── src/
│   │   ├── pages/           ← One page component per module
│   │   ├── api/             ← API client functions
│   │   ├── components/      ← Shared UI components
│   │   └── stores/          ← Zustand state stores
│   └── dist/                ← Built frontend (served by FastAPI)
├── database/
│   └── db.py                ← Schema initialisation & seed data
├── services/                ← Business logic shared across routers
├── Dockerfile
├── docker-compose.yml
└── DEPLOY.md                ← Full deployment guide
```

---

## Phone / tablet access

Once the server is running, staff open `http://<server-ip>:8765` in any browser.

- Works on Android (Chrome) and iPhone (Safari)
- Tap **"Add to Home Screen"** for an app-like shortcut
- No app installation needed

---

## Backup

All school data is in a single SQLite file:

```bash
# Manual backup
cp /opt/school_mis/school_mis.db "/opt/school_mis/backups/school_mis_$(date +%Y%m%d).db"

# Automated daily backup (add to crontab)
0 2 * * * cp /opt/school_mis/school_mis.db "/opt/school_mis/backups/school_mis_$(date +\%Y\%m\%d).db"
```
