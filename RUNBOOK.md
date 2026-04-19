## FEXERJ Portal — Operations Runbook

Day-to-day deploy / restart / diagnose commands for the FEXERJ Portal.
Two deployment targets are supported — pick the section that matches your host.

- [Synology NAS (Docker Compose)](#synology-nas-docker-compose) — current production host
- [AWS EC2 (systemd + Nginx)](#aws-ec2-systemd--nginx) — legacy / on-demand

Code architecture, API payloads, and file formats live in [`README.md`](README.md).
Calculator internals live in [`CALCULATOR.md`](CALCULATOR.md).

---

### Environments

| Environment | Branch    | Typical domain                | Notes                              |
|-------------|-----------|-------------------------------|------------------------------------|
| Production  | `master`  | `fexerj.<your-domain>`        | `PORTAL_ENVIRONMENT=production`    |
| UAT         | `develop` | `uat.fexerj.<your-domain>`    | `PORTAL_ENVIRONMENT=development`   |

Verify which revision is actually serving traffic by looking at the footer of the login/run pages:

> `Frontend <short-sha> · <local date/time>`

The short SHA is injected at build time (`vite.config.js` → `BuildStamp`). If it does not match the merged commit, your build is stale.

---

## Synology NAS (Docker Compose)

Assumptions (set in `scripts/deploy-synology.conf`):

- **Prod dir** on NAS: e.g. `/volume1/docker/fexerj-portal-prod`
- **UAT dir** on NAS: e.g. `/volume1/docker/fexerj-portal-uat`
- **Compose project names**: `fexerj-prod` / `fexerj-uat`
- **Containers**: `fexerj-<env>-nginx-1`, `fexerj-<env>-backend-1`

`docker compose` commands on the NAS require `sudo` (Synology permission model). Always pass `-p <project>` so you're looking at the right stack.

---

### Deploy (from your laptop)

```bash
bash scripts/deploy-synology.sh prod   # master → production stack
bash scripts/deploy-synology.sh uat    # develop → UAT stack
```

The script SSHs into the NAS, fast-forwards the checked-out branch, rebuilds the frontend, and runs `docker compose ... up -d --build`. Before building the **`nginx`** image it sets **`BUILD_COMMIT`** from **`git rev-parse --short`** on the NAS repo so the footer shows that Git short SHA (not `unknown`). **The same SHA on UAT and prod means the same frontend bundle** (same codebase at image build time). Manual **`docker compose ... --build`** on the NAS should run `export BUILD_COMMIT=$(git rev-parse --short HEAD)` from the deploy directory first. On any deploy failure it automatically resets the NAS working copy to the previous commit and rebuilds — the previous version is restored without manual intervention.

First-time run per environment: prompts for `PORTAL_USER` / `PORTAL_PASSWORD` and writes them to `<deploy_dir>/.env` (chmod 600).

---

### Confirm the new code is actually running

From your laptop, after the script prints "Portal is live":

1. Open `https://<env-domain>/` and read the build stamp in the footer — compare the short SHA with the commit you just deployed.
2. Or hit the health endpoint:

```bash
curl -sS https://<env-domain>/health
```

From the NAS, check the checked-out commit directly:

```bash
cd /volume1/docker/fexerj-portal-<env>
git rev-parse HEAD
git log -1 --oneline
```

---

### Logs

Combined backend + nginx stack logs (follow live):

```bash
cd /volume1/docker/fexerj-portal-<env>
sudo docker compose -f docker-compose.yml -p fexerj-<env> logs -f --tail 200
```

Backend-only:

```bash
sudo docker compose -f docker-compose.yml -p fexerj-<env> logs --tail 300 backend
```

Container Nginx (proxy in front of the backend, inside the stack):

```bash
sudo docker compose -f docker-compose.yml -p fexerj-<env> logs --tail 300 nginx
```

> UAT uses `docker-compose.uat.yml`.

---

### Start / stop / restart

```bash
cd /volume1/docker/fexerj-portal-<env>

sudo docker compose -f docker-compose.yml -p fexerj-<env> up -d        # start (or apply config change)
sudo docker compose -f docker-compose.yml -p fexerj-<env> restart      # restart all services
sudo docker compose -f docker-compose.yml -p fexerj-<env> restart backend
sudo docker compose -f docker-compose.yml -p fexerj-<env> down         # stop and remove containers
```

---

### Changing credentials

```bash
sudo nano /volume1/docker/fexerj-portal-<env>/.env
sudo docker compose -f docker-compose.yml -p fexerj-<env> restart backend
```

Keep `PORTAL_PASSWORD` ≥ 8 chars; on prod, `PORTAL_ENVIRONMENT=production` is required — the backend refuses to start with `changeme` or short passwords.

---

### Manual rollback (Synology)

`deploy-synology.sh` auto-rolls back on failure. To roll back manually to a specific commit on the NAS:

```bash
cd /volume1/docker/fexerj-portal-<env>
git fetch origin
git reset --hard <commit-sha>
cd frontend && npm ci --silent && npm run build && cd ..
sudo docker compose -f docker-compose.yml -p fexerj-<env> up -d --build
```

---

### Reverse-proxy notes (Synology DSM)

Synology DSM terminates TLS and forwards to the container Nginx on a local port. Two common symptoms to know about:

- **HTTP 413 / truncated uploads** → raise `client_max_body_size` in DSM's reverse-proxy custom headers *and* bump `PORTAL_MAX_UPLOAD_MEGABYTES` in `.env`.
- **HTTP 504 on `/run`** → raise `proxy_read_timeout` in DSM's reverse-proxy settings. The rating cycle can take a while on large binaries.

---

## AWS EC2 (systemd + Nginx)

Used for on-demand launches from a laptop. The instance is terminated when not in use.

### Launch / terminate

```bash
bash scripts/launch.sh prod         # fresh EC2 instance, master branch
bash scripts/launch.sh uat          # fresh EC2 instance, develop branch
bash scripts/terminate.sh <env>     # destroy the instance (Elastic IP is preserved)
```

`launch.sh` polls `https://<domain>/health` and prints elapsed time when the portal answers (~8 minutes typical).

---

### Initial server setup (on a fresh Ubuntu 24.04 EC2)

```bash
git clone https://github.com/pedrofaraco/fexerj-portal.git
cd fexerj-portal
sudo bash scripts/setup.sh
```

The script prompts for domain + credentials, then installs system packages, Node, Python venv, builds the frontend, writes `/etc/fexerj-portal.env` (chmod 600), registers the `fexerj-portal` systemd service, configures Nginx, and issues a Let's Encrypt cert via Certbot.

> The domain must already resolve to the public IP before running — Certbot needs DNS.

---

### Deploy updates (on an already-provisioned EC2)

After merging into `master`, SSH in and run:

```bash
cd fexerj-portal
bash scripts/update.sh
```

Pulls the latest code, updates dependencies, rebuilds the frontend, restarts the service. If any step fails, it auto-reverts to the previous commit, rebuilds, and restarts — no manual rollback needed in the common case.

Manual rollback to a specific commit:

```bash
cd fexerj-portal
git fetch origin
git reset --hard <commit-sha>
source .venv/bin/activate
pip install -r requirements.txt
cd frontend && npm ci --silent && npm run build && cd ..
sudo systemctl restart fexerj-portal
sudo systemctl reload nginx
```

---

### Start / stop / restart (EC2)

```bash
sudo systemctl status  fexerj-portal
sudo systemctl restart fexerj-portal
sudo systemctl stop    fexerj-portal
sudo systemctl start   fexerj-portal
sudo systemctl reload  nginx
```

---

### Logs (EC2)

Application:

```bash
sudo journalctl -u fexerj-portal -f
sudo journalctl -u fexerj-portal --since "30 min ago"
```

Nginx:

```bash
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

---

### Changing credentials (EC2)

```bash
sudo nano /etc/fexerj-portal.env
sudo systemctl restart fexerj-portal
```

Keep `PORTAL_ENVIRONMENT=production` on public hosts and ensure `PORTAL_PASSWORD` meets the length / non-default rules.

---

## Common ops

### Healthcheck (both deployments)

```bash
curl -sS https://<env-domain>/health                   # unauthenticated
curl -sS -u "$PORTAL_USER:$PORTAL_PASSWORD" https://<env-domain>/me
```

`GET /health` returns `{"status":"ok"}` when the backend is up. Any 5xx or timeout = investigate (see triage loop below).

---

### Triage loop (when something looks wrong)

1. **Frontend build stamp** — does the footer match the merged commit? If not, the deploy didn't take.
2. **Health endpoint** — `curl -sS https://<domain>/health`. 502 = container/systemd down; 504 = proxy timeout (see reverse-proxy notes).
3. **Backend logs** — look for tracebacks around the failing request timestamp.
   - Synology: `sudo docker compose -f docker-compose.yml -p fexerj-<env> logs --tail 300 backend`
   - EC2: `sudo journalctl -u fexerj-portal --since "15 min ago"`
4. **Proxy logs** — if the backend shows no error, the failure is in front of it.
   - Synology container nginx: `... logs --tail 300 nginx`
   - Synology DSM reverse proxy: **Control Panel → Login Portal → Advanced → Reverse Proxy → <rule> → Log**
   - EC2: `/var/log/nginx/error.log`
5. **Request correlation** — every request gets an `X-Request-ID` header (see `backend/request_id.py`). Grep for it across logs to pin down a single request:

   ```bash
   sudo docker compose -f docker-compose.yml -p fexerj-<env> logs backend | grep "<request-id>"
   ```

---

### Error-code cheat sheet

| Status | Likely cause | Where to look |
|-------:|--------------|---------------|
| `401`  | Missing / wrong Basic auth | Browser sent no credentials, or credentials differ from `.env` / `/etc/fexerj-portal.env` |
| `413`  | Upload exceeded `PORTAL_MAX_UPLOAD_MEGABYTES` (or proxy limit) | `.env` + reverse-proxy `client_max_body_size` |
| `422`  | Validation rejected the request (bad CSV, unknown player id, etc.) | Backend returns a human-readable Portuguese message in `detail` |
| `500`  | Uncaught backend exception | Backend traceback |
| `502`  | Proxy can't reach the backend | Container/systemd is down or crashing on startup |
| `504`  | Proxy timed out waiting for backend | Long-running `/run`; raise `proxy_read_timeout` |

---

### Running the test suites locally

```bash
source .venv/bin/activate
pytest -q                                     # backend + calculator — 80% coverage gate
( cd frontend && npx vitest run )             # frontend unit tests
( cd frontend && npm run lint )               # ESLint
```
