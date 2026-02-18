#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# POT Matchmaker — Deploy to EC2
# Usage: ./deploy/push.sh <EC2_PUBLIC_IP_OR_DNS> [path/to/key.pem]
# Example: ./deploy/push.sh 54.123.45.67 ~/.ssh/pot-key.pem
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

EC2_HOST="${1:?Usage: ./deploy/push.sh <EC2_HOST> [key.pem]}"
KEY_ARG=""
if [[ -n "${2:-}" ]]; then
  KEY_ARG="-i $2"
fi
SSH="ssh $KEY_ARG ec2-user@$EC2_HOST"
SCP="rsync -avz --progress $KEY_ARG"
APP_DIR="/home/ec2-user/app"

echo "==> Building frontend..."
cd "$(dirname "$0")/.."
(cd frontend && npm run build)

echo "==> Syncing backend to EC2..."
$SCP \
  --exclude '.venv' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude '.env' \
  backend/ "ec2-user@$EC2_HOST:$APP_DIR/backend/"

echo "==> Syncing frontend dist to EC2..."
$SCP frontend/dist/ "ec2-user@$EC2_HOST:$APP_DIR/frontend/dist/"

echo "==> Syncing deploy configs..."
$SCP deploy/ "ec2-user@$EC2_HOST:$APP_DIR/deploy/"

echo "==> Installing Python deps on EC2..."
$SSH "cd $APP_DIR/backend && source .venv/bin/activate && pip install -r requirements.txt -q"

echo "==> Running database migrations..."
$SSH "cd $APP_DIR/backend && source .venv/bin/activate && alembic upgrade head"

echo "==> Restarting backend service..."
$SSH "sudo systemctl restart pot-matchmaker"

echo "==> Reloading nginx..."
$SSH "sudo nginx -t && sudo systemctl reload nginx"

echo ""
echo "✓ Deployment complete — http://$EC2_HOST"
echo ""
$SSH "sudo systemctl status pot-matchmaker --no-pager | tail -5"
