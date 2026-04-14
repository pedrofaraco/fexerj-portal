#!/usr/bin/env bash
set -euo pipefail

ENV="${1:-}"
[[ "$ENV" == "prod" || "$ENV" == "uat" ]] || { echo "[ERROR] Usage: $0 <prod|uat>" >&2; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/deploy-synology.conf"
[[ -f "$CONFIG_FILE" ]] || { echo "[ERROR] Missing ${CONFIG_FILE}. Copy deploy-synology.conf.example and fill in your values." >&2; exit 1; }
# shellcheck disable=SC1090,SC1091
source "$CONFIG_FILE"

# ── Helpers ───────────────────────────────────────────────────────────────────

info()  { echo "[INFO]  $*"; }
error() { echo "[ERROR] $*" >&2; exit 1; }

NAS_PATH="/var/packages/Git/target/usr/bin:/var/packages/Node.js_v22/target/usr/local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
nas_ssh() { ssh -i "${NAS_SSH_KEY}" -p "$NAS_SSH_PORT" "${NAS_USER}@${NAS_HOST}" "export PATH=${NAS_PATH}; $*"; }

# ── Resolve env vars ──────────────────────────────────────────────────────────

if [[ "$ENV" == "prod" ]]; then
    DEPLOY_DIR="$PROD_DIR"
    BRANCH="$PROD_BRANCH"
    DOMAIN="$PROD_DOMAIN"
    COMPOSE_FILE="docker-compose.yml"
    PROJECT_NAME="fexerj-prod"
    PORTAL_ENVIRONMENT="production"
else
    DEPLOY_DIR="$UAT_DIR"
    BRANCH="$UAT_BRANCH"
    DOMAIN="$UAT_DOMAIN"
    COMPOSE_FILE="docker-compose.uat.yml"
    PROJECT_NAME="fexerj-uat"
    PORTAL_ENVIRONMENT="development"
fi

info "Environment : ${ENV} (branch: ${BRANCH})"
info "NAS target  : ${NAS_USER}@${NAS_HOST}:${NAS_SSH_PORT}"
info "Deploy dir  : ${DEPLOY_DIR}"
info "Portal env  : ${PORTAL_ENVIRONMENT}"

read -rsp "NAS sudo password: " NAS_SUDO_PASS
echo

# ── First-run credential setup ────────────────────────────────────────────────

ENV_FILE="${DEPLOY_DIR}/.env"
if ! nas_ssh "test -f ${ENV_FILE}" 2>/dev/null; then
    info "No .env found on NAS. Setting up credentials..."
    read -rp "Portal username: " PORTAL_USER
    [[ -n "$PORTAL_USER" ]] || error "Username is required."
    read -rsp "Portal password: " PORTAL_PASSWORD
    echo
    [[ -n "$PORTAL_PASSWORD" ]] || error "Password is required."
    [[ ${#PORTAL_PASSWORD} -ge 8 ]] || error "Password must be at least 8 characters."
fi

# ── Clone or update repo on NAS ───────────────────────────────────────────────

nas_ssh "
    set -euo pipefail
    if [[ ! -d ${DEPLOY_DIR}/.git ]]; then
        mkdir -p ${DEPLOY_DIR}
        git clone --branch ${BRANCH} ${REPO_URL} ${DEPLOY_DIR}
    else
        cd ${DEPLOY_DIR}
        git fetch origin
        git checkout ${BRANCH}
        git reset --hard origin/${BRANCH}
    fi
"

# ── Write .env if first run ───────────────────────────────────────────────────

if ! nas_ssh "test -f ${ENV_FILE}" 2>/dev/null; then
    nas_ssh "cat > ${ENV_FILE} << 'EOF'
PORTAL_ENVIRONMENT=${PORTAL_ENVIRONMENT}
PORTAL_USER=${PORTAL_USER}
PORTAL_PASSWORD=${PORTAL_PASSWORD}
EOF
chmod 600 ${ENV_FILE}"
    info "Credentials written to ${ENV_FILE} on NAS."
fi

# ── Build frontend on NAS ─────────────────────────────────────────────────────

info "Building frontend..."
nas_ssh "
    set -euo pipefail
    cd ${DEPLOY_DIR}/frontend
    npm ci --silent
    npm run build
"

# ── Build and restart containers ──────────────────────────────────────────────

info "Building and starting Docker containers..."
nas_ssh "
    set -euo pipefail
    cd ${DEPLOY_DIR}
    echo '${NAS_SUDO_PASS}' | sudo -S docker compose -f ${COMPOSE_FILE} -p ${PROJECT_NAME} up -d --build
"

# ── Poll until live ───────────────────────────────────────────────────────────

info "Waiting for portal to be live at https://${DOMAIN} ..."
echo ""

TIMEOUT=300
INTERVAL=10
START_TIME=$SECONDS

while [[ $(( SECONDS - START_TIME )) -lt $TIMEOUT ]]; do
    if curl -sf --max-time 5 "https://${DOMAIN}/health" -o /dev/null 2>/dev/null; then
        ELAPSED=$(( SECONDS - START_TIME ))
        printf "\r"
        info "Portal is live at https://${DOMAIN} (took $((ELAPSED / 60))min$((ELAPSED % 60))s)"
        echo ""
        exit 0
    fi
    ELAPSED=$(( SECONDS - START_TIME ))
    printf "\r[INFO]  Still starting... %dmin%02ds elapsed" $(( ELAPSED / 60 )) $(( ELAPSED % 60 ))
    sleep $INTERVAL
done

echo ""
echo "[WARN]  Portal did not respond within 5 minutes. Check Container Manager on the NAS."
