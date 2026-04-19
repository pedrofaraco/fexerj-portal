# Improvement backlog

Prioritized work; update when items ship so sessions and PRs stay aligned.

## Recently shipped (do not re-track)

- **Frontend**: `App.jsx` split into pages/hooks/components; **`postMultipart`** + UTF-8 Basic auth; debounced validation.
- **Backend / edge**: **`limit_upload_body`** documents chunked / missing `Content-Length` path; nginx **`limit_req`** on `/validate` and `/run`; **`POST /run`** single-flight (**503** + **`Retry-After`**).
- **Nginx / Docker**: full **CSP** + **`X-XSS-Protection: 0`**; **multi-stage** `docker/Dockerfile.nginx`; backend **HEALTHCHECK**; compose **`depends_on: service_healthy`** (no bind-mount `dist`).
- **Supply chain**: **Dependabot** (pip + npm); CI **`pip-audit`** + **`npm audit`**; **ESLint 10** / **`@eslint/js` 10** aligned.

## Next — production hygiene (recommended order)

1. **`calculator/`**: replace **`print()`** with **`logging`** (structured, correlatable with backend JSON logs in production).
2. **Frontend**: surface **`X-Request-ID`** (from response headers) on **amber/red error banners** so operators can grep logs.

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
