"""UI primitives — drive the AI Guardrails frontend through the GTM browser only.

Every primitive issues `browser_navigate` / `browser_evaluate` / `browser_click`
calls against the GTM browser's HTTP control endpoint at port 9223. There are
no Python-side calls to the FastAPI backend; ground-truth API queries (e.g.
audit log, rules list) are issued via in-page `fetch('/api/proxy/...')`.

The helper handles the React-controlled-input quirk we discovered: real OS
keystrokes via `browser_type_keyboard` don't propagate into React's
controlled `<textarea>` / `<input>`, so `react_set_value` uses the native
setter + dispatchEvent('input') pattern that triggers React's onChange.
"""
from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass, field
from typing import Any

GTM_URL = "http://127.0.0.1:9223"
FRONTEND = "http://127.0.0.1:3001"


class GTMError(RuntimeError):
    pass


@dataclass
class UI:
    gtm: str = GTM_URL
    frontend: str = FRONTEND
    last_evaluate_ms: float = 0.0
    log: list[str] = field(default_factory=list)

    # ---------------------------------------------------------- transport ----
    def _post(self, payload: dict, *, timeout: int = 60) -> dict:
        body = json.dumps(payload)
        r = subprocess.run(
            ["curl", "-s", "-X", "POST", self.gtm,
             "-H", "Content-Type: application/json",
             "-d", body, "--max-time", str(timeout)],
            capture_output=True, text=True, check=False,
        )
        if r.returncode != 0:
            raise GTMError(f"curl exit {r.returncode}: {r.stderr}")
        try:
            return json.loads(r.stdout)
        except json.JSONDecodeError as exc:
            raise GTMError(f"non-JSON response: {r.stdout[:200]}") from exc

    def _evaluate(self, script: str, *, timeout: int = 30) -> Any:
        t0 = time.perf_counter()
        resp = self._post({"command": "evaluate", "params": {"script": script}}, timeout=timeout)
        self.last_evaluate_ms = (time.perf_counter() - t0) * 1000
        if not resp.get("ok"):
            raise GTMError(f"evaluate failed: {resp.get('error')}")
        inner = resp["result"]["result"]
        if isinstance(inner, dict) and inner.get("error"):
            raise GTMError(f"page error: {inner['error']}")
        return inner

    # ----------------------------------------------------------- navigation -
    def visit(self, path: str) -> None:
        url = path if path.startswith("http") else f"{self.frontend}{path}"
        self._post({"command": "navigate", "params": {"url": url}})

    def goto_business_rules(self, business_id: str) -> None:
        self.visit(f"/rules?business={business_id}")
        self.wait_until('document.querySelectorAll("h1").length > 0', timeout=15)

    def goto_business_chat(self, business_id: str) -> None:
        self.visit(f"/chat?business={business_id}")
        self.wait_until('!!document.querySelector("textarea")', timeout=15)

    def goto_business_activity(self, business_id: str) -> None:
        self.visit(f"/activity?business={business_id}")

    def reload(self) -> None:
        self._evaluate("location.reload(); 'reload'")
        time.sleep(2)

    def clear_local_storage(self) -> None:
        self._evaluate("Object.keys(localStorage).filter(k=>k.startsWith('guardrails:')).forEach(k=>localStorage.removeItem(k)); 'cleared'")

    # ------------------------------------------------------- generic DOM ----
    def text(self, selector: str | None = None) -> str:
        if selector is None:
            js = "document.body.innerText"
        else:
            js = f'(document.querySelector({json.dumps(selector)})?.innerText) || ""'
        return self._evaluate(f"JSON.stringify({js})") and json.loads(self._evaluate(f"JSON.stringify({js})"))

    def query_text(self, selector: str) -> str:
        out = self._evaluate(
            f"JSON.stringify({{t: (document.querySelector({json.dumps(selector)})?.innerText) || ''}})"
        )
        return json.loads(out)["t"]

    def query_count(self, selector: str) -> int:
        out = self._evaluate(
            f"JSON.stringify({{n: document.querySelectorAll({json.dumps(selector)}).length}})"
        )
        return json.loads(out)["n"]

    def react_set_value(self, selector: str, value: str) -> None:
        js = f"""
        (() => {{
          const el = document.querySelector({json.dumps(selector)});
          if (!el) return JSON.stringify({{err: 'no element: {selector}'}});
          const proto = el.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
          Object.getOwnPropertyDescriptor(proto, 'value').set.call(el, {json.dumps(value)});
          el.dispatchEvent(new Event('input', {{bubbles: true}}));
          return JSON.stringify({{ok: true}});
        }})()
        """
        out = self._evaluate(js)
        parsed = json.loads(out) if isinstance(out, str) else out
        if parsed.get("err"):
            raise GTMError(parsed["err"])

    def click_text(self, label: str, *, exact: bool = True) -> None:
        """Click a button or link by visible text."""
        js = f"""
        (() => {{
          const want = {json.dumps(label)};
          const all = Array.from(document.querySelectorAll('button, a, [role="button"], li'));
          const m = all.find(el => {{
            const t = (el.textContent || '').trim();
            return {json.dumps(exact)} ? t === want : t.includes(want);
          }});
          if (!m) return JSON.stringify({{err: 'no match for: ' + want}});
          m.click();
          return JSON.stringify({{ok: true, tag: m.tagName}});
        }})()
        """
        out = json.loads(self._evaluate(js))
        if out.get("err"):
            raise GTMError(out["err"])

    def click_selector(self, selector: str) -> None:
        js = f"""
        (() => {{
          const el = document.querySelector({json.dumps(selector)});
          if (!el) return JSON.stringify({{err: 'no element: {selector}'}});
          el.click();
          return JSON.stringify({{ok: true}});
        }})()
        """
        out = json.loads(self._evaluate(js))
        if out.get("err"):
            raise GTMError(out["err"])

    def wait_until(self, predicate_js: str, *, timeout: int = 20, poll: float = 0.4) -> None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                ok = self._evaluate(f"JSON.stringify(!!({predicate_js}))")
            except GTMError:
                ok = "false"
            if ok and ok != "false":
                return
            time.sleep(poll)
        raise GTMError(f"wait_until timed out ({timeout}s): {predicate_js[:80]}")

    def wait_for_text(self, text: str, *, timeout: int = 20) -> None:
        self.wait_until(f"document.body.innerText.includes({json.dumps(text)})", timeout=timeout)

    def wait_for_no_text(self, text: str, *, timeout: int = 20) -> None:
        self.wait_until(f"!document.body.innerText.includes({json.dumps(text)})", timeout=timeout)

    # -------------------------------------------- in-page API (still browser)
    def fetch_in_page(self, path: str, *, method: str = "GET", body: Any = None,
                      timeout: int = 30) -> Any:
        """Issue a fetch from inside the page — goes through /api/proxy with the
        same HTTP Basic auth the real frontend uses. Used for ground-truth
        assertions on audit log, rules list, etc."""
        body_js = ""
        init_pieces = [f'method: {json.dumps(method)}', "headers: {\"Content-Type\": \"application/json\"}"]
        if body is not None:
            init_pieces.append(f'body: JSON.stringify({json.dumps(body)})')
        init = "{" + ", ".join(init_pieces) + "}"
        js = f"""
        (async () => {{
          const r = await fetch({json.dumps('/api/proxy' + path)}, {init});
          const text = await r.text();
          let data; try {{ data = JSON.parse(text); }} catch {{ data = text; }}
          return JSON.stringify({{status: r.status, data}});
        }})()
        """
        out = json.loads(self._evaluate(js, timeout=timeout))
        return out

    # ---------------------------------------------------- rules surface -----
    def list_rules(self) -> list[dict]:
        """Extract a structured snapshot of the visible rule cards."""
        js = """
        JSON.stringify(Array.from(document.querySelectorAll('[class*="rounded-"][class*="bg-bg-elevated"]')).map(card => {
          const h3 = card.querySelector('h3'); if (!h3) return null;
          const typeBadge = card.querySelector('span[class*="font-mono"]')?.textContent.trim() || '';
          const description = card.querySelectorAll('p')[0]?.textContent.trim() || '';
          const disabled = card.textContent.includes('DISABLED');
          return { name: h3.textContent.trim(), type: typeBadge, description, disabled };
        }).filter(Boolean))
        """
        return json.loads(self._evaluate(js))

    def open_add_rule_modal(self) -> None:
        self.click_text("Add rule")
        self.wait_for_text("Add a new rule", timeout=10)

    def fill_rule_prompt(self, prompt: str) -> None:
        self.react_set_value("textarea", prompt)

    def click_template(self, template_name: str) -> None:
        self.click_text(template_name)

    def click_generate(self) -> None:
        self.click_text("Generate rule")

    def wait_for_compile(self, *, timeout: int = 60) -> None:
        self.wait_until(
            '/compiled|clarif/i.test(document.body.innerText)',
            timeout=timeout,
        )

    def get_compile_state(self) -> dict:
        """Returns one of:
        {"kind": "compiled", "rule_type": "...", "name": "...", "description": "..."}
        {"kind": "failure", "clarifications": [...]}
        """
        js = """
        JSON.stringify((() => {
          // Scope all queries to the modal body so we don't accidentally pick up
          // template-tile labels from the left aside as "clarifications".
          const modalHeader = Array.from(document.querySelectorAll('h3')).find(h => /Add a new rule/.test(h.textContent || ''));
          if (!modalHeader) return {kind: 'no-modal'};
          const modal = modalHeader.closest('[class*="rounded-"]');
          const body = modal ? modal.querySelector('section') || modal : document;

          const compiled = Array.from(body.querySelectorAll('span')).find(s => /compiled/i.test(s.textContent || ''));
          if (compiled) {
            const txt = (compiled.textContent || '').replace(/^.*compiled[^a-z_]*/i, '').trim();
            const ruleType = txt.toLowerCase().replace(/ /g, '_');
            const nameInput = body.querySelector('input[type="text"]');
            const tas = body.querySelectorAll('textarea');
            const descTa = tas.length > 1 ? tas[1] : null;
            return {kind: 'compiled', rule_type: ruleType, name: (nameInput && nameInput.value) || '', description: (descTa && descTa.value) || ''};
          }
          // Failure detection: look only inside the right-column body, find a
          // block whose first heading matches "clarifying questions". Filter
          // clarification list items to non-empty, multi-word strings to avoid
          // grabbing decorative bullets.
          const failBlock = Array.from(body.querySelectorAll('div')).find(d => {
            const inner = (d.textContent || '').slice(0, 80);
            return /clarifying questions/i.test(inner);
          });
          if (failBlock) {
            const items = Array.from(failBlock.querySelectorAll('li'))
              .map(li => (li.textContent || '').trim())
              .filter(t => t.length > 8 && /\\s/.test(t));
            return {kind: 'failure', clarifications: items};
          }
          return {kind: 'unknown'};
        })())
        """
        return json.loads(self._evaluate(js))

    def click_save_rule(self) -> None:
        self.click_text("Save rule")

    def close_modal(self) -> None:
        # Click the X button in the modal header
        self._evaluate("""
        (() => {
          const modal = Array.from(document.querySelectorAll('h3')).find(h => /Add a new rule/.test(h.textContent || ''));
          if (modal) {
            const closeBtn = modal.parentElement?.querySelector('button');
            closeBtn?.click();
          }
          return 'closed';
        })()
        """)

    def open_rule_menu(self, rule_name: str) -> None:
        js = f"""
        (() => {{
          const cards = Array.from(document.querySelectorAll('[class*="rounded-"][class*="bg-bg-elevated"]'));
          const card = cards.find(c => c.querySelector('h3')?.textContent.trim() === {json.dumps(rule_name)});
          if (!card) return JSON.stringify({{err: 'no card: {rule_name}'}});
          const menuBtn = card.querySelector('button[aria-label="More"]');
          if (!menuBtn) return JSON.stringify({{err: 'no menu button'}});
          menuBtn.click();
          return JSON.stringify({{ok: true}});
        }})()
        """
        out = json.loads(self._evaluate(js))
        if out.get("err"):
            raise GTMError(out["err"])

    def confirm_browser_dialog(self, accept: bool = True) -> None:
        # window.confirm is hooked at the page level; we override before the click.
        # Return a string sentinel — never let the function value cross the CDP
        # boundary or Electron throws "An object could not be cloned".
        self._evaluate(f"window.confirm = function() {{ return {str(accept).lower()}; }}; 'confirm-set'")

    # ----------------------------------------------------- chat surface -----
    def reset_chat(self) -> None:
        self._evaluate("""
        (() => { const r = Array.from(document.querySelectorAll('button')).find(b => /Reset/i.test(b.textContent.trim())); r?.click(); return 'reset'; })()
        """)
        time.sleep(1)

    def send_chat(self, text: str, *, wait_for_done: bool = True, timeout: int = 90) -> None:
        self.react_set_value("textarea", text)
        # Click the send button (the lone <button> next to the textarea)
        self._evaluate("""
        (() => { const ta = document.querySelector('textarea'); ta?.parentElement?.querySelector('button')?.click(); return 'sent'; })()
        """)
        if wait_for_done:
            # Poll until the assistant bubble has stopped growing
            self._wait_for_stream_stable(timeout=timeout)

    def _wait_for_stream_stable(self, *, timeout: int, stable_for: float = 2.5) -> None:
        """Wait until the agent's reply has stopped streaming.

        Two signals must both be true for `stable_for` consecutive seconds:
          (a) the textarea is enabled (Send button isn't spinning)
          (b) the most recent assistant bubble's text is non-placeholder
              (more than 2 chars, not just an ellipsis)

        Returns silently on timeout — the caller decides what to do with an
        incomplete stream.
        """
        deadline = time.time() + timeout
        last_signature = None
        last_change = time.time()
        while time.time() < deadline:
            try:
                state_json = self._evaluate("""
                JSON.stringify((() => {
                  const ta = document.querySelector('textarea');
                  const enabled = !!ta && !ta.disabled;
                  // Last assistant bubble: stone-bg, not indigo
                  const bubbles = Array.from(document.querySelectorAll('[class*="bg-bg-subtle"]'))
                    .filter(b => !(b.className || '').includes('bg-indigo'));
                  const last = bubbles[bubbles.length - 1];
                  const text = (last && last.textContent || '').trim();
                  return {enabled, len: text.length, placeholder: text === '…' || text === ''};
                })())
                """)
                state = json.loads(state_json)
            except (GTMError, json.JSONDecodeError):
                state = {"enabled": False, "len": 0, "placeholder": True}
            sig = (state.get("enabled"), state.get("len"), state.get("placeholder"))
            if sig != last_signature:
                last_signature = sig
                last_change = time.time()
                time.sleep(0.4)
                continue
            # Stream is stable when textarea is enabled, content is real,
            # and we've had no change for >= stable_for seconds.
            if (state.get("enabled") and not state.get("placeholder")
                    and state.get("len", 0) > 2
                    and time.time() - last_change >= stable_for):
                return
            time.sleep(0.5)

    def get_messages(self) -> list[dict]:
        js = """
        JSON.stringify(Array.from(document.querySelectorAll('[class*="bg-indigo"], [class*="bg-bg-subtle"]')).map(b => {
          const isUser = (b.className || '').includes('bg-indigo');
          return { role: isUser ? 'user' : 'assistant', content: (b.textContent || '').trim() };
        }))
        """
        return json.loads(self._evaluate(js))

    def get_live_activity(self) -> list[dict]:
        js = """
        JSON.stringify(Array.from(document.querySelector('aside')?.querySelectorAll('[class*="rounded-md"]') || []).map(card => ({
          text: (card.textContent || '').trim()
        })))
        """
        return json.loads(self._evaluate(js))

    def get_conversation_id(self, business_id: str) -> str | None:
        js = f"JSON.stringify({{id: localStorage.getItem('guardrails:conv:' + {json.dumps(business_id)})}})"
        return json.loads(self._evaluate(js))["id"]

    def get_audit(self, conversation_id: str) -> list[dict]:
        return self.fetch_in_page(f"/api/conversations/{conversation_id}/events")["data"]

    # -------------------------------------------------- business switcher ---
    def switch_business(self, business_id: str) -> None:
        # Just navigate via URL — that triggers the popstate sync I added
        # Keep the current path; only update ?business=...
        self._evaluate(f"""
        (() => {{
          const url = new URL(window.location.href);
          url.searchParams.set('business', {json.dumps(business_id)});
          window.history.replaceState(null, '', url.toString());
          window.dispatchEvent(new PopStateEvent('popstate'));
          return 'switched';
        }})()
        """)
        time.sleep(0.5)


# ----------------------------------------------------------------------------
# Convenience: business id directory
# ----------------------------------------------------------------------------

BUSINESSES = {
    "sunrise":        "aaaa1111-aaaa-1111-aaaa-111111111111",
    "improveit":      "bbbb2222-bbbb-2222-bbbb-222222222222",
    "pipedreams":     "cccc3333-cccc-3333-cccc-333333333333",
    "cascade":        "dddd4444-dddd-4444-dddd-444444444444",
    "mountain_view":  "eeee5555-eeee-5555-eeee-555555555555",
    "atlantic_pool":  "ffff6666-ffff-6666-ffff-666666666666",
    "bay_area":       "11117777-1111-7777-1111-777777777777",
    "prairiefence":   "22228888-2222-8888-2222-888888888888",
    "gardenworks":    "33339999-3333-9999-3333-999999999999",
    "doormaster":     "4444aaaa-4444-aaaa-4444-aaaaaaaaaaaa",
    "pure_air":       "5555bbbb-5555-bbbb-5555-bbbbbbbbbbbb",
    "sunset_bath":    "6666cccc-6666-cccc-6666-cccccccccccc",
}
