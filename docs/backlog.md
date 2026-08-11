# Improvement backlog

Prioritized work; update when items ship so sessions and PRs stay aligned.

## Recently shipped (do not re-track)

- **Deploy scripts**: **`scripts/update.sh`** **`rollback()`** and **`scripts/deploy-synology.sh`** **`rollback_nas()`** preserve the **original deploy exit code**, clear **`ERR`** trap recursion, classify strict vs best-effort steps; NAS rollback no longer runs redundant **`npm ci`/`build`** (frontend is built in Docker multi-stage image).
- **`calculator/`**: **`print()`** replaced with **`logging`** (warnings via **`logger.warning`**; correlated with backend JSON logs in production).
- **Frontend**: upload **size hint** on RunPage binary field (**`MAX_UPLOAD_MB`**, documented sync with **`PORTAL_MAX_UPLOAD_MEGABYTES`** / **`client_max_body_size`**).
- **Frontend**: **`X-Request-ID`** surfaced on amber/red operator error banners (validation HTTP/parse failures, run HTTP errors, ZIP parse failures on results) with copy-to-clipboard — greppable server logs.
- **Frontend**: `App.jsx` split into pages/hooks/components; **`postMultipart`** + UTF-8 Basic auth; debounced validation.
- **Backend / edge**: **`limit_upload_body`** documents chunked / missing `Content-Length` path; nginx **`limit_req`** on `/validate` and `/run`; **`POST /run`** single-flight (**503** + **`Retry-After`**).
- **Nginx / Docker**: full **CSP** + **`X-XSS-Protection: 0`**; **multi-stage** `docker/Dockerfile.nginx`; backend **HEALTHCHECK**; compose **`depends_on: service_healthy`** (no bind-mount `dist`).
- **Supply chain**: **Dependabot** (pip + npm); CI **`pip-audit`** + **`npm audit`**; **ESLint 10** / **`@eslint/js` 10** aligned.
- **CI supply chain**: audit split into **blocking (runtime)** and **advisory (dev tooling)** for both npm (**`--omit=dev`**) and pip (**`requirements.txt`**). A transitive dev-only advisory no longer blocks unrelated PRs; Dependabot remains the remediation path.

- **Dependabot queue drained** (2026-08-08): all 21 PRs resolved. `mypy` 2.3.0, `ruff` 0.16.1, `eslint` 10.8.0, `vitest` 4.1.10, `tailwindcss` 4.3.3, `fastapi` 0.141.1, `uvicorn` 0.52.1, `react`/`react-dom` 19.2.8. Note Dependabot opens coupled packages as separate PRs; `react`/`react-dom` had to be bumped together by hand (#198) because a mismatch is a runtime crash.
- **Frontend**: `build.target` pinned to **`chrome109`**. Vite's default is a moving target that had drifted to chrome111, above the supported floor.

## Next — production hygiene (recommended order)

- **P2 — enforce the dependency-classification invariant**: nothing imported by `frontend/src/` (excluding the 12 test files) may live in `devDependencies`. True today — production code imports only `react`, `react-dom/client`, `prop-types`, `jszip`, all declared as `dependencies` — but nothing guards it. A devDependency imported from `src/` ships to the browser **and sits outside the blocking `npm audit --omit=dev` gate**: a silent hole. Either `eslint-plugin-import`'s `no-extraneous-dependencies` (check ESLint 10 flat-config compatibility first) or a short CI script. ~1h.
- **P3 — surface advisory audit findings in the PR UI**: pipe `npm audit --json` / `pip-audit -f json` into `$GITHUB_STEP_SUMMARY`. With `continue-on-error` the job renders green, so dev-tooling advisories accumulate in a log nobody opens — the risk the CI design doc predicted. ~30-45 min.
- **Considered and declined**: `npm audit --omit=dev --audit-level=high`. The blocking scope is only ~10 runtime packages, so a `low` there is rare and probably worth reading. The stall risk it guards against lived in the dev tree, which is already advisory.

## P3 — UX and accessibility (lower urgency)

- **a11y**: keyboard-focused pass on collapsible help — **`aria-*`** already present; revisit only if keyboard-only flows are broken.
- **The file inputs still read "No file selected" after "Nova execução"**: coming back from the results page remounts `RunPage`, and an `<input type="file">` cannot be repopulated by JavaScript, so the native widget reads *"No file selected"* while `SelectedFilesLine` right below it reads *"Arquivo selecionado: players.csv"*. The app is right — the `File` objects are still in `form` and the run works — but two opposite statements sit one line apart, and the operator's instinct is to re-pick files that were never lost. Options: hide the native widget behind a styled button whose label is the app's own state, or say explicitly that the previous selection is still in effect. Pre-existing; noticed while checking the mode selector on 2026-08-10. ~1h.

## P4 — Scale and observability (when needed)

- **Backend**: request ID middleware + structured logging already exist; extend only if new surfaces need correlation.
- **Streaming ZIP** or **async job + download** if memory or timeouts bite.
- **OpenAPI** export or typed client generation.

## P5 — Larger bets

- **TypeScript** on the frontend.
- Optional **pytest coverage gate** for **`calculator/`**.

## Deferred / optional

- Optional **nginx security headers** block in **`scripts/setup.sh`** (container already ships headers via **`docker/nginx.conf`**).
