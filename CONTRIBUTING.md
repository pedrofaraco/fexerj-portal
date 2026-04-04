# Contributing

## Development Environment

**Backend**

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

Leave `PORTAL_ENVIRONMENT` unset (or `development`) locally so the default `changeme` password in `.env` still works. **Do not** set `production` unless you use a real password of at least 8 characters — the app will not boot otherwise.

**Frontend**

```bash
cd frontend
npm install
```

## Running Tests

**Backend** (from repo root):

```bash
source .venv/bin/activate
pytest tests/
```

**Frontend** (from `frontend/`):

```bash
npm test
```

## Linting and Type Checking

**Backend** (from repo root):

```bash
source .venv/bin/activate
ruff check backend/ tests/
mypy backend/
```

**Frontend** (from `frontend/`):

```bash
npm run lint
npm run build
```

These same checks run automatically via GitHub Actions on pushes to `master`, `develop`, and matching `feature/**`, `fix/**`, `refactor/**`, and `chore/**` branches, and on pull requests targeting `master` or `develop` (Python lint/typecheck, shellcheck, and frontend lint, test, and production build).

## Branch Strategy

- `master` — production only; never commit directly
- `develop` — integration branch; all feature branches target this
- `feature/<name>`, `refactor/<name>`, `chore/<name>`, `fix/<name>` — one branch per task; open a PR into `develop`

## Commit Messages

Use the [Conventional Commits](https://www.conventionalcommits.org/) format:

```
<type>(<scope>): <short summary>
```

Common types: `feat`, `fix`, `refactor`, `chore`, `docs`, `test`.

Examples:
- `feat(backend): add /validate endpoint`
- `fix(frontend): handle 401 on run response`
- `chore(scripts): make setup.sh idempotent`

Keep the summary under 72 characters. Use the body for context when needed.

## Pull Request Process

1. Branch off `develop` and make your changes.
2. Ensure all tests pass locally before opening a PR.
3. Open a PR targeting `develop`.
4. A passing CI run (Python and shell linting, type check, tests, and frontend lint/build) is required before merging.
5. Squash-merge into `develop`; the branch is deleted after merge.
6. Periodically, `develop` is merged into `master` to deploy to production.
