#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# POT Matchmaker — Launch NEW (green) EC2 instance from scratch
#
# Usage:
#   ./deploy/green-deploy.sh <NEW_IP> [path/to/key.pem]
#
# Example:
#   bash deploy/green-deploy.sh 54.200.11.22 ~/Downloads/Credentials_Keys/pot-key.pem
#
# What it does:
#   1. SCP setup-ec2.sh + nginx.conf to the new instance
#   2. Run first-time bootstrap on the new instance
#   3. Copy backend/.env to the new instance (same RDS, updated ALLOWED_ORIGINS)
#   4. Run push.sh to build + deploy the code
#   5. Print verification URLs for both blue and green instances
#
# Prerequisites:
#   - New EC2 instance already launched in AWS Console (Amazon Linux 2023)
#   - SSH port 22 and HTTP port 80 open in the security group
#   - backend/.env exists locally (will be copied to the new instance)
#   - OLD_IP is set below or exported as environment variable
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

BLUE_IP="${BLUE_IP:-54.89.55.202}"   # override by exporting BLUE_IP before running

GREEN_IP="${1:?Usage: ./deploy/green-deploy.sh <NEW_IP> [key.pem]}"
KEY_FILE="${2:-}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$REPO_ROOT/backend/.env"

SSH_OPTS=(-o StrictHostKeyChecking=no -o ConnectTimeout=15)
if [[ -n "$KEY_FILE" ]]; then
  SSH_OPTS+=(-i "$KEY_FILE")
fi
SSH=(ssh "${SSH_OPTS[@]}" "ec2-user@$GREEN_IP")

# ── Preflight checks ─────────────────────────────────────────────────────────
echo ""
echo "============================================================"
echo "  POT Matchmaker — Green Instance Deploy"
echo "  Blue (old):  http://$BLUE_IP"
echo "  Green (new): http://$GREEN_IP"
echo "============================================================"
echo ""

if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: backend/.env not found at $ENV_FILE"
  echo "       Copy backend/.env.example to backend/.env and fill in values first."
  exit 1
fi

echo "==> Waiting for SSH to be ready on $GREEN_IP ..."
for i in {1..12}; do
  if "${SSH[@]}" "echo ok" &>/dev/null; then
    echo "    SSH ready."
    break
  fi
  echo "    Attempt $i/12 — sleeping 10s..."
  sleep 10
done

# ── Step 1: Upload deploy scripts ─────────────────────────────────────────────
echo ""
echo "==> Uploading deploy scripts..."
SCP_OPTS=(-o StrictHostKeyChecking=no)
[[ -n "$KEY_FILE" ]] && SCP_OPTS+=(-i "$KEY_FILE")

scp "${SCP_OPTS[@]}" "$SCRIPT_DIR/setup-ec2.sh"           "ec2-user@$GREEN_IP:~/"
scp "${SCP_OPTS[@]}" "$SCRIPT_DIR/nginx.conf"             "ec2-user@$GREEN_IP:~/"
scp "${SCP_OPTS[@]}" "$SCRIPT_DIR/pot-matchmaker.service" "ec2-user@$GREEN_IP:~/"

# ── Step 2: First-time bootstrap ─────────────────────────────────────────────
echo ""
echo "==> Running first-time EC2 setup (this takes ~2 min)..."
"${SSH[@]}" "bash ~/setup-ec2.sh"

# ── Step 3: Copy .env to new instance ─────────────────────────────────────────
echo ""
echo "==> Copying .env to green instance..."

# Append the new IP to ALLOWED_ORIGINS (non-destructively)
# Read existing value, add new IP if not already present
EXISTING_ORIGINS=$(grep '^ALLOWED_ORIGINS=' "$ENV_FILE" | cut -d= -f2- || echo "")
if echo "$EXISTING_ORIGINS" | grep -q "http://$GREEN_IP"; then
  echo "    http://$GREEN_IP already in ALLOWED_ORIGINS — no change needed."
  ENV_CONTENT=$(cat "$ENV_FILE")
else
  echo "    Adding http://$GREEN_IP to ALLOWED_ORIGINS..."
  ENV_CONTENT=$(sed "s|^ALLOWED_ORIGINS=.*|ALLOWED_ORIGINS=${EXISTING_ORIGINS},http://${GREEN_IP}|" "$ENV_FILE")
fi

# Upload the (possibly modified) .env
printf '%s\n' "$ENV_CONTENT" | "${SSH[@]}" "cat > /home/ec2-user/app/backend/.env"
echo "    .env uploaded."

# ── Step 4: Deploy code ────────────────────────────────────────────────────────
echo ""
echo "==> Running full deploy to green instance..."
bash "$SCRIPT_DIR/push.sh" "$GREEN_IP" "$KEY_FILE"

# ── Step 5: Smoke test ────────────────────────────────────────────────────────
echo ""
echo "==> Smoke testing green instance..."
HEALTH=$(curl -sf "http://$GREEN_IP/health" 2>/dev/null || echo "FAILED")
if echo "$HEALTH" | grep -q '"status"'; then
  echo "    Health check: PASSED ($HEALTH)"
else
  echo "    WARNING: health check returned unexpected response: $HEALTH"
  echo "    Check logs: ssh -i $KEY_FILE ec2-user@$GREEN_IP 'sudo journalctl -u pot-matchmaker -n 50'"
fi

# ── Done ───────────────────────────────────────────────────────────────────────
echo ""
echo "============================================================"
echo "  DEPLOY COMPLETE"
echo ""
echo "  Blue  (original): http://$BLUE_IP"
echo "  Green (new code): http://$GREEN_IP"
echo ""
echo "  Both share the same RDS database (23 attendees)."
echo ""
echo "  Verification checklist:"
echo "  [ ] http://$GREEN_IP/health → {\"status\":\"ok\"}"
echo "  [ ] http://$GREEN_IP        → POT orange brand visible"
echo "  [ ] http://$BLUE_IP         → old version still running"
echo "  [ ] Register flow works on green (no URL validation error)"
echo "  [ ] Mobile bottom tab bar visible at 390px"
echo "============================================================"
echo ""
