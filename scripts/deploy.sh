#!/usr/bin/env bash
# Deploy exercise competition to Vultr VPS
# Usage: ./scripts/deploy.sh
#
# Pushes to GitHub, then SSHs to the VPS to git pull and rebuild.
# Falls back to Vultr API console command if SSH is unavailable (WSL2 NAT issue).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
REMOTE_DIR="/opt/exercise-competition"
REPO_URL="https://github.com/williaby/exercise-competition.git"

# Load config from .env
if [[ -f "$PROJECT_DIR/.env" ]]; then
    VULTR_VPS_IP="$(grep '^VULTR_VPS_IP=' "$PROJECT_DIR/.env" | cut -d= -f2-)"
    VULTR_SSH_USER="$(grep '^VULTR_SSH_USER=' "$PROJECT_DIR/.env" | cut -d= -f2-)"
    VULTR_SSH_KEY_PATH="$(grep '^VULTR_SSH_KEY_PATH=' "$PROJECT_DIR/.env" | cut -d= -f2-)"
fi

VPS_IP="${VULTR_VPS_IP:?Set VULTR_VPS_IP in .env}"
VPS_USER="${VULTR_SSH_USER:-root}"
SSH_KEY="${VULTR_SSH_KEY_PATH:-~/.ssh/id_ed25519}"

# Step 1: Push latest code to GitHub
echo "==> Pushing to GitHub..."
cd "$PROJECT_DIR"
git push origin main

# Step 2: Deploy on VPS via SSH
REMOTE_COMMANDS=$(cat <<'REMOTE_SCRIPT'
set -e
REMOTE_DIR="/opt/exercise-competition"
REPO_URL="https://github.com/williaby/exercise-competition.git"

cd "$REMOTE_DIR"

# Initialize git if needed
if [[ ! -d .git ]]; then
    git init
    git remote add origin "$REPO_URL"
fi

# Pull latest
echo "==> Pulling latest from GitHub..."
git fetch origin main
git reset --hard origin/main

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
)

echo "==> Deploying to ${VPS_USER}@${VPS_IP}..."

if ssh -o ConnectTimeout=5 -o BatchMode=yes -i "$SSH_KEY" "${VPS_USER}@${VPS_IP}" true 2>/dev/null; then
    # SSH works — deploy directly
    ssh -i "$SSH_KEY" "${VPS_USER}@${VPS_IP}" bash -s <<< "$REMOTE_COMMANDS"
else
    echo ""
    echo "==> SSH unavailable from this environment (WSL2 NAT issue)."
    echo "==> Code has been pushed to GitHub."
    echo ""
    echo "Run this on the VPS (via Termius or Vultr console):"
    echo ""
    echo "  cd /opt/exercise-competition && git fetch origin main && git reset --hard origin/main && docker compose build --no-cache && docker compose up -d"
    echo ""
    exit 1
fi
