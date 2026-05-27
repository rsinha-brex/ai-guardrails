"""Compile a JSONL of TestResult records into TESTING_LOG_500.md.

Usage:
    python -m tests.tier4_corpus.report path/to/results.jsonl
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


SECTION_RANGES = [
    ("1A Templates",            "R-001", "R-060"),
    ("1B NL compile",           "R-061", "R-120"),
    ("1C Editing",              "R-121", "R-150"),
    ("1D Combinations",         "R-151", "R-190"),
    ("1E Adversarial",          "R-191", "R-230"),
    ("1F Lifecycle",            "R-231", "R-250"),
    ("2A Single-rule chat",     "C-001", "C-070"),
    ("2B Boundaries",           "C-071", "C-120"),
    ("2C State gathering",      "C-121", "C-160"),
    ("2D Multi-rule",           "C-161", "C-200"),
    ("2E LLM judge calibration","C-201", "C-230"),
    ("2F Output constraint",    "C-231", "C-250"),
]

STATUS_EMOJI = {"PASS": "✅", "CAVEAT": "⚠️", "FAIL": "❌", "SKIP": "⏭️"}
SEVERITY_EMOJI = {"red": "🔴", "yellow": "🟡", "green": "🟢"}


def section_for(test_id: str) -> str:
    for name, lo, hi in SECTION_RANGES:
        if lo <= test_id <= hi:
            return name
    return "?"


def render(jsonl_path: Path) -> str:
    rows: list[dict[str, Any]] = []
    with jsonl_path.open() as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))

    out: list[str] = []
    out.append(f"# AI Guardrails — 500-Test Corpus Results\n")
    out.append(f"_Generated from `{jsonl_path.name}` · {len(rows)} rows_\n")

    # ----- Summary
    by_status = Counter(r["status"] for r in rows)
    by_sev = defaultdict(Counter)
    for r in rows:
        by_sev[r["severity"]][r["status"]] += 1

    out.append("## Summary\n")
    out.append("| Severity | PASS | CAVEAT | FAIL | SKIP | Total |")
    out.append("| --- | --- | --- | --- | --- | --- |")
    for sev in ("red", "yellow", "green"):
        c = by_sev[sev]
        total = sum(c.values())
        if total:
            out.append(f"| {SEVERITY_EMOJI[sev]} {sev} | {c.get('PASS',0)} | "
                       f"{c.get('CAVEAT',0)} | {c.get('FAIL',0)} | {c.get('SKIP',0)} | {total} |")
    out.append(f"| **All** | **{by_status.get('PASS',0)}** | "
               f"**{by_status.get('CAVEAT',0)}** | **{by_status.get('FAIL',0)}** | "
               f"**{by_status.get('SKIP',0)}** | **{len(rows)}** |\n")

    # ----- Per-section detail tables
    rows_by_section = defaultdict(list)
    for r in rows:
        rows_by_section[section_for(r["id"])].append(r)
    for name, lo, hi in SECTION_RANGES:
        section_rows = sorted(rows_by_section.get(name, []), key=lambda r: r["id"])
        if not section_rows:
            continue
        out.append(f"## Section {name} ({lo}..{hi})\n")
        out.append("| ID | Sev | Tags | Status | Title | Evidence |")
        out.append("| --- | --- | --- | --- | --- | --- |")
        for r in section_rows:
            sev = SEVERITY_EMOJI.get(r["severity"], "?")
            stat = f"{STATUS_EMOJI.get(r['status'], '?')} {r['status']}"
            tags = " ".join(f"`{t}`" for t in r.get("tags", []) or [])
            evidence = (r.get("evidence", "") or "")[:140].replace("|", "\\|").replace("\n", " ")
            title = (r.get("title", "") or "")[:60].replace("|", "\\|")
            out.append(f"| {r['id']} | {sev} | {tags} | {stat} | {title} | {evidence} |")
        out.append("")

    # ----- Gap inventory
    out.append("## Gap inventory (skip reasons)\n")
    skip_groups: dict[str, list[str]] = defaultdict(list)
    for r in rows:
        if r["status"] == "SKIP":
            reason = r.get("evidence") or r.get("raw", {}).get("skip_reason") or "no-reason"
            skip_groups[reason].append(r["id"])
    out.append("| Reason | Count | Test IDs (first 8) |")
    out.append("| --- | --- | --- |")
    for reason, ids in sorted(skip_groups.items(), key=lambda kv: -len(kv[1])):
        sample = ", ".join(sorted(ids)[:8])
        out.append(f"| {reason} | {len(ids)} | {sample}{' …' if len(ids) > 8 else ''} |")
    out.append("")

    # ----- LLM judge appendix
    judge_rows = [r for r in rows if r.get("kind") == "judge_calibration"]
    if judge_rows:
        out.append("## LLM-judge calibration (Section 2E)\n")
        out.append("| ID | Severity | Customer message (gist) | Expected | Samples blocked | Evidence |")
        out.append("| --- | --- | --- | --- | --- | --- |")
        for r in sorted(judge_rows, key=lambda r: r["id"]):
            raw = r.get("raw") or {}
            samples = raw.get("samples") or []
            blocked = sum(1 for s in samples if s.get("blocked"))
            expected = raw.get("expected_judge_should_block")
            exp_str = "true" if expected is True else "false" if expected is False else "borderline"
            sev = SEVERITY_EMOJI.get(r["severity"], "?")
            title = (r.get("title", "") or "")[:60].replace("|", "\\|")
            out.append(f"| {r['id']} | {sev} | {title} | {exp_str} | {blocked}/{len(samples) or 1} | {r.get('evidence','')[:60]} |")
        out.append("")

    # ----- Cost / time
    elapsed = sum(r.get("elapsed_ms", 0) for r in rows) / 1000
    out.append("## Time spent\n")
    out.append(f"- Total wall-clock: ~{elapsed/60:.1f} min ({elapsed:.0f} s sum of per-test timings)")
    by_kind = Counter(r.get("kind") for r in rows)
    out.append(f"- Test kinds: {dict(by_kind)}")
    out.append("")

    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("jsonl")
    p.add_argument("-o", "--output", default="../../TESTING_LOG_500.md")
    args = p.parse_args(argv)

    jsonl = Path(args.jsonl).resolve()
    md = render(jsonl)
    out_path = (jsonl.parent / args.output).resolve() if not Path(args.output).is_absolute() else Path(args.output).resolve()
    # Walk up from the jsonl path until we find the repo root (the dir
    # containing pyproject.toml + frontend/), then drop the report there.
    repo_root = jsonl.resolve()
    while repo_root.name:
        if (repo_root / "frontend").exists() and (repo_root / "backend").exists():
            break
        if repo_root == repo_root.parent:
            break
        repo_root = repo_root.parent
    if (repo_root / "frontend").exists() and (repo_root / "backend").exists():
        out_path = repo_root / "TESTING_LOG_500.md"
    out_path.write_text(md)
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
