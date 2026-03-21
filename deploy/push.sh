#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# POT Matchmaker — Deploy to EC2
# Usage: ./deploy/push.sh <EC2_PUBLIC_IP_OR_DNS> [path/to/key.pem]
# Example: ./deploy/push.sh 54.123.45.67 ~/.ssh/pot-key.pem
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

EC2_HOST="${1:?Usage: ./deploy/push.sh <EC2_HOST> [key.pem]}"
KEY_FILE="${2:-}"
SSH_OPTS=()
RSYNC_OPTS=(-avz --progress)
if [[ -n "$KEY_FILE" ]]; then
  SSH_OPTS+=(-i "$KEY_FILE")
  RSYNC_OPTS+=(-e "ssh -i $KEY_FILE")
fi
SSH=(ssh ${SSH_OPTS+"${SSH_OPTS[@]}"} "ec2-user@$EC2_HOST")
APP_DIR="/home/ec2-user/app"

echo "==> Building frontend..."
cd "$(dirname "$0")/.."
(cd frontend && npm run build)

echo "==> Syncing backend to EC2..."
rsync "${RSYNC_OPTS[@]}" \
  --exclude '.venv' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude '.env' \
  backend/ "ec2-user@$EC2_HOST:$APP_DIR/backend/"

echo "==> Syncing frontend dist to EC2..."
rsync "${RSYNC_OPTS[@]}" \
  frontend/dist/ "ec2-user@$EC2_HOST:$APP_DIR/frontend/dist/"

echo "==> Syncing deploy configs..."
rsync "${RSYNC_OPTS[@]}" \
  deploy/ "ec2-user@$EC2_HOST:$APP_DIR/deploy/"

echo "==> Installing Python deps on EC2..."
"${SSH[@]}" "cd $APP_DIR/backend && ([ -d .venv ] || python3.12 -m venv .venv) && source .venv/bin/activate && pip install -r requirements.txt -q"

echo "==> Running database migrations..."
"${SSH[@]}" "cd $APP_DIR/backend && source .venv/bin/activate && alembic upgrade head"

echo "==> Restarting backend service..."
"${SSH[@]}" "sudo systemctl restart pot-matchmaker"

echo "==> Fixing frontend permissions for nginx..."
"${SSH[@]}" "chmod o+x /home/ec2-user /home/ec2-user/app /home/ec2-user/app/frontend /home/ec2-user/app/frontend/dist && chmod -R o+r /home/ec2-user/app/frontend/dist"

echo "==> Reloading nginx..."
"${SSH[@]}" "sudo nginx -t && sudo systemctl reload nginx"

echo ""
echo "==> Deploying frontend to Netlify (pot-matchmaker)..."
if command -v netlify &>/dev/null; then
  netlify deploy --prod --dir=frontend/dist
else
  echo "⚠  netlify CLI not found — skipping Netlify deploy (run manually)"
fi

echo ""
echo "✓ Deployment complete — http://$EC2_HOST + https://meet.proofoftalk.io"
echo ""
"${SSH[@]}" "sudo systemctl status pot-matchmaker --no-pager | tail -5"
