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
    info "Update failed — rolling back to ${PREVIOUS_COMMIT}..."
    # Use `git reset --hard` (not `git checkout <sha> -- .`) so HEAD actually
    # moves back to the known-good commit. With `checkout -- .` only the
    # working tree is rewritten; HEAD stays at the broken commit, which
    # leaves `git log` misleading and causes the next `git pull` to see
    # the reverted files as local "modifications" to re-apply.
    git reset --hard "${PREVIOUS_COMMIT}"
    # shellcheck source=/dev/null
    source .venv/bin/activate
    pip install --quiet -r requirements.txt
    cd "${REPO_DIR}/frontend"
    npm ci --silent
    npm run build
    cd "${REPO_DIR}"
    sudo systemctl restart "${SERVICE_NAME}"
    sudo systemctl reload nginx
    info "Rollback complete. Previous version restored."
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
