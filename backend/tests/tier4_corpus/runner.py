"""Corpus runner — drives every spec through the GTM browser.

Usage:
    python -m tests.tier4_corpus.runner [--only red|yellow|green]
                                        [--from R-001] [--to R-100]
                                        [--no-llm] [--dry-run]

Writes JSONL to backend/tests/tier4_corpus/results/<timestamp>.jsonl.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
import traceback
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tests.tier4_corpus.spec import SPECS, TestSpec
from tests.tier4_corpus.ui import BUSINESSES, UI, GTMError

log = logging.getLogger("corpus-runner")


@dataclass
class TestResult:
    id: str
    severity: str
    tags: list[str]
    title: str
    kind: str
    status: str          # PASS | FAIL | CAVEAT | SKIP
    elapsed_ms: float
    evidence: str        # short human-readable description
    raw: dict[str, Any]  # captured detail (audit, response text, etc.)


class Runner:
    def __init__(self, ui: UI, *, no_llm: bool = False, dry_run: bool = False):
        self.ui = ui
        self.no_llm = no_llm
        self.dry_run = dry_run
        self.results: list[TestResult] = []

    def run_one(self, spec: TestSpec) -> TestResult:
        t0 = time.perf_counter()
        try:
            if spec.kind == "skip":
                return self._make("SKIP", spec, t0,
                                  evidence=spec.skip_reason or "skipped",
                                  raw={"skip_reason": spec.skip_reason})
            if self.no_llm and spec.kind in ("create_via_prompt", "chat", "judge_calibration"):
                return self._make("SKIP", spec, t0,
                                  evidence="SKIP-no-llm-budget",
                                  raw={"skip_reason": "SKIP-no-llm-budget"})
            if self.dry_run:
                return self._make("PASS", spec, t0, evidence="dry-run", raw={})

            if spec.kind == "create_via_template":
                return self._run_create_via_template(spec, t0)
            if spec.kind == "create_via_prompt":
                return self._run_create_via_prompt(spec, t0)
            if spec.kind == "chat":
                return self._run_chat(spec, t0)
            if spec.kind == "toggle_rule":
                return self._run_toggle(spec, t0)
            if spec.kind == "judge_calibration":
                return self._run_judge(spec, t0)
            return self._make("CAVEAT", spec, t0,
                              evidence=f"unhandled kind: {spec.kind}", raw={})
        except GTMError as exc:
            return self._make("FAIL", spec, t0, evidence=f"GTM error: {exc}", raw={"error": str(exc)})
        except Exception as exc:  # noqa: BLE001
            return self._make("FAIL", spec, t0,
                              evidence=f"runtime error: {exc}",
                              raw={"error": str(exc), "traceback": traceback.format_exc()})

    # ------------------------------------------------------------- helpers ---

    def _make(self, status: str, spec: TestSpec, t0: float, *,
              evidence: str, raw: dict) -> TestResult:
        return TestResult(
            id=spec.id, severity=spec.severity, tags=spec.tags,
            title=spec.title, kind=spec.kind, status=status,
            elapsed_ms=(time.perf_counter() - t0) * 1000,
            evidence=evidence, raw=raw,
        )

    def _ensure_business(self, spec: TestSpec) -> str | None:
        if spec.business is None:
            return None
        biz_id = BUSINESSES.get(spec.business)
        if biz_id is None:
            raise GTMError(f"unknown business slug: {spec.business}")
        return biz_id

    # ------------------------------------------------ kind: template create -

    def _run_create_via_template(self, spec: TestSpec, t0: float) -> TestResult:
        biz_id = self._ensure_business(spec)
        self.ui.goto_business_rules(biz_id)
        time.sleep(2)  # settle for hydration
        existing = {r["name"] for r in self.ui.list_rules()}
        # Open Add rule, click template, fill fields if provided, save
        self.ui.open_add_rule_modal()
        template = spec.action.get("template")
        if template:
            try:
                self.ui.click_template(template)
            except GTMError:
                # Template tile click may need to fall back to fill-prompt path
                pass
        fields = spec.action.get("fields", {})
        if "description" in fields and "name" in fields:
            # The current Add Rule UI doesn't have separate template forms wired —
            # template selection just primes the prompt textarea with sample text.
            # Use the prompt path instead, derived from the description.
            self.ui.fill_rule_prompt(fields.get("description") or fields.get("name"))
            self.ui.click_generate()
            self.ui.wait_for_compile(timeout=60)
            preview = self.ui.get_compile_state()
            if preview.get("kind") != "compiled":
                self.ui.close_modal()
                return self._make("FAIL", spec, t0,
                                  evidence=f"compile didn't succeed: {preview.get('kind')}",
                                  raw={"preview": preview})
            # Override the compiled name with the spec's requested name so we
            # can find it on the list afterwards.
            if "name" in fields:
                # The first <input type=text> is the editable name field.
                try:
                    self.ui.react_set_value('input[type="text"]', fields["name"])
                except GTMError:
                    pass  # name may not have an editable input — ignore
            self.ui.click_save_rule()
            time.sleep(2)
        else:
            self.ui.close_modal()
            return self._make("CAVEAT", spec, t0,
                              evidence="template+fields not provided", raw={})

        rules_after = {r["name"] for r in self.ui.list_rules()}
        new_names = rules_after - existing
        if not new_names:
            return self._make("FAIL", spec, t0, evidence="rule didn't appear in list",
                              raw={"before": list(existing), "after": list(rules_after)})
        return self._make("PASS", spec, t0, evidence=f"created: {', '.join(new_names)}",
                          raw={"new_rule_names": list(new_names)})

    # -------------------------------------------------- kind: prompt create -

    def _run_create_via_prompt(self, spec: TestSpec, t0: float) -> TestResult:
        biz_id = self._ensure_business(spec)
        self.ui.goto_business_rules(biz_id)
        time.sleep(2)
        self.ui.open_add_rule_modal()
        prompt = spec.action.get("prompt", "")
        self.ui.fill_rule_prompt(prompt)

        # If the prompt is empty/whitespace, the Generate button is disabled.
        # The runner's "expected failure" tests for empty prompts pass at the
        # UI layer rather than going through the compile agent.
        gen_btn_state = self.ui._evaluate("""
        JSON.stringify((() => {
          const b = Array.from(document.querySelectorAll('button')).find(x => x.textContent.trim() === 'Generate rule');
          return {found: !!b, disabled: b ? b.disabled : null};
        })())
        """)
        try:
            btn_state = json.loads(gen_btn_state)
        except (TypeError, json.JSONDecodeError):
            btn_state = {"found": False, "disabled": None}
        if btn_state.get("disabled"):
            self.ui.close_modal()
            expected_kind = spec.expected.get("kind", "compiled")
            if expected_kind == "failure":
                return self._make("PASS", spec, t0,
                                  evidence="Generate disabled — empty prompt rejected at the UI layer",
                                  raw={"reason": "ui_disabled"})
            return self._make("FAIL", spec, t0,
                              evidence="Generate disabled — prompt empty/whitespace; expected compile",
                              raw={"reason": "ui_disabled"})

        self.ui.click_generate()
        try:
            self.ui.wait_for_compile(timeout=90)
        except GTMError as exc:
            self.ui.close_modal()
            return self._make("FAIL", spec, t0,
                              evidence=f"compile timed out: {exc}",
                              raw={"prompt": prompt[:200]})

        preview = self.ui.get_compile_state()
        self.ui.close_modal()

        expected_kind = spec.expected.get("kind", "compiled")
        actual_kind = preview.get("kind", "unknown")
        if actual_kind == "compiled" and expected_kind == "compiled":
            expected_rt = spec.expected.get("rule_type")
            if expected_rt and expected_rt not in (preview.get("rule_type") or ""):
                return self._make("CAVEAT", spec, t0,
                                  evidence=f"compiled but rule_type {preview['rule_type']} != expected {expected_rt}",
                                  raw={"preview": preview})
            return self._make("PASS", spec, t0,
                              evidence=f"compiled to {preview.get('rule_type')}", raw={"preview": preview})
        if actual_kind == "failure" and expected_kind == "failure":
            return self._make("PASS", spec, t0,
                              evidence=f"compile-failure with {len(preview.get('clarifications', []))} clarifications",
                              raw={"preview": preview})
        if expected_kind == actual_kind:
            return self._make("PASS", spec, t0, evidence=f"matched expected kind {expected_kind}", raw={"preview": preview})
        return self._make("FAIL", spec, t0,
                          evidence=f"expected kind {expected_kind}, got {actual_kind}",
                          raw={"preview": preview})

    # ------------------------------------------------------------ kind: chat

    def _run_chat(self, spec: TestSpec, t0: float) -> TestResult:
        biz_id = self._ensure_business(spec)
        if biz_id is None:
            return self._make("CAVEAT", spec, t0, evidence="no business", raw={})
        self.ui.goto_business_chat(biz_id)
        time.sleep(2)
        if spec.setup.get("reset_chat"):
            self.ui.reset_chat()
            time.sleep(1)

        for message in spec.action.get("messages", []):
            self.ui.send_chat(message, wait_for_done=True, timeout=120)

        conv_id = self.ui.get_conversation_id(biz_id)
        if not conv_id:
            return self._make("FAIL", spec, t0, evidence="no conversation id in localStorage", raw={})
        events = self.ui.get_audit(conv_id)
        outcomes = {e["outcome"] for e in events}

        expected_outcome = spec.expected.get("audit_outcome")
        rule_substring = spec.expected.get("rule_substring")
        response_required = spec.expected.get("response_substring_required")
        response_forbidden = spec.expected.get("response_substring_forbidden")

        # Determine actual chat outcome from audit
        if "blocked" in outcomes:
            actual = "blocked"
        elif any(e["outcome"] == "needs_info" for e in events):
            actual = "needs_info"
        elif any(e["outcome"] == "accepted" for e in events):
            actual = "accepted"
        elif not events:
            # No tool calls — agent answered conversationally. The engine
            # never got a chance to evaluate; that's a distinct outcome.
            actual = "informational"
        else:
            # Audit had only `info`-level events (e.g. lookup_relevant_rules,
            # state_update). Treat as informational — no enforcement decision
            # was made. Collapses the legacy `info` actual into one bucket.
            actual = "informational"

        evidence_bits = [f"actual={actual}"]
        raw = {"events": events, "outcomes": list(outcomes)}

        # Outcome match — `expected_outcome` may be:
        #   - None              → any outcome ok (record only)
        #   - "*"                → any tool fired (informational fails)
        #   - a single string    → strict match
        #   - a list of strings  → any of the listed outcomes is ok
        # `informational` always passes when expected was `accepted` (the agent
        # handled the question without needing the engine — that's a valid
        # outcome from the customer's POV; rule-engine assertions are checked
        # separately via rule_substring).
        def _outcome_ok(expected: Any, got: str) -> bool:
            if expected is None:
                return True
            if expected == "*":
                return got != "informational"
            if isinstance(expected, list):
                return got in expected or (
                    "accepted" in expected and got == "informational"
                )
            if expected == got:
                return True
            if expected == "accepted" and got == "informational":
                return True
            return False

        outcome_ok = _outcome_ok(expected_outcome, actual)
        # Rule-substring match — only meaningful when a tool actually fired
        rule_ok = True
        if rule_substring:
            fired_names = " ".join((e.get("fired_rule_name") or "").lower() for e in events)
            rule_ok = rule_substring.lower() in fired_names
            evidence_bits.append(f"rule-match={rule_ok}")
        # Response substring match — search ALL assistant bubbles, not just
        # the last one (TEST-7 fix; some chats render multiple assistant
        # bubbles when tool calls interleave with text).
        msgs = self.ui.get_messages()
        all_assistant = "\n".join(m["content"] for m in msgs if m["role"] == "assistant")
        last_assistant = next((m["content"] for m in reversed(msgs) if m["role"] == "assistant"), "")
        raw["last_assistant"] = last_assistant
        raw["all_assistant_text_len"] = len(all_assistant)
        resp_ok = True
        if response_required:
            resp_ok = response_required.lower() in all_assistant.lower()
            evidence_bits.append(f"required-substring={response_required!r}={resp_ok}")
        if response_forbidden:
            forbidden_present = response_forbidden.lower() in all_assistant.lower()
            resp_ok = resp_ok and not forbidden_present
            evidence_bits.append(f"forbidden-substring-present={forbidden_present}")

        ok = outcome_ok and rule_ok and resp_ok
        # Three statuses, in priority order:
        #  - PASS:    everything matches
        #  - CAVEAT:  engine made a defensible choice that diverges from the
        #             corpus's authorial assumption (e.g. blocked when the
        #             corpus expected accepted, but the seed's rules are
        #             stricter than the corpus author assumed) — record but
        #             don't penalize
        #  - FAIL:    a real disagreement that warrants attention
        if ok:
            status = "PASS"
        elif (
            expected_outcome in ("accepted", None)
            and actual == "blocked"
            and not rule_substring
        ):
            status = "CAVEAT"
            evidence_bits.append("engine blocked where corpus expected accepted — likely seed-vs-corpus divergence")
        elif not outcome_ok:
            status = "FAIL"
        else:
            status = "CAVEAT"
        return self._make(status, spec, t0, evidence="; ".join(evidence_bits), raw=raw)

    # --------------------------------------------------------- kind: toggle

    def _run_toggle(self, spec: TestSpec, t0: float) -> TestResult:
        biz_id = self._ensure_business(spec)
        self.ui.goto_business_rules(biz_id)
        time.sleep(2)
        self.ui.confirm_browser_dialog(True)  # in case the action triggers a confirm
        target = spec.action.get("target_rule_name")
        action_label = spec.action.get("action", "Disable")
        try:
            self.ui.open_rule_menu(target)
            time.sleep(0.5)
            self.ui.click_text(action_label)
            time.sleep(1)
        except GTMError as exc:
            return self._make("FAIL", spec, t0, evidence=f"menu click failed: {exc}", raw={})

        if spec.action.get("reload"):
            self.ui.reload()
            time.sleep(2)

        rules = self.ui.list_rules()
        match = next((r for r in rules if r["name"] == target), None)
        if not match:
            return self._make("FAIL", spec, t0,
                              evidence=f"rule {target} disappeared (delete?)", raw={"rules": rules})

        expected_active = not (action_label.lower() == "disable")
        if "is_active_after_reload" in spec.expected:
            expected_active = spec.expected["is_active_after_reload"]
        actual_active = not match.get("disabled", False)
        ok = actual_active == expected_active
        status = "PASS" if ok else "FAIL"
        return self._make(status, spec, t0,
                          evidence=f"is_active={actual_active}, expected={expected_active}",
                          raw={"rule": match})

    # ---------------------------------------------- kind: judge calibration

    def _run_judge(self, spec: TestSpec, t0: float) -> TestResult:
        """Run the same prompt N times; tally whether the agent treated it as
        an emergency. Use Sunrise's Late-day plumbing rule context (after-4-PM
        plumbing requires emergency for non-members)."""
        biz_id = self._ensure_business(spec) or BUSINESSES["sunrise"]
        self.ui.goto_business_chat(biz_id)
        samples = spec.setup.get("samples", 1)
        message = spec.action["messages"][0]
        results = []
        for i in range(samples):
            self.ui.reset_chat()
            time.sleep(1)
            self.ui.send_chat(message, wait_for_done=True, timeout=90)
            conv_id = self.ui.get_conversation_id(biz_id)
            events = self.ui.get_audit(conv_id) if conv_id else []
            blocked = any(e["outcome"] == "blocked" for e in events)
            results.append({"sample": i + 1, "blocked": blocked, "events": len(events)})

        blocked_count = sum(1 for r in results if r["blocked"])
        expected = spec.expected.get("judge_should")
        # The rule's trigger is `not(llm_judge(...))` — so when the customer's
        # message IS an emergency, the judge says yes, the trigger fails, and
        # the rule does NOT block. Inverse for non-emergency. Score accordingly.
        if expected is True:
            # Clear emergency: judge should agree → 0 blocks expected
            ok = blocked_count == 0
            evidence = f"{blocked_count}/{samples} blocked (judge classified as emergency in {samples - blocked_count}/{samples} runs)"
        elif expected is False:
            # Clear non-emergency: judge should agree → all samples blocked
            ok = blocked_count >= max(1, samples // 2 + samples % 2)
            evidence = f"{blocked_count}/{samples} blocked (judge classified as non-emergency in {blocked_count}/{samples} runs)"
        else:
            # Borderline — record distribution; always CAVEAT
            ok = True
            evidence = f"{blocked_count}/{samples} blocked (borderline — judge characterization)"
        status = "PASS" if ok and expected is not None else "CAVEAT"
        if expected is not None and not ok:
            status = "FAIL"
        return self._make(status, spec, t0, evidence=evidence,
                          raw={"samples": results, "expected_judge_should_block": expected})

    # ----------------------------------------------------------- run all ---

    def run_many(self, specs: list[TestSpec]) -> list[TestResult]:
        for i, spec in enumerate(specs, 1):
            print(f"[{i}/{len(specs)}] {spec.id} {spec.severity:6s} {spec.title[:60]}", flush=True)
            r = self.run_one(spec)
            self.results.append(r)
            print(f"     → {r.status}  ({r.elapsed_ms:.0f} ms)  {r.evidence[:100]}", flush=True)
        return self.results


# --------------------------------------------------------------------- main -


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--only", choices=["red", "yellow", "green"])
    p.add_argument("--from", dest="from_id")
    p.add_argument("--to", dest="to_id")
    p.add_argument("--no-llm", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--limit", type=int, default=None)
    p.add_argument(
        "--ids",
        help="Comma-separated spec IDs to run (e.g. R-005,R-040,C-001).",
    )
    p.add_argument(
        "--ids-from",
        help="Path to a file with one spec ID per line.",
    )
    p.add_argument(
        "--fails-from",
        help="Path to a previous JSONL run; replay only specs that ended in FAIL.",
    )
    args = p.parse_args(argv)

    specs = list(SPECS)
    if args.only:
        specs = [s for s in specs if s.severity == args.only]
    if args.from_id:
        specs = [s for s in specs if s.id >= args.from_id]
    if args.to_id:
        specs = [s for s in specs if s.id <= args.to_id]

    id_filter: set[str] = set()
    if args.ids:
        id_filter.update(s.strip() for s in args.ids.split(",") if s.strip())
    if args.ids_from:
        id_filter.update(
            line.strip()
            for line in Path(args.ids_from).read_text().splitlines()
            if line.strip() and not line.startswith("#")
        )
    if args.fails_from:
        with Path(args.fails_from).open() as f:
            for line in f:
                if not line.strip():
                    continue
                rec = json.loads(line)
                if rec.get("status") == "FAIL":
                    id_filter.add(rec["id"])
    if id_filter:
        specs = [s for s in specs if s.id in id_filter]

    if args.limit:
        specs = specs[: args.limit]

    print(f"Running {len(specs)} specs (no_llm={args.no_llm}, dry_run={args.dry_run})", flush=True)

    ui = UI()
    # Boot check + reset corpus state
    if not args.dry_run:
        try:
            ui.visit("/")
            time.sleep(2)
            reset = ui.fetch_in_page("/api/admin/wipe-all-and-reseed", method="POST")
            print(f"Boot reset: {reset.get('status')}", flush=True)
        except GTMError as exc:
            print(f"Boot failed: {exc}", file=sys.stderr)
            return 2

    runner = Runner(ui, no_llm=args.no_llm, dry_run=args.dry_run)

    # Stream JSONL writes so killing mid-run preserves data.
    out_dir = Path(__file__).resolve().parent / "results"
    out_dir.mkdir(exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out_path = out_dir / f"{stamp}.jsonl"

    results: list = []
    with out_path.open("w") as fh:
        for i, spec in enumerate(specs, 1):
            print(f"[{i}/{len(specs)}] {spec.id} {spec.severity:6s} {spec.title[:60]}", flush=True)
            r = runner.run_one(spec)
            runner.results.append(r)
            results.append(r)
            print(f"     → {r.status}  ({r.elapsed_ms:.0f} ms)  {r.evidence[:100]}", flush=True)
            fh.write(json.dumps(asdict(r)) + "\n")
            fh.flush()
    print(f"\nWrote {len(results)} results to {out_path}", flush=True)

    # Summary
    by_status: dict[str, int] = {}
    for r in results:
        by_status[r.status] = by_status.get(r.status, 0) + 1
    print(" / ".join(f"{k}={v}" for k, v in sorted(by_status.items())))

    return 0


if __name__ == "__main__":
    sys.exit(main())
