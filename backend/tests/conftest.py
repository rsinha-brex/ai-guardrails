"""pytest fixtures shared across all test tiers."""
from __future__ import annotations

import os

# Ensure tests don't accidentally hit the real DB unless explicitly opted in.
# Tier-1 + tier-2 tests don't need a DB at all.
os.environ.setdefault("OPENROUTER_API_KEY", "")
