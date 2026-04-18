# fexerj-portal

Web portal for the FEXERJ chess community — rating cycle runner and (planned) public rating/player lookups.

- **Operations & deploy commands** → [`RUNBOOK.md`](RUNBOOK.md)
- **Rating calculator internals** → [`CALCULATOR.md`](CALCULATOR.md)
- **Contributor workflow (lint, tests, branches, CI)** → [`CONTRIBUTING.md`](CONTRIBUTING.md)

---

## Features

- **Rating cycle runner** — Portuguese-language staff interface to upload tournament files, validate inputs, view an on-screen summary of processed tournaments (players and audit-style details), and download the resulting ZIP.
- Public rating lists and player database *(planned)*.

## Tech stack

- **Backend**: FastAPI (Python 3.12)
- **Frontend**: React + Vite + Tailwind CSS v4
- **Auth**: HTTP Basic over HTTPS, credentials via environment variables
- **Hosting**: Synology NAS (Docker Compose) — see [`RUNBOOK.md`](RUNBOOK.md). AWS EC2 on-demand deploy is also supported.

## Project structure

```
backend/      FastAPI application, configuration, request-id middleware, input validator
calculator/   Rating calculator library (see CALCULATOR.md)
frontend/     React frontend (Vite)
scripts/      Deploy/launch/terminate/update shell scripts
tests/        Backend + calculator test suite (pytest)
```

---

## Development setup

### Backend

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q
```

### Frontend

```bash
cd frontend
npm install
npm test
```

### Running locally (two tabs)

```bash
# Backend
source .venv/bin/activate
uvicorn backend.main:app --reload

# Frontend
cd frontend && npm run dev
```

Open `http://localhost:5173`. The Vite dev server proxies `/health`, `/me`, `/validate`, and `/run` to the backend.

Credentials for local dev:

```bash
export PORTAL_USER=youruser
export PORTAL_PASSWORD=yourpassword
# (a .env file in the repo root is also supported)
```

---

## Configuration

| Variable                       | Default       | Notes                                                                  |
|--------------------------------|---------------|------------------------------------------------------------------------|
| `PORTAL_USER`                  | —             | Basic-auth username. Must be Latin-1.                                  |
| `PORTAL_PASSWORD`              | —             | Basic-auth password. Must be Latin-1; ≥ 8 chars in `production`.       |
| `PORTAL_ENVIRONMENT`           | `development` | Set to `production` on internet-facing hosts. Blocks `changeme` / short passwords at startup. |
| `PORTAL_MAX_UPLOAD_MEGABYTES`  | `100`         | Range 1–2048. Enforced on `POST /validate` and `POST /run` **only when** `Content-Length` is present — also set `client_max_body_size` on the reverse proxy. |

---

## Input file formats

**`players.csv`** — semicolon-delimited, UTF-8 (BOM accepted):

```
Id_No;Id_CBX;Title;Name;Rtg_Nat;ClubName;Birthday;Sex;Fed;TotalNumGames;SumOpponRating;TotalPoints
```

Required fields: `Id_No`, `Name`, `Rtg_Nat`, `TotalNumGames`, `SumOpponRating`, `TotalPoints`. No duplicate `Id_No` or `Id_CBX` (among non-empty values).

**`tournaments.csv`** — semicolon-delimited, UTF-8 (BOM accepted):

```
Ord;CrId;Name;EndDate;Type;IsIrt;IsFexerj
```

`Ord` = order number, `CrId` = Chess Results ID, `EndDate` is optional. `Type` must be `SS`, `RR`, or `ST`. `IsIrt` and `IsFexerj` must be `0` or `1`.

**Binary files** — one file per tournament, named `<Ord>-<CrId>.<Ext>` where `Ext` is `TUNX` (SS), `TURX` (RR), or `TUMX` (ST). Every player in the BIO section must have a FEXERJ ID that also appears in `players.csv`.

---

## API endpoints

| Method | Path        | Auth     | Description                                                |
|--------|-------------|----------|------------------------------------------------------------|
| GET    | `/health`   | None     | Unauthenticated health check for uptime monitors.          |
| GET    | `/me`       | Required | Validate credentials — returns `{"ok": true}`.             |
| POST   | `/validate` | Required | Validate input files, returns `{"errors": [...]}`.         |
| POST   | `/run`      | Required | Run the rating cycle, returns a ZIP archive on success.    |

`first` and `count` form parameters on `/validate` and `/run` must be integers ≥ 1.

- **`422 Unprocessable Entity`** — file-level validation failures return `detail` as a list of strings (the same messages as `/validate`'s `errors`). Invalid form fields or missing files may instead return FastAPI's structured validation entries (objects with a `msg` field).
- **`413 Payload Too Large`** — returned when `Content-Length` exceeds `PORTAL_MAX_UPLOAD_MEGABYTES`. For chunked uploads with no `Content-Length`, the reverse proxy must enforce the limit.

---

## Branch strategy

- `master` — production
- `develop` — integration branch; open PRs here for day-to-day work
- `feature/<name>`, `fix/<name>`, `refactor/<name>`, `chore/<name>` — one branch per task, each targeting `develop` via pull request

CI runs on pushes to `master`, `develop`, and the branch patterns above, and on pull requests targeting `master` or `develop`. See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the full workflow.

Deploy, restart, rollback, logs, and triage commands live in [`RUNBOOK.md`](RUNBOOK.md).
