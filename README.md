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

## Branch Strategy

- `master` — production only
- `develop` — integration branch
- `feature/*` — one branch per feature; PR into `develop`
