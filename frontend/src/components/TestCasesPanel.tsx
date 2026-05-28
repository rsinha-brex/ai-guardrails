"use client";

import { useEffect, useState } from "react";
import { api, type RuleSummary, type TestCase, type RefineResponse } from "@/lib/api";
import { cn } from "@/lib/cn";
import { Check, X, Play, Loader2, Plus, Sparkles, Trash2 } from "lucide-react";

type Props = {
  rule: RuleSummary;
  businessId: string;
  onClose: () => void;
  onRuleUpdated: (next: RuleSummary) => void;
};

export function TestCasesPanel({ rule, businessId, onClose, onRuleUpdated }: Props) {
  const [cases, setCases] = useState<TestCase[] | null>(null);
  const [adding, setAdding] = useState(false);
  const [newMsg, setNewMsg] = useState("");
  const [newExpected, setNewExpected] = useState<"block" | "allow" | "needs_info">("block");
  const [running, setRunning] = useState(false);
  const [runningOne, setRunningOne] = useState<string | null>(null);
  const [refining, setRefining] = useState<string | null>(null);
  const [refinement, setRefinement] = useState<RefineResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    api.testCases.list(rule.id).then(setCases).catch((e) => setError(String(e)));
  };
  useEffect(load, [rule.id]);

  const add = async () => {
    if (!newMsg.trim()) return;
    try {
      await api.testCases.create(rule.id, {
        customer_message: newMsg.trim(),
        expected_outcome: newExpected,
      });
      setNewMsg("");
      setAdding(false);
      load();
    } catch (e) {
      setError(String(e));
    }
  };

  const runAll = async () => {
    setRunning(true);
    try {
      const updated = await api.testCases.runAll(rule.id);
      setCases(updated);
    } catch (e) {
      setError(String(e));
    } finally {
      setRunning(false);
    }
  };

  const runOne = async (id: string) => {
    setRunningOne(id);
    try {
      const updated = await api.testCases.runOne(rule.id, id);
      setCases((prev) => prev?.map((c) => (c.id === id ? updated : c)) || prev);
    } catch (e) {
      setError(String(e));
    } finally {
      setRunningOne(null);
    }
  };

  const remove = async (id: string) => {
    if (!confirm("Delete this test case?")) return;
    await api.testCases.remove(rule.id, id);
    load();
  };

  const refine = async (id: string) => {
    setRefining(id);
    setRefinement(null);
    try {
      const r = await api.testCases.refine(rule.id, id);
      setRefinement(r);
    } catch (e) {
      setError(String(e));
    } finally {
      setRefining(null);
    }
  };

  const applyRefinement = async () => {
    if (!refinement?.recompiled) return;
    const c = refinement.recompiled;
    const updated = await api.rules.update(businessId, rule.id, {
      name: c.name,
      description: c.description,
      applies_when_description: c.applies_when_description,
      parameters: c.parameters as Record<string, unknown>,
      applies_to_tools: c.applies_to_tools,
      enforcement_mode: c.enforcement_mode,
      priority: c.priority,
      source_prompt: c.source_prompt,
    });
    onRuleUpdated(updated);
    setRefinement(null);
  };

  const summary =
    cases === null
      ? "Loading…"
      : `${cases.filter((c) => c.last_run_result === "pass").length} pass · ${cases.filter((c) => c.last_run_result === "fail").length} fail`;

  return (
    <div className="fixed inset-0 z-50 flex bg-ink/30">
      <div className="flex-1" onClick={onClose} />
      <aside className="w-[440px] bg-bg-elevated border-l border-border h-full overflow-y-auto">
        <header className="px-5 py-4 border-b border-border flex items-start justify-between">
          <div>
            <h3 className="font-display text-xl text-ink">Test cases</h3>
            <p className="text-xs text-ink-muted mt-0.5">
              {rule.name} · {cases?.length || 0} scenarios
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="size-8 grid place-items-center rounded-md hover:bg-bg-subtle text-ink-muted"
          >
            <X className="size-4" />
          </button>
        </header>

        <div className="px-5 py-3 border-b border-border bg-bg-subtle flex items-center justify-between">
          <div className="text-sm text-ink-soft">{summary}</div>
          <button
            type="button"
            onClick={runAll}
            disabled={running || (cases?.length || 0) === 0}
            className="inline-flex items-center gap-1.5 rounded-md bg-ink text-bg-elevated px-3 py-1.5 text-xs font-medium hover:bg-ink-soft disabled:opacity-50"
          >
            {running ? <Loader2 className="size-3 animate-spin" /> : <Play className="size-3" />}
            {running ? "Running…" : "Run all"}
          </button>
        </div>

        {error && (
          <div className="m-4 rounded-md border border-rose/40 bg-rose-tint p-3 text-rose text-xs">
            {error}
          </div>
        )}

        <div className="p-4 space-y-3">
          {cases?.map((c) => {
            const status = c.last_run_result;
            const ribbon =
              status === "pass"
                ? "border-l-4 border-l-accent"
                : status === "fail"
                  ? "border-l-4 border-l-rose"
                  : "border-l-4 border-l-ink-faint";
            return (
              <div
                key={c.id}
                className={cn("rounded-md border border-border bg-bg-elevated p-3", ribbon)}
              >
                <div className="flex items-center justify-between text-xs">
                  <span
                    className={cn(
                      "font-mono uppercase tracking-widest",
                      status === "pass"
                        ? "text-accent"
                        : status === "fail"
                          ? "text-rose"
                          : "text-ink-muted",
                    )}
                  >
                    {status ? (status === "pass" ? "✓ PASS" : "× FAIL") : "— Not run"}
                  </span>
                  <div className="flex items-center gap-1">
                    <button
                      type="button"
                      onClick={() => runOne(c.id)}
                      disabled={runningOne === c.id}
                      className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded text-ink-muted hover:bg-bg-subtle"
                    >
                      {runningOne === c.id ? "Running…" : "Run"}
                    </button>
                    <button
                      type="button"
                      onClick={() => remove(c.id)}
                      className="size-6 grid place-items-center rounded text-ink-muted hover:bg-rose-tint hover:text-rose"
                    >
                      <Trash2 className="size-3" />
                    </button>
                  </div>
                </div>
                <div className="text-sm italic text-ink-soft mt-1">&ldquo;{c.customer_message}&rdquo;</div>
                <div className="text-[11px] text-ink-muted mt-1 font-mono">
                  expect: {c.expected_outcome}
                  {c.last_run_details && (typeof c.last_run_details === "object") && "actual" in (c.last_run_details as Record<string, unknown>) && (
                    <>
                      {" · "}got: {String((c.last_run_details as Record<string, unknown>).actual)}
                    </>
                  )}
                </div>
                {status === "fail" && (
                  <div className="mt-2">
                    <button
                      type="button"
                      onClick={() => refine(c.id)}
                      disabled={refining === c.id}
                      className="inline-flex items-center gap-1.5 text-xs text-amber bg-amber-tint border border-amber/30 px-2 py-1 rounded-md hover:border-amber/60"
                    >
                      {refining === c.id ? (
                        <Loader2 className="size-3 animate-spin" />
                      ) : (
                        <Sparkles className="size-3" />
                      )}
                      Refine rule with AI
                    </button>
                  </div>
                )}
              </div>
            );
          })}

          {/* Inline add form */}
          {adding ? (
            <div className="rounded-md border border-dashed border-border p-3 space-y-2">
              <textarea
                value={newMsg}
                onChange={(e) => setNewMsg(e.target.value)}
                placeholder="Customer message"
                rows={2}
                className="w-full rounded-md border border-border bg-bg p-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent/30"
              />
              <div className="flex items-center gap-2">
                <select
                  value={newExpected}
                  onChange={(e) => setNewExpected(e.target.value as "block" | "allow" | "needs_info")}
                  className="rounded-md border border-border bg-bg-elevated px-2 py-1 text-xs"
                >
                  <option value="block">expect: block</option>
                  <option value="allow">expect: allow</option>
                  <option value="needs_info">expect: needs_info</option>
                </select>
                <button
                  type="button"
                  onClick={add}
                  disabled={!newMsg.trim()}
                  className="ml-auto rounded-md bg-ink text-bg-elevated px-3 py-1 text-xs font-medium hover:bg-ink-soft disabled:opacity-50"
                >
                  Add
                </button>
                <button
                  type="button"
                  onClick={() => setAdding(false)}
                  className="text-xs text-ink-muted hover:text-ink"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => setAdding(true)}
              className="w-full rounded-md border border-dashed border-border py-3 text-sm text-ink-muted hover:border-border-strong hover:text-ink inline-flex items-center justify-center gap-1.5"
            >
              <Plus className="size-3.5" /> Add a test case
            </button>
          )}
        </div>

        {refinement && (
          <RefinementDiff
            res={refinement}
            onClose={() => setRefinement(null)}
            onApply={applyRefinement}
          />
        )}
      </aside>
    </div>
  );
}

