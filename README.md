# AI Guardrails — Take-Home

A multi-tenant guardrails layer for an AI customer-service agent. Business
owners describe rules in plain English (or pick from templates), the platform
compiles them into structured rules, and a Pydantic-AI chat agent enforces
those rules on every tool call.

The polished design reference is `ui_mockup.html` (the `screenshots/` folder
is the same mockup section-by-section). Architecture rationale + tradeoffs
are in `WRITEUP.md`.

## Architecture overview

```
┌──────────────────────────────────┐    REST + SSE    ┌────────────────────────────┐
│  Next.js 16 frontend             │ ───────────────→ │  FastAPI backend           │
│   /rules  /chat  /activity        │ ←─────────────── │   rules · convo · activity │
│   (App Router, Tailwind v4)       │                  │   test cases · admin       │
└──────────────────────────────────┘                  │                            │
                                                      │  Rule engine (pure Python) │
                                                      │  Pydantic-AI agents        │
                                                      │   · main · compile · refine│
                                                      │  SQLAlchemy 2.0            │
                                                      └─────────────┬──────────────┘
                                                                    │
                                                              Supabase Postgres
```

- **Frontend** at `frontend/` (Next.js 16 + Tailwind v4 + handwritten components, all from `ui_mockup.html` design tokens).
- **Backend** at `backend/` (FastAPI + Pydantic-AI + SQLAlchemy + Supabase).
- All `/api/*` traffic is HTTP-Basic-authenticated; the frontend talks to the
  backend through a thin Next.js route handler at `/api/proxy/[...path]` that
  injects the basic-auth header (so credentials never reach the browser).

## Repo layout

```
ai-guardrails/
  README.md                 ← this file
  WRITEUP.md                ← architecture rationale + tradeoffs
  BUGS.md                   ← residual bug ledger
  FAILURES.md               ← run history + systemic-fix log
  TESTING_LOG_500.md        ← 500-spec corpus baseline report
  ui_mockup.html            ← polished mockup
  screenshots/              ← per-section renders of the mockup
  .env  /  .env.example
  backend/
    app/                    ← FastAPI + engine + agents
    tests/tier1_engine/     ← 33 deterministic engine tests, <100ms
    tests/eval/             ← 52-case taxonomy-organized eval lib (deliverable)
    tests/tier4_corpus/     ← 500-spec browser-driven characterization corpus
    pyproject.toml
  frontend/
    src/app/                ← App Router pages + proxy route
    src/components/         ← AppShell, RuleCard, ChatPanel, …
    src/lib/                ← typed API client + SSE parser
```

## Running locally

### 0. Prereqs

- Python 3.12 (managed via [uv](https://github.com/astral-sh/uv))
- Node 20+ (Next.js 16 requires it)
- A Postgres URL — Supabase is what's wired here, but any Postgres works

### 1. Configure secrets

Copy `.env.example` → `.env` and fill in:

- `DATABASE_URL` — Postgres pooler URL
- `OPENROUTER_API_KEY` — for `anthropic/claude-sonnet-4.5` (main + compile) and `anthropic/claude-haiku-4.5` (judge, when used)
- `BASIC_AUTH_USER` / `BASIC_AUTH_PASS` — frontend proxy injects these

### 2. Backend

```
cd backend
uv sync --python 3.12
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The first boot runs `Base.metadata.create_all()` and seeds three businesses
(Del-Air, ImproveIt, Pipedreams) with their rule sets per § 15. Idempotent.

### 3. Frontend

```
cd frontend
npm install
npm run dev -- --port 3001
```

Then open `http://127.0.0.1:3001`. It redirects to `/rules` with a
`?business=<uuid>` query.

### 4. Tests

```
cd backend
uv run pytest tests/tier1_engine -q   # 31 deterministic engine tests, <100ms
```

## API quick-start (curl)

```
# 1. Health
curl -u admin:guardrails http://127.0.0.1:8000/health

# 2. List businesses
curl -u admin:guardrails http://127.0.0.1:8000/api/businesses

# 3. List rules for Del-Air
curl -u admin:guardrails http://127.0.0.1:8000/api/businesses/aaaa1111-aaaa-1111-aaaa-111111111111/rules

# 4. Compile a natural-language rule
curl -u admin:guardrails -X POST \
  http://127.0.0.1:8000/api/businesses/aaaa1111-aaaa-1111-aaaa-111111111111/rules/compile \
  -H 'Content-Type: application/json' \
  -d '{"prompt": "Block bookings before 8 AM on weekdays"}'

# 5. Stream a chat (SSE)
CONV=$(curl -s -u admin:guardrails -X POST http://127.0.0.1:8000/api/conversations \
  -H 'Content-Type: application/json' \
  -d '{"business_id":"aaaa1111-aaaa-1111-aaaa-111111111111"}' | jq -r .id)
curl -u admin:guardrails -N -X POST http://127.0.0.1:8000/api/conversations/$CONV/messages \
  -H 'Content-Type: application/json' \
  -d '{"content":"Hi! Can I book HVAC service Sunday afternoon?"}'

# 6. Reset all demo data
curl -u admin:guardrails -X POST http://127.0.0.1:8000/api/admin/reset-demo-data
```

## Demo script

1. `/rules?business=…` — Del-Air's six seeded rules render as cards (type
   badge, name, description, applies-to-tools, action menu).
2. **Add rule → Generate** — type "Block bookings before 8 AM on weekdays",
   click Generate, see the compile preview, save.
3. `/chat` — ask "Hi! Can I book HVAC service Sunday afternoon?" — the agent
   streams a polite refusal because the business-hours rule fires.
4. `/activity` — the conversation appears with a red "BLOCKED" badge.
5. Click into it — the timeline shows interleaved messages and tool events,
   color-coded by outcome. "Show agent context" reveals the system prompt
   snapshot from conversation start.
6. Back on `/rules`, click **Test** on a rule, add a case, click **Run all** —
   the runner spins an isolated conversation, runs the agent, and marks
   pass/fail. If it fails, click **Refine rule with AI**.

See `WRITEUP.md` for the architecture rationale, eval gaps, and tradeoffs.
