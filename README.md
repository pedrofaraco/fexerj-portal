# fexerj-portal

Web portal for the FEXERJ chess community — rating lists, player database, and staff tools.

## Features

- **Rating Cycle Runner** — Portuguese-language staff interface to upload tournament files, validate inputs, and download updated rating lists as a zip archive
- Public rating lists and player database *(planned)*

## Tech Stack

- **Backend**: FastAPI (Python)
- **Frontend**: React + Vite + Tailwind CSS
- **Auth**: HTTP Basic auth, credentials via environment variables
- **Hosting**: AWS EC2 + Nginx + HTTPS

## Project Structure

```
backend/      # FastAPI application, configuration, and input validator
calculator/   # Rating calculator library
frontend/     # React frontend (Vite)
tests/        # Backend and validator test suite (pytest)
```

## Development Setup

**Backend**

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest tests/
```

**Frontend**

```bash
cd frontend
npm install
npm test
```

## Running Locally

Run both servers simultaneously (two terminal tabs):

```bash
# Backend
source .venv/bin/activate
uvicorn backend.main:app --reload

# Frontend
cd frontend && npm run dev
```

Then open `http://localhost:5173`. The frontend proxies `/health`, `/me`, `/validate`, and `/run` to the backend automatically.

Credentials are configured via environment variables:

```bash
export PORTAL_USER=youruser
export PORTAL_PASSWORD=yourpassword
```

A `.env` file in the project root is also supported.

**Environment:** `PORTAL_ENVIRONMENT` is `development` by default. Use **`production`** only on internet-facing servers; the API then **refuses to start** with the placeholder password `changeme` or with passwords shorter than **8** characters. For local work, omit this variable or keep `development`.

**Upload size:** `PORTAL_MAX_UPLOAD_MEGABYTES` (optional, default **100**, allowed range **1–2048**) sets the maximum total body size in mebibytes for `POST /validate` and `POST /run`. The server checks the `Content-Length` header; if it is absent, this limit is not applied at the middleware layer (use a reverse proxy limit in production as well).

## Input File Formats

**players.csv** — semicolon-delimited, UTF-8 (BOM accepted):

```
Id_No;Id_CBX;Title;Name;Rtg_Nat;ClubName;Birthday;Sex;Fed;TotalNumGames;SumOpponRating;TotalPoints
```

Required fields: `Id_No`, `Name`, `Rtg_Nat`, `TotalNumGames`, `SumOpponRating`, `TotalPoints`. No duplicate `Id_No` or `Id_CBX` (among non-empty values).

**tournaments.csv** — semicolon-delimited, UTF-8 (BOM accepted):

```
Ord;CrId;Name;EndDate;Type;IsIrt;IsFexerj
```

`Ord` = order number, `CrId` = Chess Results ID, `EndDate` is optional. `Type` must be `SS`, `RR`, or `ST`. `IsIrt` and `IsFexerj` must be `0` or `1`.

**Binary files** — one file per tournament, named `<Ord>-<CrId>.<Ext>` where `Ext` is `TUNX` (SS), `TURX` (RR), or `TUMX` (ST). Every player in the BIO section must have a FEXERJ ID.

## Deployment

### On-Demand Launch (recommended)

Rather than keeping a server running continuously, the portal can be launched on demand from a laptop, used, and then terminated. You pay only for the time the instance is running.

**One-time setup** — see `CONTRIBUTING.md` for full details:

1. Allocate an Elastic IP and point your domain A record to it
2. Store credentials and domain in AWS SSM Parameter Store under a path prefix of your choice
3. Create an IAM role for the EC2 instance with SSM read access
4. Create a security group allowing inbound ports 80 and 443
5. Copy `scripts/launch.conf.example` to `scripts/launch.conf` and fill in your values (`launch.conf` is gitignored and never committed)
6. Configure an AWS CLI profile with permissions to launch and terminate EC2 instances

**Launch the portal:**

```bash
bash scripts/launch.sh prod   # production (master branch)
bash scripts/launch.sh uat    # UAT (develop branch)
```

The script launches a fresh EC2 instance, attaches the Elastic IP, and polls until the portal is live — typically under 10 minutes. It prints elapsed time and the URL when ready.

