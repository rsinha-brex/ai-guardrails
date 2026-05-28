#!/usr/bin/env bash
# scripts/eval.sh — run the full eval suite with per-case progress.
#
# Usage:
#   scripts/eval.sh                # full run (engine + compile + agent_unit + agent_e2e)
#   scripts/eval.sh -k EV-AGT      # filter by ID prefix
#   scripts/eval.sh -m deterministic   # gating subset only (no LLM, no API key required)
#
# Output:
#   - Per-case progress lines streamed to stderr
#   - tests/eval/results/latest.md   (markdown report)
#   - tests/eval/results/<stamp>.jsonl   (raw results)
#
# Without OPENROUTER_API_KEY, probabilistic cases (G9 + E2E) skip cleanly.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/backend"

if [[ ! -d .venv ]]; then
  echo "✗ no .venv yet — run scripts/setup.sh first"
  exit 1
fi

exec .venv/bin/python -m pytest tests/eval --no-header "$@"
