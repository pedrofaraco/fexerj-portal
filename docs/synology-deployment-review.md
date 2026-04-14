# Synology deployment doc — review and improvements

This document records a review of `docs/synology-deployment.md` and its alignment with the current `develop` branch contents.

## Scope

- **Reviewed doc:** `docs/synology-deployment.md`
- **Referenced implementation (develop):**
  - `Dockerfile`
  - `docker-compose.yml`, `docker-compose.uat.yml`
  - `docker/nginx.conf`
  - `scripts/deploy-synology.sh.example`
  - `scripts/deploy-synology.sh`, `scripts/deploy-synology.conf` (both gitignored)

## What’s good

- **Clear architecture narrative:** DSM reverse proxy (TLS termination) → per-environment Docker nginx → FastAPI backend.
- **Security posture is stated:** staff-facing, Basic auth, not public; includes an exposure table and explicit limitations/risks.
- **Reproducible repo surface exists on `develop`:** the Docker and nginx files referenced by the doc exist.
- **Secrets hygiene (as intended):**
  - `.env` lives on NAS, `chmod 600`
  - `scripts/deploy-synology.conf` / `scripts/deploy-synology.sh` are gitignored (the operator-specific versions)

## Key mismatches / risks to address (highest impact)

### 1) UAT environment uses `PORTAL_ENVIRONMENT=production` in the deploy script

In `scripts/deploy-synology.sh`, the first-run `.env` is written with:

- `PORTAL_ENVIRONMENT=production`

This applies to both prod and UAT, even though the doc positions UAT as `develop`/UAT. Decide the intent and make the doc+script consistent:

- **Option A (typical):** UAT uses `PORTAL_ENVIRONMENT=development`.
- **Option B (production-like UAT):** keep `production` for UAT, but explicitly state that UAT enforces production credential rules.

### 2) nginx upload/timeouts can preempt backend behavior

`docker/nginx.conf` proxies `/health|/me|/validate|/run` but does not set:

- `client_max_body_size`
- `proxy_read_timeout` / `proxy_send_timeout`

Consequences:

- large uploads may fail at nginx with 413 before backend limits or messages apply
- long `/run` executions may hit proxy timeouts

Recommended:

- Set `client_max_body_size` at or above `PORTAL_MAX_UPLOAD_MEGABYTES` (or document the effective limit is the minimum of the two).
- Set conservative timeouts aligned with expected processing time.

### 3) Forwarded headers are incomplete

`docker/nginx.conf` sets `Host` and `X-Real-IP` but not:

- `X-Forwarded-For`
- `X-Forwarded-Proto`

These become important if you later add redirects, absolute URLs, or want consistent client IP logging.

### 4) Sudo password handling is operationally convenient but should be explicit

The deploy script captures the NAS sudo password locally and pipes it into remote `sudo -S docker compose ...` over SSH.

Suggested improvements:

- **Doc:** explicitly mention this behavior in the security posture section.
- **Implementation (optional):** eliminate password use by:
  - adding the deploy user to the `docker` group on the NAS (no sudo), or
  - adding a least-privilege sudoers rule for only the required docker commands.

## Secondary improvements (nice-to-have)

### Make “ready” checks more meaningful

The deploy script polls the homepage URL. Consider also checking:

- `GET /health`
- optionally `GET /me` with Basic auth (if you want to validate auth path too)

### Health checks

The doc lists “No container health checks.” That’s fine, but you can improve robustness by adding a backend `healthcheck` (e.g. `/health`) and documenting how to observe restart loops.

### Reduce sensitive specifics (if this doc is broadly shared)

The doc includes LAN IP, DDNS hostname, and SSH port. If the repository is shared beyond trusted operators, consider replacing those with placeholders and keeping exact values in a private operator runbook.

### “Repository changes” phrasing

Statements like “no existing files were modified” tend to go stale. Prefer:

- listing the actual paths (already present), and/or
- referencing a PR/commit that introduced the Synology deployment files.

## Suggested action plan (prioritized)

1. **Decide UAT `PORTAL_ENVIRONMENT` policy** and align `docs/synology-deployment.md` + `scripts/deploy-synology.sh`.
2. **Harden `docker/nginx.conf`** with upload and timeout controls; document the effective limits.
3. **Add forwarded headers** (`X-Forwarded-For`, `X-Forwarded-Proto`) and document how TLS termination affects them.
4. **Clarify or remove sudo password piping** in the deploy process.
5. Optional: add `healthcheck` + improved polling to reduce “frontend up / backend down” false positives.

