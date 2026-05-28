#!/usr/bin/env bash
# scripts/run.sh — boot the backend (FastAPI) and frontend (Next.js) dev
# servers in two foreground processes. Trap Ctrl-C to kill both cleanly.
#
# Usage:
#   scripts/run.sh                 # boot both, default ports (8000, 3001)
#   BACKEND_PORT=9000 scripts/run.sh
#   FRONTEND_PORT=3002 scripts/run.sh
#
# If the user already has dev servers running, this script will detect the
# port collision and refuse to start a second instance — kill the existing
# one first.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-3001}"

green() { printf '\033[32m%s\033[0m\n' "$1"; }
yellow() { printf '\033[33m%s\033[0m\n' "$1"; }
red() { printf '\033[31m%s\033[0m\n' "$1"; }

port_in_use() {
  lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1
}

if port_in_use "$BACKEND_PORT"; then
  red "✗ port $BACKEND_PORT is already in use (backend). Kill it first or set BACKEND_PORT."
  exit 1
fi
if port_in_use "$FRONTEND_PORT"; then
  red "✗ port $FRONTEND_PORT is already in use (frontend). Kill it first or set FRONTEND_PORT."
  exit 1
fi

# ---------------------------------------------------------------------------
# Boot both, save PIDs, kill them on exit.
# ---------------------------------------------------------------------------
BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  yellow "→ shutting down dev servers…"
  [[ -n "$BACKEND_PID" ]] && kill "$BACKEND_PID" 2>/dev/null || true
  [[ -n "$FRONTEND_PID" ]] && kill "$FRONTEND_PID" 2>/dev/null || true
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

green "→ backend on http://127.0.0.1:$BACKEND_PORT  (auth: see .env)"
(cd backend && uv run uvicorn app.main:app --host 127.0.0.1 --port "$BACKEND_PORT") &
BACKEND_PID=$!

# Pull demo creds from .env so the health check uses whatever the user
# actually configured. Falls back to the documented defaults if .env is
# missing those keys (the seeded backend ships with the demo credentials
# documented in .env.example).
BASIC_USER="$(grep -E '^BASIC_AUTH_USER=' .env 2>/dev/null | cut -d'=' -f2- | tr -d '"' || echo)"
BASIC_PASS="$(grep -E '^BASIC_AUTH_PASS=' .env 2>/dev/null | cut -d'=' -f2- | tr -d '"' || echo)"
BASIC_USER="${BASIC_USER:-admin}"
BASIC_PASS="${BASIC_PASS:-guardrails}"

# Wait for backend health before booting frontend so we know it's up.
echo "→ waiting for backend health…"
for _ in $(seq 1 30); do
  if curl -sf -u "$BASIC_USER:$BASIC_PASS" "http://127.0.0.1:$BACKEND_PORT/health" >/dev/null 2>&1; then
    green "✓ backend healthy"
    break
  fi
  sleep 0.5
done

green "→ frontend on http://127.0.0.1:$FRONTEND_PORT"
(cd frontend && npm run dev -- --port "$FRONTEND_PORT") &
FRONTEND_PID=$!

green "============================================================"
green "Both servers running. Ctrl-C to stop."
green "  Backend:  http://127.0.0.1:$BACKEND_PORT  (basic auth: see .env)"
green "  Frontend: http://127.0.0.1:$FRONTEND_PORT"
green "============================================================"

# Wait for either child to exit; cleanup trap handles the rest.
wait -n
