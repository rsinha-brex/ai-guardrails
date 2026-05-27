"use client";

import { useEffect, useMemo, useState } from "react";
import { api, type RuleSummary } from "@/lib/api";
import { AppShell } from "@/components/AppShell";
import { RuleCard } from "@/components/RuleCard";
import { AddRuleModal } from "@/components/AddRuleModal";
import { TestCasesPanel } from "@/components/TestCasesPanel";
import { useBusinessId } from "@/lib/use-business-id";
import { useResource } from "@/lib/use-resource";
import { Plus } from "lucide-react";

export default function RulesPage() {
  const { businessId, setBusinessId } = useBusinessId();
  const [adding, setAdding] = useState(false);
  const [testing, setTesting] = useState<RuleSummary | null>(null);

  const { data: rules, error, refetch: reload } = useResource<RuleSummary[]>(
    () => (businessId ? api.rules.list(businessId) : Promise.resolve([])),
    [businessId],
  );

  // Auto-select the first business when the page loads with no `?business=`.
  useEffect(() => {
    if (businessId) return;
    api.businesses.list().then((bs) => {
      if (bs[0]) setBusinessId(bs[0].id);
    });
  }, [businessId, setBusinessId]);

  const onCreated = () => {
    setAdding(false);
    reload();
  };

  const subtitle = useMemo(() => {
    if (!rules) return "Loading…";
    const active = rules.filter((r) => r.is_active).length;
    return `${active} active · ${rules.length} total`;
  }, [rules]);

  return (
    <AppShell>
      <div className="flex items-end justify-between mb-6">
        <div>
          <h1 className="font-display text-3xl text-ink">Rules</h1>
          <p className="text-ink-muted mt-1 text-sm">{subtitle}</p>
        </div>
        <button
          type="button"
          onClick={() => setAdding(true)}
          disabled={!businessId}
          className="inline-flex items-center gap-1.5 rounded-md bg-ink text-bg-elevated px-3 py-2 text-sm font-medium hover:bg-ink-soft disabled:opacity-50"
        >
          <Plus className="size-4" /> Add rule
        </button>
      </div>

      {error && (
        <div className="rounded-md border border-rose/40 bg-rose-tint p-4 text-rose mb-4 text-sm">
          {error}
        </div>
      )}

      {rules && rules.length === 0 && (
        <div className="rounded-lg border border-dashed border-border p-12 text-center">
          <p className="text-ink-muted">No rules yet. Add the first one to get started.</p>
        </div>
      )}

      <div className="space-y-3 max-h-[calc(100vh-260px)] overflow-y-auto pr-1 -mr-1">
        {rules?.map((r) => (
          <RuleCard
            key={r.id}
            rule={r}
            businessId={businessId!}
            onChanged={reload}
            onTest={() => setTesting(r)}
          />
        ))}
      </div>

      {adding && businessId && (
        <AddRuleModal
          businessId={businessId}
          onClose={() => setAdding(false)}
          onCreated={onCreated}
        />
      )}

      {testing && businessId && (
        <TestCasesPanel
          rule={testing}
          businessId={businessId}
          onClose={() => setTesting(null)}
          onRuleUpdated={(next) => {
            setTesting(next);
            reload();
          }}
        />
      )}
    </AppShell>
  );
}
