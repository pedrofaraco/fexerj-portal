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

> **`Rtg_Nat` holds the FEXERJ rating**, despite the column name. It is the value the
> calculator reads as the player's current rating and writes back as the new one. It is
> not a CBX or FIDE rating — `Id_CBX` is an identifier only, and no external rating
> enters the system. The name is kept for compatibility with existing files.

**`players.csv` — new per-game model (26 columns)** — semicolon-delimited, UTF-8 (BOM
accepted). Accepted in `fide` mode, alongside the 12-column format above. (`compare` mode
requires the 12-column format only — see restrictions below.)

```
Id_No;Id_CBX;Title;Name;ClubName;Birthday;Sex;Fed;Rtg_Std;Games_Std;Peak2200_Std;SumOpp_Std;Pts_Std;AccGames_Std;Rtg_Rpd;Games_Rpd;Peak2200_Rpd;SumOpp_Rpd;Pts_Rpd;AccGames_Rpd;Rtg_Blz;Games_Blz;Peak2200_Blz;SumOpp_Blz;Pts_Blz;AccGames_Blz
```

The first eight columns are identity, shared across modalities: `Id_No;Id_CBX;Title;Name;ClubName;Birthday;Sex;Fed`.

The remaining eighteen columns are three groups of six — one group per modality, Classical
(`Std`), Rapid (`Rpd`), Blitz (`Blz`) — each shaped
`Rtg_<mod>;Games_<mod>;Peak2200_<mod>;SumOpp_<mod>;Pts_<mod>;AccGames_<mod>`:

- `Rtg_<mod>` — the player's current rating in that modality. **Empty means the player is
  unrated** in that modality.
- `Games_<mod>` — lifetime games played in that modality. Feeds the K factor and is preserved
  when the 1200 floor drops the player out of rated status.
- `Peak2200_<mod>` — `1` if the player has ever reached 2200 in that modality, else `0`.
- `SumOpp_<mod>` — sum of opponents' ratings accumulated toward the player's first rating in
  that modality.
- `Pts_<mod>` — points accumulated toward the player's first rating in that modality.
- `AccGames_<mod>` — how many of those accumulated games have gone into `SumOpp_<mod>`/
  `Pts_<mod>` so far. Distinct from `Games_<mod>`: it resets to `0` whenever the player gains a
  rating, and again if the floor later drops them back out, since the accumulation toward the
  next rating starts over from zero rather than resuming from the lifetime count.

`Birthday` is required in this format (it is optional in the legacy 12-column format) — the
per-game model's under-18 K-factor rule depends on it.

**`tournaments.csv`** — semicolon-delimited, UTF-8 (BOM accepted):

```
Ord;CrId;Name;EndDate;Type;IsIrt;IsFexerj
```

`Ord` = order number, `CrId` = Chess Results ID, `EndDate` is optional. `Type` must be `SS`, `RR`, or `ST`. `IsIrt` and `IsFexerj` must be `0` or `1`.

**`tournaments.csv` — new per-game model (8 columns)**:

```
Ord;CrId;Name;EndDate;Type;IsIrt;IsFexerj;TimeControl
```

Same seven columns as the legacy format, plus `TimeControl`, which must be `STD` (classical),
`RPD` (rapid), or `BLZ` (blitz). `TimeControl` is distinct from `Type`: `Type` is the pairing
format (`SS` swiss, `RR` round-robin, `ST` team), `TimeControl` is the time control the games
were played at. `EndDate` is required in this format (optional in the legacy one) — the
under-18 K-factor rule needs the period's year.

**Binary files** — one file per tournament, named `<Ord>-<CrId>.<Ext>` where `Ext` is `TUNX` (SS), `TURX` (RR), or `TUMX` (ST). Every player in the BIO section must have a FEXERJ ID that also appears in `players.csv` (CBX ID for IRT tournaments). The portal validator checks this before run.

**`compare` mode restrictions** — `compare` mode runs both engines over the same input, so its
files must satisfy both: `players.csv` must be the 12-column legacy format, and every
tournament in the period must have `TimeControl=STD`. Reason: the current engine only reads
the 12-column format and has no concept of time control.

---

## API endpoints

| Method | Path        | Auth     | Description                                                |
|--------|-------------|----------|------------------------------------------------------------|
| GET    | `/health`   | None     | Unauthenticated health check for uptime monitors.          |
| GET    | `/me`       | Required | Validate credentials — returns `{"ok": true}`.             |
| POST   | `/validate` | Required | Validate input files, returns `{"errors": [...]}`.         |
| POST   | `/run`      | Required | Run the rating cycle, returns a ZIP archive on success.    |

`first` and `count` form parameters on `/validate` and `/run` must be integers ≥ 1.

`/validate` and `/run` also accept a `mode` form parameter — `legacy` (default), `fide`, or
`compare`. Omitting it, or explicitly sending `legacy`, keeps the current behavior exactly:
same validation rules, same engine (`calculator.FexerjRatingCycle`), same output files. `fide`
runs the new per-game engine (`calculator.fide.FideRatingCycle`); `compare` runs both engines and
adds a diff. See [`CALCULATOR.md`](CALCULATOR.md) for what each engine does. An unrecognized
`mode` is rejected as a validation error, not silently treated as `legacy`.

The `/run` zip's filename and contents vary by mode:

| Mode      | Zip filename                    | Contents                                                              |
|-----------|----------------------------------|-------------------------------------------------------------------------|
| `legacy`  | `rating_cycle_output.zip`        | `RatingList_after_<Ord>.csv` and `Audit_of_Tournament_<Ord>.csv` per tournament |
| `fide`    | `rating_cycle_fide.zip`          | `RatingList.csv`, `Audit_Games.csv`, `Audit_Period.csv`                 |
| `compare` | `rating_cycle_comparison.zip`    | Both engines' outputs above, plus `Comparison.csv`                      |

- **`422 Unprocessable Entity`** — file-level validation failures return `detail` as a list of strings (the same messages as `/validate`'s `errors`). Invalid form fields or missing files may instead return FastAPI's structured validation entries (objects with a `msg` field).
- **`413 Payload Too Large`** — returned when `Content-Length` exceeds `PORTAL_MAX_UPLOAD_MEGABYTES`. For chunked uploads with no `Content-Length`, the reverse proxy must enforce the limit.

---

## Branch strategy

- `master` — production
- `develop` — integration branch; open PRs here for day-to-day work
- `feature/<name>`, `fix/<name>`, `refactor/<name>`, `chore/<name>` — one branch per task, each targeting `develop` via pull request

CI runs on pushes to `master`, `develop`, and the branch patterns above, and on pull requests targeting `master` or `develop`. See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the full workflow.

Deploy, restart, rollback, logs, and triage commands live in [`RUNBOOK.md`](RUNBOOK.md).
