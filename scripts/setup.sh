#!/usr/bin/env bash
# setup.sh — Provision a fresh Ubuntu 24.04 server for the FEXERJ Portal.
#
# Usage:
#   bash setup.sh
#
# Run once on a new EC2 instance after cloning the repository.
# The script is idempotent: re-running it is safe.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_NAME="fexerj-portal"
ENV_FILE="/etc/${SERVICE_NAME}.env"
NGINX_SITE="/etc/nginx/sites-available/${SERVICE_NAME}"
SYSTEMD_UNIT="/etc/systemd/system/${SERVICE_NAME}.service"

# ── Helpers ──────────────────────────────────────────────────────────────────

info()  { echo "[INFO]  $*"; }
error() { echo "[ERROR] $*" >&2; exit 1; }

require_root() {
    [[ $EUID -eq 0 ]] || error "Please run with sudo: sudo bash $0"
}

# ── Prompts ───────────────────────────────────────────────────────────────────

read_domain() {
    if [[ -n "${DOMAIN:-}" ]]; then
        info "Using DOMAIN from environment: ${DOMAIN}"
        return
    fi
    if [[ -f "${NGINX_SITE}" ]]; then
        DOMAIN=$(grep -oP '(?<=server_name )[^\s;]+' "${NGINX_SITE}" | head -1)
        info "Nginx config already exists for domain '${DOMAIN}', skipping domain prompt."
        return
    fi
    read -rp "Domain name (e.g. fexerj.pedrofaraco.com): " DOMAIN
    [[ -n "$DOMAIN" ]] || error "Domain name is required."
}

read_credentials() {
    if [[ -n "${PORTAL_USER:-}" && -n "${PORTAL_PASSWORD:-}" ]]; then
        info "Using credentials from environment."
        return
    fi
    if [[ -f "${ENV_FILE}" ]]; then
        info "Credentials file ${ENV_FILE} already exists, skipping credential prompt."
        # shellcheck source=/dev/null
        source "${ENV_FILE}"
        return
    fi
    read -rp "Portal username: " PORTAL_USER
    [[ -n "$PORTAL_USER" ]] || error "Username is required."
    read -rsp "Portal password: " PORTAL_PASSWORD
    echo
    [[ -n "$PORTAL_PASSWORD" ]] || error "Password is required."
}

# ── Steps ─────────────────────────────────────────────────────────────────────

install_system_deps() {
    info "Updating package lists..."
    apt-get update -q

    info "Installing system dependencies..."
    apt-get install -y -q python3-pip python3-venv nginx git certbot python3-certbot-nginx
}

install_node() {
    if command -v node &>/dev/null && [[ "$(node --version)" == v22* ]]; then
        info "Node.js 22 already installed, skipping."
        return
    fi
    info "Installing Node.js 22..."
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
    apt-get install -y -q nodejs
}

add_swap() {
    if swapon --show | grep -q /swapfile; then
        info "Swap already active, skipping."
        return
    fi
    info "Adding 512 MB swap file..."
    fallocate -l 512M /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
}

setup_python() {
    info "Setting up Python virtual environment..."
    sudo -u ubuntu bash -c "
        cd ${REPO_DIR}
        python3 -m venv .venv
        source .venv/bin/activate
        pip install --quiet -r requirements.txt
    "
}

build_frontend() {
    info "Building React frontend..."
    sudo -u ubuntu bash -c "
        cd ${REPO_DIR}/frontend
        npm ci --silent
        npm run build
    "
}

write_env_file() {
    info "Writing environment file ${ENV_FILE}..."
    cat > "${ENV_FILE}" <<EOF
PORTAL_USER=${PORTAL_USER}
PORTAL_PASSWORD=${PORTAL_PASSWORD}
EOF
    chmod 600 "${ENV_FILE}"
}

write_systemd_unit() {
    info "Writing systemd unit ${SYSTEMD_UNIT}..."
    cat > "${SYSTEMD_UNIT}" <<EOF
[Unit]
Description=FEXERJ Portal API
After=network.target

[Service]
User=ubuntu
WorkingDirectory=${REPO_DIR}
EnvironmentFile=${ENV_FILE}
ExecStart=${REPO_DIR}/.venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF
    systemctl daemon-reload
    systemctl enable "${SERVICE_NAME}"
    systemctl restart "${SERVICE_NAME}"
    info "Backend service started."
}

write_nginx_config() {
    info "Writing Nginx configuration..."
    cat > "${NGINX_SITE}" <<EOF
server {
    listen 80;
    server_name ${DOMAIN};

    root ${REPO_DIR}/frontend/dist;
    index index.html;

    location / {
        try_files \$uri \$uri/ /index.html;
    }

    location ~ ^/(me|run|validate) {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
}
EOF

    # Allow Nginx to read files owned by ubuntu
    chmod o+x /home/ubuntu

    # Enable site and remove default
    ln -sf "${NGINX_SITE}" /etc/nginx/sites-enabled/
    rm -f /etc/nginx/sites-enabled/default

    nginx -t
    systemctl reload nginx
    info "Nginx configured."
}

setup_https() {
    if certbot certificates 2>/dev/null | grep -q "Domains: ${DOMAIN}"; then
        info "HTTPS certificate already exists for ${DOMAIN}, skipping."
        return
    fi
    info "Requesting HTTPS certificate for ${DOMAIN}..."
    certbot --nginx -d "${DOMAIN}" --non-interactive --agree-tos --register-unsafely-without-email
    info "HTTPS enabled."
}

# ── Main ──────────────────────────────────────────────────────────────────────

main() {
    require_root
    read_domain
    read_credentials

    add_swap
    install_system_deps
    install_node
    setup_python
    build_frontend
    write_env_file
    write_systemd_unit
    write_nginx_config
    setup_https

    info "Setup complete. Portal is live at https://${DOMAIN}"
}

main "$@"
