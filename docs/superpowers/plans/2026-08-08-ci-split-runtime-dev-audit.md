# CI: Split Runtime and Dev Dependency Audits — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Unblock the `supply-chain-audit` CI job — which has failed on every PR since 2026-06-28 — by blocking merges only on runtime dependency vulnerabilities while keeping dev-tooling audits visible but non-blocking.

**Architecture:** The `supply-chain-audit` job's two audit steps each become two steps: one blocking pass scoped to runtime dependencies (`npm audit --omit=dev`, `pip-audit -r requirements.txt`) and one advisory pass over everything (`continue-on-error: true`). Separately, `npm audit fix` clears the four current transitive advisories through a lockfile-only change.

**Tech Stack:** GitHub Actions, npm 11.4.2 / Node 22, `pip-audit` 2.10.0, Python 3.12.

**Spec:** `docs/superpowers/specs/2026-08-08-ci-supply-chain-audit-design.md`

## Global Constraints

- **`frontend/package.json` must NOT be modified.** All four fixes are patch-level and within existing semver ranges. If `package.json` changes, stop — something re-resolved outside the intended scope.
- **No AI or tool attribution** in commit messages, PR titles, or PR descriptions — not in bullets, not in file lists, nowhere. (`CLAUDE.md`)
- **No credentials or sensitive defaults** mentioned in commit or PR messages. (`CLAUDE.md`)
- **Conventional Commits**, summary under 72 characters, written in English to match repository history.
- **Branch:** `chore/ci-split-runtime-dev-audit`, already created from `develop` at `4348aa8`. Do not branch again.
- **`actionlint` is not installed on this machine.** Use the PyYAML check given in Task 2. Do not substitute a tool you have not confirmed exists.
- **Do not open the pull request without asking Pedro first.** `CLAUDE.md` authorizes the agent to create branches, commit, and push; it stops there.

---

### Task 1: Clear the four transitive advisories via lockfile

