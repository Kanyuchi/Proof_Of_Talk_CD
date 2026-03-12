# Blue/Green EC2 Deploy + Migration Runbook
## POT Matchmaker — Proof of Talk 2026

---

## Overview

| Instance | IP | Code | Purpose |
|---|---|---|---|
| Blue (old) | `54.89.55.202` | iter-9 and earlier | Original version, real attendee data |
| Green (new) | `<NEW_IP>` | iter-12 | Branded version with all fixes |
| Database | AWS RDS | shared | Same 23 attendees, same matches |

Both instances point at the same RDS — any attendee created on one is visible on the other.

---

## Phase 1 — Launch Green Instance

### Prerequisites
- [ ] `backend/.env` exists locally with valid RDS URL and OpenAI key
- [ ] `~/Downloads/Credentials_Keys/pot-key.pem` exists and is `chmod 400`
- [ ] You have AWS console access to launch an EC2 instance

### Step 1 — Launch the new instance in AWS Console (~5 min, manual)

1. Go to **EC2 → Instances → Launch Instance**
2. Configure:
   - **Name**: `pot-matchmaker-green`
   - **AMI**: Amazon Linux 2023 (same as blue instance)
   - **Instance type**: `t3.small`
   - **Key pair**: reuse `pot-key` (or create a new one — download it to `~/Downloads/Credentials_Keys/`)
   - **Security group**: reuse the existing group (ports 22 + 80 already open)
   - **Storage**: 20 GB gp3
3. Click **Launch** → wait ~60 seconds
4. Note the **Public IPv4 address** (e.g. `54.200.11.22`)

### Step 2 — One-command deploy to green instance

```bash
# From repo root on your Mac:
bash deploy/green-deploy.sh <NEW_IP> ~/Downloads/Credentials_Keys/pot-key.pem
```

This script:
1. Waits for SSH to be ready
2. Uploads `setup-ec2.sh` and `nginx.conf`
3. Runs first-time EC2 bootstrap (nginx, python3.12, systemd service)
4. Copies `backend/.env` to the new instance (adds new IP to `ALLOWED_ORIGINS`)
5. Builds the React frontend + rsyncs backend + runs alembic migrations
6. Restarts the service and reloads nginx
7. Runs a health check smoke test

Expected output ends with:
```
  Blue  (original): http://54.89.55.202
  Green (new code): http://<NEW_IP>
  Both share the same RDS database (23 attendees).
```

### Step 3 — Verify

```bash
# Health check
curl http://<NEW_IP>/health
# Expected: {"status":"ok","service":"POT Matchmaker"}

# Blue still running
curl http://54.89.55.202/health
```

Open both in browser side-by-side:
- `http://<NEW_IP>` — new POT orange brand, Playfair/Poppins fonts, bottom tab bar on mobile
- `http://54.89.55.202` — original version, untouched

Full verification checklist:
- [ ] Green: `/health` returns `{"status":"ok","service":"POT Matchmaker"}`
- [ ] Green: Landing page shows POT orange brand (not amber)
- [ ] Blue: Still running, no regressions
- [ ] Both: Same 23 attendees visible in attendee list
- [ ] Green: Register flow completes without URL validation error or JS `prompt()`
- [ ] Green: Mobile layout — bottom tab bar visible at 390px viewport
- [ ] Green: Match cards show explanations (if OpenAI quota is available)

### Troubleshooting

**SSH timeout during setup**
```bash
# Check instance is in "running" state in AWS console
# Retry after 60s — cloud-init takes time
ssh -i ~/Downloads/Credentials_Keys/pot-key.pem ec2-user@<NEW_IP>
```

**Service not starting**
```bash
ssh -i ~/Downloads/Credentials_Keys/pot-key.pem ec2-user@<NEW_IP> \
  'sudo journalctl -u pot-matchmaker -n 50 --no-pager'
```

**Nginx 502 Bad Gateway**
```bash
# Backend hasn't started yet — check service status
ssh -i ... ec2-user@<NEW_IP> 'sudo systemctl status pot-matchmaker'
# If .venv missing:
ssh -i ... ec2-user@<NEW_IP> \
  'cd /home/ec2-user/app/backend && python3.12 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt'
```

