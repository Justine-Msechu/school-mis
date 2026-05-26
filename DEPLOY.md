# School MIS — Deployment Guide

## Option 1: Docker (Recommended for any server)

Works on Linux servers, Raspberry Pi 4/5, VPS, or any machine with Docker.

### Quick start

```bash
# 1. Clone the repo on the server
git clone <your-repo-url> school_mis
cd school_mis

# 2. Build and start
docker compose up -d --build

# 3. Open in browser
# http://<server-ip>:8765
```

The database is stored in a Docker volume (`db_data`) — it persists when you update the container.

### Updating the app

```bash
git pull
docker compose up -d --build
```

---

## Option 2: Raspberry Pi (without Docker)

A Raspberry Pi 4 (2 GB RAM) handles this system easily for a single school
(up to ~500 concurrent users with SQLite WAL mode).

### Hardware requirements

| Model       | RAM  | OK for production? |
|-------------|------|--------------------|
| Pi 3B+      | 1 GB | Yes (light load)   |
| **Pi 4 2GB**| 2 GB | **Recommended**    |
| Pi 4 4GB+   | 4 GB | Ideal              |
| Pi 5        | 4 GB | Best performance   |

Use a **Class 10 microSD** or, better, an **SSD via USB 3** (SQLite on SD cards
degrades quickly under write load).

### Setup on Raspberry Pi OS (64-bit)

```bash
# 1. Update system
sudo apt update && sudo apt upgrade -y

# 2. Install Python 3.11+ and Node 20
sudo apt install -y python3 python3-pip python3-venv curl
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# 3. Clone the repo
git clone <your-repo-url> /opt/school_mis
cd /opt/school_mis

# 4. Build the frontend
cd school-mis-app
npm ci
npm run build
cd ..

# 5. Create Python venv and install deps
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 6. Run it
SCHOOL_MIS_STATIC_DIR=/opt/school_mis/school-mis-app/dist \
  uvicorn backend.main:app --host 0.0.0.0 --port 8765
```

### Run as a systemd service (auto-start on boot)

```bash
sudo tee /etc/systemd/system/school-mis.service << 'EOF'
[Unit]
Description=School MIS
After=network.target

[Service]
User=pi
WorkingDirectory=/opt/school_mis
Environment="SCHOOL_MIS_STATIC_DIR=/opt/school_mis/school-mis-app/dist"
ExecStart=/opt/school_mis/venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8765
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable school-mis
sudo systemctl start school-mis

# Check it's running
sudo systemctl status school-mis
```

After this, the system starts automatically on every reboot.

### Find the Pi's IP address

```bash
hostname -I
```

All devices on the same WiFi/LAN can access it at `http://<pi-ip>:8765`.

---

## Option 3: VPS / Cloud (production SaaS)

For multi-school SaaS deployment:

1. Use **Docker Compose** (Option 1) on a Ubuntu 22.04 VPS (2 vCPU, 2 GB RAM minimum)
2. Put **Nginx** in front as a reverse proxy (handles HTTPS via Let's Encrypt)
3. Use a custom domain

```nginx
# /etc/nginx/sites-available/school-mis
server {
    listen 80;
    server_name mis.yourschool.com;

    location / {
        proxy_pass http://127.0.0.1:8765;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

Then run: `sudo certbot --nginx -d mis.yourschool.com`

---

## Accessing from phones

Once the server is running (any option above), staff can use the system from
any phone or tablet on the same network by opening:

```
http://<server-ip>:8765
```

No app install needed — it's a mobile-responsive web app.

**Tips for phone access:**
- Staff can tap "Add to Home Screen" in their browser for an app-like shortcut
- Works on Android (Chrome) and iPhone (Safari)
- For use outside the school network, expose the server via a domain + HTTPS

---

## Backup

The entire school data is in one file. Back it up regularly:

```bash
# Simple daily backup (add to cron)
cp /opt/school_mis/school_mis.db "/opt/school_mis/backups/school_mis_$(date +%Y%m%d).db"

# Or for Docker:
docker run --rm -v school_mis_db_data:/data -v $(pwd):/backup alpine \
  cp /data/school_mis.db /backup/school_mis_backup.db
```
