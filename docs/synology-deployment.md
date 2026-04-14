# FEXERJ Portal — Synology NAS Deployment

## 1. Overview

This document describes the architecture, implementation, and security posture of the FEXERJ Portal deployment on a Synology NAS. It is intended for review by the system architect and information security team.

The FEXERJ Portal is a staff-facing web application used by the FEXERJ chess federation to run tournament rating cycles. It consists of a Python/FastAPI backend and a React frontend. The portal is protected by HTTP Basic Authentication and is not intended for public access.

The Synology deployment replaces an on-demand AWS EC2 setup. The NAS runs continuously at the operator's premises, eliminating cloud hosting costs while maintaining HTTPS and domain-based access.

---

## 2. System Architecture

```
Internet
    │
    │ HTTPS (port 443)
    ▼
Synology Reverse Proxy (DSM built-in, nginx-based)
    │                          │
    │ fexerj.pedrofaraco.com   │ uat.fexerj.pedrofaraco.com
    ▼                          ▼
Docker: fexerj-prod-nginx-1   Docker: fexerj-uat-nginx-1
    (port 8090)                    (port 8080)
    │                          │
    │ proxy_pass                │ proxy_pass
    ▼                          ▼
Docker: fexerj-prod-backend-1  Docker: fexerj-uat-backend-1
    (port 8000, internal)          (port 8000, internal)
```

### Components

| Component | Technology | Description |
|---|---|---|
| Reverse Proxy | Synology DSM (nginx) | Terminates TLS, routes by hostname to Docker containers |
| Nginx container | nginx:alpine | Serves frontend static files, proxies API requests to backend |
| Backend container | python:3.12-slim + uvicorn | Runs the FastAPI application |
| Frontend | React + Vite (static build) | Built on the NAS at deploy time, served by Nginx |
| TLS Certificate | Let's Encrypt (DSM-managed) | Single certificate covering both prod and UAT domains |

### Environments

| Environment | Branch | Domain | Nginx Port |
|---|---|---|---|
| Production | `master` | `fexerj.pedrofaraco.com` | 8090 |
| UAT | `develop` | `uat.fexerj.pedrofaraco.com` | 8080 |

---

## 3. Infrastructure

### Hardware

- **Device:** Synology DS225+
- **CPU:** AMD Ryzen R1600 (dual-core)
- **RAM:** 2 GB (expandable to 32 GB)
- **OS:** Synology DSM 7.x
- **Location:** Operator's home network

### Network

- **NAS local IP:** `192.168.50.101`
- **Public IP:** Dynamic, managed via Synology DDNS (`faraco.synology.me`)
- **DNS:** DreamHost — both `fexerj.pedrofaraco.com` and `uat.fexerj.pedrofaraco.com` are CNAME records pointing to `faraco.synology.me`
- **Router:** Port 443 forwarded to NAS
- **SSH port:** 3582 (non-standard, operator-configured)

### Synology Packages Installed

| Package | Purpose |
|---|---|
| Container Manager | Docker engine and Docker Compose |
| Git | Repository cloning and updates on the NAS |
| Node.js v22 | Frontend build (`npm ci`, `npm run build`) |

---

## 4. Repository Changes

All changes are in the `pedrofaraco/fexerj-portal` GitHub repository. No existing files were modified — all additions are new files.

### Files Added

#### `Dockerfile`
Builds the backend Docker image.

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ backend/
COPY calculator/ calculator/
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- Base image: official `python:3.12-slim` from Docker Hub
- Only application code and dependencies are copied — no credentials, no config files
- Backend binds to `0.0.0.0:8000` inside the container (not exposed to the host directly)

#### `docker-compose.yml` (production)

```yaml
services:
  backend:
    build: .
    env_file: .env
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "8090:80"
    volumes:
      - ./frontend/dist:/usr/share/nginx/html:ro
      - ./docker/nginx.conf:/etc/nginx/conf.d/default.conf:ro
    depends_on:
      - backend
    restart: unless-stopped
```

- Backend credentials are loaded from `.env` file (see Section 5)
- Nginx mounts the built frontend as read-only
- Only port 8090 is exposed to the host; backend port 8000 is internal to the Docker network
- Both containers restart automatically on failure

#### `docker-compose.uat.yml` (UAT)

Identical to `docker-compose.yml` except Nginx exposes port 8080 instead of 8090.

#### `docker/nginx.conf`

```nginx
server {
    listen 80;

    # Align with backend upload limits to avoid nginx returning a generic 413
    # before the backend can provide a user-friendly message.
    client_max_body_size 100m;

    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location ~ ^/(health|me|validate|run)$ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # /run can take time; keep proxy timeouts generous.
        proxy_read_timeout 600s;
        proxy_send_timeout 600s;
    }
}
```

- Serves frontend static files for all routes (SPA routing)
- Proxies only the four known API endpoints to the backend by name
- No other paths are proxied — the backend is not directly reachable from outside

#### `scripts/deploy-synology.sh.example`

A reference version of the deployment script that contains only placeholder values. **Committed to the repository.**

#### `scripts/deploy-synology.conf.example`

An example configuration file containing only placeholder values. **Committed to the repository.**

#### `scripts/deploy-synology.sh`

The deployment script used by the operator. It reads settings from `deploy-synology.conf`.

#### `scripts/deploy-synology.conf` *(gitignored — never committed)*

