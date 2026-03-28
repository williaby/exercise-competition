#!/usr/bin/env bash
# Deploy exercise competition to Vultr VPS
# Usage: ./scripts/deploy.sh

set -euo pipefail

# Load config from .env
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

if [[ -f "$PROJECT_DIR/.env" ]]; then
    # Only extract the specific vars we need (avoids issues with special chars in passwords)
    VULTR_VPS_IP="$(grep '^VULTR_VPS_IP=' "$PROJECT_DIR/.env" | cut -d= -f2-)"
    VULTR_SSH_USER="$(grep '^VULTR_SSH_USER=' "$PROJECT_DIR/.env" | cut -d= -f2-)"
    VULTR_SSH_KEY_PATH="$(grep '^VULTR_SSH_KEY_PATH=' "$PROJECT_DIR/.env" | cut -d= -f2-)"
fi

VPS_IP="${VULTR_VPS_IP:?Set VULTR_VPS_IP in .env}"
VPS_USER="${VULTR_SSH_USER:-root}"
SSH_KEY="${VULTR_SSH_KEY_PATH:-~/.ssh/id_ed25519}"
REMOTE_DIR="/opt/exercise-competition"

echo "==> Deploying to ${VPS_USER}@${VPS_IP}..."

# Sync project files (exclude dev-only stuff)
rsync -avz --delete \
    --exclude '.git' \
    --exclude '.venv' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '.pytest_cache' \
    --exclude '.ruff_cache' \
    --exclude '.mypy_cache' \
    --exclude 'node_modules' \
    --exclude 'frontend/node_modules' \
    --exclude 'tmp_cleanup' \
    --exclude '.env' \
    --exclude 'htmlcov' \
    --exclude '*.egg-info' \
    -e "ssh -i ${SSH_KEY}" \
    "$PROJECT_DIR/" "${VPS_USER}@${VPS_IP}:${REMOTE_DIR}/"

echo "==> Synced files to ${REMOTE_DIR}"

# Create production .env on the server if it doesn't exist
ssh -i "$SSH_KEY" "${VPS_USER}@${VPS_IP}" bash -s <<'REMOTE_SCRIPT'
cd /opt/exercise-competition

# Create prod .env if missing
if [[ ! -f .env ]]; then
    cat > .env <<'EOF'
ENVIRONMENT=production
APP_PORT=8000
LOG_LEVEL=WARNING
EXERCISE_COMPETITION_LOG_LEVEL=WARNING
EXERCISE_COMPETITION_JSON_LOGS=true
EXERCISE_COMPETITION_DATABASE_URL=sqlite:////app/data/competition.db
VERSION=latest
EOF
    echo "==> Created production .env"
fi

# Build and deploy
echo "==> Building Docker image..."
docker compose build --no-cache

echo "==> Starting services..."
docker compose up -d

echo "==> Waiting for health check..."
sleep 5

# Check health
if curl -sf http://localhost:8000/health/live > /dev/null 2>&1; then
    echo "==> Health check PASSED"
else
    echo "==> Health check failed, checking logs..."
    docker compose logs --tail=20
fi

echo "==> Deployment complete"
docker compose ps
REMOTE_SCRIPT
