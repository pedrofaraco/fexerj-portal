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

### Initial Server Setup

On a fresh Ubuntu 24.04 instance, clone the repository and run the setup script:

```bash
git clone https://github.com/pedrofaraco/fexerj-portal.git
cd fexerj-portal
sudo bash scripts/setup.sh
```

The script will prompt for the domain name and portal credentials, then handle everything: swap, system packages, Node.js, Python environment, frontend build, systemd service, Nginx, and HTTPS via Certbot.

> The domain must already resolve to the server's public IP before running the script, as Certbot requires DNS propagation to issue the certificate.

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

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | None | Unauthenticated health check for uptime monitoring |
| GET | `/me` | Required | Validate credentials — returns `{"ok": true}` |
| POST | `/validate` | Required | Validate input files, returns `{"errors": [...]}` |
| POST | `/run` | Required | Run rating cycle, returns zip archive |

`first` and `count` form parameters on `/validate` and `/run` must be integers ≥ 1.

## Branch Strategy

- `master` — production only
- `develop` — integration branch
- `feature/*` — one branch per feature; PR into `develop`
