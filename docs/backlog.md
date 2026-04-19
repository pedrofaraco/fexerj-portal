# Improvement backlog

Prioritized work; update when items ship so sessions and PRs stay aligned.

## Recently shipped (do not re-track)

- **Deploy scripts**: **`scripts/update.sh`** **`rollback()`** and **`scripts/deploy-synology.sh`** **`rollback_nas()`** preserve the **original deploy exit code**, clear **`ERR`** trap recursion, classify strict vs best-effort steps; NAS rollback no longer runs redundant **`npm ci`/`build`** (frontend is built in Docker multi-stage image).
- **`calculator/`**: **`print()`** replaced with **`logging`** (warnings via **`logger.warning`**; correlated with backend JSON logs in production).
- **Frontend**: **`X-Request-ID`** surfaced on amber/red operator error banners (validation HTTP/parse failures, run HTTP errors, ZIP parse failures on results) with copy-to-clipboard — greppable server logs.
- **Frontend**: `App.jsx` split into pages/hooks/components; **`postMultipart`** + UTF-8 Basic auth; debounced validation.
- **Backend / edge**: **`limit_upload_body`** documents chunked / missing `Content-Length` path; nginx **`limit_req`** on `/validate` and `/run`; **`POST /run`** single-flight (**503** + **`Retry-After`**).
- **Nginx / Docker**: full **CSP** + **`X-XSS-Protection: 0`**; **multi-stage** `docker/Dockerfile.nginx`; backend **HEALTHCHECK**; compose **`depends_on: service_healthy`** (no bind-mount `dist`).
- **Supply chain**: **Dependabot** (pip + npm); CI **`pip-audit`** + **`npm audit`**; **ESLint 10** / **`@eslint/js` 10** aligned.

## Next — production hygiene (recommended order)

_No open P1/P2 hygiene items._

## P3 — UX and accessibility (lower urgency)

- **a11y**: keyboard-focused pass on collapsible help — **`aria-*`** already present; revisit only if keyboard-only flows are broken.
- Optional **client-side file size hint** before upload (aligned with server/nginx limit).

## P4 — Scale and observability (when needed)

- **Backend**: request ID middleware + structured logging already exist; extend only if new surfaces need correlation.
- **Streaming ZIP** or **async job + download** if memory or timeouts bite.
- **OpenAPI** export or typed client generation.

## P5 — Larger bets

- **TypeScript** on the frontend.
- Optional **pytest coverage gate** for **`calculator/`**.

## Deferred / optional

- Optional **nginx security headers** block in **`scripts/setup.sh`** (container already ships headers via **`docker/nginx.conf`**).
