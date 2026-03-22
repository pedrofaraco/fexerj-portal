#!/usr/bin/env bash
# update.sh — Pull the latest code and redeploy the FEXERJ Portal.
#
# Usage:
#   bash update.sh
#
# Run from the repository root on the server whenever a new version
# has been merged into the master branch.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_NAME="fexerj-portal"

info()  { echo "[INFO]  $*"; }
error() { echo "[ERROR] $*" >&2; exit 1; }

cd "${REPO_DIR}"

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