The riskiest change in this plan: `postcss` and `nanoid` are build-critical (Vite's CSS pipeline). This task is isolated so a full build regression runs against it alone.

**Files:**
- Modify: `frontend/package-lock.json` (via `npm audit fix` — do not hand-edit)
- Must remain unchanged: `frontend/package.json`

**Interfaces:**
- Consumes: nothing.
- Produces: a lockfile where `npm audit` exits 0. Task 2 does not depend on this — the two tasks are independent and either order leaves CI green — but running this first means the branch is unblocked even if Task 2 is rejected in review.

- [ ] **Step 1: Confirm the failing state**

Run from the repository root:

```bash
cd frontend && npm audit; echo "EXIT=$?"
```

Expected: `4 high severity vulnerabilities` and `EXIT=1`. The four are `brace-expansion`, `nanoid`, `postcss`, `undici`.

If the count differs, a new advisory landed since planning. That is not a reason to stop — record the actual list and continue; the fix mechanism is unchanged.

- [ ] **Step 2: Record the pre-change `package.json` hash**

```bash
cd frontend && shasum package.json
```

Save the output. Step 5 compares against it.

- [ ] **Step 3: Apply the fix**

```bash
cd frontend && npm audit fix
```

Expected: **4 packages changed, nothing added** — a 14-insertion / 14-deletion diff touching only `undici`, `postcss`, `nanoid`, and `brace-expansion`.

(An earlier revision of this plan predicted ~35 added platform binaries. That was a misreading of `npm audit fix --dry-run`, which lists optional binaries missing from the local `node_modules` rather than from the lockfile. Corrected during execution.)

- [ ] **Step 4: Verify the advisories are gone**

```bash
cd frontend && npm audit; echo "EXIT=$?"
```

Expected: `found 0 vulnerabilities` and `EXIT=0`.

- [ ] **Step 5: Verify `package.json` is untouched**

```bash
cd frontend && shasum package.json && git diff --exit-code package.json; echo "EXIT=$?"
```

Expected: hash identical to Step 2, and `EXIT=0` (no diff).

If `package.json` changed, revert everything (`git checkout -- package.json package-lock.json`) and stop. A global constraint was violated and the approach needs rethinking before proceeding.

- [ ] **Step 6: Verify the four packages moved to patched versions**

```bash
cd frontend && npm ls undici postcss nanoid brace-expansion 2>&1 | grep -E 'undici@|postcss@|nanoid@|brace-expansion@'
```

Expected: `undici@7.29.0` or later, `postcss@8.5.26`+, `nanoid@3.3.18`+, `brace-expansion@5.0.9`+.

- [ ] **Step 7: Full regression — this is the point of the task**

```bash
cd frontend && npm ci && npm run lint && npm run test:coverage && npm run build
```

Expected: lint clean; **150 tests passing across 11 files**; build completes and writes `frontend/dist/`.

A `postcss` bump that breaks the CSS pipeline would surface here. If the build fails or the test count drops, stop and report — do not commit.

- [ ] **Step 8: Verify the backend suite is unaffected**

```bash
cd /Users/pedro/workspaces/fexerj-portal && .venv/bin/pytest tests/ -q
```

Expected: **292 passed**, coverage gate satisfied (backend 96%). This should be untouched by a frontend lockfile change — running it confirms that rather than assuming it.

- [ ] **Step 9: Commit**

```bash
cd /Users/pedro/workspaces/fexerj-portal
git add frontend/package-lock.json
git commit -F - <<'EOF'
chore(deps): patch transitive dev advisories in frontend lockfile

npm audit fix bumps four transitive packages to patched versions:
undici 7.28.0 to 7.29.0, postcss 8.5.15 to 8.5.26, nanoid 3.3.14 to
3.3.18, and brace-expansion 5.0.6 to 5.0.9. All are patch-level and within
existing semver ranges, so package.json is unchanged.
EOF
```

Verify the commit touched exactly one file:

```bash
git show --stat --oneline HEAD | tail -3
```

Expected: `frontend/package-lock.json` only.

---

### Task 2: Split the audit steps by exposure surface

**Files:**
- Modify: `.github/workflows/ci.yml:20-23` (pip-audit step) and `.github/workflows/ci.yml:35-37` (npm audit step)
- Modify: `docs/backlog.md:5-14` (Recently shipped) and `docs/backlog.md:16-18` (Next)

**Interfaces:**
- Consumes: nothing from Task 1.
- Produces: a `supply-chain-audit` job with four audit steps — `pip-audit (runtime — blocking)`, `pip-audit (dev tooling — advisory)`, `npm audit (runtime — blocking)`, `npm audit (dev tooling — advisory)`. Task 3 asserts these names against the real CI run.

- [ ] **Step 1: Verify both new blocking commands pass locally**

```bash
cd /Users/pedro/workspaces/fexerj-portal
.venv/bin/pip-audit -r requirements.txt; echo "PIP_EXIT=$?"
cd frontend && npm audit --omit=dev; echo "NPM_EXIT=$?"
```

Expected: `No known vulnerabilities found` / `PIP_EXIT=0`, and `found 0 vulnerabilities` / `NPM_EXIT=0`.

Both must be 0 before editing the workflow. If either fails, the design premise is broken — a runtime dependency has a real advisory, which is exactly what the blocking gate exists to catch. Stop and report rather than weakening the gate.

- [ ] **Step 2: Replace the `pip-audit` step**

In `.github/workflows/ci.yml`, replace lines 20-23:

```yaml
      - name: pip-audit
        run: |
          python -m pip install --upgrade pip pip-audit
          pip-audit -r requirements-dev.txt
```

with:

```yaml
      # Blocking: only dependencies that reach the running service.
      - name: pip-audit (runtime — blocking)
        run: |
          python -m pip install --upgrade pip pip-audit
          pip-audit -r requirements.txt

      # Advisory: dev tooling (pytest, mypy, ruff, httpx) never reaches the
      # server. requirements-dev.txt includes requirements.txt, so this pass
      # is a superset — nothing drops out of view.
      - name: pip-audit (dev tooling — advisory)
        run: pip-audit -r requirements-dev.txt
        continue-on-error: true
```

- [ ] **Step 3: Replace the `npm audit` step**

In the same file, replace what was lines 35-37 (now shifted down by the Step 2 edit):

```yaml
      - name: npm audit
        run: npm audit
        working-directory: frontend
```

with:

```yaml
      # Blocking: only what ships to the browser (react, react-dom, jszip,
      # prop-types). A high advisory here must stop the merge.
      - name: npm audit (runtime — blocking)
        run: npm audit --omit=dev
        working-directory: frontend

      # Advisory: build and test tooling (eslint, vite, jsdom). Real risk, but
      # it requires code execution on the build machine, so it must not block
      # an unrelated PR. Dependabot is the remediation path.
      - name: npm audit (dev tooling — advisory)
        run: npm audit
        working-directory: frontend
        continue-on-error: true
```

Leave the `npm ci` step above it untouched — both audit steps depend on it.

- [ ] **Step 4: Validate the YAML parses**

`actionlint` is not installed. Use PyYAML, which is:

```bash
cd /Users/pedro/workspaces/fexerj-portal
.venv/bin/python -c "
import yaml
d = yaml.safe_load(open('.github/workflows/ci.yml'))
steps = d['jobs']['supply-chain-audit']['steps']
for s in steps:
    if 'name' in s:
        print(repr(s['name']), '| continue-on-error =', s.get('continue-on-error', False))
print('total steps:', len(steps))
"
```

Expected output:

```
'pip-audit (runtime — blocking)' | continue-on-error = False
'pip-audit (dev tooling — advisory)' | continue-on-error = True
'npm ci' | continue-on-error = False
'npm audit (runtime — blocking)' | continue-on-error = False
'npm audit (dev tooling — advisory)' | continue-on-error = True
total steps: 8
```

Eight steps total: `checkout`, `setup-python`, two pip-audit, `setup-node`, `npm ci`, two npm audit. The three `uses:` steps carry no `name`, so exactly five names print.

If a step meant to be advisory shows `continue-on-error = False`, the gate is still blocking and the whole change is inert. Fix before committing.

- [ ] **Step 5: Confirm no other job was touched**

```bash
git diff --stat .github/workflows/ci.yml
.venv/bin/python -c "
import yaml
print(sorted(yaml.safe_load(open('.github/workflows/ci.yml'))['jobs']))
"
```

Expected job list: `['lint-python', 'lint-scripts', 'supply-chain-audit', 'test-backend', 'test-frontend']` — all five still present.

- [ ] **Step 6: Update the backlog**

`docs/backlog.md` opens with "update when items ship so sessions and PRs stay aligned", and line 18 currently claims `_No open P1/P2 hygiene items._` while CI has been red for six weeks. This step is slightly beyond the spec's literal text; it is included because the file's own stated convention asks for it and leaving it stale actively misleads the next session.

Add to the end of the `## Recently shipped (do not re-track)` list:

```markdown
- **CI supply chain**: audit split into **blocking (runtime)** and **advisory (dev tooling)** for both npm (**`--omit=dev`**) and pip (**`requirements.txt`**). A transitive dev-only advisory no longer blocks unrelated PRs; Dependabot remains the remediation path.
```

Replace line 18 (`_No open P1/P2 hygiene items._`) with:

```markdown
- **P1 — drain the Dependabot queue** (14 open PRs, oldest 2026-06-28). The advisory audit step surfaces dev-tooling findings but does not fix them — Dependabot is the remediation path, so a stalled queue means findings accumulate in a check nobody reads. Includes one major: **`mypy 1.19 → 2.3`**.
```

- [ ] **Step 7: Commit**

```bash
cd /Users/pedro/workspaces/fexerj-portal
git add .github/workflows/ci.yml docs/backlog.md
git commit -F - <<'EOF'
ci: block only on runtime dependency advisories

The supply-chain-audit job failed on every PR since 2026-06-28 because
npm audit ran without separating runtime from dev dependencies. All four
current high advisories are transitive under devDependencies (eslint,
vite, jsdom) and never reach the browser bundle, yet they blocked
fourteen unrelated dependency PRs.

Both audits now run twice: a blocking pass over runtime dependencies
only, and an advisory pass over everything. pip-audit gets the same
treatment, where dev tooling had the same latent asymmetry.

The threshold is exposure surface, not severity. An advisory in a
dependency that reaches the browser or the server still blocks the merge.
EOF
```

Verify:

```bash
git show --stat --oneline HEAD | tail -4
```

Expected: `.github/workflows/ci.yml` and `docs/backlog.md` only.

---

### Task 3: Push and verify against real CI

Local green is not the acceptance criterion. The spec requires the actual workflow passing.

**Files:** none modified.

**Interfaces:**
- Consumes: the step names produced in Task 2.
- Produces: evidence that the job passes on GitHub's runner.

- [ ] **Step 1: Review the full branch diff before pushing**

```bash
cd /Users/pedro/workspaces/fexerj-portal
git log --oneline develop..HEAD
git diff --stat develop..HEAD
```

Expected four commits, in order: the design doc, this plan, the lockfile patch, the CI change. Expected files: `docs/superpowers/specs/...`, `docs/superpowers/plans/...`, `frontend/package-lock.json`, `.github/workflows/ci.yml`, `docs/backlog.md`.

Confirm `frontend/package.json` is **not** in the list.

- [ ] **Step 2: Push the branch**

```bash
git push -u origin chore/ci-split-runtime-dev-audit
```

The branch matches the `chore/**` push trigger in `ci.yml:5`, so CI starts on push — no PR needed to get a first signal.

- [ ] **Step 3: Watch the run**

Do not poll with `sleep` — foreground `sleep` is blocked in this harness. Capture the
run id, then block on `gh run watch`, which returns when the run finishes and exits
non-zero if it failed:

```bash
cd /Users/pedro/workspaces/fexerj-portal
RUN_ID=$(gh run list --branch chore/ci-split-runtime-dev-audit --limit 1 --json databaseId --jq '.[0].databaseId')
echo "run: $RUN_ID"
gh run watch "$RUN_ID" --exit-status; echo "CI_EXIT=$?"
```

Expected: `CI_EXIT=0`. Then inspect the audit steps specifically:

```bash
gh run view "$RUN_ID" --log 2>&1 | grep -E 'Supply chain audit.*(npm audit|pip-audit)' | tail -20
```

Expected: all five jobs green. Within `supply-chain-audit`, the two blocking steps pass, and the advisory `npm audit (dev tooling — advisory)` reports **0 vulnerabilities** — Task 1 cleared them. The advisory step's value shows up on a future advisory, not today.

- [ ] **Step 4: If the run fails, diagnose before touching anything**

Do not re-run hoping for a different result, and do not weaken the gate to force green. Pull the failing step:

```bash
gh run view "$RUN_ID" --log-failed 2>&1 | head -60
```

A failure in `npm audit (runtime — blocking)` means a genuine runtime advisory landed — that is the gate working, and it needs a real fix, not a config change.

- [ ] **Step 5: Report to Pedro and stop — acceptance is not yet met**

Do **not** open the pull request. `CLAUDE.md` authorizes branches, commits, and pushes; the PR is a separate call.

State this plainly in the report: **a green push run does not satisfy the spec.** The
`push` and `pull_request` triggers are different events — push builds the branch tip,
while `pull_request` builds the merge result against `develop`. The spec's acceptance
criterion is the second one, so at this point the work is verified but not accepted.

Report: the three commits, the push CI result with job names, the gap above, and the
proposed PR text below for approval.

- [ ] **Step 6: After Pedro opens the PR (or authorizes it), verify the PR run**

This step closes the spec's acceptance criterion and cannot be skipped.

```bash
cd /Users/pedro/workspaces/fexerj-portal
PR_RUN=$(gh run list --branch chore/ci-split-runtime-dev-audit --event pull_request --limit 1 --json databaseId --jq '.[0].databaseId')
gh run watch "$PR_RUN" --exit-status; echo "PR_CI_EXIT=$?"
```

Expected: `PR_CI_EXIT=0` with all five jobs green.

Only after this passes is the task complete. If `--event pull_request` returns empty,
the PR is not open yet — wait, do not substitute the push run and call it done.

**Proposed PR title:**

```
ci: block only on runtime dependency advisories
```

**Proposed PR description:**

```markdown
## Problem

`supply-chain-audit` has failed on every PR since 2026-06-28, blocking all
14 open Dependabot PRs — including `fastapi` and `uvicorn` bumps unrelated
to the cause.

`npm audit` ran without separating runtime from dev dependencies, so any
advisory anywhere in the transitive tree failed the build. The four current
`high` findings are all transitive under `devDependencies`:

| Package | Chain | Runs at |
|---|---|---|
| `brace-expansion` | `eslint` → `minimatch` | lint |
| `postcss` | `vite` | build |
| `nanoid` | `vite` → `postcss` | build |
| `undici` | `jsdom` | test env |

None reach the browser bundle.

## Changes

- **`.github/workflows/ci.yml`** — both audits split into a blocking pass over
  runtime dependencies (`npm audit --omit=dev`, `pip-audit -r requirements.txt`)
  and an advisory pass over everything (`continue-on-error: true`). The
  threshold is exposure surface, not severity: an advisory in a dependency that
  reaches the browser or the server still blocks the merge.
- **`frontend/package-lock.json`** — `npm audit fix` clears the four current
  findings: `undici 7.28.0→7.29.0`, `postcss 8.5.15→8.5.26`,
  `nanoid 3.3.14→3.3.18`, `brace-expansion 5.0.6→5.0.9`. All patch-level and
  within existing semver ranges, so **`package.json` is unchanged**. The diff is
  14 insertions and 14 deletions — nothing else moves.
- **`docs/backlog.md`** — records the change and replaces the stale
  "No open P1/P2 hygiene items" with draining the Dependabot queue.

## Known trade-off

The advisory step surfaces dev-tooling findings but does not fix them —
Dependabot is the remediation path. A stalled Dependabot queue means findings
accumulate in a check nobody reads, which makes draining that queue the next
piece of work rather than an optional follow-up.

## Test plan

- `cd frontend && npm ci && npm run lint && npm run test:coverage && npm run build`
- `pytest tests/`
- CI green on this branch
```
