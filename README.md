# fexerj-portal

Web portal for the FEXERJ chess community — rating lists, player database, and staff tools.

## Features (planned)

- **Rating Cycle Runner** *(in progress)* — upload tournament files and download updated rating lists
- Public rating lists and player database *(future)*

## Tech Stack

- **Backend**: FastAPI (Python)
- **Frontend**: React
- **Auth**: HTTP Basic auth, credentials via environment variables
- **Hosting**: AWS EC2 + Nginx + HTTPS

## Project Structure

```
backend/      # FastAPI application and configuration
calculator/   # Rating calculator library
tests/        # Test suite (pytest)
```

## Development Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest tests/
```

## Running Locally

```bash
uvicorn backend.main:app --reload
```

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
