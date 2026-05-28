#!/usr/bin/env bash
# scripts/setup.sh — one-shot bootstrap for the repo.
#
# Idempotent: re-running is safe, it'll only do work that's missing.
# Creates a Python venv via uv, installs frontend deps via npm, and
# scaffolds .env from .env.example if it doesn't exist.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

green() { printf '\033[32m%s\033[0m\n' "$1"; }
yellow() { printf '\033[33m%s\033[0m\n' "$1"; }
red() { printf '\033[31m%s\033[0m\n' "$1"; }

# ---------------------------------------------------------------------------
# 1. Required tools
# ---------------------------------------------------------------------------
need() {
  command -v "$1" >/dev/null 2>&1 || {
    red "✗ missing required tool: $1"
    case "$1" in
      uv)    echo "  install: curl -LsSf https://astral.sh/uv/install.sh | sh" ;;
      node)  echo "  install: brew install node@20  (or use nvm)" ;;
      npm)   echo "  install: brew install node@20  (npm ships with node)" ;;
    esac
    exit 1
  }
}

need uv
need node
need npm

green "✓ uv, node, npm available"

# ---------------------------------------------------------------------------
# 2. .env scaffolding
# ---------------------------------------------------------------------------
if [[ ! -f .env ]]; then
  if [[ -f .env.example ]]; then
    cp .env.example .env
    yellow "→ created .env from .env.example — fill in DATABASE_URL + OPENROUTER_API_KEY"
  else
    red "✗ no .env.example to copy from; can't scaffold .env"
    exit 1
  fi
else
  green "✓ .env already exists"
fi

# ---------------------------------------------------------------------------
# 3. Backend Python deps via uv
# ---------------------------------------------------------------------------
echo "→ syncing backend Python deps (uv)…"
(cd backend && uv sync --python 3.12)
green "✓ backend ready"

# ---------------------------------------------------------------------------
# 4. Frontend Node deps
# ---------------------------------------------------------------------------
if [[ ! -d frontend/node_modules ]]; then
  echo "→ installing frontend deps (npm)…"
  (cd frontend && npm install)
else
  green "✓ frontend node_modules already present"
fi

# ---------------------------------------------------------------------------
# 5. Final summary
# ---------------------------------------------------------------------------
green "============================================================"
green "Setup complete."
echo
echo "Next steps:"
echo "  1. Make sure .env has real DATABASE_URL + OPENROUTER_API_KEY"
echo "  2. Boot dev servers: scripts/run.sh"
echo "  3. Run the eval suite: scripts/eval.sh"
green "============================================================"
