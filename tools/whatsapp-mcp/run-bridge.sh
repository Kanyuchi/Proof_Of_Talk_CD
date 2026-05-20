#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
# Load the gitignored allowlist into the environment for the Go bridge.
set -a
[ -f .env ] && source .env
set +a
cd whatsapp-bridge
exec go run main.go