function RefinementDiff({
  res,
  onClose,
  onApply,
}: {
  res: RefineResponse;
  onClose: () => void;
  onApply: () => void;
}) {
  return (
    <div className="fixed inset-0 z-60 grid place-items-center bg-ink/30 p-6">
      <div className="w-full max-w-2xl rounded-[var(--radius-lg)] bg-bg-elevated shadow-lg overflow-hidden max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between px-5 py-4 border-b border-border">
          <h3 className="font-display text-lg">Suggested rule update</h3>
          <button
            type="button"
            onClick={onClose}
            className="size-8 grid place-items-center rounded-md hover:bg-bg-subtle text-ink-muted"
          >
            <X className="size-4" />
          </button>
        </div>
        <div className="p-5 space-y-3">
          <p className="text-sm text-ink-soft">{res.refinement.explanation}</p>
          {res.refinement.diff_summary && (
            <div className="text-xs font-mono text-ink-muted">{res.refinement.diff_summary}</div>
          )}
          <div className="rounded-md bg-bg-subtle p-3 text-sm font-mono whitespace-pre-wrap">
            {res.refinement.updated_prompt}
          </div>
          {res.recompiled && (
            <details className="text-xs">
              <summary className="cursor-pointer text-ink-muted">Recompiled parameters</summary>
              <pre className="mt-2 rounded bg-ink/95 text-bg-elevated p-3 overflow-auto max-h-56 text-[11px] font-mono">
                {JSON.stringify(res.recompiled.parameters, null, 2)}
              </pre>
            </details>
          )}
          {res.failure && (
            <div className="rounded-md border border-amber/40 bg-amber-tint p-3 text-amber text-xs">
              Couldn&apos;t recompile — {res.failure.rationale}
            </div>
          )}
        </div>
        <footer className="px-5 py-3 border-t border-border flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="text-xs text-ink-muted hover:text-ink px-2 py-1"
          >
            Reject
          </button>
          <button
            type="button"
            onClick={onApply}
            disabled={!res.recompiled}
            className="inline-flex items-center gap-1.5 rounded-md bg-accent text-bg-elevated px-3 py-1.5 text-xs font-medium hover:bg-accent-soft disabled:opacity-50"
          >
            <Check className="size-3" /> Apply changes
          </button>
        </footer>
      </div>
    </div>
  );
}
