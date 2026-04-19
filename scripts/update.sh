#!/usr/bin/env bash
# update.sh — Pull the latest code and redeploy the FEXERJ Portal.
#
# Usage:
#   bash update.sh
#
# Run from the repository root on the server whenever a new version
# has been merged into the master branch.
#
# If any step fails the script automatically rolls back to the previous
# working commit and restarts the service.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_NAME="fexerj-portal"

info()  { echo "[INFO]  $*"; }
error() { echo "[ERROR] $*" >&2; exit 1; }

cd "${REPO_DIR}"

# ── Rollback ──────────────────────────────────────────────────────────────────

PREVIOUS_COMMIT="$(git rev-parse HEAD)"

rollback() {
    local original_exit=$?
    trap - ERR # prevent recursive invocation if a rollback step itself fails

    echo "" >&2
    echo "[ERROR] Update failed (exit ${original_exit}) — rolling back to ${PREVIOUS_COMMIT}..." >&2

    # Use `git reset --hard` (not `git checkout <sha> -- .`) so HEAD actually
    # moves back to the known-good commit. With `checkout -- .` only the
    # working tree is rewritten; HEAD stays at the broken commit, which
    # leaves `git log` misleading and causes the next `git pull` to see
    # the reverted files as local "modifications" to re-apply.
    if ! git reset --hard "${PREVIOUS_COMMIT}"; then
        echo "[ERROR] Rollback: git reset --hard failed. Working tree may be inconsistent." >&2
        echo "[ERROR] Manual intervention required." >&2
        exit "${original_exit}"
    fi

    # shellcheck source=/dev/null
    if ! source .venv/bin/activate; then
        echo "[ERROR] Rollback: could not activate venv. Manual intervention required." >&2
        exit "${original_exit}"
    fi

    if ! pip install --quiet -r requirements.txt; then
        echo "[WARN]  Rollback: pip install failed — service may run with stale dependencies." >&2
    fi

    if ! (cd "${REPO_DIR}/frontend" && npm ci --silent && npm run build); then
        echo "[WARN]  Rollback: frontend rebuild failed — users may see stale UI." >&2
    fi

    if ! sudo systemctl restart "${SERVICE_NAME}"; then
        echo "[ERROR] Rollback: service restart failed. Service is likely down." >&2
        echo "[ERROR] Manual intervention required." >&2
        exit "${original_exit}"
    fi

    if ! sudo systemctl reload nginx; then
        echo "[WARN]  Rollback: nginx reload failed — config may be stale." >&2
    fi

    echo "[INFO]  Rollback complete. Previous version restored." >&2
    echo "[ERROR] Original update failed (exit ${original_exit})." >&2
    exit "${original_exit}"
}

trap rollback ERR

# ── Update ────────────────────────────────────────────────────────────────────

info "Pulling latest code from master..."
git pull origin master

info "Updating Python dependencies..."
# shellcheck source=/dev/null
source .venv/bin/activate
pip install --quiet -r requirements.txt

info "Rebuilding frontend..."
cd frontend
npm ci --silent
npm run build
cd ..

info "Restarting backend service..."
sudo systemctl restart "${SERVICE_NAME}"

info "Reloading Nginx..."
sudo systemctl reload nginx

info "Update complete."