**Terminate when done:**

```bash
bash scripts/terminate.sh prod
bash scripts/terminate.sh uat
```

The instance is destroyed. The Elastic IP remains allocated so the domain keeps resolving correctly for the next launch.

### Initial Server Setup

On a fresh Ubuntu 24.04 instance, clone the repository and run the setup script:

```bash
git clone https://github.com/pedrofaraco/fexerj-portal.git
cd fexerj-portal
sudo bash scripts/setup.sh
```

The script will prompt for the domain name and portal credentials, then handle everything: swap, system packages, Node.js, Python environment, frontend build, systemd service, Nginx, and HTTPS via Certbot.

> The domain must already resolve to the server's public IP before running the script, as Certbot requires DNS propagation to issue the certificate.

### Production checklist

- **`PORTAL_ENVIRONMENT=production`** — written by `scripts/setup.sh` into `/etc/fexerj-portal.env` on new installs. The process will not start if `PORTAL_PASSWORD` is still `changeme` or shorter than 8 characters.
- **HTTPS** — `setup.sh` configures Nginx and Certbot; use the site only over `https://` for staff traffic (Basic credentials must not cross the internet on plain HTTP).
- **Secrets** — store SSM / env passwords with at least 8 characters; avoid defaults. Keep `/etc/fexerj-portal.env` readable only by root (`chmod 600`, applied by setup).
- **Proxy limits** — set `client_max_body_size` (or equivalent) on Nginx in addition to `PORTAL_MAX_UPLOAD_MEGABYTES`.
- **Health checks** — Nginx proxies `GET /health` to the API so monitors can hit `https://<domain>/health`.

**Servers deployed before this behavior:** add `PORTAL_ENVIRONMENT=production` to `/etc/fexerj-portal.env` if it is missing, upgrade weak passwords, then `sudo systemctl restart fexerj-portal`.

### Deploying Updates

After merging new code into `master`, SSH into the server and run:

```bash
cd fexerj-portal
bash scripts/update.sh
```

This pulls the latest code, updates dependencies, rebuilds the frontend, and restarts the service.

### Rollback

If `update.sh` fails at any step it automatically reverts to the previous commit, reinstalls dependencies, rebuilds the frontend, and restarts the service. No manual intervention is needed in most cases.

To roll back manually to a specific commit:

```bash
cd fexerj-portal
git checkout <commit-hash> -- .
bash scripts/update.sh
```

### Changing Credentials

Edit `/etc/fexerj-portal.env` on the server and restart the backend:

```bash
sudo nano /etc/fexerj-portal.env
sudo systemctl restart fexerj-portal
```

Keep `PORTAL_ENVIRONMENT=production` on public hosts and ensure `PORTAL_PASSWORD` meets the length and non-default rules above.

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | None | Unauthenticated health check for uptime monitoring |
| GET | `/me` | Required | Validate credentials — returns `{"ok": true}` |
| POST | `/validate` | Required | Validate input files, returns `{"errors": [...]}` |
| POST | `/run` | Required | Run rating cycle, returns zip archive |

`first` and `count` form parameters on `/validate` and `/run` must be integers ≥ 1.

On **`POST /run`**, **HTTP 422** responses use a JSON `detail` field: file validation failures return **`detail` as a list of strings** (the same messages as `/validate`’s `errors`). Invalid form fields or missing files may instead return FastAPI’s structured validation entries (objects with a `msg` field).

**413 Payload Too Large** — **`POST /validate`** and **`POST /run`** return this when the `Content-Length` header exceeds `PORTAL_MAX_UPLOAD_MEGABYTES` (see above).

## Branch Strategy

- `master` — production only
- `develop` — integration branch; open PRs here for day-to-day work
- `feature/<name>`, `fix/<name>`, `refactor/<name>`, `chore/<name>` — one branch per task; each targets `develop` via pull request

CI runs on pushes to `master`, `develop`, and the branch patterns above, and on pull requests targeting `master` or `develop`. See [CONTRIBUTING.md](CONTRIBUTING.md) for the full workflow (lint, tests, frontend build).
