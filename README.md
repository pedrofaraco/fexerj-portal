# fexerj-portal

Web portal for the FEXERJ chess community — rating lists, player database, and staff tools.

## Features (planned)

- **Rating Cycle Runner** *(in progress)* — upload tournament files and download updated rating lists
- Public rating lists and player database *(future)*

## Tech Stack

- **Backend**: FastAPI (Python)
- **Frontend**: React
- **Auth**: Basic auth
- **Hosting**: AWS EC2 + Nginx + HTTPS

## Project Structure

```
calculator/   # Rating calculator library (adapted from fexerj-rating-calculator)
tests/        # Test suite (pytest)
```

## Development Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest tests/
```

## Branch Strategy

- `master` — production only
- `develop` — integration branch
- `feature/*` — one branch per feature; PR into `develop`