Configuration file sourced by `deploy-synology.sh`. Contains NAS connection details and environment-specific settings. Lives only on the operator's laptop.

---

## 5. Credential Management

### Portal Credentials (username/password)

- Stored in a `.env` file on the NAS at `/volume1/docker/fexerj-portal-prod/.env` and `/volume1/docker/fexerj-portal-uat/.env`
- File permissions: `chmod 600` (readable only by the owner)
- Written once at first deploy — the deploy script prompts the operator interactively and never stores them on the laptop
- **Never committed to the repository**
- Passed to the backend container via Docker's `env_file` directive
- The backend enforces a minimum password length of 8 characters and rejects the default `changeme` password when `PORTAL_ENVIRONMENT=production`

### NAS Credentials

- SSH authentication uses a pre-existing key pair (`~/.ssh/synology_faraco`) — no password stored anywhere
- The NAS sudo password is prompted at deploy time and held only in memory for the duration of the script
- **Never written to disk on the laptop or the NAS**

### What is NOT stored anywhere sensitive

| Secret | Where it lives |
|---|---|
| Portal username/password | `.env` on NAS only (chmod 600) |
| NAS SSH private key | Operator's laptop `~/.ssh/` only |
| NAS sudo password | Prompted at runtime, never persisted |
| NAS IP / SSH port | `deploy-synology.conf` on operator's laptop only (gitignored) |

---

## 6. TLS / HTTPS

- Certificate issued by **Let's Encrypt** via Synology DSM's built-in certificate manager
- Covers both `fexerj.pedrofaraco.com` and `uat.fexerj.pedrofaraco.com` as Subject Alternative Names
- Renewed automatically by DSM
- TLS is terminated at the Synology Reverse Proxy layer — traffic between the reverse proxy and the Docker containers is plain HTTP on the internal loopback interface (`localhost`)
- HTTP Basic Auth credentials travel only over the TLS-encrypted connection

---

## 7. Network Exposure

### Inbound

| Port | Protocol | Exposed to | Purpose |
|---|---|---|---|
| 443 | HTTPS | Internet | Portal access (prod and UAT via SNI) |
| 3582 | SSH | Internet | Operator deployment access |
| 5000 | HTTP | LAN only | DSM admin interface |
| 5001 | HTTPS | LAN only | DSM admin interface |

### Internal (Docker network)

| Port | Protocol | Exposed to | Purpose |
|---|---|---|---|
| 8000 | HTTP | Docker internal only | Backend API |
| 8090 | HTTP | localhost | Prod Nginx → Synology Reverse Proxy |
| 8080 | HTTP | localhost | UAT Nginx → Synology Reverse Proxy |

The backend container is **not directly reachable** from outside the Docker network. All external traffic goes through Nginx, which only proxies the four defined API endpoints.

---

## 8. Deployment Process

The operator runs a single command from their laptop:

```bash
bash scripts/deploy-synology.sh prod   # or uat
```

The script performs the following steps:

1. Resolves environment variables from `deploy-synology.conf`
2. Prompts for the NAS sudo password (held in memory only)
3. SSHs into the NAS and clones or updates the repository from GitHub to the appropriate directory
4. On first run: prompts for portal credentials and writes them to `.env` on the NAS (`chmod 600`)
5. Builds the React frontend on the NAS using Node.js 22
6. Runs `docker compose up -d --build` via sudo to build and start the containers
7. Polls `https://<domain>/health` every 10 seconds until the backend responds, printing elapsed time
8. Reports success with the live URL

### Re-deploy / Update

Running `deploy-synology.sh` again on an existing deployment:
- Pulls the latest code from the branch
- Rebuilds the frontend
- Rebuilds the Docker image if the `Dockerfile` or dependencies changed
- Restarts only the containers that changed (Docker Compose handles this)
- The `.env` file is not touched on subsequent runs

---

## 9. Known Limitations and Risks

| Risk | Severity | Notes |
|---|---|---|
| Single point of failure | Medium | NAS going offline takes both prod and UAT down. No redundancy. |
| Dynamic home IP | Low | Mitigated by Synology DDNS (`faraco.synology.me`). DNS TTL-based propagation if IP changes. |
| Home internet reliability | Medium | Dependent on ISP uptime. No SLA. Acceptable for occasional staff use. |
| No WAF or DDoS protection | Low | Portal is staff-only with HTTP Basic Auth. Not a public-facing service. |
| SSH port exposed to internet | Low | Non-standard port (3582), key-based auth only. |
| Let's Encrypt renewal | Low | Managed automatically by DSM. Failure would cause HTTPS to break after 90 days. |
| No container health checks | Low | Containers restart on failure via `restart: unless-stopped`. No alerting on restart loops. |
| Frontend built on NAS | Low | Requires Node.js 22 installed on NAS. If removed, deploy fails at build step. |

---

## 10. What Was Not Changed

The following components remain **unchanged** from the original implementation:

- `backend/` — FastAPI application code
- `frontend/` — React application code
- `calculator/` — Rating calculator library
- `tests/` — Test suite
- `scripts/setup.sh` — EC2 Ubuntu provisioning script (still functional)
- `scripts/launch.sh` — AWS EC2 on-demand launch script (still functional)
- `scripts/terminate.sh` — AWS EC2 termination script (still functional)

Both the AWS EC2 and Synology NAS deployment paths are fully operational and independent of each other.