**OpenAI 429 quota error**
This only affects enrichment/match-gen, not the basic app. Top up credits at [platform.openai.com](https://platform.openai.com/settings/organization/billing) then:
```bash
ssh -i ... ec2-user@<NEW_IP> \
  'cd /home/ec2-user/app/backend && source .venv/bin/activate && python scripts/pipeline_live.py --target live --skip-enrichment'
```

---

## Phase 2 — Supabase + Netlify Migration

**Trigger**: team approves green instance after side-by-side comparison.

### What moves where

| Layer | From | To |
|---|---|---|
| Frontend | EC2 nginx | Netlify (free CDN, custom domain) |
| Backend API | EC2 gunicorn | Render.com or Railway (always-on, ~$7/mo) |
| Database | AWS RDS | Supabase Pro ($25/mo, pgvector native) |

### What you need from the manager before starting

| Item | Service | Where to find it |
|---|---|---|
| PostgreSQL connection string | Supabase | Dashboard → Settings → Database → URI (use the `postgresql://` format) |
| Project URL | Supabase | Settings → API → Project URL |
| Service role key | Supabase | Settings → API → `service_role` (NOT anon key) |
| pgvector enabled | Supabase | Database → Extensions → search "vector" → Enable |
| Netlify team invite | Netlify | Manager adds your email to org team |
| Target domain | Netlify | e.g. `matchmaker.proofoftalk.com` |
| Backend host credentials | Render/Railway | Create account, connect GitHub repo |

### Phase 2 migration steps (~2–3 hrs)

#### 2a — Supabase schema + data
```bash
# 1. Set new DATABASE_URL in backend/.env (Supabase connection string)
#    Format: postgresql+asyncpg://postgres.<project-ref>:<password>@aws-0-eu-west-1.pooler.supabase.com:5432/postgres

# 2. Apply migrations against Supabase
cd backend
source .venv/bin/activate
alembic upgrade head

# 3. Re-ingest real attendee data
python scripts/pipeline_live.py --target live --skip-enrichment

# 4. Verify 23 attendees present
curl http://localhost:8000/api/v1/attendees | python3 -c "import sys,json; data=json.load(sys.stdin); print(len(data))"
```

Or for a full copy including embeddings and matches (faster):
```bash
# pg_dump from RDS, restore to Supabase
pg_dump "$OLD_DATABASE_URL" | psql "$SUPABASE_DATABASE_URL"
```

#### 2b — Backend on Render/Railway
```bash
# Render: connect GitHub repo at render.com/new
# Set environment variables from backend/.env in the Render dashboard
# Build command: pip install -r requirements.txt
# Start command: gunicorn -c gunicorn.conf.py app.main:app
# Note the backend URL: https://pot-matchmaker-api.onrender.com
```

#### 2c — Frontend on Netlify
```bash
cd frontend

# Update API URL to point at new backend
# In frontend/.env.production (or netlify env vars):
# VITE_API_URL=https://pot-matchmaker-api.onrender.com

npm run build

# Deploy (first time)
npx netlify-cli deploy --prod --dir=dist

# Or: connect GitHub repo at app.netlify.com/start
# Build command: npm run build
# Publish directory: dist
```

#### 2d — DNS + custom domain
```bash
# In Netlify: Site settings → Domain management → Add custom domain
# DNS panel (manager's registrar): add CNAME
#   matchmaker.proofoftalk.com → <netlify-site>.netlify.app

# SSL is automatic via Let's Encrypt on Netlify
```

#### 2e — Update CORS
```bash
# In backend .env on Render/Railway:
ALLOWED_ORIGINS=https://matchmaker.proofoftalk.com,https://<netlify-site>.netlify.app
```

#### 2f — Smoke test new stack
```bash
curl https://pot-matchmaker-api.onrender.com/health
# Expected: {"status":"ok","service":"POT Matchmaker"}

# Open https://matchmaker.proofoftalk.com
# Full register → match → profile flow
```

#### 2g — Decommission old instances
```bash
# Only after 48h of stable operation on new stack:
# AWS Console → EC2 → Select both blue and green instances → Actions → Terminate
# AWS Console → RDS → Select pot-matchmaker DB → Actions → Delete
#   (take a final snapshot first)
```

---

## Environment Variable Reference

All instances share the same core variables. Only `ALLOWED_ORIGINS` changes per host.

```bash
# Required for all environments
DATABASE_URL=postgresql+asyncpg://...
OPENAI_API_KEY=sk-proj-...
SECRET_KEY=<64-char-hex>

# Per-instance
ALLOWED_ORIGINS=http://localhost:5173,http://54.89.55.202,http://<GREEN_IP>,https://matchmaker.proofoftalk.com

# Optional enrichment
PROXYCURL_API_KEY=
TWITTER_BEARER_TOKEN=
LINKEDIN_LI_AT_COOKIE=
LINKEDIN_CSRF_TOKEN=
```

---

## Quick Reference Commands

```bash
# Deploy to green instance (Phase 1)
bash deploy/green-deploy.sh <NEW_IP> ~/Downloads/Credentials_Keys/pot-key.pem

# Deploy to existing blue instance
bash deploy/push.sh 54.89.55.202 ~/Downloads/Credentials_Keys/pot-key.pem

# SSH into an instance
ssh -i ~/Downloads/Credentials_Keys/pot-key.pem ec2-user@<IP>

# View backend logs
sudo journalctl -u pot-matchmaker -f

# Restart services
sudo systemctl restart pot-matchmaker
sudo systemctl reload nginx

# Check service status
sudo systemctl status pot-matchmaker pot-matchmaker
```
