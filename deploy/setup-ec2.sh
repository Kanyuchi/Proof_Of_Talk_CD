#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# POT Matchmaker — First-time EC2 setup (Amazon Linux 2023)
# Run once on the server: bash setup-ec2.sh
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

APP_DIR="/home/ec2-user/app"
LOG_DIR="/var/log/pot-matchmaker"

echo "==> Updating system packages..."
sudo dnf update -y

echo "==> Installing dependencies..."
sudo dnf install -y nginx python3.12 python3.12-pip git rsync

echo "==> Installing Certbot (for SSL later)..."
sudo dnf install -y certbot python3-certbot-nginx || true

echo "==> Creating app directory..."
mkdir -p "$APP_DIR/backend"
mkdir -p "$APP_DIR/frontend/dist"

echo "==> Creating log directory..."
sudo mkdir -p "$LOG_DIR"
sudo chown ec2-user:ec2-user "$LOG_DIR"

echo "==> Installing gunicorn..."
pip3.12 install --user gunicorn uvicorn[standard]

echo "==> Copying nginx config..."
sudo cp "$APP_DIR/deploy/nginx.conf" /etc/nginx/conf.d/pot-matchmaker.conf
sudo nginx -t && sudo systemctl enable nginx && sudo systemctl start nginx

echo "==> Installing systemd service..."
sudo cp "$APP_DIR/deploy/pot-matchmaker.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable pot-matchmaker

echo ""
echo "✓ EC2 setup complete."
echo ""
echo "Next steps:"
echo "  1. Copy your .env file to $APP_DIR/backend/.env"
echo "  2. Run: cd $APP_DIR/backend && python3.12 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
echo "  3. Run: alembic upgrade head"
echo "  4. Run: sudo systemctl start pot-matchmaker"
echo "  5. Edit /etc/nginx/conf.d/pot-matchmaker.conf and replace YOUR_DOMAIN"
echo "  6. Run: sudo certbot --nginx -d YOUR_DOMAIN  (for HTTPS)"
