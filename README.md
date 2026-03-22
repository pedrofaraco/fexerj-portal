# fexerj-portal

Web portal for the FEXERJ chess community — rating lists, player database, and staff tools.

## Features (planned)

- **Rating Cycle Runner** *(in progress)* — upload tournament files and download updated rating lists
- Public rating lists and player database *(future)*

## Tech Stack

- **Backend**: FastAPI (Python)
- **Frontend**: React + Vite + Tailwind CSS
- **Auth**: HTTP Basic auth, credentials via environment variables
- **Hosting**: AWS EC2 + Nginx + HTTPS

## Project Structure

```
backend/      # FastAPI application and configuration
calculator/   # Rating calculator library
frontend/     # React frontend (Vite)
tests/        # Backend test suite (pytest)
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

Then open `http://localhost:5173`. The frontend proxies `/run` to the backend automatically.

Credentials are configured via environment variables:

```bash
export PORTAL_USER=youruser
export PORTAL_PASSWORD=yourpassword
```

A `.env` file in the project root is also supported.

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

### Changing Credentials

Edit `/etc/fexerj-portal.env` on the server and restart the backend:

```bash
sudo nano /etc/fexerj-portal.env
sudo systemctl restart fexerj-portal
```

## Branch Strategy

- `master` — production only
- `develop` — integration branch
- `feature/*` — one branch per feature; PR into `develop`
