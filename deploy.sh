#!/bin/bash
set -euo pipefail

# =========================
# CONFIG
# =========================
REMOTE_USER="saad"
REMOTE_HOST="37.59.112.214"
SSH_PORT=22

APP_NAME="wikimetron2"
REMOTE_DIR="/home/saad/${APP_NAME}"

# =========================
# PRE-CHECKS LOCAL
# =========================
echo "🔎 Checking local Docker..."
docker info >/dev/null

echo "🔎 Checking SSH connectivity..."
ssh -p "$SSH_PORT" "$REMOTE_USER@$REMOTE_HOST" "echo SSH OK"

# =========================
# HARD RESET REMOTE CODE
# =========================
echo "🔥 Removing remote project directory..."
ssh -p "$SSH_PORT" "$REMOTE_USER@$REMOTE_HOST" <<EOF
set -e
rm -rf "$REMOTE_DIR"
mkdir -p "$REMOTE_DIR"
EOF

# =========================
# SYNC PROJECT (SOURCE OF TRUTH = LOCAL)
# =========================
echo "📦 Syncing fresh project snapshot..."
rsync -avz \
  --exclude node_modules \
  --exclude .git \
  --exclude .next \
  --exclude dist \
  --exclude build \
  -e "ssh -p $SSH_PORT" \
  ./ "$REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR/"

# =========================
# REMOTE DEPLOY
# =========================
ssh -p "$SSH_PORT" "$REMOTE_USER@$REMOTE_HOST" <<EOF
set -e
cd "$REMOTE_DIR"

echo "🛑 Stopping existing stack (if any)..."
docker compose down || true

echo "🧹 Cleaning dangling images..."
docker image prune -f

echo "🐳 Building images (no cache)..."
docker compose build --no-cache

echo "🚀 Starting stack..."
docker compose up -d

echo "📊 Stack status:"
docker compose ps
EOF

echo "✅ Wikimetron deployed successfully (clean state)"