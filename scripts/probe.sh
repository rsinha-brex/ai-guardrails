#!/usr/bin/env bash
# Local probe helper — drives a chat against the production deploy and
# reports the resulting tool_call + fired_rule + accepted/blocked outcome.
# Usage: probe.sh <business_id> "<customer message>" [<state-json>]
# Writes one line of structured output: STATUS=… RULE=… TOOL=… CONV=…

set -euo pipefail
BIZ="${1:?need business_id}"
MSG="${2:?need message}"

ROOT="https://ai-guardrails-ten.vercel.app"
PROXY="$ROOT/api/proxy/api"

CONV=$(curl -s -X POST "$PROXY/conversations" \
  -H 'Content-Type: application/json' \
  -d "{\"business_id\":\"$BIZ\"}" | /Users/rsinha/Documents/ai-guardrails/backend/.venv/bin/python -c "import sys,json;print(json.load(sys.stdin)['id'])")

# Send the message and consume the SSE stream until completion.
curl -sN -X POST "$PROXY/conversations/$CONV/messages" \
  -H 'Content-Type: application/json' \
  -d "{\"content\":$(printf '%s' "$MSG" | /Users/rsinha/Documents/ai-guardrails/backend/.venv/bin/python -c "import sys,json;print(json.dumps(sys.stdin.read()))")}" \
  >/tmp/probe-stream.txt 2>&1

# Read back the audit events after the turn settles.
sleep 2
EVENTS=$(curl -s "$PROXY/conversations/$CONV/events")
SUMMARY=$(echo "$EVENTS" | /Users/rsinha/Documents/ai-guardrails/backend/.venv/bin/python -c "
import sys,json
events = json.load(sys.stdin)
tool_calls = [e for e in events if e.get('event_type') == 'tool_call']
state_updates = [e for e in events if e.get('event_type') == 'state_update']
considered = [e for e in events if e.get('event_type') == 'rule_considered']

print(f'CONV={\"$CONV\"[:8]}')
print(f'EVENTS_TOTAL={len(events)}')
print(f'STATE_UPDATES={len(state_updates)}')
print(f'RULE_CONSIDERED={len(considered)}')
print(f'TOOL_CALLS={len(tool_calls)}')
for tc in tool_calls:
    print(f'  TOOL={tc.get(\"tool_name\")} OUTCOME={tc.get(\"outcome\")} RULE={tc.get(\"fired_rule_name\")}')
")

CONV_DETAIL=$(curl -s "$PROXY/conversations/$CONV")
ASSISTANT=$(curl -s "$PROXY/conversations/$CONV/messages" | /Users/rsinha/Documents/ai-guardrails/backend/.venv/bin/python -c "
import sys,json
msgs = json.load(sys.stdin)
asst = [m for m in msgs if m['role']=='assistant']
print('REPLY=', asst[-1]['content'][:200].replace(chr(10), ' ') if asst else '(none)')
")

echo "$SUMMARY"
echo "$ASSISTANT"
echo "URL=$ROOT/activity/$CONV"
