#!/bin/bash
set -e

# =========================
# CONFIG
# =========================
REMOTE_USER="saad"
REMOTE_HOST="37.59.112.214"
SSH_PORT=22

APP_NAME="wikimetron2"
REMOTE_DIR="/home/saad/$APP_NAME"

# =========================
# PRE-CHECKS
# =========================
echo "🔎 Checking Docker..."
docker info >/dev/null

echo "🔎 Checking SSH..."
ssh -p $SSH_PORT $REMOTE_USER@$REMOTE_HOST "echo SSH OK"

# =========================
# SYNC PROJECT
# =========================
echo "📦 Syncing project..."
rsync -avz --delete \
  --exclude node_modules \
  --exclude .git \
  --exclude .next \
  -e "ssh -p $SSH_PORT" \
  ./ $REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR

# =========================
# REMOTE DEPLOY
# =========================
ssh -p $SSH_PORT $REMOTE_USER@$REMOTE_HOST <<EOF
set -e
cd $REMOTE_DIR

echo "🛑 Stopping old stack..."
docker compose down || true

echo "🐳 Building images..."
docker compose build

echo "🚀 Starting stack..."
docker compose up -d

echo "📊 Stack status:"
docker compose ps
EOF

echo "✅ Wikimetron deployed successfully"